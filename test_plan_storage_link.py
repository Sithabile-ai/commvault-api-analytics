"""
Test to find the complete link: Plan -> Storage Pool -> Library
"""
import sqlite3

conn = sqlite3.connect('Database/commvault.db')
cur = conn.cursor()

print("=" * 80)
print("PLAN TO STORAGE POOL LINKAGE")
print("=" * 80)

# Check if storageTarget matches pool names
cur.execute("""
    SELECT p.planId, p.planName, p.storageTarget, sp.storagePoolId, sp.storagePoolName
    FROM plans p
    LEFT JOIN storage_pools sp ON p.storageTarget = sp.storagePoolName
    LIMIT 10
""")

print("\nPlan -> Storage Pool via storageTarget:")
for plan_id, plan_name, storage_target, pool_id, pool_name in cur.fetchall():
    print(f"Plan: {plan_name}")
    print(f"  Target: {storage_target}")
    print(f"  Pool Match: {pool_name} (ID: {pool_id})")
    print()

# Check storage_policies table
print("=" * 80)
print("STORAGE POLICIES TABLE")
print("=" * 80)

cur.execute("PRAGMA table_info(storage_policies)")
policy_columns = [row[1] for row in cur.fetchall()]
print("Storage policy columns:", policy_columns)
print()

cur.execute("SELECT * FROM storage_policies LIMIT 5")
print("Sample storage policies:")
for row in cur.fetchall():
    print(row)
print()

# Try to build complete chain: Plan -> Copy -> Storage Pool -> Library
print("=" * 80)
print("COMPLETE CHAIN: PLAN -> COPY -> POOL -> LIBRARY")
print("=" * 80)

cur.execute("""
    SELECT
        p.planId,
        p.planName,
        r.entityName as copyName,
        p.storageTarget,
        sp.storagePoolId,
        sp.storagePoolName,
        plm.libraryId,
        sl.libraryName
    FROM plans p
    LEFT JOIN retention_rules r ON p.planId = r.parentId
    LEFT JOIN storage_pools sp ON p.storageTarget = sp.storagePoolName
    LEFT JOIN pool_library_mapping plm ON sp.storagePoolId = plm.storagePoolId
    LEFT JOIN storage_libraries sl ON plm.libraryId = sl.libraryId
    WHERE r.entityType = 'plan_copy'
    LIMIT 20
""")

print("\nComplete write path (Plan -> Copy -> Pool -> Library):")
for plan_id, plan_name, copy_name, target, pool_id, pool_name, lib_id, lib_name in cur.fetchall():
    print(f"Plan: {plan_name}")
    print(f"  Copy: {copy_name}")
    print(f"  -> Storage Pool: {pool_name} (ID: {pool_id})")
    print(f"  -> Library: {lib_name} (ID: {lib_id})")
    print()

conn.close()
