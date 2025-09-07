import sqlite3
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from contextlib import contextmanager


class AppDB:
    """Database context for a specific app with isolated storage."""
    
    def __init__(self, app_name: str, db_path: Path):
        self.app_name = app_name
        self.db_path = db_path
        self._conn = None
        self._identifier_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
        self._sql_type_pattern = re.compile(r'^(INTEGER|TEXT|REAL|BLOB|NULL|NUMERIC|BOOLEAN)(\s+PRIMARY\s+KEY)?(\s+NOT\s+NULL)?$', re.IGNORECASE)
    
    def _validate_identifier(self, name: str, identifier_type: str = "identifier") -> None:
        """Validate SQL identifier to prevent injection."""
        if not self._identifier_pattern.match(name):
            raise ValueError(f"Invalid {identifier_type}: '{name}'. Must match [a-zA-Z_][a-zA-Z0-9_]*")
    
    def _validate_sql_type(self, sql_type: str) -> None:
        """Validate SQL column type."""
        if not self._sql_type_pattern.match(sql_type.strip()):
            raise ValueError(f"Invalid SQL type: '{sql_type}'")
    
    @contextmanager
    def _connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    
    def create_table(self, table_name: str, schema: Dict[str, str]) -> None:
        """Create a table in the app's database."""
        if not schema:
            raise ValueError("Schema cannot be empty")
        
        self._validate_identifier(table_name, "table name")
        
        columns = []
        for col_name, col_type in schema.items():
            self._validate_identifier(col_name, "column name")
            self._validate_sql_type(col_type)
            columns.append(f"{col_name} {col_type}")
        
        with self._connection() as conn:
            conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})")
            conn.commit()
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """Insert a row into a table."""
        self._validate_identifier(table, "table name")
        
        columns = list(data.keys())
        for col in columns:
            self._validate_identifier(col, "column name")
        
        placeholders = ["?" for _ in columns]
        
        with self._connection() as conn:
            cursor = conn.execute(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})",
                list(data.values())
            )
            conn.commit()
            return cursor.lastrowid
    
    def query(self, table: str, conditions: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Query rows from a table."""
        self._validate_identifier(table, "table name")
        
        query = f"SELECT * FROM {table}"
        params = []
        
        if conditions:
            for col in conditions.keys():
                self._validate_identifier(col, "column name")
            where_clauses = [f"{k} = ?" for k in conditions.keys()]
            query += f" WHERE {' AND '.join(where_clauses)}"
            params = list(conditions.values())
        
        with self._connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def update(self, table: str, data: Dict[str, Any], conditions: Dict[str, Any]) -> int:
        """Update rows in a table."""
        self._validate_identifier(table, "table name")
        
        if not data or not conditions:
            raise ValueError("Both data and conditions must be provided")
        
        for col in data.keys():
            self._validate_identifier(col, "column name")
        for col in conditions.keys():
            self._validate_identifier(col, "column name")
        
        set_clauses = [f"{k} = ?" for k in data.keys()]
        where_clauses = [f"{k} = ?" for k in conditions.keys()]
        
        query = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {' AND '.join(where_clauses)}"
        params = list(data.values()) + list(conditions.values())
        
        with self._connection() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.rowcount
    
    def delete(self, table: str, conditions: Dict[str, Any]) -> int:
        """Delete rows from a table."""
        self._validate_identifier(table, "table name")
        
        if not conditions:
            raise ValueError("Conditions must be provided for delete operations")
        
        for col in conditions.keys():
            self._validate_identifier(col, "column name")
        
        where_clauses = [f"{k} = ?" for k in conditions.keys()]
        query = f"DELETE FROM {table} WHERE {' AND '.join(where_clauses)}"
        
        with self._connection() as conn:
            cursor = conn.execute(query, list(conditions.values()))
            conn.commit()
            return cursor.rowcount
    
    def tables(self) -> List[str]:
        """List all tables in the app's database."""
        with self._connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            return sorted([row[0] for row in cursor.fetchall()])


class DB:
    """Main database interface for clanker."""
    
    def __init__(self, profile: Optional['Profile'] = None):
        """Initialize database interface.
        
        Args:
            profile: Profile for database path (uses current if not provided)
        """
        from ..profile import Profile
        self.profile = profile or Profile.current()
        self.db_path = self.profile.db_path
    
    @classmethod
    def for_app(cls, app_name: str, profile: Optional['Profile'] = None) -> AppDB:
        """Get a database context for a specific app with isolated storage."""
        db = cls(profile)
        app_db_path = db.profile.app_db_path(app_name)
        return AppDB(app_name, app_db_path)
    
