#!/usr/bin/env python3
"""
Version Manager for Semantic Versioning

This module provides functionality for managing semantic versions according to semver.org.
It can read, increment, and validate version numbers in the format MAJOR.MINOR.PATCH.
"""

import re
import json
import os
from typing import Tuple, Optional, Dict, Any
from enum import Enum
from pathlib import Path


class VersionType(Enum):
    """Types of version increments"""
    MAJOR = "major"
    MINOR = "minor" 
    PATCH = "patch"
    PRERELEASE = "prerelease"


class VersionManager:
    """Manages semantic versioning for the project"""
    
    def __init__(self, version_file: str = "version.json"):
        self.version_file = Path(version_file)
        self.version_pattern = re.compile(
            r'^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)'
            r'(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)'
            r'(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?'
            r'(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
        )
    
    def get_current_version(self) -> str:
        """Get the current version from version file or initialize with 0.1.0"""
        if not self.version_file.exists():
            return self._initialize_version()
        
        try:
            with open(self.version_file, 'r') as f:
                data = json.load(f)
                return data.get('version', '0.1.0')
        except (json.JSONDecodeError, FileNotFoundError):
            return self._initialize_version()
    
    def _initialize_version(self) -> str:
        """Initialize version file with default version 0.1.0"""
        version = "0.1.0"
        self._save_version(version)
        return version
    
    def _save_version(self, version: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Save version to file with optional metadata"""
        data = {
            'version': version,
            'timestamp': self._get_timestamp(),
            'metadata': metadata or {}
        }
        
        with open(self.version_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'
    
    def parse_version(self, version: str) -> Dict[str, Any]:
        """Parse semantic version string into components"""
        match = self.version_pattern.match(version)
        if not match:
            raise ValueError(f"Invalid semantic version format: {version}")
        
        groups = match.groupdict()
        return {
            'major': int(groups['major']),
            'minor': int(groups['minor']),
            'patch': int(groups['patch']),
            'prerelease': groups.get('prerelease'),
            'buildmetadata': groups.get('buildmetadata')
        }
    
    def increment_version(self, version_type: VersionType, prerelease_suffix: str = None) -> str:
        """Increment version according to semantic versioning rules"""
        current = self.get_current_version()
        parsed = self.parse_version(current)
        
        if version_type == VersionType.MAJOR:
            parsed['major'] += 1
            parsed['minor'] = 0
            parsed['patch'] = 0
            parsed['prerelease'] = None
            
        elif version_type == VersionType.MINOR:
            parsed['minor'] += 1
            parsed['patch'] = 0
            parsed['prerelease'] = None
            
        elif version_type == VersionType.PATCH:
            parsed['patch'] += 1
            parsed['prerelease'] = None
            
        elif version_type == VersionType.PRERELEASE:
            if parsed['prerelease']:
                # Increment existing prerelease
                parts = parsed['prerelease'].split('.')
                if parts[-1].isdigit():
                    parts[-1] = str(int(parts[-1]) + 1)
                else:
                    parts.append('1')
                parsed['prerelease'] = '.'.join(parts)
            else:
                # Create new prerelease
                suffix = prerelease_suffix or 'alpha'
                parsed['prerelease'] = f"{suffix}.1"
        
        new_version = self._build_version_string(parsed)
        self._save_version(new_version, {'increment_type': version_type.value})
        
        return new_version
    
    def _build_version_string(self, parsed: Dict[str, Any]) -> str:
        """Build version string from parsed components"""
        version = f"{parsed['major']}.{parsed['minor']}.{parsed['patch']}"
        
        if parsed['prerelease']:
            version += f"-{parsed['prerelease']}"
        
        if parsed['buildmetadata']:
            version += f"+{parsed['buildmetadata']}"
            
        return version
    
    def is_valid_version(self, version: str) -> bool:
        """Check if version string is valid semantic version"""
        return bool(self.version_pattern.match(version))
    
    def compare_versions(self, version1: str, version2: str) -> int:
        """Compare two versions. Returns -1, 0, or 1"""
        if not (self.is_valid_version(version1) and self.is_valid_version(version2)):
            raise ValueError("Invalid version format for comparison")
        
        v1 = self.parse_version(version1)
        v2 = self.parse_version(version2)
        
        # Compare major, minor, patch
        for component in ['major', 'minor', 'patch']:
            if v1[component] < v2[component]:
                return -1
            elif v1[component] > v2[component]:
                return 1
        
        # Handle prerelease comparison
        pre1 = v1['prerelease']
        pre2 = v2['prerelease']
        
        if pre1 is None and pre2 is None:
            return 0
        elif pre1 is None:
            return 1  # version without prerelease > version with prerelease
        elif pre2 is None:
            return -1
        else:
            # Compare prereleases lexically
            if pre1 < pre2:
                return -1
            elif pre1 > pre2:
                return 1
            else:
                return 0
    
    def get_next_version(self, commit_messages: list, breaking_changes: bool = False) -> Tuple[str, VersionType]:
        """Determine next version based on commit messages and breaking changes"""
        current = self.get_current_version()
        
        # Check for breaking changes
        if breaking_changes:
            return self.increment_version(VersionType.MAJOR), VersionType.MAJOR
        
        # Check commit messages for conventional commits
        has_features = any(msg.startswith(('feat:', 'feature:')) for msg in commit_messages)
        has_fixes = any(msg.startswith(('fix:', 'bugfix:')) for msg in commit_messages)
        
        if has_features:
            return self.increment_version(VersionType.MINOR), VersionType.MINOR
        elif has_fixes:
            return self.increment_version(VersionType.PATCH), VersionType.PATCH
        else:
            # Default to patch increment
            return self.increment_version(VersionType.PATCH), VersionType.PATCH
    
    def set_version(self, version: str) -> None:
        """Manually set specific version"""
        if not self.is_valid_version(version):
            raise ValueError(f"Invalid semantic version: {version}")
        
        self._save_version(version, {'set_manually': True})
    
    def get_version_info(self) -> Dict[str, Any]:
        """Get detailed version information"""
        if not self.version_file.exists():
            return {'version': '0.1.0', 'initialized': False}
        
        try:
            with open(self.version_file, 'r') as f:
                data = json.load(f)
                data['initialized'] = True
                data['parsed'] = self.parse_version(data['version'])
                return data
        except (json.JSONDecodeError, FileNotFoundError):
            return {'version': '0.1.0', 'initialized': False}


def main():
    """CLI interface for version manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Semantic Version Manager')
    parser.add_argument('--get', action='store_true', help='Get current version')
    parser.add_argument('--increment', choices=['major', 'minor', 'patch', 'prerelease'], 
                       help='Increment version')
    parser.add_argument('--set', help='Set specific version')
    parser.add_argument('--validate', help='Validate version format')
    parser.add_argument('--compare', nargs=2, help='Compare two versions')
    parser.add_argument('--prerelease-suffix', default='alpha', help='Prerelease suffix')
    parser.add_argument('--version-file', default='version.json', help='Version file path')
    
    args = parser.parse_args()
    
    vm = VersionManager(args.version_file)
    
    if args.get:
        print(vm.get_current_version())
    
    elif args.increment:
        version_type = VersionType(args.increment)
        new_version = vm.increment_version(version_type, args.prerelease_suffix)
        print(f"Version incremented to: {new_version}")
    
    elif args.set:
        try:
            vm.set_version(args.set)
            print(f"Version set to: {args.set}")
        except ValueError as e:
            print(f"Error: {e}")
    
    elif args.validate:
        if vm.is_valid_version(args.validate):
            print(f"Valid semantic version: {args.validate}")
        else:
            print(f"Invalid semantic version: {args.validate}")
    
    elif args.compare:
        try:
            result = vm.compare_versions(args.compare[0], args.compare[1])
            if result < 0:
                print(f"{args.compare[0]} < {args.compare[1]}")
            elif result > 0:
                print(f"{args.compare[0]} > {args.compare[1]}")
            else:
                print(f"{args.compare[0]} == {args.compare[1]}")
        except ValueError as e:
            print(f"Error: {e}")
    
    else:
        # Show version info by default
        info = vm.get_version_info()
        print(f"Current version: {info['version']}")
        if 'timestamp' in info:
            print(f"Last updated: {info['timestamp']}")


if __name__ == '__main__':
    main()