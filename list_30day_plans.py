import sqlite3
from collections import defaultdict
import sys

# Set UTF-8 encoding for output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect('Database/commvault.db')
cur = conn.cursor()

# Get all retention rules with 30-day retention
cur.execute('''
    SELECT DISTINCT
        parentName,
        entityName,
        retainBackupDataForDays,
        retainBackupDataForCycles,
        enableDataAging
    FROM retention_rules
    WHERE retainBackupDataForDays = 30
    ORDER BY parentName, entityName
''')

rules = cur.fetchall()

print('=' * 100)
print('COMPLETE LIST OF PLANS WITH 30-DAY RETENTION')
print('=' * 100)
print()
print(f'Total Plans/Copies with 30-day retention: {len(rules)}')
print()

# Group by plan
plans_dict = defaultdict(list)
for rule in rules:
    plan_name, copy_name, days, cycles, aging = rule
    plans_dict[plan_name].append((copy_name, days, cycles, aging))

print(f'Unique Plans: {len(plans_dict)}')
print()
print('=' * 100)
print('DETAILED LIST WITH COPY INFORMATION')
print('=' * 100)
print()

# Print detailed list
for idx, (plan_name, copies) in enumerate(sorted(plans_dict.items()), 1):
    print(f'{idx:3}. {plan_name}')
    for copy_name, days, cycles, aging in copies:
        aging_status = 'Enabled' if aging == 1 else 'Disabled'
        print(f'     - Copy: {copy_name}')
        print(f'       Retention: {days} days, {cycles} cycles, Aging: {aging_status}')
    print()

print()
print('=' * 100)
print('SIMPLE LIST (PLAN NAMES ONLY)')
print('=' * 100)
print()

for idx, plan_name in enumerate(sorted(plans_dict.keys()), 1):
    copy_count = len(plans_dict[plan_name])
    print(f'{idx:3}. {plan_name} ({copy_count} {"copy" if copy_count == 1 else "copies"})')

print()
print('=' * 100)
print('COPY-SEPARATED LIST')
print('=' * 100)
print()

print(f'{"#":<5} {"Plan Name":<50} {"Copy Name":<30} {"Days":<6} {"Cycles":<7} {"Aging"}')
print('-' * 100)

for idx, (plan_name, copy_name, days, cycles, aging) in enumerate(rules, 1):
    aging_status = 'Yes' if aging == 1 else 'No'
    print(f'{idx:<5} {plan_name:<50} {copy_name:<30} {days:<6} {cycles:<7} {aging_status}')

conn.close()
