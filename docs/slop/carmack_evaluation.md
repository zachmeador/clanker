# Clanker Project Review

## Snapshot
Clanker targets the right problem: wrangling many tiny AI-oriented utilities without letting dependencies or state bleed across boundaries. The foundations are lean, readable, and bias toward things that actually run. What is missing are the railings that keep the system on the rails when reality diverges from the ideal demo.

## Architecture
The split between core runtime in `src/clanker` and user apps in `apps/` is clean and keeps mental load low. Exporting commands and daemons through `pyproject.toml` is a clever way to stay declarative while still letting `uv` enforce isolation. Context generation from modular snippets is the highlight—it means you can grow documentation and live state independently. The weak side is that globals and singletons (`_agent`, module-level loggers, implicit profile directories) stitch the pieces together. That glue works for a single-process CLI, but it will fight you when you want headless services or concurrent sessions. A lightweight dependency injection hook or context object would help.

## Implementation Observations
`ClankerAgent` is mostly adapter code on top of `pydantic-ai`. That keeps surface area small but makes latency and memory scaling dependent on a third-party library you do not control. Message history is stored unbounded in memory; long console sessions will leak. Tool call parsing walks the message list twice—cache the extracted calls and reuse them. Daemon supervision leans on PID files and signal handling, which is fine, yet there is no cleanup for stale PIDs or for processes that exit before writing a PID. Starting every enabled daemon on each CLI invocation is convenient, but a misconfigured daemon will spin up and die repeatedly. Add exponential backoff or a failure budget. Storage init (`ensure_database_initialized`) runs on every CLI invocation; it should short-circuit once the schema is validated.

## Reliability and Testing
I did not see automated tests. For a framework executing shell commands, integration smoke tests are mandatory. You want to validate app discovery, export invocation, vault permissions, and daemon lifecycle. Logging is serviceable but fragmented—module-level `loguru` setup means console output, daemon logs, and background tooling may diverge. Centralize log configuration at startup and thread it through.

## Improvement Targets
1. Introduce a shared runtime context object to replace module globals so secondary processes can opt in without patching globals.
2. Persist or prune agent message history to cap memory while keeping session continuity.
3. Harden daemon management with stale PID detection, restart backoff, and explicit health reporting.
4. Cache database schema checks and vault setup so most CLI calls avoid redundant work.
5. Build a minimum integration test harness that scaffolds a sample app, runs exports via `uv`, and asserts storage isolation.

Clanker already demonstrates a practical bias—simple mechanisms, clear docs, runnable code. Tighten the control loops and add safety rails, and it will graduate from a promising prototype to a tool I would trust under automation.
