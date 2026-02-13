# -*- coding: utf-8 -*-
import threading
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

import keyring

SERVICE_NAME = "ask-michal"
TOKEN_KEY = "jwt_token"
CALLBACK_PORT = 8765


class _CallbackHandler(BaseHTTPRequestHandler):
    """Temporary HTTP handler to capture OAuth callback token."""

    token: str | None = None

    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if "token" in params:
            _CallbackHandler.token = params["token"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            html = (
                '<!DOCTYPE html><html dir="rtl" lang="he"><body '
                'style="font-family:sans-serif;text-align:center;padding:50px">'
                "<h2>ההתחברות הצליחה! ניתן לסגור חלון זה.</h2>"
                "</body></html>"
            )
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress HTTP log output


def login(server_url: str) -> str:
    """Perform OAuth login flow: opens browser, captures JWT via localhost callback."""
    _CallbackHandler.token = None

    server = HTTPServer(("localhost", CALLBACK_PORT), _CallbackHandler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    login_url = f"{server_url}/auth/login?redirect_port={CALLBACK_PORT}"
    webbrowser.open(login_url)

    thread.join(timeout=120)
    server.server_close()

    if _CallbackHandler.token:
        save_token(_CallbackHandler.token)
        return _CallbackHandler.token

    raise RuntimeError("Authentication timed out or failed")


def save_token(token: str):
    keyring.set_password(SERVICE_NAME, TOKEN_KEY, token)


def load_token() -> str | None:
    return keyring.get_password(SERVICE_NAME, TOKEN_KEY)


def clear_token():
    try:
        keyring.delete_password(SERVICE_NAME, TOKEN_KEY)
    except keyring.errors.PasswordDeleteError:
        pass
