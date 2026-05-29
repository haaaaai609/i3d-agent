"""Tests for base agent classes."""

import pytest
from pydantic import ValidationError

from i3d_agent.agents.base import AgentConfig, BaseAgent


class TestAgentConfig:
    """Tests for AgentConfig Pydantic model."""

    def test_agent_config_creation(self):
        """Test creating AgentConfig with all fields."""
        config = AgentConfig(
            name="test_agent",
            role="assistant",
            instructions="You are a helpful assistant.",
            llm_model="claude-3-opus-20240229",
            temperature=0.7,
        )
        assert config.name == "test_agent"
        assert config.role == "assistant"
        assert config.instructions == "You are a helpful assistant."
        assert config.llm_model == "claude-3-opus-20240229"
        assert config.temperature == 0.7

    def test_agent_config_defaults(self):
        """Test AgentConfig default values."""
        config = AgentConfig(
            name="test_agent",
            role="assistant",
        )
        assert config.name == "test_agent"
        assert config.role == "assistant"
        assert config.instructions == ""
        assert config.llm_model == "claude-3-5-sonnet-20241022"
        assert config.temperature == 0.7

    def test_agent_config_validation(self):
        """Test AgentConfig field validation."""
        # Temperature should be between 0 and 2
        with pytest.raises(ValidationError):
            AgentConfig(name="test", role="assistant", temperature=3.0)

        with pytest.raises(ValidationError):
            AgentConfig(name="test", role="assistant", temperature=-0.5)


class TestBaseAgent:
    """Tests for BaseAgent class."""

    def test_base_agent_init(self):
        """Test BaseAgent initialization."""
        config = AgentConfig(
            name="test_agent",
            role="assistant",
            instructions="Help users.",
        )
        agent = BaseAgent(config=config, tools=[])

        assert agent.config.name == "test_agent"
        assert agent.tools == []

    def test_base_agent_with_tools(self):
        """Test BaseAgent with initial tools."""
        config = AgentConfig(name="test", role="assistant")
        tools = [{"name": "search", "description": "Search the web"}]
        agent = BaseAgent(config=config, tools=tools)

        assert len(agent.tools) == 1
        assert agent.tools[0]["name"] == "search"

    def test_add_tool(self):
        """Test adding a tool to agent."""
        config = AgentConfig(name="test", role="assistant")
        agent = BaseAgent(config=config, tools=[])

        tool = {"name": "calculator", "description": "Calculate math expressions"}
        agent.add_tool(tool)

        assert len(agent.tools) == 1
        assert agent.tools[0] == tool

    def test_add_multiple_tools(self):
        """Test adding multiple tools."""
        config = AgentConfig(name="test", role="assistant")
        agent = BaseAgent(config=config, tools=[])

        agent.add_tool({"name": "tool1", "description": "First tool"})
        agent.add_tool({"name": "tool2", "description": "Second tool"})

        assert len(agent.tools) == 2

    def test_get_system_prompt(self):
        """Test system prompt generation."""
        config = AgentConfig(
            name="test_agent",
            role="researcher",
            instructions="Analyze data and provide insights.",
        )
        agent = BaseAgent(config=config, tools=[])

        prompt = agent.get_system_prompt()

        assert "researcher" in prompt
        assert "Analyze data and provide insights." in prompt

    def test_get_system_prompt_with_tools(self):
        """Test system prompt includes available tools."""
        config = AgentConfig(
            name="test_agent",
            role="assistant",
            instructions="Help users.",
        )
        tools = [
            {"name": "search", "description": "Search the web"},
            {"name": "calculate", "description": "Perform calculations"},
        ]
        agent = BaseAgent(config=config, tools=tools)

        prompt = agent.get_system_prompt()

        assert "search" in prompt
        assert "Search the web" in prompt
        assert "calculate" in prompt
        assert "Perform calculations" in prompt

    def test_format_tools_empty(self):
        """Test formatting tools when none available."""
        config = AgentConfig(name="test", role="assistant")
        agent = BaseAgent(config=config, tools=[])

        formatted = agent._format_tools()

        assert formatted == "No tools available."

    def test_format_tools_single(self):
        """Test formatting a single tool."""
        config = AgentConfig(name="test", role="assistant")
        agent = BaseAgent(config=config, tools=[])
        agent.add_tool({"name": "test_tool", "description": "A test tool"})

        formatted = agent._format_tools()

        assert "test_tool" in formatted
        assert "A test tool" in formatted

    def test_format_tools_multiple(self):
        """Test formatting multiple tools."""
        config = AgentConfig(name="test", role="assistant")
        tools = [
            {"name": "tool1", "description": "Description 1"},
            {"name": "tool2", "description": "Description 2"},
        ]
        agent = BaseAgent(config=config, tools=tools)

        formatted = agent._format_tools()

        assert "tool1" in formatted
        assert "tool2" in formatted
