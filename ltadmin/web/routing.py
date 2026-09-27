"""Routeur minimal : enregistrement des routes, contexte de requête, réponses.

Chaque route déclare la méthode HTTP, un motif de chemin (``{id}`` capture
un segment) et le **module métier** requis (``habilitations.Modules``) :

- ``module=PUBLIC`` : accessible sans session (connexion, santé) ;
- ``module=None`` : session requise, quel que soit le profil (référentiels
  en lecture, tableau de bord…) ;
- ``module=Modules.X`` : session requise **et** profil habilité au module.

Les fonctions de route reçoivent un :class:`Request` et retournent soit une
valeur sérialisable, soit un :class:`Response`, soit un ``Result`` de
service (traduit automatiquement en JSON + code HTTP).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Pattern, Tuple

from ltadmin.core.result import Result, ResultValue
from ltadmin.models.db_models import UserSession
from ltadmin.services.auth import habilitations
from ltadmin.web.serialization import parse_bool, parse_datetime, parse_int

PUBLIC = "__public__"

_STATUS_BY_CODE = {
    None: 200,
    "VALIDATION": 400,
    "REQUIS": 400,
    "TROP_LONG": 400,
    "DEPASSEMENT": 400,
    "AUTHENTIFICATION": 401,
    "HABILITATION": 403,
    "INTROUVABLE": 404,
    "DOUBLON": 409,
    "LIAISON": 409,
    "GESTION": 409,
    "VERROUILLE": 423,
    "TECHNIQUE": 500,
}


class HttpError(Exception):
    """Erreur HTTP explicite (message français + code stable)."""

    def __init__(self, status: int, message: str, code: str = "VALIDATION",
                 errors: Optional[List[str]] = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.code = code
        self.errors = errors or []


@dataclass
class Response:
    body: Any = None
    status: int = 200
    headers: Dict[str, str] = field(default_factory=dict)
    raw: Optional[bytes] = None
    content_type: str = "application/json; charset=utf-8"


@dataclass
class Request:
    method: str
    path: str
    query: Dict[str, str]
    body: Any
    headers: Dict[str, str]
    cookies: Dict[str, str]
    session: Optional[UserSession]
    services: Any
    app: Any
    path_params: Dict[str, str] = field(default_factory=dict)
    session_token: Optional[str] = None
    client: str = ""

    # ----- Accès typés aux paramètres -----

    @property
    def login(self) -> str:
        return self.session.login if self.session else ""

    @property
    def role(self) -> str:
        return self.session.role if self.session else ""

    def param(self, name: str, default: Optional[str] = None) -> Optional[str]:
        value = self.query.get(name)
        if value is None or value == "":
            return default
        return value

    def param_int(self, name: str, default: Optional[int] = None) -> Optional[int]:
        value = self.param(name)
        if value is None:
            return default
        try:
            return parse_int(value)
        except ValueError:
            raise HttpError(400, f"Paramètre « {name} » : entier attendu.")

    def param_bool(self, name: str, default: bool = False) -> bool:
        value = self.param(name)
        if value is None:
            return default
        try:
            parsed = parse_bool(value)
        except ValueError:
            raise HttpError(400, f"Paramètre « {name} » : booléen attendu.")
        return default if parsed is None else parsed

    def param_date(self, name: str):
        value = self.param(name)
        if value is None:
            return None
        try:
            return parse_datetime(value)
        except ValueError as ex:
            raise HttpError(400, f"Paramètre « {name} » : {ex}")

    def path_int(self, name: str) -> int:
        value = self.path_params.get(name)
        try:
            return int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            raise HttpError(400, f"Identifiant « {name} » invalide.")

    def path_str(self, name: str) -> str:
        return self.path_params.get(name, "")

    @property
    def data(self) -> Dict[str, Any]:
        """Corps JSON sous forme de dictionnaire (vide si absent)."""
        if self.body is None:
            return {}
        if not isinstance(self.body, dict):
            raise HttpError(400, "Corps de requête JSON attendu (objet).")
        return self.body

    def field(self, name: str, required: bool = False, default: Any = None) -> Any:
        value = self.data.get(name, default)
        if required and (value is None or (isinstance(value, str) and not value.strip())):
            raise HttpError(400, f"Champ « {name} » obligatoire.", "REQUIS")
        return value

    def field_int(self, name: str, required: bool = False) -> Optional[int]:
        value = self.field(name, required)
        if value is None or value == "":
            return None
        try:
            return parse_int(value)
        except (ValueError, TypeError):
            raise HttpError(400, f"Champ « {name} » : entier attendu.")

    def field_bool(self, name: str, default: bool = False) -> bool:
        value = self.field(name)
        if value is None:
            return default
        try:
            parsed = parse_bool(value)
        except ValueError:
            raise HttpError(400, f"Champ « {name} » : booléen attendu.")
        return default if parsed is None else parsed

    def field_date(self, name: str, required: bool = False):
        value = self.field(name, required)
        if value is None or value == "":
            return None
        try:
            return parse_datetime(value)
        except ValueError as ex:
            raise HttpError(400, f"Champ « {name} » : {ex}")

    def require_module(self, module: str) -> None:
        """Vérification d'habilitation ponctuelle (routes multi-modules)."""
        if not habilitations.can_access(self.role, module):
            raise HttpError(403, f"Accès refusé au module « {module} » pour votre profil.",
                            "HABILITATION")


