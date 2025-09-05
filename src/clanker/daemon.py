"""Daemon management system for Clanker apps."""

import os
import signal
import subprocess
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
from datetime import datetime
import psutil

from .profile import Profile
from .logger import get_logger

logger = get_logger("daemon")


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
    
    def __init__(self, app_name: str, daemon_id: str, profile: Optional[Profile] = None):
        """Initialize daemon management.
        
        Args:
            app_name: Name of the app this daemon belongs to
            daemon_id: Unique identifier for this daemon within the app
            profile: Profile for storage paths (uses current if not provided)
        """
        self.app_name = app_name
        self.daemon_id = daemon_id
        self.profile = profile or Profile.current()
        
        self.pid_file = self.profile.daemons_dir / f"{app_name}_{daemon_id}.pid"
        self.log_file = self.profile.app_log_file(f"{app_name}_daemon_{daemon_id}")
        
        self._process = None
        self._should_stop = False
        
    def _register_daemon(self, pid: int, command: str) -> None:
        """Register daemon in the database."""
        with sqlite3.connect(self.profile.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO _daemons 
                (app_name, daemon_id, pid, status, command, started_at, last_heartbeat)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                self.app_name,
                self.daemon_id, 
                pid,
                DaemonStatus.RUNNING,
                command,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            conn.commit()
            
    def _mark_status(self, status: str, exit_code: Optional[int] = None) -> None:
        """Persist daemon status without removing row.

        Sets pid to NULL when stopped/crashed and records ended_at when terminal.
        """
        with sqlite3.connect(self.profile.db_path) as conn:
            ended_at = datetime.now().isoformat() if status in (DaemonStatus.STOPPED, DaemonStatus.CRASHED) else None
            # Ensure row exists
            conn.execute(
                """
                INSERT OR IGNORE INTO _daemons (app_name, daemon_id, pid, status, command, started_at, last_heartbeat)
                VALUES (?, ?, NULL, ?, NULL, NULL, ?)
                """,
                (self.app_name, self.daemon_id, status, datetime.now().isoformat())
            )
            # Update fields
            conn.execute(
                """
                UPDATE _daemons
                SET status = ?, last_heartbeat = ?, pid = CASE WHEN ? IS NULL THEN pid ELSE NULL END,
                    ended_at = COALESCE(?, ended_at), exit_code = COALESCE(?, exit_code)
                WHERE app_name = ? AND daemon_id = ?
                """,
                (
                    status,
                    datetime.now().isoformat(),
                    1 if status in (DaemonStatus.STOPPED, DaemonStatus.CRASHED) else None,
                    ended_at,
                    exit_code,
                    self.app_name,
                    self.daemon_id,
                ),
            )
            conn.commit()
            
    def _update_status(self, status: str) -> None:
        """Update daemon status in database."""
        with sqlite3.connect(self.profile.db_path) as conn:
            conn.execute("""
                UPDATE _daemons 
                SET status = ?, last_heartbeat = ?
                WHERE app_name = ? AND daemon_id = ?
            """, (status, datetime.now().isoformat(), self.app_name, self.daemon_id))
            conn.commit()
            
    def _heartbeat(self) -> None:
        """Update last heartbeat timestamp."""
        with sqlite3.connect(self.profile.db_path) as conn:
            conn.execute("""
                UPDATE _daemons 
                SET last_heartbeat = ?
                WHERE app_name = ? AND daemon_id = ?
            """, (datetime.now().isoformat(), self.app_name, self.daemon_id))
            conn.commit()
    
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
            except Exception:
                pass
            
            # Write PID file
            self.pid_file.write_text(str(self._process.pid))
            
            # Register in database
            command_str = ' '.join(str(c) for c in command)
            self._register_daemon(self._process.pid, command_str)
            
            logger.info(f"Started daemon {self.app_name}:{self.daemon_id} with PID {self._process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start daemon {self.app_name}:{self.daemon_id}: {e}")
            self._cleanup_files(status=DaemonStatus.STOPPED)
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
                        os.killpg(pid, signal.SIGTERM)
                    except Exception:
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
                        except Exception:
                            pass
                    if os.name != 'nt':
                        try:
                            os.killpg(pid, signal.SIGKILL)
                        except Exception:
                            pass
                    try:
                        process.kill()
                    except Exception:
                        pass
                    try:
                        rc = process.wait(timeout=5)
                        exit_code = rc
                    except Exception:
                        pass
            except psutil.NoSuchProcess:
                # Process already gone
                pass
            
            self._cleanup_files(status=DaemonStatus.STOPPED, exit_code=exit_code)
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
        if not self.pid_file.exists():
            return None
            
        try:
            pid = int(self.pid_file.read_text().strip())
            # Verify process is actually running
            psutil.Process(pid)
            return pid
        except (ValueError, psutil.NoSuchProcess):
            # PID file is stale
            self._cleanup_files(status=DaemonStatus.CRASHED)
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
        pid = self.get_pid()
        
        if not pid:
            return {
                'app_name': self.app_name,
                'daemon_id': self.daemon_id,
                'status': DaemonStatus.STOPPED,
                'pid': None,
                'uptime': None,
                'memory_mb': None,
                'cpu_percent': None
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
                'uptime': uptime,
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'cpu_percent': process.cpu_percent(interval=0.0)
            }
            
        except psutil.NoSuchProcess:
            # Mark as crashed and clean pid file
            self._cleanup_files(status=DaemonStatus.CRASHED)
            return {
                'app_name': self.app_name,
                'daemon_id': self.daemon_id,
                'status': DaemonStatus.CRASHED,
                'pid': None,
                'uptime': None,
                'memory_mb': None,
                'cpu_percent': None
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
    
    def _cleanup_files(self, status: str = DaemonStatus.STOPPED, exit_code: Optional[int] = None) -> None:
        """Clean up PID file and persist terminal status without deleting DB row."""
        if self.pid_file.exists():
            try:
                self.pid_file.unlink()
            except Exception:
                pass
        self._mark_status(status, exit_code=exit_code)


class DaemonManager:
    """Manager for all Clanker daemons."""
    
    def __init__(self, profile: Optional[Profile] = None):
        """Initialize daemon manager.
        
        Args:
            profile: Profile for storage (uses current if not provided)
        """
        self.profile = profile or Profile.current()
        # Ensure schema exists when manager is used standalone (outside agent)
        try:
            from .storage.schema import ensure_database_initialized
            ensure_database_initialized(self.profile)
        except Exception:
            pass
    
    @contextmanager
    def _db_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.profile.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def list_daemons(self) -> List[Dict[str, Any]]:
        """List all registered daemons with status.
        
        Returns:
            List of daemon status dictionaries
        """
        daemons: List[Dict[str, Any]] = []

        # Discover configured daemons from apps
        configs: Dict[str, Dict[str, str]] = {}
        apps_dir = Path("./apps")
        if apps_dir.exists():
            for item in apps_dir.iterdir():
                if not item.is_dir() or item.name.startswith(('_', '.')):
                    continue
                pyproject_path = item / "pyproject.toml"
                if not pyproject_path.exists():
                    continue
                try:
                    import tomllib
                    with open(pyproject_path, 'rb') as f:
                        pyproject = tomllib.load(f)
                    daemon_cfg = pyproject.get("tool", {}).get("clanker", {}).get("daemons", {})
                    if daemon_cfg:
                        configs[item.name] = dict(daemon_cfg)
                except Exception:
                    continue

        # Read DB rows for additional metadata
        db_rows: Dict[tuple, sqlite3.Row] = {}
        with self._db_connection() as conn:
            cur = conn.execute(
                "SELECT app_name, daemon_id, pid, status, command, started_at, last_heartbeat, exit_code, ended_at FROM _daemons"
            )
            for row in cur.fetchall():
                db_rows[(row['app_name'], row['daemon_id'])] = row

        # Merge discovered configs and DB rows
        keys = set(db_rows.keys()) | set(
            (app, daemon_id) for app, cfg in configs.items() for daemon_id in cfg.keys()
        )

        for app_name, daemon_id in sorted(keys):
            daemon = self.get_daemon(app_name, daemon_id)
            status = daemon.get_status()
            row = db_rows.get((app_name, daemon_id))
            status.update({
                'command': (configs.get(app_name, {}) or {}).get(daemon_id) or (row['command'] if row else None),
                'started_at': row['started_at'] if row else None,
                'last_heartbeat': row['last_heartbeat'] if row else None,
                'exit_code': row['exit_code'] if row else None,
                'ended_at': row['ended_at'] if row else None,
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
        return ClankerDaemon(app_name, daemon_id, self.profile)
    
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
        """Remove database entries for daemons that are no longer running.
        
        Returns:
            Number of entries cleaned up
        """
        cleaned = 0

        with self._db_connection() as conn:
            cursor = conn.execute("SELECT app_name, daemon_id, pid FROM _daemons")

            for row in cursor.fetchall():
                try:
                    if row['pid']:
                        psutil.Process(row['pid'])
                except psutil.NoSuchProcess:
                    # Mark as crashed and clear pid instead of deleting the row
                    conn.execute(
                        """
                        UPDATE _daemons
                        SET status = ?, pid = NULL, ended_at = ?, last_heartbeat = ?
                        WHERE app_name = ? AND daemon_id = ?
                        """,
                        (
                            DaemonStatus.CRASHED,
                            datetime.now().isoformat(),
                            datetime.now().isoformat(),
                            row['app_name'],
                            row['daemon_id'],
                        ),
                    )
                    cleaned += 1

            conn.commit()

        return cleaned

    # Autostart controls
    def set_autostart(self, app_name: str, daemon_id: str, enabled: bool) -> None:
        with self._db_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO _daemon_startup (app_name, daemon_id, enabled) VALUES (?, ?, ?)",
                (app_name, daemon_id, 1 if enabled else 0),
            )
            conn.commit()

    def get_autostart(self, app_name: str, daemon_id: str) -> bool:
        with self._db_connection() as conn:
            cur = conn.execute(
                "SELECT enabled FROM _daemon_startup WHERE app_name = ? AND daemon_id = ?",
                (app_name, daemon_id),
            )
            row = cur.fetchone()
            return bool(row['enabled']) if row else False

    def start_enabled_daemons(self) -> Dict[str, bool]:
        """Start all daemons marked enabled in _daemon_startup."""
        results: Dict[str, bool] = {}

        # Discover configs
        configs: Dict[str, Dict[str, str]] = {}
        apps_dir = Path("./apps")
        if apps_dir.exists():
            for item in apps_dir.iterdir():
                if not item.is_dir() or item.name.startswith(('_', '.')):
                    continue
                pyproject_path = item / "pyproject.toml"
                if not pyproject_path.exists():
                    continue
                try:
                    import tomllib
                    with open(pyproject_path, 'rb') as f:
                        pyproject = tomllib.load(f)
                    daemon_cfg = pyproject.get("tool", {}).get("clanker", {}).get("daemons", {})
                    if daemon_cfg:
                        configs[item.name] = dict(daemon_cfg)
                except Exception:
                    continue

        with self._db_connection() as conn:
            cur = conn.execute("SELECT app_name, daemon_id FROM _daemon_startup WHERE enabled = 1")
            for row in cur.fetchall():
                app = row['app_name']
                did = row['daemon_id']
                key = f"{app}:{did}"
                daemon = self.get_daemon(app, did)
                if daemon.is_running():
                    results[key] = True
                    continue
                cmd_template = (configs.get(app, {}) or {}).get(did)
                if not cmd_template:
                    results[key] = False
                    continue
                import shlex
                cmd = shlex.split(cmd_template)
                app_dir = Path("./apps") / app
                # Run under app's uv environment by convention
                uv_cmd = ["uv", "run", "--project", f"apps/{app}"] + cmd
                results[key] = daemon.start(uv_cmd, cwd=app_dir)

        return results
