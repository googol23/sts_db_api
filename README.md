# STS DB API

Small Python utilities for connecting to and inspecting the STS PostgreSQL database.
The core API has no dependencies on other STS workspace packages.

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
from sts_db_api.db_api import get_conn, list_tables

connection = get_conn()
try:
    print(list_tables(connection))
finally:
    connection.close()
```

## Optional optical-metrology file grouping

`sts_db_api.metrology_measurements.fetch_measurements` reconstructs measured marker
or surface coordinates, converts the optical-table frame to the CBM frame, clusters
points by ladder module, and associates those clusters with the top-to-bottom module
order from PostgreSQL.

This utility is opt-in so the core database API does not eagerly import numerical
packages. Install its additional dependencies only when needed:

```sh
python -m pip install numpy scikit-learn
```

```python
from sts_db_api.metrology_measurements import fetch_measurements

measurements = fetch_measurements("L4DL000161", "/u/dlmeas/STS/L4DL000161")
```

The module does not import `sts_geo_layout`, `sts_ladder_metrology`, or any other
workspace package.
