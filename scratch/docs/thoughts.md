### key changes from the old claudio app

- there's a central agent, developed with the pydantic-ai framework. user provides their model preference and api keys for the coordinator. 
- the coordinator known as "clanker" runs applications and passes args.
- run `clanker [query]`
    - user can say "i want to build an app that does blah" and clanker will delegate this to a default or user specified llm dev tool, like claude code, gemini-cli, others, your own, etc.
    - user can say "i want to [do some thing that an app in this environment can do]" and clanker will smartly route to an llm chat, or run the app directly.

### need to think on

- if tools should be made for apps, as interfaces, or if it's just context construction + terminal use tools
- how much clanker wants to be another llm chat cli app (it doesn't at all)
- api key management. i want simple and assume high user capability. apps and clanker will use this.
- there's a great pattern idea in my head. clanker scaffolds out an app, creates the dir and stuff, then creates a llm-cli instance with a custom context explaining, then the user continues developing with that.
    - when clanker is prompted to work on a new app? 
- there needs to be a central abstraction for the available model types to clanker and its apps. a smart and simple design for knowing what ai providers the user has given clanker, and what their available models are. 
- a universal way to always have something like a CLAUDE.md. INSTRUCTIONS.md could be the general term.
- what is a conversation in clanker?
    - user runs `clanker what are my apps` this is a conversation
    - multi-step: `clanker add a good spaghetti recipe` -> clanker responds conversationally with user `how's this? x` -> user approves
    - multi-agent-multi-step: when clanker runs an app that's an agent, the agent asks 
    - what is this fundamentally, functionally?

#### the big topic of what clanker apps are and how they integrate

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

what i DON'T want:

- clanker apps to have their own 
    - console tui
    - cli additions to clanker (unnecessary rn, current functionality)
    - to be designed to be called by humans directly

the user is free to do whatever but this is not convention.

### needs

- a simple constructor for project instructions. example: if user launcher claude code through clanker, CLAUDE.mds could be constructed. maybe have an INSTRUCTIONS.md in a dir, this gets copied into that dir's CLAUDE.md? not a fan of duplicating data but this would be git ignored
- a comprehensive context for the app scaffold. ie what gets provided to the cli tool spawned from clanker.

# more thoughts

what clanker does

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

# fake user "stories"

- semi-technical user types in `clanker make a fun geocities style website about penguins`. what happens? what are they expecting?