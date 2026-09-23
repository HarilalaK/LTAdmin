"""Gestion des comptes utilisateurs, de l'établissement et des années scolaires.

Réservé au profil Administrateur (contrôlé par les habilitations côté UI).
Une seule année scolaire ACTIVE à la fois (mise à jour transactionnelle).
"""

from __future__ import annotations

from typing import List, Optional

from ltadmin.core.result import Result, ResultValue
from ltadmin.data import error_helper
from ltadmin.data.access_database import AccessDatabase
from ltadmin.data.schema import Profils, Tables
from ltadmin.models.entities import AnneeScolaire, Etablissement, Utilisateur
from ltadmin.repositories.admin_repository import AdminRepository
from ltadmin.services.auth.habilitations import PROFILS_CONNUS, normalize_profil
from ltadmin.services.common import ServiceBase
from ltadmin.services.logging.app_logger import AppLogger
from ltadmin.services.logging.journal_service import JournalService
from ltadmin.services.referentiel.parametre_service import ParametreService


class AdminService(ServiceBase):

    def __init__(self, database: AccessDatabase, logger: AppLogger,
                 journal: JournalService, parametres: ParametreService):
        super().__init__(database, logger, journal, parametres)
        self._admin = AdminRepository(database)

    # ----- Utilisateurs -----

    def list_utilisateurs(self) -> List[Utilisateur]:
        try:
            return self._admin.list_utilisateurs()
        except Exception as ex:
            self.logger.error("Liste des utilisateurs", ex)
            return []

    def get_utilisateur(self, code_utr: str) -> Optional[Utilisateur]:
        try:
            return self._admin.get_utilisateur(code_utr)
        except Exception as ex:
            self.logger.error("Lecture d’un utilisateur", ex)
            return None

    def save_utilisateur(self, utilisateur: Utilisateur, mot_de_passe: Optional[str],
                         code_utr: str) -> Result:
        """Crée ou modifie un compte. Le mot de passe n'est écrasé que s'il est fourni."""
        code = (utilisateur.code_utr or "").strip()
        if not code:
            return Result.fail("Identifiant obligatoire.", "VALIDATION")
        if len(code) > 20:
            return Result.fail("Identifiant : 20 caractères maximum.", "VALIDATION")
        if not (utilisateur.nom_utr or "").strip():
            return Result.fail("Nom de l’utilisateur obligatoire.", "VALIDATION")
        if len(utilisateur.nom_utr or "") > 120:
            return Result.fail("Nom : 120 caractères maximum.", "VALIDATION")
        profil = normalize_profil(utilisateur.profil)
        if profil not in PROFILS_CONNUS:
            return Result.fail(
                "Profil inconnu. Profils attendus : " + ", ".join(PROFILS_CONNUS) + ".",
                "VALIDATION")
        if mot_de_passe is not None and not (4 <= len(mot_de_passe) <= 120):
            return Result.fail(
                "Mot de passe : entre 4 et 120 caractères.", "VALIDATION")
        utilisateur.code_utr = code
        utilisateur.profil = profil
        if utilisateur.actif is None:
            utilisateur.actif = True
        try:
            existing = self._admin.get_utilisateur(code)
            if existing is None:
                utilisateur.mot_passe = mot_de_passe or ""
                if not utilisateur.mot_passe:
                    return Result.fail(
                        "Mot de passe initial obligatoire (4 caractères minimum).",
                        "VALIDATION")
                self._admin.insert_utilisateur(utilisateur)
                self.journal.log_creation(code_utr, Tables.UTILISATEUR, None, code)
                return Result.ok(f"Compte « {code} » créé.")
            utilisateur.mot_passe = mot_de_passe if mot_de_passe else existing.mot_passe
            self._admin.update_utilisateur(utilisateur)
            self.journal.log_modification(code_utr, Tables.UTILISATEUR, None, code)
            return Result.ok(f"Compte « {code} » enregistré.")
        except Exception as ex:
            if error_helper.is_unique_violation(ex):
                return Result.fail("Cet identifiant est déjà utilisé.", "DOUBLON")
            if error_helper.is_foreign_key_violation(ex):
                return Result.fail(
                    "Impossible de supprimer ce compte : des données y font référence.",
                    "LIAISON")
            return self.failure("Enregistrement d’un utilisateur", ex)

    def set_actif(self, code_utr_cible: str, actif: bool, code_utr: str) -> Result:
        """Active ou désactive un compte (impossible de se désactiver soi-même)."""
        if code_utr_cible == code_utr and not actif:
            return Result.fail(
                "Vous ne pouvez pas désactiver votre propre compte.", "GESTION")
        try:
            existing = self._admin.get_utilisateur(code_utr_cible)
            if existing is None:
                return Result.fail("Compte introuvable.", "INTROUVABLE")
            self._admin.set_utilisateur_actif(code_utr_cible, actif)
            self.journal.log_operation(
                code_utr, "ACTIVATION" if actif else "DESACTIVATION",
                Tables.UTILISATEUR, None, code_utr_cible)
            return Result.ok("Compte activé." if actif else "Compte désactivé.")
        except Exception as ex:
            return self.failure("Activation d’un compte", ex)

    def delete_utilisateur(self, code_utr_cible: str, code_utr: str) -> Result:
        if code_utr_cible == code_utr:
            return Result.fail(
                "Vous ne pouvez pas supprimer votre propre compte.", "GESTION")
        if code_utr_cible.upper() == "ADMIN":
            return Result.fail(
                "Le compte administrateur principal ne peut pas être supprimé.", "GESTION")
        try:
            existing = self._admin.get_utilisateur(code_utr_cible)
            if existing is None:
                return Result.fail("Compte introuvable.", "INTROUVABLE")
            self._admin.delete_utilisateur(code_utr_cible)
            self.journal.log_suppression(
                code_utr, Tables.UTILISATEUR, None, code_utr_cible)
            return Result.ok(f"Compte « {code_utr_cible} » supprimé.")
        except Exception as ex:
            if error_helper.is_foreign_key_violation(ex):
                return Result.fail(
                    "Suppression impossible : des données (notes, paiements…) font "
                    "référence à ce compte.", "LIAISON")
            return self.failure("Suppression d’un utilisateur", ex)

    # ----- Établissement -----

    def get_etablissement(self) -> Etablissement:
        try:
            return self._admin.get_etablissement() or Etablissement()
        except Exception as ex:
            self.logger.error("Lecture de l’établissement", ex)
            return Etablissement()

    def save_etablissement(self, etablissement: Etablissement, code_utr: str) -> Result:
        if not (etablissement.code_etab or "").strip():
            return Result.fail("Code établissement obligatoire.", "VALIDATION")
        if not (etablissement.nom_etab or "").strip():
            return Result.fail("Nom de l’établissement obligatoire.", "VALIDATION")
        try:
            self._admin.update_etablissement(etablissement)
            self.journal.log_modification(
                code_utr, Tables.ETABLISSEMENT, None, etablissement.nom_etab)
            return Result.ok("Identité de l’établissement enregistrée.")
        except Exception as ex:
            return self.failure("Enregistrement de l’établissement", ex)

    # ----- Années scolaires -----

    def list_annees(self) -> List[AnneeScolaire]:
        try:
            return self._admin.list_annees()
        except Exception as ex:
            self.logger.error("Liste des années scolaires", ex)
            return []

    def get_annee_active(self) -> Optional[AnneeScolaire]:
        try:
            return self._admin.get_annee_active()
        except Exception as ex:
            self.logger.error("Lecture de l’année active", ex)
            return None

    def save_annee(self, annee: AnneeScolaire, code_utr: str) -> ResultValue[int]:
        if not (annee.libelle or "").strip():
            return ResultValue.fail("Libellé d’année obligatoire.", "VALIDATION")
        if annee.date_debut is not None and annee.date_fin is not None \
                and annee.date_fin < annee.date_debut:
            return ResultValue.fail(
                "La date de fin doit être postérieure ou égale à la date de début.",
                "VALIDATION")
        try:
            if annee.id_annee is None:
                if annee.active is None:
                    annee.active = False
                id_annee = self._admin.insert_annee(annee)
                if annee.active:
                    self._admin.set_annee_active(id_annee)
                self.journal.log_creation(
                    code_utr, Tables.ANNEE_SCOLAIRE, id_annee, annee.libelle)
                return ResultValue.ok(id_annee, f"Année « {annee.libelle} » créée.")
            self._admin.update_annee(annee)
            if annee.active:
                self._admin.set_annee_active(annee.id_annee)
            self.journal.log_modification(
                code_utr, Tables.ANNEE_SCOLAIRE, annee.id_annee, annee.libelle)
            return ResultValue.ok(annee.id_annee or 0, "Année scolaire enregistrée.")
        except Exception as ex:
            if error_helper.is_unique_violation(ex):
                return ResultValue.fail("Ce libellé d’année existe déjà.", "DOUBLON")
            return self.failure_value("Enregistrement d’une année scolaire", ex)

    def activer_annee(self, id_annee: int, code_utr: str) -> Result:
        """Active une année scolaire (les autres sont désactivées, en transaction)."""
        try:
            annee = self._admin.get_annee(id_annee)
            if annee is None:
                return Result.fail("Année scolaire introuvable.", "INTROUVABLE")
            self._admin.set_annee_active(id_annee)
            self.journal.log_operation(
                code_utr, "ACTIVATION_ANNEE", Tables.ANNEE_SCOLAIRE, id_annee,
                annee.libelle)
            return Result.ok(f"Année « {annee.libelle} » activée.")
        except Exception as ex:
            return self.failure("Activation d’une année scolaire", ex)
