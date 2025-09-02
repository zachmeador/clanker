# App Context

## Location
`apps/{{app_name}}/`

## Structure
- `main.py`: CLI entry point with typer commands
- `pyproject.toml`: Dependencies and CLI export configuration
- `{{app_name}}/` package directory

## CLI Exports
Available as AI tools in Clanker console:
- Commands defined in `[tool.clanker.exports]` section
- Called as `{{app_name}}_command_name(args)`

## Storage
- File storage: `data/default/vault/{{app_name}}/`
- Database: Scoped access to shared SQLite
- Cross-app access requires explicit permission grants

## Development
- Test locally: `cd apps/{{app_name}} && uv run python main.py`
- Test via Clanker: `clanker {{app_name}}_command_name args`
- Storage access requires proper vault/db initialization
