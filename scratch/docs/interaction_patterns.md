note: this was written by a robot. i haven't vetted it yet.

### Clanker Interaction Patterns

**Core Principle**: Clanker is an LLM-native development environment where AI tools do the heavy lifting

### Primary Interface: Natural Language (No Quotes!)

`clanker save this pasta recipe from my grandmother`
`clanker what did I cook last week`
`clanker build an app that tracks my workouts`
`clanker work on the resume app`

**Input Handling**: Everything after `clanker` is captured as the request - no quotes needed

### Interaction Modes

**1. Natural Language Requests**
```bash
clanker remind me to buy groceries tomorrow
clanker show me all recipes with chicken
clanker help me update my resume for a PM role
```
- Parse entire command line after `clanker` as single request
- Route to appropriate app or action
- Handle multi-word inputs naturally

**2. Development Handoff**
```bash
clanker launch claude to build a habit tracker
clanker launch cursor fix the recipe storage bug
clanker work on the recipes app with gemini
```
- Spawns LLM tool with context + request
- Everything after launch command becomes the initial prompt

**3. Explicit App Commands**
```bash
clanker recipes add pasta primavera recipe here...
clanker resumes build senior-engineer
clanker app list
```
- First word after `clanker` checked against known apps/commands
- Falls back to natural language if not recognized

**4. Special Commands (minimal)**
```bash
clanker --help
clanker --version
clanker --list-apps
clanker --config
```
- Flag-based for explicit system commands
- Everything else assumed to be natural language

### Input Resolution Strategy

1. Check if first token is a known app → route to app CLI
2. Check if it's a system command (launch, app, profile) → execute
3. Check for flags (--help, etc.) → handle directly  
4. Default: treat entire input as natural language request → agent handles

### Implementation Notes

**Typer/Click Handling**
- Use `*args` or remainder pattern to capture all tokens
- Join tokens back into single string for processing
- No shell quoting needed for user

**Examples of Robust Parsing**
- `clanker make dinner suggestions from my saved recipes`
- `clanker recipes grep chicken` (explicit app command)
- `clanker launch claude` (opens blank session)
- `clanker launch claude create a meditation timer app` (with context)

### What This Enables

- **Natural conversation**: Type like you're talking
- **No syntax burden**: User doesn't think about quotes or escaping
- **Flexible routing**: Smart fallbacks and interpretation
- **Progressive complexity**: Simple stays simple, complex is possible