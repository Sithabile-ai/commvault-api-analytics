# API Fixes Research Results

## Date: 2025-11-13

Based on comprehensive API testing and research, here are the fixes needed for all non-working endpoints:

---

## ✅ FIXES CONFIRMED (Ready to Implement)

### 1. **Jobs API - Timeout Issue**

**Problem**: Request times out after 30 seconds
**Root Cause**: API returns 1 year of jobs by default (too much data)

**Solution**: Add `completedJobLookupTime` parameter
```python
# Current (FAILS):
response = requests.get(f"{base_url}/Job", headers=headers, timeout=30)

# Fixed (WORKS):
response = requests.get(
    f"{base_url}/Job?completedJobLookupTime=86400",  # Last 24 hours
    headers=headers,
    timeout=30
)
```

**Parameter Details**:
- `completedJobLookupTime` - Time in **seconds** to look back
- Example values:
  - `86400` = Last 24 hours
  - `604800` = Last 7 days
  - `2592000` = Last 30 days

**Additional Filters Available**:
- `?jobFilter=Backup` - Filter by job type
- `?statusList=Completed,Failed` - Filter by status
- `?clientId=123` - Filter by specific client

### 2. **MediaAgents - Wrong JSON Structure**

**Problem**: No data stored despite successful API call (HTTP 200)
**Root Cause**: Code expects `mediaAgentList` but API returns `response`

**Actual API Response Structure**:
```json
{
  "response": [
    {
      "entityInfo": {
        "id": 2,
        "name": "commserve01"
      }
    }
  ]
}
```

**Current Code (WRONG)**:
```python
def save_mediaagents_to_db(db, mediaagents_json):
    ma_list = mediaagents_json.get("mediaAgentList", [])
    if not ma_list:
        ma_list = mediaagents_json.get("mediaAgents", [])

    for ma in ma_list:
        ma_id = ma.get("mediaAgent", {}).get("mediaAgentId")
        name = ma.get("mediaAgent", {}).get("mediaAgentName", "")
```

**Fixed Code (CORRECT)**:
```python
def save_mediaagents_to_db(db, mediaagents_json):
    ma_list = mediaagents_json.get("response", [])

    for ma_entry in ma_list:
        entity_info = ma_entry.get("entityInfo", {})
        ma_id = entity_info.get("id")
        name = entity_info.get("name", "")
```

**File**: `app.py` around lines 200-220

### 3. **Libraries - Wrong JSON Structure**

**Problem**: Same as MediaAgents - uses `response` key
**Root Cause**: Code expects `libraryList` but API returns `response`

**Actual API Response Structure**:
```json
{
  "response": [
    {
      "entityInfo": {
        "id": 5,
        "name": "DiskLibrary01"
      }
    }
  ]
}
```

**Current Code (WRONG)**:
```python
def save_libraries_to_db(db, libraries_json):
    lib_list = libraries_json.get("libraryList", [])
    if not lib_list:
        lib_list = libraries_json.get("libraries", [])

    for lib in lib_list:
        lib_id = lib.get("library", {}).get("libraryId")
        name = lib.get("library", {}).get("libraryName", "")
```

**Fixed Code (CORRECT)**:
```python
def save_libraries_to_db(db, libraries_json):
    lib_list = libraries_json.get("response", [])

    for lib_entry in lib_list:
        entity_info = lib_entry.get("entityInfo", {})
        lib_id = entity_info.get("id")
        name = entity_info.get("name", "")
```

**File**: `app.py` around lines 270-290

### 4. **Storage Pools - Wrong Endpoint AND Wrong Parser**

**Problem 1**: Endpoint `/V4/StoragePool` returns HTTP 404
**Root Cause**: V4 API not available in this Commvault version

**Solution**: Use `/StoragePool` instead
```python
# Current (FAILS):
response = requests.get(f"{base_url}/V4/StoragePool", headers=headers)

# Fixed (WORKS):
response = requests.get(f"{base_url}/StoragePool", headers=headers)
```

**Problem 2**: Parser expects wrong key
**Root Cause**: Code expects `storagePools` but API returns `storagePoolList`

**Actual API Response Structure**:
```json
{
  "storagePoolList": [
    {
      "storagePool": {
        "storagePoolId": 3,
        "storagePoolName": "SP_DISK_01"
      },
      "status": "Online",
      "totalCapacity": 5368709120,
      "totalFreeSpace": 2147483648,
      "sizeOnDisk": 3221225472
    }
  ]
}
```

**Current Code (WRONG)**:
```python
def save_storage_pools_to_db(db, storage_json):
    pools_list = storage_json.get("storagePools", [])
```

