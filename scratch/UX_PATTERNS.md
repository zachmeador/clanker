# Clanker Chat CLI UX Patterns

## Current State (from src/clanker/cli.py)

**How Clanker Currently Works:**
```
# One-shot command mode (no conversation loop)
$ clanker list my apps
[clanker responds and exits]

$ clanker run recipes add "chocolate cake"
[runs app and exits]

$ clanker what's the weather
[clanker responds and exits]
```

Key characteristics:
- Single request → response → exit
- No conversation memory between invocations
- Uses InputResolver to determine if input is natural language vs command
- Creates new ClankerAgent instance for each request
- No built-in confirmation flow
- No interactive chat mode

## Full Featured Demo (`demo_4_full_featured.py`)

**The Complete UX Pattern** - Combines all essential features for a modern CLI chat interface:

### Key Features

1. **Streaming Responses**
   - Text appears word-by-word for natural feel
   - Occasional pauses for readability
   - "Thinking..." indicator while processing

2. **Context Awareness**
   - Maintains last 3 exchanges in memory
   - Detects continuation phrases ("it", "that", "run it")
   - Tracks current topic (recipes, weather, apps, etc.)

3. **Tool Call Visibility**
   - Shows when tools are being called
   - Displays tool names and arguments
   - Shows tool results as they complete

### User Experience Flow

```
You: list my apps
[Thinking...]  <- appears briefly, then replaced by:
Clanker: I found these apps: recipes weather notes
         ^--- streams in word by word

You: tell me about recipes
Clanker: The recipes app can manage your recipe collection...

You: run it
→ Calling tool: run_recipes     <- tool visibility
  Args: {"args": ""}
← Tool result received
Clanker: Running recipes app...
(understood in context of recipes)  <- context indicator

You: context
Conversation Context
Exchange 1:
  You: list my apps...
  Clanker: I found these apps...
Exchange 2:
  You: tell me about recipes...
  Clanker: The recipes app can...
  Tools used: run_recipes
Current topic: recipes
```

### Implementation Highlights

- **Async architecture** for proper streaming support
- **Rich console formatting** with colors and panels
- **Deque for conversation history** with configurable window
- **Special commands**: context, tools, exit
- **Error handling** with graceful degradation
- **Pending indicator** that gets replaced by response
