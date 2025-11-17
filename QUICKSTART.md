# Quick Start Guide

Get your Commvault Data Retrieval app running in 5 minutes!

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs Flask and requests libraries.

## Step 2: Configure Your Commvault Connection

The [config.ini](config.ini) file is already set up with your credentials:

```ini
[commvault]
base_url = http://commvaultweb01.jhb.seagatestoragecloud.co.za:81/SearchSvc/CVWebService.svc
username = guys@storvault.co.za
password = U3RyMzN0MDkhIQ==
```

If you need to change these, edit the file or use the web interface.

## Step 3: Run the Application

```bash
python app.py
```

You should see:
```
 * Running on http://0.0.0.0:5000
 * Debug mode: on
```

## Step 4: Open in Browser

Navigate to: **http://localhost:5000**

## Step 5: Fetch Data

1. The form will be pre-filled with your config settings
2. Select which data types you want to retrieve:
   - ☑️ Clients
   - ☑️ Jobs
   - ☑️ Plans
   - ☑️ Storage
3. Click **"Fetch Data from Commvault"**
4. Wait for data to be retrieved (may take a few seconds)
5. View the results on the results page!

## Step 6: Browse Your Data

Use the navigation menu to view different data types:
- **View Clients** - All client machines
- **View Jobs** - Latest 100 backup/restore jobs
- **View Plans** - Backup plans and policies
- **View Storage** - Storage policy configurations

## Database Location

All data is stored in: `Database/commvault.db`

You can query this SQLite database directly using tools like:
- [DB Browser for SQLite](https://sqlitebrowser.org/)
- `sqlite3` command line
- Python scripts

## Troubleshooting

**Can't connect?**
- Check the base URL is accessible from your machine
- Verify credentials are correct
- Ensure the Commvault server is running

**Authentication failed?**
- The password in config is Base64-encoded: `U3RyMzN0MDkhIQ==`
- If you need to change it, you can enter a plaintext password in the web form

**No data showing?**
- Check that the data types exist in your CommCell
- Look for error messages on the results page
- Check your user has permissions to access the API

## Next Steps

- Explore the [README.md](README.md) for detailed documentation
- Modify [app.py](app.py) to add custom data processing
- Query the database directly for custom reports
- Schedule automated data fetching with cron/Task Scheduler

## API Endpoints Overview

| What You Click | API Called | What You Get |
|----------------|-----------|--------------|
| Fetch Clients | `/Client` | All backup clients |
| Fetch Jobs | `/Job` | Backup/restore jobs |
| Fetch Plans | `/Plan` | Backup policies |
| Fetch Storage | `/V2/StoragePolicy` | Storage configs |

---

**Ready to go!** Start the app and begin retrieving your Commvault data.
