# Tool Export System

## How App Commands Become AI Tools
Apps expose their functionality as AI tools by adding exports to `pyproject.toml`:

```toml
[tool.clanker.exports]
hello = "python main.py hello {name}"
status = "python main.py status"
search = "python main.py search --query {query}"
```

## Tool Discovery
The Clanker agent automatically discovers these exports and creates AI tools:

- `appname_hello(name="Alice")` → executes `python apps/appname/main.py hello Alice`
- `appname_status()` → executes `python apps/appname/main.py status`  
- `appname_search(query="pasta")` → executes `python apps/appname/main.py search --query pasta`

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
