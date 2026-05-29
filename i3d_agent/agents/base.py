"""Base agent classes for i3d-agent-system."""

from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field, field_validator


class AgentConfig(BaseModel):
    """Configuration for an agent.

    Attributes:
        name: Agent name/identifier
        role: Agent role (e.g., 'researcher', 'assistant')
        instructions: System instructions for the agent
        llm_model: LLM model identifier
        temperature: Sampling temperature (0.0 to 2.0)
    """

    name: str = Field(description="Agent name/identifier")
    role: str = Field(description="Agent role or function")
    instructions: str = Field(default="", description="System instructions for the agent")
    llm_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="LLM model identifier to use",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 to 2.0)",
    )

    @field_validator("name", "role")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace from string fields."""
        return v.strip() if isinstance(v, str) else v


class BaseAgent:
    """Base agent class providing common functionality.

    This class provides the foundation for all agent implementations,
    including configuration management, tool handling, and prompt generation.

    Attributes:
        config: Agent configuration
        tools: List of available tools for the agent
    """

    def __init__(self, config: AgentConfig, tools: Optional[List[Dict[str, Any]]] = None) -> None:
        """Initialize the base agent.

        Args:
            config: Agent configuration
            tools: Optional list of tools available to the agent
        """
        self.config = config
        self.tools: List[Dict[str, Any]] = tools if tools is not None else []

    def add_tool(self, tool: Dict[str, Any]) -> None:
        """Add a tool to the agent's tool list.

        Args:
            tool: Tool dictionary containing at minimum 'name' and 'description'
        """
        self.tools.append(tool)

    def get_system_prompt(self) -> str:
        """Build and return the system prompt for this agent.

        The system prompt includes:
        - Agent role
        - Agent instructions
        - Available tools (if any)

        Returns:
            Formatted system prompt string
        """
        parts = [
            f"Role: {self.config.role}",
            f"Instructions: {self.config.instructions}",
            "",
            "Available Tools:",
            self._format_tools(),
        ]

        return "\n".join(parts)

    def _format_tools(self) -> str:
        """Format the list of tools for inclusion in system prompt.

        Returns:
            Formatted string listing available tools
        """
        if not self.tools:
            return "No tools available."

        tool_descriptions = []
        for tool in self.tools:
            name = tool.get("name", "unknown")
            description = tool.get("description", "")
            tool_descriptions.append(f"- {name}: {description}")

        return "\n".join(tool_descriptions)
