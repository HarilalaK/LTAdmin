"""Génération des bulletins : moyennes pondérées par matière, points,
moyenne générale, rang « competition », mentions (GRILLE_MENTION), décision,
min / max / rang par matière et moyenne de classe.

La génération (ou la régénération) supprime puis recrée les bulletins de la
combinaison (classe, période) dans une seule transaction.
"""

from __future__ import annotations

import datetime as _dt
from typing import Dict, List, Optional, Tuple

from ltadmin.core.result import Result, ResultValue
from ltadmin.data.access_database import AccessDatabase
from ltadmin.data.schema import Tables
from ltadmin.models.dto import BulletinResume, InscriptionDetail
from ltadmin.models.entities import (
    Bulletin,
    BulletinLigne,
    Classe,
    GrilleMention,
    PeriodeEval,
    Programme,
)
from ltadmin.repositories.bulletin_repository import BulletinRepository
from ltadmin.repositories.enrollment_repository import EnrollmentRepository
from ltadmin.repositories.evaluation_repository import EvaluationRepository
from ltadmin.repositories.planning_repository import PlanningRepository
from ltadmin.repositories.referentiel_repository import ReferentielRepository
from ltadmin.repositories.staff_repository import StaffRepository
from ltadmin.services.business.mention_helper import (
    appreciation_pour,
    rangs_competition,
    trouver,
)
from ltadmin.services.common import ServiceBase
from ltadmin.services.logging.app_logger import AppLogger
from ltadmin.services.logging.journal_service import JournalService
from ltadmin.services.referentiel.parametre_service import ParametreService


