# Commvault Infrastructure Visibility Guide

## Overview

The enhanced Commvault Data Retrieval application now provides comprehensive visibility into your Commvault infrastructure, including hardware, storage pools, hyperscale environments, and physical storage arrays.

## New Infrastructure Data Types

### 1. MediaAgents 📡

MediaAgents are the core infrastructure servers that handle data movement in Commvault.

**What you'll see:**
- MediaAgent ID and Name
- Hostname
- Operating System Type
- Status (Online/Offline)
- Available Storage Space
- Total Storage Space

**API Endpoint:** `GET /MediaAgent`

**Use Cases:**
- Monitor MediaAgent health and status
- Track storage capacity on backup infrastructure servers
- Identify MediaAgents that need capacity expansion
- Audit infrastructure for compliance

### 2. Storage Pools 💾

Storage Pools are logical groupings of storage resources (disk or tape) where backup data is stored.

**What you'll see:**
- Storage Pool ID and Name
- Pool Type (Disk, Tape, Cloud, Dedupe, etc.)
- Associated MediaAgent
- Total Capacity
- Free Space Available
- Deduplication Status (Enabled/Disabled)

**API Endpoint:** `GET /V4/StoragePool`

**Use Cases:**
- Monitor storage pool capacity and usage
- Identify pools running low on space
- Track deduplication savings
- Plan storage expansion
- Optimize storage allocation

### 3. Libraries 📚

Libraries are physical or virtual tape/disk libraries connected to MediaAgents.

**What you'll see:**
- Library ID and Name
- Library Type (Tape, Disk, VTL, etc.)
- Associated MediaAgent
- Status (Online/Offline)

**API Endpoint:** `GET /Library`

**Use Cases:**
- Monitor tape library health
- Track which MediaAgents serve which libraries
- Audit physical storage infrastructure
- Plan library maintenance

### 4. Hypervisors ☁️

Hypervisor instances represent VM infrastructure like VMware, Hyper-V, Nutanix, etc.

**What you'll see:**
- Instance ID and Name
- Hypervisor Type (VMware, Hyper-V, Nutanix, etc.)
- Hostname/vCenter
- Vendor
- Status (Active/Inactive)

**API Endpoint:** `GET /Instance`

**Use Cases:**
- Inventory all virtualization platforms
- Track hypervisor connectivity status
- Audit VM backup infrastructure
- Monitor multi-hypervisor environments

### 5. Storage Arrays 🗄️

Physical storage arrays (SAN/NAS) integrated with Commvault for snapshots and array-based backups.

**What you'll see:**
- Array ID and Name
- Array Type
- Vendor (NetApp, EMC, Pure Storage, etc.)
- Model
- Total Capacity
- Used Capacity

**API Endpoint:** `GET /V4/Storage/Array`

**Use Cases:**
- Inventory physical storage hardware
- Track array capacity utilization
- Monitor snapshot-enabled arrays
- Plan hardware refresh cycles

## How to Use Infrastructure Features

### Fetching Infrastructure Data

1. **Navigate to the home page** (`http://localhost:5000`)

2. **In the "Select Data Types" section**, you'll see two categories:
   - **📊 Basic Data** (Clients, Jobs, Plans, Storage Policies)
   - **🏗️ Infrastructure & Hardware** (New!)

3. **Select infrastructure data types** you want to retrieve:
   - ☑️ MediaAgents
   - ☑️ Storage Pools
   - ☑️ Libraries
   - ☑️ Hypervisors
   - ☑️ Storage Arrays

4. **Click "Fetch Data from Commvault"**

5. **View Results** - You'll see summary cards showing how many of each infrastructure component were retrieved

### Viewing Infrastructure Dashboard

The new **Infrastructure Dashboard** provides a comprehensive overview of your Commvault environment.

**Access:** Click "🏗️ Infrastructure Dashboard" in the navigation menu

**Dashboard Features:**

#### Summary Cards (Top Section)
- Total count of MediaAgents
- Total count of Storage Pools
- Total count of Libraries
- Total count of Hypervisors
- Total Clients
- Total Jobs

#### MediaAgents Status Table
- See all MediaAgents with their online/offline status
- Monitor storage capacity (available vs. total)
- Identify MediaAgents needing attention

