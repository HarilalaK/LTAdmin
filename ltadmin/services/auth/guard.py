"""Garde d'habilitation côté services (défense en profondeur).

L'API n'expose que les modules autorisés au profil connecté, mais chaque
écriture sensible revérifie l'habilitation avant d'agir. Les services
reçoivent le ``CODE_UTR`` de l'utilisateur (utilisé pour le journal) : la
garde résout son **profil** dans la table ``UTILISATEUR`` via le résolveur
installé par :class:`~ltadmin.services.app_composition.AppServices`.

Si aucun compte ne porte ce code (tests unitaires, scripts), la valeur est
interprétée directement comme un libellé de profil (« Enseignant »,
« ADMIN »…), ce qui conserve le comportement historique.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

from ltadmin.core.result import Result, ResultValue
from ltadmin.services.auth import habilitations

ProfileResolver = Callable[[str], Optional[str]]

_resolver: Optional[ProfileResolver] = None
_resolver_lock = threading.Lock()


def set_profile_resolver(resolver: Optional[ProfileResolver]) -> None:
    """Installe la fonction ``code_utr → profil`` (``None`` = désactiver)."""
    global _resolver
    with _resolver_lock:
        _resolver = resolver


def resolve_profile(code_utr_ou_profil: Optional[str]) -> Optional[str]:
    """Profil normalisé d'un code utilisateur (ou du libellé passé tel quel)."""
    value = (code_utr_ou_profil or "").strip()
    if not value:
        return None
    resolver = _resolver
    if resolver is not None:
        try:
            profil = resolver(value)
        except Exception:
            profil = None
        if profil:
            return habilitations.normalize_profil(profil)
    return habilitations.normalize_profil(value)


def is_allowed(code_utr_ou_profil: Optional[str], module: str) -> bool:
    return habilitations.can_access(resolve_profile(code_utr_ou_profil), module)


def ensure_allowed(code_utr_ou_profil: Optional[str], module: str) -> Optional[Result]:
    """``None`` si l'accès est autorisé, sinon un ``Result`` d'échec ``HABILITATION``."""
    if is_allowed(code_utr_ou_profil, module):
        return None
    return Result.fail(_message(code_utr_ou_profil, module), "HABILITATION")


def ensure_allowed_value(code_utr_ou_profil: Optional[str], module: str) -> Optional[ResultValue]:
    """Variante pour les services qui retournent un ``ResultValue``."""
    if is_allowed(code_utr_ou_profil, module):
        return None
    return ResultValue.fail(_message(code_utr_ou_profil, module), "HABILITATION")


def _message(code_utr_ou_profil: Optional[str], module: str) -> str:
    profil = resolve_profile(code_utr_ou_profil) or "?"
    return f"Action non autorisée pour votre profil ({profil}) : module « {module} »."