class BulletinService(ServiceBase):

    def __init__(self, database: AccessDatabase, logger: AppLogger,
                 journal: JournalService, parametres: ParametreService):
        super().__init__(database, logger, journal, parametres)
        self._bulletins = BulletinRepository(database)
        self._inscriptions = EnrollmentRepository(database)
        self._referentiel = ReferentielRepository(database)
        self._personnel = StaffRepository(database)
        self._evaluations = EvaluationRepository(database)
        self._planning = PlanningRepository(database)

    # ----- Consultation -----

    def list_resumes(self, id_classe: Optional[int] = None,
                     id_periode: Optional[int] = None) -> List[BulletinResume]:
        try:
            return self._bulletins.list_resumes(id_classe, id_periode)
        except Exception as ex:
            self.logger.error("Liste des bulletins", ex)
            return []

    def list_bulletins(self, id_classe: int, id_periode: int) -> List[Bulletin]:
        try:
            return self._bulletins.list_by_classe_periode(id_classe, id_periode)
        except Exception as ex:
            self.logger.error("Liste des bulletins d’une classe", ex)
            return []

    def get_by_inscription_periode(self, id_inscription: int,
                                   id_periode: int) -> Optional[Bulletin]:
        try:
            return self._bulletins.get_by_inscription_periode(id_inscription, id_periode)
        except Exception as ex:
            self.logger.error("Lecture d’un bulletin", ex)
            return None

    def list_lignes(self, id_bulletin: int) -> List[BulletinLigne]:
        try:
            return self._bulletins.list_lignes(id_bulletin)
        except Exception as ex:
            self.logger.error("Lecture des lignes d’un bulletin", ex)
            return []

    def get_grille_mentions(self) -> List[GrilleMention]:
        try:
            return self._bulletins.list_mentions()
        except Exception as ex:
            self.logger.error("Lecture de la grille des mentions", ex)
            return []

    def update_appreciation(self, bulletin: Bulletin, appreciation: Optional[str],
                            code_utr: str) -> Result:
        """Modifie l'appréciation générale d'un bulletin existant (sans recalcul)."""
        if bulletin.id_bulletin is None:
            return Result.fail("Bulletin introuvable.", "INTROUVABLE")
        if appreciation and len(appreciation) > 510:
            return Result.fail("Appréciation : 510 caractères maximum.", "VALIDATION")
        try:
            bulletin.appreciation = appreciation
            self._bulletins.update_appreciation(bulletin)
            self.journal.log_modification(
                code_utr, Tables.BULLETIN, bulletin.id_bulletin, "Appréciation modifiée.")
            return Result.ok("Appréciation enregistrée.")
        except Exception as ex:
            return self.failure("Modification d’une appréciation", ex)

    # ----- Génération -----

    def generer(self, id_classe: int, id_periode: int, code_utr: str) -> ResultValue[int]:
        """Génère (ou régénère) les bulletins d'une classe pour une période."""
        try:
            classe = self._referentiel.get_classe(id_classe)
            if classe is None:
                return ResultValue.fail("Classe introuvable.", "INTROUVABLE")
            periode = self._evaluations.get_periode(id_periode)
            if periode is None:
                return ResultValue.fail("Période d’évaluation introuvable.", "INTROUVABLE")

            programmes: List[Programme] = [
                prog for prog in self._personnel.list_by_classe(id_classe)
                if (prog.coefficient or 0) > 0
            ]
            if not programmes:
                return ResultValue.fail(
                    f"Aucune matière programmée pour « {classe.libelle} ».", "GESTION")

            inscrits: List[InscriptionDetail] = self._inscriptions.list_by_classe(id_classe)
            if not inscrits:
                return ResultValue.fail(
                    f"Aucun étudiant inscrit dans « {classe.libelle} ».", "GESTION")

            # Moyennes sur 20 par matière (R_MOYENNE_MATIERE filtrée classe × période).
            moyennes: Dict[Tuple[int, str], float] = {}
            formateurs: Dict[str, Optional[int]] = {}
            for row in self._evaluations.list_moyennes_matiere(id_classe, id_periode):
                if row.id_inscription is None or row.code_matiere is None:
                    continue
                if row.moyenne_mat is not None:
                    moyennes[(row.id_inscription, row.code_matiere)] = row.moyenne_mat

            grille = self._bulletins.list_mentions()
            moy_admission = self.parametres.moy_admission
            seuil_absence = self.parametres.seuil_absence

            generes = 0
            with self.db.begin_transaction():
                # Régénération : suppression ciblée (lignes puis entêtes) puis
                # recréation complète de la combinaison (classe × période).
                for id_bulletin in self._bulletins.list_ids_by_classe_periode(
                        id_classe, id_periode):
                    self._bulletins.delete_lignes_by_bulletin(id_bulletin)
                    self._bulletins.delete_bulletin(id_bulletin)

                lignes_par_matiere: Dict[str, list] = {}
                bulletins: List[Bulletin] = []

                for inscrit in inscrits:
                    lignes: List[BulletinLigne] = []
                    total_points = 0.0
                    total_coef = 0.0
                    for programme in programmes:
                        moyenne_mat = moyennes.get(
                            (inscrit.id_inscription, programme.code_matiere))
                        if moyenne_mat is None:
                            continue
                        coefficient = programme.coefficient or 1.0
                        points = moyenne_mat * coefficient
                        total_points += points
                        total_coef += coefficient
                        lignes.append(BulletinLigne(
                            id_bulletin=None,
                            code_matiere=programme.code_matiere,
                            moyenne_mat=moyenne_mat,
                            coefficient=coefficient,
                            points=points,
                            id_formateur=programme.id_formateur,
                        ))
                        formateurs.setdefault(programme.code_matiere, programme.id_formateur)

                    moyenne = total_points / total_coef if total_coef > 0 else None
                    mention = trouver(grille, moyenne)
                    admis = moyenne is not None and moyenne >= moy_admission

                    nb_absence = self._planning.sum_heures_absence(inscrit.id_inscription)
                    appreciation = appreciation_pour(
                        mention.mention if mention else None, admis)
                    if seuil_absence and nb_absence >= seuil_absence:
                        appreciation = ("Absences excessives "
                                        f"({nb_absence:g} h). " + appreciation)

                    bulletin = Bulletin(
                        id_inscription=inscrit.id_inscription,
                        id_periode=id_periode,
                        moyenne=moyenne,
                        total_points=total_points if lignes else None,
                        total_coef=total_coef if lignes else None,
                        nb_absence=nb_absence,
                        appreciation=appreciation,
                        decision=("ADMIS" if admis else "AJOURNE") if moyenne is not None
                        else None,
                        date_edition=_dt.datetime.now(),
                    )
                    bulletin.id_bulletin = self._bulletins.insert_bulletin(bulletin)
                    for ligne in lignes:
                        ligne.id_bulletin = bulletin.id_bulletin
                        ligne.id_ligne = self._bulletins.insert_ligne(ligne)
                        lignes_par_matiere.setdefault(ligne.code_matiere, []).append(ligne)
                    bulletins.append(bulletin)
                    generes += 1

                # Stats par matière : rang (competition), min et max de la classe.
                for code_matiere, lignes_matiere in lignes_par_matiere.items():
                    valeurs = [(ligne.id_ligne, ligne.moyenne_mat)
                               for ligne in lignes_matiere]
                    rangs = rangs_competition(valeurs)
                    valeurs_non_nulles = [v for _, v in valeurs if v is not None]
                    for ligne in lignes_matiere:
                        ligne.rang_mat = rangs.get(ligne.id_ligne, 0)
                        ligne.moy_min = min(valeurs_non_nulles) if valeurs_non_nulles else None
                        ligne.moy_max = max(valeurs_non_nulles) if valeurs_non_nulles else None
                        self._bulletins.update_ligne_stats(ligne)

                # Rang général, effectif et moyenne de classe.
                valeurs_generales = [(b.id_bulletin, b.moyenne) for b in bulletins]
                rangs_generaux = rangs_competition(valeurs_generales)
                moyennes_classe = [b.moyenne for b in bulletins if b.moyenne is not None]
                moy_classe = (sum(moyennes_classe) / len(moyennes_classe)
                              if moyennes_classe else None)
                for bulletin in bulletins:
                    bulletin.rang = rangs_generaux.get(bulletin.id_bulletin, 0)
                    bulletin.effectif = len(bulletins)
                    bulletin.moy_classe = moy_classe
                    self._bulletins.update_rang(bulletin)

            periode_libelle = periode.libelle or periode.code_periode or id_periode
            self.journal.log_operation(
                code_utr, "GENERATION_BULLETINS", Tables.BULLETIN, id_classe,
                f"{classe.libelle} × {periode_libelle} : {generes} bulletin(s).")
            return ResultValue.ok(
                generes, f"{generes} bulletin(s) généré(s) pour « {classe.libelle} ».")
        except Exception as ex:
            return self.failure_value("Génération des bulletins", ex)
