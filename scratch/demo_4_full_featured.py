#!/usr/bin/env python3
"""
UX Pattern: Full Featured Chat with Streaming, Context, and Tool Visibility
- Combines streaming responses, context awareness, and tool call visibility
- Shows tool calls in real-time like Claude Code and other CLI tools
- Maintains conversation history
"""

import asyncio
import time
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

console = Console()


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
        
        # Create agent with toolset
        self.agent = create_agent(
            self.model_tier,
            system_prompt=system_prompt,
            toolsets=[toolset]
        )
    
    async def handle_with_streaming(self, request: str):
        """Handle request with streaming response and tool visibility"""
        
        # Build context-aware prompt if we have history
        if self.history and self._is_continuation(request):
            context_prompt = f"Continuing from our discussion about {self.last_topic}: {request}"
        else:
            context_prompt = request
        
        # Track what's happening
        tool_calls = []
        response_text = ""
        
        try:
            # Show pending indicator
            console.print("\n[dim]Thinking...[/dim]", end="\r")
            
            # Run the agent asynchronously
            result = await self.agent.run(context_prompt)
            
            # Clear the pending indicator and show Clanker prompt
            console.print(" " * 20, end="\r")  # Clear the line
            console.print("[bold cyan]Clanker[/bold cyan]: ", end="")
            
            # Check if there were tool calls in the result
            # This is a simplified version - real implementation would parse messages
            if hasattr(result, '_messages'):
                for msg in result._messages:
                    if hasattr(msg, 'parts'):
                        for part in msg.parts:
                            if isinstance(part, ToolCallPart):
                                # Show tool being called
                                console.print(f"\n[dim yellow]→ Calling tool: {part.tool_name}[/dim yellow]")
                                if part.args:
                                    args_str = json.dumps(part.args, indent=2)
                                    console.print(f"[dim]  Args: {args_str}[/dim]")
                                tool_calls.append({
                                    'name': part.tool_name,
                                    'args': part.args
                                })
                            elif isinstance(part, ToolReturnPart):
                                # Show tool result
                                console.print(f"[dim green]← Tool result received[/dim green]")
                                if hasattr(part, 'content') and part.content:
                                    console.print(f"[dim]  {str(part.content)[:100]}...[/dim]")
            
            # Stream the response text  
            # The agent returns a RunResult with data attribute
            if hasattr(result, 'data'):
                response_text = result.data
            elif hasattr(result, 'output'):
                response_text = result.output
            else:
                response_text = str(result)
            
            # Handle case where response might be None
            if response_text is None:
                response_text = "I processed your request but have no text response."
            await self._stream_response(str(response_text))
            
            # Update history
            self.history.append({
                "user": request,
                "assistant": response_text,
                "tools": tool_calls
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
            console.print(f"  Clanker: {exchange['assistant'][:60]}...")
            if exchange.get('tools'):
                console.print(f"  [dim yellow]Tools used: {', '.join(t['name'] for t in exchange['tools'])}[/dim yellow]")
        
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