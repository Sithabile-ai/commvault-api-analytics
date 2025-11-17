"""
Check Events and Alerts for Critical Storage Pools
Analyzes events and alerts related to the 3 critical pools
"""

import sqlite3
from datetime import datetime

# Connect to database
conn = sqlite3.connect('Database/commvault.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 100)
print("EVENTS & ALERTS ANALYSIS - CRITICAL STORAGE POOLS")
print("=" * 100)
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Critical pools to check
critical_pools = ["Apex GDP", "Southern_Sun_Durban", "Simera_GDP"]
critical_pool_ids = [298, 451, 355]

print("Critical Pools Being Analyzed:")
for idx, pool in enumerate(critical_pools):
    print(f"  {idx+1}. {pool} (ID: {critical_pool_ids[idx]})")
print()

# Check database schema for events table
print("=" * 100)
print("EXAMINING EVENTS TABLE")
print("=" * 100)
print()

cur.execute("PRAGMA table_info(events)")
events_schema = cur.fetchall()

if events_schema:
    print("Events Table Schema:")
    for col in events_schema:
        print(f"  - {col['name']} ({col['type']})")
    print()

    # Get total events count
    cur.execute("SELECT COUNT(*) as count FROM events")
    total_events = cur.fetchone()['count']
    print(f"Total Events in Database: {total_events}")
    print()

    if total_events > 0:
        # Get sample of events
        cur.execute("SELECT * FROM events LIMIT 5")
        sample_events = cur.fetchall()

        print("Sample Events (first 5):")
        print("-" * 100)
        for event in sample_events:
            print(f"Event ID: {event['eventId'] if 'eventId' in event.keys() else 'N/A'}")
            for key in event.keys():
                print(f"  {key}: {event[key]}")
            print()

        # Search for storage-related events
        print("=" * 100)
        print("STORAGE-RELATED EVENTS")
        print("=" * 100)
        print()

        # Try to find events containing pool names or storage keywords
        storage_keywords = [
            'storage', 'pool', 'space', 'full', 'capacity', 'prune', 'pruning',
            'delete', 'aged', 'aging', 'disk', 'mount', 'path'
        ]

        # Check if description column exists
        columns = [col['name'] for col in events_schema]

        if 'description' in columns or 'eventDescription' in columns or 'message' in columns:
            desc_col = 'description' if 'description' in columns else ('eventDescription' if 'eventDescription' in columns else 'message')

            for keyword in storage_keywords:
                cur.execute(f"SELECT * FROM events WHERE LOWER({desc_col}) LIKE ? LIMIT 20", (f'%{keyword}%',))
                keyword_events = cur.fetchall()

                if keyword_events:
                    print(f"Events containing '{keyword}': {len(keyword_events)}")

                    # Show most recent 5
                    for event in keyword_events[:5]:
                        print(f"  - {event[desc_col][:150] if event[desc_col] else 'No description'}")
                    print()

        # Search for specific pool names
        print("=" * 100)
        print("EVENTS FOR CRITICAL POOLS")
        print("=" * 100)
        print()

        for pool_name in critical_pools:
            print(f"Searching for events mentioning: {pool_name}")
            print("-" * 100)

            if 'description' in columns or 'eventDescription' in columns or 'message' in columns:
                desc_col = 'description' if 'description' in columns else ('eventDescription' if 'eventDescription' in columns else 'message')

                cur.execute(f"SELECT * FROM events WHERE LOWER({desc_col}) LIKE ? ORDER BY eventId DESC LIMIT 10",
                           (f'%{pool_name.lower()}%',))
                pool_events = cur.fetchall()

                if pool_events:
                    print(f"  Found {len(pool_events)} events")
                    for event in pool_events:
                        print(f"    Event ID: {event['eventId'] if 'eventId' in event.keys() else 'N/A'}")
                        if 'severity' in event.keys():
                            print(f"    Severity: {event['severity']}")
                        if 'eventTime' in event.keys():
                            print(f"    Time: {event['eventTime']}")
                        print(f"    Description: {event[desc_col][:200] if event[desc_col] else 'No description'}")
                        print()
                else:
                    print(f"  No events found mentioning this pool name")
                print()
    else:
        print("No events data in database - events table is empty")
        print()
else:
    print("Events table exists but has no schema information")
    print()

# Check alerts table
print("=" * 100)
print("EXAMINING ALERTS TABLE")
print("=" * 100)
print()

cur.execute("PRAGMA table_info(alerts)")
alerts_schema = cur.fetchall()

if alerts_schema:
    print("Alerts Table Schema:")
    for col in alerts_schema:
        print(f"  - {col['name']} ({col['type']})")
    print()

    # Get total alerts count
    cur.execute("SELECT COUNT(*) as count FROM alerts")
    total_alerts = cur.fetchone()['count']
    print(f"Total Alerts in Database: {total_alerts}")
    print()

    if total_alerts > 0:
        # Get sample of alerts
        cur.execute("SELECT * FROM alerts LIMIT 5")
        sample_alerts = cur.fetchall()

        print("Sample Alerts (first 5):")
        print("-" * 100)
        for alert in sample_alerts:
            print(f"Alert ID: {alert['alertId'] if 'alertId' in alert.keys() else 'N/A'}")
            for key in alert.keys():
                print(f"  {key}: {alert[key]}")
            print()

        # Get all columns
        columns = [col['name'] for col in alerts_schema]

        # Search for storage-related alerts
        print("=" * 100)
        print("STORAGE-RELATED ALERTS")
        print("=" * 100)
        print()

        storage_keywords = [
            'storage', 'pool', 'space', 'full', 'capacity', 'low', 'critical',
            'prune', 'pruning', 'delete', 'aged', 'aging', 'disk'
        ]

        if 'alertName' in columns or 'name' in columns or 'description' in columns:
            name_col = 'alertName' if 'alertName' in columns else ('name' if 'name' in columns else 'description')

            for keyword in storage_keywords:
                cur.execute(f"SELECT * FROM alerts WHERE LOWER({name_col}) LIKE ? LIMIT 20", (f'%{keyword}%',))
                keyword_alerts = cur.fetchall()

                if keyword_alerts:
                    print(f"Alerts containing '{keyword}': {len(keyword_alerts)}")

                    # Show most recent 5
                    for alert in keyword_alerts[:5]:
                        print(f"  - {alert[name_col][:150] if alert[name_col] else 'No name'}")
                    print()

        # Search for critical/high severity alerts
        if 'severity' in columns:
            print("=" * 100)
            print("HIGH SEVERITY ALERTS")
            print("=" * 100)
            print()

            cur.execute("SELECT * FROM alerts WHERE LOWER(severity) IN ('critical', 'high', 'error') LIMIT 20")
            critical_alerts = cur.fetchall()

            if critical_alerts:
                print(f"Found {len(critical_alerts)} critical/high severity alerts:")
                print("-" * 100)

                for alert in critical_alerts:
                    print(f"Alert ID: {alert['alertId'] if 'alertId' in alert.keys() else 'N/A'}")
                    print(f"  Severity: {alert['severity']}")
                    if 'alertName' in columns:
                        print(f"  Name: {alert['alertName']}")
                    if 'description' in columns:
                        print(f"  Description: {alert['description'][:200] if alert['description'] else 'N/A'}")
                    if 'criteria' in columns:
                        print(f"  Criteria: {alert['criteria'][:200] if alert['criteria'] else 'N/A'}")
                    print()
            else:
                print("No critical/high severity alerts found")
                print()

        # Get alert definitions/policies
        print("=" * 100)
        print("ALERT DEFINITIONS")
        print("=" * 100)
        print()

        cur.execute("SELECT * FROM alerts")
        all_alerts = cur.fetchall()

        if all_alerts:
            print(f"Total Alert Definitions: {len(all_alerts)}")
            print()

            # Group by type or category if available
            if 'alertCategory' in columns or 'category' in columns:
                cat_col = 'alertCategory' if 'alertCategory' in columns else 'category'

                cur.execute(f"SELECT {cat_col}, COUNT(*) as count FROM alerts GROUP BY {cat_col}")
                categories = cur.fetchall()

                print("Alerts by Category:")
                for cat in categories:
                    print(f"  - {cat[cat_col]}: {cat['count']} alerts")
                print()

            # Show all alerts
            print("All Alert Definitions:")
            print("-" * 100)

            for alert in all_alerts:
                if 'alertName' in columns:
                    print(f"\nAlert: {alert['alertName']}")
                elif 'name' in columns:
                    print(f"\nAlert: {alert['name']}")
                else:
                    print(f"\nAlert ID: {alert['alertId'] if 'alertId' in alert.keys() else 'N/A'}")

                # Print all columns
                for key in alert.keys():
                    if key not in ['alertName', 'name', 'alertId']:
                        value = alert[key]
                        if value and len(str(value)) > 200:
                            print(f"  {key}: {str(value)[:200]}...")
                        else:
                            print(f"  {key}: {value}")
        else:
            print("No alert definitions found")
            print()

    else:
        print("No alerts data in database - alerts table is empty")
        print()
else:
    print("Alerts table exists but has no schema information")
    print()

# Check for storage pool specific alerts
print("=" * 100)
print("STORAGE POOL CAPACITY ALERTS CHECK")
print("=" * 100)
print()

print("Checking if storage pools have capacity thresholds configured...")
print()

# Get storage pools with their current status
cur.execute("""
    SELECT storagePoolId, storagePoolName, totalCapacity, freeSpace
    FROM storage_pools
    WHERE storagePoolName IN (?, ?, ?)
""", critical_pools)

critical_pool_data = cur.fetchall()

for pool in critical_pool_data:
    pool_name = pool['storagePoolName']
    pool_id = pool['storagePoolId']

    try:
        total = int(pool['totalCapacity']) if pool['totalCapacity'] else 0
        free = int(pool['freeSpace']) if pool['freeSpace'] else 0

        if total > 0:
            pct_free = (free * 100.0) / total

            print(f"Pool: {pool_name} (ID: {pool_id})")
            print(f"  Current Free Space: {pct_free:.2f}%")

            # Check if there are alerts configured for this pool
            if total_alerts > 0:
                # Try to find alerts mentioning this pool ID or name
                cur.execute(f"SELECT * FROM alerts WHERE alertId = ? OR alertId LIKE ?",
                           (pool_id, f'%{pool_id}%'))
                pool_alerts = cur.fetchall()

                if pool_alerts:
                    print(f"  Configured Alerts: {len(pool_alerts)}")
                    for alert in pool_alerts:
                        if 'alertName' in alert.keys():
                            print(f"    - {alert['alertName']}")
                else:
                    print(f"  WARNING: No specific alerts configured for this pool")
            else:
                print(f"  WARNING: No alerts configured in environment")

            # Recommend alert thresholds
            print(f"  Recommended Alert Thresholds:")
            print(f"    - Warning: <30% free space")
            print(f"    - Critical: <20% free space")
            print(f"    - Emergency: <10% free space")
            print(f"  Current Status: {'EMERGENCY' if pct_free < 10 else 'CRITICAL' if pct_free < 20 else 'WARNING'}")
            print()

    except Exception as e:
        print(f"  Error analyzing pool: {e}")
        print()

# Summary and recommendations
print("=" * 100)
print("SUMMARY & RECOMMENDATIONS")
print("=" * 100)
print()

print("Database Contents:")
print(f"  - Events: {total_events if 'total_events' in locals() else 'Unknown'}")
print(f"  - Alerts: {total_alerts if 'total_alerts' in locals() else 'Unknown'}")
print()

print("RECOMMENDATIONS:")
print()

if total_events == 0 and total_alerts == 0:
    print("CRITICAL FINDING:")
    print("  - No events or alerts in database")
    print("  - This suggests:")
    print("    1. Data may not have been retrieved from Commvault API yet")
    print("    2. Need to fetch events/alerts using REST API")
    print("    3. Alert policies may not be configured in Commvault")
    print()

    print("IMMEDIATE ACTIONS:")
    print("  1. Fetch events from Commvault API:")
    print("     GET {base_url}/Events")
    print()
    print("  2. Fetch alerts from Commvault API:")
    print("     GET {base_url}/Alert")
    print()
    print("  3. Configure storage pool capacity alerts in CommCell Console:")
    print("     - Navigate to: Control Panel > Alert Definitions")
    print("     - Create new alert: 'Storage Pool Low Space'")
    print("     - Criteria: Free Space < 20%")
    print("     - Notification: Email to storage team")
    print()

elif total_alerts == 0:
    print("WARNING:")
    print("  - Events exist but no alert definitions found")
    print("  - Recommend configuring automated alerts for:")
    print("    * Storage pool capacity thresholds")
    print("    * Failed pruning jobs")
    print("    * Aging job failures")
    print("    * Mount path accessibility issues")
    print()

else:
    print("ACTION ITEMS:")
    print("  1. Review storage-related events above")
    print("  2. Verify alert notifications are configured")
    print("  3. Ensure critical pools have specific alerts")
    print("  4. Test alert delivery mechanisms")
    print()

print("NEXT STEPS:")
print("  1. If events/alerts tables are empty:")
print("     - Run API data retrieval to populate tables")
print("     - Check app.py for event/alert fetching endpoints")
print()
print("  2. Configure proactive monitoring:")
print("     - Set up alerts for pools <30% free")
print("     - Monitor pruning job failures")
print("     - Track aging job completion rates")
print()
print("  3. Create event correlation:")
print("     - Link storage pool events to specific pools")
print("     - Correlate pruning failures with space issues")
print("     - Track historical trends")
print()

print("=" * 100)
print("END OF EVENTS & ALERTS ANALYSIS")
print("=" * 100)

conn.close()
