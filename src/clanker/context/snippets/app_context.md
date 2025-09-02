# App Context

## Location
Apps are located in the `apps/` directory

## Structure
- `main.py`: CLI entry point with typer commands
- `pyproject.toml`: Dependencies and CLI export configuration
- Package directory for larger apps

## CLI Exports
Available as AI tools in Clanker console:
- Commands defined in `[tool.clanker.exports]` section
- Called as `app_name_command_name(args)`

## Storage
- File storage: `data/<profile>/vault/<app_name>/`
- Database: Scoped access to shared SQLite
- Cross-app access requires explicit permission grants

## Development
- Test locally: `cd apps/<app_name> && uv run python main.py`
- Test via Clanker: `clanker <app_name>_<command> args`
- Storage access requires proper vault/db initialization
