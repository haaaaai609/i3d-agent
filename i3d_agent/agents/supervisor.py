"""Supervisor agent for task coordination and routing."""

from typing import Dict, Any, Optional, List

from i3d_agent.agents.base import AgentConfig, BaseAgent
from i3d_agent.llm import get_llm_client, Message


class SupervisorAgent(BaseAgent):
    """Supervisor agent for analyzing user intent and routing to appropriate agents.

    This agent analyzes user queries and routes them to specialized agents
    based on intent detection using keyword matching rules.

    Routing Rules:
    - search: "搜索", "查找", "相似", "匹配", "推荐"
    - rag: "文档", "手册", "教程", "api", "使用", "如何", "怎么"
    - process: "处理", "状态", "进度", "任务"
    - general: default fallback for unmatched queries
    """

    # Intent keywords for routing
    SEARCH_KEYWORDS = {"搜索", "查找", "相似", "匹配", "推荐"}
    RAG_KEYWORDS = {"文档", "手册", "教程", "api", "使用", "如何", "怎么"}
    PROCESS_KEYWORDS = {"处理", "状态", "进度", "任务"}

    def __init__(self, config: Optional[AgentConfig] = None) -> None:
        """Initialize the supervisor agent.

        Args:
            config: Optional agent configuration. Uses default if not provided.
        """
        if config is None:
            config = AgentConfig(
                name="supervisor",
                role="task_coordinator",
                instructions="Analyze user intent and route tasks to appropriate agents.",
            )
        super().__init__(config=config, tools=[])

    def analyze_intent(self, query: str) -> Dict[str, str]:
        """Analyze user query to determine task type and target agent.

        Args:
            query: User query string to analyze

        Returns:
            Dictionary with keys:
                - task_type: One of 'search', 'rag', 'process', 'general'
                - agent: Target agent name for the task
                - confidence: Confidence level (high/medium/low)
                - matched_keywords: List of keywords that triggered the match
        """
        query_lower = query.lower()

        # Check for search intent
        search_matches = [kw for kw in self.SEARCH_KEYWORDS if kw in query_lower]
        if search_matches:
            return {
                "task_type": "search",
                "agent": "search_agent",
                "confidence": "high" if len(search_matches) > 1 else "medium",
                "matched_keywords": search_matches,
            }

        # Check for RAG intent
        rag_matches = [kw for kw in self.RAG_KEYWORDS if kw in query_lower]
        if rag_matches:
            return {
                "task_type": "rag",
                "agent": "rag_agent",
                "confidence": "high" if len(rag_matches) > 1 else "medium",
                "matched_keywords": rag_matches,
            }

        # Check for process intent
        process_matches = [kw for kw in self.PROCESS_KEYWORDS if kw in query_lower]
        if process_matches:
            return {
                "task_type": "process",
                "agent": "process_agent",
                "confidence": "high" if len(process_matches) > 1 else "medium",
                "matched_keywords": process_matches,
            }

        # Default to general intent
        return {
            "task_type": "general",
            "agent": "general_agent",
            "confidence": "low",
            "matched_keywords": [],
        }

    def format_search_response(self, results: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
        """Format search results into a structured response.

        Args:
            results: List of search result items
            query: Original search query

        Returns:
            Formatted response dictionary
        """
        return {
            "task_type": "search",
            "query": query,
            "results": results,
            "count": len(results),
            "status": "success" if results else "no_results",
        }

    def format_rag_response(self, answer: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format RAG response with sources into a structured response.

        Args:
            answer: Generated answer from RAG system
            sources: List of source documents used

        Returns:
            Formatted response dictionary
        """
        return {
            "task_type": "rag",
            "answer": answer,
            "sources": sources,
            "source_count": len(sources),
            "status": "success",
        }

    def format_process_response(self, status: Dict[str, Any]) -> Dict[str, Any]:
        """Format process status update into a structured response.

        Args:
            status: Process status information

        Returns:
            Formatted response dictionary
        """
        return {
            "task_type": "process",
            "status": status.get("status", "unknown"),
            "progress": status.get("progress", 0),
            "message": status.get("message", ""),
            "details": status.get("details", {}),
        }

    def format_general_response(self, messages: List[str]) -> Dict[str, Any]:
        """Format general conversational response.

        Args:
            messages: List of message strings to include in response

        Returns:
            Formatted response dictionary
        """
        return {
            "task_type": "general",
            "messages": messages,
            "message_count": len(messages),
            "status": "success",
        }

    async def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle general conversational queries using LLM.

        Args:
            message: User message
            conversation_history: Optional conversation history
            tenant_id: Optional tenant ID

        Returns:
            Response dictionary with answer
        """
        system_prompt = """你是 I3D Agent System 的智能助手，专门帮助用户处理 3D CAD 模型搜索、技术文档查询和任务处理等相关问题。

你的职责：
1. 友好地回应用户的问候和一般性问题
2. 解释 I3D 系统的功能和使用方法
3. 引导用户使用搜索、文档查询等功能
4. 使用简洁、专业的中文回答

如果用户询问具体的技术问题、搜索功能或文档查询，引导他们使用相应的功能。"""

        # Build conversation context
        messages = [Message(role="user", content=message)]

        if conversation_history:
            for msg in conversation_history[-5:]:  # Last 5 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if content:
                    messages.append(Message(role=role, content=content))

        llm_client = get_llm_client()
        response = await llm_client.generate(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.8,
        )

        return {
            "task_type": "general",
            "answer": response,
            "status": "success",
        }
