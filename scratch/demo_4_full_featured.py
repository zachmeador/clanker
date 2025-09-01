#!/usr/bin/env python3
"""
UX Pattern: Full Featured Chat with Streaming, Context, and Tool Visibility
- Combines streaming responses, context awareness, and tool call visibility
- Shows tool calls in real-time like Claude Code and other CLI tools
- Maintains conversation history
"""

import asyncio
import sys
from io import StringIO
from typing import List, Dict, Any, Optional
from collections import deque
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.live import Live
from rich.table import Table
from rich.text import Text
import json

from pydantic_ai import Agent, RunContext
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.messages import (
    ToolCallPart,
    ToolReturnPart,
    TextPart,
    SystemPromptPart,
    UserPromptPart
)

from clanker.models import ModelTier, create_agent
from clanker.tools import create_clanker_toolset
from clanker import apps
import subprocess

console = Console()

# Store original run function
_original_run = apps.run

# Monkey-patch the run function to capture subprocess output
def patched_run(app_name: str, args: list = None) -> int:
    """Patched version of apps.run that captures subprocess output"""
    # Get apps
    apps_dict = apps.discover()
    
    if app_name not in apps_dict:
        return 1
    
    app = apps_dict[app_name]
    if not app.get("entry"):
        return 1
    
    # Build command
    cmd = app["entry"]
    if args:
        cmd += " " + " ".join(args)
    
    # Clean environment
    import os
    env = os.environ.copy()
    env.pop('VIRTUAL_ENV', None)
    
    try:
        # Run with captured output instead of inheriting terminal
        result = subprocess.run(
            cmd, 
            shell=True, 
            env=env,
            capture_output=True,  # Capture stdout and stderr
            text=True
        )
        
        # Store the output in a global variable for later display
        global _last_tool_output
        _last_tool_output = result.stdout + result.stderr
        
        return result.returncode
    except Exception:
        return 1

# Apply the monkey-patch
apps.run = patched_run
_last_tool_output = ""


class StreamingContextAgent:
    """Agent with streaming, context awareness, and tool visibility"""
    
    def __init__(self, model_tier: ModelTier = ModelTier.LOW, context_window: int = 3):
        self.model_tier = model_tier
        self.history = deque(maxlen=context_window)
        self.last_topic = None
        self.setup_agent()
        
    def setup_agent(self):
        """Set up the pydantic-ai agent with tools"""
        system_prompt = """You are Clanker, a helpful AI assistant.
        You have access to tools for running apps and executing safe commands.
        Be direct and helpful."""
        
        # Get toolset
        toolset = create_clanker_toolset()
        
        # For now, skip wrapping - tools are complex objects
        # We'll rely on message parsing after execution
        
        # Create agent with toolset
        self.agent = create_agent(
            self.model_tier,
            system_prompt=system_prompt,
            toolsets=[toolset]
        )
    
    async def handle_with_streaming(self, request: str):
        """Handle request with streaming response and tool visibility"""
        
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
            
            # Reset the global tool output capture
            global _last_tool_output
            _last_tool_output = ""
            
            # Run the agent (tools will execute here with output captured by our patch)
            result = await self.agent.run(context_prompt)
            
            # Get the captured tool output
            tool_output = _last_tool_output
            
            # Clear the pending indicator
            console.print(" " * 20, end="\r")  # Clear the line
            
            # Parse and display tool calls with captured output
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
            except:
                pass  # Continue if we can't parse messages
            
            # Now show the captured tool output if any
            if tool_output and tool_output.strip():
                console.print("[dim green]← Tool output:[/dim green]")
                # Show first few lines of captured output
                output_lines = tool_output.strip().split('\n')[:3]
                for line in output_lines:
                    if line.strip():
                        console.print(f"[dim]   {line[:80]}{'...' if len(line) > 80 else ''}[/dim]")
                if len(tool_output.strip().split('\n')) > 3:
                    console.print("[dim]   ...[/dim]")
            
            # Now show the Clanker prompt
            console.print("[bold cyan]Clanker[/bold cyan]: ", end="")
            
            # Stream the response text  
            # Use the output attribute from RunResult (not data!)
            if hasattr(result, 'output'):
                response_text = result.output
            elif hasattr(result, 'data'):
                response_text = result.data
            else:
                # Try converting to string as last resort
                response_text = str(result)
            
            # Handle case where response might be None or empty
            if not response_text:
                response_text = "I processed your request but have no text response."
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
            return error_msg, []
    
    async def _stream_response(self, text: str, delay: float = 0.03):
        """Simulate streaming response word by word"""
        words = text.split()
        for i, word in enumerate(words):
            console.print(word, end=" ")
            if i % 7 == 6:  # Occasional longer pause
                await asyncio.sleep(delay * 3)
            else:
                await asyncio.sleep(delay)
        console.print()  # Final newline
    
    def _is_continuation(self, request: str) -> bool:
        """Check if request continues previous topic"""
        continuations = ['it', 'that', 'this', 'them', 'those', 'run it', 'do it', 'tell me more']
        lower = request.lower()
        return any(phrase in lower for phrase in continuations)
    
    def _update_topic(self, request: str):
        """Track what we're talking about"""
        lower = request.lower()
        if 'recipe' in lower:
            self.last_topic = 'recipes'
        elif 'weather' in lower:
            self.last_topic = 'weather'
        elif 'app' in lower:
            self.last_topic = 'apps'
        elif 'bash' in lower or 'command' in lower:
            self.last_topic = 'commands'
    
    def show_context(self):
        """Display current conversation context"""
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
        """Display available tools"""
        console.print("\n[bold]Available Tools[/bold]")
        
        # Get tools from agent's toolset
        if hasattr(self.agent, '_function_tools'):
            for tool_name, tool_def in self.agent._function_tools.items():
                console.print(f"  • [cyan]{tool_name}[/cyan]")
                if hasattr(tool_def, 'description'):
                    console.print(f"    [dim]{tool_def.description}[/dim]")
        else:
            console.print("[dim]No tools configured[/dim]")


