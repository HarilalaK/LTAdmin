"""Écolage : tarifs, échéanciers, encaissements et remises.

Règles :
- échéancier idempotent (une seule génération par tarif × inscription), en
  transaction ; tranches mensuelles dès la date d'inscription ;
- part = montant / n arrondi au centime, la dernière tranche absorbe les arrondis ;
- statut d'échéance : DU (rien payé), PARTIEL, SOLDE (≥ net dû − 0,005) ;
- reçu unique REC-AAAA-######, encaissement ≤ reste + 0,01.
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from ltadmin.core.result import Result, ResultValue
from ltadmin.data import error_helper
from ltadmin.data.access_database import AccessDatabase
from ltadmin.data.schema import Tables
from ltadmin.models.dto import EcheanceDetail, PaiementCree
from ltadmin.models.entities import Echeancier, Paiement, Tarif
from ltadmin.repositories.enrollment_repository import EnrollmentRepository
from ltadmin.repositories.finance_repository import FinanceRepository
from ltadmin.services.common import ServiceBase
from ltadmin.services.logging.app_logger import AppLogger
from ltadmin.services.logging.journal_service import JournalService
from ltadmin.services.referentiel.parametre_service import ParametreService
from ltadmin.services.validation.validation import PaymentValidator

CENTIME = Decimal("0.01")
TOLERANCE = Decimal("0.005")

MODES_PAIEMENT = ("Espèces", "Chèque", "Virement", "Mobile Money", "Autre")


class EcoService(ServiceBase):

    def __init__(self, database: AccessDatabase, logger: AppLogger,
                 journal: JournalService, parametres: ParametreService):
        super().__init__(database, logger, journal, parametres)
        self._finance = FinanceRepository(database)
        self._inscriptions = EnrollmentRepository(database)

    # ----- Tarifs -----

    def list_tarifs(self, id_classe: int) -> List[Tarif]:
        try:
            return self._finance.list_tarifs_by_classe(id_classe)
        except Exception as ex:
            self.logger.error("Liste des tarifs d’une classe", ex)
            return []

    def save_tarif(self, tarif: Tarif, code_utr: str) -> ResultValue[int]:
        validation = PaymentValidator.validate_tarif(tarif)
        if not validation.is_valid:
            return self.invalid_value(validation)
        try:
            if tarif.obligatoire is None:
                tarif.obligatoire = True
            if tarif.nb_tranches is None:
                tarif.nb_tranches = 1
            if tarif.id_tarif is None:
                tarif.id_tarif = self._finance.insert_tarif(tarif)
                self.journal.log_creation(
                    code_utr, Tables.TARIF, tarif.id_tarif, tarif.type_frais)
                return ResultValue.ok(tarif.id_tarif, "Tarif enregistré.")
            updated = self._finance.update_tarif(tarif)
            if updated == 0:
                return ResultValue.fail("Tarif introuvable.", "INTROUVABLE")
            self.journal.log_modification(
                code_utr, Tables.TARIF, tarif.id_tarif, tarif.type_frais)
            return ResultValue.ok(tarif.id_tarif, "Tarif enregistré.")
        except Exception as ex:
            return self.failure_value("Enregistrement d’un tarif", ex)

    def delete_tarif(self, id_tarif: int, code_utr: str) -> Result:
        try:
            tarif = self._finance.get_tarif(id_tarif)
            if tarif is None:
                return Result.fail("Tarif introuvable.", "INTROUVABLE")
            self._finance.delete_tarif(id_tarif)
            self.journal.log_suppression(
                code_utr, Tables.TARIF, id_tarif, tarif.type_frais)
            return Result.ok("Tarif supprimé.")
        except Exception as ex:
            if error_helper.is_foreign_key_violation(ex):
                return Result.fail(
                    "Suppression impossible : des échéances sont rattachées à ce "
                    "tarif.", "LIAISON")
            return self.failure("Suppression d’un tarif", ex)

    # ----- Échéanciers -----

    def list_echeances(self, id_inscription: int) -> List[EcheanceDetail]:
        try:
            return self._finance.list_echeances_by_inscription(id_inscription)
        except Exception as ex:
            self.logger.error("Liste des échéances d’une inscription", ex)
            return []

    def get_echeance(self, id_echeance: int) -> Optional[Echeancier]:
        try:
            return self._finance.get_echeance(id_echeance)
        except Exception as ex:
            self.logger.error("Lecture d’une échéance", ex)
            return None

    def get_echeance_detail(self, id_echeance: int) -> Optional[EcheanceDetail]:
        """Échéance + total payé et dernier paiement (forme de R_PAIEMENT_ECHEANCE)."""
        try:
            echeance = self._finance.get_echeance(id_echeance)
            if echeance is None:
                return None
            paiements = self._finance.list_paiements_by_echeance(id_echeance)
            total = sum((p.montant or Decimal("0") for p in paiements), Decimal("0"))
            dernier = max((p.date_paiement for p in paiements
                           if p.date_paiement is not None), default=None)
            return EcheanceDetail(
                id_echeance=echeance.id_echeance,
                id_inscription=echeance.id_inscription,
                id_tarif=echeance.id_tarif,
                num_tranche=echeance.num_tranche,
                libelle=echeance.libelle,
                montant_du=echeance.montant_du,
                date_echeance=echeance.date_echeance,
                statut=echeance.statut,
                remise=echeance.remise,
                total_paye=total,
                dernier_paiement=dernier,
            )
        except Exception as ex:
            self.logger.error("Lecture d’une échéance", ex)
            return None

    def generer_echeancier(self, id_inscription: int, id_tarif: int,
                           code_utr: str) -> ResultValue[int]:
        """Génère l'échéancier d'un tarif pour une inscription (idempotent)."""
        try:
            tarif = self._finance.get_tarif(id_tarif)
            if tarif is None:
                return ResultValue.fail("Tarif introuvable.", "INTROUVABLE")
            inscription = self._inscriptions.get_by_id(id_inscription)
            if inscription is None:
                return ResultValue.fail("Inscription introuvable.", "INTROUVABLE")

            existantes = self._finance.count_by_inscription_tarif(id_inscription, id_tarif)
            if existantes > 0:
                return ResultValue.fail(
                    "L’échéancier de ce tarif existe déjà pour cette inscription "
                    "(supprimez-le pour le régénérer).", "DOUBLON")

            montant = tarif.montant or Decimal("0")
            if montant <= 0:
                return ResultValue.fail(
                    "Le montant du tarif doit être strictement positif.", "GESTION")
            nb_tranches = tarif.nb_tranches or 1
            if not 1 <= nb_tranches <= 24:
                return ResultValue.fail(
                    "Nombre de tranches : valeur entre 1 et 24 attendue.", "GESTION")

            type_frais = (tarif.type_frais or "Frais").strip()
            date_base = inscription.date_inscription or _dt.datetime.combine(
                _dt.date.today(), _dt.time())
            part = (montant / Decimal(nb_tranches)).quantize(CENTIME, ROUND_HALF_UP)
            total_reparti = Decimal("0")
            crees = 0
            with self.db.begin_transaction():
                for numero in range(1, nb_tranches + 1):
                    if numero == nb_tranches:
                        # La dernière tranche absorbe les arrondis de répartition.
                        montant_tranche = montant - total_reparti
                    else:
                        montant_tranche = part
                    total_reparti += montant_tranche
                    mois = (date_base.month - 1 + (numero - 1)) % 12 + 1
                    annee = date_base.year + (date_base.month - 1 + (numero - 1)) // 12
                    try:
                        echeance_date = _dt.datetime(annee, mois,
                                                     min(date_base.day, 28))
                    except ValueError:
                        echeance_date = _dt.datetime(annee, mois, 28)
                    if nb_tranches == 1:
                        libelle = type_frais
                    else:
                        libelle = f"{type_frais} — tranche {numero}/{nb_tranches}"
                    self._finance.insert_echeance(Echeancier(
                        id_inscription=id_inscription,
                        id_tarif=id_tarif,
                        num_tranche=numero,
                        libelle=libelle,
                        montant_du=montant_tranche,
                        date_echeance=echeance_date,
                        statut="DU",
                        remise=Decimal("0"),
                    ))
                    crees += 1

            self.journal.log_operation(
                code_utr, "GENERATION_ECHEANCIER", Tables.ECHEANCIER, id_inscription,
                f"{type_frais} : {crees} tranche(s), total {montant}.")
            return ResultValue.ok(
                crees, f"Échéancier généré : {crees} tranche(s) pour {type_frais}.")
        except Exception as ex:
            return self.failure_value("Génération d’un échéancier", ex)

    def supprimer_echeancier(self, id_inscription: int, id_tarif: int,
                             code_utr: str) -> Result:
        """Supprime toutes les tranches du tarif pour cette inscription (si rien payé)."""
        try:
            for echeance in self._finance.list_echeances_by_inscription(id_inscription):
                if echeance.id_tarif != id_tarif:
                    continue
                if echeance.total_paye and echeance.total_paye > 0:
                    return Result.fail(
                        "Suppression impossible : des paiements sont déjà "
                        "enregistrés sur cet échéancier.", "GESTION")
            supprimees = 0
            with self.db.begin_transaction():
                for echeance in self._finance.list_echeances_by_inscription(id_inscription):
                    if echeance.id_tarif == id_tarif and echeance.id_echeance is not None:
                        self._finance.delete_echeance(echeance.id_echeance)
                        supprimees += 1
            if supprimees == 0:
                return Result.fail("Aucune échéance à supprimer pour ce tarif.", "INTROUVABLE")
            self.journal.log_operation(
                code_utr, "SUPPRESSION_ECHEANCIER", Tables.ECHEANCIER, id_inscription,
                f"{supprimees} tranche(s) supprimée(s).")
            return Result.ok(f"{supprimees} tranche(s) supprimée(s).")
        except Exception as ex:
            return self.failure("Suppression d’un échéancier", ex)

    # ----- Encaissements -----

    def encaisser(self, id_echeance: int, montant: Decimal, mode_paie: Optional[str],
                  ref_externe: Optional[str] = None, observation: Optional[str] = None,
                  code_utr: str = "") -> ResultValue[PaiementCree]:
        """Enregistre un encaissement sur une échéance et met à jour son statut."""
        try:
            echeance = self._finance.get_echeance(id_echeance)
            if echeance is None:
                return ResultValue.fail("Échéance introuvable.", "INTROUVABLE")
            total_paye = self._finance.total_paye_by_echeance(id_echeance) or Decimal("0")
            remise = echeance.remise or Decimal("0")
            net_du = (echeance.montant_du or Decimal("0")) - remise
            reste = net_du - total_paye
            if reste <= TOLERANCE:
                return ResultValue.fail("Cette échéance est déjà soldée.", "GESTION")

            validation = PaymentValidator.validate_encaissement(montant, mode_paie, reste)
            if not validation.is_valid:
                return self.invalid_value(validation)
            if ref_externe and len(ref_externe) > 60:
                return ResultValue.fail("Référence externe : 60 caractères maximum.",
                                        "VALIDATION")
            if observation and len(observation) > 300:
                return ResultValue.fail("Observation : 300 caractères maximum.", "VALIDATION")

            paiement = Paiement(
                id_echeance=id_echeance,
                num_recu=self._generer_num_recu(),
                date_paiement=_dt.datetime.now(),
                montant=montant,
                mode_paie=(mode_paie or "").strip(),
                ref_externe=(ref_externe or "").strip() or None,
                code_utr=code_utr or None,
                observation=(observation or "").strip() or None,
            )
            id_paiement = self._finance.insert_paiement(paiement)
            nouveau_statut = self._actualiser_statut(id_echeance)
            self.journal.log_operation(
                code_utr, "ENCAISSEMENT", Tables.PAIEMENT, id_paiement,
                f"Reçu {paiement.num_recu} — {montant} ({mode_paie}).")
            return ResultValue.ok(
                PaiementCree(id_paiement, paiement.num_recu, nouveau_statut),
                f"Paiement enregistré (reçu {paiement.num_recu}).")
        except Exception as ex:
            return self.failure_value("Encaissement", ex)

    def list_paiements(self, id_echeance: int) -> List[Paiement]:
        try:
            return self._finance.list_paiements_by_echeance(id_echeance)
        except Exception as ex:
            self.logger.error("Liste des paiements d’une échéance", ex)
            return []

    def annuler_paiement(self, id_paiement: int, code_utr: str) -> Result:
        """Annule un encaissement (remboursement / erreur de saisie)."""
        try:
            paiement = self._finance.get_paiement(id_paiement)
            if paiement is None:
                return Result.fail("Paiement introuvable.", "INTROUVABLE")
            id_echeance = paiement.id_echeance
            recu = paiement.num_recu
            self._finance.delete_paiement(id_paiement)
            if id_echeance is not None:
                self._actualiser_statut(id_echeance)
            self.journal.log_suppression(
                code_utr, Tables.PAIEMENT, id_paiement, f"Reçu {recu} annulé.")
            return Result.ok(f"Paiement {recu} annulé.")
        except Exception as ex:
            return self.failure("Annulation d’un paiement", ex)

    def accorder_remise(self, id_echeance: int, remise: Optional[Decimal],
                        code_utr: str) -> Result:
        """Accorde (ou retire) une remise sur une échéance, puis recalcule le statut."""
        try:
            echeance = self._finance.get_echeance(id_echeance)
            if echeance is None:
                return Result.fail("Échéance introuvable.", "INTROUVABLE")
            montant_du = echeance.montant_du or Decimal("0")
            validation = PaymentValidator.validate_remise(remise, montant_du)
            if not validation.is_valid:
                return self.invalid(validation)
            total_paye = self._finance.total_paye_by_echeance(id_echeance) or Decimal("0")
            nouvelle_remise = remise or Decimal("0")
            if nouvelle_remise > 0 and total_paye > (montant_du - nouvelle_remise) + Decimal("0.01"):
                return Result.fail(
                    "Remise impossible : le montant déjà payé dépasse le net à payer "
                    "après remise.", "GESTION")
            self._finance.update_remise(id_echeance, nouvelle_remise if nouvelle_remise > 0 else None)
            statut = self._actualiser_statut(id_echeance)
            self.journal.log_operation(
                code_utr, "REMISE", Tables.ECHEANCIER, id_echeance,
                f"Remise {nouvelle_remise} — statut {statut}.")
            return Result.ok(f"Remise enregistrée (statut : {statut}).")
        except Exception as ex:
            return self.failure("Octroi d’une remise", ex)

    # ----- Helpers -----

    def _actualiser_statut(self, id_echeance: int) -> str:
        """Recalcule le statut d'une échéance : DU / PARTIEL / SOLDE."""
        echeance = self._finance.get_echeance(id_echeance)
        total_paye = self._finance.total_paye_by_echeance(id_echeance) or Decimal("0")
        net_du = ((echeance.montant_du or Decimal("0"))
                  - (echeance.remise or Decimal("0")))
        if total_paye <= TOLERANCE:
            statut = "DU"
        elif total_paye >= net_du - TOLERANCE:
            statut = "SOLDE"
        else:
            statut = "PARTIEL"
        self._finance.update_statut(id_echeance, statut)
        return statut

    def _generer_num_recu(self) -> str:
        """Génère un numéro de reçu unique REC-AAAA-###### avec re-tentative."""
        prefixe = f"REC-{_dt.date.today().year}-"
        existants = {r.upper() for r in self._finance.list_recus(prefixe)}
        sequence = 0
        for recu in existants:
            suffixe = recu[len(prefixe):]
            try:
                value = int(suffixe)
            except ValueError:
                continue
            if value > sequence:
                sequence = value
        while True:
            sequence += 1
            candidat = prefixe + f"{sequence:06d}"
            if candidat.upper() not in existants \
                    and not self._finance.recu_existe(candidat):
                return candidat
