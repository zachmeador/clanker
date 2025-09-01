# Example App - Export-Based Integration

This is a simple example app demonstrating the new export-based integration with Clanker.

## Features

- **CLI Commands**: `hello` and `test` commands available through Clanker CLI
- **Agent Tools**: Additional functions available as agent tools
- **Export-Based**: Uses the new `@export` decorator system instead of typer CLI

## Exported Functions

### CLI Commands (Available via `clanker example <command>`)

- `hello [name]` - Greet a user and show available AI providers
- `test` - Run a simple test

### Agent Tools (Available to Clanker agents)

- `greet_user(name)` - Say hello with provider information
- `run_test()` - Verify app functionality
- `get_system_info()` - Get system and provider information
- `validate_name(name)` - Validate if a name is acceptable
- `create_greeting(name, style)` - Create styled greetings

## Usage Examples

```bash
# CLI usage through Clanker
clanker example hello "Alice"
clanker example test

# Agent usage (through Clanker console or API)
# Agents can call functions like greet_user(), get_system_info(), etc.
```

## Migration from Typer

This app was previously built with typer CLI commands. The new export-based approach:

- ✅ Removes dependency on typer
- ✅ Allows selective exposure (CLI only, tool only, or both)
- ✅ Provides better agent integration with rich typing
- ✅ Enables self-documenting interfaces
- ✅ Supports both synchronous and asynchronous functions

## Development

The app structure is now:

```
example/
├── example/
│   ├── __init__.py     # Registers exports with Clanker
│   └── exports.py      # Contains all exported functions
├── main.py             # Simple entry point (backwards compatibility)
├── pyproject.toml      # Updated dependencies (removed typer)
└── README.md          # This file
```

## Export Declaration

Functions are exported using decorators:

```python
@export(
    name="function_name",
    description="What this function does",
    export_type=ExportType.BOTH,  # CLI, TOOL, or BOTH
    cli_path="command"             # Optional CLI command name
)
def my_function(param: str) -> str:
    # Implementation here
    pass
```

This approach makes apps loosely coupled with Clanker while enabling deep integration when desired.
