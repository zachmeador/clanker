#!/usr/bin/env python3
"""
Marvin Demo - Now using Clanker's unified model system with Pydantic AI
"""

import os
from pydantic import BaseModel
from typing import List, Optional, Literal
from enum import Enum

# Import Clanker's model system instead of Marvin
from clanker.models import create_agent, ModelTier


def demo_1_intelligent_routing():
    """
    Demo 1: Intelligent Task Routing
    
    Shows how Clanker could use marvin.run() to intelligently route
    user requests to different actions or apps.
    """
    print("\n" + "="*60)
    print("DEMO 1: INTELLIGENT TASK ROUTING")
    print("="*60 + "\n")
    
    class ActionType(Enum):
        BUILD_APP = "build_app"
        RUN_APP = "run_app"
        CHAT = "chat"
        SYSTEM_CMD = "system_cmd"
        UNCLEAR = "unclear"
    
    class TaskRoute(BaseModel):
        action: ActionType
        confidence: float  # 0.0 to 1.0
        app_name: Optional[str] = None
        reasoning: str
        suggested_command: Optional[str] = None
    
    test_queries = [
        "I want to build a todo app with deadlines and categories",
        "show me my recipes",
        "ls -la",
        "what's the weather like?",
        "run the resume builder with my latest CV",
        "create a new app for tracking my reading list",
        "python manage.py runserver",
        "tell me a joke"
    ]
    
    print("Testing query routing with marvin.run():\n")
    
    for query in test_queries:
        print(f"Query: '{query}'")
        
        # Use Clanker's model system for intelligent routing
        agent = create_agent(ModelTier.LOW)  # Fast model for routing
        
        route = agent.run_sync(
            f"""Analyze this user query and determine the best action:
            Query: {query}
            
            Available actions:
            - build_app: User wants to create a new application
            - run_app: User wants to execute an existing app (recipes, resumes, etc.)
            - chat: General conversation or questions
            - system_cmd: Direct system/shell command
            - unclear: Cannot determine intent
            
            Consider existing apps: recipes, resumes
            """,
            result_type=TaskRoute
        )
        
        print(f"  → Action: {route.action.value} (confidence: {route.confidence:.1%})")
        print(f"    Reasoning: {route.reasoning}")
        if route.suggested_command:
            print(f"    Suggested: {route.suggested_command}")
        print()


def demo_2_agent_collaboration():
    """
    Demo 2: Agent Collaboration
    
    Shows how specialized agents can work together to handle
    complex tasks, with one agent analyzing and another implementing.
    """
    print("\n" + "="*60)
    print("DEMO 2: AGENT COLLABORATION")
    print("="*60 + "\n")
    
    # Create specialized agents using Clanker's model system
    architect = create_agent(
        ModelTier.MEDIUM,  # Good balance for planning
        system_prompt="""You are an experienced system architect.
        You analyze requirements and create clear, practical designs.
        Focus on clean architecture, separation of concerns, and maintainability.
        Be specific about file structure and dependencies."""
    )
    
    implementer = create_agent(
        ModelTier.MEDIUM,  # Good balance for code generation
        system_prompt="""You are a Python developer who implements designs.
        You write clean, well-structured code following best practices.
        You use Typer for CLIs, Pydantic for models, and follow conventions."""
    )
    
    # Test scenario: Design a simple app
    requirement = "A CLI app to track daily habits with streaks and statistics"
    
    print(f"Requirement: {requirement}\n")
    print("Step 1: Architect designs the system...")
    
    class AppDesign(BaseModel):
        name: str
        description: str
        core_models: List[str]
        cli_commands: List[str]
        file_structure: dict
        key_dependencies: List[str]
    
    design = architect.run_sync(
        f"Design a CLI application for: {requirement}",
        result_type=AppDesign
    )
    
    print(f"\nDesign by Architect:")
    print(f"  App Name: {design.name}")
    print(f"  Description: {design.description}")
    print(f"  Core Models: {', '.join(design.core_models)}")
    print(f"  CLI Commands: {', '.join(design.cli_commands)}")
    print(f"  Dependencies: {', '.join(design.key_dependencies)}")
    
    print(f"\n  File Structure:")
    def print_structure(d, indent=4):
        for key, value in d.items():
            if isinstance(value, dict):
                print(" " * indent + f"├── {key}/")
                print_structure(value, indent + 4)
            else:
                print(" " * indent + f"├── {key}")
    print_structure(design.file_structure)
    
    print("\nStep 2: Implementer creates code skeleton...")
    
    class CodeSnippet(BaseModel):
        filename: str
        purpose: str
        code: str
    
    # Have the implementer create a key file based on the design
    snippet = implementer.run_sync(
        f"""Based on this design, create the main Pydantic model file:
        {design.model_dump_json(indent=2)}
        
        Focus on the core data model for habits.""",
        result_type=CodeSnippet
    )
    
    print(f"\nCode by Implementer:")
    print(f"  File: {snippet.filename}")
    print(f"  Purpose: {snippet.purpose}")
    print(f"\n  Code Preview:")
    print("  " + "\n  ".join(snippet.code.split("\n")[:15]))  # First 15 lines
    if len(snippet.code.split("\n")) > 15:
        print("  ...")


