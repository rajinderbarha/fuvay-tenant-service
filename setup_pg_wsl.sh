#!/bin/bash
# Must run as postgres user (via su or running directly)
# This script creates the serviceos user and database

echo "Setting up ServiceOS database..."

# Connect as postgres via su (no password needed since postgres is a system user)
su -c "psql -c \"CREATE USER serviceos WITH PASSWORD 'serviceos' CREATEDB;\"" postgres 2>&1 || echo "User may already exist"
su -c "createdb -O serviceos serviceos" postgres 2>&1 || echo "DB may already exist"
su -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE serviceos TO serviceos;\"" postgres 2>&1
su -c "psql -d serviceos -c \"CREATE EXTENSION IF NOT EXISTS \\\"uuid-ossp\\\"; CREATE EXTENSION IF NOT EXISTS pgcrypto;\"" postgres 2>&1

# Configure pg_hba.conf to allow md5 from all IPs
PG_HBA="/etc/postgresql/17/main/pg_hba.conf"
if ! grep -q "0.0.0.0/0" "$PG_HBA"; then
    echo "host all all 0.0.0.0/0 md5" >> "$PG_HBA"
    echo "host all all ::/0 md5" >> "$PG_HBA"
    echo "Added wildcard host rule to pg_hba.conf"
fi

# Configure listen_addresses to *
PG_CONF="/etc/postgresql/17/main/postgresql.conf"
sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_CONF"
sed -i "s/listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_CONF"
grep "listen_addresses" "$PG_CONF"

# Reload PostgreSQL config
su -c "pg_ctlcluster 17 main reload" postgres 2>&1

echo "Setup complete!"
# Test connection
PGPASSWORD=serviceos psql -h 127.0.0.1 -U serviceos -d serviceos -c "SELECT 'Connection OK';" 2>&1
