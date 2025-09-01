"""Profile management for clanker storage and configuration."""

import os
from pathlib import Path
from typing import Optional


class Profile:
    """Manages profile-specific paths for clanker storage.
    
    A profile determines where clanker stores its data, logs, and configuration.
    The active profile is determined by the CLANKER_PROFILE environment variable,
    defaulting to "default" if not set.
    """
    
    def __init__(self, name: Optional[str] = None):
        """Initialize profile with given name or from environment.
        
        Args:
            name: Profile name. If None, uses CLANKER_PROFILE env var or "default".
        """
        self.name = name or os.getenv("CLANKER_PROFILE", "default")
        self._project_root = self._find_project_root()
        self._data_root = self._project_root / "data" / self.name
        
        # Create profile directories if they don't exist
        self._ensure_directories()
    
    def _find_project_root(self) -> Path:
        """Find project root by looking for pyproject.toml or .git."""
        current = Path(__file__).resolve().parent
        
        while current != current.parent:
            if (current / "pyproject.toml").exists() or (current / ".git").exists():
                return current
            current = current.parent
        
        # Fallback to parent of src directory
        return Path(__file__).parent.parent.parent
    
    def _ensure_directories(self) -> None:
        """Create profile directories if they don't exist."""
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.vault_root.mkdir(parents=True, exist_ok=True)
    
    @property
    def data_root(self) -> Path:
        """Root directory for profile data."""
        return self._data_root
    
    @property
    def vault_root(self) -> Path:
        """Root directory for vault storage."""
        return self._data_root / "vault"
    
    @property
    def db_path(self) -> Path:
        """Path to the SQLite database."""
        return self._data_root / "clanker.db"
    
    @property
    def logs_dir(self) -> Path:
        """Directory for log files."""
        return self._data_root / "logs"
    
    @property
    def log_file(self) -> Path:
        """Path to the main clanker log file."""
        return self.logs_dir / "clanker.log"
    
    def app_log_file(self, app_name: str) -> Path:
        """Get path for app-specific log file.
        
        Args:
            app_name: Name of the app.
            
        Returns:
            Path to app's log file.
        """
        return self.logs_dir / f"{app_name}.log"
    
    @classmethod
    def current(cls) -> "Profile":
        """Get the current active profile.
        
        Returns:
            Profile instance for the current profile.
        """
        return cls()
    
    def __str__(self) -> str:
        """String representation of profile."""
        return f"Profile({self.name})"
    
    def __repr__(self) -> str:
        """Developer representation of profile."""
        return f"Profile(name={self.name!r}, data_root={self._data_root!s})"