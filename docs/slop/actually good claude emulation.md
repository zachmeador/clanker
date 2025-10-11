- if a testing convention was done in clanker it would be the most low effort possible. like "hey clanker does my weather app work" and it just runs it for a few mins and tells you what broke. no jest configs or whatever
- observability: central logging is good, but keep it dumb simple. each app already logs to its own file. could just have a `clanker logs --follow` that tails all active stuff. agent could grep through when debugging.
- secrets management: env vars + vault files that don't get committed is probably fine for now. later maybe a `secrets_` prefix for vault files that get encrypted at rest?
- dev workflows: hot reload would be sick but out of scope. staging/prod profiles... we already have profiles, just need conventions around them.


# CONTEXT & INSTRUCTIONS SYSTEM

## dynamic instruction generation

- the core insight: instructions shouldn't be static markdown that gets stale
- instead build them from:
    - snippets: reusable chunks explaining conventions (in docs/snippets or whatever)
    - live state: current apps, active daemons, recent errors
    - app-specific: each app can contribute its own context
- when clanker launches claude/cursor/whatever, it builds the instruction file on the fly
- means the agent always sees current truth, not 3-week-old docs
- CLAUDE.md, GEMINI.md, AGENTS.md etc are templates + includes basically

thinking this through more:
- snippet system lives in docs/snippets/
- each snippet is standalone: storage.md, app_structure.md, daemon_management.md
- instruction builders are in src/clanker/context/
- `context.build_for_agent(agent_type, profile, current_request)` returns the full instruction string
- includes logic like "user asked about recipes, inject recipes app docs"
- maybe snippets have frontmatter for tags/triggers? `tags: [storage, vault, cross-app]`

benefits:
- instruction files stay current automatically
- can inject request-specific context
- snippets are easier to maintain than massive markdown files
- agent handoff is easier: "here's what i know, here's what you need to know"
- testing becomes possible: "does the storage snippet get included when user asks about files?"


## agent handoffs

- sometimes clanker should spawn/switch to a specialized agent
- `clanker launch cursor i need to refactor the daemon manager`
    - builds context for cursor with: clanker overview, daemon code locations, current issue
    - launches cursor with that context as system prompt + user request
- or mid-conversation: "this is getting into deep refactoring territory, let me hand you to cursor..."
    - export conversation so far
    - build handoff context
    - launch other agent with conversation + context
- needs to feel seamless not janky
- return path? cursor finishes, drops a summary in clanker's vault, clanker reads it next time?


# STORAGE DEEP DIVE

## the sqlite situation

- current: one big clanker.db with app-scoped tables
- problem: apps that need complex queries, different schemas, or just want full control
- solution: each app can create its own db in its vault
    - main clanker.db for core stuff: daemon state, permissions, profiles
    - apps get `data/{profile}/apps/{app}/db.sqlite` automatically
    - DB.for_app() points there by default
    - cross-app db queries: explicitly pass connection strings, or just don't do it
- joining across dbs: sqlite ATTACH works fine for read-only stuff
- keeps isolation clear, no weird table name collisions


## vault patterns i'm seeing

- config files: obvious, yml/json
- logs: apps writing their own logs beyond stdout
- cache: expensive api calls, don't want in db
- exports: generated files user might want (reports, websites, whatever)
- user content: the recipes, journal entries, whatever the app is about

thinking about vault structure conventions:
```
vault/{app}/
  config.yml          # app settings, editable by user
  state.yml           # runtime state, managed by app
  cache/              # temporary, can be nuked
  logs/               # app-managed logs (stdout goes to profile.app_log_file)
  exports/            # generated user-facing files
  content/            # the actual user data
    recipes/
    journal/
```

should this be enforced? no. but put it in examples and docs.


## permission system expansion

- current: grant_permission for vault read/write between apps
- future needs:
    - tool calling: "recipes app can call weather_get tool"
    - daemon access: "backup app can start/stop other daemons"
    - profile access: "sync app can read from multiple profiles"
- probably a permissions table: (requester_app, resource_type, resource_id, permission_type)
- keep it simple: check permissions at the tool/storage boundary, fail fast with clear errors
- user should be able to `clanker permissions list` and see who can do what


# TOOL SYSTEM REFINEMENTS

## tool output visibility

