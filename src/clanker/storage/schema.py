"""Centralized database schema management for Clanker."""

import sqlite3
from pathlib import Path
from typing import Optional

from ..profile import Profile
from ..logger import get_logger

logger = get_logger("schema")

CURRENT_SCHEMA_VERSION = 1


class DatabaseSchema:
    """Manages the core Clanker system database schema.
    
    Note: Apps now use isolated per-app databases. This schema only
    manages core system tables for vault permissions and daemon tracking.
    """
    
    def __init__(self, profile: Optional[Profile] = None):
        """Initialize schema manager.
        
        Args:
            profile: Profile for database path (uses current if not provided)
        """
        self.profile = profile or Profile.current()
        self.db_path = self.profile.db_path
    
    def init_database(self) -> None:
        """Initialize the complete database schema.
        
        Creates all system tables required by Clanker core components.
        This should be called once during startup.
        """
        logger.info(f"Initializing database schema at {self.db_path}")
        
        with sqlite3.connect(self.db_path) as conn:
            # Schema version tracking for future migrations
            conn.execute("""
                CREATE TABLE IF NOT EXISTS _schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Cross-app vault file permissions (from storage/vault.py)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS _vault_permissions (
                    app_name TEXT NOT NULL,
                    target_app TEXT NOT NULL,
                    read INTEGER DEFAULT 0,
                    write INTEGER DEFAULT 0,
                    granted_by TEXT DEFAULT 'user',
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (app_name, target_app)
                )
            """)
            
            # Daemon tracking (from daemon.py)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS _daemons (
                    app_name TEXT NOT NULL,
                    daemon_id TEXT NOT NULL,
                    pid INTEGER,
                    status TEXT NOT NULL,
                    command TEXT,
                    started_at TEXT,
                    last_heartbeat TEXT,
                    PRIMARY KEY (app_name, daemon_id)
                )
            """)
            
            # Daemon startup preferences (from daemon.py)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS _daemon_startup (
                    app_name TEXT NOT NULL,
                    daemon_id TEXT NOT NULL,
                    enabled INTEGER DEFAULT 0,
                    PRIMARY KEY (app_name, daemon_id)
                )
            """)
            
            self._ensure_daemon_columns(conn)

            # Record current schema version
            conn.execute(
                "INSERT OR REPLACE INTO _schema_version (version, applied_at) VALUES (?, CURRENT_TIMESTAMP)",
                (CURRENT_SCHEMA_VERSION,),
            )

            conn.commit()

        logger.info("Database schema initialized successfully")

    def _ensure_daemon_columns(self, conn: sqlite3.Connection) -> None:
        """Ensure optional daemon tracking columns exist."""

        try:
            def _column_exists(table: str, column: str) -> bool:
                cur = conn.execute(f"PRAGMA table_info({table})")
                return any(row[1] == column for row in cur.fetchall())

            if not _column_exists("_daemons", "exit_code"):
                conn.execute("ALTER TABLE _daemons ADD COLUMN exit_code INTEGER")
            if not _column_exists("_daemons", "ended_at"):
                conn.execute("ALTER TABLE _daemons ADD COLUMN ended_at TEXT")
            if not _column_exists("_daemons", "failure_count"):
                conn.execute("ALTER TABLE _daemons ADD COLUMN failure_count INTEGER DEFAULT 0")
            if not _column_exists("_daemons", "last_failure_at"):
                conn.execute("ALTER TABLE _daemons ADD COLUMN last_failure_at TEXT")
        except Exception as e:
            logger.warning(f"Schema column ensure failed: {e}")
    
    def get_schema_version(self) -> Optional[int]:
        """Get current schema version.
        
        Returns:
            Current schema version, or None if not tracked
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT MAX(version) FROM _schema_version")
                result = cursor.fetchone()
                return result[0] if result and result[0] is not None else None
        except sqlite3.OperationalError:
            # Table doesn't exist yet
            return None
    
    def is_initialized(self) -> bool:
        """Check if database schema is initialized.
        
        Returns:
            True if schema is initialized, False otherwise
        """
        return self.get_schema_version() is not None


def init_database(profile: Optional[Profile] = None) -> None:
    """Initialize the Clanker database schema.
    
    This is the main entry point for schema initialization.
    
    Args:
        profile: Profile for database path (uses current if not provided)
    """
    schema = DatabaseSchema(profile)
    schema.init_database()


def ensure_database_initialized(profile: Optional[Profile] = None, force: bool = False) -> None:
    """Ensure database schema exists and is up-to-date (idempotent).

    Always runs initialization logic which safely creates missing tables and
    columns. Re-running is safe due to IF NOT EXISTS and column checks.

    Args:
        profile: Profile for database path (uses current if not provided)
        force: Run full initialization even if schema version is current
    """
    schema = DatabaseSchema(profile)
    if force:
        schema.init_database()
        return

    current_version = schema.get_schema_version()
    if current_version != CURRENT_SCHEMA_VERSION:
        schema.init_database()
        return

    # Lightweight check to ensure optional columns exist without re-running
    # full DDL each invocation.
    try:
        with sqlite3.connect(schema.db_path) as conn:
            schema._ensure_daemon_columns(conn)
            conn.commit()
    except Exception as e:
        logger.warning(f"Lightweight schema ensure failed, falling back to full init: {e}")
        schema.init_database()
