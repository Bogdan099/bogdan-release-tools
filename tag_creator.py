#!/usr/bin/env python3
"""
Tag Creator for Automated Release Management

This module provides functionality for creating and managing git tags
for release automation, including annotated tags with signatures.
"""

import os
import subprocess
import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum


class TagType(Enum):
    """Types of git tags"""
    LIGHTWEIGHT = "lightweight"
    ANNOTATED = "annotated"
    SIGNED = "signed"


@dataclass
class TagInfo:
    """Information about a git tag"""
    name: str
    commit_hash: str
    message: Optional[str]
    tagger: Optional[str]
    date: Optional[str]
    tag_type: TagType
    is_signed: bool = False
    
    
class GitTagError(Exception):
    """Custom exception for git tag operations"""
    pass


class TagCreator:
    """Handles creation and management of git tags"""
    
    def __init__(self, repo_path: str = ".", remote_name: str = "origin"):
        self.repo_path = Path(repo_path)
        self.remote_name = remote_name
        self.version_pattern = re.compile(
            r'^v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)'
            r'(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)'
            r'(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?'
            r'(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
        )
    
    def _run_git_command(self, args: List[str], capture_output: bool = True, 
                        check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command with error handling"""
        try:
            cmd = ["git"] + args
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=capture_output,
                text=True,
                check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            raise GitTagError(f"Git command failed: {' '.join(cmd)}\n{e.stderr}")
        except FileNotFoundError:
            raise GitTagError("Git is not installed or not in PATH")
    
    def is_git_repository(self) -> bool:
        """Check if the current directory is a git repository"""
        try:
            self._run_git_command(["rev-parse", "--git-dir"])
            return True
        except GitTagError:
            return False
    
    def get_current_commit(self, ref: str = "HEAD") -> str:
        """Get the current commit hash"""
        result = self._run_git_command(["rev-parse", ref])
        return result.stdout.strip()
    
    def get_current_branch(self) -> str:
        """Get the current branch name"""
        result = self._run_git_command(["branch", "--show-current"])
        return result.stdout.strip()
    
    def tag_exists(self, tag_name: str) -> bool:
        """Check if a tag already exists"""
        try:
            self._run_git_command(["rev-parse", f"refs/tags/{tag_name}"])
            return True
        except GitTagError:
            return False
    
    def get_existing_tags(self, pattern: Optional[str] = None) -> List[str]:
        """Get list of existing tags, optionally filtered by pattern"""
        try:
            args = ["tag", "--list"]
            if pattern:
                args.append(pattern)
            
            result = self._run_git_command(args)
            tags = [tag.strip() for tag in result.stdout.split('\n') if tag.strip()]
            return sorted(tags, reverse=True)
        except GitTagError:
            return []
    
    def get_latest_version_tag(self, prefix: str = "v") -> Optional[str]:
        """Get the latest version tag"""
        tags = self.get_existing_tags(f"{prefix}*")
        
        version_tags = []
        for tag in tags:
            if self.version_pattern.match(tag):
                version_tags.append(tag)
        
        if not version_tags:
            return None
        
        # Sort by semantic version
        def version_key(tag):
            match = self.version_pattern.match(tag)
            if match:
                groups = match.groupdict()
                return (
                    int(groups['major']),
                    int(groups['minor']),
                    int(groups['patch']),
                    groups.get('prerelease', '') == '',  # Stable versions first
                    groups.get('prerelease', '')
                )
            return (0, 0, 0, False, '')
        
        version_tags.sort(key=version_key, reverse=True)
        return version_tags[0]
    
    def get_tag_info(self, tag_name: str) -> Optional[TagInfo]:
        """Get detailed information about a tag"""
        if not self.tag_exists(tag_name):
            return None
        
        try:
            # Get tag object type
            result = self._run_git_command(["cat-file", "-t", tag_name])
            object_type = result.stdout.strip()
            
            if object_type == "tag":
                # Annotated tag
                result = self._run_git_command(["cat-file", "-p", tag_name])
                tag_content = result.stdout
                
                lines = tag_content.split('\n')
                commit_hash = ""
                tagger = ""
                date = ""
                message_lines = []
                in_message = False
                
                for line in lines:
                    if line.startswith("object "):
                        commit_hash = line.split()[1]
                    elif line.startswith("tagger "):
                        # Parse tagger line: "tagger Name <email> timestamp timezone"
                        parts = line[7:].rsplit(' ', 2)
                        if len(parts) >= 3:
                            tagger = parts[0]
                            timestamp = parts[1]
                            date = datetime.fromtimestamp(int(timestamp)).isoformat()
                    elif line == "":
                        in_message = True
                    elif in_message:
                        message_lines.append(line)
                
                # Check if signed
                is_signed = "-----BEGIN PGP SIGNATURE-----" in tag_content
                
                return TagInfo(
                    name=tag_name,
                    commit_hash=commit_hash,
                    message='\n'.join(message_lines).strip(),
                    tagger=tagger,
                    date=date,
                    tag_type=TagType.SIGNED if is_signed else TagType.ANNOTATED,
                    is_signed=is_signed
                )
            else:
                # Lightweight tag
                commit_hash = self.get_current_commit(tag_name)
                return TagInfo(
                    name=tag_name,
                    commit_hash=commit_hash,
                    message=None,
                    tagger=None,
                    date=None,
                    tag_type=TagType.LIGHTWEIGHT
                )
                
        except GitTagError:
            return None
    
    def create_lightweight_tag(self, tag_name: str, commit: str = "HEAD") -> bool:
        """Create a lightweight tag"""
        if self.tag_exists(tag_name):
            raise GitTagError(f"Tag '{tag_name}' already exists")
        
        try:
            self._run_git_command(["tag", tag_name, commit])
            print(f"Created lightweight tag: {tag_name}")
            return True
        except GitTagError as e:
            print(f"Failed to create lightweight tag: {e}")
            return False
    
    def create_annotated_tag(self, tag_name: str, message: str, 
                           commit: str = "HEAD", sign: bool = False) -> bool:
        """Create an annotated tag with a message"""
        if self.tag_exists(tag_name):
            raise GitTagError(f"Tag '{tag_name}' already exists")
        
        try:
            args = ["tag", "-a"]
            
            if sign:
                args.append("-s")
            
            args.extend(["-m", message, tag_name, commit])
            
            self._run_git_command(args)
            tag_type = "signed annotated" if sign else "annotated"
            print(f"Created {tag_type} tag: {tag_name}")
            return True
            
        except GitTagError as e:
            print(f"Failed to create annotated tag: {e}")
            return False
    
    def create_version_tag(self, version: str, message: Optional[str] = None,
                          prefix: str = "v", sign: bool = False, 
                          commit: str = "HEAD") -> bool:
        """Create a version tag with semantic versioning"""
        # Validate version format
        if not self.version_pattern.match(f"{prefix}{version}"):
            raise GitTagError(f"Invalid semantic version format: {version}")
        
        tag_name = f"{prefix}{version}"
        
        if not message:
            message = f"Release {version}"
        
        return self.create_annotated_tag(tag_name, message, commit, sign)
    
    def delete_tag(self, tag_name: str, remote: bool = False) -> bool:
        """Delete a tag locally and optionally from remote"""
        try:
            # Delete local tag
            if self.tag_exists(tag_name):
                self._run_git_command(["tag", "-d", tag_name])
                print(f"Deleted local tag: {tag_name}")
            
            # Delete remote tag
            if remote:
                try:
                    self._run_git_command(["push", self.remote_name, f":refs/tags/{tag_name}"])
                    print(f"Deleted remote tag: {tag_name}")
                except GitTagError as e:
                    print(f"Warning: Could not delete remote tag: {e}")
            
            return True
            
        except GitTagError as e:
            print(f"Failed to delete tag: {e}")
            return False
    
    def push_tag(self, tag_name: str) -> bool:
        """Push a tag to remote repository"""
        if not self.tag_exists(tag_name):
            raise GitTagError(f"Tag '{tag_name}' does not exist")
        
        try:
            self._run_git_command(["push", self.remote_name, tag_name])
            print(f"Pushed tag to remote: {tag_name}")
            return True
        except GitTagError as e:
            print(f"Failed to push tag: {e}")
            return False
    
    def push_all_tags(self) -> bool:
        """Push all tags to remote repository"""
        try:
            self._run_git_command(["push", self.remote_name, "--tags"])
            print("Pushed all tags to remote")
            return True
        except GitTagError as e:
            print(f"Failed to push tags: {e}")
            return False
    
    def get_commits_since_tag(self, tag_name: str, until: str = "HEAD") -> List[Dict[str, str]]:
        """Get commits since a specific tag"""
        if not self.tag_exists(tag_name):
            raise GitTagError(f"Tag '{tag_name}' does not exist")
        
        try:
            result = self._run_git_command([
                "log", "--pretty=format:%H|%an|%ai|%s", 
                f"{tag_name}..{until}"
            ])
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 3)
                    if len(parts) >= 4:
                        commits.append({
                            'hash': parts[0],
                            'author': parts[1],
                            'date': parts[2],
                            'message': parts[3]
                        })
            
            return commits
            
        except GitTagError:
            return []
    
    def create_release_tag(self, version: str, changelog: Optional[str] = None,
                          auto_push: bool = True, sign: bool = True) -> bool:
        """Create a complete release tag with changelog"""
        # Ensure we're in a clean state
        if not self.is_git_repository():
            raise GitTagError("Not in a git repository")
        
        # Check if there are uncommitted changes
        try:
            result = self._run_git_command(["status", "--porcelain"])
            if result.stdout.strip():
                print("Warning: There are uncommitted changes")
        except GitTagError:
            pass
        
        # Get current branch
        current_branch = self.get_current_branch()
        print(f"Creating release tag on branch: {current_branch}")
        
        # Create tag message
        if not changelog:
            # Get commits since last version tag
            last_tag = self.get_latest_version_tag()
            if last_tag:
                commits = self.get_commits_since_tag(last_tag)
                if commits:
                    changelog = "Changes in this release:\n\n"
                    for commit in commits[:10]:  # Limit to 10 commits
                        changelog += f"- {commit['message']} ({commit['hash'][:7]})\n"
                    if len(commits) > 10:
                        changelog += f"... and {len(commits) - 10} more commits"
                else:
                    changelog = "No changes since last release"
            else:
                changelog = "Initial release"
        
        tag_message = f"Release {version}\n\n{changelog}"
        
        # Create the tag
        success = self.create_version_tag(version, tag_message, sign=sign)
        
        if success and auto_push:
            tag_name = f"v{version}"
            self.push_tag(tag_name)
        
        return success
    
    def validate_tag_name(self, tag_name: str) -> Tuple[bool, str]:
        """Validate tag name according to git rules"""
        # Git tag name rules
        invalid_patterns = [
            r'\.\.', r'\.$', r'/$', r'\.lock$', r'^\.', r'[@{~^:\\\*\?\[]'
        ]
        
        if not tag_name:
            return False, "Tag name cannot be empty"
        
        if tag_name.startswith('-'):
            return False, "Tag name cannot start with hyphen"
        
        if '//' in tag_name:
            return False, "Tag name cannot contain consecutive slashes"
        
        for pattern in invalid_patterns:
            if re.search(pattern, tag_name):
                return False, f"Tag name contains invalid characters: {pattern}"
        
        # Check for control characters
        if any(ord(c) < 32 for c in tag_name):
            return False, "Tag name contains control characters"
        
        return True, "Valid tag name"
    
    def get_tag_statistics(self) -> Dict[str, Any]:
        """Get statistics about repository tags"""
        tags = self.get_existing_tags()
        
        version_tags = []
        other_tags = []
        
        for tag in tags:
            if self.version_pattern.match(tag):
                version_tags.append(tag)
            else:
                other_tags.append(tag)
        
        latest_version = self.get_latest_version_tag()
        
        stats = {
            'total_tags': len(tags),
            'version_tags': len(version_tags),
            'other_tags': len(other_tags),
            'latest_version_tag': latest_version,
            'all_tags': tags[:10],  # First 10 tags
        }
        
        if latest_version:
            commits_since = self.get_commits_since_tag(latest_version)
            stats['commits_since_latest'] = len(commits_since)
        
        return stats


def main():
    """CLI interface for tag creator"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Git Tag Creator')
    parser.add_argument('--repo-path', default='.', help='Repository path')
    parser.add_argument('--remote', default='origin', help='Remote name')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Create tag
    create_parser = subparsers.add_parser('create', help='Create a tag')
    create_parser.add_argument('name', help='Tag name')
    create_parser.add_argument('--message', help='Tag message (for annotated tags)')
    create_parser.add_argument('--commit', default='HEAD', help='Commit to tag')
    create_parser.add_argument('--lightweight', action='store_true', help='Create lightweight tag')
    create_parser.add_argument('--sign', action='store_true', help='Sign the tag')
    create_parser.add_argument('--push', action='store_true', help='Push tag after creation')
    
    # Create version tag
    version_parser = subparsers.add_parser('version', help='Create version tag')
    version_parser.add_argument('version', help='Version number (e.g., 1.0.0)')
    version_parser.add_argument('--message', help='Release message')
    version_parser.add_argument('--prefix', default='v', help='Tag prefix')
    version_parser.add_argument('--sign', action='store_true', help='Sign the tag')
    version_parser.add_argument('--push', action='store_true', help='Push tag after creation')
    
    # Release tag
    release_parser = subparsers.add_parser('release', help='Create release tag with changelog')
    release_parser.add_argument('version', help='Version number')
    release_parser.add_argument('--changelog', help='Changelog content')
    release_parser.add_argument('--no-push', action='store_true', help='Do not push tag')
    release_parser.add_argument('--no-sign', action='store_true', help='Do not sign tag')
    
    # List tags
    list_parser = subparsers.add_parser('list', help='List tags')
    list_parser.add_argument('--pattern', help='Filter pattern')
    list_parser.add_argument('--info', action='store_true', help='Show detailed info')
    
    # Delete tag
    delete_parser = subparsers.add_parser('delete', help='Delete a tag')
    delete_parser.add_argument('name', help='Tag name to delete')
    delete_parser.add_argument('--remote', action='store_true', help='Also delete from remote')
    
    # Push tags
    push_parser = subparsers.add_parser('push', help='Push tags')
    push_parser.add_argument('name', nargs='?', help='Specific tag name (or all if omitted)')
    
    # Statistics
    subparsers.add_parser('stats', help='Show tag statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        creator = TagCreator(args.repo_path, args.remote)
        
        if args.command == 'create':
            # Validate tag name
            is_valid, message = creator.validate_tag_name(args.name)
            if not is_valid:
                print(f"Invalid tag name: {message}")
                return 1
            
            if args.lightweight:
                success = creator.create_lightweight_tag(args.name, args.commit)
            else:
                message = args.message or f"Tag {args.name}"
                success = creator.create_annotated_tag(args.name, message, args.commit, args.sign)
            
            if success and args.push:
                creator.push_tag(args.name)
        
        elif args.command == 'version':
            message = args.message
            success = creator.create_version_tag(args.version, message, args.prefix, args.sign)
            
            if success and args.push:
                tag_name = f"{args.prefix}{args.version}"
                creator.push_tag(tag_name)
        
        elif args.command == 'release':
            success = creator.create_release_tag(
                args.version, 
                args.changelog,
                auto_push=not args.no_push,
                sign=not args.no_sign
            )
        
        elif args.command == 'list':
            tags = creator.get_existing_tags(args.pattern)
            if args.info:
                for tag in tags[:10]:  # Limit to 10 for detailed info
                    info = creator.get_tag_info(tag)
                    if info:
                        print(f"\nTag: {info.name}")
                        print(f"  Type: {info.tag_type.value}")
                        print(f"  Commit: {info.commit_hash[:7]}")
                        if info.tagger:
                            print(f"  Tagger: {info.tagger}")
                        if info.date:
                            print(f"  Date: {info.date}")
                        if info.message:
                            print(f"  Message: {info.message[:100]}...")
            else:
                for tag in tags:
                    print(tag)
        
        elif args.command == 'delete':
            success = creator.delete_tag(args.name, args.remote)
        
        elif args.command == 'push':
            if args.name:
                success = creator.push_tag(args.name)
            else:
                success = creator.push_all_tags()
        
        elif args.command == 'stats':
            stats = creator.get_tag_statistics()
            print(f"Repository Tag Statistics:")
            print(f"  Total tags: {stats['total_tags']}")
            print(f"  Version tags: {stats['version_tags']}")
            print(f"  Other tags: {stats['other_tags']}")
            print(f"  Latest version: {stats.get('latest_version_tag', 'None')}")
            if 'commits_since_latest' in stats:
                print(f"  Commits since latest: {stats['commits_since_latest']}")
        
        return 0
        
    except GitTagError as e:
        print(f"Error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\nOperation cancelled")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())