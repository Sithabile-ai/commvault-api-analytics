"""
Populate Storage Estate from Existing Database
Uses current database data to build storage estate overview
"""

import sqlite3
from datetime import datetime

print("=" * 100)
print("POPULATING STORAGE ESTATE FROM EXISTING DATABASE")
print("=" * 100)
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Connect to database
conn = sqlite3.connect('Database/commvault.db')
cur = conn.cursor()

# Create storage estate tables if they don't exist
print("Creating storage estate tables...")

cur.execute("""
    CREATE TABLE IF NOT EXISTS storage_libraries (
        libraryId        INTEGER PRIMARY KEY,
        libraryName      TEXT NOT NULL,
        libraryType      TEXT,
        libraryTypeDesc  TEXT,
        mediaAgentId     INTEGER,
        mediaAgentName   TEXT,
        status           TEXT,
        capacity         INTEGER,
        freeSpace        INTEGER,
        usedSpace        INTEGER,
        usedPercent      REAL,
        vendorType       INTEGER,
        storageClass     TEXT,
        mountPath        TEXT,
        isCloudStorage   INTEGER,
        isDedupe         INTEGER,
        lastFetchTime    TEXT
    )
""")

cur.execute("""
    CREATE TABLE IF NOT EXISTS pool_library_mapping (
        storagePoolId    INTEGER,
        libraryId        INTEGER,
        mappingDate      TEXT,
        PRIMARY KEY (storagePoolId, libraryId),
        FOREIGN KEY (storagePoolId) REFERENCES storage_pools(storagePoolId),
        FOREIGN KEY (libraryId) REFERENCES storage_libraries(libraryId)
    )
""")

cur.execute("""
    CREATE TABLE IF NOT EXISTS storage_write_patterns (
        planId           INTEGER,
        planName         TEXT,
        storagePoolId    INTEGER,
        storagePoolName  TEXT,
        libraryId        INTEGER,
        libraryName      TEXT,
        copyType         TEXT,
        retentionDays    INTEGER,
        lastFetchTime    TEXT
    )
""")

conn.commit()
print("Tables created successfully")
print()

# Step 1: Populate storage_libraries from existing libraries table
print("=" * 100)
print("STEP 1: POPULATING LIBRARIES FROM EXISTING DATA")
print("=" * 100)
print()

cur.execute("SELECT libraryId, libraryName, libraryType, mediaAgentName, status, lastFetchTime FROM libraries")
existing_libraries = cur.fetchall()

print(f"Found {len(existing_libraries)} libraries in database")
print()

# Library type mapping
LIBRARY_TYPES = {
    "1": "Tape Library",
    "2": "Optical Library",
    "3": "Disk Library",
    "4": "Network Attached Storage",
    "5": "Cloud Storage",
    "6": "Deduplication Engine",
    "": "Disk Library"  # Default for empty type
}

