# Commvault API Test Results

## Test Summary

**Date:** 2025-11-13
**Success Rate:** 7/14 endpoints (50%)

## ✅ Working Endpoints

### 1. Clients - `/Client`
- **Status:** ✅ WORKING
- **Data Retrieved:** 3,604 clients
- **Structure:** `{ "clientProperties": [ { "client": {...}, "clientProps": {...} } ] }`
- **Notes:** Works perfectly, large dataset

### 2. Plans - `/Plan`
- **Status:** ✅ WORKING
- **Data Retrieved:** 278 plans
- **Structure:** `{ "plans": [ {...} ] }`
- **Notes:** Good data, backup plans/policies available

### 3. Storage Policies - `/V2/StoragePolicy`
- **Status:** ✅ WORKING
- **Data Retrieved:** 226 storage policies
- **Structure:** `{ "policies": [ { "storagePolicy": {...} } ] }`
- **Notes:** Works with V2 API

### 4. MediaAgents - `/MediaAgent`
- **Status:** ✅ WORKING (Structure Different Than Expected)
- **Data Retrieved:** 10+ MediaAgents
- **Actual Structure:** `{ "response": [ { "entityInfo": { "name": "...", "id": ... } } ] }`
- **Expected Structure:** `{ "mediaAgentList": [...] }`
- **⚠️ Code Update Needed:** Parser expects different JSON structure

### 5. Libraries - `/Library`
- **Status:** ✅ WORKING (Structure Different Than Expected)
- **Data Retrieved:** Available
- **Actual Structure:** `{ "response": [...] }`
- **Expected Structure:** `{ "libraryList": [...] }`
- **⚠️ Code Update Needed:** Parser expects different JSON structure

### 6. Storage Pools - `/StoragePool` (Alternative)
- **Status:** ✅ WORKING
- **Data Retrieved:** Multiple storage pools
- **Actual Structure:** `{ "storagePoolList": [ { "storagePool": {...}, "status": "...", "totalCapacity": ..., "totalFreeSpace": ... } ] }`
- **Notes:** Use `/StoragePool` instead of `/V4/StoragePool`
- **✅ Has Capacity Data:** `totalCapacity`, `totalFreeSpace`, `sizeOnDisk`

### 7. Alerts - `/Alert`
- **Status:** ✅ WORKING (Empty Response)
- **Data Retrieved:** `{}`  (empty dict)
- **Notes:** Endpoint works but no alerts currently active

## ❌ Failed/Not Available Endpoints

### 1. Jobs - `/Job`
- **Status:** ❌ TIMEOUT
- **Issue:** Request timed out after 30 seconds
- **Reason:** Likely too much data (trying to retrieve all jobs)
- **Recommendation:** Add filters like `?clientId=X` or `?completedJobLookupTime=last24hours`

### 2. Storage Pools (V4) - `/V4/StoragePool`
- **Status:** ❌ HTTP 404
- **Issue:** V4 API not available
- **Solution:** ✅ Use `/StoragePool` instead (tested and works)

### 3. Hypervisors - `/Instance`
- **Status:** ❌ HTTP 400
- **Issue:** Bad request - endpoint may require parameters
- **Recommendation:** Try `/V2/Virtualization/hypervisors` or `/VSA`

### 4. Storage Arrays - `/V4/Storage/Array`
- **Status:** ❌ HTTP 404
- **Issue:** V4 API not available or no arrays configured
- **Recommendation:** May not be available in this Commvault version

### 5. Events - `/Event`
- **Status:** ❌ HTTP 404
- **Issue:** Endpoint not available
- **Recommendation:** Events API may not be exposed in this version

### 6. Events (Critical) - `/Event?level=Critical`
- **Status:** ❌ HTTP 404
- **Issue:** Same as above

### 7. CommCell Info - `/Commcell`
- **Status:** ❌ HTTP 404
- **Issue:** Endpoint not available
- **Recommendation:** Try `/CommCell` (capital C) or check version compatibility

## Required Code Updates

### 1. Fix MediaAgents Parser

**Current Code Expects:**
```python
ma_list = mediaagents_json.get("mediaAgentList", [])
```

**Actual Structure:**
```json
{
  "response": [
    {
      "entityInfo": {
        "name": "commserve01",
        "id": 2
      }
    }
  ]
}
```

**Required Change:**
```python
ma_list = mediaagents_json.get("response", [])
for ma_entry in ma_list:
    entity_info = ma_entry.get("entityInfo", {})
    ma_id = entity_info.get("id")
    name = entity_info.get("name", "")
```

### 2. Fix Libraries Parser

**Similar issue** - use `response` key instead of `libraryList`