async def main():
    """Main chat loop with full features"""
    
    # Welcome message
    console.print(Panel.fit(
        "[bold cyan]Full Featured Chat Demo[/bold cyan]\n"
        "Streaming + Context + Tool Visibility",
        border_style="cyan"
    ))
    
    # Initialize agent
    try:
        agent = StreamingContextAgent(
            model_tier=ModelTier.LOW,
            context_window=3
        )
        console.print("[green]✓[/green] Agent initialized\n")
    except Exception as e:
        console.print(f"[red]Failed to initialize:[/red] {e}")
        console.print("\n[yellow]Make sure API keys are configured in .env[/yellow]")
        return
    
    # Show instructions
    console.print("[dim]Features:[/dim]")
    console.print("[dim]  • Streaming responses (word by word)[/dim]")
    console.print("[dim]  • Context awareness (remembers last 3 exchanges)[/dim]")
    console.print("[dim]  • Tool call visibility (see what's happening)[/dim]")
    console.print("\n[dim]Commands:[/dim]")
    console.print("[dim]  • 'context' - Show conversation history[/dim]")
    console.print("[dim]  • 'tools' - List available tools[/dim]")
    console.print("[dim]  • 'exit' - End session[/dim]")
    console.print("\n[dim]Try: 'list my apps', 'tell me about recipes', 'run it'[/dim]")
    
    # Main chat loop
    while True:
        try:
            # Get user input
            user_input = Prompt.ask("\n[bold blue]You[/bold blue]")
            
            # Handle special commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                break
            
            if user_input.lower() == 'context':
                agent.show_context()
                continue
            
            if user_input.lower() == 'tools':
                agent.show_available_tools()
                continue
            
            # Handle request with streaming and tool visibility
            response, tools_used = await agent.handle_with_streaming(user_input)
            
            # Show context awareness indicator
            if agent._is_continuation(user_input) and agent.last_topic:
                console.print(f"[dim](understood in context of {agent.last_topic})[/dim]")
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    # Goodbye
    console.print("\n[dim]Session ended[/dim]")
    if agent.history:
        console.print(f"[dim]Total exchanges: {len(agent.history)}[/dim]")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())