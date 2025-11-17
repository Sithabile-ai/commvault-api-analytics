"""
Comprehensive Pruning Analysis: Micro vs Macro Pruning
Analyzes pruning strategy and identifies optimal approach for each storage pool
"""
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Connect to database
conn = sqlite3.connect('Database/commvault.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 100)
print("COMPREHENSIVE PRUNING STRATEGY ANALYSIS")
print("=" * 100)
print()
print("Analyzing Micro vs Macro Pruning strategies for optimal space reclamation...")
print()

# ============================================================================
# SECTION 1: UNDERSTANDING PRUNING TYPES
# ============================================================================
print("=" * 100)
print("SECTION 1: PRUNING TYPES EXPLAINED")
print("=" * 100)
print()

print("📚 PRUNING FUNDAMENTALS")
print()
print("Pruning is the process of PHYSICALLY DELETING aged data from storage.")
print("There are TWO types of pruning strategies:")
print()

print("1. MICROPRUNING (Individual Block Deletion)")
print("   ├─ What: Deletes individual data blocks as jobs age")
print("   ├─ When: Enabled by default for cloud/dedup storage")
print("   ├─ How: Reference counters decremented → Block reaches ref=0 → Deleted")
print("   ├─ Speed: Gradual, continuous space reclamation")
print("   ├─ Efficiency: Good for most scenarios")
print("   └─ Best For: Standard backup storage, cloud storage (non-WORM)")
print()

print("2. MACRO PRUNING (Bulk/DDB Seal and Prune)")
print("   ├─ What: Seals entire DDB, waits for all jobs to age, deletes entire DDB")
print("   ├─ When: Required for WORM storage, archive cloud")
print("   ├─ How: Seal DDB → Age all jobs → Delete entire DDB partition")
print("   ├─ Speed: Slow, bulk deletion only after ALL jobs aged")
print("   ├─ Efficiency: Requires 3x retention capacity")
print("   └─ Best For: WORM/immutable storage, archive cloud")
print()

print("⚠️  CRITICAL DIFFERENCES:")
print()
print("   Micropruning:")
print("   ✅ Space freed incrementally as jobs age")
print("   ✅ Lower storage capacity requirements")
print("   ✅ Faster space reclamation")
print("   ❌ Cannot be used with WORM storage")
print("   ❌ Slower on archive cloud (impractical)")
print()
print("   Macro Pruning:")
print("   ✅ Works with WORM/immutable storage")
print("   ✅ Clean, predictable DDB lifecycle")
print("   ❌ Requires 3x retention storage capacity")
print("   ❌ No space freed until ENTIRE DDB ages")
print("   ❌ Long wait time for space reclamation")
print()

# ============================================================================
# SECTION 2: CURRENT ENVIRONMENT ANALYSIS
# ============================================================================
print("=" * 100)
print("SECTION 2: CURRENT ENVIRONMENT PRUNING CONFIGURATION")
print("=" * 100)
print()

# Get storage pools
cur.execute("""
    SELECT
        storagePoolId,
        storagePoolName,
        storagePoolType,
        mediaAgentName,
        totalCapacity,
        freeSpace,
        dedupeEnabled
    FROM storage_pools
    ORDER BY storagePoolName
""")
storage_pools = cur.fetchall()

print(f"Total Storage Pools: {len(storage_pools)}")
print()

# Categorize by type
cloud_pools = []
disk_pools = []
tape_pools = []
dedup_pools = []
non_dedup_pools = []

for pool in storage_pools:
    pool_type = str(pool['storagePoolType']).lower() if pool['storagePoolType'] else ''

    if 'cloud' in pool_type:
        cloud_pools.append(pool)
    elif 'tape' in pool_type:
        tape_pools.append(pool)
    else:
        disk_pools.append(pool)

    # Check if dedupe enabled (value might be string or int)
    dedupe_val = str(pool['dedupeEnabled']).lower() if pool['dedupeEnabled'] else ''
    if dedupe_val in ['1', 'true', 'yes']:
        dedup_pools.append(pool)
    else:
        non_dedup_pools.append(pool)

print("Storage Pool Categorization:")
print(f"  - Disk Pools: {len(disk_pools)}")
print(f"  - Cloud Pools: {len(cloud_pools)}")
print(f"  - Tape Pools: {len(tape_pools)}")
print()
print(f"  - Deduplication Enabled: {len(dedup_pools)}")
print(f"  - Non-Dedup: {len(non_dedup_pools)}")
print()

# ============================================================================
# SECTION 3: PRUNING STRATEGY RECOMMENDATIONS
# ============================================================================
print("=" * 100)
print("SECTION 3: PRUNING STRATEGY RECOMMENDATIONS BY POOL TYPE")
print("=" * 100)
print()

print("📊 ANALYSIS BY STORAGE TYPE")
print()

# Dedup pools analysis
if dedup_pools:
    print(f"🔵 DEDUPLICATION POOLS ({len(dedup_pools)} pools)")
    print()
    print("   Pruning Type: MICROPRUNING (Recommended)")
    print("   Reason: Micropruning enabled by default for dedup")
    print()
    print("   How Micropruning Works for Dedup:")
    print("   1. Job ages → DDB reference counters decremented")
    print("   2. Block ref count reaches 0 → Added to pending delete queue")
    print("   3. Mark and Sweep operation identifies pruneable chunks")
    print("   4. Physical deletion from SFILES (logged in SIDBPhysicalDeletes.log)")
    print("   5. Space gradually freed as blocks become unreferenced")
    print()
    print("   ⚠️  KEY CONSIDERATION: Shared Blocks")
    print("   - Multiple jobs can reference same data blocks")
    print("   - Block not deleted until ALL jobs referencing it are aged")
    print("   - Extended retention on ONE job delays pruning for ALL jobs sharing blocks")
    print()

    # Calculate space stats
    critical_dedup = []
    for pool in dedup_pools:
        try:
            total = int(pool['totalCapacity']) if pool['totalCapacity'] else 0
            free = int(pool['freeSpace']) if pool['freeSpace'] else 0
            if total > 0:
                pct = (free * 100.0) / total
                if pct < 20:
                    critical_dedup.append((pool['storagePoolName'], pct))
        except (ValueError, TypeError):
            continue

    if critical_dedup:
        print(f"   🔴 ALERT: {len(critical_dedup)} dedup pools are critically low (<20% free)")
        print("   This indicates micropruning is NOT working properly!")
        print()
        print("   Most Critical Dedup Pools:")
        for pool_name, pct in sorted(critical_dedup, key=lambda x: x[1])[:5]:
            print(f"     - {pool_name}: {pct:.2f}% free")
        print()

    print("   Troubleshooting Micropruning Issues:")
    print("   1. Check SIDBPrune.log on MediaAgent for pruning activity")
    print("   2. Check SIDBEngine.log for Mark and Sweep operations (should run daily)")
    print("   3. Query MMDeletedAF table for pending deletes (high count = backlog)")
    print("   4. Check DDB status (must be Active, not Sealed)")
    print("   5. Verify MediaAgent is online and accessible")
    print()

# Cloud pools analysis
if cloud_pools:
    print(f"☁️  CLOUD STORAGE POOLS ({len(cloud_pools)} pools)")
    print()
    print("   Pruning Type: MICROPRUNING (Enabled by Default)")
    print("   Reason: Ensures data pruned as soon as jobs age, without DDB seal")
    print()
    print("   ⚠️  EXCEPTION: WORM-enabled Cloud Storage")
    print("   - Micropruning CANNOT be used with WORM (immutability)")
    print("   - MUST use Macro Pruning (seal DDB periodically)")
    print("   - Storage Requirement: 3x retention capacity")
    print()
    print("   Why 3x Capacity for WORM:")
    print("   - DDB 1: Active, accumulating data")
    print("   - DDB 2: Sealed, waiting for retention to expire (immutable)")
    print("   - DDB 3: Aged out, finally eligible for deletion")
    print("   - Can't prune DDB 1 until DDB 3 fully aged = 3x capacity needed")
    print()

    # Identify potential WORM pools (this is speculation without actual WORM data)
    print("   📋 ACTION REQUIRED:")
    print("   - Verify which cloud pools have WORM/immutability enabled")
    print("   - For WORM pools: Plan for 3x retention capacity")
    print("   - For non-WORM: Micropruning should be working")
    print()

# Archive cloud consideration
print("📦 ARCHIVE CLOUD STORAGE")
print()
print("   Pruning Type: MACRO PRUNING (Required)")
print("   Reason: Micropruning is impractical (extremely slow) on archive cloud")
print()
print("   Archive Cloud Best Practice:")
print("   - Seal DDB periodically (e.g., every 6 months or yearly)")
print("   - Wait for all jobs in sealed DDB to meet retention")
print("   - Macro prune entire sealed DDB")
print("   - Archive cloud optimized for write-once-read-rarely, not individual deletes")
print()

# Non-dedup pools
if non_dedup_pools:
    print(f"💾 NON-DEDUPLICATION POOLS ({len(non_dedup_pools)} pools)")
    print()
    print("   Pruning Type: DIRECT DELETION (Simplest)")
    print("   Reason: No reference counting needed")
    print()
    print("   How Non-Dedup Pruning Works:")
    print("   1. Job ages")
    print("   2. Job files directly deleted from disk")
    print("   3. Space immediately freed")
    print("   No DDB, no reference counting, no pending delete queue")
    print()
    print("   Troubleshooting Non-Dedup Pruning:")
    print("   1. Check CVMA.log on MediaAgent for pruning activity")
    print("   2. Verify mount paths are accessible")
    print("   3. Check MediaAgent is online")
    print()

# ============================================================================
# SECTION 4: STORAGE POOL PRUNING HEALTH
# ============================================================================
print("=" * 100)
print("SECTION 4: STORAGE POOL PRUNING HEALTH ASSESSMENT")
print("=" * 100)
print()

# Analyze each pool
micropruning_healthy = []
micropruning_failing = []
macropruning_candidates = []

for pool in storage_pools:
    try:
        total = int(pool['totalCapacity']) if pool['totalCapacity'] else 0
        free = int(pool['freeSpace']) if pool['freeSpace'] else 0

        if total > 0:
            pct_free = (free * 100.0) / total
            dedupe_val = str(pool['dedupeEnabled']).lower() if pool['dedupeEnabled'] else ''
            is_dedup = dedupe_val in ['1', 'true', 'yes']

            if pct_free < 20:
                # Critically low = pruning failing
                micropruning_failing.append({
                    'name': pool['storagePoolName'],
                    'pct_free': pct_free,
                    'is_dedup': is_dedup,
                    'type': pool['storagePoolType']
                })
            elif pct_free > 30:
                # Healthy space = pruning working
                micropruning_healthy.append({
                    'name': pool['storagePoolName'],
                    'pct_free': pct_free,
                    'is_dedup': is_dedup,
                    'type': pool['storagePoolType']
                })
    except (ValueError, TypeError):
        continue

print(f"Pruning Health Status:")
print(f"  ✅ Healthy Pools (>30% free): {len(micropruning_healthy)}")
print(f"  🔴 Failing Pools (<20% free): {len(micropruning_failing)}")
print()

if micropruning_failing:
    print("🚨 POOLS WITH FAILING PRUNING (Immediate Action Required):")
    print()
    print(f"{'Pool Name':<50} {'% Free':<10} {'Dedup':<8} {'Type':<20} {'Recommended Action'}")
    print("-" * 120)

    for pool in sorted(micropruning_failing, key=lambda x: x['pct_free']):
        dedup_str = "Yes" if pool['is_dedup'] else "No"
        pool_type = str(pool['type']) if pool['type'] else 'Unknown'

        # Determine action
        if pool['is_dedup']:
            action = "Check micropruning logs (SIDBPrune)"
        else:
            action = "Check CVMA logs"

        print(f"{pool['name'][:50]:<50} {pool['pct_free']:>8.2f}% {dedup_str:<8} {pool_type[:20]:<20} {action}")
    print()

# ============================================================================
# SECTION 5: MACRO PRUNING CAPACITY PLANNING
# ============================================================================
print("=" * 100)
print("SECTION 5: MACRO PRUNING CAPACITY PLANNING")
print("=" * 100)
print()

print("📊 CAPACITY REQUIREMENTS FOR MACRO PRUNING")
print()

# Get retention rules to calculate capacity
cur.execute("""
    SELECT
        retainBackupDataForDays,
        retainBackupDataForCycles,
        COUNT(*) as rule_count
    FROM retention_rules
    WHERE retainBackupDataForDays > 0
    GROUP BY retainBackupDataForDays, retainBackupDataForCycles
    ORDER BY COUNT(*) DESC
    LIMIT 10
""")
retention_groups = cur.fetchall()

print("Most Common Retention Configurations:")
print(f"{'Retention Days':<20} {'Cycles':<10} {'# Rules':<15} {'Macro Pruning Capacity'}")
print("-" * 80)

for group in retention_groups:
    days = group['retainBackupDataForDays']
    cycles = group['retainBackupDataForCycles'] if group['retainBackupDataForCycles'] else 0
    count = group['rule_count']

    # For macro pruning: need 3x retention
    macro_capacity = f"3x {days} days = ~{days * 3} days capacity"

    print(f"{days} days{' ' * (20 - len(str(days)) - 5)} {cycles:<10} {count:<15} {macro_capacity}")

print()
print("💡 INTERPRETATION:")
print()
print("If switching to Macro Pruning (seal and prune strategy):")
print("  - Must maintain 3 DDB partitions simultaneously")
print("  - Each partition holds data for retention period")
print("  - Total capacity = 3x normal retention capacity")
print()
print("Example: 30-day retention")
print("  - DDB 1: Days 1-30 (Active)")
print("  - DDB 2: Days 31-60 (Sealed, immutable)")
print("  - DDB 3: Days 61-90 (Aged, ready to delete)")
print("  - Need capacity for 90 days data, not 30 days")
print()
print("⚠️  This is why micropruning is preferred when possible!")
print()

# ============================================================================
# SECTION 6: PRUNING OPTIMIZATION RECOMMENDATIONS
# ============================================================================
print("=" * 100)
print("SECTION 6: PRUNING OPTIMIZATION RECOMMENDATIONS")
print("=" * 100)
print()

print("🎯 IMMEDIATE ACTIONS (Priority Order):")
print()

# Priority 1: Fix failing micropruning
if micropruning_failing:
    print(f"1. ⚠️  FIX MICROPRUNING ON {len(micropruning_failing)} CRITICAL POOLS")
    print()
    print("   Step-by-Step Troubleshooting:")
    print()
    print("   A. Verify MediaAgent Health")
    print("      - Location: CommCell Console → Storage Resources → MediaAgents")
    print("      - Check: All MediaAgents for critical pools show 'Online'")
    print("      - Action: Restart offline MediaAgents")
    print()
    print("   B. Check DDB Status (Dedup Pools Only)")
    print("      - Location: CommCell Console → Storage → Deduplication Engines")
    print("      - Right-click DDB → Properties → Status")
    print("      - Expected: 'Active' (not 'Sealed')")
    print("      - Check: 'Pending Deletes' count")
    print("        • Normal: <10,000")
    print("        • Warning: 10,000-100,000")
    print("        • Critical: >100,000 (severe backlog)")
    print()
    print("   C. Manually Trigger Pruning")
    print("      - Location: Right-click DDB → All Tasks")
    print("      - Select: 'Validate and Prune Aged Data'")
    print("      - Monitor: Job progress and space freed")
    print("      - Repeat for each critical pool")
    print()
    print("   D. Review Pruning Logs")
    print("      - Location: MediaAgent → <Install>/Log Files/")
    print("      - Logs: SIDBPrune.log, SIDBPhysicalDeletes.log, SIDBEngine.log")
    print("      - Look for: Errors, warnings, 'skipped' messages")
    print("      - Common issues:")
    print("        • Mount path not accessible")
    print("        • Resource exhaustion (CPU/Memory/Disk)")
    print("        • Pruning operation window restrictions")
    print()

# Priority 2: Optimize for micropruning
print("2. 🔧 OPTIMIZE CONFIGURATION FOR MICROPRUNING")
print()
print("   A. Remove Extended Retention from Dedup Copies")
print("      - Extended retention on dedup delays pruning for ALL jobs")
print("      - Recommendation: Create separate selective copies for long-term retention")
print("      - Benefit: Faster pruning on primary dedup storage")
print()
print("   B. Verify Micropruning Enabled")
print("      - Location: Storage Policy → Copy → Advanced → Deduplication Options")
print("      - Setting: 'Enable micro pruning' should be CHECKED")
print("      - Default: Enabled for cloud dedup")
print()
print("   C. Reduce Cycle Requirements (From Previous Analysis)")
print("      - 130 rules have ≤30 days + 2 cycles")
print("      - Change to 1 cycle for faster aging")
print("      - Faster aging = Faster pruning eligibility")
print()

# Priority 3: Plan for WORM if needed
if cloud_pools:
    print("3. 📋 CAPACITY PLANNING FOR WORM STORAGE (If Applicable)")
    print()
    print("   If any cloud pools use WORM/immutability:")
    print()
    print("   A. Calculate 3x Capacity Requirement")
    print("      - Current retention: X days")
    print("      - Required capacity: 3X days worth of data")
    print("      - Example: 90-day retention = 270 days capacity needed")
    print()
    print("   B. Plan DDB Sealing Schedule")
    print("      - Frequency: Every 6 months or yearly")
    print("      - Process: Seal DDB → Create new DDB → Continue backups")
    print("      - Timeline: Previous DDB remains for 3x retention period")
    print()
    print("   C. Monitor Sealed DDB Aging")
    print("      - Track when all jobs in sealed DDB meet retention")
    print("      - Only then can sealed DDB be deleted (macro pruned)")
    print()

# ============================================================================
# SECTION 7: MONITORING & VERIFICATION
# ============================================================================
print("=" * 100)
print("SECTION 7: ONGOING MONITORING & VERIFICATION")
print("=" * 100)
print()

print("📊 KEY METRICS TO MONITOR:")
print()

print("1. Storage Pool Free Space Trend")
print("   - Track % free daily")
print("   - Expected: Stable or increasing (if pruning works)")
print("   - Alert: Decreasing trend = pruning not keeping up")
print()

print("2. Pending Delete Queue (Dedup Pools)")
print("   - Query: Check SIDBEngine.log for 'Pending Deletes' count")
print("   - Expected: <10,000")
print("   - Alert: >100,000 = severe pruning backlog")
print()

print("3. Mark and Sweep Operation")
print("   - Query: Check SIDBEngine.log for 'Mark And Sweep.Last Run'")
print("   - Expected: Daily execution")
print("   - Alert: No execution in 7+ days = pruning stalled")
print()

print("4. MMDeletedAF Table Row Count")
print("   - Query: SELECT COUNT(*) FROM MMDeletedAF (CommServe database)")
print("   - Expected: Low count (aged jobs quickly pruned)")
print("   - Alert: High/growing count = pruning backlog")
print()

print("5. Pruning Job Success Rate")
print("   - Location: Job Controller → Filter by 'Pruning'")
print("   - Expected: >95% success rate")
print("   - Alert: Failed jobs or 0 bytes pruned")
print()

# ============================================================================
# SECTION 8: DECISION TREE
# ============================================================================
print("=" * 100)
print("SECTION 8: PRUNING STRATEGY DECISION TREE")
print("=" * 100)
print()

print("🌳 USE THIS DECISION TREE TO CHOOSE PRUNING STRATEGY:")
print()
print("START: What type of storage?")
print("│")
print("├─ DEDUPLICATION STORAGE")
print("│  │")
print("│  ├─ Q: Is WORM/Immutability enabled?")
print("│  │  ├─ YES → MACRO PRUNING (Required)")
print("│  │  │        ├─ Plan for 3x retention capacity")
print("│  │  │        ├─ Seal DDB periodically (6-12 months)")
print("│  │  │        └─ Macro prune after full aging")
print("│  │  │")
print("│  │  └─ NO → MICROPRUNING (Recommended)")
print("│  │           ├─ Enabled by default")
print("│  │           ├─ Gradual space reclamation")
print("│  │           └─ Monitor SIDBPrune.log")
print("│")
print("├─ CLOUD STORAGE")
print("│  │")
print("│  ├─ Q: Is this Archive Cloud?")
print("│  │  ├─ YES → MACRO PRUNING (Required)")
print("│  │  │        └─ Micropruning impractical on archive")
print("│  │  │")
print("│  │  └─ NO → Check WORM status")
print("│  │           ├─ WORM enabled → MACRO PRUNING")
print("│  │           └─ WORM disabled → MICROPRUNING (Default)")
print("│")
print("├─ NON-DEDUP DISK")
print("│  │")
print("│  └─ DIRECT DELETION (Simplest)")
print("│     ├─ Job ages → Files deleted")
print("│     ├─ No DDB complexity")
print("│     └─ Monitor CVMA.log")
print("│")
print("└─ TAPE")
print("   │")
print("   └─ TAPE RECLAMATION")
print("      ├─ Different process (not pruning)")
print("      └─ Refer to tape reclamation docs")
print()

# ============================================================================
# SECTION 9: EXECUTIVE SUMMARY
# ============================================================================
print("=" * 100)
print("SECTION 9: EXECUTIVE SUMMARY")
print("=" * 100)
print()

print("📋 ENVIRONMENT OVERVIEW:")
print()
print(f"  Total Storage Pools: {len(storage_pools)}")
print(f"    - Dedup Pools: {len(dedup_pools)} (Micropruning recommended)")
print(f"    - Non-Dedup: {len(non_dedup_pools)} (Direct deletion)")
print(f"    - Cloud Pools: {len(cloud_pools)} (Verify WORM status)")
print()

print(f"  Pruning Health:")
print(f"    - ✅ Healthy (>30% free): {len(micropruning_healthy)} pools")
print(f"    - 🔴 Critical (<20% free): {len(micropruning_failing)} pools")
print()

if micropruning_failing:
    print(f"  ⚠️  CRITICAL FINDING:")
    print(f"    {len(micropruning_failing)} pools critically low on space")
    print(f"    This is PROOF that pruning (micropruning) is NOT working!")
    print()

print("🎯 RECOMMENDED PRUNING STRATEGY:")
print()
print("  Primary Strategy: MICROPRUNING")
print("    - Used by: Most dedup and cloud pools")
print("    - Benefit: Gradual space reclamation, lower capacity needs")
print("    - Status: Currently FAILING (evidence: critical pools)")
print()
print("  Exception: MACRO PRUNING")
print("    - Required for: WORM storage, archive cloud")
print("    - Trade-off: 3x capacity requirement")
print("    - Action: Verify if any pools require this")
print()

print("🚀 NEXT STEPS:")
print()
print("  1. Execute troubleshooting steps for critical pools (Section 6)")
print("  2. Verify micropruning is enabled on all dedup pools")
print("  3. Check for WORM-enabled pools requiring macro pruning")
print("  4. Implement monitoring for key pruning metrics (Section 7)")
print("  5. Re-run this analysis in 7 days to verify improvements")
print()

print("=" * 100)
print("ANALYSIS COMPLETE")
print("=" * 100)
print()
print("📄 Review sections above for detailed findings and recommendations")
print("🔧 Implement priority actions to restore pruning functionality")
print("📊 Monitor key metrics to track improvement")
print()

conn.close()
