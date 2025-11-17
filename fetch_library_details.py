"""
Fetch Library Details from Commvault API
Retrieves comprehensive information about storage libraries including Quantum ActiveScale
"""

import requests
import base64
import configparser
import sqlite3
from datetime import datetime
import json

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
print("FETCHING LIBRARY DETAILS FROM COMMVAULT API")
print("=" * 100)
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"CommVault Server: {BASE_URL}")
print()

# Connect to database
conn = sqlite3.connect('Database/commvault.db')
cur = conn.cursor()

# Get current libraries from database
cur.execute("SELECT libraryId, libraryName FROM libraries")
existing_libraries = cur.fetchall()

print(f"Found {len(existing_libraries)} libraries in database")
print()

# Library type mapping
LIBRARY_TYPES = {
    "1": "Tape Library",
    "2": "Optical Library",
    "3": "Disk Library",
    "4": "Network Attached Storage (NAS)",
    "5": "Cloud Storage",
    "6": "Deduplication Engine"
}

# Try multiple API endpoints to get library information
library_endpoints = [
    ("/Library", "All libraries"),
    ("/V2/Library", "All libraries (V2)"),
    ("/V4/Library", "All libraries (V4)"),
]

libraries_data = []

print("=" * 100)
print("ATTEMPTING TO FETCH LIBRARY LIST")
print("=" * 100)
print()

