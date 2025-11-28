"""
Quick API Test Script
Tests Commvault API authentication with credentials from config.ini
"""
import sys
import configparser
import requests
import base64
import urllib3
from datetime import datetime

# Disable SSL warnings
urllib3.disable_warnings()

def test_api():
    """Quick API test with timing"""
    print("=" * 80)
    print("COMMVAULT API QUICK TEST")
    print("=" * 80)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Load config
    try:
        config = configparser.ConfigParser()
        config.read('config.ini')

        base_url = config.get('commvault', 'webservice_url')
        username = config.get('commvault', 'username')
        password = config.get('commvault', 'password')

        print(f"URL: {base_url}")
        print(f"User: {username}")
        print(f"Password: {password[:3]}***")
        print()
    except Exception as e:
        print(f"ERROR: Failed to load config.ini: {e}")
        return False

    # Encode password
    try:
        encoded_password = base64.b64encode(password.encode('utf-8')).decode('utf-8')
    except Exception as e:
        print(f"ERROR: Failed to encode password: {e}")
        return False

    # Test authentication
    print("Testing authentication...")
    print("-" * 80)

    try:
        login_payload = {
            "username": username,
            "password": encoded_password
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        start_time = datetime.now()

        response = requests.post(
            f"{base_url}/Login",
            json=login_payload,
            headers=headers,
            timeout=30,
            verify=False
        )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print(f"Response Time: {duration:.2f} seconds")
        print(f"Status Code: {response.status_code}")
        print()

        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get('token', '')

            if token.startswith("QSDK "):
                token = token[5:]

            print("SUCCESS! Authentication successful")
            print(f"Token: {token[:30]}...")
            print()

            # Test storage policy API
            print("Testing StoragePolicy API...")
            print("-" * 80)

            api_headers = {
                'Authtoken': f'QSDK {token}',
                'Accept': 'application/json'
            }

            policy_response = requests.get(
                f'{base_url}/StoragePolicy',
                headers=api_headers,
                timeout=30,
                verify=False
            )

            print(f"Status Code: {policy_response.status_code}")

            if policy_response.status_code == 200:
                policies = policy_response.json()
                policy_count = len(policies.get('policies', []))
                print(f"SUCCESS! Found {policy_count} storage policies")

                if policy_count > 0:
                    print()
                    print("First 5 policies:")
                    for i, policy in enumerate(policies.get('policies', [])[:5]):
                        policy_name = policy.get('storagePolicy', {}).get('storagePolicyName', 'Unknown')
                        print(f"  {i+1}. {policy_name}")
            else:
                print(f"FAILED: {policy_response.text[:200]}")

            print()
            print("=" * 80)
            print("TEST PASSED - API is working!")
            print("=" * 80)
            return True

        else:
            print(f"FAILED: Authentication failed")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:300]}")
            print()
            print("=" * 80)
            print("TEST FAILED - Authentication rejected")
            print("=" * 80)
            return False

    except requests.exceptions.Timeout as e:
        print("TIMEOUT: Connection timed out after 30 seconds")
        print()
        # Extract server and port
        server_part = base_url.split('//')[1].split('/')[0] if '//' in base_url else base_url.split('/')[0]
        port = '80/443'
        if ':' in server_part:
            parts = server_part.split(':')
            if len(parts) > 1:
                port = parts[1]
                server_part = parts[0]

        print("Diagnostic Information:")
        print(f"  Server: {server_part}")
        print(f"  Port: {port}")
        print(f"  Endpoint: /Login")
        print(f"  Username: {username}")
        print()
        print("Possible Causes:")
        print("  1. Firewall blocking the port")
        print("  2. Web service not running")
        print("  3. Network routing issue")
        print("  4. Wrong port in configuration")
        print()
        print("Recommended Actions:")
        print("  - Run: Test-NetConnection -ComputerName <server> -Port <port>")
        print("  - Contact network administrator")
        print("  - Verify Commvault web service is running")
        print()
        print("=" * 80)
        print("TEST FAILED - Cannot reach server (port blocked or service down)")
        print("=" * 80)
        return False

    except requests.exceptions.ConnectionError as e:
        error_detail = str(e)
        print(f"CONNECTION ERROR: {error_detail[:200]}")
        print()
        print("Diagnostic Information:")
        print(f"  URL: {base_url}/Login")
        print(f"  Username: {username}")
        print()
        if "Name or service not known" in error_detail or "nodename nor servname" in error_detail:
            print("DNS Resolution Failed:")
            print("  The hostname cannot be resolved to an IP address")
            print("  Check hostname spelling in config.ini")
        elif "Connection refused" in error_detail:
            print("Connection Refused:")
            print("  Server is reachable but nothing is listening on the port")
            print("  Verify Commvault web service is running")
        else:
            print("Network Error:")
            print("  Cannot establish connection to server")
            print("  Check network connectivity and firewall rules")
        print()
        print("=" * 80)
        print("TEST FAILED - Cannot connect to server")
        print("=" * 80)
        return False

    except Exception as e:
        error_type = type(e).__name__
        error_detail = str(e)
        print(f"ERROR ({error_type}): {error_detail[:200]}")
        print()
        print("Diagnostic Information:")
        print(f"  URL: {base_url}/Login")
        print(f"  Username: {username}")
        print(f"  Error Type: {error_type}")
        print()
        print("=" * 80)
        print("TEST FAILED - Unexpected error")
        print("=" * 80)
        return False


if __name__ == '__main__':
    success = test_api()
    sys.exit(0 if success else 1)
