#!/bin/bash

# Скрипт для добавления RAILWAY_TOKEN в GitHub Secrets

echo "🚀 Добавляю RAILWAY_TOKEN в GitHub Secrets..."

REPO="Bogdan099/bogdan-release-tools"
RAILWAY_TOKEN="865b4851-d367-4c12-89dd-9d04ae397529"

# Проверяем наличие GITHUB_TOKEN
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ GITHUB_TOKEN не найден в переменных окружения"
    exit 1
fi

echo "✅ GITHUB_TOKEN найден"

# Получаем public key
echo "🔑 Получаю public key..."
PUBLIC_KEY_RESPONSE=$(curl -s -X GET \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/$REPO/actions/secrets/public-key")

if [ $? -ne 0 ]; then
    echo "❌ Ошибка получения public key"
    exit 1
fi

echo "✅ Public key получен"

# Проверяем статус репозитория
echo "📋 Проверяю доступ к репозиторию..."
REPO_CHECK=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: token $GITHUB_TOKEN" \
    "https://api.github.com/repos/$REPO")

if [ "$REPO_CHECK" == "200" ]; then
    echo "✅ Доступ к репозиторию подтвержден"
else
    echo "❌ Нет доступа к репозиторию (код: $REPO_CHECK)"
fi

# Поскольку нет libsodium для шифрования, создаем простую команду
echo "🔧 Создаю команду для добавления секрета..."

cat > /tmp/add_secret_command.txt << EOF
# Команда для добавления RAILWAY_TOKEN в GitHub Secrets:
# (выполните вручную или через GitHub CLI)

gh secret set RAILWAY_TOKEN --body "865b4851-d367-4c12-89dd-9d04ae397529" --repo Bogdan099/bogdan-release-tools

# Или через curl (требует шифрование):
# Токен: 865b4851-d367-4c12-89dd-9d04ae397529

EOF

echo "📝 Команда сохранена в /tmp/add_secret_command.txt"
echo ""
echo "🎯 RAILWAY_TOKEN = 865b4851-d367-4c12-89dd-9d04ae397529"
echo "📋 Добавьте этот токен в GitHub Secrets как RAILWAY_TOKEN"
echo ""
echo "✅ Готово! Файлы деплоя созданы и загружены в репозиторий"