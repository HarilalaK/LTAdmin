"""Gestion des périodes d'évaluation et des évaluations (devoirs, interros).

Règles : barème et poids strictement positifs, période clôturée figée.
"""

from __future__ import annotations

from typing import List, Optional

from ltadmin.core.result import Result, ResultValue
from ltadmin.data import error_helper
from ltadmin.data.access_database import AccessDatabase
from ltadmin.data.schema import Tables
from ltadmin.models.dto import EvaluationDetail
from ltadmin.models.entities import Evaluation, PeriodeEval
from ltadmin.repositories.evaluation_repository import EvaluationRepository
from ltadmin.repositories.staff_repository import StaffRepository
from ltadmin.services.common import ServiceBase
from ltadmin.services.logging.app_logger import AppLogger
from ltadmin.services.logging.journal_service import JournalService
from ltadmin.services.referentiel.parametre_service import ParametreService
from ltadmin.services.validation.validation import EvaluationValidator


class EvaluationService(ServiceBase):

    def __init__(self, database: AccessDatabase, logger: AppLogger,
                 journal: JournalService, parametres: ParametreService):
        super().__init__(database, logger, journal, parametres)
        self._evaluations = EvaluationRepository(database)
        self._personnel = StaffRepository(database)

    # ----- Périodes -----

    def list_periodes(self, id_annee: Optional[int] = None) -> List[PeriodeEval]:
        try:
            return self._evaluations.list_periodes(id_annee)
        except Exception as ex:
            self.logger.error("Liste des périodes d’évaluation", ex)
            return []

    def get_periode(self, id_periode: int) -> Optional[PeriodeEval]:
        try:
            return self._evaluations.get_periode(id_periode)
        except Exception as ex:
            self.logger.error("Lecture d’une période", ex)
            return None

    def create_periode(self, periode: PeriodeEval, code_utr: str) -> ResultValue[int]:
        if periode.id_annee is None:
            # Rattachement automatique à l'année scolaire active.
            from ltadmin.repositories.admin_repository import AdminRepository
            annee = AdminRepository(self.db).get_annee_active()
            if annee is None:
                return ResultValue.fail(
                    "Aucune année scolaire active : activez-en une dans "
                    "l’administration.", "GESTION")
            periode.id_annee = annee.id_annee
        validation = EvaluationValidator.validate_periode(periode)
        if not validation.is_valid:
            return self.invalid_value(validation)
        try:
            id_periode = self._evaluations.insert_periode(periode)
            self.journal.log_creation(code_utr, Tables.PERIODE_EVAL, id_periode, periode.libelle)
            return ResultValue.ok(id_periode, "Période d’évaluation créée.")
        except Exception as ex:
            return self.failure_value("Création d’une période", ex)

    def update_periode(self, periode: PeriodeEval, code_utr: str) -> Result:
        if periode.id_periode is None:
            return Result.fail("Période introuvable.", "INTROUVABLE")
        validation = EvaluationValidator.validate_periode(periode)
        if not validation.is_valid:
            return self.invalid(validation)
        try:
            updated = self._evaluations.update_periode(periode)
            if updated == 0:
                return Result.fail("Période introuvable.", "INTROUVABLE")
            self.journal.log_modification(
                code_utr, Tables.PERIODE_EVAL, periode.id_periode, periode.libelle)
            return Result.ok("Période enregistrée.")
        except Exception as ex:
            return self.failure("Modification d’une période", ex)

    def set_periode_cloturee(self, id_periode: int, cloturee: bool, code_utr: str) -> Result:
        """Clôture (ou rouvre) une période : les notes figées ne sont plus modifiables."""
        try:
            periode = self._evaluations.get_periode(id_periode)
            if periode is None:
                return Result.fail("Période introuvable.", "INTROUVABLE")
            self._evaluations.set_periode_cloturee(id_periode, cloturee)
            self.journal.log_operation(
                code_utr,
                "CLOTURE_PERIODE" if cloturee else "REOUVERTURE_PERIODE",
                Tables.PERIODE_EVAL, id_periode, periode.libelle)
            return Result.ok(
                "Période clôturée : les notes sont figées." if cloturee
                else "Période rouverte.")
        except Exception as ex:
            return self.failure("Clôture d’une période", ex)

    # ----- Évaluations -----

    def list_evaluations(self, id_periode: Optional[int] = None,
                         id_classe: Optional[int] = None,
                         id_prog: Optional[int] = None) -> List[EvaluationDetail]:
        try:
            return self._evaluations.list_evaluations(id_periode, id_classe, id_prog)
        except Exception as ex:
            self.logger.error("Liste des évaluations", ex)
            return []

    def get_evaluation_detail(self, id_evaluation: int) -> Optional[EvaluationDetail]:
        try:
            return self._evaluations.get_evaluation_detail(id_evaluation)
        except Exception as ex:
            self.logger.error("Lecture d’une évaluation", ex)
            return None

    def create_evaluation(self, evaluation: Evaluation, code_utr: str) -> ResultValue[int]:
        if evaluation.bareme is None or evaluation.bareme <= 0:
            evaluation.bareme = self.parametres.bareme_defaut
        if evaluation.poids is None or evaluation.poids <= 0:
            evaluation.poids = 1.0
        validation = EvaluationValidator.validate_evaluation(evaluation)
        if not validation.is_valid:
            return self.invalid_value(validation)
        try:
            periode = self._evaluations.get_periode(evaluation.id_periode)
            if periode is None:
                return ResultValue.fail("Période introuvable.", "INTROUVABLE")
            if periode.cloturee is True:
                return ResultValue.fail(
                    "Période clôturée : rouvrez-la pour ajouter une évaluation.", "GESTION")
            programme = self._personnel.get_programme(evaluation.id_prog)
            if programme is None:
                return ResultValue.fail(
                    "Programme (classe × matière) introuvable.", "INTROUVABLE")
            evaluation.id_evaluation = self._evaluations.insert_evaluation(evaluation)
            self.journal.log_creation(
                code_utr, Tables.EVALUATION, evaluation.id_evaluation,
                evaluation.intitule)
            return ResultValue.ok(evaluation.id_evaluation, "Évaluation créée.")
        except Exception as ex:
            return self.failure_value("Création d’une évaluation", ex)

    def update_evaluation(self, evaluation: Evaluation, code_utr: str) -> Result:
        if evaluation.id_evaluation is None:
            return Result.fail("Évaluation introuvable.", "INTROUVABLE")
        validation = EvaluationValidator.validate_evaluation(evaluation)
        if not validation.is_valid:
            return self.invalid(validation)
        try:
            periode = self._evaluations.get_periode(evaluation.id_periode)
            if periode is not None and periode.cloturee is True:
                return Result.fail(
                    "Période clôturée : rouvrez-la pour modifier cette évaluation.", "GESTION")
            updated = self._evaluations.update_evaluation(evaluation)
            if updated == 0:
                return Result.fail("Évaluation introuvable.", "INTROUVABLE")
            self.journal.log_modification(
                code_utr, Tables.EVALUATION, evaluation.id_evaluation, evaluation.intitule)
            return Result.ok("Évaluation enregistrée.")
        except Exception as ex:
            return self.failure("Modification d’une évaluation", ex)

    def set_publiee(self, id_evaluation: int, publiee: bool, code_utr: str) -> Result:
        try:
            existing = self._evaluations.get_evaluation(id_evaluation)
            if existing is None:
                return Result.fail("Évaluation introuvable.", "INTROUVABLE")
            self._evaluations.set_evaluation_publiee(id_evaluation, publiee)
            self.journal.log_operation(
                code_utr,
                "PUBLICATION_NOTES" if publiee else "DEPUBLICATION_NOTES",
                Tables.EVALUATION, id_evaluation, existing.intitule)
            return Result.ok("Notes publiées." if publiee else "Publication retirée.")
        except Exception as ex:
            return self.failure("Publication d’une évaluation", ex)

    def delete_evaluation(self, id_evaluation: int, code_utr: str) -> Result:
        try:
            existing = self._evaluations.get_evaluation(id_evaluation)
            if existing is None:
                return Result.fail("Évaluation introuvable.", "INTROUVABLE")
            self._evaluations.delete_evaluation(id_evaluation)
            self.journal.log_suppression(
                code_utr, Tables.EVALUATION, id_evaluation, existing.intitule)
            return Result.ok("Évaluation supprimée.")
        except Exception as ex:
            if error_helper.is_foreign_key_violation(ex):
                return Result.fail(
                    "Suppression impossible : des notes sont déjà saisies pour cette "
                    "évaluation.", "LIAISON")
            return self.failure("Suppression d’une évaluation", ex)
