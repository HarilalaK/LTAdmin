"""Serveur HTTP local : API JSON (``/api/...``) + fichiers statiques de
l'interface (``ltadmin/web/static``).

Bibliothèque standard uniquement (``http.server``) : aucun framework à
installer sur les postes de l'établissement. Le serveur est multi-threads,
la base SQLite étant protégée par le verrou de :class:`Database`.
"""

from __future__ import annotations

import datetime as _dt
import json
import mimetypes
import os
import posixpath
import threading
import traceback
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlsplit

from ltadmin.core.result import Result
from ltadmin.services.app_composition import AppServices
from ltadmin.services.auth import habilitations
from ltadmin.web import api_admin, api_finance, api_pedagogie, api_scolarite
from ltadmin.web.routing import (PUBLIC, HttpError, Request, Response, Router,
                                 error_response, result_response)
from ltadmin.web.serialization import dumps
from ltadmin.web.sessions import COOKIE_NAME, SessionStore

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
MAX_BODY_BYTES = 8 * 1024 * 1024

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("font/woff2", ".woff2")


class WebApplication:
    """Assemble services, sessions et routes ; partagé par toutes les requêtes."""

    def __init__(self, services: AppServices, static_dir: str = STATIC_DIR,
                 secure_cookie: bool = False):
        self.services = services
        self.sessions = SessionStore()
        self.router = Router()
        self.static_dir = static_dir
        self.secure_cookie = secure_cookie
        self.started_at = _dt.datetime.now()
        api_scolarite.register(self.router)
        api_pedagogie.register(self.router)
        api_finance.register(self.router)
        api_admin.register(self.router)

    # ----- Cookies -----

    def session_cookie(self, token: str, expire: bool = False) -> str:
        parts = [f"{COOKIE_NAME}={token}", "Path=/", "HttpOnly", "SameSite=Lax"]
        if expire:
            parts.append("Max-Age=0")
        if self.secure_cookie:
            parts.append("Secure")
        return "; ".join(parts)

    # ----- Dispatch -----

    def handle(self, method: str, raw_path: str, headers: Dict[str, str], body: bytes,
               client: str = "") -> Response:
        split = urlsplit(raw_path)
        path = split.path
        query = {k: v[-1] for k, v in parse_qs(split.query, keep_blank_values=True).items()}
        cookies = _parse_cookies(headers.get("cookie", ""))
        token = cookies.get(COOKIE_NAME)
        session = self.sessions.get(token)
        route, params, path_known = self.router.match(method, path)
        if route is None:
            if path_known:
                return error_response(405, "Méthode non autorisée.", "METHODE")
            return error_response(404, "Ressource introuvable.", "INTROUVABLE")
        if route.module != PUBLIC:
            if session is None:
                return error_response(401, "Session expirée ou absente : reconnectez-vous.",
                                      "AUTHENTIFICATION")
            if route.module is not None and not habilitations.can_access(session.role, route.module):
                return error_response(
                    403, f"Action non autorisée pour votre profil ({session.role}) : "
                         f"module « {route.module} ».", "HABILITATION")
        parsed_body: Any = None
        if body:
            content_type = headers.get("content-type", "")
            if "json" in content_type or body[:1] in (b"{", b"["):
                try:
                    parsed_body = json.loads(body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as ex:
                    return error_response(400, f"Corps JSON illisible : {ex}", "VALIDATION")
        request = Request(method=method, path=path, query=query, body=parsed_body,
                          headers=headers, cookies=cookies, session=session,
                          services=self.services, app=self, path_params=params,
                          session_token=token, client=client)
        try:
            outcome = route.handler(request)
        except HttpError as ex:
            return error_response(ex.status, ex.message, ex.code, ex.errors)
        except Exception as ex:  # pragma: no cover - garde-fou
            self.services.logger.error(f"API {method} {path}", ex)
            traceback.print_exc()
            return error_response(500, "Erreur interne : " + str(ex), "TECHNIQUE")
        if isinstance(outcome, Response):
            return outcome
        if isinstance(outcome, Result):
            return result_response(outcome)
        return Response(body={"ok": True, "message": "", "code": None, "errors": [],
                              "value": outcome})

    # ----- Fichiers statiques -----

    def static_file(self, path: str) -> Optional[Tuple[bytes, str]]:
        """Retourne (contenu, type MIME) ou ``None`` ; ``/`` → ``index.html``."""
        relative = posixpath.normpath(path.lstrip("/")) if path not in ("", "/") else "index.html"
        if relative in ("", "."):
            relative = "index.html"
        if relative.startswith("..") or os.path.isabs(relative):
            return None
        full = os.path.join(self.static_dir, *relative.split("/"))
        if os.path.isdir(full):
            full = os.path.join(full, "index.html")
        if not os.path.isfile(full):
            return None
        if os.path.commonpath([os.path.abspath(full), os.path.abspath(self.static_dir)]) != \
                os.path.abspath(self.static_dir):
            return None
        content_type = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in (
                "application/javascript", "application/json", "image/svg+xml"):
            content_type += "; charset=utf-8"
        with open(full, "rb") as handle:
            return handle.read(), content_type


def _parse_cookies(header: str) -> Dict[str, str]:
    cookies: Dict[str, str] = {}
    if not header:
        return cookies
    try:
        jar: SimpleCookie = SimpleCookie()
        jar.load(header)
        for key, morsel in jar.items():
            cookies[key] = morsel.value
    except Exception:
        for part in header.split(";"):
            if "=" in part:
                key, value = part.strip().split("=", 1)
                cookies[key.strip()] = value.strip()
    return cookies


class LtadminRequestHandler(BaseHTTPRequestHandler):
    server_version = "LTAdmin/2.0"
    sys_version = ""
    protocol_version = "HTTP/1.1"
    app: WebApplication  # injecté par make_handler

    # Journalisation silencieuse (les erreurs passent par AppLogger).
    def log_message(self, format: str, *args) -> None:  # noqa: A002
        if os.environ.get("LTADMIN_HTTP_LOG"):
            super().log_message(format, *args)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return b""
        if length > MAX_BODY_BYTES:
            raise HttpError(413, "Requête trop volumineuse.", "VALIDATION")
        return self.rfile.read(length)

    def _dispatch(self, method: str) -> None:
        path = self.path
        try:
            if path.startswith("/api/") or path == "/api":
                body = self._read_body()
                headers = {k.lower(): v for k, v in self.headers.items()}
                response = self.app.handle(method, path, headers, body,
                                           client=self.client_address[0])
                self._send(response)
                return
            if method not in ("GET", "HEAD"):
                self._send(error_response(405, "Méthode non autorisée.", "METHODE"))
                return
            static = self.app.static_file(urlsplit(path).path)
            if static is None:
                # Application monopage : toute route inconnue renvoie index.html.
                static = self.app.static_file("/index.html")
                if static is None:
                    self._send(error_response(404, "Interface introuvable.", "INTROUVABLE"))
                    return
            content, content_type = static
            self._send(Response(raw=content, content_type=content_type,
                                headers={"Cache-Control": "no-cache"}), head_only=method == "HEAD")
        except HttpError as ex:
            self._send(error_response(ex.status, ex.message, ex.code, ex.errors))
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as ex:  # pragma: no cover
            traceback.print_exc()
            try:
                self._send(error_response(500, "Erreur interne : " + str(ex), "TECHNIQUE"))
            except Exception:
                pass

    def _send(self, response: Response, head_only: bool = False) -> None:
        payload = response.raw if response.raw is not None else dumps(response.body).encode("utf-8")
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("X-Content-Type-Options", "nosniff")
        for key, value in response.headers.items():
            self.send_header(key, value)
        self.end_headers()
        if not head_only:
            self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_HEAD(self) -> None:  # noqa: N802
        self._dispatch("HEAD")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def do_PUT(self) -> None:  # noqa: N802
        self._dispatch("PUT")

    def do_DELETE(self) -> None:  # noqa: N802
        self._dispatch("DELETE")


def make_handler(app: WebApplication):
    return type("BoundRequestHandler", (LtadminRequestHandler,), {"app": app})


class LtadminHttpServer:
    """Serveur en arrière-plan : ``start()`` retourne dès que le port écoute."""

    def __init__(self, app: WebApplication, host: str = "127.0.0.1", port: int = 0):
        self.app = app
        self.host = host
        self._server = ThreadingHTTPServer((host, port), make_handler(app))
        self._server.daemon_threads = True
        self._thread: Optional[threading.Thread] = None

    @property
    def port(self) -> int:
        return self._server.server_address[1]

    @property
    def url(self) -> str:
        host = "127.0.0.1" if self.host in ("0.0.0.0", "") else self.host
        return f"http://{host}:{self.port}/"

    def start(self) -> "LtadminHttpServer":
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        name="ltadmin-http", daemon=True)
        self._thread.start()
        return self

    def serve_forever(self) -> None:
        self._server.serve_forever()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)
