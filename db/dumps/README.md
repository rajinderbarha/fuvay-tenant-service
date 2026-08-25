# Database dumps

`serviceos.sql` is a full `pg_dump` of the local ServiceOS database — schema
**and** data. It replaces committing `db/pgdata`, which cannot go in git: the
data directory is ~1.2 GB, is written live by a running cluster (so any copy is
a torn snapshot), and sits alongside a 323 MB installer zip and a 172 MB
pgAdmin binary that both exceed GitHub's 100 MB per-file limit.

## Restore

Into a fresh database:

```bash
# from the repo root, with the portable cluster running
db/pgsql/bin/createdb.exe  -U serviceos -h 127.0.0.1 serviceos_restored
db/pgsql/bin/psql.exe      -U serviceos -h 127.0.0.1 -d serviceos_restored \
                           -f db/dumps/serviceos.sql
```

Over the existing database (destructive — drops and recreates it):

```bash
db/pgsql/bin/dropdb.exe   -U serviceos -h 127.0.0.1 serviceos
db/pgsql/bin/createdb.exe -U serviceos -h 127.0.0.1 serviceos
db/pgsql/bin/psql.exe     -U serviceos -h 127.0.0.1 -d serviceos \
                          -f db/dumps/serviceos.sql
```

Password is taken from `PGPASSWORD` (`serviceos` locally).

The dump is written with `--no-owner --no-privileges`, so it restores under
whatever role you connect as rather than requiring the original `serviceos`
role to exist.

## Refresh the dump

```bash
db/pgsql/bin/pg_dump.exe -U serviceos -h 127.0.0.1 -d serviceos \
    --no-owner --no-privileges -f db/dumps/serviceos.sql
```

## Contains real data

This dump carries the contents of the `users` table — email addresses and
bcrypt password hashes among them. If this repository is ever public, or
becomes public, that data is exposed and stays in git history even after a
later delete. For a data-free alternative use `--schema-only`:

```bash
db/pgsql/bin/pg_dump.exe -U serviceos -h 127.0.0.1 -d serviceos \
    --schema-only --no-owner --no-privileges -f db/dumps/schema.sql
```
