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
from .models import ModelTier, create_agent
from .tools import create_clanker_toolset
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
        """Set up the pydantic-ai agent with tools."""
        system_prompt = """You are Clanker, an AI-powered development environment assistant.
        You have access to tools for running apps and helping with development tasks.
        Be direct, helpful, and concise."""
        
        # Get toolset
        toolset = create_clanker_toolset()
        
        # Create agent with toolset
        self.agent = create_agent(
            self.model_tier,
            system_prompt=system_prompt,
            toolsets=[toolset]
        )
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
        
        # Track what's happening
        tool_calls = []
        response_text = ""
        tool_output = ""
        
        try:
            # Show pending indicator
            console.print("\n[dim]Thinking...[/dim]", end="\r")
            
            # Capture stdout/stderr during agent.run() to control tool output
            captured_stdout = StringIO()
            captured_stderr = StringIO()
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = captured_stdout
            sys.stderr = captured_stderr
            
            try:
                # Run the agent (tools will execute here with output captured)
                result = await self.agent.run(context_prompt)
            finally:
                # Restore stdout and stderr
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                tool_output = captured_stdout.getvalue() + captured_stderr.getvalue()
            
            # Clear the pending indicator
            console.print(" " * 20, end="\r")  # Clear the line
            
            # Parse and display tool calls
            try:
                messages_to_parse = result.new_messages()
                for msg in messages_to_parse:
                    if hasattr(msg, 'parts'):
                        for part in msg.parts:
                            if isinstance(part, ToolCallPart):
                                # Show tool that was called
                                console.print(f"[dim yellow]→ Calling: {part.tool_name}[/dim yellow]", end="")
                                if part.args:
                                    if isinstance(part.args, dict) and part.args:
                                        args_str = ', '.join(f"{k}={v}" for k, v in part.args.items())
                                        console.print(f"[dim yellow]({args_str})[/dim yellow]")
                                    else:
                                        console.print()
                                else:
                                    console.print()
                                
                                tool_calls.append({
                                    'name': part.tool_name,
                                    'args': part.args
                                })
            except Exception as e:
                logger.debug(f"Could not parse tool calls: {e}")
            
            # Show captured tool output if any
            if tool_output and tool_output.strip():
                console.print("[dim green]← Tool output:[/dim green]")
                # Show first few lines of captured output
                output_lines = tool_output.strip().split('\n')[:3]
                for line in output_lines:
                    if line.strip():
                        console.print(f"[dim]   {line[:80]}{'...' if len(line) > 80 else ''}[/dim]")
                if len(tool_output.strip().split('\n')) > 3:
                    console.print("[dim]   ...[/dim]")
            
            # Get the response text
            if hasattr(result, 'output'):
                response_text = result.output
            elif hasattr(result, 'data'):
                response_text = result.data
            else:
                response_text = str(result)
            
            # Handle case where response might be None or empty
            if not response_text:
                response_text = "I processed your request but have no text response."
            
            # Display response with streaming effect
            console.print("[bold cyan]Clanker[/bold cyan]: ", end="")
            await self._stream_response(str(response_text))
            
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
                    console.print(f"  [dim yellow]→ {tool['name']}", end="")
                    if tool.get('args'):
                        # Show condensed args
                        if isinstance(tool['args'], dict) and tool['args']:
                            args_preview = ', '.join(f"{k}={v}" for k, v in list(tool['args'].items())[:2])
                            console.print(f"({args_preview})[/dim yellow]")
                        else:
                            console.print("[/dim yellow]")
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
        
        # Get tools from agent's toolset
        if hasattr(self.agent, '_function_tools'):
            for tool_name, tool_def in self.agent._function_tools.items():
                console.print(f"  • [cyan]{tool_name}[/cyan]")
                if hasattr(tool_def, 'description'):
                    console.print(f"    [dim]{tool_def.description}[/dim]")
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