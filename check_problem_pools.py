import sqlite3

conn = sqlite3.connect('Database/commvault.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

problem_pools = ["Apex GDP", "Southern_Sun_Durban", "Simera_GDP", "Southern_Sun_City_Bowl", "MKLM_GDP"]

print("Checking problem pools from screenshot...")
print("=" * 100)

cur.execute("""
    SELECT storagePoolName, totalCapacity, freeSpace, dedupeEnabled, storagePoolType, mediaAgentName
    FROM storage_pools
    WHERE storagePoolName IN (?, ?, ?, ?, ?)
    ORDER BY storagePoolName
""", problem_pools)

rows = cur.fetchall()

if len(rows) == 0:
    print("\n❌ None of these pools found in database!")
    print("\nLet me show you what pool names actually exist:")
    cur.execute("SELECT storagePoolName FROM storage_pools ORDER BY storagePoolName LIMIT 20")
    print("\nFirst 20 pool names in database:")
    for row in cur.fetchall():
        print(f"  - {row['storagePoolName']}")
else:
    for row in rows:
        print(f"\nPool: {row['storagePoolName']}")
        print("-" * 100)

        total_str = row['totalCapacity']
        free_str = row['freeSpace']

        print(f"Raw values from database:")
        print(f"  totalCapacity: {repr(total_str)} (type: {type(total_str).__name__})")
        print(f"  freeSpace: {repr(free_str)} (type: {type(free_str).__name__})")
        print(f"  dedupeEnabled: {row['dedupeEnabled']}")
        print(f"  storagePoolType: {row['storagePoolType']}")
        print(f"  mediaAgentName: {row['mediaAgentName']}")

        # Calculate like the dashboard does
        try:
            total_cap = int(total_str) if total_str else 0
            free_sp = int(free_str) if free_str else 0

            print(f"\nAfter int() conversion:")
            print(f"  total_cap: {total_cap}")
            print(f"  free_sp: {free_sp}")

            if total_cap > 0:
                pct_free = (free_sp * 100.0) / total_cap
                pct_used = 100 - pct_free

                # Convert to TB (1024^4 bytes)
                total_tb = total_cap / (1024**4)
                free_tb = free_sp / (1024**4)
                used_tb = total_tb - free_tb

                print(f"\nCalculated metrics:")
                print(f"  Total: {total_tb:.2f} TB")
                print(f"  Free: {free_tb:.2f} TB")
                print(f"  Used: {used_tb:.2f} TB")
                print(f"  % Used: {pct_used:.2f}%")
                print(f"  % Free: {pct_free:.2f}%")

                # Show why it might display as 0.0
                if total_tb < 0.01:
                    print(f"\n  ⚠️  WARNING: Total capacity is {total_tb} TB")
                    print(f"     When rounded to 2 decimal places, this displays as 0.0 TB!")
                    print(f"     Actual size: {total_cap:,} bytes = {total_cap/(1024**3):.4f} GB")
            else:
                print(f"\n  ❌ Cannot calculate - total capacity is 0 or None")

        except Exception as e:
            print(f"\n  ❌ Error: {e}")

conn.close()
