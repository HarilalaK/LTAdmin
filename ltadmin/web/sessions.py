"""Sessions utilisateur en mémoire (cookie ``ltadmin_session``).

Le serveur n'est destiné qu'au poste local (ou au réseau interne de
l'établissement) : les sessions vivent le temps du processus, expirent après
une période d'inactivité et sont révoquées à la déconnexion.
"""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from ltadmin.models.db_models import UserSession

COOKIE_NAME = "ltadmin_session"
DEFAULT_IDLE_SECONDS = 12 * 3600


@dataclass
class SessionEntry:
    token: str
    user: UserSession
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)


class SessionStore:

    def __init__(self, idle_seconds: int = DEFAULT_IDLE_SECONDS):
        self._entries: Dict[str, SessionEntry] = {}
        self._lock = threading.Lock()
        self._idle_seconds = idle_seconds

    def create(self, user: UserSession) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._entries[token] = SessionEntry(token=token, user=user)
        return token

    def get(self, token: Optional[str]) -> Optional[UserSession]:
        if not token:
            return None
        now = time.time()
        with self._lock:
            entry = self._entries.get(token)
            if entry is None:
                return None
            if now - entry.last_seen > self._idle_seconds:
                del self._entries[token]
                return None
            entry.last_seen = now
            return entry.user

    def revoke(self, token: Optional[str]) -> None:
        if not token:
            return
        with self._lock:
            self._entries.pop(token, None)

    def revoke_user(self, login: str) -> int:
        """Révoque toutes les sessions d'un compte (désactivation, suppression)."""
        removed = 0
        with self._lock:
            for token in [t for t, e in self._entries.items()
                          if e.user.login.upper() == (login or "").upper()]:
                del self._entries[token]
                removed += 1
        return removed

    def purge(self) -> None:
        now = time.time()
        with self._lock:
            for token in [t for t, e in self._entries.items()
                          if now - e.last_seen > self._idle_seconds]:
                del self._entries[token]

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
