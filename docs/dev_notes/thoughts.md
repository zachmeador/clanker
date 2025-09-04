### key changes from the old claudio app

- there's a central agent, developed with the pydantic-ai framework. user provides their model preference and api keys for the coordinator. 
- the coordinator known as "clanker" runs applications and passes args.
- run `clanker [query]`
    - user can say "i want to build an app that does blah" and clanker will delegate this to a default or user specified llm dev tool, like claude code, gemini-cli, others, your own, etc.
    - user can say "i want to [do some thing that an app in this environment can do]" and clanker will smartly route to an llm chat, or run the app directly.

### implemented, mostly?
- simple centralized api key management with model routing based on provider avail
    - needs some minor refining probably
- there's a great pattern idea in my head. clanker scaffolds out an app, creates the dir and stuff, then creates a llm-cli instance with a custom context explaining, then the user continues developing with that.
    - when clanker is prompted to work on a new app? 
- cli tool launching with starting context + creation of context docs (CLAUDE.md)

### need to think on

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



# later features / things to consider

- git worktree creation/management for cli tools
- clanker being modular in its scope
    - clanker environment -> developing small apps in clanker
    - clanker cli, any CWD -> coding cli launcher, starting context manager? 
- at some point, giving clanker some code editing abilities will make sense. rn in cursor claude opus for planning -> grok-code-fast-1 for execution, is very powerful. 
- later, thinking about ways to make integrations or external databases have clanker conventions.

## app ideas

- something like a fully automated obsidian vault with basic md publishing utilities. stores in vault, user could i guess point obsidian to that vault dir and use it that way too?
- a silly weather app that knows that *exact* weather i like and tells me to go outside.

### recipes

... for when i get the recipes app migrated.

- chicken soup with rice

## for the non-technical people

- install and usage flow of clanker should be as easy as possible. a curl sh?
- guide users to getting api keys from providers

# daemons

- daemon session management. i don't think we want a monolithic schedule or loop. yeah we definitely don't. 
    - task scheduling. if a clanker user wants an app that does some thing like checking if the weather is some combination of things, that needs to run on a schedule. 
    
- user can do `clanker what apps are running rn` and clanker calls some tool that checks the clanker app daemons
- apps use the clanker library to stand up their own simple and easy to tear down loops. clanker apps stick to a tight (but lightweight) convention

example app that runs at x interval, checks some weather apis, logs it to the vault. simple scheduler, but it should be a service unique to the app.

"bbbut why not have just one service handle all of this??" because it's like, kB of ram? who cares? this is cleaner and isn't tightly coupled

but. clanker needs to be robust and work consistently in all environments. if the user wants an app daemon to run at system startup, there should be conventions for this and it should be seamless, a config switch.

the primary way the user interacts with clanker is by its agent. so a user can do `clanker kill all running daemons please`, `clanker what daemons are running`
- then reserved keywords in the cli: `clanker daemon [list, etc]`
- so obviously that means the current tools system needs new tools
    - and discoverability logic for seeing if an app has 
- daemons log to data/[profile]/logs/ to their own log files. does basic rotation.

the apps themselves, for now, don't need a cli for daemon management. the user can add those if they want.

## out of scope things:
- daemons depending on others to be running
- ?