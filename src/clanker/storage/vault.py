import os
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import sqlite3
from contextlib import contextmanager

from ..profile import Profile


class AppVault:
    """Document storage context for a specific app.

    - Supports any file extension. Markdown (``.md``) and YAML (``.yml``/``.yaml``)
      are first-class: YAML is parsed/validated, Markdown is read/written as text.
      All other extensions are treated as opaque binary blobs (bytes only).
    - Enforces a simple cross-app permission model backed by SQLite. By default,
      an app can access its own vault without restrictions. Cross-app access
      requires an explicit permission grant recorded in the shared database.
    - The requester app is identified via the optional ``requester_app`` parameter
      or the ``CLANKER_REQUESTER_APP`` environment variable. If absent, the
      requester defaults to the same app, allowing intra-app access.
    - Files are stored under ``data/default/vault/<app_name>/...`` in the repository root.
    """
    
    def __init__(self, app_name: str, vault_root: Path, db_path: Path, requester_app: Optional[str] = None):
        self.app_name = app_name
        self.vault_root = vault_root
        self.app_root = vault_root / app_name
        self.db_path = db_path
        # Known text types receive intelligent handling; all other types are treated as opaque blobs.
        self._text_extensions = {'.yml', '.yaml', '.md'}
        
        # Identify requester for permission checks
        env_requester = os.getenv("CLANKER_REQUESTER_APP")
        self.requester_app = requester_app or env_requester or self.app_name
        
        # Create app directory if needed
        self.app_root.mkdir(parents=True, exist_ok=True)
    
    def _validate_path(self, path: str) -> Path:
        """Validate and resolve path within app's vault.

        Allows any file extension. Known text types (.md, .yml/.yaml) get special handling
        in read/write; all other types are handled as binary blobs.
        """
        # Convert to Path and normalize
        clean_path = Path(path)
        
        # Check for path traversal attempts
        try:
            # Resolve path relative to app root
            full_path = (self.app_root / clean_path).resolve()
            # Ensure it's within app root
            full_path.relative_to(self.app_root.resolve())
        except (ValueError, RuntimeError):
            raise ValueError(f"Invalid path: {path}")
        
        return full_path
    
    @contextmanager
    def _db_connection(self):
        """Get a database connection for permission checks."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()
    
    def _check_permission(self, requester_app: str, operation: str) -> bool:
        """Check if requester has permission to access this app's vault.

        operation must be one of {'read', 'write'}.
        """
        # Apps always have access to their own vault
        if requester_app == self.app_name:
            return True

        op_column = 'read' if operation == 'read' else 'write'
        with self._db_connection() as conn:
            cursor = conn.execute(
                f"""
                SELECT 1 FROM _vault_permissions 
                WHERE app_name = ? AND target_app = ? AND {op_column} = 1
                """,
                (requester_app, self.app_name)
            )
            return cursor.fetchone() is not None
    
    def _write_binary(self, full_path: Path, content: bytes) -> None:
        """Internal method to write binary content to a file."""
        if not isinstance(content, bytes):
            raise ValueError("Binary files must contain bytes content")
        full_path.write_bytes(content)
    
    def _read_binary(self, full_path: Path) -> bytes:
        """Internal method to read binary content from a file."""
        return full_path.read_bytes()
    
    def write(self, path: str, content: Union[str, Dict, List, bytes]) -> None:
        """Write content to a file in the vault.

        - .yml/.yaml: accepts dict/list (serialized) or str (validated YAML)
        - .md: accepts str only
        - others: accepts bytes only (blob storage)
        """
        full_path = self._validate_path(path)
        # Cross-app permission check (write)
        if not self._check_permission(self.requester_app, 'write'):
            raise PermissionError(f"App '{self.requester_app}' cannot write to vault '{self.app_name}'")
        
        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Blob handling for non-text types
        if full_path.suffix not in self._text_extensions or isinstance(content, bytes):
            if not isinstance(content, bytes):
                raise ValueError("Binary files must contain bytes content; use Markdown/YAML for text content")
            self._write_binary(full_path, content)
            return
        
        # Serialize based on file type
        if full_path.suffix in ['.yml', '.yaml']:
            if isinstance(content, str):
                # If string provided for YAML file, try to parse it first to validate
                try:
                    yaml.safe_load(content)
                    output = content
                except yaml.YAMLError as e:
                    raise ValueError(f"Invalid YAML content: {e}")
            else:
                output = yaml.dump(content, default_flow_style=False, sort_keys=False)
        else:  # .md
            if not isinstance(content, str):
                raise ValueError("Markdown files must contain string content")
            output = content
        
        full_path.write_text(output, encoding='utf-8')
    
    def read(self, path: str) -> Union[str, Dict, List, bytes]:
        """Read content from a file in the vault.

        Returns bytes for unknown file types; returns parsed YAML for .yml/.yaml and
        a string for .md files.
        """
        full_path = self._validate_path(path)
        # Cross-app permission check (read)
        if not self._check_permission(self.requester_app, 'read'):
            raise PermissionError(f"App '{self.requester_app}' cannot read from vault '{self.app_name}'")
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        # Binary for unknown types
        if full_path.suffix not in self._text_extensions:
            return self._read_binary(full_path)
        
        content = full_path.read_text(encoding='utf-8')
        
        # Parse based on file type
        if full_path.suffix in ['.yml', '.yaml']:
            try:
                return yaml.safe_load(content)
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML in {path}: {e}")
        else:  # .md
            return content
    
    def list(self, path: str = "") -> List[str]:
        """List files in a directory."""
        # Cross-app permission check (read)
        if not self._check_permission(self.requester_app, 'read'):
            raise PermissionError(f"App '{self.requester_app}' cannot list from vault '{self.app_name}'")
        if path:
            base_path = self.app_root / path
        else:
            base_path = self.app_root
        
        try:
            base_path = base_path.resolve()
            base_path.relative_to(self.app_root.resolve())
        except (ValueError, RuntimeError):
            raise ValueError(f"Invalid path: {path}")
        
        if not base_path.exists():
            return []
        
        files = []
        for item in base_path.rglob("*"):
            if item.is_file():
                # Return relative path from app root (use resolved paths)
                rel_path = item.resolve().relative_to(self.app_root.resolve())
                files.append(str(rel_path))
        
        return sorted(files)
    
    def delete(self, path: str) -> None:
        """Delete a file or directory from the vault."""
        # Cross-app permission check (write)
        if not self._check_permission(self.requester_app, 'write'):
            raise PermissionError(f"App '{self.requester_app}' cannot delete from vault '{self.app_name}'")
        if path:
            full_path = self.app_root / path
        else:
            raise ValueError("Cannot delete app root directory")
        
        try:
            full_path = full_path.resolve()
            full_path.relative_to(self.app_root.resolve())
        except (ValueError, RuntimeError):
            raise ValueError(f"Invalid path: {path}")
        
        if not full_path.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        
        if full_path.is_file():
            full_path.unlink()
        else:
            # Remove directory and all contents
            import shutil
            shutil.rmtree(full_path)
    
    def exists(self, path: str) -> bool:
        """Check if a file exists."""
        try:
            # Cross-app permission check (read)
            if not self._check_permission(self.requester_app, 'read'):
                return False
            full_path = self._validate_path(path)
            return full_path.exists()
        except ValueError:
            return False


class Vault:
    """Main document storage interface for clanker."""
    
    def __init__(self, profile: Optional[Profile] = None):
        # Use provided profile or get current one
        self.profile = profile or Profile.current()
        
        # Use profile paths
        self.vault_root = self.profile.vault_root
        self.db_path = self.profile.db_path
        
        # Create vault root if needed (profile already ensures this, but be safe)
        self.vault_root.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def for_app(cls, app_name: str, requester_app: Optional[str] = None) -> AppVault:
        """Get a vault context for a specific app with requester context.

        If requester_app is None, falls back to CLANKER_REQUESTER_APP env var,
        then defaults to app_name (intra-app access).
        """
        vault = cls()
        return AppVault(app_name, vault.vault_root, vault.db_path, requester_app=requester_app)
    
    def grant_permission(self, app_name: str, target_app: str, read: bool = False, write: bool = False) -> None:
        """Grant permissions to an app for another app's vault (for use by vault agent)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO _vault_permissions (app_name, target_app, read, write)
                VALUES (?, ?, ?, ?)
            """, (app_name, target_app, int(read), int(write)))
            conn.commit()
    
    def revoke_permission(self, app_name: str, target_app: str) -> None:
        """Revoke all permissions from an app for another app's vault (for use by vault agent)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM _vault_permissions WHERE app_name = ? AND target_app = ?",
                (app_name, target_app)
            )
            conn.commit()
    
    def list_permissions(self) -> List[Dict[str, Any]]:
        """List all vault permissions (for use by vault agent)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT app_name, target_app, read, write, granted_by, granted_at
                FROM _vault_permissions
                ORDER BY app_name, target_app
            """)
            return [dict(row) for row in cursor.fetchall()]