#!/usr/bin/env python3
"""
Web API для Version Manager
Простой HTTP интерфейс для работы с версионированием
"""

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from version_manager import get_current_version, bump_version, VersionManager


class VersionAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Обработка GET запросов"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)
        
        try:
            if path == '/':
                self._serve_index()
            elif path == '/version':
                self._get_version()
            elif path == '/health':
                self._health_check()
            elif path == '/api/version':
                self._get_version_json()
            elif path == '/api/bump':
                bump_type = query.get('type', ['patch'])[0]
                prerelease_id = query.get('prerelease_id', ['alpha'])[0]
                self._bump_version(bump_type, prerelease_id)
            elif path == '/api/validate':
                version = query.get('version', [''])[0]
                if version:
                    self._validate_version(version)
                else:
                    self._send_error(400, "Missing version parameter")
            else:
                self._send_error(404, "Not Found")
                
        except Exception as e:
            self._send_error(500, str(e))
    
    def do_POST(self):
        """Обработка POST запросов"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8')) if content_length > 0 else {}
            
            if self.path == '/api/bump':
                bump_type = data.get('type', 'patch')
                prerelease_id = data.get('prerelease_id', 'alpha')
                self._bump_version(bump_type, prerelease_id)
            else:
                self._send_error(404, "Not Found")
                
        except Exception as e:
            self._send_error(500, str(e))
    
    def _serve_index(self):
        """Главная страница"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>📦 Version Manager API</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
                .method { background: #007cba; color: white; padding: 3px 8px; border-radius: 3px; font-size: 12px; }
                button { background: #007cba; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; }
                button:hover { background: #005a87; }
                #result { background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 10px 0; }
            </style>
        </head>
        <body>
            <h1>📦 Version Manager API</h1>
            <p>REST API для работы с semantic versioning</p>
            
            <div class="endpoint">
                <h3><span class="method">GET</span> /api/version</h3>
                <p>Получить текущую версию</p>
                <button onclick="getCurrentVersion()">Получить версию</button>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">GET/POST</span> /api/bump?type=patch</h3>
                <p>Увеличить версию (patch, minor, major, prerelease)</p>
                <select id="bumpType">
                    <option value="patch">Patch</option>
                    <option value="minor">Minor</option>
                    <option value="major">Major</option>
                    <option value="prerelease">Prerelease</option>
                </select>
                <button onclick="bumpVersion()">Увеличить версию</button>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">GET</span> /api/validate?version=1.0.0</h3>
                <p>Валидировать версию</p>
                <input type="text" id="validateInput" placeholder="1.2.3-alpha.1" />
                <button onclick="validateVersion()">Валидировать</button>
            </div>
            
            <div id="result"></div>
            
            <script>
                function showResult(data) {
                    document.getElementById('result').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                }
                
                async function getCurrentVersion() {
                    try {
                        const response = await fetch('/api/version');
                        const data = await response.json();
                        showResult(data);
                    } catch (e) {
                        showResult({error: e.message});
                    }
                }
                
                async function bumpVersion() {
                    try {
                        const type = document.getElementById('bumpType').value;
                        const response = await fetch(`/api/bump?type=${type}`);
                        const data = await response.json();
                        showResult(data);
                    } catch (e) {
                        showResult({error: e.message});
                    }
                }
                
                async function validateVersion() {
                    try {
                        const version = document.getElementById('validateInput').value;
                        const response = await fetch(`/api/validate?version=${version}`);
                        const data = await response.json();
                        showResult(data);
                    } catch (e) {
                        showResult({error: e.message});
                    }
                }
            </script>
        </body>
        </html>
        """
        self._send_html(html)
    
    def _get_version(self):
        """Текстовая версия"""
        version = get_current_version()
        self._send_text(f"Current version: {version}")
    
    def _get_version_json(self):
        """JSON версия"""
        version = get_current_version()
        vm = VersionManager()
        
        # Читаем дополнительную информацию из файла
        version_info = {'version': version}
        if vm.version_file.exists():
            try:
                with open(vm.version_file, 'r') as f:
                    version_info = json.load(f)
            except:
                pass
        
        self._send_json({
            'success': True,
            'version': version,
            'info': version_info
        })
    
    def _bump_version(self, bump_type, prerelease_id):
        """Увеличение версии"""
        old_version = get_current_version()
        new_version = bump_version(bump_type, prerelease_id)
        
        self._send_json({
            'success': True,
            'old_version': old_version,
            'new_version': new_version,
            'bump_type': bump_type
        })
    
    def _validate_version(self, version):
        """Валидация версии"""
        vm = VersionManager()
        is_valid = vm._is_valid_semver(version)
        
        self._send_json({
            'success': True,
            'version': version,
            'valid': is_valid
        })
    
    def _health_check(self):
        """Проверка здоровья сервиса"""
        self._send_json({
            'status': 'healthy',
            'service': 'version-manager-api',
            'current_version': get_current_version()
        })
    
    def _send_json(self, data):
        """Отправка JSON ответа"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def _send_html(self, html):
        """Отправка HTML ответа"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def _send_text(self, text):
        """Отправка текстового ответа"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(text.encode('utf-8'))
    
    def _send_error(self, code, message):
        """Отправка ошибки"""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        error_data = {'success': False, 'error': message, 'code': code}
        self.wfile.write(json.dumps(error_data).encode('utf-8'))


def main():
    """Запуск веб-сервера"""
    port = int(os.environ.get('PORT', 8080))
    server_address = ('', port)
    httpd = HTTPServer(server_address, VersionAPIHandler)
    
    print(f"🚀 Version Manager API запущен на порту {port}")
    print(f"📖 Документация: http://localhost:{port}/")
    print(f"⚡ API эндпоинты:")
    print(f"   GET  /api/version - получить версию")  
    print(f"   GET  /api/bump?type=patch - увеличить версию")
    print(f"   GET  /api/validate?version=1.0.0 - валидировать")
    print(f"   GET  /health - проверка здоровья")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Сервер остановлен")
        httpd.server_close()


if __name__ == '__main__':
    main()