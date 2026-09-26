"""Garde d'habilitation côté services (défense en profondeur).

L'interface ne montre que les modules autorisés, mais un écran atteint par un
autre chemin ne serait pas filtré : chaque écriture sensible revérifie donc le
profil de l'utilisateur avant d'agir. Le module est repéré par son nom
métier (``habilitations.Modules``), jamais par un nom de table.
"""

from __future__ import annotations

from typing import Optional

from ltadmin.core.result import Result, ResultValue
from ltadmin.services.auth import habilitations


def ensure_allowed(profil: Optional[str], module: str) -> Optional[Result]:
    """Retourne un ``Result`` d'échec si le profil n'a pas accès au module.

    ``None`` signifie « accès autorisé, continuer ». Les administrateurs
    passent toujours ; les profils inconnus n'ont droit qu'au tableau de bord,
    comme côté menu.
    """
    if habilitations.can_access(profil, module):
        return None
    return Result.fail(
        "Action non autorisée pour votre profil (" + str(profil or "?") + ").",
        "HABILITATION")


def ensure_allowed_value(profil: Optional[str], module: str) -> Optional[ResultValue]:
    """Variante pour les services qui retournent un ``ResultValue``."""
    if habilitations.can_access(profil, module):
        return None
    return ResultValue.fail(
        "Action non autorisée pour votre profil (" + str(profil or "?") + ").",
        "HABILITATION")
