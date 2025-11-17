"""
Analyze Aging Policy and Schedule Conflicts
Identifies issues that may prevent storage space reclamation
"""
import sqlite3
from collections import defaultdict
import sys

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Connect to database
conn = sqlite3.connect('Database/commvault.db')
cur = conn.cursor()

print("=" * 100)
print("AGING POLICY & SCHEDULE CONFLICT ANALYSIS")
print("=" * 100)
print()
print("Objective: Identify conflicts preventing storage space reclamation")
print()

# Get basic stats
cur.execute("SELECT COUNT(*) FROM retention_rules")
total_rules = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM retention_rules WHERE enableDataAging = 1")
aging_enabled = cur.fetchone()[0]

print(f"Total Retention Rules: {total_rules}")
print(f"Rules with Aging Enabled: {aging_enabled}")
print()

print("=" * 100)
print("CONFLICT #1: CYCLE RETENTION BLOCKING AGING")
print("=" * 100)
print()
print("Plans where cycle retention may extend data retention significantly beyond days setting")
print()

cur.execute("""
    SELECT
        parentName AS PlanName,
        entityName AS CopyName,
        retainBackupDataForDays AS ConfigDays,
        retainBackupDataForCycles AS Cycles,
        (retainBackupDataForCycles * 7) AS EstCycleDays,
        CASE
            WHEN retainBackupDataForDays > (retainBackupDataForCycles * 7)
            THEN retainBackupDataForDays
            ELSE (retainBackupDataForCycles * 7)
        END AS EffectiveDays,
        ((retainBackupDataForCycles * 7) - retainBackupDataForDays) AS ExtraDays
    FROM retention_rules
    WHERE retainBackupDataForDays > 0
      AND retainBackupDataForCycles > 0
      AND (retainBackupDataForCycles * 7) > retainBackupDataForDays
      AND enableDataAging = 1
    ORDER BY ExtraDays DESC
    LIMIT 20
""")

results = cur.fetchall()
if results:
    print(f"{'Plan Name':<40} {'Copy':<25} {'Days':>6} {'Cycles':>7} {'Est Days':>9} {'Effective':>10} {'Extra':>6}")
    print("-" * 100)
    for row in results:
        plan, copy, days, cycles, est_days, eff_days, extra = row
        print(f"{plan[:39]:<40} {copy[:24]:<25} {days:>6} {cycles:>7} {est_days:>9} {eff_days:>10} {extra:>6}")

    print()
    print(f"⚠️  Found {len(results)} plans where cycles extend retention")
    print(f"💡 Impact: Data held {sum(r[6] for r in results) / len(results):.0f} days longer on average than days setting")
else:
    print("✅ No significant cycle extension issues found")

print()
print("=" * 100)
print("CONFLICT #2: HIGH CYCLE RETENTION (Storage Bloat Risk)")
print("=" * 100)
print()
print("Plans requiring multiple backup cycles before aging (vulnerable to backup failures)")
print()

cur.execute("""
    SELECT
        parentName AS PlanName,
        COUNT(*) AS CopiesCount,
        AVG(retainBackupDataForDays) AS AvgDays,
        AVG(retainBackupDataForCycles) AS AvgCycles,
        MAX(retainBackupDataForCycles) AS MaxCycles,
        CASE
            WHEN MAX(retainBackupDataForCycles) >= 3 THEN 'HIGH RISK'
            WHEN MAX(retainBackupDataForCycles) = 2 THEN 'MEDIUM RISK'
            ELSE 'LOW RISK'
        END AS RiskLevel
    FROM retention_rules
    WHERE retainBackupDataForCycles >= 2
      AND enableDataAging = 1
    GROUP BY parentName
    ORDER BY MaxCycles DESC, AvgDays
    LIMIT 30
""")

results = cur.fetchall()
if results:
    print(f"{'Plan Name':<50} {'Copies':>7} {'Avg Days':>9} {'Avg Cycles':>11} {'Max Cycles':>11} {'Risk Level'}")
    print("-" * 100)
    high_risk = 0
    medium_risk = 0
    for row in results:
        plan, copies, avg_days, avg_cycles, max_cycles, risk = row
        print(f"{plan[:49]:<50} {copies:>7} {avg_days:>9.1f} {avg_cycles:>11.1f} {max_cycles:>11} {risk}")
        if risk == 'HIGH RISK':
            high_risk += 1
        elif risk == 'MEDIUM RISK':
            medium_risk += 1

    print()
    print(f"⚠️  HIGH RISK: {high_risk} plans (3+ cycles required)")
    print(f"⚠️  MEDIUM RISK: {medium_risk} plans (2 cycles required)")
    print(f"💡 Recommendation: Reduce cycle retention to 1 for faster storage reclamation")
