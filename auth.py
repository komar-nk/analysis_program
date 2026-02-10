# get_auth_code.py
import webbrowser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        if 'code' in params:
            self.code = params['code'][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"✅ Авторизация успешна! Вернись в консоль.")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"❌ Не получилось")

    def log_message(self, format, *args):
        pass  # Отключаем логи


# Запускаем локальный сервер
server = HTTPServer(('localhost', 8080), Handler)
thread = threading.Thread(target=server.serve_forever)
thread.daemon = True
thread.start()

print("Открываю браузер...")
webbrowser.open("длинная_ссылка_выше")
print("После авторизации сервер получит код автоматически")

# Ждём код
import time

while not hasattr(server, 'code'):
    time.sleep(0.1)

code = server.code
server.shutdown()
print(f"✅ Получен код: {code}")