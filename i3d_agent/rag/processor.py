"""Document processor for parsing, chunking, and metadata extraction."""

import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ChunkSizeConfig:
    """分块大小配置"""
    default_size: int = 800
    default_overlap: int = 150
    technical_size: int = 1000
    technical_overlap: int = 200
    business_size: int = 600
    business_overlap: int = 100
    api_size: int = 500
    api_overlap: int = 0


class DocumentProcessor:
    """文档处理器 - 负责文档解析、切分和元数据提取"""

    def __init__(self, config: Optional[ChunkSizeConfig] = None):
        self.config = config or ChunkSizeConfig()

    def split_content(
        self,
        content: str,
        doc_type: str = "technical",
        doc_id: Optional[str] = None,
        title: Optional[str] = None,
        language: str = "zh"
    ) -> List[Dict[str, Any]]:
        """根据文档类型切分内容"""
        if not content or not content.strip():
            return []

        if doc_type == "api":
            return self.split_api_document(content, doc_id, title, language)
        elif doc_type == "business":
            return self.split_paragraph(content, doc_id, title, language)
        else:  # technical
            return self.split_markdown(content, doc_id, title, language)

    def split_markdown(
        self,
        content: str,
        doc_id: Optional[str] = None,
        title: Optional[str] = None,
        language: str = "zh"
    ) -> List[Dict[str, Any]]:
        """切分 Markdown 文档 - 按标题层级和语义边界"""
        if not content or not content.strip():
            return []

        # 提取代码块并替换为占位符
        content, code_blocks = self._extract_code_blocks(content)

        # 按标题切分
        sections = self._split_by_headings(content)

        # 不再合并节，直接切分每个节
        chunks = []
        for i, section in enumerate(sections):
            section_chunks = self._split_section(
                section,
                chunk_size=self.config.technical_size,
                overlap=self.config.technical_overlap,
                code_blocks=code_blocks
            )
            chunks.extend(section_chunks)

        # 添加元数据
        chunks = self._add_metadata(
            chunks,
            doc_type="technical",
            doc_id=doc_id,
            title=title,
            language=language
        )

        return chunks

    def split_api_document(
        self,
        content: str,
        doc_id: Optional[str] = None,
        title: Optional[str] = None,
        language: str = "zh"
    ) -> List[Dict[str, Any]]:
        """切分 API 文档 - 按端点切分"""
        if not content or not content.strip():
            return []

        # 提取代码块
        content, code_blocks = self._extract_code_blocks(content)

        # 按 API 端点切分 (匹配 ## METHOD /path 格式)
        api_pattern = r'^(##\s+(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+[^\n]+)$'
        sections = re.split(api_pattern, content, flags=re.MULTILINE)

        chunks = []
        current_endpoint = None

        for i, section in enumerate(sections):
            if not section or not section.strip():
                continue

            # 检查是否是端点标题
            if re.match(r'^##\s+(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)', section.strip()):
                current_endpoint = section.strip()
            elif current_endpoint:
                # 这是端点的内容
                chunk_content = current_endpoint + "\n\n" + section.strip()
                chunks.append({
                    'content': self._restore_code_blocks(chunk_content, code_blocks),
                    'metadata': {
                        'endpoint': current_endpoint,
                        'section': current_endpoint
                    }
                })
                current_endpoint = None

        # 如果没有找到 API 端点，则将整个内容作为一个 chunk
        if not chunks and content.strip():
            chunks.append({
                'content': self._restore_code_blocks(content, code_blocks),
                'metadata': {
                    'section': title or 'API Documentation'
                }
            })

        # 添加元数据
        chunks = self._add_metadata(
            chunks,
            doc_type="api",
            doc_id=doc_id,
            title=title,
            language=language
        )

        return chunks

    def split_paragraph(
        self,
        content: str,
        doc_id: Optional[str] = None,
        title: Optional[str] = None,
        language: str = "zh"
    ) -> List[Dict[str, Any]]:
        """按段落切分文档（使用字符长度）"""
        if not content or not content.strip():
            return []

        # 按段落分割
        paragraphs = re.split(r'\n\s*\n', content.strip())

        chunks = []
        current_chunk = ""
        current_paragraphs = []
        max_chars = self.config.business_size * 2  # token 转字符

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # 如果当前段落加上后会超过限制，先保存当前 chunk
            if current_chunk and len(current_chunk + "\n\n" + para) > max_chars:
                if current_chunk:
                    chunks.append({
                        'content': current_chunk,
                        'metadata': {
                            'paragraph_count': len(current_paragraphs)
                        }
                    })
                current_chunk = para
                current_paragraphs = [para]
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
                current_paragraphs.append(para)

        # 添加最后一个 chunk
        if current_chunk:
            chunks.append({
                'content': current_chunk,
                'metadata': {
                    'paragraph_count': len(current_paragraphs)
                }
            })

        # 添加元数据
        chunks = self._add_metadata(
            chunks,
            doc_type="business",
            doc_id=doc_id,
            title=title,
            language=language
        )

        return chunks

    def estimate_tokens(self, text: str) -> int:
        """估算文本的 token 数量

        中文: 约 1.5 字符 = 1 token
        英文: 约 4 字符 = 1 token
        """
        if not text:
            return 0

        # 统计中文字符
        chinese_chars = len(re.findall(r'[一-鿿]', text))
        # 统计非中文字符
        other_chars = len(text) - chinese_chars

        # 估算 token 数
        chinese_tokens = chinese_chars / 1.5
        other_tokens = other_chars / 4

        return int(chinese_tokens + other_tokens)

    def calculate_content_hash(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _extract_code_blocks(self, content: str) -> Tuple[str, List[Dict[str, str]]]:
        """提取代码块并替换为占位符

        Returns:
            (处理后的内容, 代码块列表)
        """
        code_blocks = []
        placeholder_template = "___CODE_BLOCK_{}___"

        def replace_block(match):
            code_blocks.append({
                'lang': match.group(1) or '',
                'code': match.group(2)
            })
            return placeholder_template.format(len(code_blocks) - 1)

        # 匹配 ```lang...``` 格式的代码块
        pattern = r'```(\w*)\n(.*?)```'
        content = re.sub(pattern, replace_block, content, flags=re.DOTALL)

        return content, code_blocks

    def _restore_code_blocks(self, content: str, code_blocks: List[Dict[str, str]]) -> str:
        """将代码块占位符替换回原始代码块"""
        for i, block in enumerate(code_blocks):
            placeholder = f"___CODE_BLOCK_{i}___"
            lang = block['lang'] or ''
            restored = f"```{lang}\n{block['code']}```"
            content = content.replace(placeholder, restored)

        return content

    def _split_by_headings(self, content: str) -> List[Dict[str, str]]:
        """按标题切分内容"""
        sections = []
        lines = content.split('\n')

        current_section = []
        current_heading = ""

        for line in lines:
            # 检查是否是标题
            if line.strip().startswith('#'):
                # 保存当前节
                if current_section:
                    sections.append({
                        'heading': current_heading,
                        'content': '\n'.join(current_section)
                    })

                current_heading = line.strip()
                current_section = [line]
            else:
                current_section.append(line)

        # 添加最后一个节
        if current_section:
            sections.append({
                'heading': current_heading,
                'content': '\n'.join(current_section)
            })

        # 过滤掉空内容的节
        sections = [s for s in sections if s['content'].strip()]

        # 如果没有找到标题，返回整个内容
        if not sections:
            return [{'heading': '', 'content': content}]

        return sections

    def _merge_small_sections(self, sections: List[Dict[str, str]], max_size: int) -> List[Dict[str, str]]:
        """合并过小的节（使用字符长度而非 token 估算）"""
        if not sections:
            return sections

        merged = []
        current_chunk = sections[0]
        # 使用字符长度作为合并依据，避免 token 估算不准确的问题
        # 中文约 1.5 字符 = 1 token，所以 max_size tokens ≈ max_size * 1.5 chars
        max_chars = max_size * 2  # 使用更保守的 2x 倍数

        for section in sections[1:]:
            combined_content = current_chunk['content'] + "\n\n" + section['content']
            combined_length = len(combined_content)

            if combined_length <= max_chars:
                # 合并
                current_chunk = {
                    'heading': current_chunk['heading'],
                    'content': combined_content
                }
            else:
                # 保存当前 chunk，开始新的
                merged.append(current_chunk)
                current_chunk = section

        merged.append(current_chunk)
        return merged

    def _split_section(
        self,
        section: Dict[str, str],
        chunk_size: int,
        overlap: int,
        code_blocks: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """切分单个节（使用字符长度，包含硬切分回退）"""
        content = section['content']
        heading = section['heading']

        # 使用字符长度作为切分依据
        max_chars = chunk_size * 2  # token 转字符的倍数
        overlap_chars = overlap * 2

        # 如果内容在限制内，不需要切分
        if len(content) <= max_chars:
            return [{
                'content': self._restore_code_blocks(content, code_blocks),
                'metadata': {
                    'section': heading,
                    'chunk_index': 0
                }
            }]

        # 按句子切分
        sentences = re.split(r'([。！？\.!?])', content)
        sentences = [''.join(pair) for pair in zip(sentences[0::2], sentences[1::2]) if pair[0]]

        # 检查句子切分是否有效（如果所有"句子"都很长，说明切分失败）
        if sentences and all(len(s) > max_chars for s in sentences if s.strip()):
            # 句子切分失败，使用字符级硬切分作为回退
            return self._split_by_chars(content, heading, max_chars, overlap_chars, code_blocks)

        chunks = []
        current_chunk = ""
        chunk_index = 0

        for i, sentence in enumerate(sentences):
            test_chunk = current_chunk + sentence if current_chunk else sentence

            if len(test_chunk) <= max_chars:
                current_chunk = test_chunk
            else:
                # 保存当前 chunk
                if current_chunk:
                    chunks.append({
                        'content': self._restore_code_blocks(current_chunk, code_blocks),
                        'metadata': {
                            'section': heading,
                            'chunk_index': chunk_index
                        }
                    })
                    chunk_index += 1

                # 开始新 chunk（带 overlap）
                if overlap_chars > 0:
                    # 获取最近的几个句子作为 overlap
                    overlap_sentences = self._get_overlap_sentences_by_chars(sentences, i, overlap_chars)
                    current_chunk = ''.join(overlap_sentences) + sentence
                else:
                    current_chunk = sentence

        # 添加最后一个 chunk
        if current_chunk:
            chunks.append({
                'content': self._restore_code_blocks(current_chunk, code_blocks),
                'metadata': {
                    'section': heading,
                    'chunk_index': chunk_index
                }
            })

        return chunks

    def _split_by_chars(
        self,
        content: str,
        heading: str,
        max_chars: int,
        overlap_chars: int,
        code_blocks: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """字符级硬切分（当句子切分失败时使用）"""
        chunks = []
        chunk_index = 0
        start = 0
        content_length = len(content)

        while start < content_length:
            # 计算当前 chunk 的结束位置
            end = min(start + max_chars, content_length)

            # 如果不是最后一块，尝试在空格或换行处切分
            if end < content_length:
                # 往回找最近的换行或空格
                for i in range(end, max(start, end - 100), -1):
                    if content[i] in '\n \t':
                        end = i + 1
                        break

            # 提取当前 chunk
            chunk_content = content[start:end]
            chunks.append({
                'content': self._restore_code_blocks(chunk_content, code_blocks),
                'metadata': {
                    'section': heading,
                    'chunk_index': chunk_index
                }
            })
            chunk_index += 1

            # 移动 start 位置（考虑 overlap）
            start = end - overlap_chars if end < content_length else end

        return chunks

    def _get_overlap_sentences(self, sentences: List[str], current_index: int, overlap_tokens: int) -> List[str]:
        """获取用于重叠的句子"""
        overlap_sentences = []
        token_count = 0

        # 从当前句子往前找
        for i in range(current_index - 1, -1, -1):
            sentence = sentences[i]
            sentence_tokens = self.estimate_tokens(sentence)

            if token_count + sentence_tokens <= overlap_tokens:
                overlap_sentences.insert(0, sentence)
                token_count += sentence_tokens
            else:
                break

        return overlap_sentences

    def _get_overlap_sentences_by_chars(self, sentences: List[str], current_index: int, overlap_chars: int) -> List[str]:
        """获取用于重叠的句子（基于字符长度）"""
        overlap_sentences = []
        char_count = 0

        # 从当前句子往前找
        for i in range(current_index - 1, -1, -1):
            sentence = sentences[i]
            sentence_chars = len(sentence)

            if char_count + sentence_chars <= overlap_chars:
                overlap_sentences.insert(0, sentence)
                char_count += sentence_chars
            else:
                break

        return overlap_sentences

    def _add_metadata(
        self,
        chunks: List[Dict[str, Any]],
        doc_type: str,
        doc_id: Optional[str],
        title: Optional[str],
        language: str
    ) -> List[Dict[str, Any]]:
        """为所有 chunks 添加元数据"""
        for i, chunk in enumerate(chunks):
            if 'metadata' not in chunk:
                chunk['metadata'] = {}

            chunk['metadata'].update({
                'doc_type': doc_type,
                'doc_id': doc_id,
                'title': title,
                'language': language,
                'chunk_index': i,
                'chunk_hash': self.calculate_content_hash(chunk['content']),
                'token_count': self.estimate_tokens(chunk['content'])
            })

        return chunks