else:
    print("✅ No high cycle retention issues found")

print()
print("=" * 100)
print("CONFLICT #3: SHORT DAYS + MULTIPLE CYCLES (Inefficient Aging)")
print("=" * 100)
print()
print("Plans with short retention days but multiple cycles (aging delayed despite short policy)")
print()

cur.execute("""
    SELECT
        parentName AS PlanName,
        entityName AS CopyName,
        retainBackupDataForDays AS Days,
        retainBackupDataForCycles AS Cycles,
        (retainBackupDataForCycles * 7) AS EffectiveDays,
        ((retainBackupDataForCycles * 7) - retainBackupDataForDays) AS Delay
    FROM retention_rules
    WHERE retainBackupDataForDays <= 30
      AND retainBackupDataForDays > 0
      AND retainBackupDataForCycles >= 2
      AND enableDataAging = 1
    ORDER BY Delay DESC
    LIMIT 20
""")

results = cur.fetchall()
if results:
    print(f"{'Plan Name':<40} {'Copy':<25} {'Days':>6} {'Cycles':>7} {'Effective':>10} {'Delay':>6}")
    print("-" * 100)
    for row in results:
        plan, copy, days, cycles, effective, delay = row
        print(f"{plan[:39]:<40} {copy[:24]:<25} {days:>6} {cycles:>7} {effective:>10} {delay:>6}")

    print()
    print(f"⚠️  Found {len(results)} plans with inefficient short-term retention")
    print(f"💡 Example: 14-day retention + 2 cycles = effectively 14+ days (cycles must complete)")
    print(f"💡 Solution: Change to 1 cycle for these short-retention plans")
else:
    print("✅ No inefficient short-term retention patterns found")

print()
print("=" * 100)
print("CONFLICT #4: SINGLE CYCLE VULNERABILITY")
print("=" * 100)
print()
print("Plans with 1 cycle + long retention (vulnerable to backup failures blocking aging)")
print()

cur.execute("""
    SELECT
        parentName AS PlanName,
        entityName AS CopyName,
        retainBackupDataForDays AS Days,
        retainBackupDataForCycles AS Cycles,
        CASE
            WHEN retainBackupDataForDays >= 90 THEN 'HIGH VULNERABILITY'
            WHEN retainBackupDataForDays >= 30 THEN 'MEDIUM VULNERABILITY'
            ELSE 'LOW VULNERABILITY'
        END AS Vulnerability
    FROM retention_rules
    WHERE retainBackupDataForCycles = 1
      AND retainBackupDataForDays >= 30
      AND retainBackupDataForDays > 0
      AND enableDataAging = 1
    ORDER BY Days DESC
    LIMIT 30
""")

results = cur.fetchall()
if results:
    print(f"{'Plan Name':<40} {'Copy':<25} {'Days':>6} {'Cycles':>7} {'Vulnerability Level'}")
    print("-" * 100)
    high_vuln = 0
    medium_vuln = 0
    for row in results:
        plan, copy, days, cycles, vuln = row
        print(f"{plan[:39]:<40} {copy[:24]:<25} {days:>6} {cycles:>7} {vuln}")
        if vuln == 'HIGH VULNERABILITY':
            high_vuln += 1
        elif vuln == 'MEDIUM VULNERABILITY':
            medium_vuln += 1

    print()
    print(f"⚠️  HIGH VULNERABILITY: {high_vuln} plans (90+ days with only 1 cycle)")
    print(f"⚠️  MEDIUM VULNERABILITY: {medium_vuln} plans (30+ days with only 1 cycle)")
    print(f"💡 Impact: If full backup fails, all {len(results)} plans cannot age data")
    print(f"💡 Solution: Increase to 2 cycles OR monitor backup success rate closely")
else:
    print("✅ No single-cycle vulnerability issues found")

print()
print("=" * 100)
print("STORAGE OPTIMIZATION SUMMARY")
print("=" * 100)
print()

