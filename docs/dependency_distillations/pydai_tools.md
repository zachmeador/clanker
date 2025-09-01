# Pydantic AI Tools Reference for Clanker

## Overview

Pydantic AI provides two main classes for defining tools that AI agents can use:
- `Tool` - High-level class for wrapping Python functions as tools
- `ToolDefinition` - Lower-level dataclass defining tool metadata
- `RunContext` - Context passed to tools containing dependencies, model info, and conversation state

## RunContext

`RunContext` provides tools with access to the current execution context:

```python
@dataclass
class RunContext[AgentDepsT]:
    deps: AgentDepsT                    # Agent dependencies
    model: Model                        # The model being used
    usage: RunUsage                     # LLM usage stats
    messages: list[ModelMessage]        # Conversation history
    tool_name: str | None               # Name of current tool
    retry: int                          # Number of retries so far
    run_step: int                       # Current step in the run
```

## Tool Class

### Complete Parameters

```python
from pydantic_ai import Tool, RunContext

Tool(
    function,                           # The Python function to wrap
    takes_ctx=False,                   # Whether function takes RunContext as first arg
    name=None,                         # Custom name (defaults to function name)
    description=None,                  # Tool description (auto-generated if not provided)
    prepare=None,                      # Optional preparation function
    requires_approval=False,           # Whether tool needs human approval
    max_retries=None,                  # Max retries for this tool
    docstring_format='auto',           # Format: 'google', 'numpy', 'sphinx', 'auto'
    require_parameter_descriptions=False,  # Enforce param descriptions
    strict=None,                       # Enforce strict JSON schema (OpenAI only)
    function_schema=None,              # Custom function schema
)
```

### Key Features for Clanker

#### 1. Context-Aware Tools
Tools can receive the `RunContext` which provides access to dependencies and agent state:

```python
async def run_app_tool(ctx: RunContext, app_name: str, args: str = "") -> str:
    """Run a Clanker app with arguments"""
    # Access context dependencies if needed
    # ctx.deps could contain app registry, storage paths, etc.
    returncode = run(app_name, args.split())
    return f"Successfully ran {app_name}"

tool = Tool(run_app_tool, takes_ctx=True)
```

#### 2. Tool Preparation
The `prepare` parameter allows customizing tool availability based on context:

```python
async def prepare_app_tool(ctx: RunContext, tool_def: ToolDefinition):
    """Only enable tool if app exists"""
    if app_exists(ctx.deps.app_name):
        return tool_def
    return None  # Tool not available

tool = Tool(run_app_tool, prepare=prepare_app_tool)
```

#### 3. Approval-Required Tools
For sensitive operations, tools can require approval:

```python
tool = Tool(
    delete_all_recipes,
    requires_approval=True,  # Will defer execution for approval
    description="Delete all recipes (requires confirmation)"
)
```

## ToolDefinition Class

Lower-level representation of a tool that gets passed to the model:

```python
@dataclass
class ToolDefinition:
    name: str                           # Tool name
    parameters_json_schema: dict        # JSON schema for parameters
    description: str | None = None      # Tool description
    strict: bool | None = None          # Enforce strict JSON schema
    kind: Literal['function', 'output', 'external', 'unapproved'] = 'function'
```

### Tool Kinds

- **'function'**: Normal executable tool (default)
- **'output'**: Passes through a value, ending the run
- **'external'**: Result produced outside agent run (e.g., human input)
- **'unapproved'**: Requires human approval before execution

## Deferred Tool Execution

Pydantic AI supports deferred tool execution for tools that require:
- Human approval (`requires_approval=True`)
- External execution (long-running operations)

### DeferredToolRequests

Output type for runs with deferred tools:

```python
@dataclass
class DeferredToolRequests:
    calls: list[ToolCallPart]      # Tools requiring external execution
    approvals: list[ToolCallPart]  # Tools requiring approval
```

### DeferredToolResults

Input for continuing after deferred execution:

```python
@dataclass
class DeferredToolResults:
    calls: dict[str, Any]           # Results for external tools
    approvals: dict[str, bool | ToolApproved | ToolDenied]  # Approval decisions
```

Example usage:

```python
# First run - tool requires approval
result = agent.run("delete all recipes", output_type=DeferredToolRequests)
if isinstance(result.output, DeferredToolRequests):
    # Get user approval
    for call in result.output.approvals:
        print(f"Approve {call.tool_name}? (y/n)")
        approved = input() == 'y'
        
    # Continue with approval results
    deferred_results = DeferredToolResults(
        approvals={call.id: approved for call in result.output.approvals}
    )
    final_result = agent.run(deferred_results)
```

## Tool.from_schema

Create tools from existing JSON schemas:

```python
tool = Tool.from_schema(
    function=my_function,
    name="custom_tool",
    description="Tool description",
    json_schema={
        "type": "object",
        "properties": {
            "arg1": {"type": "string"},
            "arg2": {"type": "integer"}
        },
        "required": ["arg1"]
    },
    takes_ctx=True
)
```

