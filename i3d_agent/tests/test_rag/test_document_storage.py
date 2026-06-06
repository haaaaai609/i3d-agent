"""Tests for RAG document file storage."""

from io import BytesIO

import pytest

from i3d_agent.rag.document_storage import DocumentStorage


def test_archive_upload_writes_dated_file(tmp_path):
    storage = DocumentStorage(
        documents_path=str(tmp_path / "documents"),
        import_roots=[str(tmp_path / "import")]
    )

    stored = storage.archive_upload(
        BytesIO(b"# Hello\n\nWorld"),
        filename="hello.md",
        tenant_id="default"
    )

    assert stored.file_name == "hello.md"
    assert stored.file_md5
    assert stored.content.startswith("# Hello")
    assert "default" in stored.storage_path
    assert "hello.md" in stored.storage_path


def test_scan_directory_filters_and_hashes_files(tmp_path):
    import_root = tmp_path / "import"
    import_root.mkdir()
    (import_root / "a.md").write_text("same", encoding="utf-8")
    (import_root / "b.md").write_text("same", encoding="utf-8")
    (import_root / "skip.bin").write_bytes(b"binary")

    storage = DocumentStorage(
        documents_path=str(tmp_path / "documents"),
        import_roots=[str(import_root)]
    )

    scanned = storage.scan_directory(str(import_root), include_patterns=["*.md"])

    assert len(scanned) == 2
    assert scanned[0].file_md5 == scanned[1].file_md5
    assert {item.file_name for item in scanned} == {"a.md", "b.md"}


def test_scan_directory_rejects_paths_outside_import_roots(tmp_path):
    import_root = tmp_path / "import"
    outside = tmp_path / "outside"
    import_root.mkdir()
    outside.mkdir()

    storage = DocumentStorage(
        documents_path=str(tmp_path / "documents"),
        import_roots=[str(import_root)]
    )

    with pytest.raises(ValueError, match="outside configured import roots"):
        storage.scan_directory(str(outside))
