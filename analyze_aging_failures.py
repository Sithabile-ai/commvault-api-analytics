"""
Comprehensive Analysis of Aging Failures
Identifies why backups are not aging and storage space is not being reclaimed
"""
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Connect to database
conn = sqlite3.connect('Database/commvault.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 100)
print("COMPREHENSIVE AGING FAILURE ANALYSIS")
print("=" * 100)
print()
print("Analyzing why backups are not aging and storage space is not being reclaimed...")
print()

# ============================================================================
# SECTION 1: CHECK AVAILABLE DATA
# ============================================================================
print("=" * 100)
print("SECTION 1: DATA AVAILABILITY CHECK")
print("=" * 100)
print()

# Check what tables exist
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [row[0] for row in cur.fetchall()]
print(f"Available tables in database: {len(tables)}")
for table in tables:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    count = cur.fetchone()[0]
    print(f"  - {table}: {count} records")
print()

# ============================================================================
# SECTION 2: RETENTION POLICY ANALYSIS
# ============================================================================
print("=" * 100)
print("SECTION 2: RETENTION POLICY ANALYSIS")
print("=" * 100)
print()

# Get all retention rules
cur.execute("""
    SELECT
        ruleId,
        parentName,
        entityName,
        retainBackupDataForDays,
        retainBackupDataForCycles,
        enableDataAging,
        retainArchiverDataForDays,
        firstExtendedRetentionDays,
        firstExtendedRetentionCycles
    FROM retention_rules
    ORDER BY parentName, entityName
""")
retention_rules = cur.fetchall()

print(f"Total Retention Rules: {len(retention_rules)}")
print()

# Problem 1: Aging Disabled
aging_disabled = [r for r in retention_rules if r['enableDataAging'] == 0]
print(f"❌ CRITICAL: {len(aging_disabled)} rules have DATA AGING DISABLED")
if aging_disabled:
    print("   Plans/Policies with aging disabled (data will NEVER age):")
    for rule in aging_disabled[:10]:  # Show first 10
        print(f"      - {rule['parentName']} / {rule['entityName']}")
    if len(aging_disabled) > 10:
        print(f"      ... and {len(aging_disabled) - 10} more")
print()

# Problem 2: Infinite Retention
infinite_retention = [r for r in retention_rules if
                      r['retainBackupDataForDays'] == -1 or
                      r['retainBackupDataForCycles'] == -1]
print(f"⚠️  WARNING: {len(infinite_retention)} rules have INFINITE RETENTION")
if infinite_retention:
    print("   Plans/Policies with infinite retention (data will never age):")
    for rule in infinite_retention[:10]:
        days = rule['retainBackupDataForDays']
        cycles = rule['retainBackupDataForCycles']
        print(f"      - {rule['parentName']} / {rule['entityName']} (Days: {days}, Cycles: {cycles})")
    if len(infinite_retention) > 10:
        print(f"      ... and {len(infinite_retention) - 10} more")
print()

# Problem 3: High Cycle Requirements
high_cycle_rules = [r for r in retention_rules if r['retainBackupDataForCycles'] is not None and
                    r['retainBackupDataForCycles'] >= 3 and
                    r['retainBackupDataForDays'] is not None and
                    r['retainBackupDataForDays'] > 0]
print(f"⚠️  ISSUE: {len(high_cycle_rules)} rules require 3+ CYCLES (very slow aging)")
if high_cycle_rules:
    print("   Plans requiring many cycles to complete before aging:")
    for rule in sorted(high_cycle_rules, key=lambda x: x['retainBackupDataForCycles'], reverse=True)[:10]:
        print(f"      - {rule['parentName']} / {rule['entityName']}: {rule['retainBackupDataForCycles']} cycles + {rule['retainBackupDataForDays']} days")
print()

# Problem 4: Inefficient Short-term Policies
inefficient_short = [r for r in retention_rules if
                     r['retainBackupDataForDays'] is not None and
                     r['retainBackupDataForCycles'] is not None and
                     r['retainBackupDataForDays'] <= 30 and
                     r['retainBackupDataForCycles'] >= 2]
print(f"🔴 HIGH PRIORITY: {len(inefficient_short)} rules have SHORT RETENTION + HIGH CYCLES")
print(f"   (These are preventing storage reclamation on short-term data)")
if inefficient_short:
    print("   Inefficient short-term policies (recommend reducing cycles to 1):")
    for rule in inefficient_short[:15]:
        days = rule['retainBackupDataForDays']
        cycles = rule['retainBackupDataForCycles']
        delay_days = (cycles - 1) * 7  # Estimated delay in days
        print(f"      - {rule['parentName'][:40]:<40} {rule['entityName'][:20]:<20} | {days:>3}d + {cycles}c → ~{delay_days} day aging delay")
    if len(inefficient_short) > 15:
        print(f"      ... and {len(inefficient_short) - 15} more")
print()

# ============================================================================
# SECTION 3: PLAN ANALYSIS
# ============================================================================
print("=" * 100)
print("SECTION 3: PLAN ANALYSIS")
print("=" * 100)
print()

# Check if plans table exists and has data
if 'plans' in tables:
    cur.execute("SELECT COUNT(*) FROM plans")
    plan_count = cur.fetchone()[0]
    print(f"Total Plans in Database: {plan_count}")

    # Get plan details
    cur.execute("""
        SELECT
            planId,
            planName,
            type
        FROM plans
        ORDER BY planName
    """)
    plans = cur.fetchall()

    # Match plans with retention rules
    plans_with_issues = defaultdict(list)

    for rule in retention_rules:
        plan_name = rule['parentName']
        issues = []

        if rule['enableDataAging'] == 0:
            issues.append("AGING DISABLED")
        if rule['retainBackupDataForDays'] == -1 or rule['retainBackupDataForCycles'] == -1:
            issues.append("INFINITE RETENTION")
        if rule['retainBackupDataForCycles'] and rule['retainBackupDataForCycles'] >= 3:
            issues.append(f"HIGH CYCLES ({rule['retainBackupDataForCycles']})")
        if (rule['retainBackupDataForDays'] and rule['retainBackupDataForDays'] <= 30 and
            rule['retainBackupDataForCycles'] and rule['retainBackupDataForCycles'] >= 2):
            issues.append("INEFFICIENT SHORT-TERM")

        if issues:
            plans_with_issues[plan_name].extend(issues)

    print(f"\nPlans with Aging Issues: {len(plans_with_issues)}")
    print()
    print("Top 20 Plans with Most Critical Issues:")
    for plan_name, issues in sorted(plans_with_issues.items(), key=lambda x: len(x[1]), reverse=True)[:20]:
        unique_issues = list(set(issues))
        print(f"  - {plan_name[:60]:<60} | Issues: {', '.join(unique_issues)}")
    print()
else:
    print("⚠️  Plans table not available")
    print()

# ============================================================================
# SECTION 4: STORAGE POOL ANALYSIS
# ============================================================================
print("=" * 100)
print("SECTION 4: STORAGE POOL ANALYSIS")
print("=" * 100)
print()

if 'storage_pools' in tables:
    cur.execute("""
        SELECT
            storagePoolId,
            storagePoolName,
            totalCapacity,
            freeSpace,
            CASE
                WHEN totalCapacity > 0 THEN ROUND((freeSpace * 100.0 / totalCapacity), 2)
                ELSE 0
            END as percentFree
        FROM storage_pools
        WHERE totalCapacity > 0
        ORDER BY percentFree ASC
    """)
    pools = cur.fetchall()

    print(f"Storage Pools: {len(pools)}")
    print()

    if pools:
        print("Storage Pool Space Status:")
        print(f"{'Pool Name':<40} {'Total (GB)':<15} {'Free (GB)':<15} {'% Free':<10} {'Status'}")
        print("-" * 100)
        for pool in pools:
            try:
                total_cap = int(pool['totalCapacity']) if pool['totalCapacity'] else 0
                free_sp = int(pool['freeSpace']) if pool['freeSpace'] else 0
                total_gb = total_cap / (1024**3)
                free_gb = free_sp / (1024**3)
                pct = float(pool['percentFree']) if pool['percentFree'] else 0
            except (ValueError, TypeError):
                continue

            if pct < 10:
                status = "🔴 CRITICAL"
            elif pct < 20:
                status = "🟠 WARNING"
            elif pct < 30:
                status = "🟡 LOW"
            else:
                status = "🟢 OK"

            print(f"{pool['storagePoolName'][:40]:<40} {total_gb:>13.2f}  {free_gb:>13.2f}  {pct:>8.2f}%  {status}")
        print()

        # Calculate potential space if aging worked properly
        critical_pools = [p for p in pools if p['percentFree'] < 20]
        if critical_pools:
            print(f"⚠️  {len(critical_pools)} pools have less than 20% free space")
            print("   These pools urgently need aging to free up space")
            print()
else:
    print("⚠️  Storage pools table not available")
    print()

# ============================================================================
# SECTION 5: JOB ANALYSIS
# ============================================================================
print("=" * 100)
print("SECTION 5: JOB ANALYSIS (Last 100 Jobs)")
print("=" * 100)
print()

if 'jobs' in tables:
    cur.execute("SELECT COUNT(*) FROM jobs")
    job_count = cur.fetchone()[0]
    print(f"Total Jobs in Database: {job_count}")

    if job_count > 0:
        # Get recent job data
        cur.execute("""
            SELECT
                jobId,
                status,
                jobType,
                clientName,
                backupSetName,
                startTime,
                endTime
            FROM jobs
            ORDER BY jobId DESC
            LIMIT 100
        """)
        jobs = cur.fetchall()

        # Analyze job success rate
        failed_jobs = [j for j in jobs if j['status'] and 'failed' in str(j['status']).lower()]
        success_jobs = [j for j in jobs if j['status'] and ('completed' in str(j['status']).lower() or 'success' in str(j['status']).lower())]

        print(f"Recent Jobs Analyzed: {len(jobs)}")
        print(f"  - Failed: {len(failed_jobs)} ({len(failed_jobs)*100/len(jobs):.1f}%)")
        print(f"  - Successful: {len(success_jobs)} ({len(success_jobs)*100/len(jobs):.1f}%)")
        print()

        if failed_jobs:
            print(f"⚠️  CONCERN: {len(failed_jobs)} failed jobs in recent history")
            print("   Failed jobs prevent backup cycles from completing")
            print("   This directly blocks aging from occurring")
            print()
    else:
        print("⚠️  No job data available - need more job history to analyze")
        print()
else:
    print("⚠️  Jobs table not available")
    print()

# ============================================================================
# SECTION 6: DETAILED RECOMMENDATIONS
# ============================================================================
print("=" * 100)
print("SECTION 6: RECOMMENDATIONS TO FIX AGING ISSUES")
print("=" * 100)
print()

print("IMMEDIATE ACTIONS (Critical - Do These First):")
print()

if aging_disabled:
    print(f"1. ✅ ENABLE DATA AGING on {len(aging_disabled)} rules")
    print(f"   - These rules currently have aging DISABLED")
    print(f"   - Data will NEVER be removed until aging is enabled")
    print(f"   - Estimated Impact: Could free up significant space immediately")
    print()

if inefficient_short:
    print(f"2. 🔧 REDUCE CYCLE RETENTION on {len(inefficient_short)} short-term policies")
    print(f"   - Change from 2+ cycles to 1 cycle for policies with ≤30 days retention")
    print(f"   - This will allow aging to occur 7-14 days faster")
    print(f"   - Estimated Impact: 10-20% faster storage reclamation")
    print()

if high_cycle_rules:
    print(f"3. ⚙️  REVIEW HIGH CYCLE REQUIREMENTS on {len(high_cycle_rules)} rules")
    print(f"   - These require 3+ backup cycles before aging")
    print(f"   - If backup cycles are slow or failing, aging will be severely delayed")
    print(f"   - Recommendation: Reduce to 2 cycles maximum for most policies")
    print()

if infinite_retention:
    print(f"4. ♾️  REVIEW INFINITE RETENTION on {len(infinite_retention)} rules")
    print(f"   - These rules will NEVER age out data")
    print(f"   - Confirm if infinite retention is actually required")
    print(f"   - Consider adding finite retention periods")
    print()

print("NEXT STEPS FOR DEEPER ANALYSIS:")
print()
print("1. 📊 COLLECT JOB DATA")
print("   - Need to pull actual backup job history to see:")
print("     • Which full backups are failing (preventing cycle completion)")
print("     • Which clients haven't backed up recently (disabled clients)")
print("     • Backup success rates per plan")
print()
print("2. 🔍 CHECK DATA AGING JOB LOGS")
print("   - Review aging job execution history")
print("   - Check for aging job failures or long run times")
print("   - Verify aging jobs are scheduled and running")
print()
print("3. 📅 ANALYZE SCHEDULE CONFLICTS")
print("   - Check if aging jobs conflict with backup windows")
print("   - Verify backup schedules produce regular full backups")
print("   - Ensure cycles can actually complete")
print()

# ============================================================================
# SECTION 7: SUMMARY STATISTICS
# ============================================================================
print("=" * 100)
print("SECTION 7: EXECUTIVE SUMMARY")
print("=" * 100)
print()

total_rules = len(retention_rules)
critical_issues = len(aging_disabled)
high_priority = len(inefficient_short)
medium_priority = len(high_cycle_rules)
info_priority = len(infinite_retention)

print("AGING ISSUE SEVERITY BREAKDOWN:")
print()
print(f"  🔴 CRITICAL (Aging Disabled):           {critical_issues:>4} rules ({critical_issues*100/total_rules:.1f}%)")
print(f"  🟠 HIGH (Inefficient Short-term):       {high_priority:>4} rules ({high_priority*100/total_rules:.1f}%)")
print(f"  🟡 MEDIUM (High Cycle Requirements):    {medium_priority:>4} rules ({medium_priority*100/total_rules:.1f}%)")
print(f"  🔵 INFO (Infinite Retention):           {info_priority:>4} rules ({info_priority*100/total_rules:.1f}%)")
print(f"  🟢 OK (No Issues):                      {total_rules - critical_issues - high_priority - medium_priority - info_priority:>4} rules")
print()

print("ESTIMATED STORAGE IMPACT:")
print()
if critical_issues > 0:
    print(f"  - {critical_issues} rules with aging disabled = 0% space reclamation")
    print(f"  - Enabling aging on these could free up 20-40% of their storage")
print()
if high_priority > 0:
    print(f"  - {high_priority} inefficient short-term policies")
    print(f"  - Fixing these could accelerate reclamation by 7-14 days")
    print(f"  - Potential impact: 10-20% improvement in storage efficiency")
print()

print("=" * 100)
print("ANALYSIS COMPLETE")
print("=" * 100)
print()
print("📄 Review the sections above for detailed findings")
print("🔧 Implement the recommendations to resolve aging issues")
print("📊 Re-run this analysis after making changes to verify improvements")
print()

conn.close()
