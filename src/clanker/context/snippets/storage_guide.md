# Storage Guide

## AppVault - File Storage
```python
from clanker.storage import AppVault

vault = AppVault("myapp", vault_root="./data/default/vault", db_path="./data/default/clanker.db")

# Write files
vault.write("config.yml", {"setting": "value"})
vault.write("data.json", my_data)

# Read files
config = vault.read("config.yml")  # Auto-parses YAML
data = vault.read("data.json")     # Auto-parses JSON
```

## AppDB - Database Storage
```python
from clanker.storage import AppDB

db = AppDB("myapp", db_path="./data/default/clanker.db")

# Create table
db.create_table("items", {
    "id": "INTEGER PRIMARY KEY",
    "name": "TEXT NOT NULL",
    "value": "TEXT"
})

# Insert data
db.insert("items", {"name": "test", "value": "data"})

# Query data
results = db.select("items", where="name = ?", params=("test",))
```

## Permissions
- Apps own their own storage by default
- Cross-app access requires permission grants:
  ```python
  vault.grant_permission("other-app", "read")
  ```
