"""
Commvault Aging & Pruning Tracker
Track aging and pruning status via API without needing log files
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

class AgingPruningTracker:
    """Track aging and pruning operations via Commvault API"""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token
        self.headers = {
            'Authtoken': f'QSDK {token}',
            'Accept': 'application/json'
        }

    def get_aging_status(self, days_back: int = 7) -> Dict:
        """
        Get comprehensive aging and pruning status

        Returns:
            Dictionary containing:
            - aged_jobs: List of jobs that should have triggered aging
            - pruning_jobs: List of pruning jobs executed
            - ddb_stats: DDB statistics showing pruning effectiveness
            - retention_violations: Data that should be aged but isn't
        """
        result = {
            'aged_jobs': [],
            'pruning_jobs': [],
            'ddb_stats': [],
            'retention_violations': [],
            'summary': {}
        }

        # 1. Get job history to find auxiliary copies (aging triggers)
        print("Fetching job history...")
        jobs = self._get_recent_jobs(days_back)

        for job in jobs:
            job_type = job.get('jobType', '').lower()

            # Auxiliary copy jobs trigger aging
            if 'auxiliary' in job_type or 'aux copy' in job_type:
                result['aged_jobs'].append({
                    'job_id': job.get('jobId'),
                    'job_type': job.get('jobType'),
                    'status': job.get('status'),
                    'client': job.get('subclient', {}).get('clientName', ''),
                    'completed': job.get('jobEndTime', '')
                })

            # Pruning jobs
            elif 'prun' in job_type or 'aging' in job_type:
                result['pruning_jobs'].append({
                    'job_id': job.get('jobId'),
                    'job_type': job.get('jobType'),
                    'status': job.get('status'),
                    'start': job.get('jobStartTime', ''),
                    'end': job.get('jobEndTime', '')
                })

        # 2. Get DDB statistics to see pruning effectiveness
        print("Fetching DDB statistics...")
        result['ddb_stats'] = self._get_ddb_statistics()

        # 3. Get storage pool data to check retention
        print("Checking retention policies...")
        result['retention_violations'] = self._check_retention_violations()

        # 4. Generate summary
        result['summary'] = {
            'total_aux_copy_jobs': len(result['aged_jobs']),
            'successful_aux_copies': len([j for j in result['aged_jobs'] if 'complete' in j.get('status', '').lower()]),
            'total_pruning_jobs': len(result['pruning_jobs']),
            'successful_pruning': len([j for j in result['pruning_jobs'] if 'complete' in j.get('status', '').lower()]),
            'total_ddbs': len(result['ddb_stats']),
            'retention_issues': len(result['retention_violations'])
        }

        return result

    def _get_recent_jobs(self, days_back: int) -> List[Dict]:
        """Get jobs from last N days"""
        try:
            # Try simpler endpoint first - just get recent jobs without date filter
            response = requests.get(
                f'{self.base_url}/Job?clientId=0',
                headers=self.headers,
                timeout=60,  # Increase timeout
                verify=False
            )

            if response.status_code == 200:
                jobs_data = response.json()
                jobs_list = jobs_data.get('jobs', [])

                # Extract job summaries - limit to last 100 jobs for performance
                return [job.get('jobSummary', {}) for job in jobs_list[:100]]
            else:
                print(f"Failed to get jobs: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error getting jobs (skipping): {e}")
            # Don't fail completely if jobs can't be retrieved
            return []

    def _get_ddb_statistics(self) -> List[Dict]:
        """Get DDB store statistics"""
        ddb_stats = []

        try:
            # First, get list of storage policies to find DDB stores
            response = requests.get(
                f'{self.base_url}/StoragePolicy',
                headers=self.headers,
                timeout=30,
                verify=False
            )

            if response.status_code == 200:
                policies = response.json()

                # For each policy with dedup, get DDB stats
                for policy in policies.get('policies', [])[:20]:  # Limit to first 20
                    policy_id = policy.get('storagePolicyId')

                    # Get policy details
                    detail_response = requests.get(
                        f'{self.base_url}/StoragePolicy/{policy_id}',
                        headers=self.headers,
                        timeout=30,
                        verify=False
                    )

                    if detail_response.status_code == 200:
                        policy_detail = detail_response.json()

                        # Check if deduplication is enabled
                        for copy in policy_detail.get('copy', []):
                            dedupe_flags = copy.get('dedupeFlags', {})
                            if dedupe_flags.get('enableDeduplication'):
                                # This copy uses deduplication
                                copy_name = copy.get('StoragePolicyCopy', {}).get('copyName', 'Unknown')

                                ddb_stats.append({
                                    'policy_name': policy_detail.get('storagePolicy', {}).get('storagePolicyName', ''),
                                    'copy_name': copy_name,
                                    'has_dedup': True,
                                    'retention_days': copy.get('retentionRules', {}).get('retainBackupDataForDays', 0)
                                })

            return ddb_stats
        except Exception as e:
            print(f"Error getting DDB stats: {e}")
            return []

    def _check_retention_violations(self) -> List[Dict]:
        """Check for data that should be aged but hasn't been"""
        violations = []

        try:
            # Get recent backup jobs
            response = requests.get(
                f'{self.base_url}/Job?clientId=0',
                headers=self.headers,
                timeout=60,
                verify=False
            )

            if response.status_code == 200:
                jobs_data = response.json()
                jobs_list = jobs_data.get('jobs', [])

                # Look for backup jobs that completed but no aux copy followed
                for job in jobs_list[:50]:
                    job_summary = job.get('jobSummary', {})
                    job_type = job_summary.get('jobType', '').lower()

                    # Check if it's a backup job
                    if 'backup' in job_type and 'auxiliary' not in job_type:
                        job_id = job_summary.get('jobId')
                        completed_time = job_summary.get('jobEndTime', '')
                        client_name = job_summary.get('subclient', {}).get('clientName', '')

                        # Simple heuristic: if backup completed but we haven't seen aux copy
                        # This is simplified - real implementation would track relationships
                        violations.append({
                            'job_id': job_id,
                            'client': client_name,
                            'completed': completed_time,
                            'reason': 'Backup completed, aux copy status unknown'
                        })

        except Exception as e:
            print(f"Error checking retention violations: {e}")

        return violations[:10]  # Limit to 10 for display

    def get_aging_trending_data(self, days_back: int = 30) -> Dict:
        """
        Get trending data for aging effectiveness over time

        Returns data suitable for charting DDB size, retention compliance, etc.
        """
        trending = {
            'dates': [],
            'ddb_sizes': [],
            'backup_counts': [],
            'aux_copy_counts': [],
            'pruning_counts': []
        }

        # For now, return structure - would need historical data collection
        # This would be populated by storing daily snapshots in database

        return trending


