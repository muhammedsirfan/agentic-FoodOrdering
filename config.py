"""
Database Configuration
Stores PostgreSQL connection details
"""

import os
from urllib.parse import urlparse

# Your Neon PostgreSQL connection string
DATABASE_URL = "postgresql://neondb_owner:npg_gLFxvQ63OpmI@ep-delicate-feather-adv2yeiy-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"

# Parse connection details
url = urlparse(DATABASE_URL)

DB_CONFIG = {
    'host': url.hostname,
    'port': url.port or 5432,
    'database': url.path[1:],  # Remove leading '/'
    'user': url.username,
    'password': url.password,
    'sslmode': 'require'
}

# For debugging (remove in production)
if __name__ == "__main__":
    print("Database Configuration:")
    print(f"Host: {DB_CONFIG['host']}")
    print(f"Database: {DB_CONFIG['database']}")
    print(f"User: {DB_CONFIG['user']}")
    print(f"Port: {DB_CONFIG['port']}")