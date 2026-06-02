"""HyDE (Hypothetical Document Embeddings) service for improving retrieval.

HyDE generates hypothetical answer documents for questions, then uses these
documents for retrieval instead of the original query. This improves retrieval
quality because the hypothetical document is semantically closer to the actual
documents in the corpus.
"""

from typing import Optional

from i3d_agent.llm.client import simple_generate
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)

# Question detection patterns (Chinese and English)
QUESTION_WORDS = [
    # Chinese question words
    "如何", "怎样", "怎么", "如何", "怎样",
    "什么", "是", "哪些", "哪个",
    "为什么", "为何",
    "哪里", "哪儿", "何处",
    "何时", "几时",
    "谁", "谁人",
    "多少", "几许",
    # English question words
    "how", "what", "which", "why",
    "where", "when", "who", "whose",
    "can", "could", "would", "should",
    "is", "are", "do", "does", "did",
]


class HyDEService:
    """HyDE (Hypothetical Document Embeddings) service.

    This service generates hypothetical answer documents for questions,
    improving retrieval quality by using these documents instead of the
    original query for vector similarity search.
    """

    def __init__(self):
        """Initialize HyDE service."""
        pass

    async def generate_hypothetical(self, query: str) -> Optional[str]:
        """Generate hypothetical answer document for a query.

        Only generates hypothetical documents for questions. For non-questions
        (keywords, phrases, statements), returns None to use the original query.

        Args:
            query: User query text

        Returns:
            Hypothetical answer document, or None if query is not a question
        """
        if not query or not query.strip():
            logger.warning("Empty query provided for HyDE generation")
            return None

        # Only generate hypothetical documents for questions
        if not self._is_question(query):
            logger.debug(f"Query '{query[:50]}...' is not a question, skipping HyDE")
            return None

        try:
            # Generate hypothetical answer document
            hypothetical_doc = await self._llm_generate(query)

            logger.info(f"Generated hypothetical document for query '{query[:50]}...'")
            return hypothetical_doc

        except Exception as e:
            logger.error(f"HyDE generation failed: {e}, falling back to original query")
            # Fallback to None (use original query)
            return None

    def _is_question(self, text: str) -> bool:
        """Detect if text is a question.

        Checks if the text starts with or contains question words.

        Args:
            text: Text to check

        Returns:
            True if text appears to be a question, False otherwise
        """
        if not text or not text.strip():
            return False

        # Convert to lowercase for checking
        text_lower = text.lower().strip()

        # Check if it ends with question mark
        if text_lower.endswith("?"):
            return True

        # Check if it starts with question words
        for word in QUESTION_WORDS:
            if text_lower.startswith(word):
                return True

        return False

    async def _llm_generate(self, query: str) -> str:
        """Generate hypothetical answer document using LLM.

        Args:
            query: User query/question

        Returns:
            Hypothetical answer document
        """
        system_prompt = """你是一个专业的文档生成助手。你的任务是根据用户的问题，生成一个假设性的答案文档。

规则：
1. 生成的文档应该像是一个真实的、专业的答案
2. 包含具体的技术细节、代码示例或步骤说明
3. 结构清晰，有条理
4. 内容应该与问题高度相关
5. 用中文回答（除非问题明确要求英文）
6. 不要说"假设"或"可能"，而是以确定的语气直接回答
7. 输出应该是一个完整的、可直接使用的文档片段"""

        user_prompt = f"""请为以下问题生成一个详细的、专业的答案文档：

问题：{query}

答案文档："""

        return await simple_generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.7
        )
