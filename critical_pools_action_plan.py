"""
Critical Pools Action Plan Generator
Analyzes the 3 critical pools and provides specific remediation steps
"""

import sqlite3
from datetime import datetime

# Connect to database
conn = sqlite3.connect('Database/commvault.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 100)
print("CRITICAL STORAGE POOLS - ACTIONABLE REMEDIATION PLAN")
print("=" * 100)
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Get critical pools (<10% free)
cur.execute("""
    SELECT storagePoolId, storagePoolName, storagePoolType, mediaAgentName,
           totalCapacity, freeSpace, dedupeEnabled
    FROM storage_pools
    ORDER BY storagePoolName
""")

all_pools = cur.fetchall()
critical_pools = []

for pool in all_pools:
    try:
        total = int(pool['totalCapacity']) if pool['totalCapacity'] else 0
        free = int(pool['freeSpace']) if pool['freeSpace'] else 0

        if total > 0:
            pct_free = (free * 100.0) / total
            if pct_free < 10:
                critical_pools.append({
                    'name': pool['storagePoolName'],
                    'id': pool['storagePoolId'],
                    'type': pool['storagePoolType'],
                    'ma': pool['mediaAgentName'],
                    'total_kb': total,
                    'free_kb': free,
                    'pct_free': pct_free,
                    'pct_used': 100 - pct_free,
                    'dedup': pool['dedupeEnabled']
                })
    except:
        continue

critical_pools.sort(key=lambda x: x['pct_free'])

print(f"CRITICAL POOLS IDENTIFIED: {len(critical_pools)}")
print("=" * 100)
print()

# For each critical pool, create action plan
for idx, pool in enumerate(critical_pools, 1):
    print(f"{'#' * 100}")
    print(f"POOL #{idx}: {pool['name']}")
    print(f"{'#' * 100}")
    print()

    # Pool details
    print(f"Current Status:")
    print(f"  - Pool ID: {pool['id']}")
    print(f"  - MediaAgent: {pool['ma'] if pool['ma'] else 'N/A'}")
    print(f"  - Type: {pool['type']}")
    print(f"  - Total Capacity: {pool['total_kb'] / (1024**3):.2f} GB")
    print(f"  - Free Space: {pool['free_kb'] / (1024**3):.2f} GB")
    print(f"  - Utilization: {pool['pct_used']:.2f}% USED")
    print(f"  - Free: {pool['pct_free']:.2f}% (CRITICAL - <10%)")
    print(f"  - Deduplication: {pool['dedup']}")
    print()

    # Find associated plans/storage policies
    print(f"STEP 1: CHECK DATA AGING CONFIGURATION")
    print("-" * 100)

    # Check retention rules that might affect this pool
    cur.execute("""
        SELECT DISTINCT parentName, parentId
        FROM retention_rules
        LIMIT 10
    """)

    sample_plans = cur.fetchall()

    print(f"Action Items:")
    print(f"  [ ] Log into CommCell Console")
    print(f"  [ ] Navigate to: Storage Resources > Storage Pools > {pool['name']}")
    print(f"  [ ] Right-click > Properties > View Associated Plans/Policies")
    print(f"  [ ] For EACH associated plan:")
    print(f"      - Go to Plan Properties > Retention Rules")
    print(f"      - Verify 'Enable Data Aging' is CHECKED")
    print(f"      - Check aging schedule (should run daily)")
    print()

    print(f"Expected Findings:")
    print(f"  ✓ Data aging enabled: Space should reclaim automatically")
    print(f"  ✗ Data aging disabled: NO space will EVER be reclaimed (critical issue)")
    print()

    # Check for retention inefficiencies
    print(f"STEP 2: CHECK RETENTION RULE INEFFICIENCIES")
    print("-" * 100)

    cur.execute("""
        SELECT parentName, entityName, retainBackupDataForDays, retainBackupDataForCycles,
               enableDataAging
        FROM retention_rules
        WHERE retainBackupDataForDays <= 30 AND retainBackupDataForCycles >= 2
        ORDER BY parentName
        LIMIT 5
    """)

    inefficient_rules = cur.fetchall()

    if inefficient_rules:
        print(f"WARNING: Found inefficient retention rules that may be delaying aging:")
        print()
        for rule in inefficient_rules:
            print(f"  Plan: {rule['parentName']}")
            print(f"    Copy: {rule['entityName']}")
            print(f"    Retention: {rule['retainBackupDataForDays']} days + {rule['retainBackupDataForCycles']} cycles")
            print(f"    Aging Enabled: {'YES' if rule['enableDataAging'] == 1 else 'NO (CRITICAL!)'}")
            print(f"    Recommendation: Change to 1 cycle for faster aging")
            print()

    print(f"Action Items:")
    print(f"  [ ] Review retention rules using Retention Health Dashboard")
    print(f"  [ ] Identify rules with ≤30 days + 2+ cycles")
    print(f"  [ ] Change retention cycles from 2 → 1 for short-term retention")
    print(f"  [ ] This will reduce aging delay by 7-14 days")
    print()

    # Pruning log check
    print(f"STEP 3: CHECK PRUNING LOGS ON MEDIAAGENT")
    print("-" * 100)

    ma_name = pool['ma'] if pool['ma'] else 'UNKNOWN'

    print(f"MediaAgent: {ma_name}")
    print()
    print(f"Log Files to Check:")
    print(f"  1. Location: <CommVault Install>\\Log Files\\")
    print(f"  2. Primary Logs:")
    print(f"     - SIDBPrune.log       (Shows pruning activity)")
    print(f"     - SIDBPhysicalDeletes.log  (Shows actual deletions)")
    print(f"     - CVMA.log            (MediaAgent operations)")
    print()
    print(f"What to Look For:")
    print(f"  ✓ Recent pruning activity (last 24 hours)")
    print(f"  ✓ 'Pruning completed successfully' messages")
    print(f"  ✓ Bytes freed in recent operations")
    print(f"  ✗ 'Skipped' messages (indicates blocking issues)")
    print(f"  ✗ Errors or warnings")
    print(f"  ✗ No recent activity (pruning not running)")
    print()

    print(f"Action Items:")
    print(f"  [ ] RDP/SSH to MediaAgent: {ma_name}")
    print(f"  [ ] Navigate to log directory")
    print(f"  [ ] Open SIDBPrune.log and search for '{pool['name']}'")
    print(f"  [ ] Check last pruning timestamp")
    print(f"  [ ] Look for errors or 'skipped' entries")
    print()

    # Manual pruning trigger
    print(f"STEP 4: MANUALLY TRIGGER PRUNING (IF NEEDED)")
    print("-" * 100)

    print(f"If logs show pruning hasn't run recently:")
    print()
    print(f"Action Items:")
    print(f"  [ ] CommCell Console > Storage Resources > Disk Storage")
    print(f"  [ ] Find storage pool: {pool['name']}")
    print(f"  [ ] Right-click > All Tasks > 'Run Auxiliary Copy Pruning'")
    print(f"  [ ] Monitor job progress in Job Controller")
    print(f"  [ ] Check if space is being reclaimed")
    print()
    print(f"Expected Results:")
    print(f"  - Job should complete successfully")
    print(f"  - Free space should increase")
    print(f"  - If no space freed: aged data not available (aging issue)")
    print()

    # Emergency recommendations
    print(f"STEP 5: EMERGENCY SPACE RECLAMATION")
    print("-" * 100)

    print(f"If pool reaches <5% free (IMMINENT FAILURE):")
    print()
    print(f"IMMEDIATE Actions:")
    print(f"  [ ] SUSPEND new backup jobs targeting this pool")
    print(f"  [ ] Run emergency pruning manually")
    print(f"  [ ] Check for aged jobs manually:")
    print(f"      - CommCell Console > Job Controller")
    print(f"      - Filter: Completed jobs older than retention")
    print(f"      - Verify they're marked for deletion")
    print(f"  [ ] Contact Commvault support if issue persists")
    print()

    print(f"SHORT-TERM Workarounds:")
    print(f"  [ ] Temporarily redirect backups to different pool")
    print(f"  [ ] Add additional disk storage if available")
    print(f"  [ ] Reduce retention for non-critical data")
    print()

    print(f"LONG-TERM Fix:")
    print(f"  [ ] Optimize retention rules (1 cycle for <30 days)")
    print(f"  [ ] Implement automated pruning schedules")
    print(f"  [ ] Add monitoring/alerts for pools <20%")
    print(f"  [ ] Plan capacity expansion")
    print()
    print()

# Summary with prioritization
print("=" * 100)
print("PRIORITIZED ACTION PLAN SUMMARY")
print("=" * 100)
print()

print("PRIORITY 1 - IMMEDIATE (Next 24 hours):")
print("  1. Check pruning logs on all MediaAgents for critical pools")
print("  2. Verify data aging is enabled for associated plans")
print("  3. Manually trigger pruning for all critical pools")
print("  4. Monitor space reclamation")
print()

print("PRIORITY 2 - URGENT (This Week):")
print("  5. Review and optimize retention rules (reduce cycles to 1)")
print("  6. Verify pruning schedules are configured and running")
print("  7. Check for failed pruning jobs in last 30 days")
print("  8. Implement monitoring alerts for pools <20%")
print()

print("PRIORITY 3 - IMPORTANT (This Month):")
print("  9. Plan capacity expansion for critical pools")
print("  10. Document standard retention policies")
print("  11. Create runbook for storage pool emergencies")
print("  12. Schedule regular storage health reviews")
print()

# Query database for additional context
print("=" * 100)
print("SUPPORTING DATA")
print("=" * 100)
print()

# Check if we have job data
cur.execute("SELECT COUNT(*) as count FROM jobs")
job_count = cur.fetchone()[0]

if job_count > 0:
    cur.execute("""
        SELECT COUNT(*) as failed_jobs
        FROM jobs
        WHERE status = 'Failed' OR status = 'Failed with errors'
    """)
    failed = cur.fetchone()
    if failed:
        print(f"Failed Backup Jobs: {failed[0]}")
        print(f"  Action: Review failed jobs - may indicate storage full issues")
        print()

# Check retention rules with aging disabled
cur.execute("""
    SELECT COUNT(*) as disabled_aging
    FROM retention_rules
    WHERE enableDataAging = 0
""")
disabled_count = cur.fetchone()[0]

if disabled_count > 0:
    print(f"WARNING: {disabled_count} retention rules have aging DISABLED!")
    print(f"  These rules will NEVER age data - space will never be reclaimed")
    print(f"  Action: Review Retention Health Dashboard and enable aging")
    print()

# Check inefficient rules
cur.execute("""
    SELECT COUNT(*) as inefficient
    FROM retention_rules
    WHERE retainBackupDataForDays <= 30 AND retainBackupDataForCycles >= 2
""")
inefficient_count = cur.fetchone()[0]

if inefficient_count > 0:
    print(f"WARNING: {inefficient_count} retention rules are inefficient!")
    print(f"  Short retention (<30 days) with multiple cycles (2+)")
    print(f"  This delays aging by 7-14 days unnecessarily")
    print(f"  Action: Reduce to 1 cycle for faster space reclamation")
    print()

print("=" * 100)
print("END OF ACTION PLAN")
print("=" * 100)
print()
print("Next Steps:")
print("  1. Save this report")
print("  2. Assign tasks to team members")
print("  3. Execute PRIORITY 1 items immediately")
print("  4. Schedule follow-up review in 48 hours")
print()

conn.close()
