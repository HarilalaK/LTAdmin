"""Gestion des inscriptions : une ligne par étudiant et par classe
(historique + redoublements), contrôle de l'effectif maximum."""

from __future__ import annotations

import datetime as _dt
from typing import List, Optional

from ltadmin.core.result import Result, ResultValue
from ltadmin.data import error_helper
from ltadmin.data.access_database import AccessDatabase
from ltadmin.data.schema import Tables
from ltadmin.models.dto import InscriptionDetail
from ltadmin.models.entities import Inscription
from ltadmin.repositories.enrollment_repository import EnrollmentRepository
from ltadmin.repositories.referentiel_repository import ReferentielRepository
from ltadmin.repositories.student_repository import StudentRepository
from ltadmin.services.common import ServiceBase
from ltadmin.services.logging.app_logger import AppLogger
from ltadmin.services.logging.journal_service import JournalService
from ltadmin.services.referentiel.parametre_service import ParametreService
from ltadmin.services.validation.validation import EnrollmentValidator


class EnrollmentService(ServiceBase):

    def __init__(self, database: AccessDatabase, logger: AppLogger,
                 journal: JournalService, parametres: ParametreService):
        super().__init__(database, logger, journal, parametres)
        self._inscriptions = EnrollmentRepository(database)
        self._etudiants = StudentRepository(database)
        self._referentiel = ReferentielRepository(database)

    def list_by_classe(self, id_classe: int) -> List[InscriptionDetail]:
        try:
            return self._inscriptions.list_by_classe(id_classe)
        except Exception as ex:
            self.logger.error("Liste des inscrits d’une classe", ex)
            return []

    def list_by_etudiant(self, id_etudiant: int) -> List[InscriptionDetail]:
        try:
            return self._inscriptions.list_by_etudiant(id_etudiant)
        except Exception as ex:
            self.logger.error("Historique des inscriptions d’un étudiant", ex)
            return []

    def get_detail(self, id_inscription: int) -> Optional[InscriptionDetail]:
        try:
            return self._inscriptions.get_detail(id_inscription)
        except Exception as ex:
            self.logger.error("Lecture d’une inscription", ex)
            return None

    def get(self, id_inscription: int) -> Optional[Inscription]:
        try:
            return self._inscriptions.get_by_id(id_inscription)
        except Exception as ex:
            self.logger.error("Lecture d’une inscription", ex)
            return None

    def inscrire(self, inscription: Inscription, code_utr: str) -> ResultValue[int]:
        """Inscrit un étudiant dans une classe (contrôles : doublon, effectif max)."""
        validation = EnrollmentValidator.validate(inscription)
        if not validation.is_valid:
            return self.invalid_value(validation)
        try:
            etudiant = self._etudiants.get_by_id(inscription.id_etudiant)
            if etudiant is None:
                return ResultValue.fail("Étudiant introuvable.", "INTROUVABLE")
            classe = self._referentiel.get_classe(inscription.id_classe)
            if classe is None:
                return ResultValue.fail("Classe introuvable.", "INTROUVABLE")

            doublon = self._inscriptions.get_by_etudiant_classe(
                inscription.id_etudiant, inscription.id_classe)
            if doublon is not None:
                return ResultValue.fail(
                    f"« {etudiant.nom_complet} » est déjà inscrit dans la classe "
                    f"« {classe.libelle} ».", "DOUBLON")

            if classe.effectif_max is not None and classe.effectif_max > 0:
                effectif = self._inscriptions.count_by_classe(classe.id_classe)
                if effectif >= classe.effectif_max:
                    return ResultValue.fail(
                        f"Effectif maximum atteint pour « {classe.libelle} » "
                        f"({effectif}/{classe.effectif_max}).", "GESTION")

            if not (inscription.num_inscription or "").strip():
                inscription.num_inscription = self.generer_numero()
            if inscription.date_inscription is None:
                inscription.date_inscription = _dt.datetime.combine(
                    _dt.date.today(), _dt.time())
            if not (inscription.statut or "").strip():
                inscription.statut = "INSCRIT"

            inscription.id_inscription = self._inscriptions.insert(inscription)
            self.journal.log_creation(
                code_utr, Tables.INSCRIPTION, inscription.id_inscription,
                f"{inscription.num_inscription} — {etudiant.nom_complet} → {classe.libelle}")
            return ResultValue.ok(
                inscription.id_inscription,
                f"Inscription {inscription.num_inscription} enregistrée.")
        except Exception as ex:
            if error_helper.is_unique_violation(ex):
                return ResultValue.fail(
                    "Cette inscription existe déjà (doublon étudiant × classe).", "DOUBLON")
            return self.failure_value("Inscription d’un étudiant", ex)

    def update(self, inscription: Inscription, code_utr: str) -> Result:
        if inscription.id_inscription is None:
            return Result.fail("Inscription introuvable.", "INTROUVABLE")
        validation = EnrollmentValidator.validate(inscription)
        if not validation.is_valid:
            return self.invalid(validation)
        try:
            updated = self._inscriptions.update(inscription)
            if updated == 0:
                return Result.fail(
                    "Inscription introuvable : elle a peut-être été supprimée.", "INTROUVABLE")
            self.journal.log_modification(
                code_utr, Tables.INSCRIPTION, inscription.id_inscription,
                inscription.num_inscription)
            return Result.ok("Inscription enregistrée.")
        except Exception as ex:
            if error_helper.is_unique_violation(ex):
                return ResultValue.fail(
                    "Cette inscription existe déjà (doublon étudiant × classe).", "DOUBLON")
            return self.failure("Modification d’une inscription", ex)

    def enregistrer_sortie(self, id_inscription: int, date_sortie, motif: Optional[str],
                           code_utr: str) -> Result:
        """Enregistre une sortie (date + motif) sans supprimer l'historique."""
        try:
            inscription = self._inscriptions.get_by_id(id_inscription)
            if inscription is None:
                return Result.fail("Inscription introuvable.", "INTROUVABLE")
            inscription.date_sortie = date_sortie
            inscription.motif_sortie = motif
            inscription.statut = "SORTI"
            validation = EnrollmentValidator.validate(inscription)
            if not validation.is_valid:
                return self.invalid(validation)
            self._inscriptions.update(inscription)
            self.journal.log_modification(
                code_utr, Tables.INSCRIPTION, id_inscription, "Sortie enregistrée.")
            return Result.ok("Sortie enregistrée.")
        except Exception as ex:
            return self.failure("Enregistrement d’une sortie", ex)

    def delete(self, id_inscription: int, code_utr: str) -> Result:
        try:
            existing = self._inscriptions.get_by_id(id_inscription)
            if existing is None:
                return Result.fail("Inscription introuvable.", "INTROUVABLE")
            self._inscriptions.delete(id_inscription)
            self.journal.log_suppression(
                code_utr, Tables.INSCRIPTION, id_inscription, existing.num_inscription)
            return Result.ok("Inscription supprimée.")
        except Exception as ex:
            if error_helper.is_foreign_key_violation(ex):
                return Result.fail(
                    "Suppression impossible : cette inscription possède des notes, "
                    "absences, bulletins ou paiements.", "LIAISON")
            return self.failure("Suppression d’une inscription", ex)

    def generer_numero(self) -> str:
        """Génère un numéro d'inscription unique INS-AAAA-####."""
        prefixe = f"INS-{_dt.date.today().year}-"
        existants = {n.upper(): n for n in self._inscriptions.list_numeros(prefixe)}
        sequence = 0
        for numero in existants.values():
            suffixe = numero[len(prefixe):]
            try:
                value = int(suffixe)
            except ValueError:
                continue
            if value > sequence:
                sequence = value
        while True:
            sequence += 1
            candidat = prefixe + f"{sequence:04d}"
            if candidat.upper() not in existants:
                return candidat