for endpoint, description in library_endpoints:
    print(f"Trying: {BASE_URL}{endpoint}")
    print(f"  Description: {description}")

    try:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, verify=False, timeout=30)

        print(f"  Response Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            if data:
                print(f"  Response received, parsing...")

                # Try different response structures
                lib_list = data.get("libraryList", [])
                if not lib_list:
                    lib_list = data.get("libraries", [])
                if not lib_list and isinstance(data, list):
                    lib_list = data

                if lib_list:
                    print(f"  Found {len(lib_list)} libraries")
                    libraries_data = lib_list
                    print()
                    break
                else:
                    print(f"  No library list found in response")
                    print(f"  Response keys: {list(data.keys())[:10]}")
            else:
                print(f"  Empty response")
        else:
            print(f"  Failed: HTTP {response.status_code}")
            if response.text:
                print(f"  Response: {response.text[:200]}")

        print()

    except requests.exceptions.RequestException as e:
        print(f"  Connection error: {e}")
        print()
    except Exception as e:
        print(f"  Error: {e}")
        print()

# If we got libraries, try to get detailed info for each
if libraries_data:
    print("=" * 100)
    print("LIBRARY LIST RETRIEVED - FETCHING DETAILED INFORMATION")
    print("=" * 100)
    print()

    for lib in libraries_data:
        lib_id = lib.get("libraryId") or lib.get("id")
        lib_name = lib.get("libraryName") or lib.get("name")
        lib_type = str(lib.get("libraryType", ""))

        print(f"Library: {lib_name} (ID: {lib_id})")
        print(f"  Type: {lib_type} - {LIBRARY_TYPES.get(lib_type, 'Unknown')}")

        # Try to get detailed info
        detail_endpoint = f"/Library/{lib_id}"

        try:
            detail_response = requests.get(f"{BASE_URL}{detail_endpoint}", headers=headers, verify=False, timeout=30)

            if detail_response.status_code == 200:
                detail_data = detail_response.json()

                print(f"  Status: {detail_data.get('status', 'Unknown')}")
                print(f"  Media Agent: {detail_data.get('mediaAgentName', 'N/A')}")

                if 'capacity' in detail_data:
                    capacity_gb = detail_data['capacity'] / (1024**3)
                    print(f"  Capacity: {capacity_gb:.2f} GB")

                if 'freeSpace' in detail_data:
                    free_gb = detail_data['freeSpace'] / (1024**3)
                    print(f"  Free Space: {free_gb:.2f} GB")

                if 'libraryVendorType' in detail_data:
                    print(f"  Vendor Type: {detail_data['libraryVendorType']}")

                # Check for cloud storage specific fields
                if lib_type == "5":  # Cloud storage
                    print(f"  ** CLOUD STORAGE DETECTED **")
                    if 'cloudProvider' in detail_data:
                        print(f"  Cloud Provider: {detail_data['cloudProvider']}")
                    if 's3Endpoint' in detail_data:
                        print(f"  S3 Endpoint: {detail_data['s3Endpoint']}")
                    if 'storageClass' in detail_data:
                        print(f"  Storage Class: {detail_data['storageClass']}")

                # Save detailed data
                lib['detailedInfo'] = detail_data

            else:
                print(f"  Could not fetch details (HTTP {detail_response.status_code})")

        except Exception as e:
            print(f"  Error fetching details: {e}")

        print()

else:
    print("WARNING: Could not retrieve library list from any endpoint")
    print()
    print("Attempting to get library details for existing database entries...")
    print()

    # Try to get details for libraries we already know about
    for lib_id, lib_name in existing_libraries:
        print(f"Fetching details for: {lib_name} (ID: {lib_id})")

        detail_endpoint = f"/Library/{lib_id}"

        try:
            detail_response = requests.get(f"{BASE_URL}{detail_endpoint}", headers=headers, verify=False, timeout=30)

            print(f"  Response Status: {detail_response.status_code}")

            if detail_response.status_code == 200:
                detail_data = detail_response.json()

                lib_type = str(detail_data.get('libraryType', ''))
                print(f"  Type: {lib_type} - {LIBRARY_TYPES.get(lib_type, 'Unknown')}")
                print(f"  Status: {detail_data.get('status', 'Unknown')}")

                if 'mediaAgentName' in detail_data:
                    print(f"  Media Agent: {detail_data['mediaAgentName']}")

                if 'libraryVendorType' in detail_data:
                    print(f"  Vendor Type: {detail_data['libraryVendorType']}")

                # Check if this is Quantum ActiveScale
                if lib_type == "5":  # Cloud storage
                    print(f"  ** POSSIBLE QUANTUM ACTIVESCALE OR CLOUD STORAGE **")

                # Add to libraries_data
                libraries_data.append({
                    "libraryId": lib_id,
                    "libraryName": lib_name,
                    "libraryType": lib_type,
                    "detailedInfo": detail_data
                })

            else:
                print(f"  Failed: HTTP {detail_response.status_code}")

        except Exception as e:
            print(f"  Error: {e}")

        print()

# Analyze findings
print("=" * 100)
print("ANALYSIS - STORAGE DEVICE IDENTIFICATION")
print("=" * 100)
print()

cloud_libraries = []
disk_libraries = []
quantum_candidates = []

for lib in libraries_data:
    lib_type = str(lib.get('libraryType', ''))
    lib_name = lib.get('libraryName', '')

    if lib_type == "5":
        cloud_libraries.append(lib)

        # Check if name suggests Quantum
        if any(keyword in lib_name.upper() for keyword in ['QUANTUM', 'ACTIVESCALE', 'AS_', 'QAS']):
            quantum_candidates.append(lib)

    elif lib_type == "3":
        disk_libraries.append(lib)

print(f"Cloud Storage Libraries: {len(cloud_libraries)}")
for lib in cloud_libraries:
    print(f"  - {lib['libraryName']} (ID: {lib['libraryId']})")

print()
print(f"Disk Libraries: {len(disk_libraries)}")
for lib in disk_libraries:
    print(f"  - {lib['libraryName']} (ID: {lib['libraryId']})")

print()
print(f"Potential Quantum ActiveScale Libraries: {len(quantum_candidates)}")
for lib in quantum_candidates:
    print(f"  - {lib['libraryName']} (ID: {lib['libraryId']})")

if quantum_candidates:
    print()
    print("QUANTUM ACTIVESCALE DETECTED:")
    for lib in quantum_candidates:
        print(f"\nLibrary: {lib['libraryName']}")
        print(f"  Library ID: {lib['libraryId']}")
        print(f"  Type: Cloud Storage (Object Storage)")
        if 'detailedInfo' in lib:
            details = lib['detailedInfo']
            print(f"  Status: {details.get('status', 'Unknown')}")
            print(f"  MediaAgent: {details.get('mediaAgentName', 'N/A')}")
            if 'libraryVendorType' in details:
                print(f"  Vendor Type Code: {details['libraryVendorType']}")

# Save results to file
print()
print("=" * 100)
print("SAVING RESULTS")
print("=" * 100)
print()

# Save JSON dump
with open('library_details_dump.json', 'w') as f:
    json.dump(libraries_data, f, indent=2)
    print(f"Saved detailed library data to: library_details_dump.json")

# Save summary report
with open('LIBRARY_ANALYSIS_REPORT.txt', 'w') as f:
    f.write("=" * 100 + "\n")
    f.write("LIBRARY ANALYSIS REPORT\n")
    f.write("=" * 100 + "\n")
    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"\nTotal Libraries Analyzed: {len(libraries_data)}\n")
    f.write(f"Cloud Storage Libraries: {len(cloud_libraries)}\n")
    f.write(f"Disk Libraries: {len(disk_libraries)}\n")
    f.write(f"Quantum ActiveScale Candidates: {len(quantum_candidates)}\n")
    f.write("\n")

    f.write("=" * 100 + "\n")
    f.write("ALL LIBRARIES\n")
    f.write("=" * 100 + "\n\n")

    for lib in libraries_data:
        lib_type = str(lib.get('libraryType', ''))
        f.write(f"Library: {lib['libraryName']}\n")
        f.write(f"  ID: {lib['libraryId']}\n")
        f.write(f"  Type: {lib_type} - {LIBRARY_TYPES.get(lib_type, 'Unknown')}\n")

        if 'detailedInfo' in lib:
            details = lib['detailedInfo']
            f.write(f"  Status: {details.get('status', 'Unknown')}\n")
            f.write(f"  MediaAgent: {details.get('mediaAgentName', 'N/A')}\n")
            if 'libraryVendorType' in details:
                f.write(f"  Vendor Type: {details['libraryVendorType']}\n")

        f.write("\n")

    if quantum_candidates:
        f.write("\n")
        f.write("=" * 100 + "\n")
        f.write("QUANTUM ACTIVESCALE STORAGE DETECTED\n")
        f.write("=" * 100 + "\n\n")

        for lib in quantum_candidates:
            f.write(f"Library: {lib['libraryName']}\n")
            f.write(f"  Configuration: Cloud Storage / Object Storage\n")
            f.write(f"  Likely Vendor: Quantum ActiveScale\n")
            f.write(f"  Library ID: {lib['libraryId']}\n")
            if 'detailedInfo' in lib and 'mediaAgentName' in lib['detailedInfo']:
                f.write(f"  Connected via MediaAgent: {lib['detailedInfo']['mediaAgentName']}\n")
            f.write("\n")

print("Saved analysis report to: LIBRARY_ANALYSIS_REPORT.txt")

print()
print("=" * 100)
print("END OF LIBRARY DETAILS FETCH")
print("=" * 100)

conn.close()
