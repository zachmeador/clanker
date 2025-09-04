"""Clanker agent with natural language processing capabilities."""

from typing import List, Dict, Any, Optional
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessagesTypeAdapter

from .models import create_agent as create_pydantic_agent, ModelTier
from .tools import create_clanker_toolset
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
        self.message_history = []  # Pydantic-ai message history for persistence

        # Initialize the pydantic-ai agent with toolsets
        self._setup_agent()

    def _setup_agent(self) -> None:
        """Set up the pydantic-ai agent with system prompt and toolsets."""
        # Ensure database schema is initialized before creating tools
        from .storage.schema import ensure_database_initialized
        ensure_database_initialized()
        logger.debug("Database schema initialized")
        
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
        from .context import ContextBuilder, ContextStore, get_available_apps_context
        
        store = ContextStore()
        clanker_overview = store.get("clanker_overview") or ""
        available_apps = get_available_apps_context()
        cli_patterns = store.get("cli_patterns") or ""
        export_system = store.get("export_system") or ""
        personality = store.get("personality") or ""

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
- Use the context information above to provide accurate responses

{personality}"""

    def handle_request(self, request: str) -> dict:
        """Handle a natural language request.

        Args:
            request: The user's natural language request

        Returns:
            Dict with keys: 'response', 'tool_calls', 'tool_output'
        """
        logger.info(f"Processing request: '{request}'")

        try:
            logger.debug("Calling agent.run_sync() with message history")
            # Run the agent with conversation history
            result = self.agent.run_sync(request, message_history=self.message_history)
            return self._process_result(result)

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
            return self._process_result(result)

        except Exception as e:
            logger.error(f"Async agent request failed: {str(e)}", exc_info=True)
            return {
                'response': f"I encountered an error: {str(e)}",
                'tool_calls': [],
                'tool_output': ""
            }

    def _process_result(self, result) -> dict:
        """Process agent result into standard response format.
        
        Args:
            result: Pydantic AI result object
            
        Returns:
            Dict with keys: 'response', 'tool_calls', 'tool_output'
        """
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
                        tool_calls.append({
                            'name': part.tool_name,
                            'args': part.args
                        })

        response_text = result.output if hasattr(result, 'output') else str(result)
        if not response_text:
            response_text = "I processed your request but have no text response."

        logger.info(f"Request completed successfully")

        return {
            'response': response_text,
            'tool_calls': tool_calls,
            'tool_output': tool_output
        }

    def get_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get information about available tools with display metadata and parameter info."""
        from .tools import get_tool_display_info
        import json
        
        available_tools = {}
        if hasattr(self.agent, 'toolsets'):
            for toolset in self.agent.toolsets:
                if hasattr(toolset, 'tools') and toolset.tools:
                    for tool_name, tool_obj in toolset.tools.items():
                        # Get basic display info
                        tool_info = get_tool_display_info(tool_name)
                        
                        # Extract parameter information from the tool object
                        parameters = []
                        if hasattr(tool_obj, 'parameters_json_schema') and tool_obj.parameters_json_schema:
                            try:
                                schema = tool_obj.parameters_json_schema
                                if isinstance(schema, dict) and 'properties' in schema:
                                    required = schema.get('required', [])
                                    for param_name, param_info in schema['properties'].items():
                                        param_type = param_info.get('type', 'any')
                                        # Convert JSON schema types to Python types
                                        type_map = {
                                            'string': 'str',
                                            'integer': 'int', 
                                            'number': 'float',
                                            'boolean': 'bool',
                                            'array': 'list',
                                            'object': 'dict'
                                        }
                                        python_type = type_map.get(param_type, param_type)
                                        
                                        param_info_dict = {
                                            'name': param_name,
                                            'type': python_type,
                                            'required': param_name in required,
                                            'description': param_info.get('description', '')
                                        }
                                        
                                        # Add default value if available
                                        if 'default' in param_info:
                                            param_info_dict['default'] = param_info['default']
                                        
                                        parameters.append(param_info_dict)
                            except Exception as e:
                                logger.debug(f"Failed to parse parameters for {tool_name}: {e}")
                        
                        tool_info['parameters'] = parameters
                        available_tools[tool_name] = tool_info
        
        return available_tools


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
