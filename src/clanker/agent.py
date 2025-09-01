"""Clanker agent with natural language processing capabilities."""

from typing import List, Dict, Any, Optional
from pydantic_ai import Agent
from .models import create_agent as create_pydantic_agent, ModelTier
from .tools import create_clanker_toolset
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
        self.input_resolver = InputResolver()

        # Initialize the pydantic-ai agent with toolsets
        self._setup_agent()

    def _setup_agent(self) -> None:
        """Set up the pydantic-ai agent with system prompt and toolsets."""
        system_prompt = self._get_system_prompt()

        # Create toolset with all core tools
        toolset = create_clanker_toolset()
        logger.info("Created clanker toolset with core tools")

        self.agent = create_pydantic_agent(
            self.model_tier,
            system_prompt=system_prompt,
            toolsets=[toolset]
        )
        logger.info("Agent created successfully with toolsets")

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        available_apps = self.input_resolver.get_available_apps()

        return f"""You are Clanker, an AI-powered development environment.

Your capabilities:
- Run clanker apps: {', '.join(available_apps) if available_apps else 'No apps available'}
- Help with development tasks using available apps

CRITICAL INSTRUCTIONS:
- When users ask to run, launch, execute, or use any app, use the specific app tool (e.g., run_recipes, run_resumes)
- Do NOT respond conversationally when a tool should be used
- Available apps: {', '.join(available_apps) if available_apps else 'none'}

Guidelines:
- Be helpful and direct
- Use app-specific tools for app-related requests
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
    
    async def handle_request_async(self, request: str, context: Optional[List[Dict[str, Any]]] = None) -> Any:
        """Handle a natural language request asynchronously.

        Args:
            request: The user's natural language request
            context: Optional conversation context

        Returns:
            The agent's result object (with output, messages, etc.)
        """
        logger.info(f"Processing async request: '{request}'")

        try:
            # Build context-aware prompt if context provided
            prompt = request
            if context:
                # Add recent context to prompt
                context_str = "Previous context: "
                for exchange in context[-2:]:  # Last 2 exchanges
                    context_str += f"User: {exchange.get('user', '')[:50]}... "
                prompt = f"{context_str}\n{request}"
            
            logger.debug("Calling agent.run()")
            # Run the agent asynchronously
            result = await self.agent.run(prompt)
            logger.debug(f"Agent returned result")
            logger.info(f"Async request completed successfully")

            return result

        except Exception as e:
            logger.error(f"Async agent request failed: {str(e)}", exc_info=True)
            raise

    def get_available_tools(self) -> Dict[str, str]:
        """Get information about available tools."""
        # Get tools from the agent's toolsets
        available_tools = {}
        if hasattr(self.agent, 'toolsets'):
            for toolset in self.agent.toolsets:
                for tool_name, tool_obj in toolset.tools.items():
                    available_tools[tool_name] = tool_obj.description or f"Tool: {tool_name}"
        return available_tools
