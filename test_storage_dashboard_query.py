"""
Test the storage estate dashboard SQL queries
"""
import sqlite3

conn = sqlite3.connect('Database/commvault.db')
cur = conn.cursor()

print("=" * 80)
print("TESTING STORAGE ESTATE DASHBOARD QUERIES")
print("=" * 80)
print()

# Test 1: Get all libraries
print("Test 1: Libraries Query")
print("-" * 80)
cur.execute("""
    SELECT libraryId, libraryName, libraryType, libraryTypeDesc, mediaAgentName,
           status, capacity, freeSpace, usedSpace, usedPercent, vendorType,
           isCloudStorage, isDedupe
    FROM storage_libraries
    ORDER BY libraryTypeDesc, libraryName
    LIMIT 5
""")

libraries = cur.fetchall()
print(f"Found {len(libraries)} libraries (showing first 5):")
for lib in libraries:
    print(f"  {lib[1]} - Type: {lib[3]}, Status: {lib[5]}")
print()

# Test 2: Libraries by type
print("Test 2: Libraries by Type")
print("-" * 80)
cur.execute("""
    SELECT libraryTypeDesc, COUNT(*) as count
    FROM storage_libraries
    GROUP BY libraryTypeDesc
    ORDER BY libraryTypeDesc
""")

for lib_type, count in cur.fetchall():
    print(f"  {lib_type}: {count}")
print()

# Test 3: Storage pools
print("Test 3: Storage Pools")
print("-" * 80)
cur.execute("""
    SELECT sp.storagePoolId, sp.storagePoolName, sp.totalCapacity, sp.freeSpace
    FROM storage_pools sp
    LIMIT 5
""")

pools = cur.fetchall()
print(f"Found pools (showing first 5):")
for pool_id, pool_name, total, free in pools:
    print(f"  {pool_name}: {total} total, {free} free")
print()

# Test 4: Pool to library mapping
print("Test 4: Pool-Library Mapping")
print("-" * 80)
cur.execute("""
    SELECT plm.storagePoolId, plm.libraryId
    FROM pool_library_mapping plm
    LIMIT 5
""")

mappings = cur.fetchall()
print(f"Found {len(mappings)} mappings (showing first 5):")
for pool_id, lib_id in mappings:
    print(f"  Pool {pool_id} -> Library {lib_id}")
print()

# Test 5: Write patterns
print("Test 5: Storage Write Patterns")
print("-" * 80)
cur.execute("""
    SELECT planName, copyType, storagePoolName, libraryName, retentionDays
    FROM storage_write_patterns
    LIMIT 10
""")

patterns = cur.fetchall()
print(f"Found write patterns (showing first 10):")
for plan, copy, pool, lib, retention in patterns:
    print(f"  {plan} -> {copy} -> {pool} -> {lib} ({retention} days)")
print()

# Test 6: Overview stats
print("Test 6: Overview Statistics")
print("-" * 80)

cur.execute("SELECT COUNT(*) FROM storage_libraries")
total_libs = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM storage_libraries WHERE libraryTypeDesc = 'Disk Library'")
disk_libs = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM storage_libraries WHERE isCloudStorage = 1")
cloud_libs = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM storage_pools")
total_pools = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(*) FROM storage_pools
    WHERE CAST(freeSpace AS REAL) / NULLIF(CAST(totalCapacity AS REAL), 0) < 0.2
""")
critical_pools = cur.fetchone()[0]

cur.execute("SELECT COUNT(DISTINCT planId) FROM storage_write_patterns")
plans_count = cur.fetchone()[0]

print(f"Total Libraries: {total_libs}")
print(f"Disk Libraries: {disk_libs}")
print(f"Cloud Libraries: {cloud_libs}")
print(f"Total Storage Pools: {total_pools}")
print(f"Critical Pools (<20% free): {critical_pools}")
print(f"Plans using storage: {plans_count}")
print()

print("=" * 80)
print("ALL QUERIES SUCCESSFUL - DASHBOARD SHOULD WORK")
print("=" * 80)

conn.close()
