# Example Journal App

A personal journal application demonstrating all major Clanker features:
- **Vault storage** for markdown journal entries 
- **Database storage** for entry metadata and search indexing
- **Daemon service** for background daily summarization
- **CLI exports** making all commands available as AI tools

## Features

### Core Commands
- `add` - Add new journal entries with hashtag support
- `list` - Display recent entries with rich formatting
- `search` - Search entries by content, tags, or summary
- `stats` - Show comprehensive journal statistics  
- `backup` - Export all entries to timestamped JSON

### Background Daemon
The `summarizer` daemon runs daily to:
- Generate summaries of previous day's entries
- Extract and catalog hashtags used
- Store summaries in the vault as markdown files
- Track daemon status and health

## Storage Architecture

### Vault Usage
```
vault/
├── entries/
│   ├── {uuid}.md       # Individual journal entries with YAML frontmatter
├── summaries/
│   ├── daily_summary_2024-01-15.md  # Generated daily summaries
└── backups/
    ├── journal_backup_20240115_143022.json  # JSON backup files
```

### Database Schema
```sql
CREATE TABLE entries (
    entry_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    tags TEXT,              -- Comma-separated hashtags
    summary TEXT            -- First 100 characters
);
```

## Usage Examples

### Adding Entries
```bash
# Add a simple entry
python main.py add "Had a great day at work today!"

# Add entry with hashtags for categorization
python main.py add "Finished the big project! #work #achievement #deadline"

# Multi-line entries work too
python main.py add "Went for a long hike today.

The weather was perfect and the views were amazing. 
Definitely need to do this more often. #hiking #nature #wellness"
```

### Viewing and Searching
```bash
# Show recent entries
python main.py list --count 3

# Search by hashtag
python main.py search "#work"

# Search by content
python main.py search "hiking"

# View statistics
python main.py stats
```

### Backup and Export
```bash
# Create backup file
python main.py backup
# Creates: journal_backup_20240115_143022.json
```

## Daemon Management

Start the background summarizer:
```bash
# Through clanker daemon system
clanker daemon_start example summarizer

# Or directly (for testing)
python daemon.py --once
```

The daemon will:
1. Run every 24 hours (configurable)
2. Find entries from the previous day
3. Generate markdown summaries with statistics
4. Extract and categorize all hashtags used
5. Store results in vault under `summaries/`

## AI Tool Integration

When exported through Clanker, all commands become available as AI tools:

- `example_add(entry="...")` - Add journal entries via AI
- `example_search(query="...")` - AI can search your journal
- `example_stats()` - AI can get statistics about your writing
- `example_list(count=5)` - AI can show recent entries
- `example_backup()` - AI can trigger backups

## Technical Implementation

This app demonstrates:

1. **Dual Storage Pattern**: Vault for content, DB for metadata
2. **YAML Frontmatter**: Structured metadata in markdown files  
3. **Database Indexing**: Fast search through metadata fields
4. **Background Processing**: Daemon for automated tasks
5. **Rich CLI**: Professional command-line interface
6. **Error Handling**: Graceful failure modes
7. **Data Export**: JSON backup format for portability

The implementation shows how to build a full-featured app using Clanker's storage abstractions while maintaining data portability and search performance.