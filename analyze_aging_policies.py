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

print("=" * 80)
print("AGING POLICY ANALYSIS REPORT")
print("=" * 80)
print()

# Get all retention rules
cur.execute("""
    SELECT
        ruleId,
        entityType,
        entityName,
        parentId,
        parentName,
        retainBackupDataForDays,
        retainBackupDataForCycles,
        retainArchiverDataForDays,
        enableDataAging,
        jobBasedRetention
    FROM retention_rules
    ORDER BY parentName, entityName
""")

rules = cur.fetchall()

# Data structures for analysis
plans_by_days = defaultdict(list)
plans_with_30_days = []
plans_with_14_days = []
aging_enabled_count = 0
aging_disabled_count = 0
infinite_retention_plans = []
unique_plans = set()

print(f"Total Retention Rules: {len(rules)}")
print(f"Total Plans: {len(set(rule[4] for rule in rules))}")
print()

# Analyze each retention rule
for rule in rules:
    rule_id, entity_type, entity_name, parent_id, parent_name, days, cycles, archive_days, aging_enabled, job_based = rule

    unique_plans.add(parent_name)

    # Count aging enabled/disabled
    if aging_enabled == 1:
        aging_enabled_count += 1
    else:
        aging_disabled_count += 1

    # Check for infinite retention
    if days == -1 or cycles == -1:
        infinite_retention_plans.append((parent_name, entity_name, days, cycles))

    # Group by retention days
    if days is not None and days > 0:
        plans_by_days[days].append((parent_name, entity_name))

        # Special tracking for 30 and 14 days
        if days == 30:
            plans_with_30_days.append((parent_name, entity_name))
        elif days == 14:
            plans_with_14_days.append((parent_name, entity_name))

print("=" * 80)
print("AGING STATUS SUMMARY")
print("=" * 80)
print(f"Retention Rules with Aging ENABLED:  {aging_enabled_count} ({aging_enabled_count/len(rules)*100:.1f}%)")
print(f"Retention Rules with Aging DISABLED: {aging_disabled_count} ({aging_disabled_count/len(rules)*100:.1f}%)")
print()

print("=" * 80)
print("RETENTION DAYS DISTRIBUTION")
print("=" * 80)
print(f"{'Retention Days':<20} {'Count':<10} {'Plans/Copies'}")
print("-" * 80)

# Sort by retention days
for days in sorted(plans_by_days.keys()):
    count = len(plans_by_days[days])
    print(f"{days:>15} days {count:>10}     {', '.join(set([p[0] for p in plans_by_days[days][:3]]))[:50]}...")

print()

print("=" * 80)
print("SPECIFIC RETENTION PERIOD COUNTS")
print("=" * 80)
print(f"Plans/Copies with 30-DAY retention: {len(plans_with_30_days)}")
print(f"Plans/Copies with 14-DAY retention: {len(plans_with_14_days)}")
print()

# Count unique plans (not copies)
unique_30_day_plans = set([p[0] for p in plans_with_30_days])
unique_14_day_plans = set([p[0] for p in plans_with_14_days])

print(f"Unique PLANS with 30-day retention: {len(unique_30_day_plans)}")
print(f"Unique PLANS with 14-day retention: {len(unique_14_day_plans)}")
print()

print("=" * 80)
print("30-DAY RETENTION POLICIES")
print("=" * 80)
if plans_with_30_days:
    current_plan = None
    for plan_name, copy_name in sorted(plans_with_30_days):
        if plan_name != current_plan:
            print(f"\n📦 {plan_name}")
            current_plan = plan_name
        print(f"   └─ Copy: {copy_name}")
else:
    print("No 30-day retention policies found")

print()
print("=" * 80)
print("14-DAY RETENTION POLICIES")
print("=" * 80)
if plans_with_14_days:
    current_plan = None
    for plan_name, copy_name in sorted(plans_with_14_days):
        if plan_name != current_plan:
            print(f"\n📦 {plan_name}")
            current_plan = plan_name
        print(f"   └─ Copy: {copy_name}")
else:
    print("No 14-day retention policies found")

print()
print("=" * 80)
print("INFINITE RETENTION POLICIES")
print("=" * 80)
if infinite_retention_plans:
    print(f"Total: {len(infinite_retention_plans)}")
    print()
    current_plan = None
    for plan_name, copy_name, days, cycles in sorted(infinite_retention_plans):
        if plan_name != current_plan:
            print(f"\n📦 {plan_name}")
            current_plan = plan_name
        retention_type = "Days=-1" if days == -1 else f"Cycles={cycles}"
        print(f"   └─ Copy: {copy_name} ({retention_type})")
else:
    print("No infinite retention policies found")

print()
print("=" * 80)
print("DETAILED AGING POLICY TABLE")
print("=" * 80)

# Get detailed info with calculated effective retention
cur.execute("""
    SELECT
        parentName,
        entityName,
        retainBackupDataForDays,
        retainBackupDataForCycles,
        retainArchiverDataForDays,
        enableDataAging,
        jobBasedRetention
    FROM retention_rules
    WHERE entityType = 'plan_copy'
    ORDER BY parentName, entityName
""")

print(f"\n{'Plan Name':<40} {'Copy Name':<30} {'Days':<8} {'Cycles':<8} {'Archive':<10} {'Aging':<8}")
print("-" * 120)

for row in cur.fetchall():
    plan_name, copy_name, days, cycles, archive_days, aging, job_based = row

    days_str = "∞" if days == -1 else (str(days) if days else "N/A")
    cycles_str = "∞" if cycles == -1 else (str(cycles) if cycles else "N/A")
    archive_str = "∞" if archive_days == -1 else (str(archive_days) if archive_days and archive_days > 0 else "N/A")
    aging_str = "Enabled" if aging == 1 else "Disabled"

    print(f"{plan_name[:39]:<40} {copy_name[:29]:<30} {days_str:<8} {cycles_str:<8} {archive_str:<10} {aging_str:<8}")

print()
print("=" * 80)
print("STATISTICS BY PLAN")
print("=" * 80)

# Get statistics per plan
cur.execute("""
    SELECT
        parentName,
        COUNT(*) as copy_count,
        MIN(retainBackupDataForDays) as min_days,
        MAX(retainBackupDataForDays) as max_days,
        AVG(retainBackupDataForDays) as avg_days,
        SUM(CASE WHEN enableDataAging = 1 THEN 1 ELSE 0 END) as aging_enabled_copies
    FROM retention_rules
    WHERE entityType = 'plan_copy'
    GROUP BY parentName
    ORDER BY avg_days DESC
""")

print(f"\n{'Plan Name':<50} {'Copies':<8} {'Min Days':<10} {'Max Days':<10} {'Avg Days':<10} {'Aging On'}")
print("-" * 120)

for row in cur.fetchall():
    plan_name, copy_count, min_days, max_days, avg_days, aging_on = row

    min_str = "∞" if min_days == -1 else (str(min_days) if min_days else "N/A")
    max_str = "∞" if max_days == -1 else (str(max_days) if max_days else "N/A")
    avg_str = f"{avg_days:.1f}" if avg_days and avg_days > 0 else "N/A"

    print(f"{plan_name[:49]:<50} {copy_count:<8} {min_str:<10} {max_str:<10} {avg_str:<10} {aging_on}/{copy_count}")

print()
print("=" * 80)
print("REPORT COMPLETE")
print("=" * 80)

conn.close()
