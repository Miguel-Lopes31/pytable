"""
Migration script to fix password_hash column size in Supabase
Run this once to update the existing database schema
"""
import os
from sqlalchemy import create_engine, text

# Get DATABASE_URL from environment
database_url = os.environ.get('DATABASE_URL')

if not database_url:
    print("ERROR: DATABASE_URL not set. Please set it to your Supabase connection string.")
    print("Example: export DATABASE_URL='postgresql://...'")
    exit(1)

# Fix postgres:// prefix if needed
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

print(f"Connecting to database...")
engine = create_engine(database_url)

try:
    with engine.connect() as conn:
        print("Altering password_hash column from VARCHAR(120) to VARCHAR(255)...")
        conn.execute(text('ALTER TABLE "user" ALTER COLUMN password_hash TYPE VARCHAR(255)'))
        conn.commit()
        print("✅ Migration completed successfully!")
        print("You can now create users with longer password hashes.")
except Exception as e:
    print(f"❌ Migration failed: {e}")
    print("\nIf the column is already VARCHAR(255), this is safe to ignore.")
