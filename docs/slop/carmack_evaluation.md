# Clanker Project Review

## Snapshot
Clanker targets the right problem: wrangling many tiny AI-oriented utilities without letting dependencies or state bleed across boundaries. The foundations are lean, readable, and bias toward things that actually run. What is missing are the railings that keep the system on the rails when reality diverges from the ideal demo.

## Architecture
The split between core runtime in `src/clanker` and user apps in `apps/` is clean and keeps mental load low. Exporting commands and daemons through `pyproject.toml` is a clever way to stay declarative while still letting `uv` enforce isolation. Context generation from modular snippets is the highlight—it means you can grow documentation and live state independently. The weak side is that globals and singletons (`_agent`, module-level loggers, implicit profile directories) stitch the pieces together. That glue works for a single-process CLI, but it will fight you when you want headless services or concurrent sessions. A lightweight dependency injection hook or context object would help.

## Implementation Observations
Tool orchestration depends on fixed wiring inside `ClankerAgent` rather than a registry or dependency injection; adding a small hook layer—for example passing a context object through—would let alternate runtimes (daemon workers, services) reuse the same surface area without the current global lookups.

Message history currently grows without bound and lives only in memory, so any long console session can spike RAM and there is no persistence unless someone explicitly calls the save/load helpers. The agent replays message lists to extract tool calls twice; caching the parsed tool metadata (or teaching the model wrapper to expose it directly) would trim work on large transcripts.

Daemon supervision leans on PID files with psutil verification, which does catch stale PIDs in `get_pid()` but leaves follow-up rows sitting in `_daemons` unless someone runs cleanup. There is also no exponential backoff for crash loops, so a misconfigured daemon will thrash. Additional guardrails (grace periods, failure budget) would help.

Storage initialization (`ensure_database_initialized`) reconstructs the schema on every CLI invocation. Because `DatabaseSchema.init_database()` is idempotent that is safe, but it repeats file I/O and attach-time DDL that could short-circuit after the schema version check.

## Reliability and Testing
I did not see automated tests. For a framework executing shell commands, integration smoke tests are mandatory. You want to validate app discovery, export invocation, vault permissions, and daemon lifecycle. Logging is serviceable but fragmented—module-level `loguru` setup means console output, daemon logs, and background tooling may diverge. Centralize log configuration at startup and thread it through.

## Improvement Targets
1. Introduce a shared runtime context object to replace module globals so secondary processes can opt in without patching globals.
2. Persist or prune agent message history to cap memory while keeping session continuity.
3. Harden daemon management with stale PID detection, restart backoff, and explicit health reporting.
4. Cache database schema checks and vault setup so most CLI calls avoid redundant work.
5. Build a minimum integration test harness that scaffolds a sample app, runs exports via `uv`, and asserts storage isolation.

Clanker already demonstrates a practical bias—simple mechanisms, clear docs, runnable code. Tighten the control loops and add safety rails, and it will graduate from a promising prototype to a tool I would trust under automation.
