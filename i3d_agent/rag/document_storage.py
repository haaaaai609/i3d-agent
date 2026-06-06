"""File storage helpers for RAG document imports."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import mimetypes
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO, Dict, Iterable, List, Optional


SUPPORTED_TEXT_EXTENSIONS = {".md", ".txt", ".json", ".html", ".htm"}
DEFAULT_EXCLUDE_PATTERNS = [
    "**/.git/**",
    "**/node_modules/**",
    "**/dist/**",
    "**/__pycache__/**",
]


@dataclass
class StoredDocument:
    """A file archived for RAG ingestion."""

    file_name: str
    file_md5: str
    file_size: int
    mime_type: str
    storage_path: str
    source_path: Optional[str]
    content: str


@dataclass
class ScannedFile:
    """A file discovered during batch import."""

    source_path: str
    file_name: str
    file_md5: str
    file_size: int
    mime_type: str


class DocumentStorage:
    """Archives source files and extracts text for RAG ingestion."""

    def __init__(
        self,
        documents_path: str,
        import_roots: Optional[Iterable[str]] = None,
        now: Optional[datetime] = None,
    ):
        self.documents_path = Path(documents_path).resolve()
        self.import_roots = [
            Path(root).resolve() for root in (import_roots or []) if str(root).strip()
        ]
        self.now = now or datetime.now()

    def archive_upload(
        self,
        file_obj: BinaryIO,
        filename: str,
        tenant_id: str,
        source_path: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> StoredDocument:
        """Archive a file-like object and return extracted content."""
        data = file_obj.read()
        if isinstance(data, str):
            data = data.encode("utf-8")
        return self._archive_bytes(
            data,
            filename,
            tenant_id,
            source_path=source_path,
            mime_type=mime_type,
        )

    def archive_path(self, path: str, tenant_id: str) -> StoredDocument:
        """Archive an existing path from an allowed import root."""
        source = self._resolve_allowed_path(path)
        data = source.read_bytes()
        return self._archive_bytes(data, source.name, tenant_id, source_path=str(source))

    def scan_directory(
        self,
        directory: str,
        recursive: bool = True,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> List[ScannedFile]:
        """Scan an allowed directory and return supported files with MD5 values."""
        root = self._resolve_allowed_path(directory)
        if not root.is_dir():
            raise ValueError(f"Import path is not a directory: {directory}")

        includes = include_patterns or ["*.md", "*.txt", "*.json", "*.html", "*.htm"]
        excludes = DEFAULT_EXCLUDE_PATTERNS + (exclude_patterns or [])
        iterator = root.rglob("*") if recursive else root.glob("*")

        results: List[ScannedFile] = []
        for path in iterator:
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if not self._matches(rel, includes):
                continue
            if self._matches(rel, excludes):
                continue
            if path.suffix.lower() not in SUPPORTED_TEXT_EXTENSIONS:
                continue

            data = path.read_bytes()
            mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            results.append(
                ScannedFile(
                    source_path=str(path.resolve()),
                    file_name=path.name,
                    file_md5=hashlib.md5(data).hexdigest(),
                    file_size=len(data),
                    mime_type=mime_type,
                )
            )

        return results

    def _archive_bytes(
        self,
        data: bytes,
        filename: str,
        tenant_id: str,
        source_path: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> StoredDocument:
        file_md5 = hashlib.md5(data).hexdigest()
        safe_name = self._safe_filename(filename)
        date_dir = self.now.strftime("%Y-%m-%d")
        target_dir = self.documents_path / tenant_id / date_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{file_md5}_{safe_name}"
        target.write_bytes(data)

        return StoredDocument(
            file_name=filename,
            file_md5=file_md5,
            file_size=len(data),
            mime_type=mime_type or mimetypes.guess_type(filename)[0] or "application/octet-stream",
            storage_path=str(target),
            source_path=source_path,
            content=self._extract_text(data, filename),
        )

    def _resolve_allowed_path(self, raw_path: str) -> Path:
        path = Path(raw_path).expanduser().resolve()
        if not self.import_roots:
            raise ValueError("No RAG import roots are configured")

        for root in self.import_roots:
            try:
                path.relative_to(root)
                return path
            except ValueError:
                continue

        allowed = ", ".join(str(root) for root in self.import_roots)
        raise ValueError(f"Path is outside configured import roots: {path}. Allowed: {allowed}")

    def _extract_text(self, data: bytes, filename: str) -> str:
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_TEXT_EXTENSIONS:
            raise ValueError(f"Unsupported document type: {suffix}")

        text = data.decode("utf-8-sig")
        if suffix == ".json":
            try:
                parsed = json.loads(text)
                return json.dumps(parsed, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                return text
        return text

    @staticmethod
    def _safe_filename(filename: str) -> str:
        name = Path(filename).name.strip() or "document"
        return re.sub(r"[^A-Za-z0-9._-]+", "_", name)

    @staticmethod
    def _matches(path: str, patterns: List[str]) -> bool:
        return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)
