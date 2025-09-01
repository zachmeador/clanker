# Recipe Agent Technical Specification

## UX Interaction Patterns

### Primary Entry Point
```bash
# Launch conversational agent
uv run python main.py chat
```

### Core Conversation Flows

#### Recipe Addition Pattern
```
User: "Add this carbonara recipe I found online..."
Agent: [parses text] → [validates] → [saves] → "Added 'Classic Carbonara' with 4 servings. Tagged as: italian, pasta, quick."

User: "Wait, it's actually 6 servings and takes 20 min to cook"
Agent: [updates frontmatter] → "Updated servings to 6 and cook time to 20 minutes."
```

#### Recipe Discovery Pattern
```
User: "What pasta recipes do I have?"
Agent: [searches vault] → "Found 3 pasta recipes:
• Classic Carbonara (italian, quick)
• Pesto Genovese (italian, vegetarian)
• Arrabbiata (italian, spicy)

Which would you like to see?"

User: "Show me the carbonara"
Agent: [loads & formats] → [displays with Rich markdown]
```

#### Modification Pattern
```
User: "I made the carbonara last night and used bacon instead of pancetta"
Agent: [finds recipe] → [appends to log section] → "Noted your bacon substitution in the log."

User: "Actually, double the recipe for 8 people"
Agent: [scales ingredients] → [updates servings] → "Scaled recipe for 8 servings."
```

## Agent Architecture

### Core Agent Structure
```python
class RecipeAgent:
    def __init__(self):
        self.agent = Agent(
            model=get_model(ModelTier.MEDIUM),
            system_prompt=RECIPE_AGENT_PROMPT,
            tools=self._get_tools()
        )
        self.storage = RecipeStorage()
        self.context = ConversationContext()

    def chat(self, user_input: str) -> str:
        """Main conversation entry point"""
        try:
            result = self.agent.run_sync(user_input)
            return result.output
        except Exception as e:
            return f"Error: {e}"
```

### Tool Implementations

#### add_recipe Tool
```python
@agent.tool
def add_recipe(self, recipe_text: str, name: Optional[str] = None) -> str:
    """Parse and store recipe from natural language text.

    Args:
        recipe_text: Raw recipe text (pasted from web, etc.)
        name: Optional custom name for the recipe

    Returns:
        Success message with recipe details
    """
    # Parse with existing agent
    parser_agent = get_recipe_agent()
    result = parser_agent.run_sync(recipe_text)
    recipe = result.output

    # Handle naming
    recipe_name = name or recipe.frontmatter.title
    normalized_name = self.storage._normalize_name(recipe_name)

    # Check for duplicates
    if self.storage.exists(normalized_name):
        return f"Recipe '{recipe_name}' already exists. Use 'update {recipe_name}' to modify it."

    # Save and return
    path = self.storage.save(normalized_name, recipe)
    return f"Added '{recipe.frontmatter.title}' ({recipe.frontmatter.servings} servings) to your collection."
```

#### find_recipes Tool
```python
@agent.tool
def find_recipes(self, query: str) -> str:
    """Search recipes by ingredients, cuisine, tags, or title.

    Args:
        query: Search term (e.g., "pasta", "italian", "chicken parmesan")

    Returns:
        Formatted list of matching recipes
    """
    # Multi-field search
    all_recipes = self.storage.list_recipes()
    matches = []

    for recipe_name in all_recipes:
        recipe = self.storage.load(recipe_name)
        if not recipe:
            continue

        # Search multiple fields
        searchable_text = ' '.join([
            recipe.frontmatter.title,
            ' '.join(recipe.frontmatter.tags),
            recipe.content
        ]).lower()

        if query.lower() in searchable_text:
            matches.append(recipe)

    # Format results
    if not matches:
        return f"No recipes found matching '{query}'."

    result = f"Found {len(matches)} recipes:\n\n"
    for recipe in matches[:5]:  # Limit to 5 for readability
        tags_str = ', '.join(recipe.frontmatter.tags) if recipe.frontmatter.tags else ''
        result += f"• {recipe.frontmatter.title} ({tags_str})\n"

    if len(matches) > 5:
        result += f"\n... and {len(matches) - 5} more"

    return result
```

#### show_recipe Tool
```python
@agent.tool
def show_recipe(self, name: str) -> str:
    """Display formatted recipe with Rich markdown.

    Args:
        name: Recipe name to display

    Returns:
        Rich-formatted markdown content
    """
    recipe = self.storage.load(name)
    if not recipe:
        # Fuzzy search for similar names
        similar = self._find_similar_recipes(name)
        if similar:
            return f"Recipe '{name}' not found. Did you mean: {', '.join(similar[:3])}?"
        return f"Recipe '{name}' not found."

    # Build formatted output
    content = f"# {recipe.frontmatter.title}\n\n"
    content += f"**Servings:** {recipe.frontmatter.servings}\n"

    if recipe.frontmatter.prep_time:
        content += f"**Prep:** {recipe.frontmatter.prep_time} min\n"
    if recipe.frontmatter.cook_time:
        content += f"**Cook:** {recipe.frontmatter.cook_time} min\n"

    if recipe.frontmatter.tags:
        content += f"**Tags:** {', '.join(recipe.frontmatter.tags)}\n"

    content += "\n" + recipe.content

    return content
```

