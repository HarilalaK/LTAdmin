"""Authentification sur la table UTILISATEUR.

CODE_UTR unique, comparaison insensible à la casse comme le fait Access,
compte ACTIF requis. Note historique : les mots de passe sont stockés en
clair dans la base fournie ; le service centralise la vérification pour
permettre un durcissement ultérieur (hachage) sans toucher les écrans.
"""

from __future__ import annotations

from ltadmin.core.result import Result, ResultValue
from ltadmin.data import error_helper
from ltadmin.data.schema import Tables
from ltadmin.models.db_models import UserSession
from ltadmin.repositories.admin_repository import AdminRepository
from ltadmin.data.access_database import AccessDatabase
from ltadmin.services.auth import password_hashing
from ltadmin.services.auth.habilitations import normalize_profil
from ltadmin.services.logging.app_logger import AppLogger
from ltadmin.services.logging.journal_service import JournalService


class AuthenticationService:

    def __init__(self, database: AccessDatabase, journal: JournalService, logger: AppLogger):
        self._admin = AdminRepository(database)
        self._journal = journal
        self._logger = logger

    def authenticate(self, login: str, password: str) -> ResultValue[UserSession]:
        """Vérifie un couple identifiant / mot de passe (requête paramétrée)."""
        code = (login or "").strip()
        if not code or not (password or ""):
            return ResultValue.fail(
                "Saisissez votre identifiant et votre mot de passe.", "AUTHENTIFICATION")
        try:
            user = self._admin.get_utilisateur(code)
            if user is None or not (user.code_utr or "").strip():
                self._journal.log_connexion(code, False)
                return ResultValue.fail(
                    "Identifiant ou mot de passe incorrect.", "AUTHENTIFICATION")
            if user.actif is False:
                self._journal.log_connexion(user.code_utr, False)
                return ResultValue.fail(
                    "Ce compte est désactivé. Contactez l’administrateur.", "AUTHENTIFICATION")
            if not password_hashing.verify(password or "", user.mot_passe or ""):
                self._journal.log_connexion(user.code_utr, False)
                return ResultValue.fail(
                    "Identifiant ou mot de passe incorrect.", "AUTHENTIFICATION")
            # Migration transparente : les mots de passe historiques en clair
            # (base fournie) sont hachés dès la première connexion réussie.
            if password_hashing.needs_upgrade(user.mot_passe or ""):
                try:
                    self._admin.update_mot_passe(
                        user.code_utr, password_hashing.hash_password(password or ""))
                except Exception as upgrade_error:
                    # Le hachage ne doit pas empêcher la connexion.
                    self._logger.error("Migration du mot de passe", upgrade_error)
            display_name = user.nom_utr if (user.nom_utr or "").strip() else user.code_utr
            role = normalize_profil(user.profil)
            self._journal.log_connexion(user.code_utr, True)
            return ResultValue.ok(
                UserSession(user.code_utr, display_name, role), "Connexion réussie.")
        except Exception as ex:
            error = error_helper.interpret(ex)
            self._logger.error("Authentification", ex)
            return ResultValue.fail(
                "Connexion impossible : " + error.message, "TECHNIQUE")

    def change_password(self, code_utr: str, ancien_mot_passe: str,
                        nouveau_mot_passe: str) -> Result:
        """Change le mot de passe d'un compte après vérification de l'ancien."""
        if not nouveau_mot_passe or len(nouveau_mot_passe) < 4:
            return Result.fail(
                "Le nouveau mot de passe doit contenir au moins 4 caractères.", "VALIDATION")
        if len(nouveau_mot_passe) > 120:
            return Result.fail(
                "Le nouveau mot de passe doit contenir 120 caractères maximum.", "VALIDATION")
        try:
            user = self._admin.get_utilisateur((code_utr or "").strip())
            if user is None:
                return Result.fail("Compte introuvable.", "INTROUVABLE")
            if (user.mot_passe or "") != (ancien_mot_passe or "") \
                    and not password_hashing.verify(ancien_mot_passe or "", user.mot_passe or ""):
                return Result.fail(
                    "L’ancien mot de passe est incorrect.", "AUTHENTIFICATION")
            self._admin.update_mot_passe(
                user.code_utr, password_hashing.hash_password(nouveau_mot_passe))
            self._journal.log_operation(
                code_utr, "MOT_DE_PASSE", Tables.UTILISATEUR, None,
                "Changement de mot de passe.")
            return Result.ok("Mot de passe modifié.")
        except Exception as ex:
            error = error_helper.interpret(ex)
            self._logger.error("Changement de mot de passe", ex)
            return Result.fail(error.message, error.code)