# Calculate potential storage impact
cur.execute("""
    SELECT
        COUNT(*) AS PlanCount,
        AVG(retainBackupDataForDays) AS AvgDays,
        AVG(retainBackupDataForCycles) AS AvgCycles,
        AVG((retainBackupDataForCycles * 7)) AS AvgCycleDays,
        AVG(CASE
            WHEN retainBackupDataForDays > (retainBackupDataForCycles * 7)
            THEN retainBackupDataForDays
            ELSE (retainBackupDataForCycles * 7)
        END) AS AvgEffectiveDays
    FROM retention_rules
    WHERE retainBackupDataForDays > 0
      AND retainBackupDataForCycles > 0
      AND enableDataAging = 1
""")

stats = cur.fetchone()
if stats:
    plan_count, avg_days, avg_cycles, avg_cycle_days, avg_effective = stats
    overhead = avg_effective - avg_days

    print(f"Overall Retention Statistics:")
    print(f"  - Plans Analyzed: {plan_count}")
    print(f"  - Average Configured Days: {avg_days:.1f} days")
    print(f"  - Average Cycles: {avg_cycles:.1f}")
    print(f"  - Average Cycle Duration: {avg_cycle_days:.1f} days")
    print(f"  - Average EFFECTIVE Retention: {avg_effective:.1f} days")
    print()
    if overhead > 0:
        print(f"⚠️  Storage Overhead: {overhead:.1f} days")
        print(f"💡 Data is held {overhead:.1f} days longer than days setting suggests")
    else:
        print(f"✅ No significant storage overhead detected")

print()
print("=" * 100)
print("RECOMMENDATIONS FOR STORAGE SPACE RECLAMATION")
print("=" * 100)
print()

recommendations = []

# Check for high cycle counts
cur.execute("""
    SELECT COUNT(DISTINCT parentName)
    FROM retention_rules
    WHERE retainBackupDataForCycles >= 3
      AND enableDataAging = 1
""")
high_cycle_count = cur.fetchone()[0]
if high_cycle_count > 0:
    recommendations.append(f"1. REDUCE CYCLE RETENTION: {high_cycle_count} plans have 3+ cycles")
    recommendations.append(f"   → Change to 1-2 cycles for faster aging")
    recommendations.append(f"   → Priority: HIGH - Immediate storage impact")

# Check for short retention with multiple cycles
cur.execute("""
    SELECT COUNT(*)
    FROM retention_rules
    WHERE retainBackupDataForDays <= 30
      AND retainBackupDataForCycles >= 2
      AND enableDataAging = 1
""")
inefficient_count = cur.fetchone()[0]
if inefficient_count > 0:
    recommendations.append(f"2. FIX INEFFICIENT SHORT-TERM POLICIES: {inefficient_count} rules")
    recommendations.append(f"   → Plans with ≤30 days should use 1 cycle")
    recommendations.append(f"   → Priority: MEDIUM - Storage efficiency improvement")

# Check for single cycle with long retention
cur.execute("""
    SELECT COUNT(*)
    FROM retention_rules
    WHERE retainBackupDataForCycles = 1
      AND retainBackupDataForDays >= 60
      AND enableDataAging = 1
""")
vulnerable_count = cur.fetchone()[0]
if vulnerable_count > 0:
    recommendations.append(f"3. ADDRESS BACKUP FAILURE VULNERABILITY: {vulnerable_count} rules")
    recommendations.append(f"   → Plans with long retention + 1 cycle are at risk")
    recommendations.append(f"   → Priority: MEDIUM - Monitor backup success rates")

# Check overall effective retention
if stats and overhead > 7:
    recommendations.append(f"4. OPTIMIZE OVERALL RETENTION STRATEGY")
    recommendations.append(f"   → Average {overhead:.0f} days overhead from cycle retention")
    recommendations.append(f"   → Review cycle requirements across all plans")
    recommendations.append(f"   → Priority: LOW - Long-term optimization")

if recommendations:
    for rec in recommendations:
        print(rec)
else:
    print("✅ No major optimization opportunities identified")
    print("   Your retention policies appear well-configured")

print()
print("=" * 100)
print("NEXT ACTIONS")
print("=" * 100)
print()
print("1. Review plans flagged in conflicts above")
print("2. Check backup job success rates for high-risk plans")
print("3. Consider reducing cycle retention where appropriate")
print("4. Monitor storage space reclamation after aging jobs")
print("5. Test schedule endpoint to analyze backup timing conflicts")
print()
print("Run: python test_schedules_endpoint.py")
print("     to collect job schedule data for timing conflict analysis")
print()
print("=" * 100)

conn.close()
