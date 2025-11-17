# Commvault Pruning Log Collector
# Run this script on each MediaAgent to collect pruning logs

param(
    [string]$OutputPath = "D:\Commvault_API\MediaAgent_Logs",
    [string]$PoolName = "",
    [int]$LastNDays = 7
)

Write-Host "=====================================================================================================" -ForegroundColor Cyan
Write-Host "COMMVAULT PRUNING LOG COLLECTOR" -ForegroundColor Cyan
Write-Host "=====================================================================================================" -ForegroundColor Cyan
Write-Host ""

# Find Commvault installation directory
$cvInstallPaths = @(
    "C:\Program Files\Commvault\ContentStore",
    "C:\Program Files (x86)\Commvault\ContentStore",
    "D:\Program Files\Commvault\ContentStore",
    "E:\Commvault\ContentStore"
)

$cvInstallPath = $null
foreach ($path in $cvInstallPaths) {
    if (Test-Path $path) {
        $cvInstallPath = $path
        break
    }
}

if (-not $cvInstallPath) {
    Write-Host "ERROR: Could not find Commvault installation directory" -ForegroundColor Red
    Write-Host "Please specify the path manually" -ForegroundColor Yellow
    exit 1
}

Write-Host "Commvault Install Path: $cvInstallPath" -ForegroundColor Green
$logPath = Join-Path $cvInstallPath "Log Files"

if (-not (Test-Path $logPath)) {
    Write-Host "ERROR: Log directory not found: $logPath" -ForegroundColor Red
    exit 1
}

Write-Host "Log Path: $logPath" -ForegroundColor Green
Write-Host ""

# Create output directory
if (-not (Test-Path $OutputPath)) {
    New-Item -ItemType Directory -Path $OutputPath | Out-Null
    Write-Host "Created output directory: $OutputPath" -ForegroundColor Green
}

# Get MediaAgent name
$maName = $env:COMPUTERNAME
Write-Host "MediaAgent Name: $maName" -ForegroundColor Cyan
Write-Host ""

# Define log files to collect
$logFiles = @(
    "SIDBPrune.log",
    "SIDBPhysicalDeletes.log",
    "CVMA.log",
    "SIDBEngine.log"
)

Write-Host "=====================================================================================================" -ForegroundColor Cyan
Write-Host "COLLECTING LOG FILES" -ForegroundColor Cyan
Write-Host "=====================================================================================================" -ForegroundColor Cyan
Write-Host ""

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$reportFile = Join-Path $OutputPath "$maName`_PruningAnalysis_$timestamp.txt"

# Start report
$report = @"
====================================================================================================
MEDIAAGENT PRUNING LOG ANALYSIS
====================================================================================================
MediaAgent: $maName
Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Log Path: $logPath
Analysis Period: Last $LastNDays days
$(if ($PoolName) { "Filtering for Pool: $PoolName" })

====================================================================================================
LOG FILE COLLECTION
====================================================================================================

"@

foreach ($logFile in $logFiles) {
    $logFilePath = Join-Path $logPath $logFile

    Write-Host "Checking: $logFile..." -NoNewline

    if (Test-Path $logFilePath) {
        $fileInfo = Get-Item $logFilePath
        $fileSizeMB = [math]::Round($fileInfo.Length / 1MB, 2)

        Write-Host " FOUND ($fileSizeMB MB)" -ForegroundColor Green

        $report += @"
File: $logFile
  Status: FOUND
  Size: $fileSizeMB MB
  Last Modified: $($fileInfo.LastWriteTime)
  Path: $logFilePath

"@

        # Copy log file to output
        $destFile = Join-Path $OutputPath "$maName`_$logFile"
        Copy-Item $logFilePath $destFile -Force
        Write-Host "  Copied to: $destFile" -ForegroundColor Gray

    } else {
        Write-Host " NOT FOUND" -ForegroundColor Red
        $report += @"
File: $logFile
  Status: NOT FOUND
  Expected Path: $logFilePath

"@
    }
}

Write-Host ""
Write-Host "=====================================================================================================" -ForegroundColor Cyan
Write-Host "ANALYZING PRUNING ACTIVITY" -ForegroundColor Cyan
Write-Host "=====================================================================================================" -ForegroundColor Cyan
Write-Host ""

