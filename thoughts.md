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

### immediate tasks

- migrate old apps. redo/change the dumb parts.