@dataclass
class Route:
    method: str
    pattern: Pattern[str]
    template: str
    handler: Callable[[Request], Any]
    module: Optional[str]


class Router:

    def __init__(self):
        self._routes: List[Route] = []

    def add(self, method: str, template: str, handler: Callable[[Request], Any],
            module: Optional[str]) -> None:
        regex = "^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", template) + "/?$"
        self._routes.append(Route(method.upper(), re.compile(regex), template, handler, module))

    def route(self, method: str, template: str, module: Optional[str] = None):
        def decorator(fn: Callable[[Request], Any]):
            self.add(method, template, fn, module)
            return fn
        return decorator

    def get(self, template: str, module: Optional[str] = None):
        return self.route("GET", template, module)

    def post(self, template: str, module: Optional[str] = None):
        return self.route("POST", template, module)

    def put(self, template: str, module: Optional[str] = None):
        return self.route("PUT", template, module)

    def delete(self, template: str, module: Optional[str] = None):
        return self.route("DELETE", template, module)

    def match(self, method: str, path: str) -> Tuple[Optional[Route], Dict[str, str], bool]:
        """Retourne (route, paramètres, chemin_connu_mais_mauvaise_méthode)."""
        path_known = False
        for route in self._routes:
            match = route.pattern.match(path)
            if match is None:
                continue
            path_known = True
            if route.method == method.upper():
                return route, {k: _unquote(v) for k, v in match.groupdict().items()}, False
        return None, {}, path_known

    @property
    def routes(self) -> List[Route]:
        return list(self._routes)


def _unquote(value: str) -> str:
    from urllib.parse import unquote
    return unquote(value)


# ---------------------------------------------------------------------------
# Traduction des Result de services
# ---------------------------------------------------------------------------


def result_response(result: Result, value: Any = None) -> Response:
    """JSON ``{ok, message, code, errors, value}`` + statut HTTP dérivé du code."""
    payload: Dict[str, Any] = {
        "ok": result.is_success,
        "message": result.message,
        "code": result.code,
        "errors": list(result.errors or []),
    }
    if isinstance(result, ResultValue):
        payload["value"] = result.value
    if value is not None:
        payload["value"] = value
    status = 200 if result.is_success else _STATUS_BY_CODE.get(result.code, 409)
    return Response(body=payload, status=status)


def error_response(status: int, message: str, code: str = "VALIDATION",
                   errors: Optional[List[str]] = None) -> Response:
    return Response(body={"ok": False, "message": message, "code": code,
                          "errors": errors or []}, status=status)


def ok_response(value: Any = None, message: str = "") -> Response:
    return Response(body={"ok": True, "message": message, "code": None,
                          "errors": [], "value": value})
