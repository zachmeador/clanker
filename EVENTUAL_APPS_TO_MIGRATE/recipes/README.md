# Recipes

Simple recipe manager using clanker vault storage with AI-powered parsing.

## Features

- **AI Recipe Parsing**: Uses Claude/GPT models to automatically parse and structure recipe text
- **Vault Storage**: Recipes stored in markdown format with frontmatter metadata
- **Recipe Logging**: Track when you made recipes and add personal notes
- **Search & Discovery**: Full-text search across all recipes
- **Rich Terminal UI**: Beautiful formatting with Rich library
- **Flexible Model Support**: Uses clanker's centralized model management

## Installation

Requires Python 3.13+ and uv package manager.

```bash
cd apps/recipes
uv sync
```

## Usage

### Add a Recipe

Parse and add a new recipe from text:

```bash
uv run python main.py add "Pasta Carbonara: Cook 200g pasta. Mix 2 eggs with 50g parmesan..."
```

Or specify a custom name:

```bash
uv run python main.py add --name "Classic Carbonara" "Recipe text here..."
```

### View Recipes

List all recipes:
```bash
uv run python main.py list
```

Show a specific recipe:
```bash
uv run python main.py show "Classic Carbonara"
```

### Search Recipes

Search for recipes containing a term:
```bash
uv run python main.py grep "pasta"
uv run python main.py grep "italian"
```

### Recipe Management

Replace an existing recipe:
```bash
uv run python main.py replace "Classic Carbonara" "Updated recipe text..."
```

Delete a recipe:
```bash
uv run python main.py delete "Classic Carbonara"
```

### Recipe Logging

Log when you made a recipe:
```bash
uv run python main.py log "Classic Carbonara" "Made this for dinner - turned out great!"
```

Log with specific date:
```bash
uv run python main.py log "Classic Carbonara" --date "2024-01-15" "Family loved it!"
```

## Recipe Format

Recipes are stored as Markdown files with YAML frontmatter:

```yaml
---
title: Classic Carbonara
servings: 4
prep_time: 10
cook_time: 15
tags: [italian, pasta, quick]
source: "Family Recipe"
created: "2024-01-15T10:30:00"
---

## Ingredients
- 200g spaghetti
- 2 large eggs
- 50g grated parmesan
- 100g pancetta
- Black pepper

## Instructions

1. Cook pasta in boiling salted water
2. Fry pancetta until crispy
3. Mix eggs and cheese
4. Combine everything and serve
```

## Dependencies

- **clanker**: Core framework and vault storage
- **pydantic-ai**: AI-powered recipe parsing
- **typer**: CLI framework
- **rich**: Terminal formatting
- **python-frontmatter**: YAML frontmatter handling
- **pydantic**: Data validation

## Model Configuration

Uses clanker's centralized model management. Configure API keys in your `.env` file:

```bash
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
```

The app uses `ModelTier.MEDIUM` for balanced performance and cost.