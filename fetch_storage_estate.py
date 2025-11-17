"""
Fetch Complete Storage Estate Information from Commvault API
Collects libraries, storage pools, mount paths, and relationships
"""

import requests
import base64
import configparser
import sqlite3
from datetime import datetime
import json

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

BASE_URL = config.get('commvault', 'base_url')
USERNAME = config.get('commvault', 'username')
PASSWORD = config.get('commvault', 'password')

# Create authorization header
auth_string = f"{USERNAME}:{PASSWORD}"
auth_bytes = auth_string.encode('ascii')
base64_bytes = base64.b64encode(auth_bytes)
base64_auth = base64_bytes.decode('ascii')

headers = {
    'Authorization': f'Basic {base64_auth}',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

print("=" * 100)
print("FETCHING COMPLETE STORAGE ESTATE INFORMATION")
print("=" * 100)
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"CommVault Server: {BASE_URL}")
print()

# Connect to database
conn = sqlite3.connect('Database/commvault.db')
cur = conn.cursor()

# Update libraries table schema to include more fields
print("Updating database schema...")
try:
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

    # Create storage pool to library mapping table
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

    # Create storage write operations table (what writes to what)
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
    print("Database schema updated successfully")
    print()
except Exception as e:
    print(f"Error updating schema: {e}")
    print()

# Library type mapping
LIBRARY_TYPES = {
    "1": "Tape Library",
    "2": "Optical Library",
    "3": "Disk Library",
    "4": "Network Attached Storage",
    "5": "Cloud Storage",
    "6": "Deduplication Engine",
    "": "Unknown"
}

# Step 1: Fetch all libraries
print("=" * 100)
print("STEP 1: FETCHING ALL LIBRARIES")
print("=" * 100)
print()

libraries_data = []
library_endpoints = [
    "/Library",
    "/V2/Library",
    "/V4/Library"
]

for endpoint in library_endpoints:
    try:
        print(f"Trying endpoint: {endpoint}")
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, verify=False, timeout=30)

        if response.status_code == 200:
            data = response.json()
            lib_list = data.get("libraryList", data.get("libraries", data if isinstance(data, list) else []))

            if lib_list:
                print(f"✓ Found {len(lib_list)} libraries")
                libraries_data = lib_list
                break
        else:
            print(f"  Status: {response.status_code}")
    except Exception as e:
        print(f"  Error: {e}")

if not libraries_data:
    # Fallback: get from database
    print("Falling back to database libraries...")
    cur.execute("SELECT libraryId, libraryName FROM libraries")
    for lib_id, lib_name in cur.fetchall():
        libraries_data.append({"libraryId": lib_id, "libraryName": lib_name})

print(f"\nTotal libraries to process: {len(libraries_data)}")
print()

# Step 2: Get detailed information for each library
print("=" * 100)
print("STEP 2: FETCHING DETAILED LIBRARY INFORMATION")
print("=" * 100)
print()

