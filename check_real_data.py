import sqlite3

conn = sqlite3.connect('Database/commvault.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()

print("=" * 80)
print("DATABASE: Database/commvault.db")
print("=" * 80)
print(f"\nTables found: {len(tables)}")
for table in tables:
    print(f"  - {table[0]}")

# Check storage pools specifically
print("\n" + "=" * 80)
print("CHECKING STORAGE POOLS DATA")
print("=" * 80)

try:
    cur.execute("SELECT COUNT(*) FROM storage_pools")
    count = cur.fetchone()[0]
    print(f"\nTotal storage pools: {count}")

    if count > 0:
        # Get sample data from first 3 pools
        cur.execute("""
            SELECT storagePoolName, totalCapacity, freeSpace, dedupeEnabled
            FROM storage_pools
            LIMIT 3
        """)

        print("\nSample data (first 3 pools):")
        print("-" * 80)
        for row in cur.fetchall():
            total = row['totalCapacity']
            free = row['freeSpace']
            print(f"\nPool: {row['storagePoolName']}")
            print(f"  Total Capacity: {total} (type: {type(total).__name__})")
            print(f"  Free Space: {free} (type: {type(free).__name__})")
            print(f"  Dedup Enabled: {row['dedupeEnabled']}")

            # Try to calculate percentage
            try:
                if total and int(total) > 0:
                    pct_free = (int(free) * 100.0) / int(total)
                    print(f"  % Free: {pct_free:.2f}%")
                else:
                    print(f"  % Free: CANNOT CALCULATE (total is 0 or None)")
            except:
                print(f"  % Free: ERROR calculating")

        # Check if ALL pools have zero capacity
        cur.execute("""
            SELECT COUNT(*) FROM storage_pools
            WHERE totalCapacity IS NOT NULL AND CAST(totalCapacity AS INTEGER) > 0
        """)
        pools_with_capacity = cur.fetchone()[0]
        print(f"\n" + "=" * 80)
        print(f"Pools with capacity > 0: {pools_with_capacity} out of {count}")

        if pools_with_capacity == 0:
            print("\n⚠️  WARNING: ALL storage pools have ZERO or NULL capacity!")
            print("   This means either:")
            print("   1. The data fetch didn't retrieve capacity information")
            print("   2. The Commvault API returned zero values")
            print("   3. The database schema doesn't match expectations")
    else:
        print("\n⚠️  No storage pool data found in database")

except Exception as e:
    print(f"\n❌ Error checking storage_pools table: {e}")

# Check retention_rules
print("\n" + "=" * 80)
print("CHECKING RETENTION RULES DATA")
print("=" * 80)

try:
    cur.execute("SELECT COUNT(*) FROM retention_rules")
    count = cur.fetchone()[0]
    print(f"\nTotal retention rules: {count}")
except Exception as e:
    print(f"Error: {e}")

# Check plans
print("\n" + "=" * 80)
print("CHECKING PLANS DATA")
print("=" * 80)

try:
    cur.execute("SELECT COUNT(*) FROM plans")
    count = cur.fetchone()[0]
    print(f"\nTotal plans: {count}")
except Exception as e:
    print(f"Error: {e}")

conn.close()