# Analyze SIDBPrune.log
$pruneLogPath = Join-Path $logPath "SIDBPrune.log"
if (Test-Path $pruneLogPath) {
    $report += @"
====================================================================================================
SIDBPrune.log ANALYSIS
====================================================================================================

"@

    # Get recent pruning activity
    $cutoffDate = (Get-Date).AddDays(-$LastNDays)

    Write-Host "Searching for pruning activity in last $LastNDays days..." -ForegroundColor Yellow

    # Search for key patterns
    $patterns = @{
        "Pruning Started" = "Pruning.*started|Begin.*prune"
        "Pruning Completed" = "Pruning.*completed|Prune.*successful"
        "Errors" = "ERROR|FAILED|Exception"
        "Warnings" = "WARNING|WARN"
        "Skipped" = "Skipped|Skip"
        "Freed Space" = "Freed.*bytes|Deleted.*bytes|Reclaimed"
    }

    foreach ($patternName in $patterns.Keys) {
        $pattern = $patterns[$patternName]

        Write-Host "  Searching for: $patternName..." -NoNewline

        $matches = Select-String -Path $pruneLogPath -Pattern $pattern -AllMatches | Select-Object -Last 20

        if ($matches) {
            Write-Host " Found $($matches.Count) matches" -ForegroundColor Green

            $report += "`n$patternName (Last 20 matches):`n"
            $report += "-" * 100 + "`n"

            foreach ($match in $matches) {
                $report += "  $($match.Line)`n"
            }
            $report += "`n"
        } else {
            Write-Host " No matches" -ForegroundColor Gray
            $report += "`n$patternName: No matches found`n`n"
        }
    }

    # If filtering by pool name
    if ($PoolName) {
        Write-Host ""
        Write-Host "Filtering for pool: $PoolName" -ForegroundColor Cyan

        $poolMatches = Select-String -Path $pruneLogPath -Pattern $PoolName -Context 2 | Select-Object -Last 50

        if ($poolMatches) {
            $report += @"

====================================================================================================
POOL-SPECIFIC ACTIVITY: $PoolName
====================================================================================================

"@
            foreach ($match in $poolMatches) {
                $report += "Line $($match.LineNumber):`n"
                foreach ($line in $match.Context.PreContext) {
                    $report += "  $line`n"
                }
                $report += "  >>> $($match.Line) <<<`n"
                foreach ($line in $match.Context.PostContext) {
                    $report += "  $line`n"
                }
                $report += "`n"
            }
        } else {
            $report += "`nNo activity found for pool: $PoolName`n"
        }
    }
}

Write-Host ""
Write-Host "=====================================================================================================" -ForegroundColor Cyan
Write-Host "SUMMARY & RECOMMENDATIONS" -ForegroundColor Cyan
Write-Host "=====================================================================================================" -ForegroundColor Cyan
Write-Host ""

$report += @"

====================================================================================================
SUMMARY & RECOMMENDATIONS
====================================================================================================

Next Steps:
  1. Review the collected log files in: $OutputPath
  2. Check for ERROR or FAILED messages
  3. Verify pruning is running regularly (daily recommended)
  4. Look for "Freed bytes" entries - indicates successful space reclamation
  5. If "Skipped" messages found - investigate blocking issues

Common Issues:
  - Mount path not accessible: Check disk/network connectivity
  - Insufficient permissions: Verify service account permissions
  - No recent activity: Check pruning schedules are enabled
  - Errors/Exceptions: Review full error messages for root cause

Report saved to: $reportFile

====================================================================================================
"@

# Save report
$report | Out-File -FilePath $reportFile -Encoding UTF8

Write-Host "Report generated: $reportFile" -ForegroundColor Green
Write-Host ""
Write-Host "Log files collected:" -ForegroundColor Cyan
Get-ChildItem $OutputPath -Filter "$maName*" | ForEach-Object {
    Write-Host "  - $($_.Name)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "COLLECTION COMPLETE!" -ForegroundColor Green
Write-Host "=====================================================================================================" -ForegroundColor Cyan
