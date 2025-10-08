lots of questions around pydantic-ai's ease around controlling the prompts from query to query

## what clanker is doing

- user sends a query
    - query is likely just text.
    - later concern, not now: iamges/audio
- model sends a response
- user sends a query with the previous context

clanker assembles the full query, the user query is a part

tokens in, tokens out

