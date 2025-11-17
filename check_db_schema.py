import sqlite3

conn = sqlite3.connect('Database/commvault_data.db')
cur = conn.cursor()

# Get all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()

print("Tables in database:")
print("=" * 50)
for table in tables:
    print(f"  - {table[0]}")

print("\nLooking for storage-related tables...")
for table in tables:
    if 'storage' in table[0].lower() or 'pool' in table[0].lower():
        print(f"\nTable: {table[0]}")
        cur.execute(f"PRAGMA table_info({table[0]})")
        columns = cur.fetchall()
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")

conn.close()
