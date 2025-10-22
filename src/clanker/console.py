"""Interactive console for Clanker with streaming and context awareness."""

import asyncio
import sys
from io import StringIO
from typing import Dict, Any
from collections import deque
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from .models import ModelTier
from .agent import ClankerAgent
from .logger import get_logger

logger = get_logger("console")
console = Console()


class InteractiveConsole:
    """Interactive console with streaming responses and tool visibility."""
    
    def __init__(self, model_tier: ModelTier = ModelTier.MEDIUM, context_window: int = 5):
        """Initialize the interactive console.
        
        Args:
            model_tier: The model tier to use for the agent
            context_window: Number of exchanges to keep in history
        """
        self.model_tier = model_tier
        self.history = deque(maxlen=context_window)
        self.agent = None
        self.setup_agent()
        
    def setup_agent(self):
        """Set up the clanker agent with tools."""
        # Create ClankerAgent with the specified model tier
        self.agent = ClankerAgent(self.model_tier)
        logger.info("Interactive console agent initialized")
    
    async def handle_request(self, request: str) -> tuple[str, list]:
        """Handle a user request with streaming response and tool visibility.
        
        Args:
            request: The user's request
            
        Returns:
            Tuple of (response_text, tool_calls)
        """
        # Build context-aware prompt
        context_prompt = request
        
        # Add conversation context if we have history
        if self.history:
            # Add recent conversation summary for context
            recent_context = "\n[Previous context: "
            for exchange in list(self.history)[-2:]:  # Last 2 exchanges
                if exchange.get('tools'):
                    tools_used = ', '.join(t['name'] for t in exchange['tools'])
                    recent_context += f"User asked '{exchange['user'][:30]}...', you used tools: {tools_used}. "
                else:
                    recent_context += f"User asked '{exchange['user'][:30]}...'. "
            recent_context += "]\n"
            context_prompt = recent_context + context_prompt
        
        try:
            # Show pending indicator
            console.print("\n[dim]Thinking...[/dim]", end="\r")

            # Run the agent (now returns structured result)
            result = await self.agent.handle_request_async(context_prompt)

            # Clear the pending indicator
            console.print(" " * 20, end="\r")  # Clear the line

            # Get data from structured result
            response_text = result['response']
            tool_calls = result['tool_calls']
            tool_output = result['tool_output']

            # Display tool calls and handle confirmations
            for tool in tool_calls:
                tool_name = tool['name']
                if tool.get('args') and isinstance(tool['args'], dict) and tool['args']:
                    args_str = ', '.join(f"{k}={v}" for k, v in tool['args'].items())
                    console.print(f"[dim yellow]→ Calling: {tool_name}({args_str})[/dim yellow]")
                else:
                    console.print(f"[dim yellow]→ Calling: {tool_name}[/dim yellow]")

                # Handle confirmation for launch_claude_code tool
                # Note: Confirmation is skipped since the process will be replaced anyway
                # The tool handles its own environment cleanup

            # Show tool output if any
            if tool_output and tool_output.strip():
                console.print("[dim green]← Tool output:[/dim green]")
                # Show first few lines of captured output
                output_lines = tool_output.strip().split('\n')[:3]
                for line in output_lines:
                    if line.strip():
                        console.print(f"[dim]   {line[:80]}{'...' if len(line) > 80 else ''}[/dim]")
                if len(tool_output.strip().split('\n')) > 3:
                    console.print("[dim]   ...[/dim]")

            # Display response with streaming effect
            if response_text and response_text.strip():
                console.print("[bold cyan]Clanker[/bold cyan]: ", end="")
                await self._stream_response(str(response_text))
            else:
                # No response to show
                pass

            # Update history
            self.history.append({
                "user": request,
                "assistant": response_text,
                "tools": tool_calls,
                "tool_output": tool_output.strip() if tool_output else None
            })


            return response_text, tool_calls
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            logger.error(f"Console request failed: {e}", exc_info=True)
            return error_msg, []

    async def _stream_response(self, text: str, delay: float = 0.02):
        """Simulate streaming response word by word.

        Args:
            text: The text to stream
            delay: Delay between words in seconds
        """
        words = text.split()
        for i, word in enumerate(words):
            console.print(word, end=" ")
            if i % 10 == 9:  # Occasional longer pause
                await asyncio.sleep(delay * 2)
            else:
                await asyncio.sleep(delay)
        console.print()  # Final newline
    
    
    def show_context(self):
        """Display current conversation context."""
        if not self.history:
            console.print("[dim]No conversation history yet[/dim]")
            return
            
        console.print("\n[bold]Conversation Context[/bold]")
        for i, exchange in enumerate(self.history, 1):
            console.print(f"\n[dim]Exchange {i}:[/dim]")
            console.print(f"  You: {exchange['user'][:60]}...")
            
            # Show tools if used
            if exchange.get('tools'):
                for tool in exchange['tools']:
                    tool_name = tool['name']
                    if tool.get('args') and isinstance(tool['args'], dict) and tool['args']:
                        args_preview = ', '.join(f"{k}={v}" for k, v in list(tool['args'].items())[:2])
                        console.print(f"  [dim yellow]→ {tool_name}({args_preview})[/dim yellow]")
                    else:
                        console.print(f"  [dim yellow]→ {tool_name}[/dim yellow]")
                # Show tool output preview if available
                if exchange.get('tool_output'):
                    first_line = exchange['tool_output'].split('\n')[0][:50]
                    console.print(f"  [dim green]← {first_line}...[/dim green]")
            
            # Show response preview
            response_preview = str(exchange['assistant'])[:60] if exchange['assistant'] else "No response"
            console.print(f"  Clanker: {response_preview}...")
        
    
    def show_available_tools(self):
        """Display available tools with parameter information."""
        console.print("\n[bold]Available Tools[/bold]")

        tools = self.agent.get_available_tools()
        if tools:
            for tool_name, info in tools.items():
                # Build parameter signature
                params_str = ""
                if info.get('parameters'):
                    param_parts = []
                    for param in info['parameters']:
                        param_str = f"{param['name']}: {param['type']}"
                        if not param['required']:
                            if 'default' in param:
                                param_str += f" = {param['default']}"
                            else:
                                param_str += " = ?"
                        param_parts.append(param_str)
                    params_str = f"({', '.join(param_parts)})"
                else:
                    params_str = "()"
                
                # Display tool with signature
                console.print(f"  • [cyan]{info['name']}{params_str}[/cyan]")
                
                # Show description
                if info.get('description'):
                    console.print(f"    [dim]{info['description']}[/dim]")
                
                # Show parameter details if they have descriptions
                if info.get('parameters'):
                    for param in info['parameters']:
                        if param.get('description'):
                            console.print(f"    [dim yellow]  {param['name']}:[/dim yellow] [dim]{param['description']}[/dim]")
        else:
            console.print("[dim]No tools configured[/dim]")
    
    def _get_available_commands(self):
        """Get all available slash commands."""
        commands = {}

        # Console commands
        commands.update({
            '/help': 'Show help information',
            '/context': 'Show conversation history',
            '/tools': 'List available tools',
            '/exit': 'Exit the console'
        })

        # App exports (simplified - just get command names)
        try:
            from . import apps as apps_module
            discovered = apps_module.discover()
            for app_name, app_info in discovered.items():
                if app_info.get('exports'):
                    for export_name in app_info['exports']:
                        commands[f'/{export_name}'] = f'Run {app_name} {export_name} command'
        except:
            pass

        # Core CLI commands (basic ones)
        commands.update({
            '/list-apps': 'List all available apps',
            '/app-info': 'Show app details',
            '/models': 'Show available AI models'
        })

        return commands

    def _show_command_suggestions(self, prefix="/"):
        """Show available commands that match the prefix."""
        commands = self._get_available_commands()
        matches = [(cmd, desc) for cmd, desc in commands.items() if cmd.startswith(prefix)]
        
        if matches:
            console.print("\n[dim]Available commands:[/dim]")
            for cmd, desc in sorted(matches)[:10]:  # Show max 10 suggestions
                console.print(f"  [cyan]{cmd}[/cyan] - [dim]{desc}[/dim]")
            if len(matches) > 10:
                console.print(f"  [dim]... and {len(matches) - 10} more[/dim]")
            console.print()  # Empty line for spacing

    def _get_user_input_with_completion(self):
        """Get user input with Rich formatting and readline completion."""
        try:
            import readline

            # Set up autocomplete before prompting
            commands = list(self._get_available_commands().keys())
            def completer(text, state):
                if text.startswith('/'):
                    matches = [cmd for cmd in commands if cmd.startswith(text)]
                    return matches[state] if state < len(matches) else None
                return None

            readline.set_completer(completer)
            readline.parse_and_bind("tab: complete")

            # Use Rich prompt for proper formatting
            return Prompt.ask("\n[bold blue]You[/bold blue]").strip()

        except ImportError:
            # Fallback to basic input if readline not available
            return input("\nYou: ").strip()

    async def _handle_slash_command(self, command):
        """Handle slash command execution."""
        commands = self._get_available_commands()

        if command not in commands:
            # Try fuzzy matching or suggestion
            similar = [cmd for cmd in commands.keys() if cmd.split(':')[0] == command.split(':')[0]]
            if similar:
                console.print(f"[red]Unknown command: {command}[/red]")
                console.print(f"[dim]Did you mean one of: {', '.join(similar)}[/dim]")
            else:
                console.print(f"[red]Unknown command: {command}[/red]")
                console.print(f"[dim]Type /help for available commands[/dim]")
            return

        # Route to appropriate handler
        if command == '/help':
            self.show_help()
        elif command == '/context':
            self.show_context()
        elif command == '/tools':
            self.show_available_tools()
        elif command == '/exit':
            raise KeyboardInterrupt  # Exit the loop
        elif command.startswith('/list-apps') or command == '/list-apps':
            from . import apps as apps_module
            apps_module.list_apps()
        elif command.startswith('/models') or command == '/models':
            from .models import list_available_providers, list_available_models
            providers = list_available_providers()
            if providers:
                console.print(f"Configured providers: {', '.join(providers)}")
                available = list_available_models()
                if available:
                    console.print("Available models:")
                    for provider, models in available.items():
                        console.print(f"  {provider}: {', '.join(models)}")
            else:
                console.print("No API keys configured")
        elif ':' in command:
            # Handle app commands like /example:add
            app_cmd = command[1:]  # Remove the /
            await self._execute_app_command(app_cmd)
        else:
            console.print(f"[red]Command not implemented yet: {command}[/red]")

    async def _execute_app_command(self, app_cmd):
        """Execute app command via subprocess."""
        try:
            # Parse command (e.g., "example:add" -> app="example", cmd="add")
            if ':' in app_cmd:
                app_name, cmd_name = app_cmd.split(':', 1)
            else:
                app_name, cmd_name = app_cmd.split('_', 1) if '_' in app_cmd else (app_cmd, '')

            # Find the app and execute
            from . import apps as apps_module
            discovered = apps_module.discover()
            app_info = discovered.get(app_name)

            if not app_info:
                console.print(f"[red]App not found: {app_name}[/red]")
                return

            # For now, just show that the command was recognized
            # In a full implementation, you'd parse arguments and execute via subprocess
            console.print(f"[green]Would execute: {app_name} {cmd_name}[/green]")
            console.print(f"[dim]Note: Full argument parsing and execution not yet implemented[/dim]")

        except Exception as e:
            console.print(f"[red]Error executing command: {e}[/red]")

    def show_help(self):
        """Display help information."""
        help_text = """
[bold]Clanker Interactive Console[/bold]

[cyan]Slash Commands:[/cyan]
  /help        - Show this help message
  /context     - Show conversation history
  /tools       - List available tools
  /exit        - Exit the console
  /list-apps   - List all available apps
  /models      - Show available AI models
  /example:*   - Example app commands (add, list, search, etc.)

[cyan]Examples:[/cyan]
  "What are my recipes?"
  "/list-apps"
  "/example:add 'Today was great!'"
"""
        console.print(Panel(help_text, border_style="blue"))
    
    def _is_interactive(self) -> bool:
        """Check if we're in an interactive environment."""
        # Check if stdin is a tty (real terminal)
        if not sys.stdin.isatty():
            return False
        
        # Check if we can actually read from stdin
        try:
            # Test if stdin is readable without blocking
            import select
            ready, _, _ = select.select([sys.stdin], [], [], 0)
            # If stdin is immediately ready, it might be redirected/closed
            if ready:
                # Try to peek at stdin
                try:
                    sys.stdin.peek(1)  # This will fail if stdin is not buffered properly
                except (OSError, AttributeError):
                    return False
        except (ImportError, OSError):
            # select not available on all platforms, fall back to basic checks
            pass
        
        # Additional check: see if we can create a prompt
        try:
            # This is a more direct test - just check if rich.prompt would work
            from rich.prompt import Prompt
            # Don't actually prompt, just check if the console is compatible
            return console.is_terminal and not console.legacy_windows
        except:
            return False
    
    async def run(self):
        """Main console loop."""
        # Check if we're in an interactive environment
        if not self._is_interactive():
            console.print("[red]Error: Interactive console requires a terminal with stdin[/red]")
            console.print("[dim]Hint: Use 'clanker \"your request\"' for one-shot commands[/dim]")
            return
        
        # Welcome message with config status
        try:
            from .onboarding import get_config_status
            config = get_config_status()

            # Build status line
            status_parts = []
            if config['providers']:
                status_parts.append(f"Providers: {', '.join(config['providers'])}")
            if config['tools']:
                status_parts.append(f"Tools: {', '.join(config['tools'])}")

            status_line = " | ".join(status_parts) if status_parts else "No providers configured"

            welcome_text = f"[bold cyan]Clanker Interactive Console[/bold cyan]\n{status_line}\n\nType '/help' for commands"
        except Exception:
            # Fallback to simple welcome if config check fails
            welcome_text = "[bold cyan]Clanker Interactive Console[/bold cyan]\nType '/help' for commands"

        console.print(Panel.fit(welcome_text, border_style="cyan"))

        # Show initial tips
        console.print("[dim]Try: 'list my apps', 'what recipes do I have', 'help me with...'[/dim]")
        console.print("[dim]Tip: Type '/' to see available commands[/dim]\n")
        
        # Main loop
        while True:
            try:
                # Get user input with Rich formatting and readline completion
                user_input = self._get_user_input_with_completion()

                # Handle empty input
                if not user_input:
                    continue

                # Handle slash commands
                if user_input.startswith('/'):
                    # Special case: if user just types "/" show all commands
                    if user_input == '/':
                        self._show_command_suggestions()
                        continue
                    
                    await self._handle_slash_command(user_input)
                    continue

                # Handle regular request (natural language)
                response, tools_used = await self.handle_request(user_input)
                
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                logger.error(f"Console error: {e}", exc_info=True)
        
        # Goodbye
        console.print("\n[dim]Session ended[/dim]")
        if self.history:
            console.print(f"[dim]Total exchanges: {len(self.history)}[/dim]")