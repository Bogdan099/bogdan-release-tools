# 🚀 Release Automation Tools

Полный набор инструментов для автоматизации релизов с поддержкой semantic versioning, автоматической генерации changelog, мержа PR, создания git tags и публикации GitHub releases.

## 📋 Компоненты

### 1. Version Manager (`version_manager.py`)
Управление semantic versioning согласно semver.org:
- ✅ Инкремент версий (major, minor, patch, prerelease)
- ✅ Валидация версий
- ✅ Сравнение версий
- ✅ Автоматическое определение типа версии по коммитам
- ✅ Хранение метаданных версий

### 2. Changelog Generator (`changelog_generator.py`)
Автоматическая генерация CHANGELOG.md из git коммитов:
- ✅ Поддержка conventional commits
- ✅ Группировка по типам изменений
- ✅ Генерация release notes для GitHub
- ✅ Формат Keep a Changelog
- ✅ Обнаружение breaking changes

### 3. PR Merger (`pr_merger.py`)
Автоматический мерж pull requests после прохождения проверок:
- ✅ Проверка статуса CI/CD
- ✅ Валидация ревью
- ✅ Настраиваемые условия мержа
- ✅ Поддержка различных методов мержа
- ✅ Автоматическое удаление веток

### 4. Tag Creator (`tag_creator.py`)
Создание и управление git tags:
- ✅ Lightweight и annotated tags
- ✅ Подписанные tags (GPG)
- ✅ Автоматический push в remote
- ✅ Валидация имен tags
- ✅ Статистика по tags

### 5. Release Publisher (`release_publisher.py`)
Публикация релизов в GitHub:
- ✅ Создание GitHub releases
- ✅ Загрузка assets
- ✅ Автоматическая генерация release notes
- ✅ Поддержка draft/prerelease
- ✅ Статистика по релизам

### 6. Release Automation (`release_automation.py`)
Главный оркестратор всего процесса релиза:
- ✅ Полный автоматизированный pipeline
- ✅ Конфигурируемые настройки
- ✅ Пошаговое выполнение
- ✅ Обработка ошибок
- ✅ Статус мониторинг

## 🔧 Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-org/bogdan-release-tools.git
cd bogdan-release-tools
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройте переменные окружения:
```bash
export GITHUB_TOKEN="your_github_token"
```

## ⚙️ Конфигурация

Создайте файл `release_config.json` или используйте автоматическую генерацию:

```bash
python release_automation.py config --init
```

Пример конфигурации:
```json
{
  "version_file": "version.json",
  "changelog_file": "CHANGELOG.md", 
  "repo_path": ".",
  "remote_name": "origin",
  "repository": "owner/repo",
  "github_token": "${GITHUB_TOKEN}",
  "release_settings": {
    "tag_prefix": "v",
    "create_tag": true,
    "push_tag": true,
    "create_github_release": true,
    "sign_tags": false,
    "delete_branch_after_merge": true,
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
  "assets": [
    {
      "path": "dist/app.zip",
      "name": "application.zip",
      "label": "Application Bundle"
    }
  ]
}
```

## 🚀 Использование

### Быстрый старт - Полный автоматический релиз

```bash
# Автоматический релиз (определение типа версии по коммитам)
python release_automation.py release auto

# Patch релиз
python release_automation.py release patch

# Minor релиз с автоматическим мержем PR
python release_automation.py release minor --auto-merge-prs

# Major релиз как prerelease
python release_automation.py release major --prerelease
```

### Пошаговое использование отдельных компонентов

#### Version Manager
```bash
# Показать текущую версию
python version_manager.py --get

# Инкремент версии
python version_manager.py --increment patch
python version_manager.py --increment minor
python version_manager.py --increment major

# Установить конкретную версию
python version_manager.py --set 1.0.0

# Валидация версии
python version_manager.py --validate 1.2.3-beta.1
```

#### Changelog Generator
```bash
# Обновить CHANGELOG для новой версии
python changelog_generator.py --version 1.2.0

# Генерация с конкретного тега
python changelog_generator.py --version 1.2.0 --since-tag v1.1.0

# Генерация release notes
python changelog_generator.py --version 1.2.0 --release-notes
```

#### PR Merger
```bash
# Проверить статус конкретного PR
python pr_merger.py --repository owner/repo --status 123

# Мерж конкретного PR
python pr_merger.py --repository owner/repo --pr 123

# Ожидание и мерж после прохождения проверок
python pr_merger.py --repository owner/repo --pr 123 --wait

# Автоматический мерж всех готовых PR
python pr_merger.py --repository owner/repo --auto-merge
```

