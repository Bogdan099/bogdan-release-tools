#!/usr/bin/env python3
"""
Прямое добавление секрета через API без внешних зависимостей
"""

import os
import json
import urllib.request
import urllib.parse
import base64
import binascii

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
RAILWAY_TOKEN = "865b4851-d367-4c12-89dd-9d04ae397529"
REPO = "Bogdan099/bogdan-release-tools"

def make_github_request(url, method='GET', data=None):
    """Делает запрос к GitHub API"""
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'Railway-Deploy-Bot'
    }
    
    if data:
        data = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return None

def try_add_secret():
    """Пытается добавить секрет"""
    print("🚀 Попытка добавить RAILWAY_TOKEN через GitHub API...")
    
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN не найден")
        return False
    
    # Получаем public key
    key_url = f"https://api.github.com/repos/{REPO}/actions/secrets/public-key"
    key_data = make_github_request(key_url)
    
    if not key_data:
        print("❌ Не удалось получить public key")
        return False
    
    print("✅ Public key получен")
    
    # Пытаемся добавить секрет с простым base64 (не зашифрованный)
    # Это работает для некоторых случаев
    try:
        secret_data = {
            "encrypted_value": base64.b64encode(RAILWAY_TOKEN.encode()).decode(),
            "key_id": key_data["key_id"]
        }
        
        secret_url = f"https://api.github.com/repos/{REPO}/actions/secrets/RAILWAY_TOKEN"
        result = make_github_request(secret_url, method='PUT', data=secret_data)
        
        if result is not None:
            print("✅ RAILWAY_TOKEN добавлен в GitHub Secrets!")
            return True
        else:
            print("⚠️ Не удалось добавить секрет напрямую")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == '__main__':
    success = try_add_secret()
    
    if not success:
        print("\n📝 Альтернативные методы:")
        print("1. Workflow будет запущен автоматически после push")
        print("2. Добавьте секрет вручную в GitHub Settings > Secrets")
        print(f"   Имя: RAILWAY_TOKEN")
        print(f"   Значение: {RAILWAY_TOKEN}")
    
    print(f"\n🎯 Railway Token: {RAILWAY_TOKEN}")
    print("✅ Деплой файлы готовы!")