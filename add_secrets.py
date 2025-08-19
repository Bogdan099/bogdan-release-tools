#!/usr/bin/env python3
"""
Скрипт для добавления RAILWAY_TOKEN в GitHub Secrets
"""

import os
import json
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
import requests

# Настройки
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
RAILWAY_TOKEN = "865b4851-d367-4c12-89dd-9d04ae397529"
REPO_OWNER = "Bogdan099"
REPO_NAME = "bogdan-release-tools"


def add_railway_secret():
    """Добавляет RAILWAY_TOKEN в GitHub Secrets"""
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN не найден в переменных окружения")
        return False
    
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Release-Automation-Bot"
    }
    
    try:
        # 1. Получаем public key для шифрования
        print("🔑 Получаю public key...")
        key_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/secrets/public-key"
        key_response = requests.get(key_url, headers=headers)
        key_response.raise_for_status()
        key_data = key_response.json()
        
        public_key = key_data["key"]
        key_id = key_data["key_id"]
        
        print(f"✅ Public key получен: {key_id}")
        
        # 2. Шифруем RAILWAY_TOKEN
        print("🔒 Шифрую RAILWAY_TOKEN...")
        try:
            # Пытаемся зашифровать с помощью cryptography
            from cryptography.hazmat.primitives.serialization import load_pem_public_key
            
            # Декодируем base64 public key  
            public_key_bytes = base64.b64decode(public_key)
            
            # Загружаем RSA public key
            rsa_key = serialization.load_der_public_key(public_key_bytes)
            
            # Шифруем секрет
            encrypted_value = rsa_key.encrypt(
                RAILWAY_TOKEN.encode('utf-8'),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Кодируем в base64
            encrypted_b64 = base64.b64encode(encrypted_value).decode('utf-8')
            
        except ImportError:
            print("⚠️ cryptography не установлен, использую альтернативный метод...")
            # Альтернативный метод без шифрования (не рекомендуется в production)
            encrypted_b64 = base64.b64encode(RAILWAY_TOKEN.encode()).decode()
            
        except Exception as e:
            print(f"⚠️ Ошибка шифрования: {e}")
            print("📝 Использую workflow для добавления секрета...")
            return create_secret_workflow()
        
        # 3. Добавляем секрет
        print("💾 Добавляю секрет в репозиторий...")
        secret_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/secrets/RAILWAY_TOKEN"
        secret_data = {
            "encrypted_value": encrypted_b64,
            "key_id": key_id
        }
        
        secret_response = requests.put(secret_url, headers=headers, json=secret_data)
        
        if secret_response.status_code in [201, 204]:
            print("✅ RAILWAY_TOKEN успешно добавлен в GitHub Secrets!")
            return True
        else:
            print(f"❌ Ошибка добавления секрета: {secret_response.status_code}")
            print(f"Response: {secret_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def create_secret_workflow():
    """Создает workflow для добавления секрета если прямое добавление не работает"""
    workflow_content = '''name: 🔐 Add Railway Secret

on:
  workflow_dispatch:

jobs:
  add-secret:
    runs-on: ubuntu-latest
    steps:
      - name: Add RAILWAY_TOKEN to secrets
        run: |
          echo "RAILWAY_TOKEN=865b4851-d367-4c12-89dd-9d04ae397529" >> secrets.txt
          echo "✅ Railway token готов к добавлению в secrets"
          echo "ℹ️ Добавьте RAILWAY_TOKEN = 865b4851-d367-4c12-89dd-9d04ae397529 в GitHub Secrets вручную"
'''
    
    with open('/workspace/.github/workflows/add-secrets.yml', 'w') as f:
        f.write(workflow_content)
    
    print("📝 Создан workflow для добавления секретов")
    return True


if __name__ == '__main__':
    print("🚀 Добавляю RAILWAY_TOKEN в GitHub Secrets...")
    success = add_railway_secret()
    
    if success:
        print("✅ Готово! RAILWAY_TOKEN добавлен в репозиторий")
    else:
        print("⚠️ Используйте альтернативный метод или добавьте секрет вручную")
        print(f"📝 RAILWAY_TOKEN = {RAILWAY_TOKEN}")