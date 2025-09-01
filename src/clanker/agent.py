"""Clanker agent with natural language processing capabilities."""

import asyncio
from typing import List, Dict, Any, Optional
from pydantic_ai import Agent
from .models import create_agent as create_pydantic_agent, ModelTier
from .tools import ToolRegistry, AppTool, BashTool, LLMDevTool
from .apps import discover
from .input_resolution import InputResolver
from .logger import get_logger

logger = get_logger("agent")


class ClankerAgent:
    """Main clanker agent that handles natural language requests."""

    def __init__(self, model_tier: ModelTier = ModelTier.MEDIUM):
        """Initialize the clanker agent.

        Args:
            model_tier: The model tier to use for the agent
        """
        self.model_tier = model_tier
        self.tool_registry = ToolRegistry()
        self.input_resolver = InputResolver()

        # Register core tools first
        self._register_core_tools()

        # Initialize the pydantic-ai agent
        self._setup_agent()

    def _setup_agent(self) -> None:
        """Set up the pydantic-ai agent with system prompt."""
        system_prompt = self._get_system_prompt()

        # Get all available tools
        tools = self.tool_registry.get_available_tools()
        logger.info(f"Registering {len(tools)} tools with agent")
        for i, tool in enumerate(tools):
            logger.debug(f"Tool {i}: {getattr(tool, 'name', 'unnamed')}")

        self.agent = create_pydantic_agent(
            self.model_tier,
            system_prompt=system_prompt,
            tools=tools
        )
        logger.info("Agent created successfully with tools")

    def _register_core_tools(self) -> None:
        """Register core tools with the registry."""
        logger.info("Starting tool registration")

        # Register generic app tool
        app_tool = AppTool()
        self.tool_registry.register(app_tool)
        logger.info(f"Registered generic AppTool: {app_tool.name}")



        # Register specific app tools for better UX
        discovered_apps = discover()
        logger.info(f"Discovered {len(discovered_apps)} apps")
        for app_name, app_info in discovered_apps.items():
            specific_tool = AppTool(app_info)
            self.tool_registry.register(specific_tool)
            logger.info(f"Registered specific AppTool for: {app_name}")

        logger.info(f"Total tools registered: {len(self.tool_registry.get_available_tools())}")

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        available_apps = self.input_resolver.get_available_apps()

        return f"""You are Clanker, an AI-powered development environment.

Your capabilities:
- Run clanker apps: {', '.join(available_apps) if available_apps else 'No apps available'}
- Help with development tasks using available apps

CRITICAL INSTRUCTIONS:
- When users ask to run, launch, execute, or use any app, ALWAYS use the run_app tool
- Do NOT respond conversationally when a tool should be used
- If you need to run an app, call the run_app tool with the appropriate app_name and args
- Available apps: {', '.join(available_apps) if available_apps else 'none'}

Guidelines:
- Be helpful and direct
- Use the run_app tool for any app-related requests
- Always explain what you're doing after using tools

Available tools will be provided automatically based on context."""

    def handle_request(self, request: str) -> str:
        """Handle a natural language request.

        Args:
            request: The user's natural language request

        Returns:
            The agent's response
        """
        logger.info(f"Processing request: '{request}'")
        logger.debug(f"Available tools: {list(self.tool_registry.get_tool_info().keys())}")

        try:
            logger.debug("Calling agent.run_sync()")
            # Run the agent synchronously (following pydantic-ai patterns)
            result = self.agent.run_sync(request)
            logger.debug(f"Agent returned result with output length: {len(result.output)}")
            logger.info(f"Request completed successfully")

            return result.output

        except Exception as e:
            logger.error(f"Agent request failed: {str(e)}", exc_info=True)
            return f"I encountered an error: {str(e)}"

    def get_available_tools(self) -> Dict[str, str]:
        """Get information about available tools."""
        return self.tool_registry.get_tool_info()