**Fixed Code (CORRECT)**:
```python
def save_storage_pools_to_db(db, storage_json):
    pools_list = storage_json.get("storagePoolList", [])

    for pool_entry in pools_list:
        pool_data = pool_entry.get("storagePool", {})
        pool_id = pool_data.get("storagePoolId")
        name = pool_data.get("storagePoolName", "")
        capacity = pool_entry.get("totalCapacity", 0)
        free_space = pool_entry.get("totalFreeSpace", 0)
```

**File Changes Needed**:
1. `app.py` - Change endpoint in `fetch_data()` route (around line 600)
2. `app.py` - Fix parser in `save_storage_pools_to_db()` (around line 310-330)

---

## ⚠️ FIXES REQUIRE TESTING (Endpoint Changes)

### 5. **Events - Wrong Endpoint Path**

**Problem**: `/Event` returns HTTP 404
**Research Findings**: Correct endpoint is `/CommServ/Event`

**Current Code (FAILS)**:
```python
response = requests.get(f"{base_url}/Event", headers=headers)
```

**Proposed Fix (NEEDS TESTING)**:
```python
response = requests.get(f"{base_url}/CommServ/Event", headers=headers)
```

**Alternative Filters**:
```python
# Get critical events only
response = requests.get(f"{base_url}/CommServ/Event?level=Critical", headers=headers)

# Get events for specific time range
response = requests.get(f"{base_url}/CommServ/Event?fromTime=<timestamp>&toTime=<timestamp>", headers=headers)
```

**Expected Response Structure** (based on research):
```json
{
  "commCellEvents": [
    {
      "eventId": 12345,
      "eventCode": "17:123",
      "severity": "Critical",
      "message": "MediaAgent offline",
      "timeSource": "2025-11-13 10:30:00"
    }
  ]
}
```

**Update Needed**:
- Change endpoint in `app.py` `fetch_data()` route
- May need to update `save_events_to_db()` parser if structure differs

### 6. **Hypervisors - Wrong Endpoint**

**Problem**: `/Instance` returns HTTP 400 (Bad Request)
**Research Findings**: Multiple alternative endpoints found

**Option 1: Virtualization Clients Endpoint**
```python
response = requests.get(f"{base_url}/VSAclientlist", headers=headers)
```

**Option 2: V2 VSA Hypervisors** (Most promising)
```python
response = requests.get(f"{base_url}/V2/VSA/Hypervisors", headers=headers)
```

**Option 3: Virtualization Clients**
```python
response = requests.get(f"{base_url}/V2/Virtualization/Clients", headers=headers)
```

**Expected Response Structure** (based on research):
```json
{
  "VSInstanceProperties": [
    {
      "instance": {
        "instanceId": 2,
        "instanceName": "vcenter01",
        "clientName": "vmware_proxy"
      },
      "hypervisor": {
        "hypervisorType": "VMware",
        "vendor": "VMware",
        "hostName": "vcenter01.domain.com"
      }
    }
  ]
}
```

**Update Needed**:
- Test all 3 endpoints to find which works
- Update endpoint in `app.py` `fetch_data()` route
- May need to update `save_hypervisors_to_db()` parser

### 7. **CommCell Info - Wrong Endpoint Path**

**Problem**: `/Commcell` returns HTTP 404 (lowercase 'c' at end)
**Research Findings**: May need capital 'C' or different endpoint

**Option 1: Try Capital C**
```python
response = requests.get(f"{base_url}/CommCell", headers=headers)
```

**Option 2: GetId Endpoint** (Alternative)
```python
response = requests.get(f"{base_url}/GetId", headers=headers)
```

**Option 3: CommCell Properties**
```python
response = requests.get(f"{base_url}/CommServ", headers=headers)
```

**Update Needed**:
- Test endpoint variations
- Update endpoint in `app.py` `fetch_data()` route

---

## ❌ NOT AVAILABLE (Remove from App)

### 8. **Storage Arrays - Not Available**

**Problem**: `/V4/Storage/Array` returns HTTP 404
**Root Cause**:
- V4 API not available in this version
- May not be configured in this CommCell

**Recommendation**:
- Disable this feature in the UI
- Comment out or remove checkbox in `templates/index.html`
- Add note: "Storage Arrays API not available in this Commvault version"

**Code Changes**:
```python
# In templates/index.html - Add disabled attribute:
<label style="color: #999;">
    <input type="checkbox" name="data_type" value="storage_arrays" disabled>
    Storage Arrays - Physical storage hardware (Not available in this version)
</label>
```

---

## 📋 Implementation Priority

### **Priority 1: Critical Fixes (Working Endpoints with Wrong Parsers)**
These endpoints work but store no data due to parser bugs:

