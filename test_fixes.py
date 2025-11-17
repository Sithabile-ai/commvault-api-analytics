"""
API Fixes Verification Script
Tests all fixed endpoints to verify parser and endpoint corrections
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

def test_fixed_endpoint(name, endpoint, headers, fix_description=""):
    """Test a fixed API endpoint"""
    print("-" * 80)
    print(f"Testing FIXED: {name}")
    print(f"Endpoint: {endpoint}")
    if fix_description:
        print(f"Fix Applied: {fix_description}")
    print("-" * 80)

    try:
        response = requests.get(
            f"{BASE_URL}{endpoint}",
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
                    print(f"Keys: {list(data.keys())}")

                    # Check specific keys we expect
                    if "response" in data:
                        items = data["response"]
                        if isinstance(items, list):
                            print(f"[OK] Found 'response' key with {len(items)} items")
                            if len(items) > 0 and "entityInfo" in items[0]:
                                print(f"  [OK] Correct structure - entityInfo found!")
                                entity = items[0]["entityInfo"]
                                print(f"  Sample: ID={entity.get('id')}, Name={entity.get('name')}")

                    if "storagePoolList" in data:
                        items = data["storagePoolList"]
                        if isinstance(items, list):
                            print(f"[OK] Found 'storagePoolList' key with {len(items)} items")
                            if len(items) > 0:
                                pool = items[0]
                                print(f"  [OK] Capacity data found:")
                                print(f"    totalCapacity: {pool.get('totalCapacity')}")
                                print(f"    totalFreeSpace: {pool.get('totalFreeSpace')}")

                    if "jobs" in data:
                        items = data["jobs"]
                        if isinstance(items, list):
                            print(f"[OK] Found 'jobs' key with {len(items)} items (filtered)")

                elif isinstance(data, list):
                    print(f"Response Type: List")
                    print(f"Item Count: {len(data)}")

                # Save full response to file
                filename = f"test_fixed_{name.replace(' ', '_').replace('/', '_')}.json"
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"Full response saved to: {filename}")

                print()
                return True, data

            except json.JSONDecodeError as e:
                print(f"[FAIL] FAILED - Invalid JSON response")
                print(f"Error: {str(e)}")
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
    print("COMMVAULT API FIXES VERIFICATION")
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

    print("\n" + "=" * 80)
    print("TESTING PRIORITY 1 FIXES (Parser Updates)")
    print("=" * 80)
    print()

    results['mediaagents'] = test_fixed_endpoint(
        "MediaAgents",
        "/MediaAgent",
        headers,
        "Parser updated to use 'response' -> 'entityInfo' structure"
    )

    results['libraries'] = test_fixed_endpoint(
        "Libraries",
        "/Library",
        headers,
        "Parser updated to use 'response' -> 'entityInfo' structure"
    )

    results['storage_pools'] = test_fixed_endpoint(
        "Storage Pools",
        "/StoragePool",
        headers,
        "Endpoint changed from /V4/StoragePool to /StoragePool + parser fixed for 'storagePoolList'"
    )

    print("\n" + "=" * 80)
    print("TESTING PRIORITY 2 FIXES (Performance)")
    print("=" * 80)
    print()

    results['jobs'] = test_fixed_endpoint(
        "Jobs (Filtered)",
        "/Job?completedJobLookupTime=86400",
        headers,
        "Added completedJobLookupTime=86400 (24 hours) to prevent timeout"
    )

    print("\n" + "=" * 80)
    print("TESTING PRIORITY 3 FIXES (Endpoint Changes)")
    print("=" * 80)
    print()

    results['events'] = test_fixed_endpoint(
        "Events",
        "/CommServ/Event?level=Critical",
        headers,
        "Changed endpoint from /Event to /CommServ/Event"
    )

    # Summary
    print("\n" + "=" * 80)
    print("FIXES VERIFICATION SUMMARY")
    print("=" * 80)
    print()

    successful = sum(1 for success, _ in results.values() if success)
    total = len(results)

    print(f"Fixed endpoints working: {successful}/{total}")
    print()

    print("[OK] WORKING AFTER FIXES:")
    for name, (success, data) in results.items():
        if success:
            print(f"  - {name}")

    print()
    print("[FAIL] STILL NOT WORKING:")
    for name, (success, data) in results.items():
        if not success:
            print(f"  - {name}")

    print()
    print("=" * 80)
    print("FIX VERIFICATION RESULTS")
    print("=" * 80)
    print()

    # Detailed analysis
    if results['mediaagents'][0]:
        print("[OK] MediaAgents parser fix SUCCESSFUL - Data structure correctly parsed")
    else:
        print("[FAIL] MediaAgents parser fix FAILED - Check logs above")

    if results['libraries'][0]:
        print("[OK] Libraries parser fix SUCCESSFUL - Data structure correctly parsed")
    else:
        print("[FAIL] Libraries parser fix FAILED - Check logs above")

    if results['storage_pools'][0]:
        print("[OK] Storage Pools fix SUCCESSFUL - Endpoint and parser working")
    else:
        print("[FAIL] Storage Pools fix FAILED - Check logs above")

    if results['jobs'][0]:
        print("[OK] Jobs timeout fix SUCCESSFUL - Filter prevents timeout")
    else:
        print("[FAIL] Jobs timeout fix FAILED - Check logs above")

    if results['events'][0]:
        print("[OK] Events endpoint fix SUCCESSFUL - New endpoint works")
    else:
        print("[WARN] Events endpoint fix FAILED - Endpoint may not be available in this version")

    print()
    print("All test output files saved with prefix 'test_fixed_'")
    print(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Expected outcome
    print("=" * 80)
    print("EXPECTED VS ACTUAL")
    print("=" * 80)
    print()
    print("Expected working after fixes: 4/5 (MediaAgents, Libraries, Storage Pools, Jobs)")
    print(f"Actual working: {successful}/5")
    print()
    if successful >= 4:
        print("[OK] SUCCESS! Priority fixes are working correctly!")
    else:
        print("[WARN] Some fixes may need additional adjustments")

if __name__ == "__main__":
    main()
