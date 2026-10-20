"""Local web server: static UI + JSON API + Server-Sent Events.

Security model: binds to 127.0.0.1 only, requires a random token (given in
the URL printed at startup, then kept in an HttpOnly cookie) for every API
call, and rejects requests whose Host header is not local (DNS rebinding).
"""

import json
import mimetypes
import secrets
import socket
import sys
import threading
import webbrowser
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from deepthought import __version__
from deepthought.core import paths
from deepthought.server import api
from deepthought.server.sse import stream_events

LOCAL_HOSTS = {"127.0.0.1", "localhost", "[::1]"}
MAX_BODY = 50 << 20


class HttpError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


class Handler(BaseHTTPRequestHandler):
    server_version = f"DeepThought/{__version__}"
    protocol_version = "HTTP/1.1"

    # quiet logs
    def log_message(self, fmt, *args):
        if self.server.verbose:
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    # -------------------------------------------------------- helpers
    @property
    def app(self):
        return self.server.app

    def _host_ok(self):
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        return host in LOCAL_HOSTS or host == self.server.bind_host

    def _token_ok(self):
        token = self.headers.get("X-DT-Token")
        if not token:
            jar = cookies.SimpleCookie(self.headers.get("Cookie", ""))
            token = jar["dt_token"].value if "dt_token" in jar else ""
        return secrets.compare_digest(token or "", self.server.token)

    def send_json(self, data, status=200, headers=None):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def send_bytes(self, data, content_type, status=200, headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def read_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_BODY:
            raise HttpError(413, "request too large")
        return self.rfile.read(n) if n else b""

    def read_json(self):
        raw = self.read_body()
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except ValueError:
            raise HttpError(400, "invalid JSON body")

    # -------------------------------------------------------- dispatch
    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def _dispatch(self, method):
        try:
            if not self._host_ok():
                raise HttpError(403, "forbidden host")
            url = urlparse(self.path)
            query = {k: v[-1] for k, v in parse_qs(url.query).items()}
            if url.path.startswith("/api/"):
                if not self._token_ok():
                    raise HttpError(401, "missing or invalid token: open the URL printed in your terminal")
                if url.path == "/api/events" and method == "GET":
                    return stream_events(self, self.app.bus)
                result = api.route(self, method, url.path, query)
                if result is not None:
                    self.send_json(result)
                return
            if method != "GET":
                raise HttpError(405, "method not allowed")
            return self._static(url.path, query)
        except HttpError as e:
            self.send_json({"error": e.message}, status=e.status)
        except api.ApiError as e:
            self.send_json({"error": str(e)}, status=e.status)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:  # pragma: no cover
            import traceback

            traceback.print_exc()
            try:
                self.send_json({"error": f"internal error: {e}"}, status=500)
            except OSError:
                pass

    def _static(self, path, query):
        headers = {}
        if path in ("/", "/index.html"):
            if query.get("token") and secrets.compare_digest(query["token"], self.server.token):
                headers["Set-Cookie"] = f"dt_token={self.server.token}; HttpOnly; SameSite=Strict; Path=/"
            elif not self._token_ok():
                body = (b"<!doctype html><meta charset=utf-8><title>DeepThought</title>"
                        b"<body style='font-family:system-ui;background:#111;color:#eee;padding:3em'>"
                        b"<h1>DeepThought</h1><p>Open the link printed in your terminal "
                        b"(it contains your access token).</p>")
                return self.send_bytes(body, "text/html; charset=utf-8", 401)
            path = "/index.html"
        root = paths.WEB_DIR.resolve()
        target = (root / path.lstrip("/")).resolve()
        if not str(target).startswith(str(root)) or not target.is_file():
            raise HttpError(404, "not found")
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if target.suffix in (".js", ".mjs"):
            ctype = "text/javascript"
        headers["Cache-Control"] = "no-cache"
        self.send_bytes(target.read_bytes(), ctype + ("; charset=utf-8" if ctype.startswith("text") else ""),
                        headers=headers)


class App:
    """Long-lived objects shared by every request."""

    def __init__(self):
        from deepthought.core import selfupdate
        from deepthought.core.config import Config
        from deepthought.core.executor import RunManager
        from deepthought.core.registry import Registry

        self.config = Config()
        self.registry = Registry(self.config)
        self.manager = RunManager(self.config, self.registry)
        self.bus = self.manager.bus
        self.update_status = selfupdate.cached_status()
        if self.config["check_updates"]:
            selfupdate.check_in_background(self._update_checked)

    def _update_checked(self, status):
        self.update_status = status
        self.bus.publish({"type": "update", "status": status})


def _free_port(host, start):
    for port in range(start, start + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    raise OSError("no free port found")


def serve(port=0, open_browser=True, project=None, host="127.0.0.1", verbose=False):
    app = App()
    port = _free_port(host, port or app.config["port"])
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    server.app = app
    server.token = secrets.token_urlsafe(18)
    server.bind_host = host
    server.verbose = verbose
    url = f"http://{'localhost' if host == '127.0.0.1' else host}:{port}/?token={server.token}"
    if project:
        p = Path(project).expanduser().resolve()
        if p.is_dir():
            app.manager.projects.add(str(p))
            url += f"#/project/{p}"
    print(f"\n  \x1b[1;36mDeepThought\x1b[0m {__version__} is running at\n\n    \x1b[4m{url}\x1b[0m\n", flush=True)
    print("  Press Ctrl-C to stop.\n", flush=True)
    if open_browser and app.config["open_browser"]:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        print("\nbye 👋")
    finally:
        server.server_close()
    return 0