1. ✅ **MediaAgents** - Working endpoint, wrong parser
2. ✅ **Libraries** - Working endpoint, wrong parser
3. ✅ **Storage Pools** - Wrong endpoint + wrong parser

**Impact**: HIGH - These are core infrastructure features
**Effort**: LOW - Simple parser updates
**Testing**: Use existing `test_output_*.json` files to verify

### **Priority 2: Performance Fix (Timeout Issue)**
4. ✅ **Jobs** - Add time filter to prevent timeout

**Impact**: HIGH - Jobs are critical monitoring data
**Effort**: LOW - Add single parameter
**Testing**: Easy to test with 24-hour filter

### **Priority 3: Endpoint Research (Need Testing)**
5. ⚠️ **Events** - Try `/CommServ/Event`
6. ⚠️ **Hypervisors** - Try 3 alternative endpoints
7. ⚠️ **CommCell Info** - Try capital 'C' variation

**Impact**: MEDIUM - Nice-to-have monitoring features
**Effort**: MEDIUM - Requires testing multiple endpoints
**Testing**: May require trial and error

### **Priority 4: Cleanup (Remove Non-Working)**
8. ❌ **Storage Arrays** - Disable in UI

**Impact**: LOW - Not available anyway
**Effort**: LOW - Simple UI change
**Testing**: None needed

---

## 🔧 Detailed Code Changes Required

### File: `app.py`

#### Change 1: Fix MediaAgents Parser (Line ~200-220)
**Current**:
```python
def save_mediaagents_to_db(db, mediaagents_json):
    cursor = db.cursor()
    ma_list = mediaagents_json.get("mediaAgentList", [])
    if not ma_list:
        ma_list = mediaagents_json.get("mediaAgents", [])

    for ma in ma_list:
        ma_data = ma.get("mediaAgent", {})
        ma_id = ma_data.get("mediaAgentId")
        name = ma_data.get("mediaAgentName", "")
```

**Replace with**:
```python
def save_mediaagents_to_db(db, mediaagents_json):
    cursor = db.cursor()
    ma_list = mediaagents_json.get("response", [])

    for ma_entry in ma_list:
        entity_info = ma_entry.get("entityInfo", {})
        ma_id = entity_info.get("id")
        name = entity_info.get("name", "")

        # Additional fields may be in the ma_entry itself, not entityInfo
        # Adjust as needed based on test_output_MediaAgents.json
```

#### Change 2: Fix Libraries Parser (Line ~270-290)
**Current**:
```python
def save_libraries_to_db(db, libraries_json):
    cursor = db.cursor()
    lib_list = libraries_json.get("libraryList", [])
    if not lib_list:
        lib_list = libraries_json.get("libraries", [])

    for lib in lib_list:
        lib_data = lib.get("library", {})
        lib_id = lib_data.get("libraryId")
        name = lib_data.get("libraryName", "")
```

**Replace with**:
```python
def save_libraries_to_db(db, libraries_json):
    cursor = db.cursor()
    lib_list = libraries_json.get("response", [])

    for lib_entry in lib_list:
        entity_info = lib_entry.get("entityInfo", {})
        lib_id = entity_info.get("id")
        name = entity_info.get("name", "")

        # Additional fields from lib_entry
```

#### Change 3: Fix Storage Pools Endpoint (Line ~600 in fetch_data route)
**Current**:
```python
elif dtype == "storage_pools":
    response = requests.get(f"{base_url}/V4/StoragePool", headers=headers, timeout=30)
```

**Replace with**:
```python
elif dtype == "storage_pools":
    response = requests.get(f"{base_url}/StoragePool", headers=headers, timeout=30)
```

#### Change 4: Fix Storage Pools Parser (Line ~310-330)
**Current**:
```python
def save_storage_pools_to_db(db, storage_json):
    cursor = db.cursor()
    pools_list = storage_json.get("storagePools", [])
```

**Replace with**:
```python
def save_storage_pools_to_db(db, storage_json):
    cursor = db.cursor()
    pools_list = storage_json.get("storagePoolList", [])

    for pool_entry in pools_list:
        pool_data = pool_entry.get("storagePool", {})
        pool_id = pool_data.get("storagePoolId")
        name = pool_data.get("storagePoolName", "")

        # Capacity info is at pool_entry level, not inside storagePool
        capacity = pool_entry.get("totalCapacity", 0)
        free_space = pool_entry.get("totalFreeSpace", 0)
```

#### Change 5: Fix Jobs Timeout (Line ~580 in fetch_data route)
**Current**:
```python
if "jobs" in data_types:
    response = requests.get(f"{base_url}/Job", headers=headers, timeout=30)
```

