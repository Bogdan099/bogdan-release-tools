#!/usr/bin/env python3
"""
Changelog Generator for Automated Release Management

This module generates CHANGELOG.md files from git commit messages,
following conventional commits specification and Keep a Changelog format.
"""

import re
import subprocess
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum


class CommitType(Enum):
    """Conventional commit types"""
    FEAT = "feat"
    FIX = "fix"
    DOCS = "docs"
    STYLE = "style"
    REFACTOR = "refactor"
    PERF = "perf"
    TEST = "test"
    BUILD = "build"
    CI = "ci"
    CHORE = "chore"
    REVERT = "revert"


@dataclass
class Commit:
    """Represents a git commit with parsed conventional commit information"""
    hash: str
    message: str
    author: str
    date: str
    type: Optional[str] = None
    scope: Optional[str] = None
    description: str = ""
    body: str = ""
    footer: str = ""
    breaking_change: bool = False
    closes_issues: List[str] = None
    
    def __post_init__(self):
        if self.closes_issues is None:
            self.closes_issues = []


class ChangelogGenerator:
    """Generates changelogs from git commit history"""
    
    def __init__(self, repo_path: str = ".", changelog_file: str = "CHANGELOG.md"):
        self.repo_path = Path(repo_path)
        self.changelog_file = Path(changelog_file)
        self.conventional_commit_pattern = re.compile(
            r'^(?P<type>\w+)(?:\((?P<scope>[\w\-\.]+)\))?\!?:\s(?P<description>.+?)(?:\n\n(?P<body>.*?))?(?:\n\n(?P<footer>.*))?$',
            re.MULTILINE | re.DOTALL
        )
        self.breaking_change_pattern = re.compile(r'BREAKING CHANGE:\s(.+)', re.MULTILINE)
        self.closes_pattern = re.compile(r'(?:closes?|fixes?|resolves?)\s+#(\d+)', re.IGNORECASE)
        
    def get_git_commits(self, since_tag: Optional[str] = None, until_tag: Optional[str] = None) -> List[Commit]:
        """Get git commits since last tag or specified range"""
        try:
            # Build git log command
            cmd = ["git", "log", "--pretty=format:%H|%an|%ai|%s|%b", "--reverse"]
            
            if since_tag and until_tag:
                cmd.append(f"{since_tag}..{until_tag}")
            elif since_tag:
                cmd.append(f"{since_tag}..HEAD")
            elif until_tag:
                cmd.append(f"HEAD..{until_tag}")
            
            result = subprocess.run(cmd, 
                                  capture_output=True, 
                                  text=True, 
                                  cwd=self.repo_path,
                                  check=True)
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|', 4)
                    if len(parts) >= 4:
                        commit = Commit(
                            hash=parts[0],
                            author=parts[1],
                            date=parts[2],
                            message=parts[3],
                            body=parts[4] if len(parts) > 4 else ""
                        )
                        self._parse_conventional_commit(commit)
                        commits.append(commit)
            
            return commits
            
        except subprocess.CalledProcessError as e:
            print(f"Error getting git commits: {e}")
            return []
    
    def _parse_conventional_commit(self, commit: Commit) -> None:
        """Parse conventional commit message format"""
        match = self.conventional_commit_pattern.match(commit.message)
        
        if match:
            commit.type = match.group('type')
            commit.scope = match.group('scope')
            commit.description = match.group('description')
            if match.group('body'):
                commit.body = match.group('body').strip()
            if match.group('footer'):
                commit.footer = match.group('footer').strip()
        else:
            # Non-conventional commit
            commit.description = commit.message
        
        # Check for breaking changes
        if '!' in commit.message or 'BREAKING CHANGE' in commit.message:
            commit.breaking_change = True
        
        # Extract closed issues
        closes_matches = self.closes_pattern.findall(commit.message + " " + commit.body)
        commit.closes_issues = [f"#{issue}" for issue in closes_matches]
    
    def get_last_tag(self) -> Optional[str]:
        """Get the last git tag"""
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    
    def group_commits_by_type(self, commits: List[Commit]) -> Dict[str, List[Commit]]:
        """Group commits by their type"""
        grouped = {
            'breaking': [],
            'features': [],
            'fixes': [],
            'performance': [],
            'documentation': [],
            'styles': [],
            'refactors': [],
            'tests': [],
            'build': [],
            'ci': [],
            'chores': [],
            'reverts': [],
            'other': []
        }
        
        for commit in commits:
            if commit.breaking_change:
                grouped['breaking'].append(commit)
            elif commit.type == CommitType.FEAT.value:
                grouped['features'].append(commit)
            elif commit.type == CommitType.FIX.value:
                grouped['fixes'].append(commit)
            elif commit.type == CommitType.PERF.value:
                grouped['performance'].append(commit)
            elif commit.type == CommitType.DOCS.value:
                grouped['documentation'].append(commit)
            elif commit.type == CommitType.STYLE.value:
                grouped['styles'].append(commit)
            elif commit.type == CommitType.REFACTOR.value:
                grouped['refactors'].append(commit)
            elif commit.type == CommitType.TEST.value:
                grouped['tests'].append(commit)
            elif commit.type == CommitType.BUILD.value:
                grouped['build'].append(commit)
            elif commit.type == CommitType.CI.value:
                grouped['ci'].append(commit)
            elif commit.type == CommitType.CHORE.value:
                grouped['chores'].append(commit)
            elif commit.type == CommitType.REVERT.value:
                grouped['reverts'].append(commit)
            else:
                grouped['other'].append(commit)
        
        return grouped
    
    def format_commit_entry(self, commit: Commit) -> str:
        """Format a single commit for changelog entry"""
        scope_str = f"**{commit.scope}**: " if commit.scope else ""
        
        entry = f"- {scope_str}{commit.description}"
        
        # Add commit hash (short)
        short_hash = commit.hash[:7]
        entry += f" ([{short_hash}](../../commit/{commit.hash}))"
        
        # Add closed issues
        if commit.closes_issues:
            entry += f" (closes {', '.join(commit.closes_issues)})"
        
        return entry
    
    def generate_changelog_section(self, version: str, commits: List[Commit], date: str = None) -> str:
        """Generate a changelog section for a version"""
        if not commits:
            return ""
        
        date_str = date or datetime.now().strftime("%Y-%m-%d")
        grouped_commits = self.group_commits_by_type(commits)
        
        section = f"\n## [{version}] - {date_str}\n"
        
        # Breaking Changes
        if grouped_commits['breaking']:
            section += "\n### ⚠ BREAKING CHANGES\n\n"
            for commit in grouped_commits['breaking']:
                section += self.format_commit_entry(commit) + "\n"
        
        # Features
        if grouped_commits['features']:
            section += "\n### ✨ Features\n\n"
            for commit in grouped_commits['features']:
                section += self.format_commit_entry(commit) + "\n"
        
        # Bug Fixes
        if grouped_commits['fixes']:
            section += "\n### 🐛 Bug Fixes\n\n"
            for commit in grouped_commits['fixes']:
                section += self.format_commit_entry(commit) + "\n"
        
        # Performance
        if grouped_commits['performance']:
            section += "\n### ⚡ Performance Improvements\n\n"
            for commit in grouped_commits['performance']:
                section += self.format_commit_entry(commit) + "\n"
        
        # Documentation
        if grouped_commits['documentation']:
            section += "\n### 📚 Documentation\n\n"
            for commit in grouped_commits['documentation']:
                section += self.format_commit_entry(commit) + "\n"
        
        # Code Refactoring
        if grouped_commits['refactors']:
            section += "\n### ♻️ Code Refactoring\n\n"
            for commit in grouped_commits['refactors']:
                section += self.format_commit_entry(commit) + "\n"
        
        # Tests
        if grouped_commits['tests']:
            section += "\n### ✅ Tests\n\n"
            for commit in grouped_commits['tests']:
                section += self.format_commit_entry(commit) + "\n"
        
        # Build System
        if grouped_commits['build']:
            section += "\n### 🔧 Build System\n\n"
            for commit in grouped_commits['build']:
                section += self.format_commit_entry(commit) + "\n"
        
        # CI/CD
        if grouped_commits['ci']:
            section += "\n### 👷 CI/CD\n\n"
            for commit in grouped_commits['ci']:
                section += self.format_commit_entry(commit) + "\n"
        
        # Other changes
        if grouped_commits['other']:
            section += "\n### 📦 Other Changes\n\n"
            for commit in grouped_commits['other']:
                section += self.format_commit_entry(commit) + "\n"
        
        return section
    
    def create_initial_changelog(self) -> str:
        """Create initial changelog with header"""
        return """# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

"""
    
    def update_changelog(self, version: str, commits: List[Commit] = None, date: str = None) -> str:
        """Update changelog with new version"""
        # Get commits if not provided
        if commits is None:
            last_tag = self.get_last_tag()
            commits = self.get_git_commits(since_tag=last_tag)
        
        # Read existing changelog or create new one
        existing_content = ""
        if self.changelog_file.exists():
            with open(self.changelog_file, 'r', encoding='utf-8') as f:
                existing_content = f.read()
        else:
            existing_content = self.create_initial_changelog()
        
        # Generate new section
        new_section = self.generate_changelog_section(version, commits, date)
        
        # Insert new section after "## [Unreleased]"
        unreleased_pattern = r'(## \[Unreleased\]\s*\n)'
        if re.search(unreleased_pattern, existing_content):
            new_content = re.sub(
                unreleased_pattern,
                r'\1' + new_section,
                existing_content
            )
        else:
            # Fallback: add at the beginning
            lines = existing_content.split('\n')
            header_end = 0
            for i, line in enumerate(lines):
                if line.startswith('## '):
                    header_end = i
                    break
            
            lines.insert(header_end, new_section.strip())
            new_content = '\n'.join(lines)
        
        # Write updated changelog
        with open(self.changelog_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return new_content
    
    def generate_release_notes(self, version: str, commits: List[Commit] = None) -> str:
        """Generate release notes for GitHub releases"""
        if commits is None:
            last_tag = self.get_last_tag()
            commits = self.get_git_commits(since_tag=last_tag)
        
        if not commits:
            return f"## {version}\n\nNo changes in this release."
        
        grouped_commits = self.group_commits_by_type(commits)
        notes = f"## {version}\n"
        
        # Breaking Changes
        if grouped_commits['breaking']:
            notes += "\n### ⚠️ Breaking Changes\n"
            for commit in grouped_commits['breaking']:
                notes += f"- {commit.description}\n"
        
        # Features  
        if grouped_commits['features']:
            notes += "\n### ✨ New Features\n"
            for commit in grouped_commits['features']:
                notes += f"- {commit.description}\n"
        
        # Bug Fixes
        if grouped_commits['fixes']:
            notes += "\n### 🐛 Bug Fixes\n"
            for commit in grouped_commits['fixes']:
                notes += f"- {commit.description}\n"
        
        # Performance
        if grouped_commits['performance']:
            notes += "\n### ⚡ Performance\n"
            for commit in grouped_commits['performance']:
                notes += f"- {commit.description}\n"
        
        # Other notable changes
        other_types = ['documentation', 'refactors', 'tests', 'build', 'ci']
        other_commits = []
        for commit_type in other_types:
            other_commits.extend(grouped_commits[commit_type])
        
        if other_commits:
            notes += "\n### 📦 Other Changes\n"
            for commit in other_commits[:10]:  # Limit to 10 items
                notes += f"- {commit.description}\n"
            if len(other_commits) > 10:
                notes += f"- ... and {len(other_commits) - 10} more changes\n"
        
        return notes
    
    def get_contributors(self, commits: List[Commit]) -> List[str]:
        """Get unique contributors from commits"""
        authors = set()
        for commit in commits:
            authors.add(commit.author)
        return sorted(list(authors))


def main():
    """CLI interface for changelog generator"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Changelog Generator')
    parser.add_argument('--version', required=True, help='Version to generate changelog for')
    parser.add_argument('--output', default='CHANGELOG.md', help='Output file')
    parser.add_argument('--since-tag', help='Generate changelog since this tag')
    parser.add_argument('--until-tag', help='Generate changelog until this tag')
    parser.add_argument('--release-notes', action='store_true', help='Generate release notes format')
    parser.add_argument('--repo-path', default='.', help='Repository path')
    
    args = parser.parse_args()
    
    generator = ChangelogGenerator(args.repo_path, args.output)
    
    # Get commits
    commits = generator.get_git_commits(args.since_tag, args.until_tag)
    
    if args.release_notes:
        # Generate release notes
        notes = generator.generate_release_notes(args.version, commits)
        print(notes)
    else:
        # Update changelog
        content = generator.update_changelog(args.version, commits)
        print(f"Updated {args.output} with {len(commits)} commits for version {args.version}")
        
        # Show contributors
        contributors = generator.get_contributors(commits)
        if contributors:
            print(f"\nContributors to this release:")
            for contributor in contributors:
                print(f"  - {contributor}")


if __name__ == '__main__':
    main()