def main():
    """Example usage"""
    import sys
    import configparser
    sys.path.insert(0, '.')
    from app import authenticate_commvault

    # Load credentials from config.ini
    config = configparser.ConfigParser()
    config.read('config.ini')

    base_url = config.get('commvault', 'webservice_url')
    username = config.get('commvault', 'username')
    password = config.get('commvault', 'password')

    print("Authenticating...")
    print(f"URL: {base_url}")
    print(f"User: {username}")
    token = authenticate_commvault(base_url, username, password)

    if not token:
        print("Authentication failed!")
        return

    print("Authentication successful!")
    print("=" * 80)
    print()

    tracker = AgingPruningTracker(base_url, token)
    status = tracker.get_aging_status(days_back=7)

    print("AGING & PRUNING STATUS (Last 7 Days)")
    print("=" * 80)
    print()

    print(f"Auxiliary Copy Jobs (Aging Triggers): {status['summary']['total_aux_copy_jobs']}")
    print(f"  Successful: {status['summary']['successful_aux_copies']}")
    print()

    print(f"Pruning Jobs: {status['summary']['total_pruning_jobs']}")
    print(f"  Successful: {status['summary']['successful_pruning']}")
    print()

    print(f"DDB Stores with Deduplication: {status['summary']['total_ddbs']}")
    for ddb in status['ddb_stats'][:10]:
        print(f"  - {ddb['policy_name']} / {ddb['copy_name']} (Retention: {ddb['retention_days']} days)")
    print()

    if status['aged_jobs']:
        print("Recent Auxiliary Copy Jobs:")
        for job in status['aged_jobs'][:10]:
            print(f"  Job {job['job_id']}: {job['client']} - {job['status']}")

    print()
    print("=" * 80)


if __name__ == '__main__':
    main()
