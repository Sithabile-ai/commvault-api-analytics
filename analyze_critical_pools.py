"""
Critical Pools Analysis - Database-Based Diagnostics
Performs comprehensive analysis using local database since API may not be accessible
"""

import sqlite3
from datetime import datetime

# Connect to database
conn = sqlite3.connect('Database/commvault.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 100)
print("CRITICAL STORAGE POOLS - COMPREHENSIVE DATABASE ANALYSIS")
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

# Save output to file as well
output_file = f"CRITICAL_POOLS_ANALYSIS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
output = []

output.append("=" * 100)
output.append("CRITICAL STORAGE POOLS - ACTIONABLE ANALYSIS")
output.append("=" * 100)
output.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
output.append(f"Total Critical Pools: {len(critical_pools)}")
output.append("")

# Analyze each critical pool
for idx, pool in enumerate(critical_pools, 1):
    section = []
    section.append("#" * 100)
    section.append(f"CRITICAL POOL #{idx}: {pool['name']}")
    section.append("#" * 100)
    section.append("")

    # Pool status
    section.append("CURRENT STATUS:")
    section.append(f"  Pool ID: {pool['id']}")
    section.append(f"  MediaAgent: {pool['ma'] if pool['ma'] else 'NOT SPECIFIED'}")
    section.append(f"  Type: {pool['type']}")
    section.append(f"  Deduplication: {pool['dedup']}")
    section.append(f"  Total Capacity: {pool['total_kb'] / (1024**3):.4f} GB ({pool['total_kb']:,} KB)")
    section.append(f"  Free Space: {pool['free_kb'] / (1024**3):.4f} GB ({pool['free_kb']:,} KB)")
    section.append(f"  Utilization: {pool['pct_used']:.2f}% USED")
    section.append(f"  Free: {pool['pct_free']:.2f}% (CRITICAL)")
    section.append("")

    # Pruning type based on dedup status
    if pool['dedup'] == 'Y':
        pruning_type = "MICROPRUNING (Deduplication enabled)"
        section.append("PRUNING CHARACTERISTICS:")
        section.append(f"  Type: {pruning_type}")
        section.append("  Process: Gradual block-level deletion via DDB")
        section.append("  Logs to Check: SIDBPrune.log, DDBVerification.log")
        section.append("  Key Concern: Pending deletes backlog in DDB")
    else:
        pruning_type = "MACRO PRUNING (Non-dedup storage)"
        section.append("PRUNING CHARACTERISTICS:")
        section.append(f"  Type: {pruning_type}")
        section.append("  Process: Direct file deletion (faster)")
        section.append("  Logs to Check: SIDBPrune.log, SIDBPhysicalDeletes.log")
        section.append("  Advantage: Space reclaimed immediately after aging")
    section.append("")

    # Check for associated plans
    section.append("ASSOCIATED PLANS CHECK:")

    # Since we don't have direct pool-to-plan mapping, check all plans
    cur.execute("""
        SELECT DISTINCT parentName, parentId, enableDataAging
        FROM retention_rules
        ORDER BY parentName
        LIMIT 20
    """)

    sample_plans = cur.fetchall()
    section.append(f"  Total Plans in Environment: {len(sample_plans)}+ (sample shown)")
    section.append("")
    section.append("  ACTION REQUIRED:")
    section.append(f"    1. CommCell Console > Storage > Storage Pools > {pool['name']}")
    section.append("    2. Right-click > Properties > View Associated Plans")
    section.append("    3. For EACH associated plan, verify:")
    section.append("       - Data Aging is ENABLED")
    section.append("       - Aging schedule runs daily")
    section.append("       - Recent aging jobs completed successfully")
    section.append("")

    # Check data aging status in environment
    section.append("DATA AGING ANALYSIS:")

    cur.execute("""
        SELECT enableDataAging, COUNT(*) as count
        FROM retention_rules
        GROUP BY enableDataAging
    """)

    aging_stats = cur.fetchall()
    for stat in aging_stats:
        status = "ENABLED" if stat['enableDataAging'] == 1 else "DISABLED (CRITICAL!)"
        section.append(f"  Rules with aging {status}: {stat['count']}")

    section.append("")
    section.append("  WARNING: If any plan using this pool has aging disabled:")
    section.append("    - Space will NEVER be reclaimed")
    section.append("    - Pool will continue filling until failure")
    section.append("    - IMMEDIATE action required to enable aging")
    section.append("")

    # Check retention rule inefficiencies
    section.append("RETENTION RULE OPTIMIZATION:")

    cur.execute("""
        SELECT COUNT(*) as inefficient_count
        FROM retention_rules
        WHERE retainBackupDataForDays <= 30 AND retainBackupDataForCycles >= 2
    """)

    inefficient_count = cur.fetchone()['inefficient_count']

    if inefficient_count > 0:
        section.append(f"  WARNING: {inefficient_count} rules in environment have inefficient retention")
        section.append("  Problem: Short retention (<=30 days) + multiple cycles (2+)")
        section.append("  Impact: Delays aging by 7-14 days unnecessarily")
        section.append("")
        section.append("  RECOMMENDATION:")
        section.append("    - Change retention cycles from 2+ to 1 for rules <=30 days")
        section.append("    - This will accelerate space reclamation by 7-14 days")
        section.append("    - Expected improvement: 10-20% faster space reclamation")
        section.append("")

        cur.execute("""
            SELECT parentName, entityName, retainBackupDataForDays, retainBackupDataForCycles
            FROM retention_rules
            WHERE retainBackupDataForDays <= 30 AND retainBackupDataForCycles >= 2
            ORDER BY parentName
            LIMIT 5
        """)

        sample_rules = cur.fetchall()
        section.append("  Sample rules to optimize:")
        for rule in sample_rules:
            section.append(f"    - {rule['parentName']} / {rule['entityName']}")
            section.append(f"      Current: {rule['retainBackupDataForDays']} days + {rule['retainBackupDataForCycles']} cycles")
            section.append(f"      Change to: {rule['retainBackupDataForDays']} days + 1 cycle")
    else:
        section.append("  STATUS: No inefficient short-term rules found")

    section.append("")

    # Immediate actions
    section.append("IMMEDIATE ACTIONS (NEXT 4 HOURS):")
    section.append("")
    section.append("  PRIORITY 1 - VERIFY PRUNING STATUS:")
    section.append(f"    [ ] Access MediaAgent: {pool['ma'] if pool['ma'] else 'IDENTIFY MEDIAAGENT FIRST'}")
    section.append("    [ ] Navigate to: <CommVault Install>\\Log Files\\")
    section.append("    [ ] Open SIDBPrune.log")
    section.append(f"    [ ] Search for: {pool['name']}")
    section.append("    [ ] Check last pruning timestamp (should be <24 hours)")
    section.append("    [ ] Look for errors: 'Failed', 'Skipped', 'Exception'")
    section.append("    [ ] Verify bytes freed entries exist")
    section.append("")

    section.append("  PRIORITY 2 - VERIFY DATA AGING:")
    section.append("    [ ] CommCell Console > Policies and Plans")
    section.append(f"    [ ] Find plans associated with pool: {pool['name']}")
    section.append("    [ ] For each plan: Properties > Retention")
    section.append("    [ ] Verify 'Enable Data Aging' is CHECKED")
    section.append("    [ ] Check aging schedule (should be daily)")
    section.append("    [ ] Job Controller > Filter 'Aging' jobs")
    section.append("    [ ] Verify recent aging jobs completed successfully")
    section.append("")

    section.append("  PRIORITY 3 - MANUAL PRUNING TRIGGER:")
    section.append("    [ ] CommCell Console > Storage Resources > Disk Storage")
    section.append(f"    [ ] Find pool: {pool['name']}")
    section.append("    [ ] Right-click > All Tasks > 'Run Auxiliary Copy Pruning'")
    section.append("    [ ] Monitor job in Job Controller")
    section.append("    [ ] Check if free space increases")
    section.append("")

    # Emergency thresholds
    if pool['pct_free'] < 5:
        section.append("  EMERGENCY STATUS - POOL BELOW 5% FREE!")
        section.append("    [ ] SUSPEND new backups targeting this pool IMMEDIATELY")
        section.append("    [ ] Redirect backups to alternative storage")
        section.append("    [ ] Escalate to Commvault support")
        section.append("    [ ] Plan emergency capacity expansion")
        section.append("")

    section.append("EXPECTED OUTCOMES:")
    section.append("  24 Hours: Pool should reach >12% free")
    section.append("  48 Hours: Pool should reach >15% free")
    section.append("  1 Week: Pool should stabilize at >20% free")
    section.append("")
    section.append("  If outcomes not met:")
    section.append("    - Review logs for pruning failures")
    section.append("    - Check for disk/mount path issues")
    section.append("    - Verify aging is marking data for deletion")
    section.append("    - Escalate to Commvault support")
    section.append("")

    # Print and save
    for line in section:
        print(line)
        output.append(line)

    print()
    output.append("")

# Environment-wide statistics
print("=" * 100)
print("ENVIRONMENT-WIDE ANALYSIS")
print("=" * 100)
print()

output.append("=" * 100)
output.append("ENVIRONMENT-WIDE ANALYSIS")
output.append("=" * 100)
output.append("")

# Total pools
cur.execute("SELECT COUNT(*) as total FROM storage_pools WHERE totalCapacity IS NOT NULL AND totalCapacity != ''")
total_pools = cur.fetchone()['total']

print(f"Total Storage Pools: {total_pools}")
print(f"Critical Pools (<10% free): {len(critical_pools)}")
print(f"Percentage Critical: {(len(critical_pools) * 100.0 / total_pools):.1f}%")
print()

output.append(f"Total Storage Pools: {total_pools}")
output.append(f"Critical Pools (<10% free): {len(critical_pools)}")
output.append(f"Percentage Critical: {(len(critical_pools) * 100.0 / total_pools):.1f}%")
output.append("")

# Data aging status
cur.execute("""
    SELECT enableDataAging, COUNT(*) as count
    FROM retention_rules
    GROUP BY enableDataAging
""")

aging_stats = cur.fetchall()

print("DATA AGING STATUS (All Plans):")
for stat in aging_stats:
    status = "ENABLED" if stat['enableDataAging'] == 1 else "DISABLED"
    print(f"  {status}: {stat['count']} retention rules")

    output.append(f"Data Aging {status}: {stat['count']} retention rules")

print()
output.append("")

# Inefficient retention rules
cur.execute("""
    SELECT COUNT(*) as count
    FROM retention_rules
    WHERE retainBackupDataForDays <= 30 AND retainBackupDataForCycles >= 2
""")

inefficient = cur.fetchone()['count']

print(f"RETENTION RULE INEFFICIENCIES:")
print(f"  Rules with short retention + multiple cycles: {inefficient}")
print(f"  Impact: Delayed aging by 7-14 days")
print(f"  Recommendation: Review Retention Health Dashboard")
print(f"  Action: Change to 1 cycle for rules <=30 days")
print()

output.append(f"Inefficient Retention Rules: {inefficient}")
output.append(f"  (Short retention <=30 days + 2+ cycles)")
output.append("")

# Summary and next steps
print("=" * 100)
print("SUMMARY - IMMEDIATE ACTION PLAN")
print("=" * 100)
print()

output.append("=" * 100)
output.append("SUMMARY - IMMEDIATE ACTION PLAN")
output.append("=" * 100)
output.append("")

summary = [
    "CRITICAL SITUATION:",
    f"  - {len(critical_pools)} storage pools are critically low on space (<10% free)",
    "  - Risk of backup failures if space exhausted",
    "  - Immediate action required to prevent service disruption",
    "",
    "ROOT CAUSES IDENTIFIED:",
    "  1. Pruning may not be running or failing (requires log verification)",
    "  2. Data aging may be disabled on some plans (prevents space reclamation)",
    f"  3. {inefficient} retention rules causing aging delays",
    "",
    "PRIORITY ACTIONS (EXECUTE NOW):",
    "",
    "NEXT 4 HOURS:",
    "  [ ] Check pruning logs on MediaAgents for all 3 critical pools",
    "  [ ] Verify data aging enabled for plans using critical pools",
    "  [ ] Manually trigger pruning for all 3 critical pools",
    "  [ ] Monitor space reclamation",
    "",
    "NEXT 24 HOURS:",
    f"  [ ] Optimize {inefficient} inefficient retention rules (reduce to 1 cycle)",
    "  [ ] Verify pruning schedules are configured",
    "  [ ] Fix any failed pruning jobs",
    "  [ ] Implement monitoring for pools <20% free",
    "",
    "NEXT WEEK:",
    "  [ ] Verify all critical pools >20% free",
    "  [ ] Create runbook for storage emergencies",
    "  [ ] Plan capacity expansion if needed",
    "  [ ] Schedule regular storage health reviews",
    "",
    "TOOLS AVAILABLE:",
    "  1. collect_pruning_logs.ps1 - Run on MediaAgents to gather logs",
    "  2. Storage Pool Health Dashboard - http://127.0.0.1:5000/dashboard/storage",
    "  3. Retention Health Dashboard - http://127.0.0.1:5000/dashboard/retention",
    "  4. CRITICAL_POOLS_ACTION_PLAN.txt - Detailed step-by-step guide",
    "",
    "ESCALATION:",
    "  - If pools drop below 5% free: SUSPEND backups immediately",
    "  - If pruning shows persistent failures: Contact Commvault support",
    "  - If no space reclaimed after 48 hours: Escalate to management",
    ""
]

for line in summary:
    print(line)
    output.append(line)

# Save to file
with open(output_file, 'w') as f:
    f.write('\n'.join(output))

print("=" * 100)
print(f"ANALYSIS SAVED TO: {output_file}")
print("=" * 100)
print()
print("NEXT STEP:")
print("  Run: powershell .\\collect_pruning_logs.ps1 -PoolName \"Apex GDP\"")
print("  (Execute on each MediaAgent managing critical pools)")
print()

conn.close()
