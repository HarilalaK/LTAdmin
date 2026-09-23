"""Gestion des examens : sessions, épreuves, saisie des notes d'examen et
calcul des résultats finaux (moyenne CC + moyenne examen pondérées)."""

from __future__ import annotations

import datetime as _dt
from typing import List, Optional

from ltadmin.core.result import Result, ResultValue
from ltadmin.data import error_helper
from ltadmin.data.access_database import AccessDatabase
from ltadmin.data.schema import Tables
from ltadmin.models.dto import EpreuveDetail, NoteSaisieRow
from ltadmin.models.entities import Epreuve, NoteExamen, ResultatFinal, SessionExam
from ltadmin.repositories.bulletin_repository import BulletinRepository
from ltadmin.repositories.enrollment_repository import EnrollmentRepository
from ltadmin.repositories.exam_repository import ExamRepository
from ltadmin.services.business.mention_helper import rangs_competition, trouver
from ltadmin.services.common import ServiceBase
from ltadmin.services.logging.app_logger import AppLogger
from ltadmin.services.logging.journal_service import JournalService
from ltadmin.services.referentiel.parametre_service import ParametreService
from ltadmin.services.validation.validation import ExamValidator, GradeValidator


class ExamService(ServiceBase):

    def __init__(self, database: AccessDatabase, logger: AppLogger,
                 journal: JournalService, parametres: ParametreService):
        super().__init__(database, logger, journal, parametres)
        self._examens = ExamRepository(database)
        self._bulletins = BulletinRepository(database)
        self._inscriptions = EnrollmentRepository(database)

    # ----- Sessions -----

    def list_sessions(self, id_annee: Optional[int] = None) -> List[SessionExam]:
        try:
            return self._examens.list_sessions(id_annee)
        except Exception as ex:
            self.logger.error("Liste des sessions d’examen", ex)
            return []

    def get_session(self, id_session: int) -> Optional[SessionExam]:
        try:
            return self._examens.get_session(id_session)
        except Exception as ex:
            self.logger.error("Lecture d’une session", ex)
            return None

    def create_session(self, session: SessionExam, code_utr: str) -> ResultValue[int]:
        if session.id_annee is None:
            from ltadmin.repositories.admin_repository import AdminRepository
            annee = AdminRepository(self.db).get_annee_active()
            if annee is None:
                return ResultValue.fail(
                    "Aucune année scolaire active : activez-en une dans "
                    "l’administration.", "GESTION")
            session.id_annee = annee.id_annee
        validation = ExamValidator.validate_session(session)
        if not validation.is_valid:
            return self.invalid_value(validation)
        try:
            if session.cloturee is None:
                session.cloturee = False
            session.id_session = self._examens.insert_session(session)
            self.journal.log_creation(
                code_utr, Tables.SESSION_EXAM, session.id_session, session.libelle)
            return ResultValue.ok(session.id_session, "Session d’examen créée.")
        except Exception as ex:
            return self.failure_value("Création d’une session", ex)

    def update_session(self, session: SessionExam, code_utr: str) -> Result:
        if session.id_session is None:
            return Result.fail("Session introuvable.", "INTROUVABLE")
        validation = ExamValidator.validate_session(session)
        if not validation.is_valid:
            return self.invalid(validation)
        try:
            updated = self._examens.update_session(session)
            if updated == 0:
                return Result.fail("Session introuvable.", "INTROUVABLE")
            self.journal.log_modification(
                code_utr, Tables.SESSION_EXAM, session.id_session, session.libelle)
            return Result.ok("Session enregistrée.")
        except Exception as ex:
            return self.failure("Modification d’une session", ex)

    def set_session_cloturee(self, id_session: int, cloturee: bool, code_utr: str) -> Result:
        try:
            session = self._examens.get_session(id_session)
            if session is None:
                return Result.fail("Session introuvable.", "INTROUVABLE")
            self._examens.set_session_cloturee(id_session, cloturee)
            self.journal.log_operation(
                code_utr,
                "CLOTURE_SESSION" if cloturee else "REOUVERTURE_SESSION",
                Tables.SESSION_EXAM, id_session, session.libelle)
            return Result.ok(
                "Session clôturée : les notes d’examen sont figées." if cloturee
                else "Session rouverte.")
        except Exception as ex:
            return self.failure("Clôture d’une session", ex)

    def delete_session(self, id_session: int, code_utr: str) -> Result:
        try:
            session = self._examens.get_session(id_session)
            if session is None:
                return Result.fail("Session introuvable.", "INTROUVABLE")
            self._examens.delete_session(id_session)
            self.journal.log_suppression(
                code_utr, Tables.SESSION_EXAM, id_session, session.libelle)
            return Result.ok("Session supprimée.")
        except Exception as ex:
            if error_helper.is_foreign_key_violation(ex):
                return Result.fail(
                    "Suppression impossible : des épreuves et des notes d’examen "
                    "sont rattachées à cette session.", "LIAISON")
            return self.failure("Suppression d’une session", ex)

    # ----- Épreuves -----

    def list_epreuves(self, id_session: Optional[int] = None,
                      id_classe: Optional[int] = None) -> List[EpreuveDetail]:
        try:
            return self._examens.list_epreuves(id_session, id_classe)
        except Exception as ex:
            self.logger.error("Liste des épreuves", ex)
            return []

    def get_epreuve(self, id_epreuve: int) -> Optional[Epreuve]:
        try:
            return self._examens.get_epreuve(id_epreuve)
        except Exception as ex:
            self.logger.error("Lecture d’une épreuve", ex)
            return None

    def get_epreuve_detail(self, id_epreuve: int) -> Optional[EpreuveDetail]:
        try:
            return self._examens.get_epreuve_detail(id_epreuve)
        except Exception as ex:
            self.logger.error("Lecture d’une épreuve", ex)
            return None

    def create_epreuve(self, epreuve: Epreuve, code_utr: str) -> ResultValue[int]:
        if epreuve.bareme is None or epreuve.bareme <= 0:
            epreuve.bareme = self.parametres.bareme_defaut
        if epreuve.coefficient is None or epreuve.coefficient <= 0:
            epreuve.coefficient = 1.0
        validation = ExamValidator.validate_epreuve(epreuve)
        if not validation.is_valid:
            return self.invalid_value(validation)
        try:
            session = self._examens.get_session(epreuve.id_session)
            if session is None:
                return ResultValue.fail("Session d’examen introuvable.", "INTROUVABLE")
            epreuve.id_epreuve = self._examens.insert_epreuve(epreuve)
            self.journal.log_creation(
                code_utr, Tables.EPREUVE, epreuve.id_epreuve,
                f"Épreuve {epreuve.code_matiere}")
            return ResultValue.ok(epreuve.id_epreuve, "Épreuve créée.")
        except Exception as ex:
            return self.failure_value("Création d’une épreuve", ex)

    def update_epreuve(self, epreuve: Epreuve, code_utr: str) -> Result:
        if epreuve.id_epreuve is None:
            return Result.fail("Épreuve introuvable.", "INTROUVABLE")
        validation = ExamValidator.validate_epreuve(epreuve)
        if not validation.is_valid:
            return self.invalid(validation)
        try:
            updated = self._examens.update_epreuve(epreuve)
            if updated == 0:
                return Result.fail("Épreuve introuvable.", "INTROUVABLE")
            self.journal.log_modification(
                code_utr, Tables.EPREUVE, epreuve.id_epreuve, epreuve.code_matiere)
            return Result.ok("Épreuve enregistrée.")
        except Exception as ex:
            return self.failure("Modification d’une épreuve", ex)

    def delete_epreuve(self, id_epreuve: int, code_utr: str) -> Result:
        try:
            epreuve = self._examens.get_epreuve(id_epreuve)
            if epreuve is None:
                return Result.fail("Épreuve introuvable.", "INTROUVABLE")
            self._examens.delete_epreuve(id_epreuve)
            self.journal.log_suppression(
                code_utr, Tables.EPREUVE, id_epreuve, epreuve.code_matiere)
            return Result.ok("Épreuve supprimée.")
        except Exception as ex:
            if error_helper.is_foreign_key_violation(ex):
                return Result.fail(
                    "Suppression impossible : des notes d’examen sont rattachées "
                    "à cette épreuve.", "LIAISON")
            return self.failure("Suppression d’une épreuve", ex)

    # ----- Saisie des notes d'examen -----

    def get_grille_saisie(self, id_epreuve: int) -> List[NoteSaisieRow]:
        try:
            epreuve = self._examens.get_epreuve(id_epreuve)
            if epreuve is None or epreuve.id_classe is None:
                return []
            return self._examens.list_grille_saisie(id_epreuve, epreuve.id_classe)
        except Exception as ex:
            self.logger.error("Grille de saisie des notes d’examen", ex)
            return []

    def upsert_note(self, id_epreuve: int, id_inscription: int,
                    valeur: Optional[float], absent: bool,
                    copie_num: Optional[str], code_utr: str) -> Result:
        """Enregistre la note d'examen d'un inscrit (0 ≤ note ≤ barème)."""
        try:
            epreuve = self._examens.get_epreuve(id_epreuve)
            if epreuve is None:
                return Result.fail("Épreuve introuvable.", "INTROUVABLE")
            session = self._examens.get_session(epreuve.id_session)
            if session is not None and session.cloturee is True:
                return Result.fail(
                    "Session clôturée : les notes d’examen sont figées.", "GESTION")
            bareme = epreuve.bareme if epreuve.bareme is not None \
                else self.parametres.bareme_defaut
            validation = GradeValidator.validate_note(valeur, absent, bareme)
            if not validation.is_valid:
                return self.invalid(validation)
            if not copie_num or not copie_num.strip():
                copie_num = None
            elif len(copie_num) > 40:
                return Result.fail("N° de copie : 40 caractères maximum.", "VALIDATION")

            existing = self._examens.get_note_examen(id_epreuve, id_inscription)
            if existing is None:
                id_note = self._examens.insert_note_examen(NoteExamen(
                    id_epreuve=id_epreuve,
                    id_inscription=id_inscription,
                    valeur_note=None if absent else valeur,
                    absent=absent,
                    copie_num=copie_num,
                    date_saisie=_dt.datetime.now(),
                    code_utr=code_utr))
                self.journal.log_creation(
                    code_utr, Tables.NOTE_EXAMEN, id_note,
                    f"Épreuve {id_epreuve} / inscrit {id_inscription}")
            else:
                existing.valeur_note = None if absent else valeur
                existing.absent = absent
                existing.copie_num = copie_num
                existing.date_saisie = _dt.datetime.now()
                existing.code_utr = code_utr
                self._examens.update_note_examen(existing)
                self.journal.log_modification(
                    code_utr, Tables.NOTE_EXAMEN, existing.id_note_ex,
                    f"Épreuve {id_epreuve} / inscrit {id_inscription}")
            return Result.ok("Note d’examen enregistrée.")
        except Exception as ex:
            return self.failure("Saisie d’une note d’examen", ex)

    # ----- Résultats finaux -----

    def list_resultats(self, id_classe: int) -> List[ResultatFinal]:
        try:
            return self._bulletins.list_by_classe(id_classe)
        except Exception as ex:
            self.logger.error("Liste des résultats finaux", ex)
            return []

    def get_resultat(self, id_inscription: int) -> Optional[ResultatFinal]:
        try:
            return self._bulletins.get_by_inscription(id_inscription)
        except Exception as ex:
            self.logger.error("Lecture d’un résultat final", ex)
            return None

    def generer_resultats(self, id_classe: int, id_session: int,
                          code_utr: str) -> ResultValue[int]:
        """Calcule les résultats finaux d'une classe (idempotent).

        MOY_CC = moyenne des bulletins ; MOY_EXAM = Σ(note/bareme×20×coef)/Σcoef ;
        MOYENNE_GEN = CC×POIDS_CC/100 + EXAM×POIDS_EXAMEN/100 (une partie absente
        → l'autre seule ; aucune → NULL). Décision ADMIS/AJOURNÉ selon MOY_ADMISSION.
        """
        try:
            inscrits = self._inscriptions.list_by_classe(id_classe)
            if not inscrits:
                return ResultValue.fail("Aucun étudiant inscrit dans cette classe.", "GESTION")

            poids_cc = self.parametres.poids_cc
            poids_examen = self.parametres.poids_examen
            moy_admission = self.parametres.moy_admission
            grille = self._bulletins.list_mentions()

            # Notes d'examen ramenées sur 20 et pondérées par coefficient.
            examens: dict = {}
            for row in self._examens.list_notes_ponderes(id_classe, id_session):
                id_inscription = row.get("ID_INSCRIPTION")
                if id_inscription is None:
                    continue
                accum = examens.setdefault(id_inscription, {"points": 0.0, "coef": 0.0})
                absent = bool(row.get("ABSENT"))
                note = row.get("VALEUR_NOTE")
                if absent or note is None:
                    continue
                bareme = row.get("BAREME") or 20.0
                coefficient = row.get("COEFFICIENT") or 1.0
                if bareme <= 0 or coefficient <= 0:
                    continue
                accum["points"] += (float(note) / float(bareme)) * 20.0 * float(coefficient)
                accum["coef"] += float(coefficient)

            generes = 0
            valeurs: list = []
            with self.db.begin_transaction():
                for inscrit in inscrits:
                    # Idempotent : une seule ligne de résultat par inscription.
                    self._bulletins.delete_by_inscription(inscrit.id_inscription)

                    moyennes_bulletins = self._bulletins.list_moyennes_by_inscription(
                        inscrit.id_inscription)
                    moy_cc = (sum(moyennes_bulletins) / len(moyennes_bulletins)
                              if moyennes_bulletins else None)

                    accum = examens.get(inscrit.id_inscription)
                    moy_exam = (accum["points"] / accum["coef"]
                                if accum and accum["coef"] > 0 else None)

                    if moy_cc is not None and moy_exam is not None:
                        moyenne_gen = (moy_cc * poids_cc / 100.0
                                       + moy_exam * poids_examen / 100.0)
                    elif moy_cc is not None:
                        moyenne_gen = moy_cc
                    elif moy_exam is not None:
                        moyenne_gen = moy_exam
                    else:
                        moyenne_gen = None

                    admis = moyenne_gen is not None and moyenne_gen >= moy_admission
                    mention = trouver(grille, moyenne_gen)

                    resultat = ResultatFinal(
                        id_inscription=inscrit.id_inscription,
                        moy_cc=moy_cc,
                        moy_exam=moy_exam,
                        moyenne_gen=moyenne_gen,
                        mention=mention.mention if mention else None,
                        decision="ADMIS" if admis else "AJOURNE",
                        credit_valide=None,
                        date_delib=_dt.datetime.now(),
                        observation=None,
                    )
                    self._bulletins.insert_resultat(resultat)
                    generes += 1
                    if moyenne_gen is not None:
                        valeurs.append((inscrit.id_inscription, moyenne_gen))

            rangs = rangs_competition(valeurs)
            for id_inscription, _ in valeurs:
                resultat = self._bulletins.get_by_inscription(id_inscription)
                if resultat is not None:
                    resultat.rang = rangs.get(id_inscription, 0)
                    self._bulletins.update_resultat_rang(resultat)

            self.journal.log_operation(
                code_utr, "GENERATION_RESULTATS", Tables.RESULTAT_FINAL, id_classe,
                f"{generes} résultat(s) calculé(s).")
            return ResultValue.ok(generes, f"{generes} résultat(s) final(aux) calculé(s).")
        except Exception as ex:
            return self.failure_value("Calcul des résultats finaux", ex)