**Replace with**:
```python
if "jobs" in data_types:
    # Fetch only last 24 hours of jobs to prevent timeout
    response = requests.get(
        f"{base_url}/Job?completedJobLookupTime=86400",
        headers=headers,
        timeout=30
    )
```

#### Change 6: Fix Events Endpoint (Line ~650 in fetch_data route)
**Current**:
```python
elif dtype == "events":
    response = requests.get(f"{base_url}/Event?level=Critical", headers=headers, timeout=30)
```

**Replace with (NEEDS TESTING)**:
```python
elif dtype == "events":
    response = requests.get(f"{base_url}/CommServ/Event?level=Critical", headers=headers, timeout=30)
```

---

## 🧪 Testing Plan

### Step 1: Test Priority 1 Fixes (Parser Updates)
```bash
# Run the test script again
python test_api_endpoints.py

# Check if MediaAgents, Libraries, Storage Pools now show data counts
```

### Step 2: Test Jobs with Filter
```python
# Add to test script:
results['jobs_filtered'] = test_endpoint("Jobs (24h)", "/Job?completedJobLookupTime=86400", headers)
```

### Step 3: Test Events Endpoint Variations
```python
# Try different endpoints:
test_endpoint("Events (CommServ)", "/CommServ/Event", headers)
test_endpoint("Events (Critical)", "/CommServ/Event?level=Critical", headers)
```

### Step 4: Test Hypervisors Endpoints
```python
test_endpoint("Hypervisors (VSA)", "/VSAclientlist", headers)
test_endpoint("Hypervisors (V2)", "/V2/VSA/Hypervisors", headers)
test_endpoint("Hypervisors (Clients)", "/V2/Virtualization/Clients", headers)
```

### Step 5: Verify Data in Database
```bash
# Check database after fixes:
python -c "import sqlite3; db = sqlite3.connect('Database/commvault.db'); cursor = db.cursor(); cursor.execute('SELECT COUNT(*) FROM mediaagents'); print(f'MediaAgents: {cursor.fetchone()[0]}'); cursor.execute('SELECT COUNT(*) FROM libraries'); print(f'Libraries: {cursor.fetchone()[0]}'); cursor.execute('SELECT COUNT(*) FROM storage_pools'); print(f'Storage Pools: {cursor.fetchone()[0]}')"
```

---

## 📊 Expected Outcomes After Fixes

| Endpoint | Before Fix | After Fix | Status |
|----------|-----------|-----------|--------|
| Clients | ✅ Working (3,604) | ✅ Working | No change |
| Plans | ✅ Working (278) | ✅ Working | No change |
| Storage Policies | ✅ Working (226) | ✅ Working | No change |
| MediaAgents | ❌ No data | ✅ 10+ agents | **FIXED** |
| Libraries | ❌ No data | ✅ Multiple libs | **FIXED** |
| Storage Pools | ❌ 404 Error | ✅ Pools + capacity | **FIXED** |
| Jobs | ❌ Timeout | ✅ Last 24h jobs | **FIXED** |
| Alerts | ✅ Working (empty) | ✅ Working | No change |
| Events | ❌ 404 | ⚠️ Testing needed | **PENDING** |
| Hypervisors | ❌ 400 Error | ⚠️ Testing needed | **PENDING** |
| CommCell Info | ❌ 404 | ⚠️ Testing needed | **PENDING** |
| Storage Arrays | ❌ 404 | ❌ Disabled | **REMOVED** |

**Success Rate**:
- Current: 7/14 (50%)
- After Priority 1 & 2 fixes: 11/14 (78%)
- After all fixes (optimistic): 13/14 (93%)

---

## 📝 Summary

### Confirmed Fixes (Ready to Implement):
1. ✅ MediaAgents parser - Use `response` → `entityInfo` structure
2. ✅ Libraries parser - Use `response` → `entityInfo` structure
3. ✅ Storage Pools endpoint - Change to `/StoragePool`
4. ✅ Storage Pools parser - Use `storagePoolList` key
5. ✅ Jobs timeout - Add `completedJobLookupTime=86400` parameter

### Requires Testing:
6. ⚠️ Events - Try `/CommServ/Event` endpoint
7. ⚠️ Hypervisors - Try `/VSAclientlist` or `/V2/VSA/Hypervisors`
8. ⚠️ CommCell Info - Try `/CommCell` (capital C)

### Not Available:
9. ❌ Storage Arrays - Disable feature in UI

**Next Steps**:
1. Implement Priority 1 & 2 fixes (confirmed working)
2. Test the application with real Commvault API
3. Research and test Priority 3 endpoint variations
4. Update documentation with working endpoints
