#!/usr/bin/env python3
"""
Version Manager for Semantic Versioning

Инструмент для работы с semantic versioning согласно semver.org
Основные функции: bump_version, get_current_version
"""

import re
import json
import os
from typing import Optional, Dict, Any
from pathlib import Path
from enum import Enum


class VersionBumpType(Enum):
    """Типы инкремента версии"""
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    PRERELEASE = "prerelease"


class VersionManager:
    """Менеджер версий для semantic versioning"""
    
    def __init__(self, version_file: str = "version.json"):
        self.version_file = Path(version_file)
        # Регулярное выражение для валидации semantic version
        self.semver_pattern = re.compile(
            r'^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)'
            r'(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)'
            r'(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?'
            r'(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
        )
    
    def get_current_version(self) -> str:
        """
        Получить текущую версию из файла версий
        
        Returns:
            str: Текущая версия в формате semantic versioning
        """
        if not self.version_file.exists():
            # Инициализируем файл с начальной версией
            initial_version = "0.1.0"
            self._save_version(initial_version)
            return initial_version
        
        try:
            with open(self.version_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('version', '0.1.0')
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            # Если файл поврежден, возвращаем версию по умолчанию
            default_version = "0.1.0"
            self._save_version(default_version)
            return default_version
    
    def bump_version(self, bump_type: str, prerelease_identifier: str = "alpha") -> str:
        """
        Увеличить версию согласно semantic versioning
        
        Args:
            bump_type (str): Тип инкремента - 'major', 'minor', 'patch', 'prerelease'
            prerelease_identifier (str): Идентификатор для prerelease версий
            
        Returns:
            str: Новая версия
            
        Raises:
            ValueError: При некорректном типе инкремента или версии
        """
        current_version = self.get_current_version()
        
        # Валидируем текущую версию
        if not self._is_valid_semver(current_version):
            raise ValueError(f"Текущая версия некорректна: {current_version}")
        
        # Валидируем тип инкремента
        try:
            bump_enum = VersionBumpType(bump_type.lower())
        except ValueError:
            raise ValueError(f"Некорректный тип инкремента: {bump_type}. Доступные: {[t.value for t in VersionBumpType]}")
        
        # Парсим текущую версию
        version_parts = self._parse_version(current_version)
        
        # Выполняем инкремент
        new_version = self._increment_version(version_parts, bump_enum, prerelease_identifier)
        
        # Сохраняем новую версию
        self._save_version(new_version)
        
        return new_version
    
    def _parse_version(self, version: str) -> Dict[str, Any]:
        """Парсит версию на компоненты"""
        match = self.semver_pattern.match(version)
        if not match:
            raise ValueError(f"Некорректный формат версии: {version}")
        
        groups = match.groupdict()
        return {
            'major': int(groups['major']),
            'minor': int(groups['minor']),
            'patch': int(groups['patch']),
            'prerelease': groups.get('prerelease'),
            'buildmetadata': groups.get('buildmetadata')
        }
    
    def _increment_version(self, version_parts: Dict[str, Any], bump_type: VersionBumpType, prerelease_id: str) -> str:
        """Увеличивает версию согласно типу инкремента"""
        major = version_parts['major']
        minor = version_parts['minor']
        patch = version_parts['patch']
        prerelease = version_parts['prerelease']
        
        if bump_type == VersionBumpType.MAJOR:
            major += 1
            minor = 0
            patch = 0
            prerelease = None
            
        elif bump_type == VersionBumpType.MINOR:
            minor += 1
            patch = 0
            prerelease = None
            
        elif bump_type == VersionBumpType.PATCH:
            patch += 1
            prerelease = None
            
        elif bump_type == VersionBumpType.PRERELEASE:
            if prerelease:
                # Увеличиваем существующий prerelease
                prerelease = self._increment_prerelease(prerelease)
            else:
                # Создаем новый prerelease
                prerelease = f"{prerelease_id}.1"
        
        # Строим новую версию
        new_version = f"{major}.{minor}.{patch}"
        if prerelease:
            new_version += f"-{prerelease}"
            
        return new_version
    
    def _increment_prerelease(self, prerelease: str) -> str:
        """Увеличивает prerelease версию"""
        parts = prerelease.split('.')
        
        # Ищем последнюю числовую часть
        for i in range(len(parts) - 1, -1, -1):
            if parts[i].isdigit():
                parts[i] = str(int(parts[i]) + 1)
                return '.'.join(parts)
        
        # Если числовых частей нет, добавляем .1
        return f"{prerelease}.1"
    
    def _is_valid_semver(self, version: str) -> bool:
        """Проверяет, является ли версия корректной по semantic versioning"""
        return bool(self.semver_pattern.match(version))
    
    def _save_version(self, version: str) -> None:
        """Сохраняет версию в файл с метаданными"""
        from datetime import datetime
        
        version_data = {
            'version': version,
            'updated_at': datetime.utcnow().isoformat() + 'Z',
            'format': 'semantic'
        }
        
        # Создаем директорию если не существует
        self.version_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.version_file, 'w', encoding='utf-8') as f:
            json.dump(version_data, f, indent=2, ensure_ascii=False)


# Глобальный экземпляр менеджера версий
_version_manager = VersionManager()


def get_current_version() -> str:
    """
    Получить текущую версию проекта
    
    Returns:
        str: Текущая версия в формате semantic versioning
    """
    return _version_manager.get_current_version()


def bump_version(bump_type: str, prerelease_identifier: str = "alpha") -> str:
    """
    Увеличить версию проекта
    
    Args:
        bump_type (str): Тип инкремента - 'major', 'minor', 'patch', 'prerelease'
        prerelease_identifier (str): Идентификатор для prerelease версий (по умолчанию 'alpha')
        
    Returns:
        str: Новая версия
        
    Examples:
        >>> bump_version('patch')
        '1.0.1'
        >>> bump_version('minor')
        '1.1.0'
        >>> bump_version('major')
        '2.0.0'
        >>> bump_version('prerelease', 'beta')
        '1.0.1-beta.1'
    """
    return _version_manager.bump_version(bump_type, prerelease_identifier)


def main():
    """CLI интерфейс для работы с версиями"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Менеджер версий для semantic versioning')
    
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
    
    # Команда получения текущей версии
    subparsers.add_parser('get', help='Получить текущую версию')
    
    # Команда увеличения версии
    bump_parser = subparsers.add_parser('bump', help='Увеличить версию')
    bump_parser.add_argument('type', choices=['major', 'minor', 'patch', 'prerelease'],
                           help='Тип инкремента версии')
    bump_parser.add_argument('--prerelease-id', default='alpha',
                           help='Идентификатор для prerelease (по умолчанию: alpha)')
    
    # Команда валидации версии
    validate_parser = subparsers.add_parser('validate', help='Валидировать версию')
    validate_parser.add_argument('version', help='Версия для валидации')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        vm = VersionManager()
        
        if args.command == 'get':
            current = get_current_version()
            print(f"Текущая версия: {current}")
            
        elif args.command == 'bump':
            old_version = get_current_version()
            new_version = bump_version(args.type, args.prerelease_id)
            print(f"Версия изменена: {old_version} → {new_version}")
            
        elif args.command == 'validate':
            if vm._is_valid_semver(args.version):
                print(f"✅ Версия '{args.version}' корректна")
            else:
                print(f"❌ Версия '{args.version}' некорректна")
                return 1
        
        return 0
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())