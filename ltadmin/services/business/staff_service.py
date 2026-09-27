"""Formateurs et programmes (classe × matière × formateur × coefficient).

Matricule formateur automatique ``FOR-AAAA-####`` ; un seul programme par
couple (classe, matière) — index unique ``IX_PROG_UNI``.
"""

from __future__ import annotations

import datetime as _dt
from typing import List, Optional

from ltadmin.core.result import Result, ResultValue
from ltadmin.data import error_helper
from ltadmin.data.database import Database
from ltadmin.data.schema import Tables
from ltadmin.models.dto import ProgrammeDetail
from ltadmin.models.entities import Formateur, Programme
from ltadmin.repositories.staff_repository import StaffRepository
from ltadmin.services.auth.guard import ensure_allowed, ensure_allowed_value
from ltadmin.services.auth.habilitations import Modules
from ltadmin.services.common import ServiceBase
from ltadmin.services.logging.app_logger import AppLogger
from ltadmin.services.logging.journal_service import JournalService
from ltadmin.services.referentiel.parametre_service import ParametreService
from ltadmin.services.validation.validation import StaffValidator


class StaffService(ServiceBase):

    def __init__(self, database: Database, logger: AppLogger,
                 journal: JournalService, parametres: ParametreService):
        super().__init__(database, logger, journal, parametres)
        self._staff = StaffRepository(database)

    # ----- Formateurs -----

    def list_formateurs(self, recherche: Optional[str] = None,
                        actifs_seulement: bool = False) -> List[Formateur]:
        try:
            return self._staff.search_formateurs(recherche, actifs_seulement)
        except Exception as ex:
            self.logger.error("Liste des formateurs", ex)
            return []

    def get_formateur(self, id_formateur: int) -> Optional[Formateur]:
        try:
            return self._staff.get_formateur(id_formateur)
        except Exception as ex:
            self.logger.error("Lecture d’un formateur", ex)
            return None

    def count_formateurs(self) -> int:
        try:
            return self._staff.count_formateurs()
        except Exception as ex:
            self.logger.error("Comptage des formateurs", ex)
            return 0

    def create_formateur(self, formateur: Formateur, code_utr: str) -> ResultValue[int]:
        denied = ensure_allowed_value(code_utr, Modules.FORMATEURS)
        if denied is not None:
            return denied
        validation = StaffValidator.validate_formateur(formateur)
        if not validation.is_valid:
            return self.invalid_value(validation)
        try:
            if not (formateur.matricule or "").strip():
                formateur.matricule = self.generer_matricule()
            if formateur.actif is None:
                formateur.actif = True
            formateur.id_formateur = self._staff.insert_formateur(formateur)
            self.journal.log_creation(code_utr, Tables.FORMATEUR, formateur.id_formateur,
                                      f"{formateur.matricule} — {formateur.nom_complet}")
            return ResultValue.ok(formateur.id_formateur,
                                  f"Formateur {formateur.matricule} créé.")
        except Exception as ex:
            if error_helper.is_unique_violation(ex):
                return ResultValue.fail("Ce matricule est déjà utilisé.", "DOUBLON")
            return self.failure_value("Création d’un formateur", ex)

    def update_formateur(self, formateur: Formateur, code_utr: str) -> Result:
        denied = ensure_allowed(code_utr, Modules.FORMATEURS)
        if denied is not None:
            return denied
        if formateur.id_formateur is None:
            return Result.fail("Formateur introuvable.", "INTROUVABLE")
        validation = StaffValidator.validate_formateur(formateur)
        if not validation.is_valid:
            return self.invalid(validation)
        try:
            if self._staff.update_formateur(formateur) == 0:
                return Result.fail("Formateur introuvable : il a peut-être été supprimé.",
                                   "INTROUVABLE")
            self.journal.log_modification(code_utr, Tables.FORMATEUR, formateur.id_formateur,
                                          f"{formateur.matricule} — {formateur.nom_complet}")
            return Result.ok("Fiche formateur enregistrée.")
        except Exception as ex:
            if error_helper.is_unique_violation(ex):
                return Result.fail("Ce matricule est déjà utilisé.", "DOUBLON")
            return self.failure("Modification d’un formateur", ex)

    def delete_formateur(self, id_formateur: int, code_utr: str) -> Result:
        denied = ensure_allowed(code_utr, Modules.FORMATEURS)
        if denied is not None:
            return denied
        try:
            existing = self._staff.get_formateur(id_formateur)
            if existing is None:
                return Result.fail("Formateur introuvable.", "INTROUVABLE")
            self._staff.delete_formateur(id_formateur)
            self.journal.log_suppression(code_utr, Tables.FORMATEUR, id_formateur,
                                         existing.nom_complet)
            return Result.ok("Formateur supprimé.")
        except Exception as ex:
            if error_helper.is_foreign_key_violation(ex):
                return Result.fail(
                    "Suppression impossible : ce formateur est affecté à des programmes, "
                    "des paies ou des bulletins.", "LIAISON")
            return self.failure("Suppression d’un formateur", ex)

    def generer_matricule(self) -> str:
        prefixe = f"FOR-{_dt.date.today().year}-"
        existants = {m.upper() for m in self._staff.list_matricules(prefixe)}
        sequence = 0
        for matricule in existants:
            try:
                sequence = max(sequence, int(matricule[len(prefixe):]))
            except ValueError:
                continue
        while True:
            sequence += 1
            candidat = prefixe + f"{sequence:04d}"
            if candidat.upper() not in existants:
                return candidat

    # ----- Programmes -----

    def list_programmes(self, id_classe: Optional[int] = None,
                        id_formateur: Optional[int] = None) -> List[ProgrammeDetail]:
        try:
            if id_classe is not None:
                return self._staff.list_by_classe(id_classe)
            if id_formateur is not None:
                return self._staff.list_by_formateur(id_formateur)
            return self._staff.list_all_programmes()
        except Exception as ex:
            self.logger.error("Liste des programmes", ex)
            return []

    def get_programme(self, id_prog: int) -> Optional[Programme]:
        try:
            return self._staff.get_programme(id_prog)
        except Exception as ex:
            self.logger.error("Lecture d’un programme", ex)
            return None

    def save_programme(self, programme: Programme, code_utr: str) -> ResultValue[int]:
        denied = ensure_allowed_value(code_utr, Modules.FORMATEURS)
        if denied is not None:
            return denied
        validation = StaffValidator.validate_programme(programme)
        if not validation.is_valid:
            return self.invalid_value(validation)
        try:
            if programme.coefficient is None:
                programme.coefficient = 1.0
            if programme.note_elimin is None:
                programme.note_elimin = self.parametres.note_eliminatoire
            if programme.id_prog is None:
                doublon = self._staff.get_programme_by_classe_matiere(
                    programme.id_classe, programme.code_matiere)
                if doublon is not None:
                    return ResultValue.fail(
                        "Cette matière figure déjà au programme de la classe.", "DOUBLON")
                programme.id_prog = self._staff.insert_programme(programme)
                self.journal.log_creation(code_utr, Tables.PROGRAMME, programme.id_prog,
                                          f"classe {programme.id_classe} — {programme.code_matiere}")
                return ResultValue.ok(programme.id_prog, "Matière ajoutée au programme.")
            if self._staff.update_programme(programme) == 0:
                return ResultValue.fail("Programme introuvable.", "INTROUVABLE")
            self.journal.log_modification(code_utr, Tables.PROGRAMME, programme.id_prog,
                                          f"classe {programme.id_classe} — {programme.code_matiere}")
            return ResultValue.ok(programme.id_prog, "Programme enregistré.")
        except Exception as ex:
            if error_helper.is_unique_violation(ex):
                return ResultValue.fail(
                    "Cette matière figure déjà au programme de la classe.", "DOUBLON")
            return self.failure_value("Enregistrement d’un programme", ex)

    def delete_programme(self, id_prog: int, code_utr: str) -> Result:
        denied = ensure_allowed(code_utr, Modules.FORMATEURS)
        if denied is not None:
            return denied
        try:
            existing = self._staff.get_programme(id_prog)
            if existing is None:
                return Result.fail("Programme introuvable.", "INTROUVABLE")
            self._staff.delete_programme(id_prog)
            self.journal.log_suppression(code_utr, Tables.PROGRAMME, id_prog,
                                         f"classe {existing.id_classe} — {existing.code_matiere}")
            return Result.ok("Matière retirée du programme.")
        except Exception as ex:
            if error_helper.is_foreign_key_violation(ex):
                return Result.fail(
                    "Suppression impossible : des évaluations ou des créneaux d’emploi du "
                    "temps utilisent ce programme.", "LIAISON")
            return self.failure("Suppression d’un programme", ex)
