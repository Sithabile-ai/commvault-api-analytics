"""
Commvault Data Retrieval Web Application
Flask-based web app to connect to Commvault REST API and store data in SQLite
"""

from flask import Flask, render_template, request, g, flash, redirect, url_for, session, Response
import sqlite3
import requests
import base64
import json
import configparser
import os
import time
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'commvault_secret_key_change_in_production'  # Change this in production

# API Activity Logger
def log_api_activity(activity_type, message):
    """Log API activity to session for display in frontend"""
    if 'api_activity' not in session:
        session['api_activity'] = []

    session['api_activity'].append({
        'type': activity_type,
        'message': message,
        'timestamp': datetime.now().strftime('%H:%M:%S')
    })

    # Keep only last 50 entries
    if len(session['api_activity']) > 50:
        session['api_activity'] = session['api_activity'][-50:]

    session.modified = True

# API Request Logger
def log_api_request(method, endpoint, status_code, count=None, duration=None):
    """Log API GET requests to session for display in frontend"""
    try:
        if 'api_requests' not in session:
            session['api_requests'] = []

        # Determine status class
        status_class = 'success' if 200 <= status_code < 300 else 'error'

        session['api_requests'].append({
            'method': method,
            'endpoint': endpoint,
            'status_code': status_code,
            'status_class': status_class,
            'count': count,
            'duration': duration,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })

        # Keep only last 30 entries
        if len(session['api_requests']) > 30:
            session['api_requests'] = session['api_requests'][-30:]

        session.modified = True
    except RuntimeError:
        # Working outside of request context - skip session logging
        pass

# Configuration
CONFIG_FILE = 'config.ini'
DB_PATH = 'Database/commvault.db'

def load_config():
    """Load configuration from config.ini file"""
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        return {
            'base_url': config.get('commvault', 'base_url', fallback=''),
            'username': config.get('commvault', 'username', fallback=''),
            'password': config.get('commvault', 'password', fallback=''),
            'db_path': config.get('database', 'db_path', fallback='Database/commvault.db')
        }
    return {'base_url': '', 'username': '', 'password': '', 'db_path': 'Database/commvault.db'}

def get_db():
    """Get database connection"""
    if 'db' not in g:
        # Ensure Database directory exists
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Close database connection"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database schema"""
    db = sqlite3.connect(DB_PATH)
    cursor = db.cursor()

    # Create table for Clients
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            clientId       INTEGER PRIMARY KEY,
            clientName     TEXT,
            hostName       TEXT,
            clientGUID     TEXT,
            lastFetchTime  TEXT
        )
    """)

    # Create table for Jobs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            jobId          INTEGER PRIMARY KEY,
            clientId       INTEGER,
            clientName     TEXT,
            jobType        TEXT,
            status         TEXT,
            startTime      TEXT,
            endTime        TEXT,
            backupSetName  TEXT,
            lastFetchTime  TEXT
        )
    """)

    # Create table for Plans (Policies)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            planId         INTEGER PRIMARY KEY,
            planName       TEXT,
            planType       TEXT,
            lastFetchTime  TEXT
        )
    """)

    # Create table for Storage Policies
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS storage_policies (
            storagePolicyId   INTEGER PRIMARY KEY,
            storagePolicyName TEXT,
            lastFetchTime     TEXT
        )
    """)

    # Create table for MediaAgents (Infrastructure)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mediaagents (
            mediaAgentId      INTEGER PRIMARY KEY,
            mediaAgentName    TEXT,
            hostName          TEXT,
            osType            TEXT,
            status            TEXT,
            availableSpace    TEXT,
            totalSpace        TEXT,
            lastFetchTime     TEXT
        )
    """)

    # Create table for Libraries (Tape/Disk Libraries)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS libraries (
            libraryId         INTEGER PRIMARY KEY,
            libraryName       TEXT,
            libraryType       TEXT,
            mediaAgentName    TEXT,
            status            TEXT,
            lastFetchTime     TEXT
        )
    """)

    # Create table for Storage Pools
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS storage_pools (
            storagePoolId     INTEGER PRIMARY KEY,
            storagePoolName   TEXT,
            storagePoolType   TEXT,
            mediaAgentName    TEXT,
            totalCapacity     TEXT,
            freeSpace         TEXT,
            dedupeEnabled     TEXT,
            lastFetchTime     TEXT
        )
    """)

    # Create table for Hypervisors/VM Infrastructure
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hypervisors (
            instanceId        INTEGER PRIMARY KEY,
            instanceName      TEXT,
            hypervisorType    TEXT,
            hostName          TEXT,
            vendor            TEXT,
            status            TEXT,
            lastFetchTime     TEXT
        )
    """)

    # Create table for Disk Storage Arrays
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS storage_arrays (
            arrayId           INTEGER PRIMARY KEY,
            arrayName         TEXT,
            arrayType         TEXT,
            vendor            TEXT,
            model             TEXT,
            totalCapacity     TEXT,
            usedCapacity      TEXT,
            lastFetchTime     TEXT
        )
    """)

    # Create table for Plans (Modern Commvault backup configuration)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            planId            INTEGER PRIMARY KEY,
            planName          TEXT,
            description       TEXT,
            type              INTEGER,
            subtype           INTEGER,
            numCopies         INTEGER,
            numAssocEntities  INTEGER,
            rpoInMinutes      INTEGER,
            storageTarget     TEXT,
            storagePolicyId   INTEGER,
            isElastic         INTEGER,
            statusFlag        INTEGER,
            lastFetchTime     TEXT
        )
    """)

    # Create table for Retention Rules (Aging Policy data)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS retention_rules (
            ruleId                          INTEGER PRIMARY KEY AUTOINCREMENT,
            entityType                      TEXT NOT NULL,
            entityId                        INTEGER NOT NULL,
            entityName                      TEXT,
            parentId                        INTEGER,
            parentName                      TEXT,
            retainBackupDataForDays         INTEGER,
            retainBackupDataForCycles       INTEGER,
            retainArchiverDataForDays       INTEGER,
            enableDataAging                 INTEGER,
            jobBasedRetention               INTEGER,
            firstExtendedRetentionDays      INTEGER,
            firstExtendedRetentionCycles    INTEGER,
            secondExtendedRetentionDays     INTEGER,
            secondExtendedRetentionCycles   INTEGER,
            lastFetchTime                   TEXT,
            UNIQUE(entityType, entityId)
        )
    """)

    # Create table for Events (Alerts and Critical Events)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            eventId           INTEGER PRIMARY KEY,
            eventCode         TEXT,
            severity          TEXT,
            eventType         TEXT,
            message           TEXT,
            timeSource        TEXT,
            subsystem         TEXT,
            clientName        TEXT,
            jobId             INTEGER,
            lastFetchTime     TEXT
        )
    """)

    # Create table for Alerts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            alertId           INTEGER PRIMARY KEY,
            alertName         TEXT,
            alertType         TEXT,
            severity          TEXT,
            status            TEXT,
            alertMessage      TEXT,
            triggerTime       TEXT,
            lastFetchTime     TEXT
        )
    """)

    # Create table for CommCell Info (Health Check)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS commcell_info (
            id                INTEGER PRIMARY KEY,
            commcellName      TEXT,
            commserveVersion  TEXT,
            timeZone          TEXT,
            commserveHost     TEXT,
            status            TEXT,
            lastCheckTime     TEXT
        )
    """)

    # Create table for Selected MediaAgents (for environment filtering)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS selected_mediaagents (
            mediaAgentId      INTEGER PRIMARY KEY,
            mediaAgentName    TEXT NOT NULL,
            selectedDate      TEXT,
            notes             TEXT,
            FOREIGN KEY (mediaAgentId) REFERENCES mediaagents(mediaAgentId)
        )
    """)

    # Enhance jobs table with performance metrics (if not exists, SQLite will ignore)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs_enhanced (
            jobId                INTEGER PRIMARY KEY,
            clientId             INTEGER,
            clientName           TEXT,
            jobType              TEXT,
            status               TEXT,
            startTime            TEXT,
            endTime              TEXT,
            backupSetName        TEXT,
            sizeOfApplication    TEXT,
            sizeOfMediaOnDisk    TEXT,
            percentSavings       REAL,
            throughputMBps       REAL,
            jobElapsedTime       TEXT,
            filesCount           INTEGER,
            lastFetchTime        TEXT
        )
    """)

    db.commit()
    db.close()