def demo_3_context_aware_generation():
    """
    Demo 3: Context-Aware Generation
    
    Shows how Marvin can generate contextually appropriate content
    based on existing patterns and conventions in the codebase.
    """
    print("\n" + "="*60)
    print("DEMO 3: CONTEXT-AWARE GENERATION")
    print("="*60 + "\n")
    
    # Simulate existing codebase context
    existing_code_context = """
    Existing Clanker conventions:
    - All apps live in apps/ directory
    - Each app has its own pyproject.toml
    - Apps use Typer for CLI with Rich for output
    - Data stored in data/{app_name}/ directory
    - Pydantic models in models.py
    - CLI interface in cli.py
    - Storage logic in storage.py
    """
    
    print("Testing context-aware code generation:\n")
    
    # Example 1: Generate consistent CLI command
    class CLICommand(BaseModel):
        name: str
        function_name: str
        help_text: str
        parameters: List[dict]
        implementation: str
    
    new_feature = "export recipes to markdown files"
    
    print(f"Feature Request: {new_feature}")
    print("\nGenerating Typer CLI command following conventions...")
    
    # Use fast model for code generation
    agent = create_agent(ModelTier.LOW)
    
    command = agent.run_sync(
        f"""Create a Typer CLI command for: {new_feature}
        
        Context: {existing_code_context}
        
        Follow these patterns:
        - Use @app.command() decorator
        - Include type hints
        - Use Rich for console output
        - Handle errors gracefully
        - Follow existing parameter naming conventions
        """,
        result_type=CLICommand
    )
    
    print(f"\nGenerated Command: {command.name}")
    print(f"Function: {command.function_name}()")
    print(f"Help: {command.help_text}")
    print(f"Parameters: {[p['name'] for p in command.parameters]}")
    print(f"\nImplementation:\n{command.implementation}")
    
    # Example 2: Generate compatible data model
    print("\n" + "-"*40)
    print("Generating compatible Pydantic model...")
    
    class ModelGeneration(BaseModel):
        model_name: str
        imports: List[str]
        fields: List[dict]
        methods: List[str]
        full_code: str
    
    model_request = "a model for tracking reading progress in books"
    
    # Use medium tier for more complex model generation
    agent = create_agent(ModelTier.MEDIUM)
    
    model = agent.run_sync(
        f"""Create a Pydantic model for: {model_request}
        
        Context: {existing_code_context}
        
        Requirements:
        - Use Pydantic v2 syntax
        - Include field validation where appropriate
        - Add useful computed properties
        - Follow naming conventions from existing models
        """,
        result_type=ModelGeneration
    )
    
    print(f"\nModel: {model.model_name}")
    print(f"Fields: {[f['name'] for f in model.fields]}")
    print(f"Methods: {model.methods}")
    print(f"\nCode:\n{model.full_code}")


def main():
    """Run all demos"""
    print("\n🤖 MARVIN DEEP DIVE - CLANKER INTEGRATION 🤖")
    
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("\n⚠️  No API keys found in .env file!")
        print("Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in your .env file")
        return
    
    try:
        # Run each demo
        demo_1_intelligent_routing()
        demo_2_agent_collaboration()
        demo_3_context_aware_generation()
        
        print("\n" + "="*60)
        print("✅ All demos completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure you have valid API keys in your .env file")


if __name__ == "__main__":
    main()