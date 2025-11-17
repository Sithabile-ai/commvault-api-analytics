import sqlite3

conn = sqlite3.connect('Database/commvault_data.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute('''
    SELECT storagePoolName, totalCapacity, freeSpace
    FROM storage_pools
    WHERE storagePoolName IN ("Apex GDP", "Southern_Sun_Durban", "Simera_GDP")
    ORDER BY storagePoolName
''')

rows = cur.fetchall()

print('Raw database values:')
print('=' * 100)
for r in rows:
    total = r["totalCapacity"]
    free = r["freeSpace"]
    print(f'{r["storagePoolName"]:<30} | Total: {total} ({type(total).__name__}) | Free: {free} ({type(free).__name__})')

    # Try to calculate percentage
    try:
        if total and int(total) > 0:
            pct_free = (int(free) * 100.0) / int(total)
            pct_used = 100 - pct_free
            total_tb = int(total) / (1024**4)
            free_tb = int(free) / (1024**4)
            print(f'  Calculated: Total={total_tb:.2f} TB, Free={free_tb:.2f} TB, Used={pct_used:.2f}%')
        else:
            print(f'  ERROR: Total capacity is 0 or None')
    except Exception as e:
        print(f'  ERROR: {e}')
    print()

conn.close()
