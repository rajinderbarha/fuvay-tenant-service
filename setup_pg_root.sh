#!/bin/bash
set -e

echo "=== ServiceOS PostgreSQL Setup ==="

# 1. Create serviceos role and database
su -c "psql -c \"DO \\\$\\\$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'serviceos') THEN CREATE USER serviceos WITH PASSWORD 'serviceos' CREATEDB LOGIN; END IF; END \\\$\\\$;\"" postgres
echo "User created/verified."

su -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname = 'serviceos'\" | grep -q 1 || createdb -O serviceos serviceos" postgres
echo "Database created/verified."

su -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE serviceos TO serviceos;\"" postgres
su -c "psql -d serviceos -c \"GRANT ALL ON SCHEMA public TO serviceos;\"" postgres
echo "Privileges granted."

# 2. Create extensions
su -c "psql -d serviceos -c \"CREATE EXTENSION IF NOT EXISTS \\\"uuid-ossp\\\"; CREATE EXTENSION IF NOT EXISTS pgcrypto;\"" postgres
echo "Extensions created."

# 3. Configure listen_addresses to accept all connections
PG_CONF="/etc/postgresql/17/main/postgresql.conf"
if grep -q "#listen_addresses = 'localhost'" "$PG_CONF"; then
    sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_CONF"
elif grep -q "listen_addresses = 'localhost'" "$PG_CONF"; then
    sed -i "s/listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_CONF"
fi
grep "listen_addresses" "$PG_CONF" | head -2
echo "listen_addresses configured."

# 4. Add pg_hba.conf entries for host connections
PG_HBA="/etc/postgresql/17/main/pg_hba.conf"
if ! grep -q "host all all 0.0.0.0/0 md5" "$PG_HBA"; then
    echo "# ServiceOS: allow all host connections with md5" >> "$PG_HBA"
    echo "host all all 0.0.0.0/0 md5" >> "$PG_HBA"
    echo "host all all ::/0 md5" >> "$PG_HBA"
    echo "pg_hba.conf updated."
else
    echo "pg_hba.conf already has host rules."
fi

# 5. Reload PostgreSQL
su -c "pg_ctlcluster 17 main reload" postgres
echo "PostgreSQL reloaded."

# 6. Test TCP connection
PGPASSWORD=serviceos psql -h 127.0.0.1 -p 5432 -U serviceos -d serviceos -c "SELECT 'WSL PostgreSQL OK' AS status;" 2>&1

echo "=== Setup Complete ==="
