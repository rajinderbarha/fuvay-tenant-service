#!/bin/bash
set -e

# Create serviceos user if not exists
sudo -u postgres psql -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'serviceos') THEN CREATE USER serviceos WITH PASSWORD 'serviceos' CREATEDB; END IF; END \$\$;"

# Create database if not exists
sudo -u postgres psql -c "SELECT 1 FROM pg_database WHERE datname = 'serviceos'" | grep -q 1 || sudo -u postgres createdb -O serviceos serviceos

# Grant all privileges
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE serviceos TO serviceos;"

# Update pg_hba.conf to allow connections from all (WSL network)
PG_HBA="/etc/postgresql/17/main/pg_hba.conf"
if ! grep -q "host all all 0.0.0.0/0 md5" "$PG_HBA"; then
    echo "host all all 0.0.0.0/0 md5" | sudo tee -a "$PG_HBA"
fi

# Configure postgres to listen on all interfaces
PG_CONF="/etc/postgresql/17/main/postgresql.conf"
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_CONF"
sudo sed -i "s/listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_CONF"

# Restart PostgreSQL to apply config
sudo service postgresql restart

echo "PostgreSQL setup complete!"
psql -h 127.0.0.1 -U serviceos -d serviceos -c "SELECT version();" 2>&1
