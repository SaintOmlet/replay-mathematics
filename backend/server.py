"""Serve the downloadable math trainer on the user's local machine."""

import argparse
import json
import mimetypes
import re
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from threading import Lock
from collections import deque
from contextlib import contextmanager
import time
from urllib.parse import unquote, urlsplit

from . import coach
from .storage import ApiError, StudyStore


ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
SESSION_ROUTE = re.compile(r"/api/sessions/([a-f0-9]{32})(?:/(answer|hint|next|finish|coach|expire))?\Z")
LESSON_ROUTE = re.compile(r"/api/lessons/([a-z0-9-]+)(?:/(complete))?\Z")
ASSET_TYPES = {".css", ".html", ".js", ".svg", ".png", ".ico", ".woff2", ".webp", ".jpg", ".jpeg", ".webmanifest", ".json"}
BODY_LIMIT = 16 * 1024
SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; "
    "frame-ancestors 'none'; form-action 'self'"
)


class CoachLimiter:
    """Per-server fixed allowance, with sliding windows and bounded concurrency."""
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.calls = deque()
        self.running = 0
        self.lock = Lock()

    @contextmanager
    def reserve(self):
        with self.lock:
            now = self.clock()
            while self.calls and self.calls[0] <= now - 86400:
                self.calls.popleft()
            if self.running >= 2 or len(self.calls) >= 60 or sum(t > now-60 for t in self.calls) >= 6:
                raise ApiError(429, "Лимит наставника: 6 запросов в минуту, 60 за сутки работы сервера, до 2 одновременно.")
            self.calls.append(now)
            self.running += 1
        try:
            yield
        finally:
            with self.lock:
                self.running -= 1


class AppServer(ThreadingHTTPServer):
    def __init__(self, address, store):
        super().__init__(address, Handler)
        self.store = store
        self.coach_limiter = CoachLimiter()


class Handler(BaseHTTPRequestHandler):
    server_version = "Replay"
    sys_version = ""

    def version_string(self):
        return "Replay"

    def setup(self):
        super().setup()
        self.connection.settimeout(15)
    def do_GET(self):
        self.handle_request("GET")

    def do_HEAD(self):
        self.handle_request("HEAD")

    def do_POST(self):
        self.handle_request("POST")

    def log_message(self, format, *args):
        pass

    def handle_request(self, method):
        try:
            self.check_host()
            path = urlsplit(self.path).path
            if path.startswith("/api/"):
                payload = self.read_json() if method == "POST" else None
                data = self.dispatch_api(method, path, payload)
                self.send_json(200, data)
            elif method in ("GET", "HEAD"):
                self.send_asset(path)
            else:
                raise ApiError(404, "Страница не найдена.")
        except ApiError as error:
            self.send_json(error.status, {"error": str(error)})
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as error:
            print(f"Internal request error: {type(error).__name__}", flush=True)
            self.send_json(500, {"error": "Ошибка приложения. Проверь окно сервера."})

    def check_host(self):
        port = self.server.server_address[1]
        allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if port == 80:
            allowed.update({"127.0.0.1", "localhost"})
        if (self.headers.get("Host") or "").lower() not in allowed:
            raise ApiError(403, "Открой приложение по адресу локального сервера.")
        origin = self.headers.get("Origin")
        if origin is not None and origin not in {f"http://{host}" for host in allowed}:
            raise ApiError(403, "Запрос должен идти со страницы приложения.")

    def read_json(self):
        if self.headers.get_content_type() != "application/json":
            raise ApiError(415, "Ожидаются данные JSON.")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ApiError(400, "Неверная длина запроса.") from None
        if length < 0 or length > BODY_LIMIT:
            raise ApiError(413, "Запрос слишком большой.")
        try:
            data = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeError):
            raise ApiError(400, "Не удалось прочитать данные.") from None
        if not isinstance(data, dict):
            raise ApiError(400, "Ожидается объект JSON.")
        return data

    def dispatch_api(self, method, path, payload):
        store = self.server.store
        if method in ("GET", "HEAD"):
            if path == "/api/health":
                return {"status": "ok"}
            if path == "/api/catalog":
                return {**store.catalog(), "coachAvailable": coach.available()}
            if path == "/api/progress":
                return store.progress()
        if method == "POST" and path == "/api/sessions":
            return store.start(payload)
        lesson_match = LESSON_ROUTE.fullmatch(path)
        if lesson_match:
            topic_id, action = lesson_match.groups()
            if method in ("GET", "HEAD") and action is None:
                return store.get_lesson(topic_id)
            if method == "POST" and action == "complete":
                return store.complete_lesson(topic_id)
        match = SESSION_ROUTE.fullmatch(path)
        if match:
            session_id, action = match.groups()
            if method in ("GET", "HEAD") and action is None:
                return store.access(session_id)
            if method == "POST" and action == "coach":
                if not coach.available():
                    raise ApiError(503, "ИИ-наставник отключён. Готовые подсказки доступны.")
                with self.server.coach_limiter.reserve():
                    context = store.coach_context(session_id, payload.get("index"))
                    return coach.reply(context, payload.get("message"))
            if method == "POST" and action:
                return store.access(session_id, action, payload)
        raise ApiError(404, "Запрошенный ресурс не найден.")

    def send_asset(self, path):
        relative = unquote(path).lstrip("/") or "index.html"
        try:
            file = (FRONTEND / relative).resolve()
        except (OSError, ValueError):
            raise ApiError(404, "Страница не найдена.") from None
        if not file.is_relative_to(FRONTEND) or file.suffix not in ASSET_TYPES or not file.is_file():
            raise ApiError(404, "Страница не найдена.")
        mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        if file.suffix == ".js":
            mime = "application/javascript"
        if mime.startswith("text/") or file.suffix in (".json", ".js"):
            mime += "; charset=utf-8"
        self.send_bytes(200, file.read_bytes(), mime)

    def send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_bytes(status, body, "application/json; charset=utf-8")

    def send_bytes(self, status, body, mime):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", SECURITY_POLICY)
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description="Запустить локальный тренажёр математики")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--open-browser", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("Порт должен быть от 0 до 65535.")
    with AppServer(("127.0.0.1", args.port), StudyStore(args.data_dir)) as server:
        url = f"http://127.0.0.1:{server.server_address[1]}"
        print(f"Тренажёр доступен на {url}", flush=True)
        if args.open_browser:
            Thread(target=webbrowser.open, args=(url,), daemon=True).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nСервер остановлен.")


if __name__ == "__main__":
    main()