#### Storage Pools Table
- View all storage pools with capacity information
- See free space and total capacity
- Check deduplication status
- Identify pools running low on space

#### Libraries Table
- List all tape and disk libraries
- Check which MediaAgent serves each library
- Monitor library online/offline status

#### Hypervisor Infrastructure Table
- View all hypervisor instances
- See hypervisor type and vendor
- Monitor connection status

#### Jobs Summary
- Total job count
- Completed jobs count
- Failed jobs count
- Success rate percentage

### Viewing Individual Data Types

Navigate to specific data type views using the menu:

- **Clients** - View all backup clients
- **Jobs** - View latest 100 backup jobs
- **MediaAgents** - View all MediaAgents with full details
- **Storage Pools** - View all storage pools with capacity
- **Libraries** - View all libraries
- **Hypervisors** - View all hypervisor instances
- **Storage Arrays** - View all storage arrays

## Database Schema

All infrastructure data is stored in SQLite with the following tables:

### mediaagents
```sql
CREATE TABLE mediaagents (
    mediaAgentId      INTEGER PRIMARY KEY,
    mediaAgentName    TEXT,
    hostName          TEXT,
    osType            TEXT,
    status            TEXT,
    availableSpace    TEXT,
    totalSpace        TEXT,
    lastFetchTime     TEXT
)
```

### storage_pools
```sql
CREATE TABLE storage_pools (
    storagePoolId     INTEGER PRIMARY KEY,
    storagePoolName   TEXT,
    storagePoolType   TEXT,
    mediaAgentName    TEXT,
    totalCapacity     TEXT,
    freeSpace         TEXT,
    dedupeEnabled     TEXT,
    lastFetchTime     TEXT
)
```

### libraries
```sql
CREATE TABLE libraries (
    libraryId         INTEGER PRIMARY KEY,
    libraryName       TEXT,
    libraryType       TEXT,
    mediaAgentName    TEXT,
    status            TEXT,
    lastFetchTime     TEXT
)
```

### hypervisors
```sql
CREATE TABLE hypervisors (
    instanceId        INTEGER PRIMARY KEY,
    instanceName      TEXT,
    hypervisorType    TEXT,
    hostName          TEXT,
    vendor            TEXT,
    status            TEXT,
    lastFetchTime     TEXT
)
```

### storage_arrays
```sql
CREATE TABLE storage_arrays (
    arrayId           INTEGER PRIMARY KEY,
    arrayName         TEXT,
    arrayType         TEXT,
    vendor            TEXT,
    model             TEXT,
    totalCapacity     TEXT,
    usedCapacity      TEXT,
    lastFetchTime     TEXT
)
```

## Common Use Cases

### 1. Capacity Planning

**Objective:** Identify storage pools nearing capacity

**Steps:**
1. Fetch Storage Pools data
2. Go to Infrastructure Dashboard
3. Review Storage Pools table
4. Look for pools with low free space
5. Plan expansion or data migration

### 2. Infrastructure Health Monitoring

**Objective:** Monitor all infrastructure components status

**Steps:**
1. Fetch all infrastructure data types
2. Open Infrastructure Dashboard
3. Check MediaAgents Status section for offline agents
4. Check Libraries section for offline libraries
5. Check Hypervisors section for inactive instances

### 3. Hyperscale Environment Audit

**Objective:** Inventory all hyperscale/VM infrastructure

**Steps:**
1. Fetch Hypervisors data
2. Go to View Hypervisors page
3. Export data or query database:
   ```sql
   SELECT instanceName, hypervisorType, vendor, status
   FROM hypervisors
   ORDER BY vendor, hypervisorType;
   ```

### 4. Storage Hardware Inventory

**Objective:** Document all physical storage arrays

**Steps:**
1. Fetch Storage Arrays data
2. Go to View Storage Arrays page
3. Review vendor, model, and capacity information
4. Use for hardware refresh planning

### 5. MediaAgent Load Distribution

**Objective:** Understand which MediaAgents serve which resources

