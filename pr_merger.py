#!/usr/bin/env python3
"""
PR Merger for Automated Release Management

This module provides functionality for automatically merging pull requests
after all required checks have passed and conditions are met.
"""

import os
import time
import json
import requests
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass


class PRState(Enum):
    """Pull request states"""
    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"


class CheckStatus(Enum):
    """Status check states"""
    PENDING = "pending"
    SUCCESS = "success" 
    FAILURE = "failure"
    ERROR = "error"
    NEUTRAL = "neutral"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    ACTION_REQUIRED = "action_required"


class MergeMethod(Enum):
    """Available merge methods"""
    MERGE = "merge"
    SQUASH = "squash"
    REBASE = "rebase"


@dataclass
class PRInfo:
    """Pull request information"""
    number: int
    title: str
    state: str
    mergeable: bool
    mergeable_state: str
    merged: bool
    base_branch: str
    head_branch: str
    author: str
    created_at: str
    updated_at: str
    draft: bool = False
    labels: List[str] = None
    assignees: List[str] = None
    reviewers: List[str] = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = []
        if self.assignees is None:
            self.assignees = []
        if self.reviewers is None:
            self.reviewers = []


@dataclass
class CheckRun:
    """Status check or check run information"""
    name: str
    status: str
    conclusion: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    html_url: Optional[str]