## Error Handling Patterns

### Validation Errors
```
User: "Add this recipe with no title"
Agent: "Missing recipe title. Can you provide the recipe name?"
```

### Duplicate Handling
```
User: "Add carbonara recipe..."
Agent: "Recipe 'Classic Carbonara' already exists. Would you like to:
• Update the existing recipe
• Save as 'Classic Carbonara v2'
• Replace completely"
```

### Malformed Input
```
User: "Show me recipes with xyz ingredient"
Agent: "No recipes found with 'xyz'. Did you mean 'eggs' or 'eggsplant'?"
```

## Context Management

### Conversation State
```python
class ConversationContext:
    def __init__(self):
        self.recent_recipes = []  # Last 5 recipes mentioned
        self.last_operation = None  # Track what was just done
        self.user_preferences = {}  # Units, cuisine preferences, etc.

    def update_recent(self, recipe_name: str):
        """Track recently accessed recipes for context"""
        if recipe_name in self.recent_recipes:
            self.recent_recipes.remove(recipe_name)
        self.recent_recipes.insert(0, recipe_name)
        self.recent_recipes = self.recent_recipes[:5]
```

### Contextual Responses
```
Context: User just added "Carbonara"
User: "What's the cook time?"
Agent: [knows context] → "For the Carbonara you just added: 15 minutes"
```

## System Prompt

```
You are a recipe assistant that helps users manage their recipe collection through natural conversation.

CORE BEHAVIORS:
- Always use tools to interact with the recipe vault
- Be conversational but concise
- Handle malformed input gracefully
- Provide helpful suggestions
- Remember context from recent operations

TOOL USAGE:
- Use add_recipe for new recipes
- Use find_recipes for searches
- Use show_recipe for displaying recipes
- Use update_recipe for modifications
- Use log_recipe_made for cooking notes

VALIDATION:
- Ensure recipes have title and servings
- Infer missing fields when possible
- Ask for clarification on ambiguous input

ERROR HANDLING:
- Suggest corrections for typos
- Offer alternatives for missing recipes
- Provide clear feedback on failures
```

## CLI Integration

### Hybrid Interface
```python
@app.command()
def chat(
    model: Optional[str] = typer.Option(None, "--model", help="Model to use"),
    verbose: bool = typer.Option(False, "--verbose", help="Show agent thoughts")
):
    """Interactive recipe assistant."""
    agent = RecipeAgent(model=model)

    console.print("[bold blue]Recipe Assistant[/bold blue] (type 'exit' to quit)")
    console.print("Example: 'Add this carbonara recipe...' or 'Show me pasta recipes'\n")

    while True:
        try:
            user_input = Prompt.ask(">>> ")
            if user_input.lower() in ['exit', 'quit', 'q']:
                break

            with console.status("[yellow]Thinking...[/yellow]"):
                response = agent.chat(user_input)

            console.print(Markdown(response))

        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
```

## Tool Signatures

### Complete Tool Set
```python
# Core CRUD
add_recipe(recipe_text: str, name: Optional[str]) -> str
find_recipes(query: str) -> str
show_recipe(name: str) -> str
update_recipe(name: str, changes: str) -> str
delete_recipe(name: str) -> str

# Enhanced features
log_recipe_made(name: str, note: str, date: Optional[str]) -> str
scale_recipe(name: str, servings: int) -> str
find_similar(name: str) -> str
generate_shopping_list(recipes: List[str]) -> str

# Utility
list_recent() -> str
get_stats() -> str
search_by_ingredient(ingredient: str) -> str
```

## Performance Considerations

### Caching Strategy
```python
class RecipeCache:
    def __init__(self):
        self.recipe_cache = {}  # name -> recipe object
        self.search_cache = {}  # query -> results (with TTL)

    def get_recipe(self, name: str) -> Optional[RecipeContent]:
        """Cache recipe objects to avoid repeated file I/O"""
        if name not in self.recipe_cache:
            recipe = self.storage.load(name)
            if recipe:
                self.recipe_cache[name] = recipe
        return self.recipe_cache.get(name)
```

### Search Optimization
- Pre-compute searchable text for all recipes
- Use fuzzy matching for recipe names
- Cache common search results
- Index tags and ingredients separately

## Testing Patterns

### Tool Testing
```python
def test_add_recipe_tool():
    agent = RecipeAgent()
    recipe_text = "Simple Pasta: Cook pasta, add sauce."

    result = agent.add_recipe(recipe_text)
    assert "Simple Pasta" in result
    assert storage.exists("simple-pasta")
```

### Conversation Testing
```python
def test_conversation_flow():
    agent = RecipeAgent()

    # Test addition
    response1 = agent.chat("Add a simple pasta recipe")
    assert "added" in response1.lower()

    # Test context awareness
    response2 = agent.chat("What's the cook time?")
    assert "pasta" in response2.lower()
```
