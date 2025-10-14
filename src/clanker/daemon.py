"""Daemon management system for Clanker apps."""

import os
import signal
import subprocess
import sqlite3
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager
from datetime import datetime, timedelta
import psutil

from .profile import Profile
from .runtime import RuntimeContext, get_runtime_context
from .logger import get_logger

logger = get_logger("daemon")

FAILURE_BACKOFF_SCHEDULE = (5, 30, 120, 600)


class DaemonStatus:
    """Daemon status constants."""
    STOPPED = "stopped"
    RUNNING = "running"
    CRASHED = "crashed"
    STARTING = "starting"
    STOPPING = "stopping"


class ClankerDaemon:
    """Base class for Clanker app daemons.
    
    Provides lifecycle management, PID tracking, logging, and graceful shutdown
    for background processes in Clanker apps.
    """
    
    def __init__(
        self,
        app_name: str,
        daemon_id: str,
        profile: Optional[Profile] = None,
        runtime: Optional[RuntimeContext] = None,
    ):
        """Initialize daemon management.
        
        Args:
            app_name: Name of the app this daemon belongs to
            daemon_id: Unique identifier for this daemon within the app
            profile: Profile for storage paths (uses current if not provided)
        """
        self.app_name = app_name
        self.daemon_id = daemon_id
        self.runtime = runtime or get_runtime_context()
        self.profile = profile or self.runtime.profile
        
        self.pid_file = self.profile.daemons_dir / f"{app_name}_{daemon_id}.pid"
        self.log_file = self.profile.app_log_file(f"{app_name}_daemon_{daemon_id}")
        self.state_file = self.profile.daemons_dir / f"{app_name}_{daemon_id}.json"

        self._process = None
        self._should_stop = False

    def _load_state(self) -> dict:
        """Load daemon state from JSON file."""
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text())
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load state from {self.state_file}: {e}")
        return {
            "status": DaemonStatus.STOPPED,
            "pid": None,
            "command": None,
            "started_at": None,
            "last_heartbeat": None,
            "exit_code": None,
            "ended_at": None,
            "failure_count": 0,
            "last_failure_at": None
        }

    def _save_state(self, state: dict) -> None:
        """Save daemon state to JSON file."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.state_file.write_text(json.dumps(state, indent=2))
        except OSError as e:
            logger.error(f"Failed to save state to {self.state_file}: {e}")

    def _register_daemon(self, pid: int, command: str) -> None:
        """Register daemon in state file."""
        state = self._load_state()
        now = datetime.now().isoformat()
        state.update({
            "pid": pid,
            "status": DaemonStatus.RUNNING,
            "command": command,
            "started_at": now,
            "last_heartbeat": now,
            "failure_count": 0,
            "last_failure_at": None
        })
        self._save_state(state)

    def _mark_status(self, status: str, exit_code: Optional[int] = None, *, reset_failures: bool = False) -> None:
        """Persist daemon status to state file.

        Sets pid to NULL when stopped/crashed and records ended_at when terminal.
        """
        state = self._load_state()
        now = datetime.now().isoformat()
        ended_at = now if status in (DaemonStatus.STOPPED, DaemonStatus.CRASHED) else state.get("ended_at")

        # Update state
        clear_pid = status in (DaemonStatus.STOPPED, DaemonStatus.CRASHED)
        state.update({
            "status": status,
            "last_heartbeat": now,
            "pid": None if clear_pid else state.get("pid"),
            "ended_at": ended_at,
            "exit_code": exit_code
        })

        if status == DaemonStatus.CRASHED:
            state["failure_count"] = state.get("failure_count", 0) + 1
            state["last_failure_at"] = now

        if reset_failures:
            state["failure_count"] = 0
            state["last_failure_at"] = None

        self._save_state(state)
            
    def _update_status(self, status: str) -> None:
        """Update daemon status in state file."""
        state = self._load_state()
        state["status"] = status
        state["last_heartbeat"] = datetime.now().isoformat()
        self._save_state(state)

    def _heartbeat(self) -> None:
        """Update last heartbeat timestamp."""
        state = self._load_state()
        state["last_heartbeat"] = datetime.now().isoformat()
        self._save_state(state)
    
    def start(self, command: List[str], cwd: Optional[Path] = None) -> bool:
        """Start the daemon process.
        
        Args:
            command: Command and arguments to run
            cwd: Working directory for the process
            
        Returns:
            True if started successfully, False otherwise
        """
        if self.is_running():
            logger.warning(f"Daemon {self.app_name}:{self.daemon_id} is already running")
            return False
            
        try:
            # Ensure directories exist
            self.pid_file.parent.mkdir(parents=True, exist_ok=True)
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Open log file for daemon output
            log_handle = open(self.log_file, 'a')
            
            # Start process in new session (daemonize)
            creationflags = 0
            if os.name == 'nt':
                # Best-effort detach and allow group control on Windows
                CREATE_NEW_PROCESS_GROUP = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x00000200)
                DETACHED_PROCESS = getattr(subprocess, 'DETACHED_PROCESS', 0x00000008)
                creationflags = CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS

            self._process = subprocess.Popen(
                command,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                cwd=cwd,
                start_new_session=(os.name != 'nt'),  # Detach from parent session on POSIX
                creationflags=creationflags if os.name == 'nt' else 0,
            )

            try:
                # Close parent's reference; child keeps the FD
                log_handle.close()
            except Exception as e:
                logger.debug(f"Failed to close log handle: {e}")
            
            # Write PID file
            self.pid_file.write_text(str(self._process.pid))
            
            # Register in database
            command_str = ' '.join(str(c) for c in command)
            self._register_daemon(self._process.pid, command_str)
            
            logger.info(f"Started daemon {self.app_name}:{self.daemon_id} with PID {self._process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start daemon {self.app_name}:{self.daemon_id}: {e}")
            self._cleanup_files(status=DaemonStatus.CRASHED)
            return False
    
    def stop(self, timeout: int = 10) -> bool:
        """Stop the daemon gracefully.
        
        Args:
            timeout: Seconds to wait before force-killing
            
        Returns:
            True if stopped successfully, False otherwise
        """
        pid = self.get_pid()
        if not pid:
            logger.info(f"Daemon {self.app_name}:{self.daemon_id} is not running")
            self._cleanup_files()
            return True
            
        try:
            self._update_status(DaemonStatus.STOPPING)
            
            # Try graceful shutdown first
            exit_code: Optional[int] = None
            try:
                process = psutil.Process(pid)
                if os.name != 'nt':
                    # Send SIGTERM to the whole process group
                    try:
                        pgid = os.getpgid(pid)
                        os.killpg(pgid, signal.SIGTERM)
                    except Exception as e:
                        logger.debug(f"Failed to send SIGTERM to process group of {pid}: {e}")
                        process.terminate()
                else:
                    process.terminate()

                # Wait for graceful shutdown
                try:
                    rc = process.wait(timeout=timeout)
                    exit_code = rc
                except psutil.TimeoutExpired:
                    logger.warning(f"Daemon {self.app_name}:{self.daemon_id} didn't stop gracefully, force killing")
                    # Kill children first to avoid orphans
                    for child in process.children(recursive=True):
                        try:
                            child.kill()
                        except Exception as e:
                            logger.debug(f"Failed to kill child process {child.pid}: {e}")
                    if os.name != 'nt':
                        try:
                            pgid = os.getpgid(pid)
                            os.killpg(pgid, signal.SIGKILL)
                        except Exception as e:
                            logger.debug(f"Failed to send SIGKILL to process group of {pid}: {e}")
                    try:
                        process.kill()
                    except Exception as e:
                        logger.debug(f"Failed to kill process {pid}: {e}")
                    try:
                        rc = process.wait(timeout=5)
                        exit_code = rc
                    except Exception as e:
                        logger.debug(f"Process {pid} still not responding after SIGKILL: {e}")
            except psutil.NoSuchProcess:
                # Process already gone
                pass
            
            self._cleanup_files(status=DaemonStatus.STOPPED, exit_code=exit_code, reset_failures=True)
            logger.info(f"Stopped daemon {self.app_name}:{self.daemon_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop daemon {self.app_name}:{self.daemon_id}: {e}")
            return False
    
    def get_pid(self) -> Optional[int]:
        """Get the PID of the running daemon.

        Returns:
            PID if daemon is running, None otherwise
        """
        state = self._load_state()
        pid = state.get("pid")

        if not pid:
            return None

        try:
            # Verify process is actually running
            psutil.Process(pid)
            return pid
        except psutil.NoSuchProcess:
            # Process is not running, update state
            self._mark_status(DaemonStatus.CRASHED)
            return None
    
    def is_running(self) -> bool:
        """Check if daemon is currently running.
        
        Returns:
            True if daemon is running, False otherwise
        """
        return self.get_pid() is not None
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed daemon status information.

        Returns:
            Dictionary with status, PID, uptime, etc.
        """
        state = self._load_state()
        pid = state.get("pid")

        if not pid:
            return {
                'app_name': self.app_name,
                'daemon_id': self.daemon_id,
                'status': state.get("status", DaemonStatus.STOPPED),
                'pid': None,
                'command': state.get("command"),
                'started_at': state.get("started_at"),
                'last_heartbeat': state.get("last_heartbeat"),
                'exit_code': state.get("exit_code"),
                'ended_at': state.get("ended_at"),
                'failure_count': state.get("failure_count", 0)
            }

        try:
            process = psutil.Process(pid)
            create_time = process.create_time()
            uptime = time.time() - create_time
            # Update heartbeat whenever we positively observe the process
            self._heartbeat()

            return {
                'app_name': self.app_name,
                'daemon_id': self.daemon_id,
                'status': DaemonStatus.RUNNING,
                'pid': pid,
                'command': state.get("command"),
                'started_at': state.get("started_at"),
                'last_heartbeat': state.get("last_heartbeat"),
                'uptime': uptime,
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'cpu_percent': process.cpu_percent(interval=0.1),
                'exit_code': state.get("exit_code"),
                'ended_at': state.get("ended_at"),
                'failure_count': state.get("failure_count", 0)
            }

        except psutil.NoSuchProcess:
            # Mark as crashed
            self._mark_status(DaemonStatus.CRASHED)
            return {
                'app_name': self.app_name,
                'daemon_id': self.daemon_id,
                'status': DaemonStatus.CRASHED,
                'pid': None,
                'command': state.get("command"),
                'started_at': state.get("started_at"),
                'last_heartbeat': state.get("last_heartbeat"),
                'exit_code': state.get("exit_code"),
                'ended_at': datetime.now().isoformat(),
                'failure_count': state.get("failure_count", 0) + 1
            }
    
    def get_logs(self, lines: int = 50) -> List[str]:
        """Get recent log lines from daemon.
        
        Args:
            lines: Number of lines to return
            
        Returns:
            List of log lines
        """
        if not self.log_file.exists():
            return []
            
        try:
            # Efficient tail: read up to last ~64KB to avoid loading huge files
            max_bytes = 64 * 1024
            with open(self.log_file, 'rb') as f:
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                read_size = min(max_bytes, file_size)
                f.seek(-read_size, os.SEEK_END)
                chunk = f.read(read_size)
            text = chunk.decode(errors='replace')
            all_lines = text.splitlines()
            return all_lines[-lines:]
        except Exception as e:
            logger.error(f"Failed to read logs for {self.app_name}:{self.daemon_id}: {e}")
            return []
    
    def _cleanup_files(
        self,
        status: str = DaemonStatus.STOPPED,
        exit_code: Optional[int] = None,
        *,
        reset_failures: bool = False,
    ) -> None:
        """Clean up PID file and persist terminal status."""
        if self.pid_file.exists():
            try:
                self.pid_file.unlink()
            except Exception as e:
                logger.debug(f"Failed to remove PID file {self.pid_file}: {e}")
        self._mark_status(status, exit_code=exit_code, reset_failures=reset_failures)


