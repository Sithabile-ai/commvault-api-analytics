"""
Test script to find how copies map to storage pools
"""
import sqlite3

conn = sqlite3.connect('Database/commvault.db')
cur = conn.cursor()

print("=" * 80)
print("CHECKING PLANS TABLE")
print("=" * 80)

# Get plans table columns
cur.execute("PRAGMA table_info(plans)")
plans_columns = [row[1] for row in cur.fetchall()]
print("Plans table columns:", plans_columns)
print()

# Sample plans data
cur.execute("SELECT * FROM plans LIMIT 3")
sample_plans = cur.fetchall()
print("Sample plans:")
for plan in sample_plans:
    print(plan)
print()

# Check for copy-related tables
print("=" * 80)
print("CHECKING FOR COPY/STORAGE TABLES")
print("=" * 80)

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%copy%'")
copy_tables = cur.fetchall()
print("Tables with 'copy' in name:", copy_tables)

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%storage%'")
storage_tables = cur.fetchall()
print("Tables with 'storage' in name:", storage_tables)
print()

# Check if there's a table linking copies to storage pools
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
all_tables = [row[0] for row in cur.fetchall()]
print("\nAll tables in database:")
for table in all_tables:
    print(f"  - {table}")
print()

# Check storage_pools table structure
print("=" * 80)
print("STORAGE_POOLS TABLE STRUCTURE")
print("=" * 80)

cur.execute("PRAGMA table_info(storage_pools)")
pool_columns = [row[1] for row in cur.fetchall()]
print("Storage pools columns:", pool_columns)
print()

# Sample storage pools
cur.execute("SELECT storagePoolId, storagePoolName FROM storage_pools LIMIT 10")
print("Sample storage pools:")
for pool_id, pool_name in cur.fetchall():
    print(f"  {pool_id}: {pool_name}")
print()

# Try to find if copy names match storage pool names
print("=" * 80)
print("MATCHING COPY NAMES TO STORAGE POOLS")
print("=" * 80)

cur.execute("""
    SELECT DISTINCT r.entityName, r.parentName
    FROM retention_rules r
    ORDER BY r.entityName
    LIMIT 20
""")

print("Unique copy names:")
for copy_name, plan_name in cur.fetchall():
    print(f"  Copy: {copy_name} (Plan: {plan_name})")

    # Try to find matching storage pool
    cur.execute("""
        SELECT storagePoolName
        FROM storage_pools
        WHERE storagePoolName LIKE ?
        LIMIT 1
    """, (f"%{copy_name}%",))

    pool_match = cur.fetchone()
    if pool_match:
        print(f"    -> MATCH: {pool_match[0]}")

conn.close()
