### key changes from the old claudio app

- there's a central agent, developed with the marvin framework (pydantic-ai wrapper, very clean). user provides their model preference and api keys for the coordinator. 
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

### immediate tasks

- migrate old apps. redo/change the dumb parts.