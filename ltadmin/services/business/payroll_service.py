"""Paie des formateurs : calcul du montant à partir des heures réalisées
(séances de l'emploi du temps) × taux horaire. Une paie calculée est figée."""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal
from typing import List, Optional

from ltadmin.core.result import Result, ResultValue
from ltadmin.data import error_helper
from ltadmin.data.access_database import AccessDatabase
from ltadmin.data.schema import Tables
from ltadmin.models.entities import Formateur, PaieFormateur
from ltadmin.repositories.finance_repository import FinanceRepository
from ltadmin.repositories.planning_repository import PlanningRepository
from ltadmin.repositories.staff_repository import StaffRepository
from ltadmin.services.auth.guard import ensure_allowed, ensure_allowed_value
from ltadmin.services.auth.habilitations import Modules
from ltadmin.services.common import ServiceBase
from ltadmin.services.logging.app_logger import AppLogger
from ltadmin.services.logging.journal_service import JournalService
from ltadmin.services.referentiel.parametre_service import ParametreService
from ltadmin.services.validation.validation import PayrollValidator


class PayrollService(ServiceBase):

    def __init__(self, database: AccessDatabase, logger: AppLogger,
                 journal: JournalService, parametres: ParametreService):
        super().__init__(database, logger, journal, parametres)
        self._finance = FinanceRepository(database)
        self._personnel = StaffRepository(database)
        self._planning = PlanningRepository(database)

    def list_formateurs(self, recherche: Optional[str] = None,
                        actifs_seulement: bool = False) -> List[Formateur]:
        try:
            return self._personnel.search_formateurs(recherche, actifs_seulement)
        except Exception as ex:
            self.logger.error("Liste des formateurs", ex)
            return []

    def list_paies_by_formateur(self, id_formateur: int) -> List[PaieFormateur]:
        try:
            return self._finance.list_paies_by_formateur(id_formateur)
        except Exception as ex:
            self.logger.error("Liste des paies d’un formateur", ex)
            return []

    def list_paies_by_periode(self, periode: str) -> List[PaieFormateur]:
        try:
            return self._finance.list_paies_by_periode(periode)
        except Exception as ex:
            self.logger.error("Liste des paies d’une période", ex)
            return []

    def heures_realisees(self, id_formateur: int, debut, fin) -> float:
        """Heures réalisées par un formateur sur une période (séances via EDT)."""
        try:
            return self._planning.sum_heures_formateur(id_formateur, debut, fin)
        except Exception as ex:
            self.logger.error("Calcul des heures d’un formateur", ex)
            return 0.0

    def calculer_paie(self, id_formateur: int, periode: str, debut, fin,
                      code_utr: str) -> ResultValue[int]:
        """Calcule et fige la paie d'un formateur pour une période (≤ 12 mois)."""
        denied = ensure_allowed_value(code_utr, Modules.PAIE)
        if denied is not None:
            return denied
        validation = PayrollValidator.validate_calcul(id_formateur, debut, fin)
        if not validation.is_valid:
            return self.invalid_value(validation)
        periode = (periode or "").strip()
        if not periode:
            return ResultValue.fail("Période (libellé) obligatoire.", "VALIDATION")
        if len(periode) > 40:
            return ResultValue.fail("Période : 40 caractères maximum.", "VALIDATION")
        try:
            formateur = self._personnel.get_formateur(id_formateur)
            if formateur is None:
                return ResultValue.fail("Formateur introuvable.", "INTROUVABLE")
            existante = self._finance.get_paie_by_formateur_periode(id_formateur, periode)
            if existante is not None:
                return ResultValue.fail(
                    f"La paie « {periode} » existe déjà pour ce formateur "
                    "(supprimez-la pour recalculer).", "DOUBLON")

            nb_heures = self._planning.sum_heures_formateur(id_formateur, debut, fin)
            if nb_heures <= 0:
                return ResultValue.fail(
                    "Aucune heure réalisée sur cette période : paie non calculée.",
                    "GESTION")
            taux = formateur.taux_horaire or Decimal("0")
            if taux <= 0:
                return ResultValue.fail(
                    "Taux horaire du formateur non renseigné ou nul.", "GESTION")
            montant = (Decimal(str(nb_heures)) * taux).quantize(Decimal("0.01"))

            id_paie = self._finance.insert_paie(PaieFormateur(
                id_formateur=id_formateur,
                periode=periode,
                nb_heures=nb_heures,
                taux=taux,
                montant=montant,
                paye=False,
                date_paie=None,
                observation=None,
            ))
            self.journal.log_operation(
                code_utr, "CALCUL_PAIE", Tables.PAIE_FORMATEUR, id_paie,
                f"{formateur.nom_complet} — {periode} : {nb_heures:g} h × {taux} = {montant}.")
            return ResultValue.ok(
                id_paie, f"Paie calculée : {nb_heures:g} h × {taux} = {montant}.")
        except Exception as ex:
            return self.failure_value("Calcul d’une paie", ex)

    def marquer_payee(self, id_paie: int, paye: bool, date_paie, code_utr: str) -> Result:
        denied = ensure_allowed(code_utr, Modules.PAIE)
        if denied is not None:
            return denied
        try:
            paie = self._finance.get_paie(id_paie)
            if paie is None:
                return Result.fail("Paie introuvable.", "INTROUVABLE")
            self._finance.set_paie_payee(
                id_paie, paye, date_paie or _dt.datetime.now() if paye else None)
            self.journal.log_operation(
                code_utr, "PAIEMENT_PAIE" if paye else "ANNULATION_PAIEMENT_PAIE",
                Tables.PAIE_FORMATEUR, id_paie, paie.periode)
            return Result.ok("Paie marquée comme payée." if paye else "Paiement retiré.")
        except Exception as ex:
            return self.failure("Marquage d’une paie", ex)

    def update_observation(self, paie: PaieFormateur, observation: Optional[str],
                           code_utr: str) -> Result:
        if paie.id_paie is None:
            return Result.fail("Paie introuvable.", "INTROUVABLE")
        if observation and len(observation) > 300:
            return Result.fail("Observation : 300 caractères maximum.", "VALIDATION")
        denied = ensure_allowed(code_utr, Modules.PAIE)
        if denied is not None:
            return denied
        try:
            paie.observation = observation
            self._finance.update_paie(paie)
            self.journal.log_modification(
                code_utr, Tables.PAIE_FORMATEUR, paie.id_paie, "Observation modifiée.")
            return Result.ok("Observation enregistrée.")
        except Exception as ex:
            return self.failure("Modification d’une observation de paie", ex)

    def delete_paie(self, id_paie: int, code_utr: str) -> Result:
        denied = ensure_allowed(code_utr, Modules.PAIE)
        if denied is not None:
            return denied
        try:
            paie = self._finance.get_paie(id_paie)
            if paie is None:
                return Result.fail("Paie introuvable.", "INTROUVABLE")
            if paie.paye:
                return Result.fail(
                    "Paie déjà versée : annulez d’abord le paiement avant de la "
                    "supprimer.", "GESTION")
            self._finance.delete_paie(id_paie)
            self.journal.log_suppression(
                code_utr, Tables.PAIE_FORMATEUR, id_paie, paie.periode)
            return Result.ok("Paie supprimée.")
        except Exception as ex:
            if error_helper.is_foreign_key_violation(ex):
                return Result.fail("Suppression impossible : données liées.", "LIAISON")
            return self.failure("Suppression d’une paie", ex)
