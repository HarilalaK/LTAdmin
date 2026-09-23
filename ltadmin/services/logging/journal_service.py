"""Journal applicatif en base (table JOURNAL) : qui a fait quoi, quand, sur quoi.

Toutes les écritures sont « au mieux » : un échec de journalisation est tracé
dans le fichier technique mais ne fait jamais échouer l'opération.
"""

from __future__ import annotations

import datetime as _dt
from typing import List, Optional

from ltadmin.data.access_database import AccessDatabase
from ltadmin.data.schema import Tables
from ltadmin.models.entities import JournalEntry
from ltadmin.repositories.admin_repository import AdminRepository
from ltadmin.services.logging.app_logger import AppLogger


class JournalService:

    def __init__(self, database: AccessDatabase, logger: AppLogger):
        self._admin = AdminRepository(database)
        self._logger = logger

    def log(self, code_utr: Optional[str], action: str,
            table_cible: Optional[str] = None, id_cible: Optional[int] = None,
            detail: Optional[str] = None) -> None:
        try:
            self._admin.insert_journal(JournalEntry(
                date_log=_dt.datetime.now(),
                code_utr=code_utr.strip() if code_utr and code_utr.strip() else None,
                action_log=JournalService.truncate(action, 80),
                table_cible=table_cible.strip() if table_cible and table_cible.strip() else None,
                id_cible=id_cible,
                detail=detail,
            ))
        except Exception as ex:
            self._logger.warning(f"Journalisation impossible ({action}) : {ex}")

    def log_connexion(self, code_utr: str, reussie: bool) -> None:
        self.log(
            code_utr,
            "CONNEXION" if reussie else "CONNEXION_REFUSEE",
            Tables.UTILISATEUR, None,
            "Ouverture de session." if reussie
            else "Identifiant ou mot de passe incorrect.")

    def log_creation(self, code_utr: str, table: str, id_cible: Optional[int],
                     detail: Optional[str] = None) -> None:
        self.log(code_utr, "CREATION", table, id_cible, detail)

    def log_modification(self, code_utr: str, table: str, id_cible: Optional[int],
                         detail: Optional[str] = None) -> None:
        self.log(code_utr, "MODIFICATION", table, id_cible, detail)

    def log_suppression(self, code_utr: str, table: str, id_cible: Optional[int],
                        detail: Optional[str] = None) -> None:
        self.log(code_utr, "SUPPRESSION", table, id_cible, detail)

    def log_operation(self, code_utr: str, operation: str, table: Optional[str],
                      id_cible: Optional[int], detail: Optional[str] = None) -> None:
        self.log(code_utr, operation, table, id_cible, detail)

    def consulter(self, depuis=None, code_utr: Optional[str] = None,
                  action: Optional[str] = None, max_rows: int = 500) -> List[JournalEntry]:
        try:
            return self._admin.list_journal(depuis, code_utr, action, max_rows)
        except Exception as ex:
            self._logger.error("Consultation du journal", ex)
            return []

    @staticmethod
    def truncate(value: str, max_length: int) -> str:
        return value if len(value) <= max_length else value[:max_length]
