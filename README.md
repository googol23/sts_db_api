# STS Database Utilities

Small Python utilities for connecting to and inspecting the STS PostgreSQL database.

## Requirements

- Python 3.10+
- `psycopg2` (for example, `python -m pip install psycopg2-binary`)

## Configuration

Create a local credentials file from the provided example:

```sh
cp db_credentials.example.json db_credentials.json
chmod 600 db_credentials.json
```

Fill in the connection settings in `db_credentials.json`. This file is ignored by Git and, on POSIX systems, must be owned by the current user with permissions `0600`.

The `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD` environment variables override values from the file. Set `DB_CREDENTIALS_FILE` to use a different credentials file.

## Usage

```python
from db_api import get_conn, list_tables

connection = get_conn()
try:
    print(list_tables(connection))
finally:
    connection.close()
```