**Steps:**
1. Fetch MediaAgents, Storage Pools, and Libraries
2. Query database:
   ```sql
   SELECT
       m.mediaAgentName,
       COUNT(DISTINCT sp.storagePoolId) as pool_count,
       COUNT(DISTINCT l.libraryId) as library_count
   FROM mediaagents m
   LEFT JOIN storage_pools sp ON m.mediaAgentName = sp.mediaAgentName
   LEFT JOIN libraries l ON m.mediaAgentName = l.mediaAgentName
   GROUP BY m.mediaAgentName;
   ```

## Advanced Queries

### Find Storage Pools by Type
```sql
SELECT storagePoolName, storagePoolType, totalCapacity, freeSpace, dedupeEnabled
FROM storage_pools
WHERE storagePoolType = 'Disk'
ORDER BY storagePoolName;
```

### List Hypervisors by Vendor
```sql
SELECT vendor, COUNT(*) as count,
       GROUP_CONCAT(instanceName, ', ') as instances
FROM hypervisors
GROUP BY vendor
ORDER BY count DESC;
```

### MediaAgent Capacity Summary
```sql
SELECT
    mediaAgentName,
    osType,
    status,
    totalSpace,
    availableSpace,
    CASE
        WHEN totalSpace != 'N/A'
        THEN CAST(availableSpace AS REAL) / CAST(totalSpace AS REAL) * 100
        ELSE 0
    END as percent_free
FROM mediaagents
ORDER BY percent_free ASC;
```

### Storage Arrays by Vendor
```sql
SELECT vendor, model, COUNT(*) as count, SUM(totalCapacity) as total_capacity
FROM storage_arrays
GROUP BY vendor, model
ORDER BY vendor, model;
```

## Troubleshooting

### No Infrastructure Data Showing

**Problem:** Dashboard shows "No Infrastructure Data Available"

**Solutions:**
1. Go to home page and fetch infrastructure data
2. Make sure you select infrastructure checkboxes (MediaAgents, Storage Pools, etc.)
3. Check for API errors in the results page
4. Verify your Commvault user has permissions to view infrastructure

### API Endpoint Errors

**Problem:** "Failed with status 404" for infrastructure endpoints

**Solutions:**
1. Verify your Commvault version supports these API endpoints (v11.24+)
2. Check if the endpoint paths are correct for your version
3. Some endpoints may use different versions (V2, V4, etc.)
4. Try fetching from CommandCenter web console to verify data exists

### Empty Tables

**Problem:** Data fetched but tables are empty

**Solutions:**
1. Check the JSON response structure in results
2. The parsing logic may need adjustment for your Commvault version
3. Review the `save_*_to_db()` functions in [app.py](app.py)
4. Enable debug mode and check console output

## API Version Compatibility

The infrastructure endpoints use different API versions:

| Feature | Endpoint | Notes |
|---------|----------|-------|
| MediaAgents | `/MediaAgent` | Available in v11+ |
| Libraries | `/Library` | Available in v11+ |
| Storage Pools | `/V4/StoragePool` | V4 API, v11.24+ |
| Hypervisors | `/Instance` | Returns VM instances |
| Storage Arrays | `/V4/Storage/Array` | V4 API, v11.24+ |

If you're using an older Commvault version, some endpoints may not be available or may use different paths.

## Best Practices

1. **Regular Updates**: Fetch infrastructure data weekly to track changes
2. **Capacity Monitoring**: Set alerts for storage pools below 20% free space
3. **Status Checks**: Monitor MediaAgent and Library status daily
4. **Audit Trail**: Use `lastFetchTime` to track when data was last updated
5. **Backup Database**: Keep backups of `commvault.db` for historical analysis
6. **Export Reports**: Query database to generate custom infrastructure reports

## Next Steps

- Set up automated scheduled fetching (cron/Task Scheduler)
- Create custom SQL views for specific infrastructure reports
- Export data to CSV for executive reporting
- Integrate with monitoring tools (Prometheus, Grafana, etc.)
- Build alerting based on threshold values

---

**Need Help?**

- Check [README.md](README.md) for general application documentation
- Review [QUICKSTART.md](QUICKSTART.md) for setup instructions
- Consult Commvault REST API documentation at [api.commvault.com](https://api.commvault.com)