- right now: tool output goes to agent, agent summarizes for user
- problem: sometimes you want direct output (think `ls`, `grep`)
- idea: tool metadata could specify output_mode
    ```toml
    [tool.clanker.exports]
    search = {
      cmd = "python main.py search {query}",
      desc = "search entries",
      output_mode = "direct"  # or "agent_only", "structured"
    }
    ```
- direct: prints to console immediately, agent sees it too
- agent_only: current behavior
- structured: json/yaml output parsed for agent, formatted for user
- later problem: not later, actually important

## tool composition

- what if tools could call other tools?
- recipes_add might want to call weather_get to note "made on a rainy day"
- two approaches:
    1. apps can just call `clanker {tool}` via subprocess (works now, kinda ugly)
    2. tool context gets passed down: app code can import from clanker and call tools directly
- leaning toward 2, means apps can be more integrated
- but keep it optional, not required


## mcp bridge

- exporting clanker tools as mcp tools is cool
- but also: importing mcp tools into clanker?
- use case: user has claude desktop with some mcp servers, wants clanker to use them
- `clanker mcp import fetch` -> adds fetch as a tool in clanker context
- stored in profile somewhere, like `data/{profile}/mcp_tools.yml`
- clanker agent calls it by shelling out to mcp client? or native mcp support in clanker?
- not urgent but would make clanker play nice with ecosystem


# UX & INTERFACE IDEAS

## console improvements

- current: basic typer cli + agent console
- slash commands: `/tools`, `/apps`, `/status` instead of typing them out
    - with autocomplete showing available commands
    - not sure if typer can do this or need prompt_toolkit?
- command history that persists per profile
- colored output that doesn't suck (rich is fine but keep it minimal)
- agent working indicators: not just "thinking..." but "calling recipes_add" or whatever

## conversational polish

- clanker should feel natural to talk to
- avoid: "I've successfully completed the task" (robot voice)
- prefer: "done, added it to your recipes" (human voice)
- also avoid over-explaining unless user seems confused
- match user's tone: if they're terse, be terse back
- this is mostly prompt engineering but worth noting

## error messages that don't suck

- bad: "Error: NoneType object has no attribute 'get'"
- good: "couldn't find that recipe. here's what i do have: [list]"
- apps should return useful error messages in their tool outputs
- clanker should catch common errors and humanize them
- maybe a convention: apps return json with {success, data, error, help}
    - help field has "try this instead" suggestions


# APP ARCHITECTURE PATTERNS

## the agent app pattern

- some apps are just cli tools: in, out, done
- some apps are agents: recipes, assistant, probably others
- agent apps need:
    - conversational state (not the same as data state)
    - ability to ask clarifying questions
    - access to their own tool suite
    - handoff back to clanker when done
- thinking the protocol is:
    1. clanker calls agent app tool
    2. app realizes it needs conversation, returns {needs_conversation: true, context: ...}
    3. clanker spawns subagent with app's context + tools
    4. subagent does its thing, updates storage
    5. subagent returns {done: true, summary: "added chicken soup recipe"}
    6. clanker sees completion, summarizes to user
- or is this overengineered? maybe apps just always do what they can with inputs, return results
    - if something's ambiguous, return error asking for clarification
    - clanker relays it, user clarifies, calls again
- latter is simpler, former is more powerful. start with latter.


## daemon patterns

- daemon should be for:
    - servers (web apps, apis)
    - background processors (scraping, etl, monitoring)
    - scheduled tasks that run frequently
- daemon should NOT be for:
    - one-off jobs (use tools)
    - things that block on user input (use tools or agent)
- conventions:
    - daemon stdout/stderr goes to logs automatically
    - daemon can write to vault/db freely
    - daemon can't call clanker agent (no user to respond to)
    - daemon errors should be clear: crash = obvious, silent fail = includes health check
- health checks: optional, but recommended
    - `[tool.clanker.daemons.myworker]`
    - `command = "python worker.py"`
    - `health_check = "curl localhost:8000/health"` (optional)
    - clanker runs health check on interval, restarts if failing?


## the miniapp pattern

- not every app needs full structure
- sometimes you just want a single python script with one command
- support this:
    ```
    apps/weather/
      weather.py          # single file, no package
      pyproject.toml      # just exports, maybe requests as dep
    ```