for lib in existing_libraries:
    lib_id, lib_name, lib_type, ma_name, status, fetch_time = lib

    # Determine library type
    if not lib_type:
        lib_type = "3"  # Default to Disk Library

    lib_type_desc = LIBRARY_TYPES.get(lib_type, "Disk Library")
    is_cloud = 1 if lib_type == "5" else 0
    is_dedupe = 1 if lib_type == "6" else 0

    # Check if library name suggests cloud storage
    if any(keyword in lib_name.upper() for keyword in ['CLOUD', 'S3', 'AZURE', 'AWS', 'QUANTUM', 'ACTIVESCALE']):
        is_cloud = 1
        lib_type_desc = "Cloud Storage"

    print(f"Adding: {lib_name}")
    print(f"  Type: {lib_type_desc}")
    print(f"  Status: {status}")

    cur.execute("""
        INSERT OR REPLACE INTO storage_libraries
        (libraryId, libraryName, libraryType, libraryTypeDesc, mediaAgentName,
         status, isCloudStorage, isDedupe, lastFetchTime)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        lib_id,
        lib_name,
        lib_type,
        lib_type_desc,
        ma_name,
        status or 'Online',
        is_cloud,
        is_dedupe,
        datetime.now().isoformat()
    ))
    print()

conn.commit()
print(f"OK - Populated {len(existing_libraries)} libraries")
print()

# Step 2: Map storage pools to libraries
print("=" * 100)
print("STEP 2: MAPPING STORAGE POOLS TO LIBRARIES")
print("=" * 100)
print()

# Try to infer library from pool name or get from storage_pools if available
cur.execute("""
    SELECT sp.storagePoolId, sp.storagePoolName, sp.mediaAgentName
    FROM storage_pools sp
""")

pools = cur.fetchall()
print(f"Found {len(pools)} storage pools")
print()

mapped_count = 0

for pool_id, pool_name, ma_name in pools:
    # Try to find matching library by name similarity or MediaAgent
    cur.execute("""
        SELECT libraryId, libraryName
        FROM storage_libraries
        WHERE mediaAgentName = ? OR libraryName LIKE ?
        LIMIT 1
    """, (ma_name, f"%{pool_name.split('_')[0]}%"))

    library_match = cur.fetchone()

    if library_match:
        lib_id, lib_name = library_match

        cur.execute("""
            INSERT OR REPLACE INTO pool_library_mapping
            (storagePoolId, libraryId, mappingDate)
            VALUES (?, ?, ?)
        """, (pool_id, lib_id, datetime.now().isoformat()))

        mapped_count += 1
        if mapped_count <= 10:  # Show first 10
            print(f"Mapped: {pool_name} -> {lib_name}")

conn.commit()
print()
print(f"OK - Mapped {mapped_count} pools to libraries")
print()

# Step 3: Analyze storage write patterns
print("=" * 100)
print("STEP 3: ANALYZING STORAGE WRITE PATTERNS")
print("=" * 100)
print()

# Build complete write path: Plan -> Copy -> Pool -> Library
cur.execute("""
    SELECT DISTINCT
        p.planId,
        p.planName,
        r.entityName as copyName,
        sp.storagePoolId,
        sp.storagePoolName,
        r.retainBackupDataForDays as retentionDays
    FROM plans p
    LEFT JOIN retention_rules r ON p.planId = r.parentId
    LEFT JOIN storage_pools sp ON p.storageTarget = sp.storagePoolName
    WHERE r.entityType = 'plan_copy' AND sp.storagePoolId IS NOT NULL
""")

write_patterns = cur.fetchall()
print(f"Found {len(write_patterns)} plan-copy-to-storage relationships")
print()

saved_count = 0

for plan_id, plan_name, copy_name, pool_id, pool_name, retention_days in write_patterns:
    # Get library for this pool
    cur.execute("""
        SELECT sl.libraryId, sl.libraryName
        FROM pool_library_mapping plm
        JOIN storage_libraries sl ON plm.libraryId = sl.libraryId
        WHERE plm.storagePoolId = ?
    """, (pool_id,))

    library_info = cur.fetchone()
    library_id = library_info[0] if library_info else None
    library_name = library_info[1] if library_info else None

    cur.execute("""
        INSERT OR REPLACE INTO storage_write_patterns
        (planId, planName, storagePoolId, storagePoolName, libraryId, libraryName,
         copyType, retentionDays, lastFetchTime)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        plan_id,
        plan_name,
        pool_id,
        pool_name,
        library_id,
        library_name,
        copy_name or "Primary/Auxiliary",
        retention_days,
        datetime.now().isoformat()
    ))

    saved_count += 1
    if saved_count <= 10:  # Show first 10
        print(f"Mapped: {plan_name} -> {copy_name} -> {pool_name} -> {library_name}")

conn.commit()
print()
print(f"OK - Saved {saved_count} storage write patterns")
print()

# Step 4: Calculate and display summary
print("=" * 100)
print("STORAGE ESTATE SUMMARY")
print("=" * 100)
print()

# Libraries by type
cur.execute("""
    SELECT libraryTypeDesc, COUNT(*) as count
    FROM storage_libraries
    GROUP BY libraryTypeDesc
""")

print("Libraries by Type:")
for lib_type, count in cur.fetchall():
    print(f"  {lib_type}: {count}")

print()

# Storage pools
cur.execute("SELECT COUNT(*) FROM storage_pools")
total_pools = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(*) FROM storage_pools
    WHERE CAST(freeSpace AS REAL) / NULLIF(CAST(totalCapacity AS REAL), 0) < 0.2
""")
critical_pools = cur.fetchone()[0]

print(f"Storage Pools:")
print(f"  Total: {total_pools}")
print(f"  Critical (<20% free): {critical_pools}")
print()

# Write patterns
cur.execute("SELECT COUNT(DISTINCT planId) FROM storage_write_patterns")
plans_count = cur.fetchone()[0]

cur.execute("SELECT COUNT(DISTINCT storagePoolId) FROM storage_write_patterns")
pools_in_use = cur.fetchone()[0]

print(f"Storage Usage:")
print(f"  Plans writing to storage: {plans_count}")
print(f"  Storage pools in use: {pools_in_use}")
print()

# Check for cloud storage
cur.execute("SELECT COUNT(*) FROM storage_libraries WHERE isCloudStorage = 1")
cloud_count = cur.fetchone()[0]

if cloud_count > 0:
    print(f"Cloud Storage Detected:")
    cur.execute("SELECT libraryName FROM storage_libraries WHERE isCloudStorage = 1")
    for (lib_name,) in cur.fetchall():
        print(f"  - {lib_name}")
    print()

print("=" * 100)
print("STORAGE ESTATE POPULATION COMPLETE")
print("=" * 100)
print()

print("Database tables populated:")
print("  OK - storage_libraries - Libraries with type and status")
print("  OK - pool_library_mapping - Pool to library relationships")
print("  OK - storage_write_patterns - What writes to what storage")
print()

print("Next: Access the Storage Estate dashboard at:")
print("  http://127.0.0.1:5000/dashboard/storage-estate")
print()

conn.close()
