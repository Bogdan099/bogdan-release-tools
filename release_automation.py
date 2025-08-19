#!/usr/bin/env python3
"""
Release Automation Pipeline

This is the main script that orchestrates the complete release automation process,
integrating all components: version management, changelog generation, PR merging,
tag creation, and GitHub release publishing.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Import our release automation components
from version_manager import VersionManager, VersionType
from changelog_generator import ChangelogGenerator
from pr_merger import PRMerger
from tag_creator import TagCreator
from release_publisher import ReleasePublisher, Release, ReleaseAsset


class ReleaseAutomationError(Exception):
    """Custom exception for release automation operations"""
    pass


class ReleaseAutomation:
    """Main class orchestrating the complete release automation pipeline"""
    
    def __init__(self, config_file: str = "release_config.json"):
        self.config_file = Path(config_file)
        self.config = self._load_config()
        
        # Initialize components
        self.version_manager = VersionManager(self.config.get('version_file', 'version.json'))
        self.changelog_generator = ChangelogGenerator(
            repo_path=self.config.get('repo_path', '.'),
            changelog_file=self.config.get('changelog_file', 'CHANGELOG.md')
        )
        
        # GitHub components require token
        github_token = self.config.get('github_token') or os.environ.get('GITHUB_TOKEN')
        if github_token and self.config.get('repository'):
            self.pr_merger = PRMerger(github_token, self.config['repository'])
            self.release_publisher = ReleasePublisher(github_token, self.config['repository'])
            
            # Configure PR merger settings
            self.pr_merger.configure_merge_settings(**self.config.get('pr_merge_settings', {}))
        else:
            self.pr_merger = None
            self.release_publisher = None
        
        self.tag_creator = TagCreator(
            repo_path=self.config.get('repo_path', '.'),
            remote_name=self.config.get('remote_name', 'origin')
        )
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        # Default configuration
        default_config = {
            "version_file": "version.json",
            "changelog_file": "CHANGELOG.md",
            "repo_path": ".",
            "remote_name": "origin",
            "repository": "",
            "github_token": "",
            "release_settings": {
                "tag_prefix": "v",
                "create_tag": True,
                "push_tag": True,
                "create_github_release": True,
                "sign_tags": False,
                "delete_branch_after_merge": True,
                "target_branch": "main"
            },
            "pr_merge_settings": {
                "method": "squash",
                "required_reviews": 1,
                "required_status_checks": [],
                "auto_merge_labels": ["ready-to-merge"],
                "blocked_labels": ["do-not-merge", "wip"],
                "target_branches": ["main", "master"],
                "timeout_minutes": 30
            },
            "assets": []
        }
        
        # Save default config
        self._save_config(default_config)
        return default_config
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def create_release(self, version_type: str, **kwargs) -> Dict[str, Any]:
        """Create a complete release with all steps"""
        print(f"🚀 Starting release automation for {version_type} version...")
        
        results = {
            'success': False,
            'version': None,
            'steps_completed': [],
            'errors': []
        }
        
        try:
            # Step 1: Determine new version
            print("📊 Step 1: Version Management")
            current_version = self.version_manager.get_current_version()
            print(f"Current version: {current_version}")
            
            # Get commit messages for version determination
            last_tag = self.changelog_generator.get_last_tag()
            commits = self.changelog_generator.get_git_commits(since_tag=last_tag)
            commit_messages = [commit.message for commit in commits]
            
            # Determine version type if not specified
            if version_type == 'auto':
                breaking_changes = kwargs.get('breaking_changes', False)
                new_version, detected_type = self.version_manager.get_next_version(
                    commit_messages, breaking_changes
                )
                print(f"Auto-detected version type: {detected_type.value}")
            else:
                version_enum = VersionType(version_type)
                new_version = self.version_manager.increment_version(version_enum)
            
            results['version'] = new_version
            results['steps_completed'].append('version_increment')
            print(f"New version: {new_version}")
            
            # Step 2: Generate changelog
            print("\n📝 Step 2: Changelog Generation")
            self.changelog_generator.update_changelog(new_version, commits)
            results['steps_completed'].append('changelog_update')
            print("Changelog updated")
            
            # Step 3: Create git tag
            if self.config['release_settings']['create_tag']:
                print("\n🏷️ Step 3: Tag Creation")
                tag_message = f"Release {new_version}"
                success = self.tag_creator.create_version_tag(
                    new_version,
                    message=tag_message,
                    prefix=self.config['release_settings']['tag_prefix'],
                    sign=self.config['release_settings']['sign_tags']
                )
                
                if success:
                    results['steps_completed'].append('tag_creation')
                    
                    # Push tag if configured
                    if self.config['release_settings']['push_tag']:
                        tag_name = f"{self.config['release_settings']['tag_prefix']}{new_version}"
                        self.tag_creator.push_tag(tag_name)
                        results['steps_completed'].append('tag_push')
                        print("Tag pushed to remote")
                else:
                    results['errors'].append("Failed to create git tag")
            
            # Step 4: Create GitHub release
            if (self.config['release_settings']['create_github_release'] and 
                self.release_publisher):
                print("\n📦 Step 4: GitHub Release Publishing")
                
                # Prepare release notes
                release_notes = self.changelog_generator.generate_release_notes(new_version, commits)
                
                # Prepare assets
                assets = []
                for asset_config in self.config.get('assets', []):
                    asset_path = Path(asset_config['path'])
                    if asset_path.exists():
                        assets.append(ReleaseAsset(
                            file_path=asset_path,
                            name=asset_config.get('name'),
                            label=asset_config.get('label')
                        ))
                
                # Create release
                tag_name = f"{self.config['release_settings']['tag_prefix']}{new_version}"
                release_data = self.release_publisher.create_release_from_tag(
                    tag_name=tag_name,
                    name=f"Release {new_version}",
                    body=release_notes,
                    draft=kwargs.get('draft', False),
                    prerelease=kwargs.get('prerelease', False),
                    assets=assets
                )
                
                if release_data:
                    results['steps_completed'].append('github_release')
                    results['release_url'] = release_data['html_url']
                    print(f"GitHub release created: {release_data['html_url']}")
                else:
                    results['errors'].append("Failed to create GitHub release")
            
            # Step 5: Auto-merge PRs if configured
            if kwargs.get('auto_merge_prs', False) and self.pr_merger:
                print("\n🔄 Step 5: Auto-merge Pull Requests")
                merged_prs = self.pr_merger.auto_merge_prs()
                if merged_prs:
                    results['merged_prs'] = merged_prs
                    results['steps_completed'].append('pr_auto_merge')
                    print(f"Auto-merged PRs: {merged_prs}")
            
            results['success'] = True
            print(f"\n✅ Release automation completed successfully!")
            print(f"🎉 Released version {new_version}")
            
        except Exception as e:
            results['errors'].append(str(e))
            print(f"\n❌ Release automation failed: {e}")
        
        return results
    
    def prepare_release(self, pr_number: Optional[int] = None) -> Dict[str, Any]:
        """Prepare for release by merging PRs and checking status"""
        print("🔍 Preparing for release...")
        
        results = {
            'ready_for_release': False,
            'checks': {},
            'errors': []
        }
        
        try:
            if not self.pr_merger:
                results['errors'].append("PR merger not configured (missing GitHub token or repository)")
                return results
            
            # Check specific PR or all auto-merge PRs
            if pr_number:
                print(f"Checking PR #{pr_number}")
                can_merge, reasons = self.pr_merger.check_merge_conditions(pr_number)
                
                results['checks'][f'pr_{pr_number}'] = {
                    'can_merge': can_merge,
                    'reasons': reasons
                }
                
                if can_merge:
                    success = self.pr_merger.merge_pr(pr_number)
                    results['checks'][f'pr_{pr_number}']['merged'] = success
            else:
                print("Checking all auto-merge PRs")
                merged_prs = self.pr_merger.auto_merge_prs()
                results['merged_prs'] = merged_prs
            
            # Check repository status
            last_tag = self.changelog_generator.get_last_tag()
            commits_since_last = self.changelog_generator.get_git_commits(since_tag=last_tag)
            
            results['checks']['repository'] = {
                'last_tag': last_tag,
                'commits_since_last': len(commits_since_last),
                'uncommitted_changes': self._check_uncommitted_changes()
            }
            
            # Determine if ready for release
            has_new_commits = len(commits_since_last) > 0
            no_blocking_issues = len(results['errors']) == 0
            
            results['ready_for_release'] = has_new_commits and no_blocking_issues
            
            if results['ready_for_release']:
                print("✅ Repository is ready for release")
            else:
                print("⚠️ Repository not ready for release")
                if not has_new_commits:
                    print("  - No new commits since last release")
                if not no_blocking_issues:
                    print("  - Blocking issues found")
            
        except Exception as e:
            results['errors'].append(str(e))
        
        return results
    
    def _check_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes"""
        try:
            result = self.tag_creator._run_git_command(["status", "--porcelain"])
            return bool(result.stdout.strip())
        except:
            return False
    
    def get_release_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the release automation system"""
        status = {
            'version_info': self.version_manager.get_version_info(),
            'tag_statistics': self.tag_creator.get_tag_statistics(),
            'config': self.config,
            'components': {
                'version_manager': True,
                'changelog_generator': True,
                'tag_creator': True,
                'pr_merger': self.pr_merger is not None,
                'release_publisher': self.release_publisher is not None
            }
        }
        
        if self.release_publisher:
            try:
                status['release_statistics'] = self.release_publisher.get_release_statistics()
            except:
                status['release_statistics'] = {'error': 'Could not fetch release statistics'}
        
        return status


def main():
    """CLI interface for release automation"""
    parser = argparse.ArgumentParser(description='Release Automation Pipeline')
    parser.add_argument('--config', default='release_config.json', help='Configuration file')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Release command
    release_parser = subparsers.add_parser('release', help='Create a complete release')
    release_parser.add_argument('version_type', 
                               choices=['major', 'minor', 'patch', 'prerelease', 'auto'],
                               help='Version increment type')
    release_parser.add_argument('--breaking-changes', action='store_true', 
                               help='Mark as breaking changes (for auto version)')
    release_parser.add_argument('--draft', action='store_true', help='Create as draft release')
    release_parser.add_argument('--prerelease', action='store_true', help='Mark as prerelease')
    release_parser.add_argument('--auto-merge-prs', action='store_true', help='Auto-merge PRs')
    
    # Prepare command  
    prepare_parser = subparsers.add_parser('prepare', help='Prepare for release')
    prepare_parser.add_argument('--pr', type=int, help='Specific PR to check/merge')
    
    # Status command
    subparsers.add_parser('status', help='Show release automation status')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Configuration management')
    config_parser.add_argument('--init', action='store_true', help='Initialize configuration')
    config_parser.add_argument('--show', action='store_true', help='Show current configuration')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        automation = ReleaseAutomation(args.config)
        
        if args.command == 'release':
            results = automation.create_release(
                version_type=args.version_type,
                breaking_changes=args.breaking_changes,
                draft=args.draft,
                prerelease=args.prerelease,
                auto_merge_prs=args.auto_merge_prs
            )
            
            print(f"\nRelease Results:")
            print(f"Success: {results['success']}")
            print(f"Version: {results['version']}")
            print(f"Steps completed: {', '.join(results['steps_completed'])}")
            
            if results['errors']:
                print(f"Errors: {', '.join(results['errors'])}")
            
            if 'release_url' in results:
                print(f"Release URL: {results['release_url']}")
            
            return 0 if results['success'] else 1
        
        elif args.command == 'prepare':
            results = automation.prepare_release(args.pr)
            
            print(f"Ready for release: {results['ready_for_release']}")
            
            if results['errors']:
                print(f"Errors: {', '.join(results['errors'])}")
            
            print(json.dumps(results, indent=2, default=str))
        
        elif args.command == 'status':
            status = automation.get_release_status()
            print(json.dumps(status, indent=2, default=str))
        
        elif args.command == 'config':
            if args.init:
                print(f"Configuration initialized: {automation.config_file}")
            elif args.show:
                print(json.dumps(automation.config, indent=2, ensure_ascii=False))
            else:
                print(f"Configuration file: {automation.config_file}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())