class DaemonManager:
    """Manager for all Clanker daemons."""

    def __init__(self, profile: Optional[Profile] = None, runtime: Optional[RuntimeContext] = None):
        """Initialize daemon manager.

        Args:
            profile: Profile for storage (uses current if not provided)
        """
        self.runtime = runtime or get_runtime_context()
        self.profile = profile or self.runtime.profile
    
    def list_daemons(self) -> List[Dict[str, Any]]:
        """List all registered daemons with status.

        Returns:
            List of daemon status dictionaries
        """
        daemons: List[Dict[str, Any]] = []

        # Discover configured daemons from registry manifests
        try:
            from .tools import discover_daemon_configs
            configs: Dict[str, Dict[str, str]] = discover_daemon_configs()
        except Exception:
            configs = {}

        # Find all daemon state files
        daemon_state_files = []
        if self.profile.daemons_dir.exists():
            for state_file in self.profile.daemons_dir.glob("*_*.json"):
                # Parse app_name_daemon_id.json format
                filename = state_file.stem  # Remove .json extension
                if '_' in filename:
                    parts = filename.split('_', 1)
                    if len(parts) == 2:
                        app_name, daemon_id = parts
                        daemon_state_files.append((app_name, daemon_id, state_file))

        # Also check configured daemons that might not have state files yet
        for app_name, app_configs in configs.items():
            for daemon_id in app_configs.keys():
                if not any((app_name, daemon_id) == (a, d) for a, d, _ in daemon_state_files):
                    daemon_state_files.append((app_name, daemon_id, None))

        for app_name, daemon_id, state_file in sorted(daemon_state_files):
            daemon = self.get_daemon(app_name, daemon_id)
            status = daemon.get_status()
            status.update({
                'command': (configs.get(app_name, {}) or {}).get(daemon_id) or status.get('command'),
            })
            daemons.append(status)

        return daemons
    
    def get_daemon(self, app_name: str, daemon_id: str) -> ClankerDaemon:
        """Get daemon instance.
        
        Args:
            app_name: App name
            daemon_id: Daemon ID
            
        Returns:
            ClankerDaemon instance
        """
        return ClankerDaemon(app_name, daemon_id, self.profile, runtime=self.runtime)
    
    def stop_all_daemons(self) -> Dict[str, bool]:
        """Stop all running daemons.
        
        Returns:
            Dictionary mapping daemon name to success status
        """
        results = {}
        
        for daemon_info in self.list_daemons():
            if daemon_info['status'] == DaemonStatus.RUNNING:
                daemon = self.get_daemon(daemon_info['app_name'], daemon_info['daemon_id'])
                key = f"{daemon_info['app_name']}:{daemon_info['daemon_id']}"
                results[key] = daemon.stop()
        
        return results
    
    def cleanup_stale_entries(self) -> int:
        """Clean up state files for daemons that are no longer running.

        Returns:
            Number of entries cleaned up
        """
        cleaned = 0

        if not self.profile.daemons_dir.exists():
            return cleaned

        for state_file in self.profile.daemons_dir.glob("*_*.json"):
            try:
                # Parse app_name_daemon_id.json format
                filename = state_file.stem
                if '_' in filename:
                    parts = filename.split('_', 1)
                    if len(parts) == 2:
                        app_name, daemon_id = parts

                        # Load state and check if process is still running
                        state = json.loads(state_file.read_text())
                        pid = state.get('pid')

                        if pid:
                            try:
                                psutil.Process(pid)
                            except psutil.NoSuchProcess:
                                # Mark as crashed
                                state['status'] = DaemonStatus.CRASHED
                                state['pid'] = None
                                state['ended_at'] = datetime.now().isoformat()
                                state['last_heartbeat'] = datetime.now().isoformat()
                                state['failure_count'] = state.get('failure_count', 0) + 1
                                state_file.write_text(json.dumps(state, indent=2))
                                cleaned += 1

            except (json.JSONDecodeError, OSError):
                # If we can't parse the state file, remove it
                try:
                    state_file.unlink()
                    cleaned += 1
                except OSError:
                    pass

        return cleaned

    # Autostart controls
    def set_autostart(self, app_name: str, daemon_id: str, enabled: bool) -> None:
        """Set autostart configuration for a daemon."""
        autostart_file = self.profile.daemons_dir / f"{app_name}_{daemon_id}_autostart.json"
        autostart_file.parent.mkdir(parents=True, exist_ok=True)
        autostart_file.write_text(json.dumps({"enabled": enabled}))

    def get_autostart(self, app_name: str, daemon_id: str) -> bool:
        """Get autostart configuration for a daemon."""
        autostart_file = self.profile.daemons_dir / f"{app_name}_{daemon_id}_autostart.json"
        if autostart_file.exists():
            try:
                data = json.loads(autostart_file.read_text())
                return data.get("enabled", False)
            except (json.JSONDecodeError, OSError):
                pass
        return False

    def _next_restart_time(self, failure_count: int, last_failure_at: Optional[str]) -> Optional[datetime]:
        if failure_count <= 0 or not last_failure_at:
            return None
        try:
            last = datetime.fromisoformat(last_failure_at)
        except ValueError:
            return None
        index = min(failure_count - 1, len(FAILURE_BACKOFF_SCHEDULE) - 1)
        delay_seconds = FAILURE_BACKOFF_SCHEDULE[index]
        return last + timedelta(seconds=delay_seconds)

    def start_enabled_daemons(self) -> Dict[str, bool]:
        """Start all daemons marked enabled for autostart."""
        results: Dict[str, bool] = {}

        # Discover configs from registry manifests
        try:
            from .tools import discover_daemon_configs
            configs: Dict[str, Dict[str, str]] = discover_daemon_configs()
        except Exception:
            configs = {}

        # Find all autostart configuration files
        autostart_configs = []
        if self.profile.daemons_dir.exists():
            for autostart_file in self.profile.daemons_dir.glob("*_*_autostart.json"):
                try:
                    data = json.loads(autostart_file.read_text())
                    if data.get("enabled", False):
                        # Parse app_name_daemon_id_autostart.json format
                        filename = autostart_file.stem  # Remove .json
                        parts = filename.split('_', 2)  # Split into 3 parts max
                        if len(parts) >= 2:
                            app_name = parts[0]
                            daemon_id = parts[1]
                            autostart_configs.append((app_name, daemon_id, autostart_file))
                except (json.JSONDecodeError, OSError):
                    continue

        for app_name, daemon_id, autostart_file in autostart_configs:
            key = f"{app_name}:{daemon_id}"
            daemon = self.get_daemon(app_name, daemon_id)

            if daemon.is_running():
                results[key] = True
                continue

            cmd_template = (configs.get(app_name, {}) or {}).get(daemon_id)
            if not cmd_template:
                results[key] = False
                continue

            # Check failure backoff
            state = daemon._load_state()
            failure_count = state.get('failure_count', 0)
            last_failure_at = state.get('last_failure_at')

            next_time = self._next_restart_time(failure_count, last_failure_at)
            if next_time and datetime.now() < next_time:
                logger.warning(
                    f"Skipping restart for {key}; failure_count={failure_count}, retry after {next_time.isoformat()}"
                )
                results[key] = False
                continue

            import shlex
            cmd = shlex.split(cmd_template)
            app_dir = Path("./apps") / app_name
            # Run under app's uv environment by convention
            uv_cmd = ["uv", "run", "--project", f"apps/{app_name}"] + cmd
            results[key] = daemon.start(uv_cmd, cwd=app_dir)

        return results
