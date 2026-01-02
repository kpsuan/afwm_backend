#!/bin/bash
# AWFM Database Setup Script
# Run this script to create the PostgreSQL database and user

echo "Setting up AWFM PostgreSQL database..."

sudo -u postgres psql << 'EOF'
-- Create database
DROP DATABASE IF EXISTS awfm_db;
CREATE DATABASE awfm_db;

-- Create user
DROP USER IF EXISTS awfm_user;
CREATE USER awfm_user WITH PASSWORD 'awfm_password_2026';

-- Grant privileges
ALTER DATABASE awfm_db OWNER TO awfm_user;
GRANT ALL PRIVILEGES ON DATABASE awfm_db TO awfm_user;

-- Connect to database and grant schema privileges
\c awfm_db
GRANT ALL ON SCHEMA public TO awfm_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO awfm_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO awfm_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO awfm_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO awfm_user;

-- Verify
\l awfm_db
\du awfm_user
EOF

echo ""
echo "Database created successfully!"
echo "   Database: awfm_db"
echo "   User: awfm_user"
echo "   Password: awfm_password_2026"
echo ""
echo "Next steps:"
echo "1. Run migrations: python manage.py migrate"
echo "2. Create superuser: python manage.py createsuperuser"
echo "3. Seed content: python manage.py seed_content"
