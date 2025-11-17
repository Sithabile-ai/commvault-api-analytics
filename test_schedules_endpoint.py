"""
Test script to check Commvault Schedules API endpoints
"""
import requests
import json
import sys
import getpass

# Try to read config.ini first
import configparser
config = configparser.ConfigParser()

base_url = ""
username = ""
password = ""

if config.read('config.ini'):
    base_url = config.get('commvault', 'base_url', fallback='')
    username = config.get('commvault', 'username', fallback='')
    password = config.get('commvault', 'password', fallback='')

# If not in config, prompt user
if not base_url:
    print("Enter Commvault connection details:")
    base_url = input("Base URL: ").rstrip("/")
    username = input("Username: ")
    password = getpass.getpass("Password: ")

if not all([base_url, username, password]):
    print("ERROR: Missing required information.")
    sys.exit(1)

print("=" * 80)
print("TESTING COMMVAULT SCHEDULES API ENDPOINTS")
print("=" * 80)
print()
print(f"Base URL: {base_url}")
print(f"Username: {username}")
print()

# Login
print("Step 1: Authenticating...")
try:
    login_url = f"{base_url}/Login"
    login_response = requests.post(
        login_url,
        headers={"Content-Type": "application/json"},
        json={"username": username, "password": password},
        timeout=30
    )

    if login_response.status_code != 200:
        print(f"❌ Login failed: HTTP {login_response.status_code}")
        print(f"Response: {login_response.text}")
        sys.exit(1)

    token = login_response.json().get('token')
    if not token:
        print("❌ No token received from login")
        sys.exit(1)

    print(f"✅ Login successful! Token received.")

except Exception as e:
    print(f"❌ Login error: {e}")
    sys.exit(1)

# Setup headers
headers = {
    "Authtoken": token,
    "Content-Type": "application/json"
}

print()
print("=" * 80)
print("TESTING SCHEDULE ENDPOINTS")
print("=" * 80)
print()

# Test 1: GET /Schedules (all schedules)
print("Test 1: GET /Schedules (all schedules)")
print("-" * 80)
try:
    url = f"{base_url}/Schedules"
    print(f"URL: {url}")
    response = requests.get(url, headers=headers, timeout=30)
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ SUCCESS - Schedules endpoint available!")

        # Save response
        with open('test_output_Schedules_All.json', 'w') as f:
            json.dump(data, f, indent=2)
        print(f"📄 Response saved to: test_output_Schedules_All.json")

        # Analyze response
        if 'taskDetail' in data:
            task_count = len(data.get('taskDetail', []))
            print(f"📊 Found {task_count} scheduled tasks")
        elif isinstance(data, list):
            print(f"📊 Found {len(data)} items")
        else:
            print(f"📊 Response keys: {list(data.keys())}")

    elif response.status_code == 404:
        print("❌ FAILED - Endpoint not found (404)")
        print("   This endpoint may not be available in your Commvault version")
    else:
        print(f"❌ FAILED - HTTP {response.status_code}")
        print(f"Response: {response.text[:500]}")

except Exception as e:
    print(f"❌ ERROR: {e}")

print()

# Test 2: GET /Schedules with admin flag
print("Test 2: GET /Schedules?admin=1 (include system schedules)")
print("-" * 80)
try:
    url = f"{base_url}/Schedules?admin=1"
    print(f"URL: {url}")
    response = requests.get(url, headers=headers, timeout=30)
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ SUCCESS - Admin schedules endpoint available!")

        # Save response
        with open('test_output_Schedules_Admin.json', 'w') as f:
            json.dump(data, f, indent=2)
        print(f"📄 Response saved to: test_output_Schedules_Admin.json")

        # Analyze response
        if 'taskDetail' in data:
            task_count = len(data.get('taskDetail', []))
            print(f"📊 Found {task_count} scheduled tasks (including admin/system)")
        elif isinstance(data, list):
            print(f"📊 Found {len(data)} items")

    elif response.status_code == 404:
        print("❌ FAILED - Endpoint not found (404)")
    else:
        print(f"❌ FAILED - HTTP {response.status_code}")

except Exception as e:
    print(f"❌ ERROR: {e}")

print()

# Test 3: GET /SchedulePolicy
print("Test 3: GET /SchedulePolicy")
print("-" * 80)
try:
    url = f"{base_url}/SchedulePolicy"
    print(f"URL: {url}")
    response = requests.get(url, headers=headers, timeout=30)
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ SUCCESS - SchedulePolicy endpoint available!")

        # Save response
        with open('test_output_SchedulePolicy.json', 'w') as f:
            json.dump(data, f, indent=2)
        print(f"📄 Response saved to: test_output_SchedulePolicy.json")

        # Analyze response
        if isinstance(data, dict):
            print(f"📊 Response keys: {list(data.keys())}")
        elif isinstance(data, list):
            print(f"📊 Found {len(data)} schedule policies")

    elif response.status_code == 404:
        print("❌ FAILED - Endpoint not found (404)")
        print("   This endpoint may not be available in your Commvault version")
    else:
        print(f"❌ FAILED - HTTP {response.status_code}")
        print(f"Response: {response.text[:500]}")

except Exception as e:
    print(f"❌ ERROR: {e}")

print()

# Test 4: GET /Task (alternative endpoint)
print("Test 4: GET /Task (alternative endpoint)")
print("-" * 80)
try:
    url = f"{base_url}/Task"
    print(f"URL: {url}")
    response = requests.get(url, headers=headers, timeout=30)
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ SUCCESS - Task endpoint available!")

        # Save response
        with open('test_output_Task.json', 'w') as f:
            json.dump(data, f, indent=2)
        print(f"📄 Response saved to: test_output_Task.json")

        # Analyze response
        if isinstance(data, dict):
            print(f"📊 Response keys: {list(data.keys())}")
        elif isinstance(data, list):
            print(f"📊 Found {len(data)} tasks")

    elif response.status_code == 404:
        print("❌ FAILED - Endpoint not found (404)")
    else:
        print(f"❌ FAILED - HTTP {response.status_code}")

except Exception as e:
    print(f"❌ ERROR: {e}")

print()
print("=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print()
print("Tested endpoints:")
print("  1. GET /Schedules")
print("  2. GET /Schedules?admin=1")
print("  3. GET /SchedulePolicy")
print("  4. GET /Task")
print()
print("Check the test_output_*.json files for detailed responses.")
print()
print("=" * 80)
