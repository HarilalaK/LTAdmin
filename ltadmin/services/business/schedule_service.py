"""Gestion de l'emploi du temps (EDT) : planification des matières par
classe, détection des conflits (salle et formateur occupés sur le créneau)."""

from __future__ import annotations

from typing import List, Optional

from ltadmin.core.result import Result, ResultValue
from ltadmin.data import error_helper
from ltadmin.data.access_database import AccessDatabase
from ltadmin.data.schema import Tables
from ltadmin.models.dto import EdtSlotDetail
from ltadmin.models.entities import Absence, Creneau, EmploiDuTemps, Seance
from ltadmin.repositories.planning_repository import PlanningRepository
from ltadmin.repositories.referentiel_repository import ReferentielRepository
from ltadmin.repositories.staff_repository import StaffRepository
from ltadmin.services.auth.guard import ensure_allowed, ensure_allowed_value
from ltadmin.services.auth.habilitations import Modules
from ltadmin.services.common import ServiceBase
from ltadmin.services.logging.app_logger import AppLogger
from ltadmin.services.logging.journal_service import JournalService
from ltadmin.services.referentiel.parametre_service import ParametreService
from ltadmin.services.validation.validation import PlanningValidator


class ScheduleService(ServiceBase):

    def __init__(self, database: AccessDatabase, logger: AppLogger,
                 journal: JournalService, parametres: ParametreService):
        super().__init__(database, logger, journal, parametres)
        self._planning = PlanningRepository(database)
        self._referentiel = ReferentielRepository(database)
        self._personnel = StaffRepository(database)

    # ----- Créneaux horaires -----

    def list_creneaux(self) -> List[Creneau]:
        try:
            return self._planning.list_creneaux()
        except Exception as ex:
            self.logger.error("Liste des créneaux", ex)
            return []

    def get_creneau(self, id_creneau: int) -> Optional[Creneau]:
        try:
            return self._planning.get_creneau(id_creneau)
        except Exception as ex:
            self.logger.error("Lecture d’un créneau", ex)
            return None

    def save_creneau(self, creneau: Creneau, code_utr: str) -> Result:
        denied = ensure_allowed(code_utr, Modules.EMPLOI_DU_TEMPS)
        if denied is not None:
            return denied
        validation = PlanningValidator.validate_creneau(creneau)
        if not validation.is_valid:
            return self.invalid(validation)
        try:
            if creneau.id_creneau is None:
                id_creneau = self._planning.insert_creneau(creneau)
                creneau.id_creneau = id_creneau
                self.journal.log_creation(
                    code_utr, Tables.CRENEAU, id_creneau, creneau.libelle)
            else:
                self._planning.update_creneau(creneau)
                self.journal.log_modification(
                    code_utr, Tables.CRENEAU, creneau.id_creneau, creneau.libelle)
            return Result.ok("Créneau enregistré.")
        except Exception as ex:
            return self.failure("Enregistrement d’un créneau", ex)

    def delete_creneau(self, id_creneau: int, code_utr: str) -> Result:
        denied = ensure_allowed(code_utr, Modules.EMPLOI_DU_TEMPS)
        if denied is not None:
            return denied
        try:
            creneau = self._planning.get_creneau(id_creneau)
            if creneau is None:
                return Result.fail("Créneau introuvable.", "INTROUVABLE")
            self._planning.delete_creneau(id_creneau)
            self.journal.log_suppression(
                code_utr, Tables.CRENEAU, id_creneau, creneau.libelle)
            return Result.ok("Créneau supprimé.")
        except Exception as ex:
            if error_helper.is_foreign_key_violation(ex):
                return Result.fail(
                    "Suppression impossible : ce créneau est utilisé par l’emploi "
                    "du temps.", "LIAISON")
            return self.failure("Suppression d’un créneau", ex)

    # ----- Emploi du temps -----

    def list_slots(self, id_classe: Optional[int] = None) -> List[EdtSlotDetail]:
        try:
            if id_classe is None:
                # Toutes les classes : on agrège par classe active connue.
                result: List[EdtSlotDetail] = []
                for classe in self._referentiel.list_classes():
                    result.extend(self._planning.list_slots_by_classe(classe.id_classe))
                return result
            return self._planning.list_slots_by_classe(id_classe)
        except Exception as ex:
            self.logger.error("Liste des créneaux d’emploi du temps", ex)
            return []

    def get_slot(self, id_edt: int) -> Optional[EdtSlotDetail]:
        try:
            return self._planning.get_slot_detail(id_edt)
        except Exception as ex:
            self.logger.error("Lecture d’un créneau d’EDT", ex)
            return None

    def _verifier_conflits(self, slot: EmploiDuTemps,
                           exclude_id_edt: Optional[int]) -> Optional[str]:
        """Conflit salle ou formateur sur le créneau (jour, créneau, actif)."""
        programme = self._personnel.get_programme(slot.id_prog) if slot.id_prog else None
        concurrents = self._planning.list_slots_concurrents(
            slot.jour, slot.id_creneau, exclude_id_edt)
        for concurrent in concurrents:
            if (slot.id_salle is not None and concurrent.id_salle is not None
                    and slot.id_salle == concurrent.id_salle):
                return (f"Conflit : la salle « {concurrent.salle or concurrent.id_salle} » "
                        f"est déjà réservée sur ce créneau.")
            if (programme is not None and programme.id_formateur is not None
                    and concurrent.id_formateur is not None
                    and programme.id_formateur == concurrent.id_formateur):
                return (f"Conflit : le formateur « {concurrent.formateur or ''} » "
                        f"enseigne déjà ailleurs sur ce créneau.")
        return None

    def create_slot(self, slot: EmploiDuTemps, code_utr: str) -> ResultValue[int]:
        denied = ensure_allowed_value(code_utr, Modules.EMPLOI_DU_TEMPS)
        if denied is not None:
            return denied
        validation = PlanningValidator.validate_slot(slot)
        if not validation.is_valid:
            return self.invalid_value(validation)
        try:
            if slot.id_salle is not None:
                salle = self._referentiel.get_salle(slot.id_salle)
                if salle is None:
                    return ResultValue.fail("Salle introuvable.", "INTROUVABLE")
                if salle.disponible is False:
                    return ResultValue.fail(
                        f"La salle « {salle.nom_salle or slot.id_salle} » n’est pas "
                        f"disponible.", "GESTION")
            conflit = self._verifier_conflits(slot, None)
            if conflit is not None:
                return ResultValue.fail(conflit, "GESTION")
            if slot.actif is None:
                slot.actif = True
            id_edt = self._planning.insert_slot(slot)
            slot.id_edt = id_edt
            self.journal.log_creation(
                code_utr, Tables.EMPLOI_DU_TEMPS, id_edt,
                f"{slot.jour} — créneau {slot.id_creneau}")
            return ResultValue.ok(id_edt, "Créneau d’emploi du temps planifié.")
        except Exception as ex:
            return self.failure_value("Planification d’un créneau", ex)

    def update_slot(self, slot: EmploiDuTemps, code_utr: str) -> Result:
        denied = ensure_allowed(code_utr, Modules.EMPLOI_DU_TEMPS)
        if denied is not None:
            return denied
        if slot.id_edt is None:
            return Result.fail("Créneau d’EDT introuvable.", "INTROUVABLE")
        validation = PlanningValidator.validate_slot(slot)
        if not validation.is_valid:
            return self.invalid(validation)
        try:
            if slot.id_salle is not None:
                salle = self._referentiel.get_salle(slot.id_salle)
                if salle is not None and salle.disponible is False:
                    return Result.fail(
                        f"La salle « {salle.nom_salle or slot.id_salle} » n’est pas "
                        f"disponible.", "GESTION")
            conflit = self._verifier_conflits(slot, slot.id_edt)
            if conflit is not None:
                return Result.fail(conflit, "GESTION")
            updated = self._planning.update_slot(slot)
            if updated == 0:
                return Result.fail("Créneau d’EDT introuvable.", "INTROUVABLE")
            self.journal.log_modification(
                code_utr, Tables.EMPLOI_DU_TEMPS, slot.id_edt, slot.jour)
            return Result.ok("Créneau d’emploi du temps enregistré.")
        except Exception as ex:
            return self.failure("Modification d’un créneau d’EDT", ex)

    def delete_slot(self, id_edt: int, code_utr: str) -> Result:
        denied = ensure_allowed(code_utr, Modules.EMPLOI_DU_TEMPS)
        if denied is not None:
            return denied
        try:
            slot = self._planning.get_slot(id_edt)
            if slot is None:
                return Result.fail("Créneau d’EDT introuvable.", "INTROUVABLE")
            self._planning.delete_slot(id_edt)
            self.journal.log_suppression(
                code_utr, Tables.EMPLOI_DU_TEMPS, id_edt, slot.jour)
            return Result.ok("Créneau d’emploi du temps supprimé.")
        except Exception as ex:
            if error_helper.is_foreign_key_violation(ex):
                return Result.fail(
                    "Suppression impossible : des séances sont rattachées à ce "
                    "créneau.", "LIAISON")
            return self.failure("Suppression d’un créneau d’EDT", ex)

    # ----- Séances -----

    def list_seances(self, debut=None, fin=None, id_classe: Optional[int] = None):
        """Séances réalisées (cahier de texte), filtrables par dates et classe."""
        try:
            return self._planning.list_seances(debut, fin, id_classe)
        except Exception as ex:
            self.logger.error("Liste des séances", ex)
            return []

    def get_seance(self, id_seance: int) -> Optional[Seance]:
        try:
            return self._planning.get_seance(id_seance)
        except Exception as ex:
            self.logger.error("Lecture d’une séance", ex)
            return None

    def list_seances_by_edt(self, id_edt: int):
        try:
            return self._planning.list_seances_by_edt(id_edt)
        except Exception as ex:
            self.logger.error("Liste des séances d’un créneau", ex)
            return []

    def save_seance(self, seance: Seance, code_utr: str) -> Result:
        denied = ensure_allowed(code_utr, Modules.EMPLOI_DU_TEMPS)
        if denied is not None:
            return denied
        validation = PlanningValidator.validate_seance(seance)
        if not validation.is_valid:
            return self.invalid(validation)
        try:
            if seance.id_seance is None:
                id_seance = self._planning.insert_seance(seance)
                seance.id_seance = id_seance
                self.journal.log_creation(
                    code_utr, Tables.SEANCE, id_seance, str(seance.date_seance))
            else:
                self._planning.update_seance(seance)
                self.journal.log_modification(
                    code_utr, Tables.SEANCE, seance.id_seance, str(seance.date_seance))
            return Result.ok("Séance enregistrée.")
        except Exception as ex:
            return self.failure("Enregistrement d’une séance", ex)

    def delete_seance(self, id_seance: int, code_utr: str) -> Result:
        denied = ensure_allowed(code_utr, Modules.EMPLOI_DU_TEMPS)
        if denied is not None:
            return denied
        try:
            seance = self._planning.get_seance(id_seance)
            if seance is None:
                return Result.fail("Séance introuvable.", "INTROUVABLE")
            self._planning.delete_seance(id_seance)
            self.journal.log_suppression(
                code_utr, Tables.SEANCE, id_seance, str(seance.date_seance))
            return Result.ok("Séance supprimée.")
        except Exception as ex:
            if error_helper.is_foreign_key_violation(ex):
                return Result.fail(
                    "Suppression impossible : des absences sont rattachées à cette "
                    "séance.", "LIAISON")
            return self.failure("Suppression d’une séance", ex)

    # ----- Absences -----

    def list_absences_by_seance(self, id_seance: int):
        try:
            return self._planning.list_absences_by_seance(id_seance)
        except Exception as ex:
            self.logger.error("Liste des absences d’une séance", ex)
            return []

    def list_absences_by_inscription(self, id_inscription: int):
        try:
            return self._planning.list_absences_by_inscription(id_inscription)
        except Exception as ex:
            self.logger.error("Liste des absences d’un étudiant", ex)
            return []

    def total_heures_absence(self, id_inscription: int) -> float:
        try:
            return self._planning.sum_heures_absence(id_inscription)
        except Exception as ex:
            self.logger.error("Total d’heures d’absence", ex)
            return 0.0

    def save_absence(self, absence: Absence, code_utr: str) -> Result:
        denied = ensure_allowed(code_utr, Modules.ABSENCES)
        if denied is not None:
            return denied
        validation = PlanningValidator.validate_absence(absence)
        if not validation.is_valid:
            return self.invalid(validation)
        try:
            if absence.id_absence is None:
                id_absence = self._planning.insert_absence(absence)
                absence.id_absence = id_absence
                self.journal.log_creation(
                    code_utr, Tables.ABSENCE, id_absence, f"Séance {absence.id_seance}")
            else:
                self._planning.update_absence(absence)
                self.journal.log_modification(
                    code_utr, Tables.ABSENCE, absence.id_absence, f"Séance {absence.id_seance}")
            return Result.ok("Absence enregistrée.")
        except Exception as ex:
            return self.failure("Enregistrement d’une absence", ex)

    def delete_absence(self, id_absence: int, code_utr: str) -> Result:
        denied = ensure_allowed(code_utr, Modules.ABSENCES)
        if denied is not None:
            return denied
        try:
            self._planning.delete_absence(id_absence)
            self.journal.log_suppression(code_utr, Tables.ABSENCE, id_absence)
            return Result.ok("Absence supprimée.")
        except Exception as ex:
            return self.failure("Suppression d’une absence", ex)
