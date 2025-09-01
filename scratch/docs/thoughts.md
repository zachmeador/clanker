### key changes from the old claudio app

- there's a central agent, developed with the pydantic-ai framework. user provides their model preference and api keys for the coordinator. 
- the coordinator known as "clanker" runs applications and passes args.
- run `clanker [query]`
    - user can say "i want to build an app that does blah" and clanker will delegate this to a default or user specified llm dev tool, like claude code, gemini-cli, others, your own, etc.
    - user can say "i want to [do some thing that an app in this environment can do]" and clanker will smartly route to an llm chat, or run the app directly.
- convention for the cli interfaces will be to use typer. need to migrate.
- dir structure tweaks. check this project's structure and ensure code aligns

### need to think on

- if tools should be made for apps, as interfaces, or if it's just context construction + terminal use tools
- how much clanker wants to be another llm chat cli app (it doesn't at all)
- api key management. i want simple and assume high user capability. apps and clanker will use this.
- there's a great pattern idea in my head. clanker scaffolds out an app, creates the dir and stuff, then creates a llm-cli instance with a custom context explaining, then the user continues developing with that.
    - when clanker is prompted to work on a new app? 
- there needs to be a central abstraction for the available model types to clanker and its apps. a smart and simple design for knowing what ai providers the user has given clanker, and what their available models are. 
- there needs to be a central simple abstraction for logging. use loguru i guess because it's clean.
- a universal way to always have something like a CLAUDE.md
- on `clanker` run it should check what apps exist
    - we need some sort of SIMPLE app abstraction

### boring things

- cli interface in apps should be typer by default

### needs

- a simple constructor for project instructions. example: if user launcher claude code through clanker, CLAUDE.mds could be constructed. maybe have an INSTRUCTIONS.md in a dir, this gets copied into that dir's CLAUDE.md? not a fan of duplicating data but this would be git ignored
- a comprehensive context for the app scaffold. ie what gets provided to the cli tool spawned from clanker.

### immediate tasks

- migrate old apps. redo/change the dumb parts.

# more thoughts

what clanker does

- consistent and extendable scaffold for ai made applications
- common storage conventions, simple to understand
- provides context to ai cli tools and creates sessions when appropriate given a user request
- the clanker project acts as a development environment
- the clanker package is for core functionality
- it assumes highly of the user
- it assumes the user is using llms for nearly every possible task you can take in clanker
- central ui is an llm chat
    - so far this is a pain in the ass to think about. i almost want to hand off everything possible to ai cli tools if their context controls their behavior well enough
- other cli behavior spec:
    - clanker app list: list apps
    - clanker profile list/set/add/remove (or something like that)
    - clanker launch claude/cursor/gemini launches, say, a claude code instance with system context explaining clanker
        - `clanker launch claude need to add an app that tells me if the weather is blahblah` adds request as user request to CC. (i think this is possible)
    - the user can obviously also ask clanker to do these things for them
- clanker has tool access
    - unsure yet if i want to give a general bash tool or specific tools

what clanker doesn't do

- duplicate effort having its own chat tui. there are other llm clis.
- have an advanced ui for app management or other clanker things. 

# fake user "stories"

- semi-technical user types in `clanker make a fun geocities style website about penguins`. what happens? what are they expecting?