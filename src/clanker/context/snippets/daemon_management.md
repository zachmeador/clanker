# Daemon Management

## Configuration
Daemons defined in app `pyproject.toml`:
```toml
[tool.clanker.daemons]
daemon_id = "python script.py --args"
```

## Commands
- `daemon_list()` - All daemons with status
- `daemon_start(app, daemon_id)` - Start daemon
- `daemon_stop(app, daemon_id)` - Stop daemon
- `daemon_logs(app, daemon_id)` - View logs
- `daemon_status(app, daemon_id)` - Check status
- `daemon_restart(app, daemon_id)` - Restart daemon
- `daemon_kill_all()` - Emergency stop all
- `daemon_enable_autostart(app, daemon_id)` - Enable autostart
- `daemon_start_enabled()` - Start autostart-enabled daemons

## Implementation
- Runs under `uv` in app environments: `uv run --project apps/{app} {command}`
- State tracked in Clanker DB: `_daemons` (runtime), `_daemon_startup` (autostart)
- PID files: `profile.daemons_dir/{app}_{daemon_id}.pid`
- Logs: `profile.app_log_file({app}_daemon_{daemon_id})`
- Graceful shutdown: SIGTERM → timeout → SIGKILL