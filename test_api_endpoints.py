"""
API Endpoint Testing Script
Tests all Commvault API endpoints to verify data availability
"""

import requests
import base64
import json
import configparser
from datetime import datetime

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

BASE_URL = config.get('commvault', 'base_url')
USERNAME = config.get('commvault', 'username')
PASSWORD = config.get('commvault', 'password')

def authenticate():
    """Authenticate and get token"""
    print("=" * 80)
    print("AUTHENTICATING WITH COMMVAULT API")
    print("=" * 80)
    print(f"Base URL: {BASE_URL}")
    print(f"Username: {USERNAME}")

    # Ensure password is Base64 encoded
    try:
        base64.b64decode(PASSWORD)
        encoded_password = PASSWORD
    except:
        encoded_password = base64.b64encode(PASSWORD.encode('utf-8')).decode('utf-8')

    login_payload = {
        "username": USERNAME,
        "password": encoded_password
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/Login",
            json=login_payload,
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get('token', '')

            # Strip QSDK prefix if present
            if token.startswith("QSDK "):
                token = token[5:]

            print(f"[OK] Authentication successful!")
            print(f"Token (first 30 chars): {token[:30]}...")
            print()
            return token
        else:
            print(f"[FAIL] Authentication failed!")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None

    except Exception as e:
        print(f"[ERROR] Error during authentication: {str(e)}")
        return None

def test_endpoint(endpoint_name, endpoint_path, headers, description=""):
    """Test a specific API endpoint"""
    print("-" * 80)
    print(f"Testing: {endpoint_name}")
    print(f"Endpoint: {endpoint_path}")
    if description:
        print(f"Description: {description}")
    print("-" * 80)

    try:
        response = requests.get(
            f"{BASE_URL}{endpoint_path}",
            headers=headers,
            timeout=30
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                print(f"[OK] SUCCESS - Data retrieved")

                # Print data structure info
                if isinstance(data, dict):
                    print(f"Response Type: Dictionary")
                    print(f"Keys: {list(data.keys())[:10]}")  # First 10 keys

                    # Try to count items in common list fields
                    for possible_list_key in ['clientProperties', 'jobs', 'plans', 'policies',
                                              'mediaAgentList', 'mediaAgents', 'storagePools',
                                              'libraryList', 'libraries', 'VSInstanceProperties',
                                              'instances', 'storageArrays', 'arrays', 'events',
                                              'commCellEvents', 'alerts', 'alertList']:
                        if possible_list_key in data:
                            items = data[possible_list_key]
                            if isinstance(items, list):
                                print(f"[OK] Found list: '{possible_list_key}' with {len(items)} items")
                                if len(items) > 0:
                                    print(f"  Sample item keys: {list(items[0].keys())[:10]}")

                elif isinstance(data, list):
                    print(f"Response Type: List")
                    print(f"Item Count: {len(data)}")
                    if len(data) > 0:
                        print(f"Sample item keys: {list(data[0].keys())[:10]}")

                # Save full response to file for inspection
                filename = f"test_output_{endpoint_name.replace(' ', '_').replace('/', '_')}.json"
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"Full response saved to: {filename}")

                print()
                return True, data

            except json.JSONDecodeError as e:
                print(f"[FAIL] FAILED - Invalid JSON response")
                print(f"Error: {str(e)}")
                print(f"Response text (first 500 chars): {response.text[:500]}")
                print()
                return False, None
        else:
            print(f"[FAIL] FAILED - HTTP {response.status_code}")
            print(f"Response: {response.text[:500]}")
            print()
            return False, None

    except requests.exceptions.Timeout:
        print(f"[FAIL] FAILED - Request timed out")
        print()
        return False, None
    except Exception as e:
        print(f"[FAIL] FAILED - Error: {str(e)}")
        print()
        return False, None

def main():
    """Main test function"""
    print("\n" + "=" * 80)
    print("COMMVAULT API ENDPOINT TESTING")
    print("=" * 80)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Authenticate
    token = authenticate()
    if not token:
        print("Cannot proceed without authentication. Exiting.")
        return

    headers = {
        "Accept": "application/json",
        "Authtoken": token
    }

    results = {}

    # Test all endpoints
    print("\n" + "=" * 80)
    print("TESTING BASIC DATA ENDPOINTS")
    print("=" * 80)
    print()

    results['clients'] = test_endpoint("Clients", "/Client", headers, "All client machines")
    results['jobs'] = test_endpoint("Jobs", "/Job", headers, "Backup/restore jobs")
    results['plans'] = test_endpoint("Plans", "/Plan", headers, "Backup plans/policies")
    results['storage_policies'] = test_endpoint("Storage Policies", "/V2/StoragePolicy", headers, "Storage policies")

    print("\n" + "=" * 80)
    print("TESTING INFRASTRUCTURE ENDPOINTS")
    print("=" * 80)
    print()

    results['mediaagents'] = test_endpoint("MediaAgents", "/MediaAgent", headers, "Backup infrastructure servers")
    results['libraries'] = test_endpoint("Libraries", "/Library", headers, "Tape/disk libraries")
    results['storage_pools'] = test_endpoint("Storage Pools", "/V4/StoragePool", headers, "Storage pools (V4 API)")

    # Try alternative storage pool endpoint
    if not results['storage_pools'][0]:
        print("Trying alternative storage pool endpoint...")
        results['storage_pools_alt'] = test_endpoint("Storage Pools (Alt)", "/StoragePool", headers, "Storage pools (older API)")

    results['hypervisors'] = test_endpoint("Hypervisors/Instances", "/Instance", headers, "VM infrastructure")
    results['storage_arrays'] = test_endpoint("Storage Arrays", "/V4/Storage/Array", headers, "Physical storage arrays")

    print("\n" + "=" * 80)
    print("TESTING MONITORING ENDPOINTS")
    print("=" * 80)
    print()

    results['events'] = test_endpoint("Events (All)", "/Event", headers, "All system events")
    results['events_critical'] = test_endpoint("Events (Critical)", "/Event?level=Critical", headers, "Critical events only")
    results['alerts'] = test_endpoint("Alerts", "/Alert", headers, "Active alerts")
    results['commcell'] = test_endpoint("CommCell Info", "/Commcell", headers, "CommCell/CommServe information")

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()

    successful = sum(1 for success, _ in results.values() if success)
    total = len(results)

    print(f"Successful endpoints: {successful}/{total}")
    print()

    print("[OK] WORKING ENDPOINTS:")
    for name, (success, data) in results.items():
        if success:
            print(f"  - {name}")

    print()
    print("[FAIL] FAILED ENDPOINTS:")
    for name, (success, data) in results.items():
        if not success:
            print(f"  - {name}")

    print()
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()

    # Provide recommendations based on results
    if not results.get('storage_pools', (False, None))[0]:
        print("[WARN] Storage Pools (V4) failed - Your Commvault version may not support V4 API")
        print("  Recommendation: Try /StoragePool or /V2/StoragePool endpoints")

    if not results.get('storage_arrays', (False, None))[0]:
        print("[WARN] Storage Arrays failed - This may require specific configuration")
        print("  Recommendation: Check if storage arrays are configured in your CommCell")

    if not results.get('hypervisors', (False, None))[0]:
        print("[WARN] Hypervisors/Instances failed - May need different endpoint")
        print("  Recommendation: Try /V2/Virtualization/hypervisors or check VM configuration")

    if not results.get('events', (False, None))[0]:
        print("[WARN] Events failed - Event logging may not be available via REST API")
        print("  Recommendation: Check Commvault version and API permissions")

    print()
    print("All test output files saved with prefix 'test_output_'")
    print(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

if __name__ == "__main__":
    main()
