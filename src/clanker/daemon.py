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
            
    def _unregister_daemon(self) -> None:
        """Remove daemon from database."""
        with sqlite3.connect(self.profile.db_path) as conn:
            conn.execute(
                "DELETE FROM _daemons WHERE app_name = ? AND daemon_id = ?",
                (self.app_name, self.daemon_id)
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
            self._process = subprocess.Popen(
                command,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                cwd=cwd,
                start_new_session=True,  # Detach from parent session
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            # Write PID file
            self.pid_file.write_text(str(self._process.pid))
            
            # Register in database
            command_str = ' '.join(str(c) for c in command)
            self._register_daemon(self._process.pid, command_str)
            
            logger.info(f"Started daemon {self.app_name}:{self.daemon_id} with PID {self._process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start daemon {self.app_name}:{self.daemon_id}: {e}")
            self._cleanup_files()
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
            try:
                process = psutil.Process(pid)
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=timeout)
                except psutil.TimeoutExpired:
                    logger.warning(f"Daemon {self.app_name}:{self.daemon_id} didn't stop gracefully, force killing")
                    process.kill()
                    process.wait(timeout=5)
                    
            except psutil.NoSuchProcess:
                # Process already gone
                pass
                
            self._cleanup_files()
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
            self._cleanup_files()
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
            
            return {
                'app_name': self.app_name,
                'daemon_id': self.daemon_id,
                'status': DaemonStatus.RUNNING,
                'pid': pid,
                'uptime': uptime,
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'cpu_percent': process.cpu_percent()
            }
            
        except psutil.NoSuchProcess:
            self._cleanup_files()
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
            with open(self.log_file, 'r') as f:
                all_lines = f.readlines()
                return [line.rstrip() for line in all_lines[-lines:]]
        except Exception as e:
            logger.error(f"Failed to read logs for {self.app_name}:{self.daemon_id}: {e}")
            return []
    
    def _cleanup_files(self) -> None:
        """Clean up PID file and database entry."""
        if self.pid_file.exists():
            self.pid_file.unlink()
        self._unregister_daemon()


class DaemonManager:
    """Manager for all Clanker daemons."""
    
    def __init__(self, profile: Optional[Profile] = None):
        """Initialize daemon manager.
        
        Args:
            profile: Profile for storage (uses current if not provided)
        """
        self.profile = profile or Profile.current()
    
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
        daemons = []
        
        with self._db_connection() as conn:
            cursor = conn.execute("""
                SELECT app_name, daemon_id, pid, status, command, started_at
                FROM _daemons
                ORDER BY app_name, daemon_id
            """)
            
            for row in cursor.fetchall():
                daemon = ClankerDaemon(row['app_name'], row['daemon_id'], self.profile)
                status = daemon.get_status()
                status.update({
                    'command': row['command'],
                    'started_at': row['started_at']
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
                    conn.execute(
                        "DELETE FROM _daemons WHERE app_name = ? AND daemon_id = ?",
                        (row['app_name'], row['daemon_id'])
                    )
                    cleaned += 1
            
            conn.commit()
        
        return cleaned