class PRMerger:
    """Handles automated merging of pull requests"""
    
    def __init__(self, github_token: str, repository: str, base_url: str = "https://api.github.com"):
        self.github_token = github_token
        self.repository = repository  # format: "owner/repo"
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'PR-Merger/1.0'
        })
        
        # Default merge configuration
        self.merge_config = {
            'method': MergeMethod.SQUASH,
            'delete_head_branch': True,
            'required_status_checks': [],
            'required_reviews': 1,
            'dismiss_stale_reviews': True,
            'require_up_to_date': True,
            'auto_merge_labels': ['auto-merge', 'ready-to-merge'],
            'blocked_labels': ['do-not-merge', 'work-in-progress', 'wip'],
            'target_branches': ['main', 'master'],
            'timeout_minutes': 30,
            'retry_interval_seconds': 60
        }
    
    def configure_merge_settings(self, **kwargs) -> None:
        """Update merge configuration"""
        self.merge_config.update(kwargs)
    
    def get_pr_info(self, pr_number: int) -> Optional[PRInfo]:
        """Get pull request information"""
        try:
            url = f"{self.base_url}/repos/{self.repository}/pulls/{pr_number}"
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            return PRInfo(
                number=data['number'],
                title=data['title'],
                state=data['state'],
                mergeable=data.get('mergeable', False),
                mergeable_state=data.get('mergeable_state', 'unknown'),
                merged=data['merged'],
                base_branch=data['base']['ref'],
                head_branch=data['head']['ref'],
                author=data['user']['login'],
                created_at=data['created_at'],
                updated_at=data['updated_at'],
                draft=data.get('draft', False),
                labels=[label['name'] for label in data.get('labels', [])],
                assignees=[assignee['login'] for assignee in data.get('assignees', [])],
                reviewers=[reviewer['login'] for reviewer in data.get('requested_reviewers', [])]
            )
            
        except requests.RequestException as e:
            print(f"Error getting PR info: {e}")
            return None
    
    def get_pr_reviews(self, pr_number: int) -> List[Dict[str, Any]]:
        """Get pull request reviews"""
        try:
            url = f"{self.base_url}/repos/{self.repository}/pulls/{pr_number}/reviews"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            print(f"Error getting PR reviews: {e}")
            return []
    
    def get_status_checks(self, pr_number: int) -> List[CheckRun]:
        """Get status checks for a pull request"""
        pr_info = self.get_pr_info(pr_number)
        if not pr_info:
            return []
        
        checks = []
        
        try:
            # Get combined status (legacy status API)
            status_url = f"{self.base_url}/repos/{self.repository}/commits/{pr_info.head_branch}/status"
            status_response = self.session.get(status_url)
            status_response.raise_for_status()
            status_data = status_response.json()
            
            for status in status_data.get('statuses', []):
                checks.append(CheckRun(
                    name=status['context'],
                    status=status['state'],
                    conclusion=status['state'],
                    started_at=status['created_at'],
                    completed_at=status['updated_at'],
                    html_url=status.get('target_url')
                ))
            
            # Get check runs (newer checks API)
            checks_url = f"{self.base_url}/repos/{self.repository}/commits/{pr_info.head_branch}/check-runs"
            checks_response = self.session.get(checks_url)
            checks_response.raise_for_status()
            checks_data = checks_response.json()
            
            for check in checks_data.get('check_runs', []):
                checks.append(CheckRun(
                    name=check['name'],
                    status=check['status'],
                    conclusion=check['conclusion'],
                    started_at=check['started_at'],
                    completed_at=check['completed_at'],
                    html_url=check['html_url']
                ))
                
        except requests.RequestException as e:
            print(f"Error getting status checks: {e}")
        
        return checks
    
    def check_merge_conditions(self, pr_number: int) -> Tuple[bool, List[str]]:
        """Check if PR meets all merge conditions"""
        pr_info = self.get_pr_info(pr_number)
        if not pr_info:
            return False, ["Could not retrieve PR information"]
        
        reasons = []
        
        # Check PR state
        if pr_info.state != PRState.OPEN.value:
            reasons.append(f"PR is not open (current state: {pr_info.state})")
        
        if pr_info.merged:
            reasons.append("PR is already merged")
        
        if pr_info.draft:
            reasons.append("PR is in draft state")
        
        # Check target branch
        if pr_info.base_branch not in self.merge_config['target_branches']:
            reasons.append(f"Target branch '{pr_info.base_branch}' is not in allowed list")
        
        # Check blocked labels
        blocked_labels = set(pr_info.labels) & set(self.merge_config['blocked_labels'])
        if blocked_labels:
            reasons.append(f"PR has blocking labels: {', '.join(blocked_labels)}")
        
        # Check auto-merge labels (if configured)
        if self.merge_config['auto_merge_labels']:
            auto_merge_labels = set(pr_info.labels) & set(self.merge_config['auto_merge_labels'])
            if not auto_merge_labels:
                reasons.append(f"PR missing required auto-merge labels: {', '.join(self.merge_config['auto_merge_labels'])}")
        
        # Check mergeable state
        if not pr_info.mergeable:
            reasons.append("PR is not mergeable")
        
        if pr_info.mergeable_state in ['dirty', 'blocked']:
            reasons.append(f"PR mergeable state is '{pr_info.mergeable_state}'")
        
        # Check reviews
        reviews = self.get_pr_reviews(pr_number)
        approved_reviews = [r for r in reviews if r['state'] == 'APPROVED']
        requested_changes = [r for r in reviews if r['state'] == 'CHANGES_REQUESTED']
        
        if len(approved_reviews) < self.merge_config['required_reviews']:
            reasons.append(f"Not enough approvals ({len(approved_reviews)}/{self.merge_config['required_reviews']})")
        
        if requested_changes:
            reasons.append("There are requested changes")
        
        # Check status checks
        status_checks = self.get_status_checks(pr_number)
        required_checks = self.merge_config['required_status_checks']
        
        if required_checks:
            for required_check in required_checks:
                matching_checks = [c for c in status_checks if c.name == required_check]
                if not matching_checks:
                    reasons.append(f"Required status check '{required_check}' not found")
                elif not any(c.conclusion == 'success' for c in matching_checks):
                    reasons.append(f"Required status check '{required_check}' has not passed")
        
        # Check all status checks are successful (if no specific requirements)
        if not required_checks:
            failing_checks = [c for c in status_checks if c.conclusion in ['failure', 'error', 'cancelled', 'timed_out']]
            if failing_checks:
                reasons.append(f"Failing checks: {', '.join(c.name for c in failing_checks)}")
            
            pending_checks = [c for c in status_checks if c.status == 'pending' or c.conclusion is None]
            if pending_checks:
                reasons.append(f"Pending checks: {', '.join(c.name for c in pending_checks)}")
        
        return len(reasons) == 0, reasons
    
    def merge_pr(self, pr_number: int, method: Optional[MergeMethod] = None, 
                commit_title: Optional[str] = None, commit_message: Optional[str] = None) -> bool:
        """Merge a pull request"""
        merge_method = method or self.merge_config['method']
        
        try:
            pr_info = self.get_pr_info(pr_number)
            if not pr_info:
                print(f"Could not get PR {pr_number} information")
                return False
            
            url = f"{self.base_url}/repos/{self.repository}/pulls/{pr_number}/merge"
            data = {
                'merge_method': merge_method.value
            }
            
            if commit_title:
                data['commit_title'] = commit_title
            if commit_message:
                data['commit_message'] = commit_message
            
            response = self.session.put(url, json=data)
            response.raise_for_status()
            
            print(f"Successfully merged PR #{pr_number}: {pr_info.title}")
            
            # Delete head branch if configured
            if self.merge_config['delete_head_branch'] and not pr_info.head_branch.startswith('dependabot/'):
                self._delete_branch(pr_info.head_branch)
            
            return True
            
        except requests.RequestException as e:
            print(f"Error merging PR {pr_number}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    print(f"Error details: {error_details}")
                except:
                    print(f"Response: {e.response.text}")
            return False
    
    def _delete_branch(self, branch_name: str) -> bool:
        """Delete a branch after merge"""
        try:
            url = f"{self.base_url}/repos/{self.repository}/git/refs/heads/{branch_name}"
            response = self.session.delete(url)
            response.raise_for_status()
            print(f"Deleted branch: {branch_name}")
            return True
        except requests.RequestException as e:
            print(f"Could not delete branch {branch_name}: {e}")
            return False
    
    def wait_and_merge(self, pr_number: int, timeout_minutes: Optional[int] = None) -> bool:
        """Wait for conditions to be met, then merge PR"""
        timeout = timeout_minutes or self.merge_config['timeout_minutes']
        end_time = datetime.now() + timedelta(minutes=timeout)
        
        print(f"Waiting to merge PR #{pr_number}...")
        
        while datetime.now() < end_time:
            can_merge, reasons = self.check_merge_conditions(pr_number)
            
            if can_merge:
                print("All conditions met, attempting to merge...")
                return self.merge_pr(pr_number)
            else:
                print(f"Waiting for conditions: {'; '.join(reasons)}")
                time.sleep(self.merge_config['retry_interval_seconds'])
        
        print(f"Timeout reached after {timeout} minutes")
        return False
    
    def auto_merge_prs(self, label_filter: Optional[str] = None) -> List[int]:
        """Automatically merge all eligible PRs"""
        try:
            # Get open PRs
            url = f"{self.base_url}/repos/{self.repository}/pulls"
            params = {'state': 'open'}
            
            if label_filter:
                params['labels'] = label_filter
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            prs = response.json()
            
            merged_prs = []
            
            for pr_data in prs:
                pr_number = pr_data['number']
                
                # Check if PR has auto-merge labels
                pr_labels = [label['name'] for label in pr_data.get('labels', [])]
                if self.merge_config['auto_merge_labels']:
                    if not any(label in pr_labels for label in self.merge_config['auto_merge_labels']):
                        continue
                
                print(f"Checking PR #{pr_number}: {pr_data['title']}")
                
                can_merge, reasons = self.check_merge_conditions(pr_number)
                if can_merge:
                    if self.merge_pr(pr_number):
                        merged_prs.append(pr_number)
                else:
                    print(f"Cannot merge PR #{pr_number}: {'; '.join(reasons)}")
            
            return merged_prs
            
        except requests.RequestException as e:
            print(f"Error getting PRs for auto-merge: {e}")
            return []
    
    def get_merge_status(self, pr_number: int) -> Dict[str, Any]:
        """Get detailed merge status for a PR"""
        pr_info = self.get_pr_info(pr_number)
        if not pr_info:
            return {'error': 'Could not retrieve PR information'}
        
        can_merge, reasons = self.check_merge_conditions(pr_number)
        status_checks = self.get_status_checks(pr_number)
        reviews = self.get_pr_reviews(pr_number)
        
        return {
            'pr_number': pr_number,
            'title': pr_info.title,
            'state': pr_info.state,
            'can_merge': can_merge,
            'reasons': reasons,
            'mergeable': pr_info.mergeable,
            'mergeable_state': pr_info.mergeable_state,
            'reviews': {
                'approved': len([r for r in reviews if r['state'] == 'APPROVED']),
                'changes_requested': len([r for r in reviews if r['state'] == 'CHANGES_REQUESTED']),
                'required': self.merge_config['required_reviews']
            },
            'checks': {
                'total': len(status_checks),
                'passing': len([c for c in status_checks if c.conclusion == 'success']),
                'failing': len([c for c in status_checks if c.conclusion in ['failure', 'error']]),
                'pending': len([c for c in status_checks if c.status == 'pending'])
            },
            'labels': pr_info.labels
        }


def main():
    """CLI interface for PR merger"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Automated PR Merger')
    parser.add_argument('--token', help='GitHub token (or set GITHUB_TOKEN env var)')
    parser.add_argument('--repository', required=True, help='Repository in owner/repo format')
    parser.add_argument('--pr', type=int, help='PR number to merge')
    parser.add_argument('--auto-merge', action='store_true', help='Auto-merge all eligible PRs')
    parser.add_argument('--status', type=int, help='Get merge status for PR')
    parser.add_argument('--wait', action='store_true', help='Wait for conditions before merging')
    parser.add_argument('--timeout', type=int, default=30, help='Timeout in minutes for waiting')
    parser.add_argument('--method', choices=['merge', 'squash', 'rebase'], default='squash', help='Merge method')
    
    args = parser.parse_args()
    
    token = args.token or os.environ.get('GITHUB_TOKEN')
    if not token:
        print("Error: GitHub token required (--token or GITHUB_TOKEN env var)")
        return 1
    
    merger = PRMerger(token, args.repository)
    merger.configure_merge_settings(
        timeout_minutes=args.timeout,
        method=MergeMethod(args.method)
    )
    
    if args.status:
        status = merger.get_merge_status(args.status)
        print(json.dumps(status, indent=2))
    
    elif args.pr:
        if args.wait:
            success = merger.wait_and_merge(args.pr)
        else:
            can_merge, reasons = merger.check_merge_conditions(args.pr)
            if can_merge:
                success = merger.merge_pr(args.pr)
            else:
                print(f"Cannot merge PR #{args.pr}:")
                for reason in reasons:
                    print(f"  - {reason}")
                success = False
        
        return 0 if success else 1
    
    elif args.auto_merge:
        merged_prs = merger.auto_merge_prs()
        print(f"Merged {len(merged_prs)} PRs: {merged_prs}")
    
    else:
        print("Please specify --pr, --auto-merge, or --status")
        return 1
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())