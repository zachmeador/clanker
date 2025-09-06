# CORE ARCHITECTURE & DESIGN

## what clanker does

- consistent and extendable scaffold for ai made applications
- common storage conventions, simple to understand
- provides context to ai cli tools and creates sessions when appropriate given a user request
- the clanker project acts as a development environment
- the clanker package is for core functionality
- it assumes highly of the user
- it assumes the user is using llms for nearly every possible task you can take in clanker
- central ui is an llm chat console
- other cli behavior spec:
    - clanker app list: list apps
    - clanker launch claude/cursor/gemini launches, say, a claude code instance with system context explaining clanker
        - `clanker launch claude need to add an app that tells me if the weather is blahblah` adds request as user request to CC. (i think this is possible)


# APP INTEGRATION & CONVENTIONS

## the big topic of what clanker apps are and how they integrate

- the user can always add an app to apps/, but they only get integrated into clanker's tool context if the user `export`s them through a clanker convention
    - user can export "functions" that are actually cli commands. the reason is clanker apps are in their own uv environment, with their own dependencies
- all exported app functionality to clanker should work as an llm tool
- example of what i'm imagining:
    - user: `clanker heres a paste of my grandma's chicken noodle soup recipe [blah], add it to my recipes`
    - clanker, having tools added, sees a `recipes_add` tool with a single string arg. 
    - clanker writes the recipe to the tool to the best of its ability
    - `recipes_add` takes it from there, provides some output back to clanker
    - clanker sees tool completion and says something to user
- clanker's example app should always be useful for understanding all of the main conventions

## out of scope things:
- daemons depending on others to be running
- ?


# OPEN QUESTIONS & CONSIDERATIONS

## need to think on

- what is a conversation in clanker?
    - user runs `clanker what are my apps` this is a conversation
    - multi-step: `clanker add a good spaghetti recipe` -> clanker responds conversationally with user `how's this? x` -> user approves
    - multi-agent-multi-step: when clanker runs an app that's an agent, the agent asks 
    - what is this fundamentally, functionally?
- a more thought-out app scaffolding. not going to do file boilerplating but maybe a simple example app showing most of the clanker api. an INSTRUCTIONS.md for the app. 
- leads me to think there at some point needs to be an automated process for building the INSTRUCTIONS.md's


# USER STORIES & USE CASES

## fake user "stories"

- semi-technical user types in `clanker make a fun geocities style website about penguins`. what happens? what are they expecting?

## for the non-technical people

- install and usage flow of clanker should be as easy as possible. a curl sh?
- guide users to getting api keys from providers


# FUTURE IDEAS

## later features / things to consider

- one single sqlite by default is really dumb
    - instead an app can create a clanker db stored in a profile
    - because how hard is it to join two sqlite dbs? not hard
- warming up to in-console slash commands. `tools` -> `/tools`. with a visual autocomplete for slash commands.
- mcp tool exporting.
    - would be a subset of the tools in clanker, and maybe some that are only mcp? not sure
- git worktree creation/management for cli tools
- clanker being usable in other contexts
    - clanker environment -> developing small apps in clanker
    - clanker cli, any CWD -> coding cli launcher, starting context manager? there's actually a lot of possibilities here. **
- at some point, giving clanker some code editing abilities will make sense. 
    - rn claude opus for planning -> grok-code-fast-1 for execution, is very powerful
- also thinking about a pattern of clanker moving the user to another agent console, rare but useful for a few things
- needs a web search and web fetch tool. or could just call a cli tool for this?

- later, what about an extremely simple console ui sdk? prefabs for a couple menu types or dialogs idk

- way later, probably refactor/redesign the console/tools modules

## really rough maybe ideas

- when clanker agent calls a tool, current ux is the output is only seen by the agent and the agent usually relays it back to the user.
    - always want this? thinking no, for having something like a mini-ui within the console. or just console prints with formatting.
    - and/or, a verbosity setting that ran show truncated output from the tool call
- and/or, custom ui widgets that can run in console, built on the fly by clanker through a tool call. like if a user needs to pick from a certain set of things, a menu basically.
    - simple, not a framework.
- convention for push notifications to a phone

## app ideas

- something like a fully automated obsidian vault with basic md publishing utilities. stores in vault, user could i guess point obsidian to that vault dir and use it that way too?
- user request: flashcard building from obsidian vault, other sources
- a weather app that knows the *exact* weather i like and tells me to go outside.
    - later, someday, work on a messaging system
- the actual recipe app i want:
    - would be agent-based, so clanker calling it would be a "subagent" i guess
    - stored in the vault, similar to obsidian's frontmatter format
    - strongly enforced formatting on all recipes, with comprehensive metadata on things i care about. use frontmatter for this.
    - a log system, so i can be like `clanker btw that recipe you made yesterday was really good. made it for lunch` 
        - -> calls recipe log tool -> logs verbatim line, with timestamp
        - does this get stored in the vault files? i think it should. concurrent writes probably won't be a thing. if they are a thing, clanker-vault should be hardened if possible.
    - ingredients and their quantities are formatted consistently
    - recipe source urls are included if they exist
    - later:
        - storing available ingredients, purchase date, expiration date. the latter 2 nullable
- rebuild of my old smdata project. finance data etl stuff basically. a few api providers for the source data. 
    - easy ways to call alerts, build various momentum metrics, more
    - `clanker add bollinger bands to all of my market feed transforms`
    - tgcr coefficients, effr, other related one

### recipes

... for when i get the recipes app migrated.

- chicken soup with rice
- beef barbacoa style roast, consomme rich gravy sorta thing
- marinated sliced mushrooms

### claude opus's takes on development workflows 9/5/2025:

- if a testing convention was done in clanker it would be the most low effort possible. like "hey clanker does my weather app work" and it just runs it for a few mins and tells you what broke. no jest configs or whatever
- development workflows: the agent-driven deployment thing is the key insight. "clanker my weather daemon is acting weird in prod" -> it switches you to a debug session, shows logs, maybe spins up a staging copy to compare
- mcp exporting is actually huge. clanker apps become tools for any mcp client, not just clanker itself. could be the distribution mechanism - your recipes app works in cursor, claude desktop, whatever
    - also tools that hit the clanker agent?

### claude opus's takes 9/4/2025:
```
  Additional scopes to consider:

  Inter-app communication - Beyond CLI exports, apps may need to share data/events. Consider a
  pub/sub system or shared message queue.

  App versioning/rollback - As apps evolve, you'll need migration strategies and the ability to
  pin/rollback versions.

  App marketplace/sharing - Enable users to share/discover apps. Git-based distribution? Package
  registry?

  Testing framework - Conventions for app testing, integration tests between apps, agent behavior
   testing.

  Observability - Centralized logging aggregation, metrics/telemetry, tracing requests across
  apps.

  Security boundaries - Network isolation options, secrets management beyond API keys,
  capability-based permissions.

  Development workflows - Hot reload for app development, staging/prod profiles, blue-green
  deployments for daemons.
```

my takes on those takes:
- a pubsub type thing could be interesting
- git and git worktrees seem like a crucial aspect of clanker, would be the answer to the versioning (at least the codebase)
    - db/vault migrations: out of scope, rare enough to not care about right now
- app modularity + easy install/manage ux will eventually be a thing but not important right now
- if a testing convention was done in clanker it would be the most low