- builds on uv's script support
- if you need more, refactor to full app
- don't make everything heavyweight by default


# SPECIFIC APP ELABORATIONS

## recipes app details

user adds recipes through conversation, app enforces format:
```yaml
---
title: Chicken Noodle Soup
source: "grandma"
source_url: null
added: 2025-01-15
tags: [soup, chicken, comfort-food]
difficulty: easy
time: 60
servings: 6
---

## Ingredients

- 1 whole chicken
- 2 cups egg noodles
- 4 carrots, diced
...

## Instructions

1. boil chicken in large pot...
```

the log system:
- `clanker that chicken soup was great, made it for 8 people`
- recipes app finds the most recent chicken soup recipe (or asks which one)
- appends to log section in the yaml:
```yaml
## Log

- 2025-01-16: made it for 8 people, turned out great
```

search should be fuzzy: "got anything with mushrooms and pasta"
- matches on title, ingredients, tags, instructions
- ranks by relevance
- shows most-made recipes higher (from log)

agent behavior:
- when adding: asks clarifying questions if recipe is vague
- "how long should it simmer?" instead of guessing
- when user references a recipe: matches by name, recency, or asks
- "which stew? you have beef stew and chicken stew"


## assistant app spec

the goal system needs to not be gtd busywork.

object types:
- **Goal**: something you want to accomplish. "launch new website", "learn rust"
    - status: planning | active | paused | done | dropped
    - timeline: optional start/end dates
    - linked to: workstreams, commitments
- **Workstream**: ongoing effort. "client work", "clanker development"
    - no end date, just active or not
    - groups related goals
- **Commitment**: you told someone you'd do something by sometime
    - who, what, when
    - linked to goals optionally
    - reminders fire based on due date
- **Reminder**: fire at time or based on trigger
    - "remind me friday to review designs"
    - "ping me if i haven't touched the recipes app in a week"

conversational intake examples:
- "i told bob i'd get him that report by friday"
    - -> creates Commitment(who: bob, what: report, when: friday)
    - -> asks: "is this for a specific goal?" or just links to current context
- "i'm working on the new recipes feature today"
    - -> checks if "recipes feature" is a Goal, creates if not
    - -> logs Interaction against that goal
- "actually push that to next tuesday"
    - -> finds most recent commitment/goal with a date
    - -> updates, logs Reschedule event

no manual field filling, the agent figures it out from conversation.

vault structure:
```
vault/assistant/
  goals/
    launch-new-website.md     # current state + history
    learn-rust.md
  workstreams/
    client-work.md
  daily/
    2025-01-15.md             # daily summary, auto-generated
```

db tables hold events, current state, relationships.
vault holds human-readable views.

cross-app hooks:
```python
# other apps can call this
assistant_summary(goal_id=None)  # returns current status
assistant_update(text="finished that thing")  # logs an interaction
```

auto-summaries:
- end of day: "here's what moved today"
- friday: "here's your week"
- triggered by query: "what's the status on website launch"


## finance/market app (smdata rebuild)

the actual useful bits:
- **data ingestion**: pull from apis (alpha vantage, twelve data, whatever)
    - cache aggressively in vault/cache
    - store processed in db
- **watch system**: track specific metrics/pairs
    - bollinger bands on (silver / btc)
    - "tell me when spy breaks 500"
    - stores watch configs in vault, eval engine in daemon
- **alerts**: fire when condition met
    - stdout to daemon log
    - optional push notification (later)
    - logs alert events to db for analysis
- **analysis tools**: commands for quick queries
    - "what's the correlation between btc and gold last 90 days"
    - "show me effr and tgcr for last week"
    - returns data + maybe a simple ascii chart

conversational:
- "add a watch on btc/usd crossing 50k"
- "has gold been correlated with spy lately"
- "what's the 50-day moving average on ethereum"

daemon runs watch checks every N minutes, logs violations.

vault structure:
```
vault/markets/
  config.yml         # api keys, refresh intervals
  watches/
    btc-usd-50k.yml
    silver-ratio.yml
  cache/
    btc-usd-daily.json
    gold-prices.json
```

later: jupyter notebook generation? "make me a chart of these three things"


# INSTALLATION & ONBOARDING

## the curl | sh problem

