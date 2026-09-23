"""Accès typé aux règles de gestion de la table PARAMETRE.

Les valeurs sont stockées en texte dans Access ; elles sont mises en cache
et rechargées à chaque modification explicite. En cas de valeur absente ou
illisible, les défauts documentés de la base sont utilisés.
"""

from __future__ import annotations

from typing import Dict, Optional

from ltadmin.core.result import Result
from ltadmin.data import error_helper
from ltadmin.data.schema import ParametreKeys, Tables
from ltadmin.repositories.admin_repository import AdminRepository
from ltadmin.data.access_database import AccessDatabase
from ltadmin.services.logging.app_logger import AppLogger
from ltadmin.services.logging.journal_service import JournalService


class ParametreService:

    def __init__(self, database: AccessDatabase, journal: JournalService, logger: AppLogger):
        self._admin = AdminRepository(database)
        self._journal = journal
        self._logger = logger
        self._cache: Dict[str, str] = {}
        self._loaded = False

    # ----- Règles de gestion connues -----

    @property
    def bareme_defaut(self) -> float:
        return self.get_double(ParametreKeys.BAREME_DEFAUT, 20.0)

    @property
    def moy_admission(self) -> float:
        return self.get_double(ParametreKeys.MOY_ADMISSION, 10.0)

    @property
    def note_eliminatoire(self) -> float:
        return self.get_double(ParametreKeys.NOTE_ELIMINATOIRE, 5.0)

    @property
    def poids_cc(self) -> float:
        return self.get_double(ParametreKeys.POIDS_CC, 40.0)

    @property
    def poids_examen(self) -> float:
        return self.get_double(ParametreKeys.POIDS_EXAMEN, 60.0)

    @property
    def seuil_absence(self) -> float:
        return self.get_double(ParametreKeys.SEUIL_ABSENCE, 30.0)

    @property
    def devise(self) -> str:
        return self.get_string(ParametreKeys.DEVISE, "MGA")

    # ----- Accès générique -----

    def get_all(self) -> Dict[str, str]:
        self._ensure_loaded()
        return dict(self._cache)

    def list_parametres(self):
        """Tous les paramètres (entités complètes, avec description)."""
        try:
            return self._admin.list_parametres()
        except Exception as ex:
            self._logger.error("Liste des paramètres", ex)
            return []

    def get_string(self, cle: str, defaut: str) -> str:
        self._ensure_loaded()
        valeur = self._cache.get(cle)
        if valeur is not None and valeur.strip():
            return valeur.strip()
        return defaut

    def get_double(self, cle: str, defaut: float) -> float:
        text = self.get_string(cle, "").replace(",", ".")
        try:
            return float(text)
        except (TypeError, ValueError):
            return defaut

    def set_value(self, cle: str, valeur: str, code_utr: str) -> Result:
        """Modifie une règle de gestion (action explicite, journalisée)."""
        if not cle or not cle.strip():
            return Result.fail("Clé de paramètre obligatoire.", "VALIDATION")
        if len(valeur or "") > 510:
            return Result.fail("Valeur trop longue (510 caractères maximum).", "VALIDATION")
        try:
            updated = self._admin.update_valeur(cle.strip(), (valeur or "").strip())
            if updated == 0:
                return Result.fail(f"Paramètre « {cle} » introuvable.", "INTROUVABLE")
            self.invalidate()
            self._journal.log_modification(code_utr, Tables.PARAMETRE, None, f"{cle} = {valeur}")
            return Result.ok("Paramètre enregistré.")
        except Exception as ex:
            error = error_helper.interpret(ex)
            self._logger.error("Modification de paramètre", ex)
            return Result.fail(error.message, error.code)

    def invalidate(self) -> None:
        self._loaded = False
        self._cache = {}

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        try:
            for parametre in self._admin.list_parametres():
                if parametre.cle and parametre.cle.strip():
                    self._cache[parametre.cle] = parametre.valeur or ""
        except Exception as ex:
            self._logger.error("Chargement des paramètres", ex)
        self._loaded = True
