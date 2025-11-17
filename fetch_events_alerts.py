"""
Fetch Events and Alerts from Commvault API
Retrieves event and alert data and saves to database
"""

import requests
import base64
import configparser
import sqlite3
from datetime import datetime

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
print("FETCHING EVENTS AND ALERTS FROM COMMVAULT API")
print("=" * 100)
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"CommVault Server: {BASE_URL}")
print()

# Connect to database
conn = sqlite3.connect('Database/commvault.db')
cur = conn.cursor()

# Function to save events to database
def save_events_to_db(events_json):
    """Save Events data to database"""
    count = 0

    # Try different response formats
    events_list = events_json.get("commCellEvents", [])
    if not events_list:
        events_list = events_json.get("events", [])

    if not events_list and isinstance(events_json, list):
        events_list = events_json

    for event_entry in events_list:
        try:
            cur.execute(
                """REPLACE INTO events
                   (eventId, eventCode, severity, eventType, message, timeSource,
                    subsystem, clientName, jobId, lastFetchTime)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event_entry.get("eventId"),
                    event_entry.get("eventCode"),
                    event_entry.get("severity"),
                    event_entry.get("eventType"),
                    event_entry.get("description") or event_entry.get("message"),
                    event_entry.get("timeSource"),
                    event_entry.get("subsystem"),
                    event_entry.get("clientName"),
                    event_entry.get("jobId"),
                    datetime.now().isoformat()
                )
            )
            count += 1
        except Exception as e:
            print(f"  Error saving event: {e}")

    conn.commit()
    return count

# Function to save alerts to database
def save_alerts_to_db(alerts_json):
    """Save Alerts data to database"""
    count = 0

    alerts_list = alerts_json.get("alertList", [])
    if not alerts_list:
        alerts_list = alerts_json.get("alerts", [])

    if not alerts_list and isinstance(alerts_json, list):
        alerts_list = alerts_json

    for alert_entry in alerts_list:
        try:
            cur.execute(
                """REPLACE INTO alerts
                   (alertId, alertName, alertType, severity, status,
                    alertMessage, triggerTime, lastFetchTime)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    alert_entry.get("alertId") or alert_entry.get("id"),
                    alert_entry.get("alertName") or alert_entry.get("name"),
                    alert_entry.get("alertType") or alert_entry.get("type"),
                    alert_entry.get("severity"),
                    alert_entry.get("status"),
                    alert_entry.get("alertMessage") or alert_entry.get("message"),
                    alert_entry.get("triggerTime"),
                    datetime.now().isoformat()
                )
            )
            count += 1
        except Exception as e:
            print(f"  Error saving alert: {e}")

    conn.commit()
    return count

# Fetch Events
print("=" * 100)
print("FETCHING EVENTS")
print("=" * 100)
print()

events_fetched = False
events_count = 0

# Try multiple endpoints
event_endpoints = [
    ("/Event", "All events"),
    ("/Event?level=Critical", "Critical events only"),
    ("/Event?level=Error", "Error events"),
    ("/Event?level=Warning", "Warning events"),
    ("/CommServ/Event", "CommServ events"),
    ("/Events", "Events endpoint")
]