- want: `curl -sSL https://clanker.dev/install.sh | sh`
- installs uv if needed
- installs clanker package
- walks through:
    - profile creation (or use default)
    - api key setup (anthropic, openai, xai, whatever)
    - example app install
- ends with: "try: clanker hello"

but also concerned about:
- curl sh is scary to some users, good to many
- alternative: uv tool install clanker ?
- means clanker needs to be published to pypi
- which is fine, makes updates easier too

onboarding flow:
```bash
$ clanker init
Welcome to clanker!

Setting up your default profile...
Where should clanker store data? [~/.clanker/data]:
Which LLM providers do you want to use?
  [x] Anthropic (Claude)
  [ ] OpenAI
  [ ] XAI (Grok)

Enter your Anthropic API key: sk-...

Installing example app...
Done! Try: clanker example_add "went hiking today"
```

## docs & help

- `clanker help` should be actually helpful
    - not just list commands
    - "what do you want to do?" with examples
    - "learn more: https://clanker.dev/docs"
- docs site should have:
    - quickstart: 5 minutes to your first custom app
    - cookbook: common patterns (daemon, agent, tool composition)
    - api reference: generated from code
    - video: 2-minute walkthrough
- in-repo docs/ is for development notes, not user docs
    - user docs go on the site
    - keep this thoughts.md, architecture notes, etc in docs/dev_notes


# RANDOM TACTICAL THINGS

## stuff that's bugging me

- error handling in daemon management is verbose, should be more graceful
- profile system works but cli ux is meh: `clanker --profile dev` every time
    - maybe: `clanker profile switch dev` persists to a dotfile
    - then just `clanker stuff` uses active profile
- cli tool names: `clanker recipes_add` is functional but ugly
    - could support: `clanker recipes add` (with subcommands)
    - means app exports need to specify nesting?
    - or just teach users to think in tool names, not subcommands
- vault path resolution: sometimes confusing what's relative to
    - always absolute paths in code
    - user-facing: relative to vault root
- db schema migrations: punting on this but it will bite eventually
    - maybe apps include a migrations/ dir with numbered sql files?
    - clanker runs them on app update?
    - or just document "if you change schema, write a script"

## quick wins

- better logging: structlog or just json logs?
- config validation: pydantic models for app configs
- shell completions: typer supports this, just need to document
- vim mode in console: prompt_toolkit has this
- export conversation: save chat history to vault for later review


# MORE SCATTERED THOUGHTS

## why not just use X framework

- langchain: too much abstraction, magic, vendor lock-in vibes
- autogen: interesting but heavy, not the ux i want
- openinterpreter: close! but not extensible enough, no app isolation
- custom solution: keeps it simple, exactly what i need, fun to build

clanker's specific wins:
- apps in isolated uv environments
- storage conventions without being a database framework
- conversation as primary interface
- llm-agnostic (switch providers easily)
- actually small enough to understand the whole thing


## the multimodal future

- clanker should handle images, audio, video eventually
- vault already stores binary files fine
- tools could take/return media
- use case: "clanker add this screenshot to my design references"
    - -> vision model extracts info, tags it, stores in vault
- or: "clanker what's this song" with audio file
    - -> music recognition, adds to listening log
- not urgent but keep it in mind when designing tool interfaces


## clanker as an os?

- half-joking but: profiles are like user accounts
- apps are like programs
- vault is filesystem
- db is registry/system tables
- daemons are services
- agent is the shell

if you squint it's a little os for ai apps. interesting framing.
maybe markets it as "your personal ai operating environment"


## on complexity budgets

- every feature has a complexity cost
- some features are worth it: app isolation, tool system
- some aren't: elaborate permission ui, complex migrations
- rule: if it takes more than a paragraph to explain, think twice
- another rule: if i wouldn't use it daily, probably skip it
- stay small, stay useful


## names i workshopped and why clanker

- considered: forge, anvil, workshop, scaffold, lattice
- clanker because:
    - sounds mechanical, industrial
    - suggests building/making things
    - kinda weird, memorable
    - short, easy to type
    - .dev domain was available
- doesn't take itself too seriously which is good


## success metrics that matter

not:
- number of features
- lines of code
- github stars (ok maybe a little)

actually matters:
- can someone build a useful app in an afternoon?
- does it feel good to use?
- do i use it for real things?
- would i recommend it to a friend?

stay focused on that.