### 3. Fix Storage Pools Parser

**Current Code:**
```python
pools_list = storage_json.get("storagePools", [])
```

**Actual Structure:**
```python
pools_list = storage_json.get("storagePoolList", [])
```

**Also Update Endpoint:**
- Change from `/V4/StoragePool` to `/StoragePool`

### 4. Fix Jobs Timeout

**Add Filters:**
```python
# Instead of: /Job
# Use: /Job?clientId=X  or
#      /Job?completedJobLookupTime=last24hours
```

### 5. Remove Non-Working Endpoints

Disable or comment out:
- Events endpoints
- CommCell Info endpoint (until we find correct path)
- Hypervisors (needs investigation)
- Storage Arrays (may not be configured)

## Data Available for Dashboard

### ✅ Working Infrastructure Data:

1. **Clients** - 3,604 machines ✅
2. **MediaAgents** - 10+ servers ✅
3. **Storage Pools** - Multiple pools with capacity info ✅
4. **Libraries** - Available ✅
5. **Plans** - 278 backup plans ✅
6. **Storage Policies** - 226 policies ✅

### ✅ Capacity Monitoring Available:

Storage Pools provide:
- `totalCapacity` - Total storage capacity
- `totalFreeSpace` - Available free space
- `sizeOnDisk` - Used space
- `status` - "Online" / "Offline"
- `storagePoolType` - Type of storage

This is PERFECT for capacity monitoring!

### ❌ Not Available (Yet):

1. **Jobs** - Need to add filters to prevent timeout
2. **Events/Alerts** - API not available in this version
3. **Hypervisors** - Need different endpoint
4. **CommCell Health** - Need correct endpoint

## Recommendations

### Immediate Actions:

1. **Update MediaAgents parser** to use `response` key
2. **Update Libraries parser** to use `response` key
3. **Update Storage Pools** to use `/StoragePool` endpoint
4. **Update Storage Pools parser** to use `storagePoolList` key
5. **Add job filters** to prevent timeout

### Alternative Approaches:

#### For Jobs:
```python
# Filter by recent jobs only
/Job?completedJobLookupTime=last24hours
# Or filter by client
/Job?clientId=123
# Or limit results
/Job?pageSize=100
```

#### For Hypervisors:
Try these alternatives:
- `/V2/Virtualization/hypervisors`
- `/VSA` (Virtual Server Agent)
- `/V2/vsa/vm`

#### For CommCell Info:
Try these alternatives:
- `/CommCell` (capital C)
- `/GetId` (gets CommServe ID)
- `/Ping` (health check)

### What Works Great:

1. **Storage Capacity Monitoring** ✅
   - All data available in Storage Pools
   - Can track capacity, free space, usage
   - Perfect for dashboard

2. **Infrastructure Inventory** ✅
   - MediaAgents list
   - Libraries list
   - 3,600+ clients
   - 278 plans

3. **Storage Policies** ✅
   - 226 policies available
   - Can track configurations

## Updated Endpoint List

### Use These Endpoints:

| Feature | Endpoint | Status |
|---------|----------|--------|
| Clients | `/Client` | ✅ Working |
| Plans | `/Plan` | ✅ Working |
| Storage Policies | `/V2/StoragePolicy` | ✅ Working |
| MediaAgents | `/MediaAgent` | ✅ Working (update parser) |
| Libraries | `/Library` | ✅ Working (update parser) |
| Storage Pools | `/StoragePool` | ✅ Working (update parser & endpoint) |
| Jobs | `/Job?completedJobLookupTime=last24hours` | ⚠️ Needs filter |

### Don't Use (Not Available):

- `/V4/StoragePool` - Use `/StoragePool` instead
- `/Event` - Not available
- `/Commcell` - Not available (try alternatives)
- `/Instance` - Not working (try alternatives)
- `/V4/Storage/Array` - Not available

## Next Steps

1. Update [app.py](app.py) with corrected parsers
2. Change Storage Pools endpoint from V4 to standard
3. Add job filters to prevent timeout
4. Test alternative endpoints for Hypervisors
5. Remove/disable non-working monitoring features
6. Update documentation with actual working endpoints

## Test Files Generated

All API responses saved to:
- `test_output_Clients.json` - 3,604 clients
- `test_output_Plans.json` - 278 plans
- `test_output_Storage_Policies.json` - 226 policies
- `test_output_MediaAgents.json` - MediaAgents list
- `test_output_Libraries.json` - Libraries list
- `test_output_Storage_Pools_(Alt).json` - Storage pools with capacity
- `test_output_Alerts.json` - Empty (no active alerts)

Review these files to see exact JSON structures.
