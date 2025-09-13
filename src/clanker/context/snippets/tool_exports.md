# Tool Export System

## How App Commands Become AI Tools
Apps expose their functionality as AI tools by adding exports to `pyproject.toml`:

```toml
[tool.clanker.exports]
hello = {cmd = "python main.py hello {name}", desc = "Generate a greeting"}
status = {cmd = "python main.py status", desc = "Show current status"}
search = {cmd = "python main.py search --query {query}", desc = "Search with query"}
list = {cmd = "python main.py list", desc = "List all items"}
```

## Tool Discovery
The Clanker agent automatically discovers these exports and creates AI tools:

- `appname_hello(name="Alice")` → executes `uv run --project apps/appname python main.py hello Alice`
- `appname_status()` → executes `uv run --project apps/appname python main.py status`
- `appname_search(query="pasta")` → executes `uv run --project apps/appname python main.py search --query pasta`

## Usage Examples
```bash
# User asks in natural language
clanker "say hello to Alice"
# Agent automatically calls appname_hello(name="Alice")

clanker "search for pasta recipes"
# Agent calls appname_search(query="pasta recipes")
```

## Parameter Handling
- `{param}`: Required string parameter
- Parameters are passed as command-line arguments
- Agent determines which parameters to use based on user request
- Complex parameters are automatically quoted/escaped
