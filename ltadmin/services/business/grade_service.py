"""Saisie et suivi des notes de contrôle continu.

Règles : note entre 0 et barème (sauf absent), période non clôturée,
étudiant inscrit dans la classe de l'évaluation, unicité (évaluation, inscrit).
"""

from __future__ import annotations

import datetime as _dt
from typing import List, Optional

from ltadmin.core.result import Result
from ltadmin.data.access_database import AccessDatabase
from ltadmin.data.schema import Tables
from ltadmin.models.dto import MoyenneMatiereRow, MoyennePeriodeRow, NoteSaisieRow
from ltadmin.models.entities import Note
from ltadmin.repositories.enrollment_repository import EnrollmentRepository
from ltadmin.repositories.evaluation_repository import EvaluationRepository
from ltadmin.services.auth.guard import ensure_allowed
from ltadmin.services.auth.habilitations import Modules
from ltadmin.services.common import ServiceBase
from ltadmin.services.logging.app_logger import AppLogger
from ltadmin.services.logging.journal_service import JournalService
from ltadmin.services.referentiel.parametre_service import ParametreService
from ltadmin.services.validation.validation import GradeValidator


class GradeService(ServiceBase):

    def __init__(self, database: AccessDatabase, logger: AppLogger,
                 journal: JournalService, parametres: ParametreService):
        super().__init__(database, logger, journal, parametres)
        self._evaluations = EvaluationRepository(database)
        self._inscriptions = EnrollmentRepository(database)

    def get_grille_saisie(self, id_evaluation: int) -> List[NoteSaisieRow]:
        try:
            evaluation = self._evaluations.get_evaluation_detail(id_evaluation)
            if evaluation is None or evaluation.id_classe is None:
                return []
            return self._evaluations.list_grille_saisie(id_evaluation, evaluation.id_classe)
        except Exception as ex:
            self.logger.error("Chargement de la grille de saisie", ex)
            return []

    def upsert_note(self, id_evaluation: int, id_inscription: int,
                    valeur: Optional[float], absent: bool,
                    observation: Optional[str], code_utr: str) -> Result:
        """Enregistre (insertion ou mise à jour) la note d'un inscrit."""
        denied = ensure_allowed(code_utr, Modules.NOTES)
        if denied is not None:
            return denied
        try:
            evaluation = self._evaluations.get_evaluation_detail(id_evaluation)
            if evaluation is None:
                return Result.fail("Évaluation introuvable.", "INTROUVABLE")
            if evaluation.periode_cloturee is True:
                return Result.fail("Période clôturée : les notes sont figées.", "GESTION")
            if not observation or not observation.strip():
                observation = None
            elif len(observation) > 300:
                return Result.fail("Observation : 300 caractères maximum.", "VALIDATION")

            bareme = evaluation.bareme if evaluation.bareme is not None \
                else self.parametres.bareme_defaut
            validation = GradeValidator.validate_note(valeur, absent, bareme)
            if not validation.is_valid:
                return self.invalid(validation)

            inscription = self._inscriptions.get_by_id(id_inscription)
            if inscription is None:
                return Result.fail("Inscription introuvable.", "INTROUVABLE")
            if inscription.id_classe != evaluation.id_classe:
                return Result.fail(
                    "Cet étudiant n’est pas inscrit dans la classe de cette évaluation.",
                    "GESTION")

            existing = self._evaluations.get_note(id_evaluation, id_inscription)
            if existing is None:
                id_note = self._evaluations.insert_note(Note(
                    id_evaluation=id_evaluation,
                    id_inscription=id_inscription,
                    valeur_note=None if absent else valeur,
                    absent=absent,
                    observation=observation,
                    date_saisie=_dt.datetime.now(),
                    code_utr=code_utr))
                self.journal.log_creation(
                    code_utr, Tables.NOTE, id_note,
                    f"Éval {id_evaluation} / inscrit {id_inscription}")
            else:
                existing.valeur_note = None if absent else valeur
                existing.absent = absent
                existing.observation = observation
                existing.date_saisie = _dt.datetime.now()
                existing.code_utr = code_utr
                self._evaluations.update_note(existing)
                self.journal.log_modification(
                    code_utr, Tables.NOTE, existing.id_note,
                    f"Éval {id_evaluation} / inscrit {id_inscription}")
            return Result.ok("Note enregistrée.")
        except Exception as ex:
            return self.failure("Saisie d’une note", ex)

    def delete_note(self, id_note: int, code_utr: str) -> Result:
        denied = ensure_allowed(code_utr, Modules.NOTES)
        if denied is not None:
            return denied
        try:
            self._evaluations.delete_note(id_note)
            self.journal.log_suppression(code_utr, Tables.NOTE, id_note)
            return Result.ok("Note supprimée.")
        except Exception as ex:
            return self.failure("Suppression d’une note", ex)

    def get_moyennes_matiere(self, id_classe: Optional[int] = None,
                             id_periode: Optional[int] = None) -> List[MoyenneMatiereRow]:
        try:
            return self._evaluations.list_moyennes_matiere(id_classe, id_periode)
        except Exception as ex:
            self.logger.error("Lecture des moyennes par matière", ex)
            return []

    def get_moyennes_periode(self, id_classe: Optional[int] = None,
                             id_periode: Optional[int] = None) -> List[MoyennePeriodeRow]:
        try:
            return self._evaluations.list_moyennes_periode(id_classe, id_periode)
        except Exception as ex:
            self.logger.error("Lecture des moyennes par période", ex)
            return []