## Practical Examples for Clanker

### Example 1: Dynamic App Tools

```python
from pydantic_ai import Tool, RunContext
from clanker.apps import discover, run

def create_app_tools():
    """Create tools for each discovered Clanker app"""
    tools = []
    apps = discover()
    
    for app_name, app_info in apps.items():
        # Create a tool function for each app
        async def app_tool(ctx: RunContext, args: str = "", name=app_name) -> str:
            arg_list = args.split() if args else []
            returncode = run(name, arg_list)
            
            if returncode == 0:
                return f"Successfully ran {name}"
            else:
                return f"{name} exited with code {returncode}"
        
        # Create tool with descriptive metadata
        tool = Tool(
            app_tool,
            name=f"run_{app_name}",
            description=app_info.get("description", f"Run the {app_name} app"),
            takes_ctx=True
        )
        tools.append(tool)
    
    return tools
```

### Example 2: Tool with Output Capture

```python
import subprocess
from io import StringIO
import sys

async def run_app_with_capture(ctx: RunContext, app_name: str, args: str = "") -> str:
    """Run app and capture output"""
    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    
    try:
        returncode = run(app_name, args.split())
        output = captured_output.getvalue()
        
        return f"Output:\n{output}\nExit code: {returncode}"
    finally:
        sys.stdout = old_stdout

tool = Tool(
    run_app_with_capture,
    takes_ctx=True,
    description="Run app and capture its output"
)
```

### Example 3: Conditional Tool Availability

```python
async def bash_tool(ctx: RunContext, command: str) -> str:
    """Execute bash command (only in dev mode)"""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout or result.stderr

async def prepare_bash(ctx: RunContext, tool_def: ToolDefinition):
    """Only enable bash in development mode"""
    if ctx.deps.get("dev_mode", False):
        return tool_def
    return None

bash = Tool(
    bash_tool,
    takes_ctx=True,
    prepare=prepare_bash,
    description="Execute bash commands (dev mode only)"
)
```

## Tool Execution Flow in Clanker

1. **Discovery**: Tools are created dynamically based on available apps
2. **Registration**: Tools are added to the agent's toolset
3. **Execution**: When agent.run() is called:
   - LLM decides which tool to call
   - Tool executes immediately within the run
   - Output is captured and returned to LLM
   - LLM formulates final response

## Key Insights for Tool Visibility

The challenge with showing tool calls in real-time stems from the execution model:

1. **Synchronous Execution**: Tools execute within `agent.run()`, not before or after
2. **No Interception Points**: Pydantic AI doesn't provide hooks during tool execution
3. **Message History**: Tool calls are only visible in message history after completion

### Potential Solutions

1. **Output Capture During Execution**:
```python
import sys
from io import StringIO

# Capture stdout during agent.run()
captured = StringIO()
old_stdout = sys.stdout
sys.stdout = captured

result = await agent.run(prompt)

sys.stdout = old_stdout
tool_output = captured.getvalue()

# Now display tool output in controlled way
if tool_output:
    console.print(f"[dim]Tool output: {tool_output}[/dim]")
```

2. **Deferred Tools for Visibility**:
```python
# Make tools deferred to get visibility before execution
tool = Tool(
    run_recipes,
    requires_approval=True  # Forces deferred execution
)

# Now you can see what will be called before it executes
result = agent.run(prompt, output_type=DeferredToolRequests)
for call in result.output.calls:
    print(f"Will call: {call.tool_name}({call.args})")
```

3. **Custom prepare Function**:
```python
async def log_and_prepare(ctx: RunContext, tool_def: ToolDefinition):
    # Log that tool is about to be available
    print(f"Tool {tool_def.name} prepared for step {ctx.run_step}")
    return tool_def

tool = Tool(my_function, prepare=log_and_prepare)
```

4. **Message History Analysis**:
```python
# Access conversation history in RunContext
async def context_aware_tool(ctx: RunContext, arg: str):
    # See what's been discussed
    for msg in ctx.messages:
        if hasattr(msg, 'parts'):
            for part in msg.parts:
                if isinstance(part, ToolCallPart):
                    print(f"Previous tool: {part.tool_name}")
    
    # Tool logic here
    return "result"
```

## Best Practices for Clanker

1. **Descriptive Names**: Use clear, action-oriented tool names (`run_recipes`, not `recipes`)
2. **Comprehensive Descriptions**: Include available commands/options in descriptions
3. **Error Handling**: Return informative error messages rather than raising exceptions
4. **Output Formatting**: Return structured, parseable output for the LLM
5. **Context Usage**: Use RunContext for dependencies rather than global state

## References

- [Pydantic AI Tools API](https://ai.pydantic.dev/api/tools/)
- [Pydantic AI Agent Documentation](https://ai.pydantic.dev/agents/)
- [Tool Examples](https://ai.pydantic.dev/examples/)