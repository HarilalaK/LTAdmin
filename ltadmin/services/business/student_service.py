"""Gestion des dossiers étudiants : recherche, création (matricule auto),
modification, suppression. Équivalent applicatif de NOUVEAU_MATRICULE()."""

from __future__ import annotations

import datetime as _dt
from typing import List, Optional

from ltadmin.core.result import Result, ResultValue
from ltadmin.data import error_helper
from ltadmin.data.access_database import AccessDatabase
from ltadmin.data.schema import Tables
from ltadmin.models.entities import Etudiant
from ltadmin.repositories.student_repository import StudentRepository
from ltadmin.services.common import ServiceBase
from ltadmin.services.logging.app_logger import AppLogger
from ltadmin.services.logging.journal_service import JournalService
from ltadmin.services.referentiel.parametre_service import ParametreService
from ltadmin.services.validation.validation import StudentValidator


class StudentService(ServiceBase):

    def __init__(self, database: AccessDatabase, logger: AppLogger,
                 journal: JournalService, parametres: ParametreService):
        super().__init__(database, logger, journal, parametres)
        self._etudiants = StudentRepository(database)

    def search(self, recherche: Optional[str], max_rows: int = 500) -> List[Etudiant]:
        try:
            return self._etudiants.search(recherche, max_rows)
        except Exception as ex:
            self.logger.error("Recherche d’étudiants", ex)
            return []

    def get(self, id_etudiant: int) -> Optional[Etudiant]:
        try:
            return self._etudiants.get_by_id(id_etudiant)
        except Exception as ex:
            self.logger.error("Lecture d’un étudiant", ex)
            return None

    def count(self) -> int:
        try:
            return self._etudiants.count()
        except Exception as ex:
            self.logger.error("Comptage des étudiants", ex)
            return 0

    def create(self, etudiant: Etudiant, code_utr: str) -> ResultValue[int]:
        validation = StudentValidator.validate(etudiant)
        if not validation.is_valid:
            return self.invalid_value(validation)
        try:
            if not (etudiant.matricule or "").strip():
                etudiant.matricule = self.generer_matricule()
            etudiant.date_creation = _dt.datetime.now()
            if not (etudiant.statut or "").strip():
                etudiant.statut = "ACTIF"
            etudiant.id_etudiant = self._etudiants.insert(etudiant)
            self.journal.log_creation(
                code_utr, Tables.ETUDIANT, etudiant.id_etudiant,
                f"{etudiant.matricule} — {etudiant.nom_complet}".strip())
            return ResultValue.ok(etudiant.id_etudiant,
                                  f"Étudiant {etudiant.matricule} créé.")
        except Exception as ex:
            if error_helper.is_unique_violation(ex):
                return ResultValue.fail(
                    "Ce matricule est déjà utilisé par un autre étudiant.", "DOUBLON")
            return self.failure_value("Création d’un étudiant", ex)

    def update(self, etudiant: Etudiant, code_utr: str) -> Result:
        if etudiant.id_etudiant is None:
            return Result.fail("Étudiant introuvable.", "INTROUVABLE")
        validation = StudentValidator.validate(etudiant)
        if not validation.is_valid:
            return self.invalid(validation)
        try:
            updated = self._etudiants.update(etudiant)
            if updated == 0:
                return Result.fail(
                    "Étudiant introuvable : il a peut-être été supprimé.", "INTROUVABLE")
            self.journal.log_modification(
                code_utr, Tables.ETUDIANT, etudiant.id_etudiant,
                f"{etudiant.matricule} — {etudiant.nom_complet}".strip())
            return Result.ok("Dossier étudiant enregistré.")
        except Exception as ex:
            if error_helper.is_unique_violation(ex):
                return Result.fail(
                    "Ce matricule est déjà utilisé par un autre étudiant.", "DOUBLON")
            return self.failure("Modification d’un étudiant", ex)

    def delete(self, id_etudiant: int, code_utr: str) -> Result:
        try:
            existing = self._etudiants.get_by_id(id_etudiant)
            if existing is None:
                return Result.fail("Étudiant introuvable.", "INTROUVABLE")
            self._etudiants.delete(id_etudiant)
            self.journal.log_suppression(
                code_utr, Tables.ETUDIANT, id_etudiant,
                f"{existing.matricule} — {existing.nom_complet}".strip())
            return Result.ok("Étudiant supprimé.")
        except Exception as ex:
            if error_helper.is_foreign_key_violation(ex):
                return Result.fail(
                    "Suppression impossible : cet étudiant possède des inscriptions "
                    "ou des données liées.", "LIAISON")
            return self.failure("Suppression d’un étudiant", ex)

    def generer_matricule(self) -> str:
        """Génère un matricule unique ETU-AAAA-#### (année + séquence).

        Réessaie en cas de collision (index unique IX_ETU_MAT).
        """
        prefixe = f"ETU-{_dt.date.today().year}-"
        existants = {m.upper(): m for m in self._etudiants.list_matricules(prefixe)}
        sequence = 0
        for matricule in existants.values():
            suffixe = matricule[len(prefixe):]
            try:
                numero = int(suffixe)
            except ValueError:
                continue
            if numero > sequence:
                sequence = numero
        while True:
            sequence += 1
            candidat = prefixe + f"{sequence:04d}"
            if candidat.upper() not in existants:
                return candidat