for endpoint, description in event_endpoints:
    print(f"Trying: {BASE_URL}{endpoint}")
    print(f"  Description: {description}")

    try:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, verify=False, timeout=30)

        print(f"  Response Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            # Check if we got data
            if data:
                print(f"  Response received, attempting to parse...")

                # Try to determine the structure
                if isinstance(data, dict):
                    keys = list(data.keys())
                    print(f"  Response keys: {keys[:10]}")

                    # Look for event data
                    events_list = data.get("commCellEvents", [])
                    if not events_list:
                        events_list = data.get("events", [])
                    if not events_list:
                        events_list = data.get("eventList", [])

                    if events_list:
                        print(f"  Found {len(events_list)} events")
                        count = save_events_to_db(data)
                        events_count += count
                        print(f"  Saved {count} events to database")
                        events_fetched = True
                        print()
                        break
                    else:
                        print(f"  No event list found in response")
                elif isinstance(data, list):
                    print(f"  Found {len(data)} events (list format)")
                    count = save_events_to_db(data)
                    events_count += count
                    print(f"  Saved {count} events to database")
                    events_fetched = True
                    print()
                    break
            else:
                print(f"  Empty response")
        else:
            print(f"  Failed: HTTP {response.status_code}")
            print(f"  Response: {response.text[:200]}")

        print()

    except requests.exceptions.RequestException as e:
        print(f"  Connection error: {e}")
        print()
    except Exception as e:
        print(f"  Error: {e}")
        print()

if not events_fetched:
    print("WARNING: Could not fetch events from any endpoint")
    print("This could mean:")
    print("  1. API endpoint requires different authentication")
    print("  2. Events feature not available in this Commvault version")
    print("  3. Network/firewall blocking access")
    print()

# Fetch Alerts
print("=" * 100)
print("FETCHING ALERTS")
print("=" * 100)
print()

alerts_fetched = False
alerts_count = 0

# Try multiple endpoints
alert_endpoints = [
    ("/Alert", "All alerts"),
    ("/Alert/Definition", "Alert definitions"),
    ("/Alerts", "Alerts endpoint"),
    ("/AlertDefinition", "Alert definition endpoint")
]

for endpoint, description in alert_endpoints:
    print(f"Trying: {BASE_URL}{endpoint}")
    print(f"  Description: {description}")

    try:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, verify=False, timeout=30)

        print(f"  Response Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            if data:
                print(f"  Response received, attempting to parse...")

                if isinstance(data, dict):
                    keys = list(data.keys())
                    print(f"  Response keys: {keys[:10]}")

                    # Look for alert data
                    alerts_list = data.get("alertList", [])
                    if not alerts_list:
                        alerts_list = data.get("alerts", [])
                    if not alerts_list:
                        alerts_list = data.get("definitions", [])

                    if alerts_list:
                        print(f"  Found {len(alerts_list)} alerts")
                        count = save_alerts_to_db(data)
                        alerts_count += count
                        print(f"  Saved {count} alerts to database")
                        alerts_fetched = True
                        print()
                        break
                    else:
                        print(f"  No alert list found in response")
                elif isinstance(data, list):
                    print(f"  Found {len(data)} alerts (list format)")
                    count = save_alerts_to_db(data)
                    alerts_count += count
                    print(f"  Saved {count} alerts to database")
                    alerts_fetched = True
                    print()
                    break
            else:
                print(f"  Empty response")
        else:
            print(f"  Failed: HTTP {response.status_code}")
            print(f"  Response: {response.text[:200]}")

        print()

    except requests.exceptions.RequestException as e:
        print(f"  Connection error: {e}")
        print()
    except Exception as e:
        print(f"  Error: {e}")
        print()

if not alerts_fetched:
    print("WARNING: Could not fetch alerts from any endpoint")
    print("This could mean:")
    print("  1. No alert definitions configured in Commvault")
    print("  2. API endpoint requires different authentication")
    print("  3. Alerts feature not available in this version")
    print()

# Summary
print("=" * 100)
print("SUMMARY")
print("=" * 100)
print()

print(f"Events Fetched: {events_count}")
print(f"Alerts Fetched: {alerts_count}")
print()

if events_count > 0 or alerts_count > 0:
    print("SUCCESS: Data has been saved to database")
    print()
    print("Next steps:")
    print("  1. Run: python check_events_alerts.py")
    print("  2. Review events/alerts related to critical pools")
    print("  3. Check Storage Pool Health Dashboard")
    print()
else:
    print("NO DATA RETRIEVED")
    print()
    print("Possible reasons:")
    print("  1. API connectivity issues")
    print("  2. Authentication/authorization problems")
    print("  3. Events/Alerts not configured in Commvault")
    print("  4. Different API endpoint required for your version")
    print()
    print("Alternative approach:")
    print("  1. Configure alert definitions in CommCell Console:")
    print("     - Control Panel > Alert Definitions")
    print("     - Create 'Storage Pool Low Space' alert")
    print("     - Criteria: Free Space < 20%")
    print()
    print("  2. Review Event Viewer in CommCell Console:")
    print("     - Tools > Event Viewer")
    print("     - Filter for storage-related events")
    print("     - Check for pruning failures")
    print()

# Check current database status
cur.execute("SELECT COUNT(*) as count FROM events")
db_events = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) as count FROM alerts")
db_alerts = cur.fetchone()[0]

print("Current Database Status:")
print(f"  Total Events: {db_events}")
print(f"  Total Alerts: {db_alerts}")
print()

print("=" * 100)
print("END OF FETCH OPERATION")
print("=" * 100)

conn.close()
