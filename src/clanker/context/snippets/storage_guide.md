# Storage Guide

## Vault - File Storage
```python
from clanker.storage import Vault

vault = Vault.for_app("myapp")

# Write files
vault.write("config.yml", {"setting": "value"})
vault.write("data.json", my_data)

# Read files
config = vault.read("config.yml")  # Auto-parses YAML
data = vault.read("data.json")     # Auto-parses JSON

# List files
files = vault.list()  # All files in app vault
files = vault.list("subfolder")  # Files in subfolder
```

## DB - Database Storage
```python
from clanker.storage import DB

db = DB.for_app("myapp")  # Isolated database per app

# Create table (in app's isolated database)
db.create_table("items", {
    "id": "INTEGER PRIMARY KEY",
    "name": "TEXT NOT NULL",
    "value": "TEXT"
})

# Insert data
db.insert("items", {"name": "test", "value": "data"})

# Query data
results = db.query("items", {"name": "test"})
```

## Cross-App Access
Apps have isolated storage by default:

- **Vault**: Cross-app access with explicit permissions
- **Database**: Each app has its own isolated SQLite database

```python
# Vault cross-app access (with permissions)
vault = Vault()
vault.grant_permission("requester-app", "target-app", read=True, write=False)

# Access another app's vault
vault = Vault.for_app("target-app", requester_app="requester-app")
data = vault.read("shared-config.yml")

# Database isolation - no cross-app access
db = DB.for_app("myapp")  # Uses data/default/apps/myapp/db.sqlite
```

## Storage Types
- **Vault**: Files (.yml/.yaml auto-parsed, .md as text, others as binary)
- **DB**: Isolated SQLite database per app at `data/<profile>/apps/<app>/db.sqlite`
