"""
Comprehensive Pruning Policy Analysis
Analyzes why aged data is not being pruned and space is not being reclaimed
"""
import sqlite3
import sys
from collections import defaultdict

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Connect to database
conn = sqlite3.connect('Database/commvault.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 100)
print("PRUNING POLICY ANALYSIS - WHY ISN'T SPACE BEING RECLAIMED?")
print("=" * 100)
print()
print("Analyzing the relationship between aging, pruning, and storage reclamation...")
print()

# ============================================================================
# UNDERSTANDING: AGING vs PRUNING
# ============================================================================
print("=" * 100)
print("BACKGROUND: AGING vs PRUNING")
print("=" * 100)
print()
print("📚 KEY CONCEPTS:")
print()
print("1. AGING (Logical Operation)")
print("   - Marks data as eligible for deletion based on retention rules")
print("   - Runs daily at 12:00 PM (configurable)")
print("   - Does NOT free up space - only marks data")
print("   - Fast operation (metadata only)")
print()
print("2. PRUNING (Physical Operation)")
print("   - Actually deletes aged data from disk")
print("   - Frees up physical storage space")
print("   - Resource-intensive operation")
print("   - Runs after aging completes")
print()
print("3. THE PROBLEM:")
print("   If aging marks data but pruning doesn't run or complete,")
print("   storage space will NOT be reclaimed!")
print()

# ============================================================================
# SECTION 1: STORAGE POLICY ANALYSIS
# ============================================================================
print("=" * 100)
print("SECTION 1: STORAGE POLICY & PRUNING CONFIGURATION")
print("=" * 100)
print()

# Check storage policies table
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='storage_policies'")
if cur.fetchone():
    cur.execute("SELECT COUNT(*) FROM storage_policies")
    policy_count = cur.fetchone()[0]
    print(f"Total Storage Policies: {policy_count}")

    if policy_count > 0:
        cur.execute("""
            SELECT
                storagePolicyId,
                storagePolicyName
            FROM storage_policies
            ORDER BY storagePolicyName
        """)
        policies = cur.fetchall()

        print()
        print("Storage Policies Requiring Pruning Analysis:")
        print(f"{'Policy Name':<70}")
        print("-" * 100)
        for policy in policies[:20]:
            print(f"{policy['storagePolicyName'][:70]:<70}")

        if len(policies) > 20:
            print(f"... and {len(policies) - 20} more policies")
        print()
    else:
        print("⚠️  No storage policies found in database")
        print()
else:
    print("⚠️  Storage policies table not available")
    print()

# ============================================================================
# SECTION 2: DEDUPLICATION & PRUNING ISSUES
# ============================================================================
print("=" * 100)
print("SECTION 2: DEDUPLICATION & PRUNING COMPLEXITY")
print("=" * 100)
print()

print("🔍 DEDUPLICATION PRUNING PROCESS:")
print()
print("For deduplicated storage, pruning is MORE COMPLEX:")
print()
print("Step 1: Data Aging runs → Jobs marked as aged")
print("Step 2: DDB (Deduplication Database) reference counters decremented")
print("Step 3: Blocks with zero references moved to 'Pending Pruning' queue")
print("Step 4: Physical pruning operation removes blocks from disk")
print("Step 5: Space reclaimed and available")
print()
print("⚠️  PRUNING CAN BE BLOCKED BY:")
print("   - DDB not sealed (for cloud storage)")
print("   - MediaAgent offline or overloaded")
print("   - Mount paths offline")
print("   - Pruning operation window restrictions")
print("   - High pending delete counts in DDB")
print("   - Resource constraints (CPU/memory)")
print()

# Check if we have library data
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='libraries'")
if cur.fetchone():
    cur.execute("SELECT COUNT(*) FROM libraries WHERE libraryType IS NOT NULL")
    lib_count = cur.fetchone()[0]

    if lib_count > 0:
        print(f"Libraries Configured: {lib_count}")

        cur.execute("""
            SELECT
                libraryId,
                libraryName,
                libraryType
            FROM libraries
            WHERE libraryType IS NOT NULL
            ORDER BY libraryName
            LIMIT 15
        """)
        libraries = cur.fetchall()

        print()
        print("Libraries (where pruning must occur):")
        for lib in libraries:
            lib_type = lib['libraryType'] if lib['libraryType'] else 'Unknown'
            print(f"  - {lib['libraryName'][:60]:<60} | Type: {lib_type}")
        print()
    else:
        print("⚠️  No library data available for pruning analysis")
        print()
else:
    print("⚠️  Libraries table not available")
    print()

# ============================================================================
# SECTION 3: MEDIAAGENT & MOUNT PATH ANALYSIS
# ============================================================================
print("=" * 100)
print("SECTION 3: MEDIAAGENT HEALTH (Critical for Pruning)")
print("=" * 100)
print()

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mediaagents'")
if cur.fetchone():
    cur.execute("SELECT COUNT(*) FROM mediaagents")
    ma_count = cur.fetchone()[0]

    print(f"Total MediaAgents: {ma_count}")
    print()

    if ma_count > 0:
        print("⚠️  CRITICAL: MediaAgents must be ONLINE for pruning to work!")
        print()
        print("MediaAgent Status:")
        print(f"{'MediaAgent Name':<40} {'Host':<30}")
        print("-" * 100)

        cur.execute("""
            SELECT
                mediaAgentId,
                mediaAgentName,
                hostName
            FROM mediaagents
            ORDER BY mediaAgentName
            LIMIT 20
        """)
        mas = cur.fetchall()

        for ma in mas:
            print(f"{ma['mediaAgentName'][:40]:<40} {ma['hostName'][:30] if ma['hostName'] else 'N/A':<30}")

        if ma_count > 20:
            print(f"... and {ma_count - 20} more MediaAgents")
        print()

        print("⚠️  ACTION REQUIRED:")
        print("   - Verify all MediaAgents are ONLINE in Commvault console")
        print("   - Check MediaAgent logs (SIDBPrune.log) for pruning issues")
        print("   - Ensure mount paths are accessible")
        print()
    else:
        print("⚠️  No MediaAgent data available")
        print()
else:
    print("⚠️  MediaAgents table not available")
    print()

# ============================================================================
# SECTION 4: RETENTION RULES & PRUNING DEPENDENCY
# ============================================================================
print("=" * 100)
print("SECTION 4: RETENTION RULES IMPACT ON PRUNING")
print("=" * 100)
print()

cur.execute("""
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN enableDataAging = 1 THEN 1 ELSE 0 END) as aging_enabled,
        SUM(CASE WHEN enableDataAging = 0 THEN 1 ELSE 0 END) as aging_disabled
    FROM retention_rules
""")
stats = cur.fetchone()

print(f"Total Retention Rules: {stats['total']}")
print(f"  - Aging Enabled: {stats['aging_enabled']} ({stats['aging_enabled']*100/stats['total']:.1f}%)")
print(f"  - Aging DISABLED: {stats['aging_disabled']} ({stats['aging_disabled']*100/stats['total']:.1f}%)")
print()

if stats['aging_disabled'] > 0:
    print(f"🔴 CRITICAL FINDING: {stats['aging_disabled']} rules have aging DISABLED")
    print("   → Data will NEVER be marked for aging")
    print("   → Pruning will NEVER occur for this data")
    print("   → Storage space will NEVER be reclaimed")
    print()

# Analyze cycle-based retention blocking pruning
cur.execute("""
    SELECT
        COUNT(*) as count,
        AVG(retainBackupDataForCycles) as avg_cycles
    FROM retention_rules
    WHERE retainBackupDataForCycles >= 2
      AND retainBackupDataForDays <= 30
      AND enableDataAging = 1
""")
cycle_issue = cur.fetchone()

if cycle_issue['count'] > 0:
    print(f"⚠️  PRUNING DELAY: {cycle_issue['count']} rules have cycle requirements")
    print(f"   Average cycles required: {cycle_issue['avg_cycles']:.1f}")
    print("   → Aging delayed = Pruning delayed = Space NOT reclaimed")
    print()

# ============================================================================
# SECTION 5: STORAGE POOL SPACE ANALYSIS
# ============================================================================
print("=" * 100)
print("SECTION 5: STORAGE POOL SPACE (Proof of Pruning Failure)")
print("=" * 100)
print()

cur.execute("""
    SELECT
        storagePoolName,
        totalCapacity,
        freeSpace
    FROM storage_pools
""")
all_pools = cur.fetchall()

# Calculate percentages
critical_pools = []
warning_pools = []
low_pools = []

for pool in all_pools:
    try:
        total = int(pool['totalCapacity']) if pool['totalCapacity'] else 0
        free = int(pool['freeSpace']) if pool['freeSpace'] else 0
        if total > 0:
            pct = (free * 100.0) / total
            if pct < 10:
                critical_pools.append((pool['storagePoolName'], pct))
            elif pct < 20:
                warning_pools.append((pool['storagePoolName'], pct))
            elif pct < 30:
                low_pools.append((pool['storagePoolName'], pct))
    except (ValueError, TypeError):
        continue

print(f"Storage Pool Health:")
print(f"  - Total Pools: {len(all_pools)}")
print(f"  - 🔴 CRITICAL (<10% free): {len(critical_pools)}")
print(f"  - 🟠 WARNING (10-20% free): {len(warning_pools)}")
print(f"  - 🟡 LOW (20-30% free): {len(low_pools)}")
print()

if len(critical_pools) > 0 or len(warning_pools) > 0:
    print("💥 STORAGE CRISIS DETECTED!")
    print()
    print(f"   {len(critical_pools) + len(warning_pools)} pools are critically low on space")
    print("   This is PROOF that pruning is not working properly!")
    print()
    print("   If aging were working AND pruning were completing:")
    print("   → Aged data would be deleted")
    print("   → Space would be freed")
    print("   → Pools would not be critically full")
    print()

# Sort critical pools by percent free
critical_and_warning = critical_pools + warning_pools
critical_and_warning.sort(key=lambda x: x[1])

if critical_and_warning:
    print("Most Critical Pools (Highest Pruning Priority):")
    print(f"{'Pool Name':<50} {'% Free':<10}")
    print("-" * 100)
    for pool_name, pct in critical_and_warning[:15]:
        print(f"{pool_name[:50]:<50} {pct:>8.2f}%")
    print()

# ============================================================================
# SECTION 6: ROOT CAUSE ANALYSIS
# ============================================================================
print("=" * 100)
print("SECTION 6: ROOT CAUSE - WHY ISN'T PRUNING WORKING?")
print("=" * 100)
print()

print("ANALYSIS FINDINGS:")
print()

# Finding 1: Aging configuration issues
if stats['aging_disabled'] > 0:
    print(f"1. ❌ AGING DISABLED on {stats['aging_disabled']} rules")
    print("   ROOT CAUSE: If aging doesn't run, pruning has nothing to delete")
    print("   SOLUTION: Enable data aging on all retention rules")
    print()

# Finding 2: Cycle retention delays
if cycle_issue['count'] > 0:
    print(f"2. ⏱️  CYCLE RETENTION DELAYS on {cycle_issue['count']} rules")
    print("   ROOT CAUSE: Data not marked for aging = Not eligible for pruning")
    print("   SOLUTION: Reduce cycle requirements from 2 → 1 for short-term policies")
    print()

# Finding 3: Storage pools critically low
if len(critical_pools) > 0 or len(warning_pools) > 0:
    print(f"3. 💾 STORAGE POOLS CRITICALLY LOW ({len(critical_pools) + len(warning_pools)} pools)")
    print("   ROOT CAUSE: Pruning not completing or not running at all")
    print("   POSSIBLE CAUSES:")
    print("      a) MediaAgents offline or overloaded")
    print("      b) DDB sealed/corrupted (for deduplication)")
    print("      c) Pruning operation windows blocking execution")
    print("      d) Mount paths offline")
    print("      e) High pending delete queue in DDB")
    print("   SOLUTION: Check MediaAgent status, DDB health, and pruning logs")
    print()

# Finding 4: No job data for deeper analysis
cur.execute("SELECT COUNT(*) FROM jobs WHERE status IS NOT NULL")
job_count_with_status = cur.fetchone()[0]

if job_count_with_status == 0:
    print("4. ⚠️  LIMITED JOB DATA")
    print("   Cannot verify if aging jobs are running successfully")
    print("   Cannot confirm if pruning operations are scheduled")
    print("   SOLUTION: Collect comprehensive job history including aging/pruning jobs")
    print()

# ============================================================================
# SECTION 7: DETAILED RECOMMENDATIONS
# ============================================================================
print("=" * 100)
print("SECTION 7: RECOMMENDATIONS TO FIX PRUNING ISSUES")
print("=" * 100)
print()

print("PRIORITY 1: VERIFY PRUNING IS ENABLED & RUNNING")
print()
print("Step 1: Check Data Aging Configuration")
print("  - Go to CommCell Console → Storage Resources → Storage Policies")
print("  - Right-click each policy → Properties → Retention tab")
print("  - Verify 'Enable Data Aging' is checked")
print("  - Check 'Data Aging Time' (default: 12:00 PM)")
print()

print("Step 2: Verify MediaAgent Status")
print("  - Go to CommCell Console → Storage Resources → MediaAgents")
print("  - Verify all MediaAgents show as 'Online'")
print("  - Check 'Control Panel' → 'Event Viewer' for errors")
print()

print("Step 3: Check DDB Status (for Deduplication)")
print("  - Go to CommCell Console → Storage Resources → Deduplication Engines")
print("  - Right-click DDB → Properties")
print("  - Check 'Status' field (should be 'Active', not 'Sealed')")
print("  - Note 'Pending Deletes' count (high = pruning backlog)")
print()

print("Step 4: Manually Trigger Pruning")
print("  - Right-click Deduplication Database")
print("  - Select 'All Tasks' → 'Validate and Prune Aged Data'")
print("  - Monitor job progress")
print("  - Check if space is freed after completion")
print()

print("PRIORITY 2: RESOLVE CONFIGURATION ISSUES")
print()

if stats['aging_disabled'] > 0:
    print(f"Action 1: Enable aging on {stats['aging_disabled']} retention rules")
    print("  - Update retention rules to enable data aging")
    print("  - This allows data to be marked for pruning")
    print()

if cycle_issue['count'] > 0:
    print(f"Action 2: Fix cycle retention on {cycle_issue['count']} rules")
    print("  - Reduce from 2 cycles → 1 cycle for ≤30 day policies")
    print("  - Allows faster aging = faster pruning eligibility")
    print()

if len(critical_pools) > 0:
    print(f"Action 3: Emergency space reclamation on {len(critical_pools)} critical pools")
    print("  - Manually run pruning on most critical pools first")
    print("  - Consider temporary storage expansion if needed")
    print("  - Monitor pruning job completion")
    print()

print("PRIORITY 3: VERIFY PRUNING RESULTS")
print()
print("Step 1: Run Data Retention Forecast Report")
print("  - CommCell Console → Reports → Data Retention Forecast")
print("  - Shows what data should be aged/pruned")
print("  - Identifies issues preventing pruning")
print()

print("Step 2: Check Pruning Logs")
print("  - On MediaAgent: <Install_Path>/Log Files/SIDBPrune.log")
print("  - Look for pruning job execution")
print("  - Check for errors or warnings")
print()

print("Step 3: Monitor Storage Pool Space")
print("  - After pruning runs, check if pool free space increases")
print("  - If no change = pruning failed or didn't run")
print("  - Investigate root cause from logs")
print()

# ============================================================================
# SECTION 8: SUMMARY
# ============================================================================
print("=" * 100)
print("SECTION 8: EXECUTIVE SUMMARY")
print("=" * 100)
print()

print("THE AGING-PRUNING RELATIONSHIP:")
print()
print("  AGING (Logical) → Marks data eligible for deletion")
print("         ↓")
print("  PRUNING (Physical) → Actually deletes the data")
print("         ↓")
print("  SPACE RECLAMATION → Storage freed up")
print()

print("CURRENT STATE:")
print()
if stats['aging_disabled'] > 0:
    print(f"  ❌ {stats['aging_disabled']} rules have aging DISABLED → No data marked for pruning")
else:
    print(f"  ✅ All {stats['total']} rules have aging ENABLED")

if cycle_issue['count'] > 0:
    print(f"  ⏱️  {cycle_issue['count']} rules have cycle delays → Aging delayed → Pruning delayed")

if len(critical_pools) + len(warning_pools) > 0:
    print(f"  💾 {len(critical_pools) + len(warning_pools)} pools critically low → PROOF pruning not working")
else:
    print(f"  ✅ Storage pools have adequate free space")

print()
print("MOST LIKELY ROOT CAUSES:")
print()
print("  1. Aging not marking data due to cycle retention requirements")
print("  2. Pruning operations not completing (MediaAgent issues)")
print("  3. DDB sealed or corrupted (for deduplication storage)")
print("  4. Pruning operation windows restricting when pruning can run")
print()

print("IMMEDIATE ACTIONS:")
print()
print("  1. Fix aging configuration (enable aging, reduce cycles)")
print("  2. Verify MediaAgent health and availability")
print("  3. Manually run 'Validate and Prune Aged Data' on critical pools")
print("  4. Monitor pruning job logs for errors")
print("  5. Check DDB status if using deduplication")
print()

print("=" * 100)
print("ANALYSIS COMPLETE")
print("=" * 100)
print()

conn.close()