def authenticate_commvault(base_url, username, password):
    """
    Authenticate with Commvault API and return auth token

    Args:
        base_url: Commvault API base URL
        username: Username for authentication (can include @ for email format)
        password: Password (can be plaintext or Base64-encoded)

    Returns:
        Auth token string or None if authentication fails
    """
    try:
        # Check if password is already Base64 encoded
        # If not, encode it
        try:
            # Try to decode to check if it's valid base64
            decoded = base64.b64decode(password).decode('utf-8')
            # Check if decoded value is reasonable (not binary gibberish)
            if len(decoded) > 0 and all(c.isprintable() or c.isspace() for c in decoded):
                encoded_password = password
            else:
                # Looks like binary data, encode the original
                encoded_password = base64.b64encode(password.encode('utf-8')).decode('utf-8')
        except:
            # Not valid base64, encode it
            encoded_password = base64.b64encode(password.encode('utf-8')).decode('utf-8')

        login_payload = {
            "username": username,
            "password": encoded_password
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        # Make login request
        start_time = time.time()
        response = requests.post(
            f"{base_url}/Login",
            json=login_payload,
            headers=headers,
            timeout=30,
            verify=False  # Disable SSL verification for self-signed certs
        )
        duration = int((time.time() - start_time) * 1000)  # Convert to milliseconds

        # Log the POST request
        log_api_request('POST', '/Login', response.status_code, duration=duration)

        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get('token', '')

            # Strip "QSDK " prefix if present
            if token.startswith("QSDK "):
                token = token[5:]

            print(f"Authentication successful for user: {username}")
            return token
        else:
            print(f"Login failed with status {response.status_code}: {response.text[:200]}")
            return None

    except requests.exceptions.Timeout as e:
        error_msg = f"Connection timeout after 30 seconds"
        print(f"Authentication error (TIMEOUT): {error_msg}")
        print(f"  URL: {base_url}/Login")
        print(f"  User: {username}")
        print(f"  This typically indicates port {base_url.split(':')[1].split('/')[0] if ':' in base_url else '80'} is not accessible")
        log_api_activity('error', f'Authentication timeout for {username}')
        return None
    except requests.exceptions.ConnectionError as e:
        error_msg = str(e)
        print(f"Authentication error (CONNECTION): {error_msg[:200]}")
        print(f"  URL: {base_url}/Login")
        print(f"  User: {username}")
        print(f"  Cannot reach server - check network connectivity")
        log_api_activity('error', f'Connection error for {username}: {error_msg[:100]}')
        return None
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        print(f"Authentication error (REQUEST): {error_msg[:200]}")
        print(f"  URL: {base_url}/Login")
        print(f"  User: {username}")
        log_api_activity('error', f'Request error for {username}: {error_msg[:100]}')
        return None
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        print(f"Authentication error ({error_type}): {error_msg[:200]}")
        print(f"  URL: {base_url}/Login")
        print(f"  User: {username}")
        log_api_activity('error', f'{error_type} for {username}: {error_msg[:100]}')
        return None

def save_clients_to_db(db, clients_json):
    """Save clients data to database"""
    cur = db.cursor()
    fetch_time = datetime.now().isoformat()

    client_properties = clients_json.get("clientProperties", [])
    for client_entry in client_properties:
        client_info = client_entry.get("client", {})
        client_id = client_info.get("clientId")
        name = client_info.get("clientName", "")
        host = client_info.get("hostName", "")
        guid = client_info.get("GUID", "")

        if client_id:
            cur.execute(
                "REPLACE INTO clients (clientId, clientName, hostName, clientGUID, lastFetchTime) VALUES (?, ?, ?, ?, ?)",
                (client_id, name, host, guid, fetch_time)
            )

    return len(client_properties)

def save_jobs_to_db(db, jobs_json):
    """Save jobs data to database"""
    cur = db.cursor()
    fetch_time = datetime.now().isoformat()

    jobs_list = jobs_json.get("jobs", [])
    for job_entry in jobs_list:
        job_summary = job_entry.get("jobSummary", {})
        job_id = job_summary.get("jobId")

        if job_id:
            client_id = job_summary.get("subclient", {}).get("clientId", 0)
            client_name = job_summary.get("subclient", {}).get("clientName", "")
            job_type = job_summary.get("jobType", "")
            status = job_summary.get("status", "")
            start_time = job_summary.get("jobStartTime", "")
            end_time = job_summary.get("jobEndTime", "")
            backupset_name = job_summary.get("backupSet", {}).get("backupSetName", "")

            cur.execute(
                """REPLACE INTO jobs
                (jobId, clientId, clientName, jobType, status, startTime, endTime, backupSetName, lastFetchTime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (job_id, client_id, client_name, job_type, status, start_time, end_time, backupset_name, fetch_time)
            )

    return len(jobs_list)

def save_plans_to_db(db, plans_json):
    """Save plans data to database"""
    cur = db.cursor()
    fetch_time = datetime.now().isoformat()

    plans_list = plans_json.get("plans", [])
    for plan_entry in plans_list:
        plan_id = plan_entry.get("plan", {}).get("planId")
        plan_name = plan_entry.get("plan", {}).get("planName", "")
        plan_type = plan_entry.get("planType", "")

        if plan_id:
            cur.execute(
                "REPLACE INTO plans (planId, planName, planType, lastFetchTime) VALUES (?, ?, ?, ?)",
                (plan_id, plan_name, plan_type, fetch_time)
            )

    return len(plans_list)

def save_storage_to_db(db, storage_json):
    """Save storage policies data to database"""
    cur = db.cursor()
    fetch_time = datetime.now().isoformat()

    policies_list = storage_json.get("policies", [])
    for policy_entry in policies_list:
        storage_policy = policy_entry.get("storagePolicy", {})
        policy_id = storage_policy.get("storagePolicyId")
        policy_name = storage_policy.get("storagePolicyName", "")

        if policy_id:
            cur.execute(
                "REPLACE INTO storage_policies (storagePolicyId, storagePolicyName, lastFetchTime) VALUES (?, ?, ?)",
                (policy_id, policy_name, fetch_time)
            )

    return len(policies_list)

def save_mediaagents_to_db(db, mediaagents_json):
    """Save MediaAgents data to database"""
    cur = db.cursor()
    fetch_time = datetime.now().isoformat()

    # FIXED: API returns response array with entityInfo structure
    ma_list = mediaagents_json.get("response", [])

    # Fallback to old structure for compatibility
    if not ma_list:
        ma_list = mediaagents_json.get("mediaAgentList", [])
        if not ma_list:
            ma_list = mediaagents_json.get("mediaAgents", [])

    for ma_entry in ma_list:
        # Check if using new entityInfo structure
        if "entityInfo" in ma_entry:
            entity_info = ma_entry.get("entityInfo", {})
            ma_id = entity_info.get("id")
            name = entity_info.get("name", "")
            host = entity_info.get("hostName", "")
            os_type = ma_entry.get("osType", "")
            status = ma_entry.get("status", "Online")
            available_space = ma_entry.get("availableSpace", "N/A")
            total_space = ma_entry.get("totalSpace", "N/A")
        else:
            # Old structure fallback
            ma_info = ma_entry.get("mediaAgent", ma_entry)
            ma_id = ma_info.get("mediaAgentId")
            name = ma_info.get("mediaAgentName", "")
            host = ma_info.get("hostName", "")
            os_type = ma_info.get("osType", "")
            status = ma_info.get("status", "Online")
            available_space = ma_info.get("availableSpace", "N/A")
            total_space = ma_info.get("totalSpace", "N/A")

        if ma_id:
            cur.execute(
                """REPLACE INTO mediaagents
                (mediaAgentId, mediaAgentName, hostName, osType, status, availableSpace, totalSpace, lastFetchTime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (ma_id, name, host, os_type, status, str(available_space), str(total_space), fetch_time)
            )

    return len(ma_list)

def save_libraries_to_db(db, libraries_json):
    """Save Libraries data to database"""
    cur = db.cursor()
    fetch_time = datetime.now().isoformat()

    # FIXED: API returns response array with entityInfo structure
    lib_list = libraries_json.get("response", [])

    # Fallback to old structure for compatibility
    if not lib_list:
        lib_list = libraries_json.get("libraryList", [])
        if not lib_list:
            lib_list = libraries_json.get("libraries", [])

    for lib_entry in lib_list:
        # Check if using new entityInfo structure
        if "entityInfo" in lib_entry:
            entity_info = lib_entry.get("entityInfo", {})
            lib_id = entity_info.get("id")
            name = entity_info.get("name", "")
            lib_type = lib_entry.get("libraryType", "")
            ma_name = lib_entry.get("mediaAgentName", "")
            status = lib_entry.get("status", "Online")
        else:
            # Old structure fallback
            lib_info = lib_entry.get("library", lib_entry)
            lib_id = lib_info.get("libraryId")
            name = lib_info.get("libraryName", "")
            lib_type = lib_info.get("libraryType", "")
            ma_name = lib_info.get("mediaAgentName", "")
            status = lib_info.get("status", "Online")

        if lib_id:
            cur.execute(
                """REPLACE INTO libraries
                (libraryId, libraryName, libraryType, mediaAgentName, status, lastFetchTime)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (lib_id, name, lib_type, ma_name, status, fetch_time)
            )

    return len(lib_list)

def save_storage_pools_to_db(db, pools_json):
    """Save Storage Pools data to database"""
    cur = db.cursor()
    fetch_time = datetime.now().isoformat()

    # FIXED: API returns storagePoolList (not storagePools)
    pools_list = pools_json.get("storagePoolList", [])

    # Fallback to old structure for compatibility
    if not pools_list:
        pools_list = pools_json.get("storagePools", [])
        if not pools_list:
            pools_list = pools_json.get("storagePoolsList", [])

    for pool_entry in pools_list:
        # FIXED: Pool ID and name are in storagePoolEntity, not storagePool
        pool_entity = pool_entry.get("storagePoolEntity", {})
        pool_id = pool_entity.get("storagePoolId")
        name = pool_entity.get("storagePoolName", "")

        # Pool type is at pool_entry level
        pool_type = pool_entry.get("storagePoolType", "")

        # Storage type for better categorization
        storage_type = pool_entry.get("storageType", "")

        # MediaAgent name - may not always be present
        ma_name = pool_entry.get("mediaAgentName", "")

        # Capacity info is at pool_entry level
        total_cap = pool_entry.get("totalCapacity", "N/A")
        free_space = pool_entry.get("totalFreeSpace", "N/A")

        # Check for deduplication in dedupeFlags if present
        dedupe_flags = pool_entry.get("dedupeFlags", {})
        if dedupe_flags and dedupe_flags.get("enableDeduplication"):
            dedupe = "Yes"
        else:
            dedupe = pool_entry.get("dedupeEnabled", "No")

        if pool_id:
            cur.execute(
                """REPLACE INTO storage_pools
                (storagePoolId, storagePoolName, storagePoolType, mediaAgentName, totalCapacity, freeSpace, dedupeEnabled, lastFetchTime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (pool_id, name, pool_type, ma_name, str(total_cap), str(free_space), str(dedupe), fetch_time)
            )

    return len(pools_list)

def save_hypervisors_to_db(db, hypervisors_json):
    """Save Hypervisors/VM Infrastructure data to database"""
    cur = db.cursor()
    fetch_time = datetime.now().isoformat()

    hv_list = hypervisors_json.get("VSInstanceProperties", [])
    if not hv_list:
        hv_list = hypervisors_json.get("instances", [])

    for hv_entry in hv_list:
        hv_info = hv_entry.get("instance", hv_entry)
        instance_id = hv_info.get("instanceId")
        name = hv_info.get("instanceName", "")
        hv_type = hv_info.get("hypervisorType", hv_info.get("vendorName", ""))
        host = hv_info.get("clientName", hv_info.get("hostName", ""))
        vendor = hv_info.get("vendor", hv_info.get("vendorName", ""))
        status = hv_info.get("status", "Active")

        if instance_id:
            cur.execute(
                """REPLACE INTO hypervisors
                (instanceId, instanceName, hypervisorType, hostName, vendor, status, lastFetchTime)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (instance_id, name, hv_type, host, vendor, status, fetch_time)
            )

    return len(hv_list)

def save_storage_arrays_to_db(db, arrays_json):
    """Save Storage Arrays data to database"""
    cur = db.cursor()
    fetch_time = datetime.now().isoformat()

    arrays_list = arrays_json.get("storageArrays", [])
    if not arrays_list:
        arrays_list = arrays_json.get("arrays", [])

    for array_entry in arrays_list:
        array_info = array_entry.get("array", array_entry)
        array_id = array_info.get("arrayId", array_info.get("id"))
        name = array_info.get("arrayName", array_info.get("name", ""))
        array_type = array_info.get("arrayType", "")
        vendor = array_info.get("vendor", "")
        model = array_info.get("model", "")
        total_cap = array_info.get("totalCapacity", "N/A")
        used_cap = array_info.get("usedCapacity", "N/A")

        if array_id:
            cur.execute(
                """REPLACE INTO storage_arrays
                (arrayId, arrayName, arrayType, vendor, model, totalCapacity, usedCapacity, lastFetchTime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (array_id, name, array_type, vendor, model, str(total_cap), str(used_cap), fetch_time)
            )

    return len(arrays_list)

def save_plans_to_db(db, plans_json):
    """Save Plans data to database with retention rules extraction"""
    cur = db.cursor()
    fetch_time = datetime.now().isoformat()

    plans_list = plans_json.get("plans", [])

    plan_count = 0
    retention_count = 0

    for plan_entry in plans_list:
        # Extract plan basic info
        plan_info = plan_entry.get("plan", {})
        plan_id = plan_info.get("planId")
        plan_name = plan_info.get("planName", "")

        # Summary info
        description = plan_entry.get("description", "")
        plan_type = plan_entry.get("type", 0)
        subtype = plan_entry.get("subtype", 0)
        num_copies = plan_entry.get("numCopies", 0)
        num_entities = plan_entry.get("numAssocEntities", 0)
        rpo_minutes = plan_entry.get("rpoInMinutes", 0)
        storage_target = plan_entry.get("storageTarget", "")

        # Flags
        is_elastic = 1 if plan_entry.get("isElastic", False) else 0
        status_flag = plan_entry.get("planStatusFlag", 0)

        # Associated storage policy
        storage = plan_entry.get("storage", {})
        storage_policy_info = storage.get("storagePolicy", {})
        storage_policy_id = storage_policy_info.get("storagePolicyId", None)

        if plan_id:
            # Save plan basic info
            cur.execute("""
                REPLACE INTO plans (
                    planId, planName, description, type, subtype,
                    numCopies, numAssocEntities, rpoInMinutes,
                    storageTarget, storagePolicyId, isElastic,
                    statusFlag, lastFetchTime
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                plan_id, plan_name, description, plan_type, subtype,
                num_copies, num_entities, rpo_minutes, storage_target,
                storage_policy_id, is_elastic, status_flag, fetch_time
            ))
            plan_count += 1

            # Extract retention rules from each copy
            copies = storage.get("copy", [])
            for copy in copies:
                copy_info = copy.get("StoragePolicyCopy", {})
                copy_id = copy_info.get("copyId")
                copy_name = copy_info.get("copyName", "")

                if copy_id:
                    retention_rules = copy.get("retentionRules", {})
                    retention_flags = retention_rules.get("retentionFlags", {})

                    # Extract extended retention if present
                    extended_retention = copy.get("extendedRetentionRules", {})
                    first_extended = extended_retention.get("firstExtendedRetentionRule", {})
                    second_extended = extended_retention.get("secondExtendedRetentionRule", {})

                    # Save retention rule
                    cur.execute("""
                        REPLACE INTO retention_rules (
                            entityType, entityId, entityName, parentId, parentName,
                            retainBackupDataForDays, retainBackupDataForCycles,
                            retainArchiverDataForDays, enableDataAging, jobBasedRetention,
                            firstExtendedRetentionDays, firstExtendedRetentionCycles,
                            secondExtendedRetentionDays, secondExtendedRetentionCycles,
                            lastFetchTime
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        'plan_copy', copy_id, copy_name, plan_id, plan_name,
                        retention_rules.get('retainBackupDataForDays', -1),
                        retention_rules.get('retainBackupDataForCycles', -1),
                        retention_rules.get('retainArchiverDataForDays', -1),
                        retention_flags.get('enableDataAging', 0),
                        retention_flags.get('jobBasedRetention', 0),
                        first_extended.get('retainBackupDataForDays', None),
                        first_extended.get('retainBackupDataForCycles', None),
                        second_extended.get('retainBackupDataForDays', None),
                        second_extended.get('retainBackupDataForCycles', None),
                        fetch_time
                    ))
                    retention_count += 1

    return plan_count

def save_events_to_db(db, events_json):
    """Save Events data to database"""
    cur = db.cursor()
    fetch_time = datetime.now().isoformat()

    events_list = events_json.get("commCellEvents", [])
    if not events_list:
        events_list = events_json.get("events", [])

    for event_entry in events_list:
        event_id = event_entry.get("eventId", event_entry.get("id"))
        event_code = event_entry.get("eventCode", event_entry.get("eventCodeString", ""))
        severity = event_entry.get("severity", event_entry.get("severityString", ""))
        event_type = event_entry.get("eventType", "")
        message = event_entry.get("description", event_entry.get("message", ""))
        time_source = event_entry.get("timeSource", "")
        subsystem = event_entry.get("subsystem", event_entry.get("subsystemString", ""))
        client_name = event_entry.get("clientName", "")
        job_id = event_entry.get("jobId", 0)

        if event_id:
            cur.execute(
                """REPLACE INTO events
                (eventId, eventCode, severity, eventType, message, timeSource, subsystem, clientName, jobId, lastFetchTime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_id, event_code, severity, event_type, message, time_source, subsystem, client_name, job_id, fetch_time)
            )

    return len(events_list)

def save_alerts_to_db(db, alerts_json):
    """Save Alerts data to database"""
    cur = db.cursor()
    fetch_time = datetime.now().isoformat()

    alerts_list = alerts_json.get("alertList", [])
    if not alerts_list:
        alerts_list = alerts_json.get("alerts", [])

    for alert_entry in alerts_list:
        alert_info = alert_entry.get("alert", alert_entry)
        alert_id = alert_info.get("alertId", alert_info.get("id"))
        name = alert_info.get("alertName", alert_info.get("name", ""))
        alert_type = alert_info.get("alertType", "")
        severity = alert_info.get("severity", "")
        status = alert_info.get("status", "Active")
        message = alert_info.get("message", alert_info.get("description", ""))
        trigger_time = alert_info.get("triggerTime", alert_info.get("timeStamp", ""))

        if alert_id:
            cur.execute(
                """REPLACE INTO alerts
                (alertId, alertName, alertType, severity, status, alertMessage, triggerTime, lastFetchTime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (alert_id, name, alert_type, severity, status, message, trigger_time, fetch_time)
            )

    return len(alerts_list)

def save_commcell_info_to_db(db, commcell_json):
    """Save CommCell info to database"""
    cur = db.cursor()
    check_time = datetime.now().isoformat()

    commcell_name = commcell_json.get("commCellName", commcell_json.get("name", ""))
    version = commcell_json.get("version", commcell_json.get("commServeVersion", ""))
    timezone = commcell_json.get("timeZone", "")
    host = commcell_json.get("commServeHostName", commcell_json.get("hostName", ""))
    status = "Online"  # If we can fetch this, CommServe is online

    # Always update the single row (id=1)
    cur.execute(
        """REPLACE INTO commcell_info
        (id, commcellName, commserveVersion, timeZone, commserveHost, status, lastCheckTime)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (1, commcell_name, version, timezone, host, status, check_time)
    )

    return 1

def save_enhanced_jobs_to_db(db, jobs_json):
    """Save enhanced job data with performance metrics"""
    cur = db.cursor()
    fetch_time = datetime.now().isoformat()

    jobs_list = jobs_json.get("jobs", [])
    for job_entry in jobs_list:
        job_summary = job_entry.get("jobSummary", {})
        job_id = job_summary.get("jobId")

        if job_id:
            client_id = job_summary.get("subclient", {}).get("clientId", 0)
            client_name = job_summary.get("subclient", {}).get("clientName", "")
            job_type = job_summary.get("jobType", "")
            status = job_summary.get("status", "")
            start_time = job_summary.get("jobStartTime", "")
            end_time = job_summary.get("jobEndTime", "")
            backupset_name = job_summary.get("backupSet", {}).get("backupSetName", "")

            # Performance metrics
            size_app = job_summary.get("sizeOfApplication", 0)
            size_disk = job_summary.get("sizeOfMediaOnDisk", 0)
            percent_savings = job_summary.get("percentSavings", 0.0)

            # Calculate throughput if we have elapsed time and size
            elapsed_time = job_summary.get("jobElapsedTime", 0)
            throughput = 0.0
            if elapsed_time and size_app:
                # Convert to MB/s (size_app is usually in bytes, elapsed_time in seconds)
                try:
                    throughput = (float(size_app) / 1024 / 1024) / float(elapsed_time) if elapsed_time > 0 else 0
                except:
                    throughput = 0.0

            files_count = job_summary.get("totalNumOfFiles", job_summary.get("filesCount", 0))

            cur.execute(
                """REPLACE INTO jobs_enhanced
                (jobId, clientId, clientName, jobType, status, startTime, endTime, backupSetName,
                 sizeOfApplication, sizeOfMediaOnDisk, percentSavings, throughputMBps, jobElapsedTime, filesCount, lastFetchTime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (job_id, client_id, client_name, job_type, status, start_time, end_time, backupset_name,
                 str(size_app), str(size_disk), percent_savings, throughput, str(elapsed_time), files_count, fetch_time)
            )

    return len(jobs_list)

@app.route("/", methods=["GET"])
def index():
    """Display configuration and data selection page"""
    config = load_config()
    return render_template("index.html", config=config)

@app.route("/fetch", methods=["POST"])
def fetch_data():
    """Fetch data from Commvault API and store in database"""
    # Read form data
    base_url = request.form.get("base_url", "").rstrip("/")
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    data_types = request.form.getlist("data_type")

    if not base_url or not username or not password:
        flash("Please provide all required connection details", "error")
        log_api_activity('error', 'Missing connection details')
        return redirect(url_for('index'))

    if not data_types:
        flash("Please select at least one data type to fetch", "warning")
        log_api_activity('warning', 'No data types selected')
        return redirect(url_for('index'))

    log_api_activity('info', f'Starting data fetch for {len(data_types)} data types')
    log_api_activity('info', f'Target: {base_url.split("//")[1].split("/")[0] if "//" in base_url else base_url.split("/")[0]}')

    # Authenticate with Commvault API
    log_api_activity('info', 'Authenticating with Commvault API...')
    token = authenticate_commvault(base_url, username, password)

    if not token:
        flash("Authentication failed. Please check your credentials.", "error")
        log_api_activity('error', 'Authentication failed - invalid credentials')
        return redirect(url_for('index'))

    log_api_activity('success', f'Authenticated as: {username}')

    # Prepare headers for API requests
    headers = {
        "Accept": "application/json",
        "Authtoken": token
    }

    db = get_db()
    results = {}
    counts = {}
    errors = {}

    # Fetch selected data types
    for dtype in data_types:
        try:
            if dtype == "clients":
                log_api_activity('info', 'Fetching Clients data...')
                start_time = time.time()
                response = requests.get(f"{base_url}/Client", headers=headers, timeout=30)
                duration = int((time.time() - start_time) * 1000)
                if response.status_code == 200:
                    data = response.json()
                    results["clients"] = data
                    counts["clients"] = save_clients_to_db(db, data)
                    log_api_request('GET', '/Client', response.status_code, count=counts["clients"], duration=duration)
                    log_api_activity('success', f'Retrieved {counts["clients"]} clients')
                else:
                    log_api_request('GET', '/Client', response.status_code, duration=duration)
                    errors["clients"] = f"Failed with status {response.status_code}"
                    log_api_activity('error', f'Clients fetch failed: HTTP {response.status_code}')

            elif dtype == "jobs":
                # FIXED: Add time filter to prevent timeout (86400 = last 24 hours)
                log_api_activity('info', 'Fetching Jobs (last 24h)...')
                response = requests.get(f"{base_url}/Job?completedJobLookupTime=86400", headers=headers, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    results["jobs"] = data
                    counts["jobs"] = save_jobs_to_db(db, data)
                    log_api_activity('success', f'Retrieved {counts["jobs"]} jobs')
                else:
                    errors["jobs"] = f"Failed with status {response.status_code}"
                    log_api_activity('error', f'Jobs fetch failed: HTTP {response.status_code}')

            elif dtype == "plans":
                response = requests.get(f"{base_url}/Plan", headers=headers, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    results["plans"] = data
                    counts["plans"] = save_plans_to_db(db, data)
                else:
                    errors["plans"] = f"Failed with status {response.status_code}"

            elif dtype == "storage":
                response = requests.get(f"{base_url}/V2/StoragePolicy", headers=headers, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    results["storage"] = data
                    counts["storage"] = save_storage_to_db(db, data)
                else:
                    errors["storage"] = f"Failed with status {response.status_code}"

            elif dtype == "plans":
                log_api_activity('info', 'Fetching Plans (with retention rules)...')
                start_time = time.time()
                response = requests.get(f"{base_url}/Plan", headers=headers, timeout=30)
                duration = int((time.time() - start_time) * 1000)
                if response.status_code == 200:
                    data = response.json()
                    results["plans"] = data
                    counts["plans"] = save_plans_to_db(db, data)
                    log_api_request('GET', '/Plan', response.status_code, count=counts["plans"], duration=duration)
                    log_api_activity('success', f'Retrieved {counts["plans"]} plans with retention rules')
                else:
                    log_api_request('GET', '/Plan', response.status_code, duration=duration)
                    errors["plans"] = f"Failed with status {response.status_code}"
                    log_api_activity('error', f'Plans fetch failed: HTTP {response.status_code}')

            elif dtype == "mediaagents":
                log_api_activity('info', 'Fetching MediaAgents...')
                start_time = time.time()
                response = requests.get(f"{base_url}/MediaAgent", headers=headers, timeout=30)
                duration = int((time.time() - start_time) * 1000)
                if response.status_code == 200:
                    data = response.json()
                    results["mediaagents"] = data
                    counts["mediaagents"] = save_mediaagents_to_db(db, data)
                    log_api_request('GET', '/MediaAgent', response.status_code, count=counts["mediaagents"], duration=duration)
                    log_api_activity('success', f'Retrieved {counts["mediaagents"]} MediaAgents')
                else:
                    log_api_request('GET', '/MediaAgent', response.status_code, duration=duration)
                    errors["mediaagents"] = f"Failed with status {response.status_code}"
                    log_api_activity('error', f'MediaAgents fetch failed: HTTP {response.status_code}')

            elif dtype == "libraries":
                response = requests.get(f"{base_url}/Library", headers=headers, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    results["libraries"] = data
                    counts["libraries"] = save_libraries_to_db(db, data)
                else:
                    errors["libraries"] = f"Failed with status {response.status_code}"

            elif dtype == "storage_pools":
                # FIXED: Use /StoragePool instead of /V4/StoragePool (V4 not available)
                log_api_activity('info', 'Fetching Storage Pools...')
                start_time = time.time()
                response = requests.get(f"{base_url}/StoragePool", headers=headers, timeout=30)
                duration = int((time.time() - start_time) * 1000)
                if response.status_code == 200:
                    data = response.json()
                    results["storage_pools"] = data
                    counts["storage_pools"] = save_storage_pools_to_db(db, data)
                    log_api_request('GET', '/StoragePool', response.status_code, count=counts["storage_pools"], duration=duration)
                    log_api_activity('success', f'Retrieved {counts["storage_pools"]} storage pools')
                else:
                    log_api_request('GET', '/StoragePool', response.status_code, duration=duration)
                    errors["storage_pools"] = f"Failed with status {response.status_code}"
                    log_api_activity('error', f'Storage Pools fetch failed: HTTP {response.status_code}')

            elif dtype == "hypervisors":
                response = requests.get(f"{base_url}/Instance", headers=headers, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    results["hypervisors"] = data
                    counts["hypervisors"] = save_hypervisors_to_db(db, data)
                else:
                    errors["hypervisors"] = f"Failed with status {response.status_code}"

            elif dtype == "storage_arrays":
                # Try V4 endpoint for storage arrays
                response = requests.get(f"{base_url}/V4/Storage/Array", headers=headers, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    results["storage_arrays"] = data
                    counts["storage_arrays"] = save_storage_arrays_to_db(db, data)
                else:
                    errors["storage_arrays"] = f"Failed with status {response.status_code}"

            elif dtype == "events":
                # FIXED: Try /CommServ/Event endpoint (needs testing)
                # Fetch recent critical events (last 7 days by default)
                response = requests.get(f"{base_url}/CommServ/Event?level=Critical", headers=headers, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    results["events"] = data
                    counts["events"] = save_events_to_db(db, data)
                else:
                    # Fallback to old endpoint if new one fails
                    response = requests.get(f"{base_url}/Event?level=Critical", headers=headers, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        results["events"] = data
                        counts["events"] = save_events_to_db(db, data)
                    else:
                        errors["events"] = f"Failed with status {response.status_code}"

            elif dtype == "alerts":
                response = requests.get(f"{base_url}/Alert", headers=headers, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    results["alerts"] = data
                    counts["alerts"] = save_alerts_to_db(db, data)
                else:
                    errors["alerts"] = f"Failed with status {response.status_code}"

            elif dtype == "commcell_info":
                # Fetch CommCell info for health check
                response = requests.get(f"{base_url}/Commcell", headers=headers, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    results["commcell_info"] = data
                    counts["commcell_info"] = save_commcell_info_to_db(db, data)
                else:
                    errors["commcell_info"] = f"Failed with status {response.status_code}"

            elif dtype == "jobs_enhanced":
                # Fetch jobs with enhanced metrics
                response = requests.get(f"{base_url}/Job", headers=headers, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    results["jobs_enhanced"] = data
                    counts["jobs_enhanced"] = save_enhanced_jobs_to_db(db, data)
                    # Also save to regular jobs table
                    save_jobs_to_db(db, data)
                else:
                    errors["jobs_enhanced"] = f"Failed with status {response.status_code}"

        except requests.exceptions.Timeout:
            errors[dtype] = "Request timed out"
        except requests.exceptions.RequestException as e:
            errors[dtype] = f"Request error: {str(e)}"
        except Exception as e:
            errors[dtype] = f"Error: {str(e)}"

    # Commit database changes
    db.commit()

    # Show success message
    if counts:
        success_msg = "Data fetched successfully: " + ", ".join([f"{k}: {v} records" for k, v in counts.items()])
        flash(success_msg, "success")

    if errors:
        error_msg = "Errors occurred: " + ", ".join([f"{k}: {v}" for k, v in errors.items()])
        flash(error_msg, "error")

    return render_template("results.html", results=results, counts=counts, errors=errors)

@app.route("/view/<data_type>")
def view_data(data_type):
    """View stored data from database"""
    db = get_db()
    cur = db.cursor()

    data = []
    columns = []

    if data_type == "clients":
        cur.execute("SELECT * FROM clients ORDER BY clientName")
        columns = ["Client ID", "Client Name", "Hostname", "GUID", "Last Fetch"]
    elif data_type == "jobs":
        cur.execute("SELECT * FROM jobs ORDER BY startTime DESC LIMIT 100")
        columns = ["Job ID", "Client ID", "Client Name", "Job Type", "Status", "Start Time", "End Time", "Backup Set", "Last Fetch"]
    elif data_type == "plans":
        cur.execute("""
            SELECT
                planId,
                planName,
                type,
                numCopies,
                numAssocEntities,
                rpoInMinutes,
                lastFetchTime
            FROM plans
            ORDER BY planName
        """)
        # Convert to list of dictionaries for the custom template
        plan_columns = ['planId', 'planName', 'type', 'numCopies', 'numAssocEntities', 'rpoInMinutes', 'lastFetchTime']
        plans_data = []
        for row in cur.fetchall():
            plans_data.append(dict(zip(plan_columns, row)))
        return render_template("plans.html", data=plans_data)
    elif data_type == "storage":
        cur.execute("SELECT * FROM storage_policies ORDER BY storagePolicyName")
        columns = ["Storage Policy ID", "Storage Policy Name", "Last Fetch"]
    elif data_type == "mediaagents":
        cur.execute("SELECT * FROM mediaagents ORDER BY mediaAgentName")
        columns = ["MediaAgent ID", "MediaAgent Name", "Hostname", "OS Type", "Status", "Available Space", "Total Space", "Last Fetch"]
    elif data_type == "libraries":
        cur.execute("SELECT * FROM libraries ORDER BY libraryName")
        columns = ["Library ID", "Library Name", "Library Type", "MediaAgent", "Status", "Last Fetch"]
    elif data_type == "storage_pools":
        cur.execute("SELECT * FROM storage_pools ORDER BY storagePoolName")
        columns = ["Pool ID", "Pool Name", "Pool Type", "MediaAgent", "Total Capacity", "Free Space", "Dedupe", "Last Fetch"]
    elif data_type == "hypervisors":
        cur.execute("SELECT * FROM hypervisors ORDER BY instanceName")
        columns = ["Instance ID", "Instance Name", "Hypervisor Type", "Hostname", "Vendor", "Status", "Last Fetch"]
    elif data_type == "storage_arrays":
        cur.execute("SELECT * FROM storage_arrays ORDER BY arrayName")
        columns = ["Array ID", "Array Name", "Array Type", "Vendor", "Model", "Total Capacity", "Used Capacity", "Last Fetch"]
    elif data_type == "events":
        cur.execute("SELECT * FROM events ORDER BY timeSource DESC LIMIT 200")
        columns = ["Event ID", "Event Code", "Severity", "Event Type", "Message", "Time", "Subsystem", "Client", "Job ID", "Last Fetch"]
    elif data_type == "alerts":
        cur.execute("SELECT * FROM alerts ORDER BY triggerTime DESC")
        columns = ["Alert ID", "Alert Name", "Alert Type", "Severity", "Status", "Message", "Trigger Time", "Last Fetch"]
    elif data_type == "jobs_enhanced":
        cur.execute("SELECT * FROM jobs_enhanced ORDER BY startTime DESC LIMIT 100")
        columns = ["Job ID", "Client ID", "Client", "Type", "Status", "Start", "End", "Backup Set", "Size (App)", "Size (Disk)", "Savings %", "Throughput MB/s", "Duration", "Files", "Last Fetch"]
    elif data_type == "commcell_info":
        cur.execute("SELECT * FROM commcell_info")
        columns = ["ID", "CommCell Name", "Version", "Time Zone", "Host", "Status", "Last Check"]
    else:
        flash(f"Unknown data type: {data_type}", "error")
        return redirect(url_for('index'))

    data = cur.fetchall()

    return render_template("view.html", data_type=data_type, data=data, columns=columns)

@app.route("/plan/<int:plan_id>")
def view_plan_details(plan_id):
    """View detailed information for a specific plan"""
    db = get_db()
    cur = db.cursor()

    # Get plan details
    cur.execute("""
        SELECT
            planId,
            planName,
            description,
            type,
            subtype,
            numCopies,
            numAssocEntities,
            rpoInMinutes,
            storageTarget,
            storagePolicyId,
            isElastic,
            statusFlag,
            lastFetchTime
        FROM plans
        WHERE planId = ?
    """, (plan_id,))

    plan_row = cur.fetchone()
    if not plan_row:
        flash(f"Plan with ID {plan_id} not found", "error")
        return redirect(url_for('view_data', data_type='plans'))

    # Convert to dictionary
    columns = ['planId', 'planName', 'description', 'type', 'subtype', 'numCopies',
               'numAssocEntities', 'rpoInMinutes', 'storageTarget', 'storagePolicyId',
               'isElastic', 'statusFlag', 'lastFetchTime']
    plan = dict(zip(columns, plan_row))

    # Get retention rules for this plan
    cur.execute("""
        SELECT
            entityName,
            retainBackupDataForDays,
            retainBackupDataForCycles,
            retainArchiverDataForDays,
            enableDataAging,
            jobBasedRetention,
            firstExtendedRetentionDays,
            firstExtendedRetentionCycles,
            secondExtendedRetentionDays,
            secondExtendedRetentionCycles
        FROM retention_rules
        WHERE parentId = ? AND entityType = 'PLAN'
        ORDER BY entityName
    """, (plan_id,))

    retention_columns = ['entityName', 'retainBackupDataForDays', 'retainBackupDataForCycles',
                        'retainArchiverDataForDays', 'enableDataAging', 'jobBasedRetention',
                        'firstExtendedRetentionDays', 'firstExtendedRetentionCycles',
                        'secondExtendedRetentionDays', 'secondExtendedRetentionCycles']
    retention_rules = []
    for row in cur.fetchall():
        retention_rules.append(dict(zip(retention_columns, row)))

    # Get storage policy name if available
    storage_policy_name = None
    if plan.get('storagePolicyId'):
        cur.execute("SELECT storagePolicyName FROM storage_policies WHERE storagePolicyId = ?",
                   (plan['storagePolicyId'],))
        sp_row = cur.fetchone()
        if sp_row:
            storage_policy_name = sp_row[0]

    # Get associated entities count breakdown (if we have the data)
    # For now, we just have the count from the plan record

    return render_template("plan_details.html",
                         plan=plan,
                         retention_rules=retention_rules,
                         storage_policy_name=storage_policy_name)

@app.route("/mediaagents")
def view_mediaagents():
    """View MediaAgents with detailed information panel and selection"""
    db = get_db()
    cur = db.cursor()

    # Get all MediaAgents with selection status
    cur.execute("""
        SELECT
            m.mediaAgentId,
            m.mediaAgentName,
            m.hostName,
            m.osType,
            m.status,
            m.availableSpace,
            m.totalSpace,
            m.lastFetchTime,
            CASE WHEN s.mediaAgentId IS NOT NULL THEN 1 ELSE 0 END as isSelected,
            s.selectedDate,
            s.notes
        FROM mediaagents m
        LEFT JOIN selected_mediaagents s ON m.mediaAgentId = s.mediaAgentId
        ORDER BY isSelected DESC, m.mediaAgentName
    """)

    # Convert to list of dictionaries
    columns = ['mediaAgentId', 'mediaAgentName', 'hostName', 'osType', 'status',
               'availableSpace', 'totalSpace', 'lastFetchTime', 'isSelected',
               'selectedDate', 'notes']
    data = []
    for row in cur.fetchall():
        data.append(dict(zip(columns, row)))

    # Get counts
    cur.execute("SELECT COUNT(*) FROM mediaagents")
    total_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM selected_mediaagents")
    selected_count = cur.fetchone()[0]

    return render_template("mediaagents_selectable.html", data=data,
                         total_count=total_count,
                         selected_count=selected_count)

@app.route("/mediaagents/select/<int:ma_id>", methods=['POST'])
def select_mediaagent(ma_id):
    """Select a MediaAgent for monitoring"""
    db = get_db()
    cur = db.cursor()

    # Get MediaAgent name
    cur.execute("SELECT mediaAgentName FROM mediaagents WHERE mediaAgentId = ?", (ma_id,))
    result = cur.fetchone()

    if result:
        ma_name = result[0]
        # Insert or replace into selected_mediaagents
        cur.execute("""
            INSERT OR REPLACE INTO selected_mediaagents (mediaAgentId, mediaAgentName, selectedDate, notes)
            VALUES (?, ?, ?, ?)
        """, (ma_id, ma_name, datetime.now().isoformat(), "Selected for monitoring"))
        db.commit()
        flash(f"MediaAgent '{ma_name}' selected for monitoring", "success")
    else:
        flash(f"MediaAgent ID {ma_id} not found", "error")

    return redirect(url_for('view_mediaagents'))

@app.route("/mediaagents/deselect/<int:ma_id>", methods=['POST'])
def deselect_mediaagent(ma_id):
    """Deselect a MediaAgent from monitoring"""
    db = get_db()
    cur = db.cursor()

    # Get MediaAgent name before deleting
    cur.execute("SELECT mediaAgentName FROM selected_mediaagents WHERE mediaAgentId = ?", (ma_id,))
    result = cur.fetchone()

    if result:
        ma_name = result[0]
        cur.execute("DELETE FROM selected_mediaagents WHERE mediaAgentId = ?", (ma_id,))
        db.commit()
        flash(f"MediaAgent '{ma_name}' removed from monitoring", "info")
    else:
        flash(f"MediaAgent ID {ma_id} not in selected list", "warning")

    return redirect(url_for('view_mediaagents'))

@app.route("/mediaagents/update-note/<int:ma_id>", methods=['POST'])
def update_mediaagent_note(ma_id):
    """Update notes for a selected MediaAgent"""
    db = get_db()
    cur = db.cursor()

    note = request.form.get('note', '')

    cur.execute("""
        UPDATE selected_mediaagents
        SET notes = ?
        WHERE mediaAgentId = ?
    """, (note, ma_id))
    db.commit()

    flash("Notes updated", "success")
    return redirect(url_for('view_mediaagents'))

@app.route("/dashboard")
def infrastructure_dashboard():
    """Display infrastructure overview dashboard"""
    db = get_db()
    cur = db.cursor()

    # Get counts and summary data
    stats = {}

    # MediaAgents summary
    cur.execute("SELECT COUNT(*) as count FROM mediaagents")
    stats['mediaagents_count'] = cur.fetchone()[0]

    cur.execute("SELECT mediaAgentName, status, availableSpace, totalSpace FROM mediaagents ORDER BY mediaAgentName")
    stats['mediaagents'] = cur.fetchall()

    # Storage Pools summary
    cur.execute("SELECT COUNT(*) as count FROM storage_pools")
    stats['pools_count'] = cur.fetchone()[0]

    cur.execute("SELECT storagePoolName, storagePoolType, totalCapacity, freeSpace, dedupeEnabled FROM storage_pools ORDER BY storagePoolName")
    stats['storage_pools'] = cur.fetchall()

    # Libraries summary
    cur.execute("SELECT COUNT(*) as count FROM libraries")
    stats['libraries_count'] = cur.fetchone()[0]

    cur.execute("SELECT libraryName, libraryType, mediaAgentName, status FROM libraries ORDER BY libraryName")
    stats['libraries'] = cur.fetchall()

    # Hypervisors summary
    cur.execute("SELECT COUNT(*) as count FROM hypervisors")
    stats['hypervisors_count'] = cur.fetchone()[0]

    cur.execute("SELECT instanceName, hypervisorType, vendor, status FROM hypervisors ORDER BY instanceName")
    stats['hypervisors'] = cur.fetchall()

    # Clients summary
    cur.execute("SELECT COUNT(*) as count FROM clients")
    stats['clients_count'] = cur.fetchone()[0]

    # Jobs summary
    cur.execute("SELECT COUNT(*) as count FROM jobs")
    stats['jobs_count'] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) as count FROM jobs WHERE status LIKE '%Completed%'")
    stats['jobs_completed'] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) as count FROM jobs WHERE status LIKE '%Failed%'")
    stats['jobs_failed'] = cur.fetchone()[0]

    # Events and Alerts summary
    cur.execute("SELECT COUNT(*) as count FROM events")
    stats['events_count'] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) as count FROM events WHERE severity = 'Critical'")
    stats['critical_events'] = cur.fetchone()[0]

    cur.execute("SELECT eventCode, severity, message, timeSource, clientName FROM events WHERE severity IN ('Critical', 'Error') ORDER BY timeSource DESC LIMIT 10")
    stats['recent_critical_events'] = cur.fetchall()

    cur.execute("SELECT COUNT(*) as count FROM alerts")
    stats['alerts_count'] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) as count FROM alerts WHERE status = 'Active'")
    stats['active_alerts'] = cur.fetchone()[0]

    # CommCell Health
    cur.execute("SELECT commcellName, commserveVersion, status, lastCheckTime FROM commcell_info LIMIT 1")
    commcell_info = cur.fetchone()
    stats['commcell_info'] = commcell_info if commcell_info else None

    # Enhanced job metrics (if available)
    cur.execute("SELECT COUNT(*) as count FROM jobs_enhanced")
    enhanced_count = cur.fetchone()[0]

    if enhanced_count > 0:
        cur.execute("SELECT AVG(percentSavings) FROM jobs_enhanced WHERE percentSavings > 0")
        avg_savings = cur.fetchone()[0]
        stats['avg_dedupe_savings'] = round(avg_savings, 2) if avg_savings else 0

        cur.execute("SELECT AVG(throughputMBps) FROM jobs_enhanced WHERE throughputMBps > 0")
        avg_throughput = cur.fetchone()[0]
        stats['avg_throughput'] = round(avg_throughput, 2) if avg_throughput else 0
    else:
        stats['avg_dedupe_savings'] = 0
        stats['avg_throughput'] = 0

    return render_template("dashboard.html", stats=stats)

@app.route("/dashboard/retention")
def retention_health_dashboard():
    """Display retention health analytics dashboard"""
    db = get_db()
    cur = db.cursor()

    # Get all retention rules for analysis
    cur.execute("""
        SELECT
            ruleId,
            parentName,
            entityName,
            retainBackupDataForDays,
            retainBackupDataForCycles,
            enableDataAging,
            retainArchiverDataForDays,
            firstExtendedRetentionDays,
            firstExtendedRetentionCycles
        FROM retention_rules
        ORDER BY parentName, entityName
    """)
    retention_rules = cur.fetchall()

    # Initialize counters
    stats = {
        'total_rules': len(retention_rules),
        'aging_disabled': 0,
        'infinite_retention': 0,
        'high_cycles': 0,
        'inefficient_short_term': 0,
        'optimal': 0
    }

    # Problem categories
    aging_disabled_rules = []
    infinite_retention_rules = []
    high_cycle_rules = []
    inefficient_short_rules = []
    optimal_rules = []

    # Analyze each rule
    for rule in retention_rules:
        days = rule['retainBackupDataForDays']
        cycles = rule['retainBackupDataForCycles']
        aging_enabled = rule['enableDataAging']

        rule_dict = dict(rule)

        # Check for issues
        has_issue = False

        if aging_enabled == 0:
            stats['aging_disabled'] += 1
            aging_disabled_rules.append(rule_dict)
            has_issue = True

        if days == -1 or cycles == -1:
            stats['infinite_retention'] += 1
            infinite_retention_rules.append(rule_dict)
            has_issue = True

        if cycles and cycles >= 3 and days and days > 0:
            stats['high_cycles'] += 1
            high_cycle_rules.append(rule_dict)
            has_issue = True

        if days and days <= 30 and cycles and cycles >= 2:
            stats['inefficient_short_term'] += 1
            inefficient_short_rules.append(rule_dict)
            has_issue = True

        if not has_issue:
            stats['optimal'] += 1
            optimal_rules.append(rule_dict)

    # Calculate percentages
    if stats['total_rules'] > 0:
        stats['aging_disabled_pct'] = round((stats['aging_disabled'] / stats['total_rules']) * 100, 1)
        stats['infinite_retention_pct'] = round((stats['infinite_retention'] / stats['total_rules']) * 100, 1)
        stats['high_cycles_pct'] = round((stats['high_cycles'] / stats['total_rules']) * 100, 1)
        stats['inefficient_short_term_pct'] = round((stats['inefficient_short_term'] / stats['total_rules']) * 100, 1)
        stats['optimal_pct'] = round((stats['optimal'] / stats['total_rules']) * 100, 1)
    else:
        stats['aging_disabled_pct'] = 0
        stats['infinite_retention_pct'] = 0
        stats['high_cycles_pct'] = 0
        stats['inefficient_short_term_pct'] = 0
        stats['optimal_pct'] = 0

    # Get plans with issues
    plans_with_issues = {}
    for rule in retention_rules:
        plan_name = rule['parentName']
        if plan_name not in plans_with_issues:
            plans_with_issues[plan_name] = {
                'aging_disabled': False,
                'infinite_retention': False,
                'high_cycles': False,
                'inefficient_short_term': False,
                'issue_count': 0
            }

        days = rule['retainBackupDataForDays']
        cycles = rule['retainBackupDataForCycles']
        aging_enabled = rule['enableDataAging']

        if aging_enabled == 0:
            plans_with_issues[plan_name]['aging_disabled'] = True
            plans_with_issues[plan_name]['issue_count'] += 1

        if days == -1 or cycles == -1:
            plans_with_issues[plan_name]['infinite_retention'] = True
            plans_with_issues[plan_name]['issue_count'] += 1

        if cycles and cycles >= 3 and days and days > 0:
            plans_with_issues[plan_name]['high_cycles'] = True
            plans_with_issues[plan_name]['issue_count'] += 1

        if days and days <= 30 and cycles and cycles >= 2:
            plans_with_issues[plan_name]['inefficient_short_term'] = True
            plans_with_issues[plan_name]['issue_count'] += 1

    # Filter plans with actual issues
    problematic_plans = {k: v for k, v in plans_with_issues.items() if v['issue_count'] > 0}

    # Sort by issue count
    top_problem_plans = sorted(problematic_plans.items(), key=lambda x: x[1]['issue_count'], reverse=True)[:20]

    return render_template("retention_health_dashboard.html",
                         stats=stats,
                         aging_disabled_rules=aging_disabled_rules[:10],
                         infinite_retention_rules=infinite_retention_rules[:10],
                         high_cycle_rules=high_cycle_rules[:10],
                         inefficient_short_rules=inefficient_short_rules[:10],
                         top_problem_plans=top_problem_plans)

@app.route("/dashboard/storage")
def storage_pool_health_dashboard():
    """Display storage pool health analytics dashboard"""
    db = get_db()
    cur = db.cursor()

    # Get all storage pools with capacity information
    cur.execute("""
        SELECT
            storagePoolId,
            storagePoolName,
            storagePoolType,
            mediaAgentName,
            totalCapacity,
            freeSpace,
            dedupeEnabled,
            lastFetchTime
        FROM storage_pools
        ORDER BY storagePoolName
    """)

    storage_pools = [dict(row) for row in cur.fetchall()]

    # Initialize statistics
    stats = {
        'total_pools': len(storage_pools),
        'critical': 0,      # < 10% free
        'warning': 0,       # 10-20% free
        'low': 0,           # 20-30% free
        'ok': 0,            # > 30% free
        'no_data': 0,       # Missing capacity data
        'dedup_pools': 0,
        'non_dedup_pools': 0,
        'total_capacity_tb': 0,
        'total_free_tb': 0,
        'avg_utilization': 0
    }

    # Lists for categorized pools
    critical_pools = []
    warning_pools = []
    low_pools = []
    ok_pools = []

    # Process each pool
    total_capacity_bytes = 0
    total_free_bytes = 0
    pools_with_data = 0

    for pool in storage_pools:
        # Check dedup status
        dedupe_val = str(pool['dedupeEnabled']).lower() if pool['dedupeEnabled'] else ''
        is_dedup = dedupe_val in ['1', 'true', 'yes']
        pool['is_dedup'] = is_dedup

        if is_dedup:
            stats['dedup_pools'] += 1
        else:
            stats['non_dedup_pools'] += 1

        # Calculate capacity metrics
        try:
            total_cap = int(pool['totalCapacity']) if pool['totalCapacity'] else 0
            free_sp = int(pool['freeSpace']) if pool['freeSpace'] else 0

            if total_cap > 0:
                pools_with_data += 1
                total_capacity_bytes += total_cap
                total_free_bytes += free_sp

                # Calculate percentage free
                pct_free = (free_sp * 100.0) / total_cap
                pct_used = 100 - pct_free

                # Convert to TB for display (values are in KB, so divide by 1024^3)
                total_tb = total_cap / (1024**3)
                free_tb = free_sp / (1024**3)
                used_tb = total_tb - free_tb

                pool['totalCapacity_tb'] = round(total_tb, 5)
                pool['freeSpace_tb'] = round(free_tb, 5)
                pool['usedSpace_tb'] = round(used_tb, 5)
                pool['pct_free'] = round(pct_free, 2)
                pool['pct_used'] = round(pct_used, 2)

                # Categorize by health
                if pct_free < 10:
                    stats['critical'] += 1
                    critical_pools.append(pool)
                elif pct_free < 20:
                    stats['warning'] += 1
                    warning_pools.append(pool)
                elif pct_free < 30:
                    stats['low'] += 1
                    low_pools.append(pool)
                else:
                    stats['ok'] += 1
                    ok_pools.append(pool)
            else:
                stats['no_data'] += 1
                pool['pct_free'] = None
                pool['pct_used'] = None

        except (ValueError, TypeError, ZeroDivisionError):
            stats['no_data'] += 1
            pool['pct_free'] = None
            pool['pct_used'] = None

    # Calculate overall statistics (values are in KB, so divide by 1024^3 for TB)
    if total_capacity_bytes > 0:
        stats['total_capacity_tb'] = round(total_capacity_bytes / (1024**3), 5)
        stats['total_free_tb'] = round(total_free_bytes / (1024**3), 5)
        stats['total_used_tb'] = round((total_capacity_bytes - total_free_bytes) / (1024**3), 5)
        stats['avg_utilization'] = round(((total_capacity_bytes - total_free_bytes) * 100.0) / total_capacity_bytes, 2)

    # Calculate percentages for visualization
    if stats['total_pools'] > 0:
        stats['critical_pct'] = round((stats['critical'] * 100.0) / stats['total_pools'], 1)
        stats['warning_pct'] = round((stats['warning'] * 100.0) / stats['total_pools'], 1)
        stats['low_pct'] = round((stats['low'] * 100.0) / stats['total_pools'], 1)
        stats['ok_pct'] = round((stats['ok'] * 100.0) / stats['total_pools'], 1)
    else:
        stats['critical_pct'] = 0
        stats['warning_pct'] = 0
        stats['low_pct'] = 0
        stats['ok_pct'] = 0

    # Sort pools by % used (most full first)
    all_pools_with_data = critical_pools + warning_pools + low_pools + ok_pools
    all_pools_with_data.sort(key=lambda x: x['pct_used'] if x['pct_used'] is not None else 0, reverse=True)
    top_full_pools = all_pools_with_data[:10]

    # Sort critical pools by % free (lowest first)
    critical_pools.sort(key=lambda x: x['pct_free'] if x['pct_free'] is not None else 100)

    return render_template("storage_pool_dashboard.html",
                         stats=stats,
                         critical_pools=critical_pools,
                         warning_pools=warning_pools,
                         top_full_pools=top_full_pools,
                         all_pools=all_pools_with_data)

@app.route("/retention/policies")
def view_retention_policies():
    """View all retention policies (aging policies) grouped by plan/policy"""
    db = get_db()
    cur = db.cursor()

    # Get summary statistics
    stats = {}

    cur.execute("SELECT COUNT(*) as count FROM retention_rules")
    stats['total_rules'] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) as count FROM retention_rules WHERE enableDataAging = 1")
    stats['aging_enabled_count'] = cur.fetchone()[0]

    cur.execute("SELECT AVG(retainBackupDataForDays) FROM retention_rules WHERE retainBackupDataForDays > 0")
    avg_days = cur.fetchone()[0]
    stats['avg_retention_days'] = round(avg_days) if avg_days else 0

    cur.execute("SELECT COUNT(*) as count FROM retention_rules WHERE retainBackupDataForDays = -1 OR retainBackupDataForCycles = -1")
    stats['infinite_retention_count'] = cur.fetchone()[0]

    # Get all retention rules grouped by parent (plan or policy)
    cur.execute("""
        SELECT
            ruleId,
            entityType,
            entityId,
            entityName,
            parentId,
            parentName,
            retainBackupDataForDays,
            retainBackupDataForCycles,
            retainArchiverDataForDays,
            enableDataAging,
            jobBasedRetention,
            firstExtendedRetentionDays,
            firstExtendedRetentionCycles,
            secondExtendedRetentionDays,
            secondExtendedRetentionCycles,
            lastFetchTime
        FROM retention_rules
        ORDER BY parentName, entityName
    """)

    rules = cur.fetchall()

    # Convert to list of dictionaries for easier template access
    columns = ['ruleId', 'entityType', 'entityId', 'entityName', 'parentId', 'parentName',
               'retainBackupDataForDays', 'retainBackupDataForCycles', 'retainArchiverDataForDays',
               'enableDataAging', 'jobBasedRetention', 'firstExtendedRetentionDays',
               'firstExtendedRetentionCycles', 'secondExtendedRetentionDays', 'secondExtendedRetentionCycles',
               'lastFetchTime']

    rules_dicts = []
    for rule in rules:
        rule_dict = {}
        for i, col in enumerate(columns):
            rule_dict[col] = rule[i]
        rules_dicts.append(rule_dict)

    # Group by parent name
    grouped_policies = {}
    for rule in rules_dicts:
        parent = rule['parentName'] or 'Unknown'
        if parent not in grouped_policies:
            grouped_policies[parent] = []
        grouped_policies[parent].append(rule)

    return render_template("retention_policies.html",
                           stats=stats if stats['total_rules'] > 0 else None,
                           grouped_policies=grouped_policies if grouped_policies else None)

@app.route("/retention/details/<int:rule_id>")
def view_retention_policy_details(rule_id):
    """View detailed information for a specific retention rule"""
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT
            ruleId,
            entityType,
            entityId,
            entityName,
            parentId,
            parentName,
            retainBackupDataForDays,
            retainBackupDataForCycles,
            retainArchiverDataForDays,
            enableDataAging,
            jobBasedRetention,
            firstExtendedRetentionDays,
            firstExtendedRetentionCycles,
            secondExtendedRetentionDays,
            secondExtendedRetentionCycles,
            lastFetchTime
        FROM retention_rules
        WHERE ruleId = ?
    """, (rule_id,))

    rule = cur.fetchone()

    if not rule:
        flash(f"Retention rule {rule_id} not found", "error")
        return redirect(url_for('view_retention_policies'))

    # Convert to dictionary
    columns = ['ruleId', 'entityType', 'entityId', 'entityName', 'parentId', 'parentName',
               'retainBackupDataForDays', 'retainBackupDataForCycles', 'retainArchiverDataForDays',
               'enableDataAging', 'jobBasedRetention', 'firstExtendedRetentionDays',
               'firstExtendedRetentionCycles', 'secondExtendedRetentionDays', 'secondExtendedRetentionCycles',
               'lastFetchTime']

    rule_dict = {}
    for i, col in enumerate(columns):
        rule_dict[col] = rule[i]

    # Calculate effective retention
    days = rule_dict['retainBackupDataForDays']
    cycles = rule_dict['retainBackupDataForCycles']

    if days == -1 or cycles == -1:
        effective_retention = "Infinite"
        effective_retention_note = "Data will never be aged out"
    elif days is None and cycles is None:
        effective_retention = "Not Configured"
        effective_retention_note = "No retention settings configured"
    else:
        # Assume average cycle duration of 7 days for calculation
        avg_cycle_duration = 7
        days_retention = days if days and days > 0 else 0
        cycles_retention = (cycles * avg_cycle_duration) if cycles and cycles > 0 else 0
        effective_retention = max(days_retention, cycles_retention)
        effective_retention_note = f"Based on MAX({days_retention} days, {cycles} cycles × {avg_cycle_duration} days avg cycle)"

    rule_dict['effective_retention'] = effective_retention
    rule_dict['effective_retention_note'] = effective_retention_note

    return render_template("retention_policy_details.html", rule=rule_dict)

@app.route("/dashboard/events-alerts")
def events_alerts_dashboard():
    """Display Events & Alerts configuration and monitoring dashboard"""
    db = get_db()
    cur = db.cursor()

    # Get events statistics
    cur.execute("SELECT COUNT(*) as count FROM events")
    total_events = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) as count FROM events WHERE severity = 'Critical'")
    critical_events = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) as count FROM events WHERE severity = 'Error'")
    error_events = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) as count FROM events WHERE severity = 'Warning'")
    warning_events = cur.fetchone()[0]

    # Get alerts statistics
    cur.execute("SELECT COUNT(*) as count FROM alerts")
    total_alerts = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) as count FROM alerts WHERE status = 'Enabled'")
    enabled_alerts = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) as count FROM alerts WHERE status = 'Disabled'")
    disabled_alerts = cur.fetchone()[0]

    # Get recent critical events (storage-related)
    cur.execute("""
        SELECT eventId, eventCode, severity, message, timeSource, clientName, subsystem
        FROM events
        WHERE severity IN ('Critical', 'Error')
        ORDER BY timeSource DESC
        LIMIT 20
    """)
    recent_critical_events = cur.fetchall()

    # Get all alert definitions
    cur.execute("""
        SELECT alertId, alertName, alertType, severity, status, alertMessage
        FROM alerts
        ORDER BY alertName
    """)
    alert_definitions = cur.fetchall()

    # Get critical storage pools for alert recommendations
    cur.execute("""
        SELECT storagePoolId, storagePoolName, totalCapacity, freeSpace
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
                        'pct_free': round(pct_free, 2),
                        'total_gb': round(total / (1024**3), 4),
                        'free_gb': round(free / (1024**3), 4)
                    })
        except:
            continue

    # Recommended alert configurations
    recommended_alerts = [
        {
            'name': 'Storage Pool Critical - Below 10%',
            'type': 'Storage Pool Capacity',
            'severity': 'Critical',
            'threshold': '<10% free space',
            'action': 'Email + SMS to on-call',
            'priority': 'IMMEDIATE',
            'configured': False
        },
        {
            'name': 'Storage Pool Warning - Below 20%',
            'type': 'Storage Pool Capacity',
            'severity': 'Warning',
            'threshold': '<20% free space',
            'action': 'Email to storage team',
            'priority': 'HIGH',
            'configured': False
        },
        {
            'name': 'Storage Pool Info - Below 30%',
            'type': 'Storage Pool Capacity',
            'severity': 'Information',
            'threshold': '<30% free space',
            'action': 'Daily digest email',
            'priority': 'MEDIUM',
            'configured': False
        },
        {
            'name': 'Pruning Job Failed',
            'type': 'Job Failure',
            'severity': 'Critical',
            'threshold': 'Auxiliary Copy job fails',
            'action': 'Email to storage team',
            'priority': 'HIGH',
            'configured': False
        },
        {
            'name': 'Data Aging Failed',
            'type': 'Job Failure',
            'severity': 'Critical',
            'threshold': 'Aging job fails',
            'action': 'Email to backup team',
            'priority': 'HIGH',
            'configured': False
        },
        {
            'name': 'Mount Path Inaccessible',
            'type': 'System Error',
            'severity': 'Critical',
            'threshold': 'Storage mount path error',
            'action': 'Email + Page on-call',
            'priority': 'IMMEDIATE',
            'configured': False
        }
    ]

    # Check which recommended alerts are already configured
    for rec_alert in recommended_alerts:
        for alert in alert_definitions:
            if alert['alertName'] and rec_alert['name'].lower() in alert['alertName'].lower():
                rec_alert['configured'] = True
                break

    # Alert configuration status
    config_status = {
        'events_enabled': total_events > 0,
        'alerts_configured': total_alerts > 0,
        'critical_pools_monitored': False,  # Will check if alerts exist for critical pools
        'pruning_monitoring': False,
        'aging_monitoring': False,
        'email_configured': 'Unknown',  # Would need to check API
        'sms_configured': 'Unknown'
    }

    # Check if critical pools have specific alerts
    if critical_pools and total_alerts > 0:
        config_status['critical_pools_monitored'] = True

    # Statistics
    stats = {
        'total_events': total_events,
        'critical_events': critical_events,
        'error_events': error_events,
        'warning_events': warning_events,
        'total_alerts': total_alerts,
        'enabled_alerts': enabled_alerts,
        'disabled_alerts': disabled_alerts,
        'critical_pools_count': len(critical_pools),
        'config_score': 0
    }

    # Calculate configuration score (0-100)
    score = 0
    if config_status['events_enabled']:
        score += 20
    if config_status['alerts_configured']:
        score += 30
    if enabled_alerts > 0:
        score += 20
    if enabled_alerts >= 5:  # Has multiple alerts configured
        score += 15
    if len(critical_pools) == 0:  # No critical pools
        score += 15

    stats['config_score'] = min(score, 100)

    return render_template("events_alerts_dashboard.html",
                         stats=stats,
                         config_status=config_status,
                         recent_events=recent_critical_events,
                         alert_definitions=alert_definitions,
                         recommended_alerts=recommended_alerts,
                         critical_pools=critical_pools)

@app.route("/dashboard/storage-estate")
def storage_estate_dashboard():
    """Display comprehensive storage estate overview"""
    db = get_db()
    cur = db.cursor()

    # Get all libraries
    cur.execute("""
        SELECT libraryId, libraryName, libraryType, libraryTypeDesc, mediaAgentName,
               status, capacity, freeSpace, usedSpace, usedPercent, vendorType,
               isCloudStorage, isDedupe
        FROM storage_libraries
        ORDER BY libraryTypeDesc, libraryName
    """)

    libraries = []
    for row in cur.fetchall():
        libraries.append({
            'libraryId': row[0],
            'libraryName': row[1],
            'libraryType': row[2],
            'libraryTypeDesc': row[3],
            'mediaAgentName': row[4],
            'status': row[5],
            'capacity': row[6],
            'freeSpace': row[7],
            'usedSpace': row[8],
            'usedPercent': row[9],
            'vendorType': row[10],
            'isCloudStorage': row[11],
            'isDedupe': row[12]
        })

    # Get storage pools
    cur.execute("""
        SELECT storagePoolId, storagePoolName, storagePoolType, mediaAgentName,
               totalCapacity, freeSpace, dedupeEnabled
        FROM storage_pools
        ORDER BY storagePoolName
    """)

    pools = []
    for row in cur.fetchall():
        total_cap = int(row[4]) if row[4] and row[4] != 'None' else 0
        free_sp = int(row[5]) if row[5] and row[5] != 'None' else 0
        used_pct = ((total_cap - free_sp) / total_cap * 100) if total_cap else 0

        pools.append({
            'storagePoolId': row[0],
            'storagePoolName': row[1],
            'storagePoolType': row[2],
            'mediaAgentName': row[3],
            'totalCapacity': total_cap,
            'freeSpace': free_sp,
            'usedPercent': used_pct,
            'dedupeEnabled': row[6]
        })

    # Get pool-to-library mappings
    cur.execute("""
        SELECT plm.storagePoolId, sp.storagePoolName, plm.libraryId, sl.libraryName
        FROM pool_library_mapping plm
        LEFT JOIN storage_pools sp ON plm.storagePoolId = sp.storagePoolId
        LEFT JOIN storage_libraries sl ON plm.libraryId = sl.libraryId
    """)

    pool_library_map = {}
    for row in cur.fetchall():
        pool_library_map[row[0]] = {
            'poolName': row[1],
            'libraryId': row[2],
            'libraryName': row[3]
        }

    # Get write patterns (what writes to what)
    cur.execute("""
        SELECT planId, planName, storagePoolId, storagePoolName,
               libraryId, libraryName, retentionDays
        FROM storage_write_patterns
        ORDER BY planName
    """)

    write_patterns = []
    for row in cur.fetchall():
        write_patterns.append({
            'planId': row[0],
            'planName': row[1],
            'storagePoolId': row[2],
            'storagePoolName': row[3],
            'libraryId': row[4],
            'libraryName': row[5],
            'retentionDays': row[6]
        })

    # Calculate overview statistics
    total_libraries = len(libraries)
    disk_libraries = sum(1 for lib in libraries if lib['libraryTypeDesc'] == 'Disk Library')
    cloud_libraries = sum(1 for lib in libraries if lib['isCloudStorage'])
    dedupe_libraries = sum(1 for lib in libraries if lib['isDedupe'])
    online_libraries = sum(1 for lib in libraries if lib['status'] == 'Online')

    total_capacity_bytes = sum(lib['capacity'] for lib in libraries if lib['capacity'])
    total_free_bytes = sum(lib['freeSpace'] for lib in libraries if lib['freeSpace'])
    total_used_bytes = total_capacity_bytes - total_free_bytes
    overall_used_pct = (total_used_bytes / total_capacity_bytes * 100) if total_capacity_bytes else 0

    total_pools = len(pools)
    critical_pools = sum(1 for pool in pools if pool['usedPercent'] > 80)

    # Group libraries by type
    libraries_by_type = {}
    for lib in libraries:
        lib_type = lib['libraryTypeDesc'] or 'Unknown'
        if lib_type not in libraries_by_type:
            libraries_by_type[lib_type] = []
        libraries_by_type[lib_type].append(lib)

    # Count plans writing to storage
    unique_plans = len(set(wp['planId'] for wp in write_patterns if wp['planId']))
    unique_pools_in_use = len(set(wp['storagePoolId'] for wp in write_patterns if wp['storagePoolId']))

    overview = {
        'total_libraries': total_libraries,
        'disk_libraries': disk_libraries,
        'cloud_libraries': cloud_libraries,
        'dedupe_libraries': dedupe_libraries,
        'online_libraries': online_libraries,
        'offline_libraries': total_libraries - online_libraries,
        'total_capacity_tb': total_capacity_bytes / (1024**4),
        'total_free_tb': total_free_bytes / (1024**4),
        'total_used_tb': total_used_bytes / (1024**4),
        'overall_used_pct': overall_used_pct,
        'total_pools': total_pools,
        'critical_pools': critical_pools,
        'plans_writing_to_storage': unique_plans,
        'pools_in_use': unique_pools_in_use
    }

    return render_template("storage_estate_dashboard.html",
                         overview=overview,
                         libraries=libraries,
                         libraries_by_type=libraries_by_type,
                         pools=pools,
                         pool_library_map=pool_library_map,
                         write_patterns=write_patterns)

@app.route("/dashboard/logs")
def logs_dashboard():
    """Display aging and pruning log analysis"""

    db = get_db()
    cur = db.cursor()

    # Get collection history
    cur.execute("""
        SELECT collectionId, mediaAgentName, collectionTime, logsCollected,
               totalSize, status, errorCount, errorDetails
        FROM log_collection_history
        ORDER BY collectionTime DESC
        LIMIT 10
    """)

    collection_history = []
    for row in cur.fetchall():
        collection_history.append({
            'collectionId': row[0],
            'mediaAgentName': row[1],
            'collectionTime': row[2],
            'logsCollected': row[3],
            'totalSize': row[4],
            'status': row[5],
            'errorCount': row[6],
            'errorDetails': row[7]
        })

    # Get pruning summary by date
    cur.execute("""
        SELECT
            DATE(logDate) as date,
            SUM(CASE WHEN operation = 'Pruning' THEN recordsProcessed ELSE 0 END) as totalPruned,
            SUM(CASE WHEN operation = 'PhysicalDelete' THEN recordsProcessed ELSE 0 END) as totalPhysical,
            SUM(CASE WHEN bytesReclaimed IS NOT NULL THEN bytesReclaimed ELSE 0 END) as totalBytes,
            COUNT(CASE WHEN status = 'Error' THEN 1 END) as errorCount
        FROM aging_pruning_logs
        WHERE logDate >= date('now', '-30 days')
        GROUP BY DATE(logDate)
        ORDER BY date DESC
    """)

    pruning_summary = []
    for row in cur.fetchall():
        pruning_summary.append({
            'date': row[0],
            'totalPruned': row[1] or 0,
            'totalPhysical': row[2] or 0,
            'totalBytes': row[3] or 0,
            'totalGB': (row[3] or 0) / (1024**3),
            'errorCount': row[4]
        })

    # Get recent errors
    cur.execute("""
        SELECT
            logDate,
            logTime,
            mediaAgentName,
            logType,
            operation,
            errorMessage
        FROM aging_pruning_logs
        WHERE status = 'Error'
        ORDER BY logDate DESC, logTime DESC
        LIMIT 50
    """)

    errors = []
    for row in cur.fetchall():
        errors.append({
            'logDate': row[0],
            'logTime': row[1],
            'mediaAgentName': row[2],
            'logType': row[3],
            'operation': row[4],
            'errorMessage': row[5]
        })

    # Get DDB-specific statistics
    cur.execute("""
        SELECT
            ddbStoreId,
            SUM(recordsProcessed) as totalPruned,
            MAX(logDate || ' ' || logTime) as lastPruning,
            COUNT(*) as operationCount
        FROM aging_pruning_logs
        WHERE operation = 'Pruning'
        AND ddbStoreId IS NOT NULL
        GROUP BY ddbStoreId
        ORDER BY totalPruned DESC
    """)

    ddb_stats = []
    for row in cur.fetchall():
        ddb_stats.append({
            'ddbStoreId': row[0],
            'totalPruned': row[1] or 0,
            'lastPruning': row[2],
            'operationCount': row[3]
        })

    # Get overall statistics
    cur.execute("""
        SELECT
            COUNT(*) as totalEntries,
            SUM(CASE WHEN operation = 'Pruning' THEN recordsProcessed ELSE 0 END) as totalPruned,
            SUM(CASE WHEN operation = 'PhysicalDelete' THEN recordsProcessed ELSE 0 END) as totalPhysical,
            SUM(bytesReclaimed) as totalBytes,
            COUNT(CASE WHEN status = 'Error' THEN 1 END) as errorCount
        FROM aging_pruning_logs
    """)

    row = cur.fetchone()
    overall_stats = {
        'totalEntries': row[0] or 0,
        'totalPruned': row[1] or 0,
        'totalPhysical': row[2] or 0,
        'totalBytes': row[3] or 0,
        'totalGB': (row[3] or 0) / (1024**3) if row[3] else 0,
        'totalTB': (row[3] or 0) / (1024**4) if row[3] else 0,
        'errorCount': row[4] or 0
    }

    # Get Mark and Sweep operations
    cur.execute("""
        SELECT
            DATE(logDate) as date,
            COUNT(*) as operations,
            SUM(recordsProcessed) as totalMarked
        FROM aging_pruning_logs
        WHERE operation = 'MarkAndSweep'
        AND logDate >= date('now', '-30 days')
        GROUP BY DATE(logDate)
        ORDER BY date DESC
    """)

    mark_sweep = []
    for row in cur.fetchall():
        mark_sweep.append({
            'date': row[0],
            'operations': row[1],
            'totalMarked': row[2] or 0
        })

    return render_template("logs_dashboard.html",
                         collection_history=collection_history,
                         pruning_summary=pruning_summary,
                         errors=errors,
                         ddb_stats=ddb_stats,
                         overall_stats=overall_stats,
                         mark_sweep=mark_sweep)


@app.route("/logs/collect", methods=['POST'])
def collect_logs():
    """Trigger log collection from MediaAgent via API"""
    # Redirect to the logs dashboard - collection happens via SSE
    return redirect(url_for('logs_dashboard'))


@app.route("/logs/collect/stream")
def collect_logs_stream():
    """Server-Sent Events stream for real-time log collection progress"""

    def generate():
        import configparser

        try:
            # Send initial status
            yield f"data: {json.dumps({'status': 'starting', 'message': 'Initializing log collection...'})}\n\n"

            # Load configuration
            config = configparser.ConfigParser()

            # Check if config.ini exists
            if not os.path.exists('config.ini'):
                yield f"data: {json.dumps({'status': 'error', 'message': 'config.ini not found. Please create config.ini from config.ini.example with your Commvault API credentials.'})}\n\n"
                return

            config.read('config.ini')

            # Validate required settings
            if not config.has_section('commvault'):
                yield f"data: {json.dumps({'status': 'error', 'message': 'config.ini missing [commvault] section. Please check config.ini.example for correct format.'})}\n\n"
                return

            media_agent = config.get('commvault', 'media_agent', fallback='cvhsxman01.jhb.seagatestoragecloud.co.za')

            # Get UNC path from config
            if not config.has_section('collection'):
                yield f"data: {json.dumps({'status': 'error', 'message': 'config.ini missing [collection] section'})}\n\n"
                return

            unc_path = config.get('collection', 'unc_path', fallback=f'\\\\{media_agent}\\C$\\Program Files\\Commvault\\ContentStore\\Log Files')

            yield f"data: {json.dumps({'status': 'progress', 'message': f'Connecting to {media_agent}...', 'percent': 10})}\n\n"

            # Define log files to collect
            log_files = [
                "SIDBPrune.log",
                "SIDBEngine.log",
                "SIDBPhysicalDeletes.log",
                "DataAging.log",
                "MediaManagerPrune.log",
                "CVMA.log",
                "cvd.log",
                "clBackup.log"
            ]

            total_files = len(log_files)
            collected = []
            errors = []

            # Ensure Logs directory exists
            os.makedirs('Logs', exist_ok=True)

            # Use UNC path to copy files directly
            import shutil
            from datetime import datetime

            for i, log_file in enumerate(log_files):
                percent = 10 + int((i / total_files) * 85)
                yield f"data: {json.dumps({'status': 'progress', 'message': f'Copying {log_file}...', 'percent': percent, 'current': i+1, 'total': total_files})}\n\n"

                source_path = os.path.join(unc_path, log_file)
                local_path = os.path.join('Logs', log_file)

                try:
                    if os.path.exists(source_path):
                        shutil.copy2(source_path, local_path)
                        size = os.path.getsize(local_path)
                        collected.append({'file': log_file, 'size': size})
                        yield f"data: {json.dumps({'status': 'progress', 'message': f'Copied {log_file} ({size:,} bytes)', 'percent': percent})}\n\n"
                    else:
                        errors.append({'file': log_file, 'error': 'File not found'})
                        yield f"data: {json.dumps({'status': 'warning', 'message': f'Skipped {log_file} (not found)'})}\n\n"

                except PermissionError as e:
                    errors.append({'file': log_file, 'error': f'Permission denied: {e}'})
                    yield f"data: {json.dumps({'status': 'warning', 'message': f'Permission denied: {log_file}'})}\n\n"
                except Exception as e:
                    errors.append({'file': log_file, 'error': str(e)})
                    yield f"data: {json.dumps({'status': 'warning', 'message': f'Failed to copy {log_file}: {str(e)}'})}\n\n"

            # Finalizing
            yield f"data: {json.dumps({'status': 'progress', 'message': 'Finalizing...', 'percent': 95})}\n\n"

            # Store collection history in database if logs were collected
            if len(collected) > 0:
                import sqlite3
                try:
                    db = sqlite3.connect(config.get('database', 'path', fallback='Database/commvault.db'))
                    cur = db.cursor()

                    timestamp = datetime.now().isoformat()
                    for log_info in collected:
                        cur.execute("""
                            INSERT INTO collectionHistory (timestamp, fileName, fileSize, collectionMethod)
                            VALUES (?, ?, ?, 'UNC')
                        """, (timestamp, log_info['file'], log_info['size']))

                    db.commit()
                    db.close()
                except Exception as e:
                    yield f"data: {json.dumps({'status': 'warning', 'message': f'Warning: Failed to store collection history: {str(e)}'})}\n\n"

            # Complete
            if len(collected) > 0:
                yield f"data: {json.dumps({'status': 'complete', 'message': f'Successfully collected {len(collected)} of {total_files} logs', 'collected': len(collected), 'errors': len(errors), 'percent': 100})}\n\n"
            else:
                yield f"data: {json.dumps({'status': 'error', 'message': f'Failed to collect logs. {len(errors)} errors occurred.', 'errors': len(errors)})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': f'Error: {str(e)}'})}\n\n"

    return Response(generate(), mimetype='text/event-stream')


@app.route("/logs/parse", methods=['POST'])
def parse_logs():
    """Trigger log parsing"""

    import subprocess

    try:
        # Run log parsing script
        result = subprocess.run(
            ['python', 'parse_aging_logs.py'],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            flash('Log parsing completed successfully', 'success')
        else:
            flash(f'Log parsing failed: {result.stderr}', 'error')

    except subprocess.TimeoutExpired:
        flash('Log parsing timed out', 'error')
    except Exception as e:
        flash(f'Error parsing logs: {e}', 'error')

    return redirect(url_for('logs_dashboard'))


@app.route("/aging/report")
def aging_report():
    """Display aging and pruning report"""
    from aging_tracker import AgingPruningTracker
    import configparser

    try:
        # Load config directly
        config = configparser.ConfigParser()
        config.read('config.ini')

        base_url = config.get('commvault', 'webservice_url')
        username = config.get('commvault', 'username')
        password = config.get('commvault', 'password')

        if not all([base_url, username, password]):
            flash('Please configure Commvault credentials in config.ini', 'error')
            return redirect(url_for('index'))

        # Authenticate
        token = authenticate_commvault(base_url, username, password)

        if not token:
            flash('Authentication failed', 'error')
            return redirect(url_for('index'))

        # Get aging status
        tracker = AgingPruningTracker(base_url, token)
        status = tracker.get_aging_status(days_back=7)
        trending = tracker.get_aging_trending_data(days_back=30)

        return render_template('aging_report.html',
                             status=status,
                             trending=trending)

    except Exception as e:
        flash(f'Error generating aging report: {str(e)}', 'error')
        return redirect(url_for('logs_dashboard'))


@app.route("/aging/check/stream")
def aging_check_stream():
    """Server-Sent Events stream for real-time aging status check"""

    def generate():
        import configparser
        from aging_tracker import AgingPruningTracker

        try:
            yield f"data: {json.dumps({'status': 'starting', 'message': 'Checking aging status...', 'percent': 0})}\n\n"

            # Load config
            config = configparser.ConfigParser()
            config.read('config.ini')

            base_url = config.get('commvault', 'webservice_url')
            username = config.get('commvault', 'username')
            password = config.get('commvault', 'password')

            yield f"data: {json.dumps({'status': 'progress', 'message': 'Authenticating...', 'percent': 10})}\n\n"

            token = authenticate_commvault(base_url, username, password)

            if not token:
                yield f"data: {json.dumps({'status': 'error', 'message': 'Authentication failed'})}\n\n"
                return

            yield f"data: {json.dumps({'status': 'progress', 'message': 'Fetching retention policies...', 'percent': 30})}\n\n"

            tracker = AgingPruningTracker(base_url, token)
            status = tracker.get_aging_status(days_back=7)

            yield f"data: {json.dumps({'status': 'progress', 'message': 'Analyzing job history...', 'percent': 60})}\n\n"

            # Send results
            summary = status['summary']

            msg1 = f'Found {summary["total_ddbs"]} DDB stores'
            msg2 = f'Found {summary["total_aux_copy_jobs"]} aux copy jobs'

            yield f"data: {json.dumps({'status': 'progress', 'message': msg1, 'percent': 80})}\n\n"
            yield f"data: {json.dumps({'status': 'progress', 'message': msg2, 'percent': 90})}\n\n"

            yield f"data: {json.dumps({'status': 'complete', 'message': 'Aging check complete', 'percent': 100, 'summary': summary})}\n\n"

        except Exception as e:
            error_msg = f'Error: {str(e)}'
            yield f"data: {json.dumps({'status': 'error', 'message': error_msg})}\n\n"

    return Response(generate(), mimetype='text/event-stream')


@app.route("/api/config")
def api_config():
    """API Configuration and Endpoint Status Page"""
    try:
        # Load configuration
        config = configparser.ConfigParser()
        config.read('config.ini')

        base_url = config.get('commvault', 'webservice_url')
        username = config.get('commvault', 'username')
        password = config.get('commvault', 'password')
        media_agent = config.get('commvault', 'media_agent', fallback='Not configured')
        verify_ssl = config.get('api', 'verify_ssl', fallback='false').lower() == 'true'
        timeout = config.get('api', 'timeout', fallback='300')

        # Mask password for display
        password_masked = password[:10] + '...' if len(password) > 10 else '***'

        # Test authentication
        auth_status = {
            'success': False,
            'error': None,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        token = None
        try:
            response = requests.post(
                f'{base_url}/Login',
                json={'username': username, 'password': password},
                headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
                timeout=30,
                verify=verify_ssl
            )

            if response.status_code == 200:
                data = response.json()
                if 'token' in data and data['token']:
                    token = data['token']
                    if token.startswith('QSDK '):
                        token = token[5:]
                    auth_status['success'] = True
                else:
                    auth_status['error'] = 'No token received'
                    if 'errList' in data:
                        auth_status['error'] = data['errList'][0].get('errLogMessage', 'Unknown error')
            else:
                auth_status['error'] = f'HTTP {response.status_code}'
        except Exception as e:
            auth_status['error'] = str(e)[:100]

        # Define endpoints to test
        endpoint_list = [
            '/Client',
            '/StoragePolicy',
            '/MediaAgent',
            '/StoragePool',
            '/Job',
            '/Subclient',
            '/Agent',
            '/BackupSet',
            '/Instance',
            '/Schedule',
            '/Library',
            '/CommCell',
            '/AlertRule',
            '/V2/Client',
            '/V2/StoragePolicy',
            '/V2/MediaAgent',
            '/V2/StoragePool',
            '/V4/ServerInfo',
            '/DDB',
            '/Retention',
        ]

        # Test each endpoint
        endpoints = []
        for endpoint_path in endpoint_list:
            endpoint_info = {
                'path': endpoint_path,
                'status': None,
                'message': '',
                'has_data': False,
                'count': 0,
                'sample_data': None
            }

            if not token:
                endpoint_info['status'] = 'N/A'
                endpoint_info['message'] = 'No authentication token'
                endpoints.append(endpoint_info)
                continue

            try:
                headers = {'Authtoken': f'QSDK {token}', 'Accept': 'application/json'}
                r = requests.get(
                    f'{base_url}{endpoint_path}',
                    headers=headers,
                    timeout=10,
                    verify=verify_ssl
                )

                endpoint_info['status'] = r.status_code

                if r.status_code == 200:
                    try:
                        data = r.json()

                        # Check if data is available
                        if isinstance(data, list):
                            endpoint_info['has_data'] = len(data) > 0
                            endpoint_info['count'] = len(data)
                            endpoint_info['message'] = f'List with {len(data)} items'
                            if len(data) > 0:
                                endpoint_info['sample_data'] = json.dumps(data[0], indent=2)[:500]
                        elif isinstance(data, dict):
                            # Check common data keys
                            data_keys = ['clients', 'policies', 'mediaAgents', 'jobs', 'storagePools']
                            for key in data_keys:
                                if key in data:
                                    count = len(data[key]) if isinstance(data[key], list) else 1
                                    endpoint_info['has_data'] = count > 0
                                    endpoint_info['count'] = count
                                    endpoint_info['message'] = f'Dict with {count} {key}'
                                    if count > 0:
                                        sample = data[key][0] if isinstance(data[key], list) else data[key]
                                        endpoint_info['sample_data'] = json.dumps(sample, indent=2)[:500]
                                    break

                            if not endpoint_info['has_data']:
                                endpoint_info['message'] = f'Dict with keys: {", ".join(list(data.keys())[:5])}'
                                endpoint_info['sample_data'] = json.dumps(data, indent=2)[:500]
                        else:
                            endpoint_info['message'] = f'Response type: {type(data).__name__}'
                    except:
                        endpoint_info['message'] = f'Non-JSON response ({len(r.text)} bytes)'
                elif r.status_code == 401:
                    endpoint_info['message'] = 'Unauthorized - Check permissions'
                elif r.status_code == 404:
                    endpoint_info['message'] = 'Endpoint not found'
                else:
                    endpoint_info['message'] = r.text[:100]

            except requests.exceptions.Timeout:
                endpoint_info['status'] = 'Timeout'
                endpoint_info['message'] = 'Request timed out (10s)'
            except Exception as e:
                endpoint_info['status'] = 'Error'
                endpoint_info['message'] = str(e)[:100]

            endpoints.append(endpoint_info)

        # Calculate summary statistics
        success_count = sum(1 for e in endpoints if e['status'] == 200)
        failed_count = sum(1 for e in endpoints if e['status'] and e['status'] not in [200, 'N/A'])
        data_count = sum(1 for e in endpoints if e['has_data'])

        summary = {
            'success_count': success_count,
            'failed_count': failed_count,
            'data_count': data_count
        }

        # Prepare template data
        config_data = {
            'base_url': base_url,
            'username': username,
            'password_masked': password_masked,
            'media_agent': media_agent,
            'verify_ssl': verify_ssl,
            'timeout': timeout
        }

        return render_template(
            'api_config.html',
            config=config_data,
            auth_status=auth_status,
            endpoints=endpoints,
            summary=summary,
            test_timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

    except Exception as e:
        return f"Error loading API configuration: {str(e)}", 500


if __name__ == "__main__":
    # Initialize database on first run
    init_db()

    # Run Flask development server
    app.run(debug=True, host='0.0.0.0', port=5000)
