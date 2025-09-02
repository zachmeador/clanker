# CLI Export System

## How It Works
Apps can expose their CLI commands as AI tools by adding `[tool.clanker.exports]` to `pyproject.toml`:

```toml
[tool.clanker.exports]
hello = "python main.py hello {name}"
status = "python main.py status"
search = "python main.py search --query {query}"
```

## Available as AI Tools
- `appname_hello(name="Alice")` → `python apps/appname/main.py hello Alice`
- `appname_status()` → `python apps/appname/main.py status`
- `appname_search(query="pasta")` → `python apps/appname/main.py search --query pasta`

## In Clanker Console
```bash
clanker "use the hello command"
# Agent finds and calls appname_hello tool
```

## Parameter Types
- String parameters: `{param}`
- Optional parameters: `{param}` (agent decides if needed)
- All parameters passed as command line arguments
