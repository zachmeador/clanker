"""Clanker agent with natural language processing capabilities."""

from typing import List, Dict, Any, Optional
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessagesTypeAdapter

from .models import create_agent as create_pydantic_agent, ModelTier
from .tools import create_clanker_toolset
from .logger import get_logger
from .context import CoreContextManager

logger = get_logger("agent")


class ClankerAgent:
    """Main clanker agent that handles natural language requests."""

    def __init__(self, model_tier: ModelTier = ModelTier.MEDIUM):
        """Initialize the clanker agent.

        Args:
            model_tier: The model tier to use for the agent
        """
        self.model_tier = model_tier
        self.message_history = []  # Pydantic-ai message history for persistence
        self.context_manager = CoreContextManager()  # Context for responses

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
        clanker_overview = self.context_manager.get_snippet("clanker_overview")
        available_apps = self.context_manager._get_available_apps_context()
        cli_patterns = self.context_manager.get_snippet("cli_patterns")
        export_system = self.context_manager.get_snippet("export_system")

        return f"""{clanker_overview}

Your capabilities:
- Run clanker apps using available tools
- Help with development tasks
- Provide contextual information about the system

{available_apps}

{cli_patterns}

{export_system}

CRITICAL INSTRUCTIONS:
- When users ask to run, launch, execute, or use any app, use the specific app tool
- Do NOT respond conversationally when a tool should be used
- Available tools are provided automatically

Guidelines:
- Be helpful and direct
- Use tools for app-related requests
- Explain what you're doing after using tools
- Use the context information above to provide accurate responses"""

    def handle_request(self, request: str) -> dict:
        """Handle a natural language request.

        Args:
            request: The user's natural language request

        Returns:
            Dict with keys: 'response', 'tool_calls', 'tool_output'
        """
        logger.info(f"Processing request: '{request}'")

        # Special handling for launch requests - these replace the process
        if self._is_launch_request(request):
            self._handle_launch_request(request)
            # If we get here, the launch failed - continue with normal processing
            pass

        try:
            logger.debug("Calling agent.run_sync() with message history")
            # Run the agent with conversation history
            result = self.agent.run_sync(request, message_history=self.message_history)

            # Update message history for future conversations
            self.message_history = result.new_messages()

            # Extract tool call information for console display
            tool_calls = []
            tool_output = ""

            # Parse tool calls from the result messages
            for msg in result.new_messages():
                if hasattr(msg, 'parts'):
                    for part in msg.parts:
                        if hasattr(part, 'tool_name') and hasattr(part, 'args'):
                            # This is a tool call
                            tool_calls.append({
                                'name': part.tool_name,
                                'args': part.args
                            })
                            # For CLI export tools, we can capture output here
                            # (In a more complete implementation, we'd capture tool stdout)
                            if hasattr(part, 'tool_name') and 'example_' in part.tool_name:
                                # This would be where we capture actual tool output
                                # For now, we'll leave tool_output empty as the agent handles it
                                pass

            response_text = result.output if hasattr(result, 'output') else str(result)
            if not response_text:
                response_text = "I processed your request but have no text response."

            logger.debug(f"Agent returned result with output length: {len(response_text)}")
            logger.info(f"Request completed successfully")

            return {
                'response': response_text,
                'tool_calls': tool_calls,
                'tool_output': tool_output
            }

        except Exception as e:
            logger.error(f"Agent request failed: {str(e)}", exc_info=True)
            return {
                'response': f"I encountered an error: {str(e)}",
                'tool_calls': [],
                'tool_output': ""
            }

    async def handle_request_async(self, request: str) -> dict:
        """Handle a natural language request asynchronously.

        Args:
            request: The user's natural language request

        Returns:
            Dict with keys: 'response', 'tool_calls', 'tool_output'
        """
        logger.info(f"Processing async request: '{request}'")

        try:
            logger.debug("Calling agent.run() with message history")
            # Run the agent with conversation history
            result = await self.agent.run(request, message_history=self.message_history)

            # Update message history for future conversations
            self.message_history = result.new_messages()

            # Extract tool call information for console display
            tool_calls = []
            tool_output = ""

            # Parse tool calls from the result messages
            for msg in result.new_messages():
                if hasattr(msg, 'parts'):
                    for part in msg.parts:
                        if hasattr(part, 'tool_name') and hasattr(part, 'args'):
                            # This is a tool call
                            tool_calls.append({
                                'name': part.tool_name,
                                'args': part.args
                            })

            response_text = result.output if hasattr(result, 'output') else str(result)
            if not response_text:
                response_text = "I processed your request but have no text response."

            logger.debug(f"Agent returned result")
            logger.info(f"Async request completed successfully")

            return {
                'response': response_text,
                'tool_calls': tool_calls,
                'tool_output': tool_output
            }

        except Exception as e:
            logger.error(f"Async agent request failed: {str(e)}", exc_info=True)
            return {
                'response': f"I encountered an error: {str(e)}",
                'tool_calls': [],
                'tool_output': ""
            }

    def get_available_tools(self) -> Dict[str, str]:
        """Get information about available tools."""
        # Get tools from the agent's toolsets
        available_tools = {}
        if hasattr(self.agent, 'toolsets'):
            for toolset in self.agent.toolsets:
                for tool_name, tool_obj in toolset.tools.items():
                    available_tools[tool_name] = tool_obj.description or f"Tool: {tool_name}"
        return available_tools

    def _is_launch_request(self, request: str) -> bool:
        """Check if request is asking to launch Claude Code."""
        request_lower = request.lower()
        launch_keywords = ['launch', 'start', 'open', 'run']
        claude_keywords = ['claude', 'claude code', 'claude-code']

        has_launch = any(word in request_lower for word in launch_keywords)
        has_claude = any(word in request_lower for word in claude_keywords)

        return has_launch and has_claude

    def _handle_launch_request(self, request: str) -> None:
        """Handle launch requests by calling the tool directly."""
        logger.info(f"Detected launch request: '{request}'")

        try:
            # Extract query from request (everything after launch/start keywords)
            query = self._extract_launch_query(request)

            # Execute launch tool directly (this will replace the process if successful)
            from .tools import launch_claude_code
            launch_claude_code(None, query)  # ctx can be None for direct call

            # If we get here, the launch failed - log and continue
            logger.warning("Launch tool returned without replacing process")

        except Exception as e:
            logger.error(f"Launch request handling failed: {e}")
            # Continue with normal processing on failure

    def _extract_launch_query(self, request: str) -> str:
        """Extract the query part from a launch request."""
        # Remove launch keywords and extract the rest as query
        query = request.lower()
        query = query.replace('launch', '').replace('start', '').replace('open', '').replace('run', '')
        query = query.replace('claude', '').replace('claude code', '').replace('claude-code', '')
        query = query.strip()

        # If query is empty, use a default
        if not query:
            query = "general development work"

        return query

    def save_conversation(self, filepath: str) -> None:
        """Save current conversation history to file."""
        try:
            import json
            from pydantic_core import to_jsonable_python

            json_data = to_jsonable_python(self.message_history)
            with open(filepath, 'w') as f:
                json.dump(json_data, f, indent=2)
            logger.info(f"Conversation saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")

    def load_conversation(self, filepath: str) -> None:
        """Load conversation history from file."""
        try:
            import json

            with open(filepath, 'r') as f:
                json_data = json.load(f)

            self.message_history = ModelMessagesTypeAdapter.validate_python(json_data)
            logger.info(f"Conversation loaded from {filepath}")
        except FileNotFoundError:
            logger.info(f"No conversation file found at {filepath}")
        except Exception as e:
            logger.error(f"Failed to load conversation: {e}")

    def clear_conversation(self) -> None:
        """Clear the conversation history."""
        self.message_history = []
        logger.info("Conversation history cleared")
