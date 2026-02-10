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
            self.wfile.write(b"OK: Authorization successful! Return to console.")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"ERROR: Failed to get authorization code")

    def log_message(self, format, *args):
        pass  # Disable logging


# Start local server
server = HTTPServer(('localhost', 8080), Handler)
thread = threading.Thread(target=server.serve_forever)
thread.daemon = True
thread.start()

print("Opening browser...")
webbrowser.open("LONG_AUTH_URL_HERE")
print("After authorization, the server will receive the code automatically")

# Wait for code
import time

while not hasattr(server, 'code'):
    time.sleep(0.1)

code = server.code
server.shutdown()
print(f"Success! Got code: {code}")