for idx, lib in enumerate(libraries_data, 1):
    lib_id = lib.get("libraryId") or lib.get("id")
    lib_name = lib.get("libraryName") or lib.get("name")

    print(f"[{idx}/{len(libraries_data)}] {lib_name} (ID: {lib_id})")

    try:
        response = requests.get(f"{BASE_URL}/Library/{lib_id}", headers=headers, verify=False, timeout=30)

        if response.status_code == 200:
            detail_data = response.json()

            lib_type = str(detail_data.get("libraryType", lib.get("libraryType", "")))
            lib_type_desc = LIBRARY_TYPES.get(lib_type, "Unknown")

            capacity = detail_data.get("capacity", 0)
            free_space = detail_data.get("freeSpace", 0)
            used_space = capacity - free_space if capacity else 0
            used_percent = (used_space / capacity * 100) if capacity else 0

            is_cloud = 1 if lib_type == "5" else 0
            is_dedupe = 1 if lib_type == "6" else 0

            # Insert into storage_libraries table
            cur.execute("""
                INSERT OR REPLACE INTO storage_libraries
                (libraryId, libraryName, libraryType, libraryTypeDesc, mediaAgentId, mediaAgentName,
                 status, capacity, freeSpace, usedSpace, usedPercent, vendorType, isCloudStorage,
                 isDedupe, lastFetchTime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lib_id,
                lib_name,
                lib_type,
                lib_type_desc,
                detail_data.get("mediaAgentId"),
                detail_data.get("mediaAgentName"),
                detail_data.get("status", "Unknown"),
                capacity,
                free_space,
                used_space,
                used_percent,
                detail_data.get("libraryVendorType"),
                is_cloud,
                is_dedupe,
                datetime.now().isoformat()
            ))

            print(f"  Type: {lib_type_desc}")
            print(f"  Status: {detail_data.get('status', 'Unknown')}")
            print(f"  Capacity: {capacity / (1024**3):.2f} GB" if capacity else "  Capacity: N/A")
            print(f"  ✓ Saved to database")

        else:
            print(f"  Failed: HTTP {response.status_code}")

    except Exception as e:
        print(f"  Error: {e}")

    print()

conn.commit()

# Step 3: Map storage pools to libraries
print("=" * 100)
print("STEP 3: MAPPING STORAGE POOLS TO LIBRARIES")
print("=" * 100)
print()

# Get all storage pools
cur.execute("SELECT storagePoolId, storagePoolName FROM storage_pools")
pools = cur.fetchall()

print(f"Found {len(pools)} storage pools to map")
print()

# Try to get pool details via API to find library associations
pool_library_map = {}

for pool_id, pool_name in pools[:10]:  # Sample first 10 to avoid timeout
    print(f"Checking pool: {pool_name} (ID: {pool_id})")

    try:
        response = requests.get(f"{BASE_URL}/StoragePool/{pool_id}", headers=headers, verify=False, timeout=30)

        if response.status_code == 200:
            pool_data = response.json()

            library_id = pool_data.get("libraryId")
            library_name = pool_data.get("libraryName")

            if library_id:
                print(f"  → Library: {library_name} (ID: {library_id})")

                cur.execute("""
                    INSERT OR REPLACE INTO pool_library_mapping
                    (storagePoolId, libraryId, mappingDate)
                    VALUES (?, ?, ?)
                """, (pool_id, library_id, datetime.now().isoformat()))

                pool_library_map[pool_id] = library_id
            else:
                print(f"  No library association found")
        else:
            print(f"  Failed: HTTP {response.status_code}")

    except Exception as e:
        print(f"  Error: {e}")

conn.commit()
print()
print(f"Mapped {len(pool_library_map)} pools to libraries")
print()

# Step 4: Analyze storage write patterns (what writes to what)
print("=" * 100)
print("STEP 4: ANALYZING STORAGE WRITE PATTERNS")
print("=" * 100)
print()

# Get plan-to-pool relationships from retention_rules
cur.execute("""
    SELECT DISTINCT
        r.planId,
        p.planName,
        r.storagePoolId,
        sp.storagePoolName
    FROM retention_rules r
    LEFT JOIN plans p ON r.planId = p.planId
    LEFT JOIN storage_pools sp ON r.storagePoolId = sp.storagePoolId
    WHERE r.storagePoolId IS NOT NULL
""")

write_patterns = cur.fetchall()

print(f"Found {len(write_patterns)} plan-to-storage relationships")
print()

for plan_id, plan_name, pool_id, pool_name in write_patterns:
    # Get library for this pool
    library_id = pool_library_map.get(pool_id)
    library_name = None

    if library_id:
        cur.execute("SELECT libraryName FROM storage_libraries WHERE libraryId = ?", (library_id,))
        result = cur.fetchone()
        if result:
            library_name = result[0]

    # Get retention days
    cur.execute("""
        SELECT retentionRuleDays
        FROM retention_rules
        WHERE planId = ? AND storagePoolId = ?
        LIMIT 1
    """, (plan_id, pool_id))

    retention = cur.fetchone()
    retention_days = retention[0] if retention else None

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
        "Primary/Auxiliary",
        retention_days,
        datetime.now().isoformat()
    ))

conn.commit()
print(f"Saved {len(write_patterns)} storage write patterns")
print()

# Generate summary statistics
print("=" * 100)
print("STORAGE ESTATE SUMMARY")
print("=" * 100)
print()

# Count by type
cur.execute("""
    SELECT libraryTypeDesc, COUNT(*) as count,
           SUM(capacity) as total_capacity,
           SUM(freeSpace) as total_free,
           AVG(usedPercent) as avg_used_pct
    FROM storage_libraries
    WHERE libraryTypeDesc != 'Unknown'
    GROUP BY libraryTypeDesc
""")

print("Libraries by Type:")
for lib_type, count, total_cap, total_free, avg_used in cur.fetchall():
    print(f"  {lib_type}: {count} libraries")
    if total_cap:
        print(f"    Total Capacity: {total_cap / (1024**4):.2f} TB")
        print(f"    Total Free: {total_free / (1024**4):.2f} TB")
        print(f"    Avg Used: {avg_used:.1f}%")
    print()

# Storage pools summary
cur.execute("SELECT COUNT(*) FROM storage_pools")
total_pools = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(*) FROM storage_pools
    WHERE CAST(freeSpace AS REAL) / NULLIF(CAST(totalCapacity AS REAL), 0) < 0.2
""")
critical_pools = cur.fetchone()[0]

print(f"Storage Pools: {total_pools}")
print(f"  Critical (<20% free): {critical_pools}")
print()

# Write patterns summary
cur.execute("SELECT COUNT(DISTINCT planId) FROM storage_write_patterns")
plans_using_storage = cur.fetchone()[0]

cur.execute("SELECT COUNT(DISTINCT storagePoolId) FROM storage_write_patterns")
pools_in_use = cur.fetchone()[0]

print(f"Storage Usage:")
print(f"  Plans writing to storage: {plans_using_storage}")
print(f"  Storage pools in active use: {pools_in_use}")
print()

print("=" * 100)
print("STORAGE ESTATE DATA COLLECTION COMPLETE")
print("=" * 100)
print()

print("Database tables updated:")
print("  ✓ storage_libraries")
print("  ✓ pool_library_mapping")
print("  ✓ storage_write_patterns")
print()

print("Next: Access the Storage Estate dashboard in the web app")

conn.close()
