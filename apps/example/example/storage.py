"""Storage operations for the journal app using both Vault and DB."""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import re

from clanker.storage import Vault, DB


class JournalStorage:
    """Handles journal entry storage using Clanker's Vault and DB systems."""
    
    def __init__(self):
        """Initialize storage systems."""
        self.vault = Vault.for_app("example")
        self.db = DB.for_app("example")
        self._ensure_database_schema()
    
    def _ensure_database_schema(self):
        """Ensure the journal entries table exists."""
        self.db.create_table("entries", {
            "entry_id": "TEXT PRIMARY KEY",
            "created_at": "TEXT NOT NULL",
            "word_count": "INTEGER NOT NULL",
            "tags": "TEXT",  # Comma-separated tags
            "summary": "TEXT"  # First 100 chars
        })
    
    def add_entry(self, content: str) -> str:
        """Add a new journal entry.
        
        Stores content in Vault as markdown, metadata in DB.
        
        Args:
            content: The journal entry text
            
        Returns:
            The entry ID
        """
        entry_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Extract metadata
        word_count = len(content.split())
        tags = self._extract_tags(content)
        summary = content[:100].replace('\n', ' ').strip()
        
        # Create markdown with frontmatter
        markdown_content = f"""---
entry_id: {entry_id}
created_at: {timestamp}
word_count: {word_count}
tags: {tags}
---

{content}
"""
        
        # Store in vault as markdown
        self.vault.write(f"entries/{entry_id}.md", markdown_content)
        
        # Store metadata in database
        self.db.insert("entries", {
            "entry_id": entry_id,
            "created_at": timestamp,
            "word_count": word_count,
            "tags": tags,
            "summary": summary
        })
        
        return entry_id
    
    def get_recent_entries(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get the most recent journal entries.
        
        Args:
            count: Number of entries to return
            
        Returns:
            List of entry metadata dictionaries
        """
        # Query from database ordered by creation date
        all_entries = self.db.query("entries")
        # Sort by created_at descending
        sorted_entries = sorted(all_entries, key=lambda x: x['created_at'], reverse=True)
        return sorted_entries[:count]
    
    def get_entry_content(self, entry_id: str) -> str:
        """Get the content of a journal entry.
        
        Args:
            entry_id: The entry ID
            
        Returns:
            The entry content (without frontmatter)
        """
        try:
            # Read from vault
            content = self.vault.read(f"entries/{entry_id}.md")
            
            # Strip frontmatter
            if content.startswith("---"):
                # Find the end of frontmatter
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    return parts[2].strip()
            
            return content.strip()
            
        except FileNotFoundError:
            return f"Content not found for entry {entry_id}"
    
    def search_entries(self, query: str) -> List[Dict[str, Any]]:
        """Search entries by content or tags.
        
        Args:
            query: Search term
            
        Returns:
            List of matching entry metadata
        """
        query_lower = query.lower()
        matching_entries = []
        
        # Get all entries from database
        all_entries = self.db.query("entries")
        
        for entry in all_entries:
            # Check if query matches tags
            if query_lower in entry['tags'].lower():
                matching_entries.append(entry)
                continue
            
            # Check if query matches summary
            if query_lower in entry['summary'].lower():
                matching_entries.append(entry)
                continue
                
            # Check full content
            try:
                content = self.get_entry_content(entry['entry_id'])
                if query_lower in content.lower():
                    matching_entries.append(entry)
            except:
                continue
        
        # Sort by created_at descending
        return sorted(matching_entries, key=lambda x: x['created_at'], reverse=True)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get journal statistics.
        
        Returns:
            Dictionary with various statistics
        """
        all_entries = self.db.query("entries")
        
        if not all_entries:
            return {
                'total_entries': 0,
                'total_words': 0,
                'avg_words': 0,
                'first_entry': None,
                'last_entry': None,
                'entries_this_month': 0
            }
        
        # Calculate statistics
        total_entries = len(all_entries)
        total_words = sum(entry['word_count'] for entry in all_entries)
        avg_words = total_words / total_entries if total_entries > 0 else 0
        
        # Sort by date
        sorted_entries = sorted(all_entries, key=lambda x: x['created_at'])
        first_entry = sorted_entries[0]['created_at'].split('T')[0]  # Just the date part
        last_entry = sorted_entries[-1]['created_at'].split('T')[0]
        
        # Count entries this month
        current_month = datetime.now().strftime('%Y-%m')
        entries_this_month = sum(1 for entry in all_entries 
                                if entry['created_at'].startswith(current_month))
        
        return {
            'total_entries': total_entries,
            'total_words': total_words,
            'avg_words': avg_words,
            'first_entry': first_entry,
            'last_entry': last_entry,
            'entries_this_month': entries_this_month
        }
    
    def create_backup(self) -> str:
        """Create a complete backup of all journal data stored in vault.
        
        Returns:
            The backup filename
        """
        all_entries = self.db.query("entries")
        backup_data = {
            'created_at': datetime.now().isoformat(),
            'total_entries': len(all_entries),
            'entries': []
        }
        
        for entry in all_entries:
            entry_data = dict(entry)  # Copy metadata
            # Add full content
            try:
                entry_data['content'] = self.get_entry_content(entry['entry_id'])
            except:
                entry_data['content'] = f"[Content not found for entry {entry['entry_id']}]"
            
            backup_data['entries'].append(entry_data)
        
        # Sort entries by created_at
        backup_data['entries'].sort(key=lambda x: x['created_at'])
        
        # Save to vault (auto-serializes to JSON)
        backup_filename = f"backups/journal_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.vault.write(backup_filename, backup_data)
        
        return backup_filename
    
    def _extract_tags(self, content: str) -> str:
        """Extract hashtags from content.
        
        Args:
            content: The journal entry text
            
        Returns:
            Comma-separated tags string
        """
        # Find all hashtags (#word)
        tags = re.findall(r'#(\w+)', content)
        # Remove duplicates and sort
        unique_tags = sorted(set(tag.lower() for tag in tags))
        return ', '.join(unique_tags) if unique_tags else ''