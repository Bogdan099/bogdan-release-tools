#!/usr/bin/env python3
"""
Release Publisher for Automated Release Management

This module provides functionality for publishing GitHub releases
with assets, release notes, and proper versioning.
"""

import os
import json
import requests
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
import mimetypes


@dataclass
class ReleaseAsset:
    """Represents a release asset to upload"""
    file_path: Union[str, Path]
    name: Optional[str] = None
    label: Optional[str] = None
    content_type: Optional[str] = None
    
    def __post_init__(self):
        self.file_path = Path(self.file_path)
        if not self.name:
            self.name = self.file_path.name
        if not self.content_type:
            self.content_type, _ = mimetypes.guess_type(str(self.file_path))
            if not self.content_type:
                self.content_type = 'application/octet-stream'


@dataclass
class Release:
    """Represents a GitHub release"""
    tag_name: str
    name: Optional[str] = None
    body: str = ""
    draft: bool = False
    prerelease: bool = False
    target_commitish: str = "main"
    assets: List[ReleaseAsset] = field(default_factory=list)
    generate_release_notes: bool = False
    
    def __post_init__(self):
        if not self.name:
            self.name = self.tag_name


class GitHubReleaseError(Exception):
    """Custom exception for GitHub release operations"""
    pass


class ReleasePublisher:
    """Handles publishing GitHub releases"""
    
    def __init__(self, github_token: str, repository: str, base_url: str = "https://api.github.com"):
        self.github_token = github_token
        self.repository = repository  # format: "owner/repo"
        self.base_url = base_url
        self.upload_url = "https://uploads.github.com"
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Release-Publisher/1.0'
        })
    
    def get_release(self, tag_name: str) -> Optional[Dict[str, Any]]:
        """Get an existing release by tag name"""
        try:
            url = f"{self.base_url}/repos/{self.repository}/releases/tags/{tag_name}"
            response = self.session.get(url)
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            print(f"Error getting release: {e}")
            return None
    
    def list_releases(self, per_page: int = 30, page: int = 1) -> List[Dict[str, Any]]:
        """List repository releases"""
        try:
            url = f"{self.base_url}/repos/{self.repository}/releases"
            params = {'per_page': per_page, 'page': page}
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            print(f"Error listing releases: {e}")
            return []
    
    def get_latest_release(self, include_prereleases: bool = False) -> Optional[Dict[str, Any]]:
        """Get the latest release"""
        if include_prereleases:
            releases = self.list_releases(per_page=1)
            return releases[0] if releases else None
        
        try:
            url = f"{self.base_url}/repos/{self.repository}/releases/latest"
            response = self.session.get(url)
            
            if response.status_code == 404:
                return None
                
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            print(f"Error getting latest release: {e}")
            return None
    
    def create_release(self, release: Release) -> Optional[Dict[str, Any]]:
        """Create a new GitHub release"""
        try:
            # Check if release already exists
            existing = self.get_release(release.tag_name)
            if existing:
                print(f"Release {release.tag_name} already exists")
                return existing
            
            url = f"{self.base_url}/repos/{self.repository}/releases"
            data = {
                'tag_name': release.tag_name,
                'name': release.name,
                'body': release.body,
                'draft': release.draft,
                'prerelease': release.prerelease,
                'target_commitish': release.target_commitish,
                'generate_release_notes': release.generate_release_notes
            }
            
            response = self.session.post(url, json=data)
            response.raise_for_status()
            
            release_data = response.json()
            print(f"Created release: {release.tag_name}")
            
            # Upload assets if provided
            if release.assets:
                self.upload_assets(release_data['id'], release.assets)
            
            return release_data
            
        except requests.RequestException as e:
            error_msg = f"Error creating release: {e}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    error_msg += f"\nDetails: {error_details}"
                except:
                    error_msg += f"\nResponse: {e.response.text}"
            raise GitHubReleaseError(error_msg)
    
    def update_release(self, release_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """Update an existing release"""
        try:
            url = f"{self.base_url}/repos/{self.repository}/releases/{release_id}"
            
            response = self.session.patch(url, json=kwargs)
            response.raise_for_status()
            
            print(f"Updated release: {release_id}")
            return response.json()
            
        except requests.RequestException as e:
            print(f"Error updating release: {e}")
            return None
    
    def delete_release(self, release_id: int) -> bool:
        """Delete a release"""
        try:
            url = f"{self.base_url}/repos/{self.repository}/releases/{release_id}"
            
            response = self.session.delete(url)
            response.raise_for_status()
            
            print(f"Deleted release: {release_id}")
            return True
            
        except requests.RequestException as e:
            print(f"Error deleting release: {e}")
            return False
    
    def upload_asset(self, release_id: int, asset: ReleaseAsset) -> Optional[Dict[str, Any]]:
        """Upload a single asset to a release"""
        if not asset.file_path.exists():
            raise GitHubReleaseError(f"Asset file not found: {asset.file_path}")
        
        try:
            # Get upload URL for the release
            url = f"{self.base_url}/repos/{self.repository}/releases/{release_id}"
            response = self.session.get(url)
            response.raise_for_status()
            
            upload_url = response.json()['upload_url']
            # Remove the {?name,label} template from the URL
            upload_url = upload_url.split('{')[0]
            
            # Prepare upload parameters
            params = {'name': asset.name}
            if asset.label:
                params['label'] = asset.label
            
            # Calculate file hash for integrity
            file_hash = self._calculate_file_hash(asset.file_path)
            
            # Upload the asset
            with open(asset.file_path, 'rb') as f:
                headers = {
                    'Authorization': f'token {self.github_token}',
                    'Content-Type': asset.content_type,
                    'Accept': 'application/vnd.github.v3+json'
                }
                
                upload_response = requests.post(
                    upload_url,
                    params=params,
                    headers=headers,
                    data=f
                )
                upload_response.raise_for_status()
            
            asset_data = upload_response.json()
            print(f"Uploaded asset: {asset.name} ({asset_data['size']} bytes)")
            print(f"File SHA256: {file_hash}")
            
            return asset_data
            
        except requests.RequestException as e:
            error_msg = f"Error uploading asset {asset.name}: {e}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f"\nResponse: {e.response.text}"
            raise GitHubReleaseError(error_msg)
    
    def upload_assets(self, release_id: int, assets: List[ReleaseAsset]) -> List[Dict[str, Any]]:
        """Upload multiple assets to a release"""
        uploaded_assets = []
        
        for asset in assets:
            try:
                asset_data = self.upload_asset(release_id, asset)
                if asset_data:
                    uploaded_assets.append(asset_data)
            except GitHubReleaseError as e:
                print(f"Failed to upload asset {asset.name}: {e}")
        
        return uploaded_assets
    
    def delete_asset(self, asset_id: int) -> bool:
        """Delete a release asset"""
        try:
            url = f"{self.base_url}/repos/{self.repository}/releases/assets/{asset_id}"
            
            response = self.session.delete(url)
            response.raise_for_status()
            
            print(f"Deleted asset: {asset_id}")
            return True
            
        except requests.RequestException as e:
            print(f"Error deleting asset: {e}")
            return False
    
    def _calculate_file_hash(self, file_path: Path, algorithm: str = "sha256") -> str:
        """Calculate hash of a file"""
        hash_obj = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    
    def generate_release_notes_from_commits(self, tag_name: str, previous_tag: Optional[str] = None) -> str:
        """Generate release notes from commit history (requires git)"""
        try:
            import subprocess
            
            if previous_tag:
                cmd = ["git", "log", f"{previous_tag}..{tag_name}", "--pretty=format:- %s (%h)"]
            else:
                cmd = ["git", "log", tag_name, "--pretty=format:- %s (%h)", "--max-count=50"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if result.stdout.strip():
                return f"## Changes\n\n{result.stdout}"
            else:
                return "No changes in this release."
                
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "Release notes could not be generated automatically."
    
    def create_release_from_tag(self, tag_name: str, name: Optional[str] = None,
                               body: Optional[str] = None, draft: bool = False,
                               prerelease: bool = False, assets: Optional[List[ReleaseAsset]] = None) -> Optional[Dict[str, Any]]:
        """Create a release from an existing git tag"""
        # Determine if this is a prerelease based on version
        if prerelease is False:  # Only auto-detect if not explicitly set
            prerelease = self._is_prerelease_version(tag_name)
        
        # Generate release notes if not provided
        if not body:
            latest_release = self.get_latest_release()
            previous_tag = latest_release['tag_name'] if latest_release else None
            body = self.generate_release_notes_from_commits(tag_name, previous_tag)
        
        release = Release(
            tag_name=tag_name,
            name=name or tag_name,
            body=body,
            draft=draft,
            prerelease=prerelease,
            assets=assets or []
        )
        
        return self.create_release(release)
    
    def _is_prerelease_version(self, version: str) -> bool:
        """Determine if version string indicates a prerelease"""
        prerelease_indicators = [
            'alpha', 'beta', 'rc', 'pre', 'dev', 'snapshot',
            '-alpha', '-beta', '-rc', '-pre', '-dev'
        ]
        
        version_lower = version.lower()
        return any(indicator in version_lower for indicator in prerelease_indicators)
    
    def publish_draft_release(self, release_id: int) -> Optional[Dict[str, Any]]:
        """Publish a draft release"""
        return self.update_release(release_id, draft=False)
    
    def create_assets_archive(self, assets: List[Path], archive_name: str = "release-assets.zip") -> Path:
        """Create a ZIP archive of multiple assets"""
        import zipfile
        
        archive_path = Path(archive_name)
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for asset_path in assets:
                if asset_path.exists():
                    if asset_path.is_file():
                        zipf.write(asset_path, asset_path.name)
                    elif asset_path.is_dir():
                        for file_path in asset_path.rglob('*'):
                            if file_path.is_file():
                                zipf.write(file_path, file_path.relative_to(asset_path.parent))
        
        print(f"Created assets archive: {archive_path}")
        return archive_path
    
    def get_release_statistics(self) -> Dict[str, Any]:
        """Get statistics about releases"""
        releases = self.list_releases(per_page=100)
        
        stats = {
            'total_releases': len(releases),
            'draft_releases': len([r for r in releases if r['draft']]),
            'prereleases': len([r for r in releases if r['prerelease']]),
            'releases_with_assets': len([r for r in releases if r['assets']]),
            'total_downloads': sum(sum(asset['download_count'] for asset in r['assets']) for r in releases),
            'latest_release': releases[0] if releases else None
        }
        
        if releases:
            stats['average_assets_per_release'] = sum(len(r['assets']) for r in releases) / len(releases)
            stats['most_downloaded_release'] = max(
                releases,
                key=lambda r: sum(asset['download_count'] for asset in r['assets'])
            )
        
        return stats
    
    def validate_release_data(self, release: Release) -> Tuple[bool, List[str]]:
        """Validate release data before creation"""
        errors = []
        
        if not release.tag_name:
            errors.append("Tag name is required")
        
        if not release.name:
            errors.append("Release name is required")
        
        # Check assets exist
        for asset in release.assets:
            if not asset.file_path.exists():
                errors.append(f"Asset file not found: {asset.file_path}")
            elif asset.file_path.stat().st_size > 2 * 1024 * 1024 * 1024:  # 2GB limit
                errors.append(f"Asset file too large (>2GB): {asset.file_path}")
        
        return len(errors) == 0, errors


def main():
    """CLI interface for release publisher"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GitHub Release Publisher')
    parser.add_argument('--token', help='GitHub token (or set GITHUB_TOKEN env var)')
    parser.add_argument('--repository', required=True, help='Repository in owner/repo format')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Create release
    create_parser = subparsers.add_parser('create', help='Create a new release')
    create_parser.add_argument('tag', help='Tag name for the release')
    create_parser.add_argument('--name', help='Release name (defaults to tag name)')
    create_parser.add_argument('--body', help='Release description')
    create_parser.add_argument('--body-file', help='Read release description from file')
    create_parser.add_argument('--draft', action='store_true', help='Create as draft')
    create_parser.add_argument('--prerelease', action='store_true', help='Mark as prerelease')
    create_parser.add_argument('--target', default='main', help='Target branch/commit')
    create_parser.add_argument('--assets', nargs='*', help='Asset files to upload')
    create_parser.add_argument('--generate-notes', action='store_true', help='Generate release notes')
    
    # Update release
    update_parser = subparsers.add_parser('update', help='Update an existing release')
    update_parser.add_argument('tag', help='Tag name of the release')
    update_parser.add_argument('--name', help='New release name')
    update_parser.add_argument('--body', help='New release description')
    update_parser.add_argument('--body-file', help='Read new description from file')
    update_parser.add_argument('--draft', action='store_true', help='Make draft')
    update_parser.add_argument('--publish', action='store_true', help='Publish draft')
    
    # List releases
    list_parser = subparsers.add_parser('list', help='List releases')
    list_parser.add_argument('--count', type=int, default=10, help='Number of releases to show')
    list_parser.add_argument('--drafts', action='store_true', help='Include drafts')
    
    # Delete release
    delete_parser = subparsers.add_parser('delete', help='Delete a release')
    delete_parser.add_argument('tag', help='Tag name of the release')
    
    # Upload assets
    upload_parser = subparsers.add_parser('upload', help='Upload assets to existing release')
    upload_parser.add_argument('tag', help='Tag name of the release')
    upload_parser.add_argument('assets', nargs='+', help='Asset files to upload')
    
    # Statistics
    subparsers.add_parser('stats', help='Show release statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    token = args.token or os.environ.get('GITHUB_TOKEN')
    if not token:
        print("Error: GitHub token required (--token or GITHUB_TOKEN env var)")
        return 1
    
    try:
        publisher = ReleasePublisher(token, args.repository)
        
        if args.command == 'create':
            # Prepare release body
            body = args.body or ""
            if args.body_file:
                with open(args.body_file, 'r', encoding='utf-8') as f:
                    body = f.read()
            
            # Prepare assets
            assets = []
            if args.assets:
                for asset_path in args.assets:
                    assets.append(ReleaseAsset(asset_path))
            
            release = Release(
                tag_name=args.tag,
                name=args.name or args.tag,
                body=body,
                draft=args.draft,
                prerelease=args.prerelease,
                target_commitish=args.target,
                assets=assets,
                generate_release_notes=args.generate_notes
            )
            
            # Validate before creating
            is_valid, errors = publisher.validate_release_data(release)
            if not is_valid:
                print("Validation errors:")
                for error in errors:
                    print(f"  - {error}")
                return 1
            
            result = publisher.create_release(release)
            if result:
                print(f"Release created: {result['html_url']}")
        
        elif args.command == 'update':
            existing = publisher.get_release(args.tag)
            if not existing:
                print(f"Release not found: {args.tag}")
                return 1
            
            updates = {}
            if args.name:
                updates['name'] = args.name
            if args.body:
                updates['body'] = args.body
            if args.body_file:
                with open(args.body_file, 'r', encoding='utf-8') as f:
                    updates['body'] = f.read()
            if args.draft:
                updates['draft'] = True
            if args.publish:
                updates['draft'] = False
            
            if updates:
                result = publisher.update_release(existing['id'], **updates)
                if result:
                    print(f"Release updated: {result['html_url']}")
        
        elif args.command == 'list':
            releases = publisher.list_releases(per_page=args.count)
            
            for release in releases:
                status = "📝 DRAFT" if release['draft'] else "🚀 PUBLISHED"
                if release['prerelease']:
                    status += " (prerelease)"
                
                assets_count = len(release['assets'])
                downloads = sum(asset['download_count'] for asset in release['assets'])
                
                print(f"{status} {release['tag_name']} - {release['name']}")
                print(f"  Created: {release['created_at'][:10]}")
                print(f"  Assets: {assets_count}, Downloads: {downloads}")
                print(f"  URL: {release['html_url']}")
                print()
        
        elif args.command == 'delete':
            existing = publisher.get_release(args.tag)
            if not existing:
                print(f"Release not found: {args.tag}")
                return 1
            
            success = publisher.delete_release(existing['id'])
            if success:
                print(f"Deleted release: {args.tag}")
        
        elif args.command == 'upload':
            existing = publisher.get_release(args.tag)
            if not existing:
                print(f"Release not found: {args.tag}")
                return 1
            
            assets = [ReleaseAsset(asset_path) for asset_path in args.assets]
            uploaded = publisher.upload_assets(existing['id'], assets)
            print(f"Uploaded {len(uploaded)} assets")
        
        elif args.command == 'stats':
            stats = publisher.get_release_statistics()
            print("Release Statistics:")
            print(f"  Total releases: {stats['total_releases']}")
            print(f"  Draft releases: {stats['draft_releases']}")
            print(f"  Prereleases: {stats['prereleases']}")
            print(f"  Releases with assets: {stats['releases_with_assets']}")
            print(f"  Total downloads: {stats['total_downloads']}")
            
            if 'average_assets_per_release' in stats:
                print(f"  Average assets per release: {stats['average_assets_per_release']:.1f}")
            
            if stats['latest_release']:
                latest = stats['latest_release']
                print(f"  Latest release: {latest['tag_name']} ({latest['created_at'][:10]})")
        
        return 0
        
    except GitHubReleaseError as e:
        print(f"Error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\nOperation cancelled")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())