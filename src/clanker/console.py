"""Interactive console for Clanker with streaming and context awareness."""

import asyncio
import sys
from io import StringIO
from typing import Dict, Any
from collections import deque
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from pydantic_ai.messages import ToolCallPart
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
        self.last_topic = None
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
            if self._is_continuation(request):
                # This is a continuation - add explicit context
                context_prompt = f"Continuing from our discussion about {self.last_topic}: {request}"
            
            # Add recent conversation summary for context
            recent_context = "\n[Previous context: "
            for exchange in list(self.history)[-2:]:  # Last 2 exchanges
                if exchange.get('tools'):
                    tools_used = ', '.join(t['name'] for t in exchange['tools'])
                    recent_context += f"User asked '{exchange['user'][:30]}...', you used tools: {tools_used}. "
                else:
                    recent_context += f"User asked '{exchange['user'][:30]}...'. "
            recent_context += "]\n"
            
            if len(self.history) > 0:
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

            # Update topic tracking
            self._update_topic(request)

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
    
    def _is_continuation(self, request: str) -> bool:
        """Check if request continues previous topic."""
        continuations = ['it', 'that', 'this', 'them', 'those', 'run it', 'do it', 'tell me more']
        lower = request.lower()
        return any(phrase in lower for phrase in continuations)
    
    def _update_topic(self, request: str):
        """Track what we're talking about."""
        lower = request.lower()
        if 'recipe' in lower:
            self.last_topic = 'recipes'
        elif 'weather' in lower:
            self.last_topic = 'weather'
        elif 'app' in lower:
            self.last_topic = 'apps'
        elif 'file' in lower or 'code' in lower:
            self.last_topic = 'code'
        elif 'bash' in lower or 'command' in lower:
            self.last_topic = 'commands'
    
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
        
        if self.last_topic:
            console.print(f"\n[dim]Current topic: {self.last_topic}[/dim]")
    
    def show_available_tools(self):
        """Display available tools."""
        console.print("\n[bold]Available Tools[/bold]")

        # Get tools from the second toolset (our FunctionToolset)
        if hasattr(self.agent, 'agent') and hasattr(self.agent.agent, 'toolsets') and len(self.agent.agent.toolsets) > 1:
            # toolsets[1] should be our FunctionToolset with the CLI export tools
            toolset = self.agent.agent.toolsets[1]
            if hasattr(toolset, 'tools') and toolset.tools:
                for tool_name, tool in toolset.tools.items():
                    console.print(f"  • [cyan]{tool_name}[/cyan]")
                    # Use the tool's description or function docstring for better info
                    description = getattr(tool, 'description', None) or getattr(tool.function, '__doc__', None)
                    if description and description != "A tool function for an agent.":
                        console.print(f"    [dim]{description}[/dim]")
            else:
                console.print("[dim]No tools configured[/dim]")
        else:
            console.print("[dim]No tools configured[/dim]")
    
    def show_help(self):
        """Display help information."""
        help_text = """
[bold]Clanker Interactive Console[/bold]

[cyan]Commands:[/cyan]
  context  - Show conversation history
  tools    - List available tools
  help     - Show this help message
  exit     - Exit the console
  
[cyan]Features:[/cyan]
  • Natural language queries
  • Streaming responses
  • Tool execution visibility
  • Context-aware conversations
  
[cyan]Examples:[/cyan]
  "What are my recipes?"
  "List all Python files"
  "Run the example app"
"""
        console.print(Panel(help_text, border_style="blue"))
    
    async def run(self):
        """Main console loop."""
        # Welcome message
        console.print(Panel.fit(
            "[bold cyan]Clanker Interactive Console[/bold cyan]\n"
            "Type 'help' for commands, 'exit' to quit",
            border_style="cyan"
        ))
        
        # Show initial tips
        console.print("[dim]Try: 'list my apps', 'what recipes do I have', 'help me with...'[/dim]\n")
        
        # Main loop
        while True:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold blue]You[/bold blue]")
                
                # Handle special commands
                if user_input.lower() in ['exit', 'quit', 'q']:
                    break
                
                if user_input.lower() == 'context':
                    self.show_context()
                    continue
                
                if user_input.lower() == 'tools':
                    self.show_available_tools()
                    continue
                
                if user_input.lower() == 'help':
                    self.show_help()
                    continue
                
                # Handle regular request
                response, tools_used = await self.handle_request(user_input)
                
                # Show context awareness indicator
                if self._is_continuation(user_input) and self.last_topic:
                    console.print(f"[dim](understood in context of {self.last_topic})[/dim]")
                
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