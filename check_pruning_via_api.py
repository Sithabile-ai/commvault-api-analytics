"""
Check Pruning Activity via Commvault REST API
Alternative to pulling log files - uses API endpoints for Events and Jobs
"""

import requests
import base64
import json
import configparser
import sqlite3
from datetime import datetime, timedelta

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

BASE_URL = config.get('commvault', 'base_url')
USERNAME = config.get('commvault', 'username')
PASSWORD = config.get('commvault', 'password')

# Create authorization header
auth_string = f"{USERNAME}:{PASSWORD}"
auth_bytes = auth_string.encode('ascii')
base64_bytes = base64.b64encode(auth_bytes)
base64_auth = base64_bytes.decode('ascii')

headers = {
    'Authorization': f'Basic {base64_auth}',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

print("=" * 100)
print("PRUNING ACTIVITY CHECK - VIA REST API")
print("=" * 100)
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Connect to database to get critical pool info
conn = sqlite3.connect('Database/commvault.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get critical pools (<10% free)
cur.execute("""
    SELECT storagePoolId, storagePoolName, mediaAgentName, freeSpace, totalCapacity
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
                    'ma': pool['mediaAgentName'],
                    'pct_free': pct_free
                })
    except:
        continue

critical_pools.sort(key=lambda x: x['pct_free'])

print(f"CRITICAL POOLS IDENTIFIED: {len(critical_pools)}")
print()

for idx, pool in enumerate(critical_pools, 1):
    print(f"{idx}. {pool['name']}")
    print(f"   - Pool ID: {pool['id']}")
    print(f"   - MediaAgent: {pool['ma'] if pool['ma'] else 'N/A'}")
    print(f"   - Free Space: {pool['pct_free']:.2f}%")
    print()

print("=" * 100)
print("CHECKING PRUNING JOBS VIA API")
print("=" * 100)
print()

# API Endpoint 1: Get Jobs (Pruning/Auxiliary Copy jobs)
# Commvault API endpoint: /Job?jobFilter=Completed&jobFilter=Failed
try:
    jobs_url = f"{BASE_URL}/Job"

    # Calculate date range (last 7 days)
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)

    params = {
        'startTime': int(start_time.timestamp()),
        'endTime': int(end_time.timestamp()),
        'jobCategory': 'Auxiliary Copy'  # Pruning falls under Auxiliary Copy
    }

    print(f"Requesting jobs from API...")
    print(f"URL: {jobs_url}")
    print(f"Date Range: {start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}")
    print()

    response = requests.get(jobs_url, headers=headers, params=params, verify=False, timeout=30)

    print(f"Response Status: {response.status_code}")

    if response.status_code == 200:
        jobs_data = response.json()

        if 'jobs' in jobs_data:
            jobs = jobs_data['jobs']
            print(f"Total Jobs Retrieved: {len(jobs)}")
            print()

            # Filter for pruning-related jobs
            pruning_jobs = []
            for job in jobs:
                job_type = job.get('jobType', '').lower()
                subclient_name = job.get('subclient', {}).get('subclientName', '').lower()

                if 'prune' in job_type or 'prune' in subclient_name or job.get('jobType') == 'Auxiliary Copy':
                    pruning_jobs.append(job)

            print(f"Pruning-Related Jobs: {len(pruning_jobs)}")
            print()

            if pruning_jobs:
                print("RECENT PRUNING JOBS:")
                print("-" * 100)

                for job in pruning_jobs[:20]:  # Show last 20
                    job_id = job.get('jobId', 'N/A')
                    job_status = job.get('status', 'Unknown')
                    job_start = job.get('jobStartTime', 0)
                    job_end = job.get('jobEndTime', 0)

                    if job_start:
                        start_dt = datetime.fromtimestamp(job_start)
                        print(f"Job ID: {job_id}")
                        print(f"  Status: {job_status}")
                        print(f"  Started: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}")

                        if job_end:
                            end_dt = datetime.fromtimestamp(job_end)
                            duration = (job_end - job_start) / 60  # minutes
                            print(f"  Completed: {end_dt.strftime('%Y-%m-%d %H:%M:%S')} ({duration:.1f} min)")

                        # Check for errors
                        if job_status != 'Completed':
                            print(f"  ⚠️  WARNING: Job did not complete successfully!")

                        print()
            else:
                print("⚠️  WARNING: No pruning jobs found in last 7 days!")
                print("   This indicates pruning may not be running!")
                print()
        else:
            print("⚠️  No 'jobs' key in response")
            print(f"Response keys: {list(jobs_data.keys())}")
            print()
    else:
        print(f"❌ API request failed: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        print()

except requests.exceptions.RequestException as e:
    print(f"❌ Error connecting to API: {e}")
    print()
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    print()

print("=" * 100)
print("CHECKING EVENTS/ALERTS VIA API")
print("=" * 100)
print()

# API Endpoint 2: Get Events
try:
    events_url = f"{BASE_URL}/Events"

    params = {
        'level': 'Error,Warning',  # Get errors and warnings
        'showInfo': 'true'
    }

    print(f"Requesting events from API...")
    print(f"URL: {events_url}")
    print()

    response = requests.get(events_url, headers=headers, params=params, verify=False, timeout=30)

    print(f"Response Status: {response.status_code}")

    if response.status_code == 200:
        events_data = response.json()

        if 'commCellInfo' in events_data or 'events' in events_data:
            events = events_data.get('events', [])
            print(f"Total Events Retrieved: {len(events)}")
            print()

            # Filter for storage/pruning related events
            storage_events = []
            for event in events:
                description = event.get('description', '').lower()
                event_code = str(event.get('eventCode', ''))

                # Look for pruning, storage pool, or space-related events
                if any(keyword in description for keyword in ['prune', 'storage', 'space', 'full', 'capacity', 'delete']):
                    storage_events.append(event)

            print(f"Storage/Pruning-Related Events: {len(storage_events)}")
            print()

            if storage_events:
                print("RECENT STORAGE/PRUNING EVENTS:")
                print("-" * 100)

                for event in storage_events[:20]:  # Show last 20
                    event_id = event.get('eventId', 'N/A')
                    event_time = event.get('timeSource', 0)
                    severity = event.get('severity', 'Unknown')
                    description = event.get('description', 'No description')

                    if event_time:
                        event_dt = datetime.fromtimestamp(event_time)
                        print(f"Event ID: {event_id} | Severity: {severity}")
                        print(f"  Time: {event_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"  Description: {description[:200]}")
                        print()
            else:
                print("ℹ️  No critical storage events found")
                print()
        else:
            print("⚠️  Unexpected response format")
            print(f"Response keys: {list(events_data.keys())}")
            print()
    else:
        print(f"❌ API request failed: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        print()

except requests.exceptions.RequestException as e:
    print(f"❌ Error connecting to API: {e}")
    print()
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    print()

print("=" * 100)
print("CHECKING DATA AGING STATUS")
print("=" * 100)
print()

# Check retention rules for aging configuration
cur.execute("""
    SELECT parentName, parentId, enableDataAging, COUNT(*) as rule_count
    FROM retention_rules
    GROUP BY parentName, enableDataAging
    ORDER BY parentName
""")

aging_status = cur.fetchall()

print(f"Data Aging Status by Plan:")
print("-" * 100)

aging_disabled_plans = []
for status in aging_status:
    plan_name = status['parentName']
    aging_enabled = status['enableDataAging']
    rule_count = status['rule_count']

    status_text = "✓ ENABLED" if aging_enabled == 1 else "✗ DISABLED"

    print(f"{plan_name}: {status_text} ({rule_count} rules)")

    if aging_enabled == 0:
        aging_disabled_plans.append(plan_name)

print()

if aging_disabled_plans:
    print(f"⚠️  WARNING: {len(aging_disabled_plans)} plans have data aging DISABLED!")
    print("   These plans will NEVER reclaim space automatically!")
    print()
    print("   Plans with aging disabled:")
    for plan in aging_disabled_plans[:10]:
        print(f"   - {plan}")
    if len(aging_disabled_plans) > 10:
        print(f"   ... and {len(aging_disabled_plans) - 10} more")
    print()

print("=" * 100)
print("RETENTION RULE INEFFICIENCIES")
print("=" * 100)
print()

# Check for inefficient retention rules
cur.execute("""
    SELECT COUNT(*) as count
    FROM retention_rules
    WHERE retainBackupDataForDays <= 30 AND retainBackupDataForCycles >= 2
""")

inefficient_count = cur.fetchone()['count']

if inefficient_count > 0:
    print(f"⚠️  WARNING: {inefficient_count} retention rules are inefficient!")
    print(f"   Short retention (≤30 days) with 2+ cycles delays aging by 7-14 days")
    print()

    cur.execute("""
        SELECT parentName, entityName, retainBackupDataForDays, retainBackupDataForCycles
        FROM retention_rules
        WHERE retainBackupDataForDays <= 30 AND retainBackupDataForCycles >= 2
        ORDER BY parentName
        LIMIT 10
    """)

    sample_rules = cur.fetchall()

    print("   Sample inefficient rules:")
    for rule in sample_rules:
        print(f"   - {rule['parentName']} / {rule['entityName']}")
        print(f"     Retention: {rule['retainBackupDataForDays']} days + {rule['retainBackupDataForCycles']} cycles")
        print(f"     Recommendation: Change to 1 cycle")
        print()

print("=" * 100)
print("SUMMARY & RECOMMENDATIONS")
print("=" * 100)
print()

print("API-Based Analysis Completed:")
print()
print("✓ Checked pruning job history via /Job endpoint")
print("✓ Checked events/alerts via /Events endpoint")
print("✓ Verified data aging configuration in database")
print("✓ Identified retention rule inefficiencies")
print()
print("LIMITATIONS:")
print("  - API does not provide raw log file access (SIDBPrune.log, etc.)")
print("  - Detailed pruning operations require log file review")
print("  - For deep diagnostics, use collect_pruning_logs.ps1 on MediaAgents")
print()
print("NEXT STEPS:")
print()
print("1. IMMEDIATE:")
print("   [ ] Review pruning job failures (if any found above)")
print("   [ ] Enable data aging for disabled plans")
print("   [ ] Manually trigger pruning for critical pools")
print()
print("2. SHORT-TERM:")
print(f"   [ ] Optimize {inefficient_count} inefficient retention rules")
print("   [ ] Run collect_pruning_logs.ps1 on MediaAgents for detailed diagnostics")
print("   [ ] Monitor space reclamation on critical pools")
print()
print("3. LONG-TERM:")
print("   [ ] Set up automated alerts for pools <20% free")
print("   [ ] Schedule regular pruning verification")
print("   [ ] Plan capacity expansion for critical pools")
print()

conn.close()

print("=" * 100)
print("END OF API-BASED ANALYSIS")
print("=" * 100)
