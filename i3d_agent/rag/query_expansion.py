"""Query expansion service for improving retrieval recall using LLM."""

from typing import List
from i3d_agent.llm.client import simple_generate
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)


class QueryExpansionService:
    """Query expansion service - generates alternative query formulations using LLM."""

    def __init__(self):
        """Initialize query expansion service."""
        pass

    async def expand_query(
        self,
        query: str,
        num_variations: int = 3
    ) -> List[str]:
        """Expand query into multiple alternative formulations.

        Args:
            query: Original query text
            num_variations: Number of variations to generate (default: 3)

        Returns:
            List of query variations including the original query
        """
        if not query or not query.strip():
            logger.warning("Empty query provided for expansion")
            return [query] if query else []

        try:
            # Generate variations using LLM
            variations_text = await self._llm_generate(query, num_variations)

            # Parse and clean variations
            variations = self._parse_variations(variations_text)

            # Add original query if not already present
            if query not in variations:
                variations.insert(0, query)

            # Remove duplicates while preserving order
            seen = set()
            unique_variations = []
            for var in variations:
                if var not in seen:
                    seen.add(var)
                    unique_variations.append(var)

            logger.info(f"Expanded query '{query[:50]}...' into {len(unique_variations)} variations")
            return unique_variations

        except Exception as e:
            logger.error(f"Query expansion failed: {e}, falling back to original query")
            # Fallback to original query only
            return [query]

    async def _llm_generate(self, query: str, num_variations: int) -> str:
        """Generate query variations using LLM.

        Args:
            query: Original query
            num_variations: Number of variations to generate

        Returns:
            Generated variations text
        """
        system_prompt = """你是一个搜索查询优化专家。你的任务是生成与原查询语义相同但表述不同的替代查询，以提高搜索召回率。

规则：
1. 生成的查询应保持原意，但使用不同的词汇和句式
2. 考虑同义词、相关概念、不同的表述方式
3. 每行一个查询变体
4. 不要添加编号或项目符号
5. 直接输出查询文本，不要有其他内容"""

        user_prompt = f"""请为以下查询生成 {num_variations} 个不同的表述方式，每行一个：

查询：{query}

变体："""

        return await simple_generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.7
        )

    def _parse_variations(self, text: str) -> List[str]:
        """Parse variations from LLM response text.

        Args:
            text: LLM response text

        Returns:
            List of cleaned variation strings
        """
        if not text:
            return []

        variations = []

        # Split by newlines
        lines = text.strip().split('\n')

        for line in lines:
            # Clean the line
            cleaned = self._clean_line(line)
            if cleaned:
                variations.append(cleaned)

        return variations

    def _clean_line(self, line: str) -> str:
        """Clean a single line from LLM response.

        Args:
            line: Raw line from LLM response

        Returns:
            Cleaned line text
        """
        # Remove leading/trailing whitespace
        line = line.strip()

        if not line:
            return ""

        # Remove numbered list format (e.g., "1.", "2.", etc.)
        if line[0].isdigit() and len(line) > 1 and line[1] in ['.', ')', '、']:
            line = line[2:].strip()

        # Remove bullet points
        if line.startswith('-') or line.startswith('•') or line.startswith('*'):
            line = line[1:].strip()

        # Remove markdown-style bold
        line = line.replace('**', '').replace('*', '')

        return line.strip()
