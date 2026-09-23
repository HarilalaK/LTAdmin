"""Localisation de la base LTA_ADM.accdb.

Ordre de résolution : argument de ligne de commande → variable
d'environnement LTADMIN_DB → dossier de l'exécutable → dossier courant →
5 niveaux de dossiers parents (remonter depuis un dossier de travail).
"""

from __future__ import annotations

import os
import sys
from typing import Optional

DATABASE_FILE_NAME = "LTA_ADM.accdb"


class DatabaseLocator:

    def __init__(self, database_file_name: str = DATABASE_FILE_NAME):
        self._database_file_name = database_file_name

    def locate(self, cli_argument: Optional[str] = None) -> str:
        """Retourne le chemin de la base, en la cherchant dans l'ordre documenté."""
        candidate = self._first_existing([
            (cli_argument or "").strip() or None,
            (os.environ.get("LTADMIN_DB") or "").strip() or None,
            self._beside_executable(),
            os.path.join(os.getcwd(), self._database_file_name),
            *self._parent_candidates(),
        ])
        if candidate:
            return os.path.abspath(candidate)
        # Aucune base trouvée : on retourne le chemin par défaut (dossier de
        # l'exécutable) pour que le message d'erreur reste parlant.
        return os.path.abspath(
            self._beside_executable() or os.path.join(os.getcwd(), self._database_file_name))

    def _beside_executable(self) -> Optional[str]:
        try:
            base = os.path.dirname(os.path.abspath(sys.argv[0])) or os.getcwd()
        except Exception:
            base = os.getcwd()
        candidate = os.path.join(base, self._database_file_name)
        return candidate if os.path.isfile(candidate) else None

    def _parent_candidates(self):
        directory = os.getcwd()
        result = []
        for _ in range(5):
            directory = os.path.dirname(directory)
            if not directory:
                break
            candidate = os.path.join(directory, self._database_file_name)
            result.append(candidate)
        return result

    @staticmethod
    def _first_existing(candidates) -> Optional[str]:
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None
