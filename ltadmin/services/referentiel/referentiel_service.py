"""Gestion du référentiel : filières, niveaux, salles, classes, modules, matières."""

from __future__ import annotations

from typing import List, Optional

from ltadmin.core.result import Result, ResultValue
from ltadmin.data import error_helper
from ltadmin.data.access_database import AccessDatabase
from ltadmin.data.schema import Tables
from ltadmin.models.dto import ClasseDetail
from ltadmin.models.entities import (
    Classe,
    Filiere,
    Matiere,
    ModuleFormation,
    Niveau,
    Salle,
)
from ltadmin.repositories.referentiel_repository import ReferentielRepository
from ltadmin.services.common import ServiceBase
from ltadmin.services.logging.app_logger import AppLogger
from ltadmin.services.logging.journal_service import JournalService
from ltadmin.services.referentiel.parametre_service import ParametreService
from ltadmin.services.validation.validation import ReferentielValidator


class ReferentielService(ServiceBase):

    def __init__(self, database: AccessDatabase, logger: AppLogger,
                 journal: JournalService, parametres: ParametreService):
        super().__init__(database, logger, journal, parametres)
        self._referentiel = ReferentielRepository(database)

    # ----- Filières -----

    def list_filieres(self, actives_seulement: bool = False) -> List[Filiere]:
        try:
            return self._referentiel.list_filieres(actives_seulement)
        except Exception as ex:
            self.logger.error("Liste des filières", ex)
            return []

    def save_filiere(self, filiere: Filiere, code_utr: str) -> Result:
        code = (filiere.code_filiere or "").strip()
        if not code:
            return Result.fail("Code filière obligatoire.", "VALIDATION")
        if len(code) > 20:
            return Result.fail("Code filière : 20 caractères maximum.", "VALIDATION")
        if not (filiere.libelle or "").strip():
            return Result.fail("Libellé de la filière obligatoire.", "VALIDATION")
        if filiere.duree_ans is not None and filiere.duree_ans <= 0:
            return Result.fail("Durée : nombre d’années strictement positif.", "VALIDATION")
        filiere.code_filiere = code
        if filiere.active is None:
            filiere.active = True
        try:
            if self._referentiel.get_filiere(code) is None:
                self._referentiel.insert_filiere(filiere)
                self.journal.log_creation(code_utr, Tables.FILIERE, None, code)
                return Result.ok(f"Filière « {code} » créée.")
            self._referentiel.update_filiere(filiere)
            self.journal.log_modification(code_utr, Tables.FILIERE, None, code)
            return Result.ok(f"Filière « {code} » enregistrée.")
        except Exception as ex:
            if error_helper.is_unique_violation(ex):
                return Result.fail("Ce code filière existe déjà.", "DOUBLON")
            return self.failure("Enregistrement d’une filière", ex)

    def delete_filiere(self, code: str, code_utr: str) -> Result:
        try:
            if self._referentiel.get_filiere(code) is None:
                return Result.fail("Filière introuvable.", "INTROUVABLE")
            self._referentiel.delete_filiere(code)
            self.journal.log_suppression(code_utr, Tables.FILIERE, None, code)
            return Result.ok("Filière supprimée.")
        except Exception as ex:
            if error_helper.is_foreign_key_violation(ex):
                return Result.fail(
                    "Suppression impossible : des classes ou modules utilisent cette "
                    "filière.", "LIAISON")
            return self.failure("Suppression d’une filière", ex)

    # ----- Niveaux -----

    def list_niveaux(self) -> List[Niveau]:
        try:
            return self._referentiel.list_niveaux()
        except Exception as ex:
            self.logger.error("Liste des niveaux", ex)
            return []

    def save_niveau(self, niveau: Niveau, code_utr: str) -> Result:
        code = (niveau.code_niveau or "").strip()
        if not code:
            return Result.fail("Code niveau obligatoire.", "VALIDATION")
        if len(code) > 20:
            return Result.fail("Code niveau : 20 caractères maximum.", "VALIDATION")
        if not (niveau.libelle or "").strip():
            return Result.fail("Libellé du niveau obligatoire.", "VALIDATION")
        niveau.code_niveau = code
        try:
            if self._referentiel.get_niveau(code) is None:
                self._referentiel.insert_niveau(niveau)
                self.journal.log_creation(code_utr, Tables.NIVEAU, None, code)
                return Result.ok(f"Niveau « {code} » créé.")
            self._referentiel.update_niveau(niveau)
            self.journal.log_modification(code_utr, Tables.NIVEAU, None, code)
            return Result.ok(f"Niveau « {code} » enregistré.")
        except Exception as ex:
            if error_helper.is_unique_violation(ex):
                return Result.fail("Ce code niveau existe déjà.", "DOUBLON")
            return self.failure("Enregistrement d’un niveau", ex)

    def delete_niveau(self, code: str, code_utr: str) -> Result:
        try:
            if self._referentiel.get_niveau(code) is None:
                return Result.fail("Niveau introuvable.", "INTROUVABLE")
            self._referentiel.delete_niveau(code)
            self.journal.log_suppression(code_utr, Tables.NIVEAU, None, code)
            return Result.ok("Niveau supprimé.")
        except Exception as ex:
            if error_helper.is_foreign_key_violation(ex):
                return Result.fail(
                    "Suppression impossible : des classes utilisent ce niveau.", "LIAISON")
            return self.failure("Suppression d’un niveau", ex)

    # ----- Salles -----

    def list_salles(self, disponibles_seulement: bool = False) -> List[Salle]:
        try:
            return self._referentiel.list_salles(disponibles_seulement)
        except Exception as ex:
            self.logger.error("Liste des salles", ex)
            return []

    def get_salle(self, id_salle: int) -> Optional[Salle]:
        try:
            return self._referentiel.get_salle(id_salle)
        except Exception as ex:
            self.logger.error("Lecture d’une salle", ex)
            return None

    def save_salle(self, salle: Salle, code_utr: str) -> Result:
        if not (salle.nom_salle or "").strip():
            return Result.fail("Nom de la salle obligatoire.", "VALIDATION")
        if salle.capacite is not None and salle.capacite <= 0:
            return Result.fail("Capacité : valeur strictement positive.", "VALIDATION")
        if salle.disponible is None:
            salle.disponible = True
        try:
            if salle.id_salle is None:
                id_salle = self._referentiel.insert_salle(salle)
                salle.id_salle = id_salle
                self.journal.log_creation(
                    code_utr, Tables.SALLE, id_salle, salle.nom_salle)
            else:
                self._referentiel.update_salle(salle)
                self.journal.log_modification(
                    code_utr, Tables.SALLE, salle.id_salle, salle.nom_salle)
            return Result.ok("Salle enregistrée.")
        except Exception as ex:
            return self.failure("Enregistrement d’une salle", ex)

    def delete_salle(self, id_salle: int, code_utr: str) -> Result:
        try:
            salle = self._referentiel.get_salle(id_salle)
            if salle is None:
                return Result.fail("Salle introuvable.", "INTROUVABLE")
            self._referentiel.delete_salle(id_salle)
            self.journal.log_suppression(
                code_utr, Tables.SALLE, id_salle, salle.nom_salle)
            return Result.ok("Salle supprimée.")
        except Exception as ex:
            if error_helper.is_foreign_key_violation(ex):
                return Result.fail(
                    "Suppression impossible : des classes ou créneaux d’EDT utilisent "
                    "cette salle.", "LIAISON")
            return self.failure("Suppression d’une salle", ex)

    # ----- Classes -----

    def list_classes(self, id_annee: Optional[int] = None) -> List[Classe]:
        try:
            return self._referentiel.list_classes(id_annee)
        except Exception as ex:
            self.logger.error("Liste des classes", ex)
            return []

    def list_classes_detail(self, id_annee: Optional[int] = None) -> List[ClasseDetail]:
        try:
            return self._referentiel.list_classes_detail(id_annee)
        except Exception as ex:
            self.logger.error("Liste détaillée des classes", ex)
            return []

    def get_classe(self, id_classe: int) -> Optional[Classe]:
        try:
            return self._referentiel.get_classe(id_classe)
        except Exception as ex:
            self.logger.error("Lecture d’une classe", ex)
            return None

    def save_classe(self, classe: Classe, code_utr: str) -> Result:
        if classe.id_annee is None:
            # Rattachement automatique à l'année scolaire active.
            from ltadmin.repositories.admin_repository import AdminRepository
            annee = AdminRepository(self.db).get_annee_active()
            if annee is None:
                return Result.fail(
                    "Aucune année scolaire active : activez-en une dans "
                    "l’administration.", "GESTION")
            classe.id_annee = annee.id_annee
        validation = ReferentielValidator.validate_classe(classe)
        if not validation.is_valid:
            return self.invalid(validation)
        if classe.code_filiere and self._referentiel.get_filiere(classe.code_filiere) is None:
            return Result.fail("Filière inconnue.", "INTROUVABLE")
        if classe.code_niveau and self._referentiel.get_niveau(classe.code_niveau) is None:
            return Result.fail("Niveau inconnu.", "INTROUVABLE")
        if classe.id_salle is not None and self._referentiel.get_salle(classe.id_salle) is None:
            return Result.fail("Salle inconnue.", "INTROUVABLE")
        try:
            if classe.id_classe is None:
                id_classe = self._referentiel.insert_classe(classe)
                classe.id_classe = id_classe
                self.journal.log_creation(
                    code_utr, Tables.CLASSE, id_classe, classe.libelle)
            else:
                self._referentiel.update_classe(classe)
                self.journal.log_modification(
                    code_utr, Tables.CLASSE, classe.id_classe, classe.libelle)
            return Result.ok("Classe enregistrée.")
        except Exception as ex:
            return self.failure("Enregistrement d’une classe", ex)

    def delete_classe(self, id_classe: int, code_utr: str) -> Result:
        try:
            classe = self._referentiel.get_classe(id_classe)
            if classe is None:
                return Result.fail("Classe introuvable.", "INTROUVABLE")
            inscrits = self._referentiel.count_inscrits(id_classe)
            if inscrits > 0:
                return Result.fail(
                    f"Suppression impossible : {inscrits} inscription(s) rattachée(s) "
                    "à cette classe.", "LIAISON")
            self._referentiel.delete_classe(id_classe)
            self.journal.log_suppression(
                code_utr, Tables.CLASSE, id_classe, classe.libelle)
            return Result.ok("Classe supprimée.")
        except Exception as ex:
            if error_helper.is_foreign_key_violation(ex):
                return Result.fail(
                    "Suppression impossible : des programmes, épreuves ou emplois du "
                    "temps utilisent cette classe.", "LIAISON")
            return self.failure("Suppression d’une classe", ex)

    # ----- Modules et matières -----

    def list_modules(self, code_filiere: Optional[str] = None) -> List[ModuleFormation]:
        try:
            return self._referentiel.list_modules(code_filiere)
        except Exception as ex:
            self.logger.error("Liste des modules", ex)
            return []

    def save_module(self, module: ModuleFormation, code_utr: str) -> Result:
        code = (module.code_module or "").strip()
        if not code:
            return Result.fail("Code module obligatoire.", "VALIDATION")
        if not (module.module_lib or "").strip():
            return Result.fail("Libellé du module obligatoire.", "VALIDATION")
        module.code_module = code
        try:
            if self._referentiel.get_module(code) is None:
                self._referentiel.insert_module(module)
                self.journal.log_creation(code_utr, Tables.MODULE_FORMATION, None, code)
                return Result.ok(f"Module « {code} » créé.")
            self._referentiel.update_module(module)
            self.journal.log_modification(code_utr, Tables.MODULE_FORMATION, None, code)
            return Result.ok(f"Module « {code} » enregistré.")
        except Exception as ex:
            if error_helper.is_unique_violation(ex):
                return Result.fail("Ce code module existe déjà.", "DOUBLON")
            return self.failure("Enregistrement d’un module", ex)

    def delete_module(self, code: str, code_utr: str) -> Result:
        try:
            if self._referentiel.get_module(code) is None:
                return Result.fail("Module introuvable.", "INTROUVABLE")
            self._referentiel.delete_module(code)
            self.journal.log_suppression(code_utr, Tables.MODULE_FORMATION, None, code)
            return Result.ok("Module supprimé.")
        except Exception as ex:
            if error_helper.is_foreign_key_violation(ex):
                return Result.fail(
                    "Suppression impossible : des matières utilisent ce module.", "LIAISON")
            return self.failure("Suppression d’un module", ex)

    def list_matieres(self, code_module: Optional[str] = None) -> List[Matiere]:
        try:
            return self._referentiel.list_matieres(code_module)
        except Exception as ex:
            self.logger.error("Liste des matières", ex)
            return []

    def save_matiere(self, matiere: Matiere, code_utr: str) -> Result:
        code = (matiere.code_matiere or "").strip()
        if not code:
            return Result.fail("Code matière obligatoire.", "VALIDATION")
        if len(code) > 20:
            return Result.fail("Code matière : 20 caractères maximum.", "VALIDATION")
        if not (matiere.libelle or "").strip():
            return Result.fail("Libellé de la matière obligatoire.", "VALIDATION")
        if matiere.code_module and self._referentiel.get_module(matiere.code_module) is None:
            return Result.fail("Module inconnu.", "INTROUVABLE")
        matiere.code_matiere = code
        try:
            if self._referentiel.get_matiere(code) is None:
                self._referentiel.insert_matiere(matiere)
                self.journal.log_creation(code_utr, Tables.MATIERE, None, code)
                return Result.ok(f"Matière « {code} » créée.")
            self._referentiel.update_matiere(matiere)
            self.journal.log_modification(code_utr, Tables.MATIERE, None, code)
            return Result.ok(f"Matière « {code} » enregistrée.")
        except Exception as ex:
            if error_helper.is_unique_violation(ex):
                return Result.fail("Ce code matière existe déjà.", "DOUBLON")
            return self.failure("Enregistrement d’une matière", ex)

    def delete_matiere(self, code: str, code_utr: str) -> Result:
        try:
            if self._referentiel.get_matiere(code) is None:
                return Result.fail("Matière introuvable.", "INTROUVABLE")
            self._referentiel.delete_matiere(code)
            self.journal.log_suppression(code_utr, Tables.MATIERE, None, code)
            return Result.ok("Matière supprimée.")
        except Exception as ex:
            if error_helper.is_foreign_key_violation(ex):
                return Result.fail(
                    "Suppression impossible : des programmes, bulletins ou épreuves "
                    "utilisent cette matière.", "LIAISON")
            return self.failure("Suppression d’une matière", ex)