#### Tag Creator
```bash
# Создать версионный тег
python tag_creator.py version 1.2.0 --sign --push

# Создать релизный тег с changelog
python tag_creator.py release 1.2.0 --changelog "Major improvements"

# Список тегов
python tag_creator.py list --info

# Статистика по тегам
python tag_creator.py stats
```

#### Release Publisher
```bash
# Создать релиз из тега
python release_publisher.py create v1.2.0 --body "Release notes here"

# Создать релиз с assets
python release_publisher.py create v1.2.0 --assets dist/app.zip docs.pdf

# Список релизов
python release_publisher.py list --count 5

# Статистика по релизам
python release_publisher.py stats
```

### Подготовка к релизу

```bash
# Проверить готовность репозитория
python release_automation.py status

# Подготовить релиз (мерж PR)
python release_automation.py prepare

# Проверить конкретный PR
python release_automation.py prepare --pr 123
```

## 📊 Мониторинг и статистика

```bash
# Полный статус системы
python release_automation.py status

# Статистика по версиям
python version_manager.py --get

# Статистика по тегам
python tag_creator.py stats

# Статистика по релизам
python release_publisher.py stats
```

## 🔄 CI/CD Интеграция

### GitHub Actions Example

```yaml
name: Release Automation

on:
  push:
    branches: [main]
  pull_request:
    types: [labeled]

jobs:
  auto-merge:
    if: contains(github.event.pull_request.labels.*.name, 'ready-to-merge')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Auto-merge PR
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python pr_merger.py --repository ${{ github.repository }} --pr ${{ github.event.number }}

  release:
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Create Release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python release_automation.py release auto
```

## 🛠️ Расширенные функции

### Conventional Commits
Система поддерживает conventional commits для автоматического определения типа версии:

- `feat:` → minor increment
- `fix:` → patch increment
- `BREAKING CHANGE:` → major increment
- `docs:`, `style:`, `refactor:`, `test:`, `chore:` → организация в changelog

### Настройка PR мержа

```python
# В release_config.json
{
  "pr_merge_settings": {
    "method": "squash",  # merge, squash, rebase
    "required_reviews": 2,
    "required_status_checks": ["ci", "tests", "security-scan"],
    "auto_merge_labels": ["ready-to-merge", "hotfix"],
    "blocked_labels": ["do-not-merge", "wip", "needs-review"],
    "target_branches": ["main", "develop"],
    "timeout_minutes": 60,
    "dismiss_stale_reviews": true,
    "require_up_to_date": true
  }
}
```

### Подписание тегов и релизов

```bash
# Настройка GPG для подписания
git config user.signingkey YOUR_GPG_KEY_ID
git config commit.gpgsign true
git config tag.gpgsign true

# Создание подписанного релиза
python tag_creator.py release 1.0.0 --no-push --sign
```

## 🧪 Тестирование

```bash
# Установка dev-зависимостей
pip install pytest pytest-cov

# Запуск тестов
pytest tests/

# С покрытием кода
pytest --cov=. tests/
```

## 📚 API Reference

### Version Manager API
```python
from version_manager import VersionManager, VersionType

vm = VersionManager()
current = vm.get_current_version()
new_version = vm.increment_version(VersionType.MINOR)
```

### Changelog Generator API
```python
from changelog_generator import ChangelogGenerator

cg = ChangelogGenerator()
commits = cg.get_git_commits(since_tag="v1.0.0")
cg.update_changelog("1.1.0", commits)
```

### Release Publisher API
```python
from release_publisher import ReleasePublisher, Release, ReleaseAsset

rp = ReleasePublisher(token, "owner/repo")
release = Release(
    tag_name="v1.0.0",
    name="Release 1.0.0",
    body="Release notes",
    assets=[ReleaseAsset("dist/app.zip")]
)
result = rp.create_release(release)
```

## 🤝 Contributing

1. Fork репозиторий
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📄 License

Этот проект лицензируется под MIT License - см. файл [LICENSE](LICENSE) для деталей.

## 🆘 Поддержка

Если у вас есть вопросы или проблемы:

1. Проверьте [Issues](https://github.com/your-org/bogdan-release-tools/issues)
2. Создайте новый issue с подробным описанием
3. Используйте labels для категоризации

## 📈 Roadmap

- [ ] Поддержка multiple repositories
- [ ] Webhook интеграции
- [ ] Slack/Teams notifications
- [ ] Release approval workflow
- [ ] Custom release templates
- [ ] Docker container deployment
- [ ] Rollback functionality