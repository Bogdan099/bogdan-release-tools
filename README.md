# 📦 Version Manager

Инструмент для работы с semantic versioning в Python проектах.

## ✨ Особенности

- 📊 **Semantic Versioning** - полная поддержка semver.org
- 🔄 **Bump функциональность** - увеличение major, minor, patch и prerelease версий  
- ✅ **Валидация** - проверка корректности версий
- 💾 **Хранение** - сохранение версий в JSON файле с метаданными
- 🖥️ **CLI интерфейс** - удобное использование из командной строки
- 🐍 **Программный API** - использование в Python коде

## 🚀 Установка

Скачайте `version_manager.py` в ваш проект. Зависимости не требуются - используется только стандартная библиотека Python.

## 📖 Использование

### CLI интерфейс

```bash
# Получить текущую версию
python3 version_manager.py get

# Увеличить patch версию (1.0.0 → 1.0.1)
python3 version_manager.py bump patch

# Увеличить minor версию (1.0.1 → 1.1.0)
python3 version_manager.py bump minor

# Увеличить major версию (1.1.0 → 2.0.0)
python3 version_manager.py bump major

# Создать prerelease версию (2.0.0 → 2.0.0-alpha.1)
python3 version_manager.py bump prerelease

# Создать prerelease с кастомным идентификатором
python3 version_manager.py bump prerelease --prerelease-id beta

# Валидировать версию
python3 version_manager.py validate 1.2.3-alpha.1
```

### Программный API

```python
from version_manager import get_current_version, bump_version

# Получить текущую версию
current = get_current_version()
print(f"Текущая версия: {current}")

# Увеличить версию
new_patch = bump_version('patch')
new_minor = bump_version('minor')
new_major = bump_version('major')
new_prerelease = bump_version('prerelease', 'beta')

print(f"Patch: {new_patch}")
print(f"Minor: {new_minor}")  
print(f"Major: {new_major}")
print(f"Prerelease: {new_prerelease}")
```

### Объектно-ориентированный API

```python
from version_manager import VersionManager

vm = VersionManager('my_version.json')

# Получить текущую версию
current = vm.get_current_version()

# Увеличить версию  
new_version = vm.bump_version('minor')

# Валидация
is_valid = vm._is_valid_semver('1.2.3-alpha.1')
```

## 📁 Файл версий

Version Manager создает файл `version.json` со следующей структурой:

```json
{
  "version": "1.2.0-beta.1",
  "updated_at": "2024-01-15T10:30:45.123456Z",
  "format": "semantic"
}
```

## 📋 Semantic Versioning

Поддерживается полный стандарт [semver.org](https://semver.org/):

- **MAJOR** версия увеличивается при несовместимых изменениях API
- **MINOR** версия увеличивается при добавлении функциональности с обратной совместимостью
- **PATCH** версия увеличивается при исправлении багов с обратной совместимостью
- **PRERELEASE** версии для предварительных релизов

### Примеры корректных версий:

- `1.0.0`
- `1.2.3`
- `1.0.0-alpha`
- `1.0.0-alpha.1`
- `1.0.0-alpha0.valid`
- `1.0.0-alpha.0valid`
- `1.0.0-alpha-a.b-c-somethinglong+metadata`
- `1.0.0-rc.1+meta`

## 🔧 API Reference

### Функции

#### `get_current_version() -> str`
Возвращает текущую версию проекта из файла версий.

#### `bump_version(bump_type: str, prerelease_identifier: str = "alpha") -> str`
Увеличивает версию согласно типу инкремента.

**Параметры:**
- `bump_type`: Тип инкремента - 'major', 'minor', 'patch', 'prerelease'
- `prerelease_identifier`: Идентификатор для prerelease версий (по умолчанию 'alpha')

**Возвращает:**
- Новую версию в формате string

### Класс VersionManager

#### `__init__(version_file: str = "version.json")`
Создает экземпляр менеджера версий.

#### `get_current_version() -> str`
Получает текущую версию из файла.

#### `bump_version(bump_type: str, prerelease_identifier: str = "alpha") -> str`
Увеличивает версию согласно типу.

## 🛠️ Разработка

### Тестирование

```bash
# Базовое тестирование функциональности
python3 version_manager.py get
python3 version_manager.py bump patch
python3 version_manager.py validate 1.0.0
```

### Расширение

Version Manager использует только стандартную библиотеку Python и легко расширяется:

- Добавьте новые форматы хранения версий
- Интегрируйте с системами CI/CD
- Добавьте поддержку других систем версионирования
- Создайте плагины для популярных инструментов

## 📄 Лицензия

MIT License - см. файл [LICENSE](LICENSE) для деталей.

## 🤝 Поддержка

Если у вас есть вопросы или предложения:

1. Создайте issue в репозитории
2. Опишите проблему подробно
3. Приложите примеры использования

---

**Version Manager** - надежный инструмент для работы с semantic versioning в ваших Python проектах! 🚀