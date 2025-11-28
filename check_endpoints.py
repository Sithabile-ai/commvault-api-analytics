"""
REST API Endpoint Discovery Script
Tests common Commvault REST API endpoints to discover available resources
"""
import requests
import configparser
import base64
import urllib3
import json

# Disable SSL warnings
urllib3.disable_warnings()

def check_endpoints():
    """Check available REST API endpoints"""

    # Load config
    config = configparser.ConfigParser()
    config.read('config.ini')
    base_url = config.get('commvault', 'webservice_url')
    username = config.get('commvault', 'username')
    password = config.get('commvault', 'password')

    # Encode password
    try:
        decoded = base64.b64decode(password).decode('utf-8')
        encoded_password = password
    except:
        encoded_password = base64.b64encode(password.encode('utf-8')).decode('utf-8')

    # Authenticate
    print('=' * 80)
    print('COMMVAULT REST API ENDPOINT DISCOVERY')
    print('=' * 80)
    print(f'Authenticating to: {base_url}')
    print(f'Username: {username}')
    print()

    response = requests.post(
        f'{base_url}/Login',
        json={'username': username, 'password': encoded_password},
        headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
        timeout=30,
        verify=False
    )

    if response.status_code != 200:
        print(f'Authentication failed: {response.status_code}')
        print(response.text[:500])
        return

    token = response.json().get('token', '')
    if token.startswith('QSDK '):
        token = token[5:]
    print(f'Authentication successful!')
    print(f'Token: {token[:30]}...')
    print()

    headers = {
        'Authtoken': token,
        'Accept': 'application/json'
    }

    # Test common endpoints
    endpoints = [
        '/Job',
        '/Client',
        '/StoragePolicy',
        '/MediaAgent',
        '/StoragePool',
        '/Subclient',
        '/Agent',
        '/JobSummary',
        '/Schedule',
        '/BackupSet',
        '/Instance',
        '/CommCell',
        '/Library',
        '/DDB',
        '/AuxCopy',
        '/DataAging',
        '/Pruning',
        '/AlertRule',
        '/V2/MediaAgents',
        '/V2/StoragePools',
        '/V2/StoragePolicies'
    ]

    print('Testing API endpoints:')
    print('=' * 80)
    print(f'{"Endpoint":<35} {"Status":<15} {"Details"}')
    print('-' * 80)

    results = []

    for endpoint in endpoints:
        try:
            r = requests.get(f'{base_url}{endpoint}', headers=headers, timeout=10, verify=False)

            if r.status_code == 200:
                status = 'SUCCESS'
                try:
                    data = r.json()
                    if isinstance(data, list):
                        detail = f'Found {len(data)} items'
                        results.append({
                            'endpoint': endpoint,
                            'status': 'success',
                            'count': len(data),
                            'sample': data[:2] if len(data) > 0 else []
                        })
                    elif isinstance(data, dict):
                        keys = list(data.keys())[:5]
                        detail = f'Keys: {", ".join(keys)}'
                        results.append({
                            'endpoint': endpoint,
                            'status': 'success',
                            'keys': keys,
                            'sample': data
                        })
                    else:
                        detail = f'Type: {type(data).__name__}'
                        results.append({
                            'endpoint': endpoint,
                            'status': 'success',
                            'type': type(data).__name__
                        })
                except Exception as e:
                    detail = f'Length: {len(r.text)} bytes'
                    results.append({
                        'endpoint': endpoint,
                        'status': 'success',
                        'size': len(r.text)
                    })
            else:
                status = f'{r.status_code}'
                detail = r.text[:80].replace('\n', ' ')
                results.append({
                    'endpoint': endpoint,
                    'status': status,
                    'error': detail
                })

            print(f'{endpoint:<35} {status:<15} {detail}')

        except Exception as e:
            status = 'ERROR'
            detail = str(e)[:60]
            print(f'{endpoint:<35} {status:<15} {detail}')
            results.append({
                'endpoint': endpoint,
                'status': 'error',
                'error': str(e)
            })

    print('=' * 80)
    print()

    # Show successful endpoints with details
    print('SUCCESSFUL ENDPOINTS WITH SAMPLE DATA:')
    print('=' * 80)

    for result in results:
        if result.get('status') == 'success':
            print(f"\n{result['endpoint']}:")
            print('-' * 80)
            if 'sample' in result:
                print(json.dumps(result['sample'], indent=2)[:500])

    print()
    print('=' * 80)
    print('ENDPOINT DISCOVERY COMPLETE')
    print('=' * 80)

if __name__ == '__main__':
    check_endpoints()
