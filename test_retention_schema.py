"""
Test script to examine retention_rules schema and relationships
"""
import sqlite3

conn = sqlite3.connect('Database/commvault.db')
cur = conn.cursor()

print("=" * 80)
print("RETENTION RULES SAMPLE DATA")
print("=" * 80)

cur.execute("""
    SELECT entityType, entityId, entityName, parentId, parentName,
           retainBackupDataForDays
    FROM retention_rules
    LIMIT 10
""")

print("\nSample Records:")
for row in cur.fetchall():
    print(f"Type: {row[0]}, ID: {row[1]}, Name: {row[2]}")
    print(f"  Parent ID: {row[3]}, Parent Name: {row[4]}")
    print(f"  Retention Days: {row[5]}")
    print()

# Check what entity types exist
print("=" * 80)
print("ENTITY TYPES IN RETENTION RULES")
print("=" * 80)

cur.execute("""
    SELECT DISTINCT entityType, COUNT(*) as count
    FROM retention_rules
    GROUP BY entityType
""")

for entity_type, count in cur.fetchall():
    print(f"Type: {entity_type}, Count: {count}")

# Try to find relationship to storage pools
print("\n" + "=" * 80)
print("CHECKING PARENT RELATIONSHIPS")
print("=" * 80)

cur.execute("""
    SELECT r.entityName, r.parentName, sp.storagePoolName
    FROM retention_rules r
    LEFT JOIN storage_pools sp ON r.parentId = sp.storagePoolId
    WHERE r.parentId IS NOT NULL
    LIMIT 10
""")

print("\nRetention Rule -> Parent -> Storage Pool mapping:")
for entity_name, parent_name, pool_name in cur.fetchall():
    print(f"Entity: {entity_name}")
    print(f"  Parent: {parent_name}")
    print(f"  Pool Match: {pool_name}")
    print()

conn.close()
