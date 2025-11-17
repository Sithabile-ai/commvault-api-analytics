"""
Simple test script to verify Commvault API connection
Run this before starting the Flask app to test your credentials
"""

import requests
import base64
import configparser
import sys

def test_connection():
    """Test connection to Commvault API"""
    print("=" * 60)
    print("Commvault API Connection Test")
    print("=" * 60)

    # Load configuration
    config = configparser.ConfigParser()
    config.read('config.ini')

    base_url = config.get('commvault', 'base_url')
    username = config.get('commvault', 'username')
    password = config.get('commvault', 'password')

    print(f"\n1. Configuration loaded:")
    print(f"   Base URL: {base_url}")
    print(f"   Username: {username}")
    print(f"   Password: {'*' * len(password)}")

    # Test 1: Check if password is Base64
    print(f"\n2. Checking password encoding...")
    try:
        decoded = base64.b64decode(password).decode('utf-8')
        print(f"   ✓ Password appears to be Base64-encoded")
        print(f"   Decoded: {'*' * len(decoded)}")
    except:
        print(f"   ℹ Password appears to be plaintext (will be encoded)")
        password = base64.b64encode(password.encode('utf-8')).decode('utf-8')

    # Test 2: Attempt login
    print(f"\n3. Attempting authentication...")
    login_payload = {
        "username": username,
        "password": password
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            f"{base_url}/Login",
            json=login_payload,
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            print(f"   ✓ Authentication successful!")
            token_data = response.json()
            token = token_data.get('token', '')

            if token.startswith("QSDK "):
                token = token[5:]

            print(f"   Token received (first 20 chars): {token[:20]}...")

            # Test 3: Try to fetch clients
            print(f"\n4. Testing API access (fetching clients)...")
            auth_headers = {
                "Accept": "application/json",
                "Authtoken": token
            }

            clients_response = requests.get(
                f"{base_url}/Client",
                headers=auth_headers,
                timeout=30
            )

            if clients_response.status_code == 200:
                clients_data = clients_response.json()
                client_count = len(clients_data.get('clientProperties', []))
                print(f"   ✓ API access successful!")
                print(f"   Found {client_count} clients in the CommCell")

                if client_count > 0:
                    print(f"\n   Sample clients:")
                    for i, client_entry in enumerate(clients_data.get('clientProperties', [])[:3]):
                        client = client_entry.get('client', {})
                        print(f"   - {client.get('clientName', 'N/A')}")

                print(f"\n{'=' * 60}")
                print("✓ CONNECTION TEST PASSED")
                print("Your configuration is correct and ready to use!")
                print("Run 'python app.py' to start the Flask application")
                print(f"{'=' * 60}")
                return True
            else:
                print(f"   ✗ Failed to fetch clients")
                print(f"   Status: {clients_response.status_code}")
                print(f"   Response: {clients_response.text[:200]}")
                return False
        else:
            print(f"   ✗ Authentication failed")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            print(f"\n   Possible issues:")
            print(f"   - Check username and password are correct")
            print(f"   - Verify the base URL is accessible")
            print(f"   - Ensure your account has API access")
            return False

    except requests.exceptions.ConnectionError:
        print(f"   ✗ Connection failed")
        print(f"   Cannot reach {base_url}")
        print(f"\n   Possible issues:")
        print(f"   - Check the server address and port")
        print(f"   - Verify network connectivity")
        print(f"   - Ensure the Commvault server is running")
        return False
    except requests.exceptions.Timeout:
        print(f"   ✗ Connection timeout")
        print(f"   The server is not responding")
        return False
    except Exception as e:
        print(f"   ✗ Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        success = test_connection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {str(e)}")
        sys.exit(1)
