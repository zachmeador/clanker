# Pydantic AI Messages - Technical Summary for Clanker

## Core Functionality
Pydantic AI's message system provides conversation history management for agent runs, enabling context preservation across multiple interactions. Messages are model-agnostic and can be serialized to JSON for persistence.

## Basic Message Access

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-4o', system_prompt='Be helpful')
result = agent.run_sync('Tell me about Python')

# Get all messages including system prompt
all_msgs = result.all_messages()

# Get only messages from this run
new_msgs = result.new_messages()

# Get as JSON bytes
json_msgs = result.all_messages_json()
```

## Continuing Conversations

```python
# First interaction
result1 = agent.run_sync('What is asyncio?')
print(result1.output)

# Continue conversation with context
result2 = agent.run_sync(
    'Can you give an example?', 
    message_history=result1.new_messages()
)
print(result2.output)  # Will provide asyncio example based on prior context
```

## Message Persistence

```python
from pydantic_core import to_jsonable_python
from pydantic_ai.messages import ModelMessagesTypeAdapter

# Save messages to JSON
messages = result.all_messages()
json_data = to_jsonable_python(messages)

# Store in AppDB for cross-app sharing
db.execute("INSERT INTO conversations (messages) VALUES (?)", 
           [json.dumps(json_data)])

# Load messages from JSON
loaded_json = db.fetchone("SELECT messages FROM conversations")
restored_messages = ModelMessagesTypeAdapter.validate_python(
    json.loads(loaded_json)
)

# Resume conversation with loaded history
result = agent.run_sync('Continue...', message_history=restored_messages)
```

## History Processors for Token Management

```python
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelMessage

def limit_tokens_by_tier(
    ctx: RunContext[None], 
    messages: list[ModelMessage]
) -> list[ModelMessage]:
    """Adjust history based on model tier"""
    tier = ctx.agent.model_name
    
    if 'haiku' in tier or 'mini' in tier:  # LOW tier
        return messages[-3:]  # Keep only recent 3
    elif 'sonnet' in tier:  # MEDIUM tier  
        return messages[-10:]
    return messages  # HIGH tier gets full history

def filter_sensitive_data(messages: list[ModelMessage]) -> list[ModelMessage]:
    """Remove messages containing sensitive patterns"""
    return [
        msg for msg in messages 
        if not any(word in str(msg) for word in ['password', 'secret'])
    ]

# Apply multiple processors
agent = Agent(
    'openai:gpt-4o',
    history_processors=[filter_sensitive_data, limit_tokens_by_tier]
)
```

## Summarizing Old Messages

```python
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelRequest, UserPromptPart

# Summarizer using cheap model
summarizer = Agent('openai:gpt-4o-mini', 
    system_prompt='Summarize key points concisely')

async def compress_history(messages: list[ModelMessage]) -> list[ModelMessage]:
    if len(messages) > 20:
        # Summarize older messages
        old_msgs = messages[:15]
        summary = await summarizer.run(message_history=old_msgs)
        
        # Create summary message
        summary_msg = ModelRequest(parts=[
            UserPromptPart(content=f"Previous context: {summary.output}")
        ])
        
        # Return summary + recent messages
        return [summary_msg] + messages[-5:]
    return messages

agent = Agent('openai:gpt-4o', history_processors=[compress_history])
```

## Clanker Integration Examples

### ClankerAgent with Conversation Memory

```python
# In agent.py
class ClankerAgent:
    def __init__(self, ...):
        self.conversation_cache = {}  # In-memory cache
        
    async def handle_request(self, query: str, session_id: str = None):
        # Load previous conversation if exists
        message_history = None
        if session_id and session_id in self.conversation_cache:
            message_history = self.conversation_cache[session_id]
        
        # Run with history
        result = await self.agent.run(
            query, 
            message_history=message_history
        )
        
        # Cache for next interaction
        if session_id:
            self.conversation_cache[session_id] = result.new_messages()
        
        return result.output
```

### Cross-App Context Sharing

```python
# App A saves conversation
from clanker.storage import AppDB
from pydantic_core import to_jsonable_python

db = AppDB("recipe-finder", db_path)
messages = result.all_messages()
db.execute(
    "INSERT INTO shared_contexts (context_id, messages) VALUES (?, ?)",
    ["cooking_session_123", json.dumps(to_jsonable_python(messages))]
)

# App B loads and continues
from pydantic_ai.messages import ModelMessagesTypeAdapter

db = AppDB("meal-planner", db_path)
data = db.fetchone(
    "SELECT messages FROM shared_contexts WHERE context_id = ?",
    ["cooking_session_123"]
)
messages = ModelMessagesTypeAdapter.validate_python(json.loads(data))

# Continue with context from recipe-finder
agent = get_agent("meal-planning")
result = agent.run_sync(
    "Create a shopping list for these recipes",
    message_history=messages
)
```

### Model Tier-Aware Processing

```python
# In models.py enhancement
from pydantic_ai import Agent

def create_tier_optimized_agent(
    name: str, 
    tier: ModelTier,
    **kwargs
) -> Agent:
    """Create agent with tier-appropriate history processing"""
    
    processors = []
    
    if tier == ModelTier.LOW:
        # Aggressive trimming for cheap models
        processors.append(lambda msgs: msgs[-3:])
    elif tier == ModelTier.MEDIUM:
        # Moderate history with summarization
        processors.append(create_summarizer(max_msgs=10))
    # HIGH tier gets full history
    
    return Agent(
        get_model_for_tier(tier),
        history_processors=processors,
        **kwargs
    )
```

## Testing with FunctionModel

```python
# Test history processors
from pydantic_ai.models.function import FunctionModel, AgentInfo

def test_message_filtering():
    captured_messages = []
    
    def mock_model(messages: list[ModelMessage], info: AgentInfo):
        captured_messages.extend(messages)
        return ModelResponse(parts=[TextPart(content="test")])
    
    model = FunctionModel(mock_model)
    agent = Agent(model, history_processors=[filter_sensitive_data])
    
    # Run with sensitive data
    sensitive_history = [
        ModelRequest(parts=[UserPromptPart(content="my password is 123")])
    ]
    
    agent.run_sync("Hello", message_history=sensitive_history)
    
    # Verify sensitive message was filtered
    assert not any("password" in str(msg) for msg in captured_messages)
```

## Key Implementation Notes
- Messages are simple dataclasses, easily manipulated
- History processors must maintain tool call/return pairing
- StreamedRunResult messages incomplete until stream finishes
- System prompts not regenerated when message_history provided
- Processors replace history (make copies if needed)