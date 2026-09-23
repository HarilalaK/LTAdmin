"""Tests Examens : épreuves, notes d'examen, résultats finaux pondérés."""

from __future__ import annotations

import datetime as _dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ltadmin.models.entities import (  # noqa: E402
    Epreuve,
    Etudiant,
    Evaluation,
    Inscription,
    Programme,
    SessionExam,
)
from test_base import BaseTestCase  # noqa: E402
from test_grades_bulletins import GradeFlowTestCase  # noqa: E402


class TestExamens(GradeFlowTestCase):

    def _creer_session(self) -> int:
        session = SessionExam(libelle="Examens finaux 2026", nature="EXAMEN FINAL",
                              date_debut=_dt.datetime(2026, 6, 1),
                              date_fin=_dt.datetime(2026, 6, 15))
        result = self.services.exams.create_session(session, "ADMIN")
        self.assertTrue(result.success, result.message)
        return session.id_session

    def _creer_epreuve(self, id_session: int, code_matiere: str,
                       coefficient: float = 1.0, bareme: float = 20.0) -> int:
        epreuve = Epreuve(
            id_session=id_session,
            id_classe=self.ID_CLASSE,
            code_matiere=code_matiere,
            date_epreuve=_dt.datetime(2026, 6, 2),
            heure_debut="08:00",
            duree_mn=120,
            coefficient=coefficient,
            bareme=bareme,
        )
        result = self.services.exams.create_epreuve(epreuve, "ADMIN")
        self.assertTrue(result.success, result.message)
        return epreuve.id_epreuve

    def test_session_epreuve_notes(self):
        id_session = self._creer_session()
        id_epreuve = self._creer_epreuve(id_session, "FRA", coefficient=2.0)
        grille = self.services.exams.get_grille_saisie(id_epreuve)
        self.assertEqual(len(grille), 3)  # les 3 inscrits
        result = self.services.exams.upsert_note(
            id_epreuve, self.inscrits[0], 15.0, False, "C-001", "ADMIN")
        self.assertTrue(result.success)
        result = self.services.exams.upsert_note(
            id_epreuve, self.inscrits[0], 18.0, False, "C-001", "ADMIN")
        self.assertTrue(result.success)  # remplace la note
        grille = self.services.exams.get_grille_saisie(id_epreuve)
        ligne = next(r for r in grille if r.id_inscription == self.inscrits[0])
        self.assertEqual(ligne.valeur_note, 18.0)

    def test_note_hors_bareme_refusee(self):
        id_session = self._creer_session()
        id_epreuve = self._creer_epreuve(id_session, "ANG", bareme=10.0)
        result = self.services.exams.upsert_note(
            id_epreuve, self.inscrits[0], 11.0, False, None, "ADMIN")
        self.assertFalse(result.success)

    def test_session_cloturee_fige_saisie(self):
        id_session = self._creer_session()
        id_epreuve = self._creer_epreuve(id_session, "FRA")
        self.assertTrue(self.services.exams.set_session_cloturee(
            id_session, True, "ADMIN").success)
        result = self.services.exams.upsert_note(
            id_epreuve, self.inscrits[0], 12.0, False, None, "ADMIN")
        self.assertFalse(result.success)
        self.assertEqual(result.code, "GESTION")

    def test_resultats_finaux_ponderes(self):
        """MOY_CC (bulletins) + MOY_EXAM (notes/20 × coef) → MOYENNE_GEN."""
        # --- Contrôle continu : une éval FRA (coef 2) et ANG (coef 1).
        id_eval_fra = self._creer_evaluation("FRA")
        id_eval_ang = self._creer_evaluation("ANG")
        self._saisir(id_eval_fra, self.inscrits[0], 16.0)
        self._saisir(id_eval_ang, self.inscrits[0], 10.0)
        self.assertTrue(self.services.bulletins.generer(
            self.ID_CLASSE, self.ID_PERIODE, "ADMIN").success)
        # CC de l'inscrit 0 = (16×2 + 10)/3 = 14.
        # --- Examen : FRA coef 2 note 15 ; ANG coef 1 note 9.
        id_session = self._creer_session()
        id_epreuve_fra = self._creer_epreuve(id_session, "FRA", coefficient=2.0)
        id_epreuve_ang = self._creer_epreuve(id_session, "ANG", coefficient=1.0)
        self.assertTrue(self.services.exams.upsert_note(
            id_epreuve_fra, self.inscrits[0], 15.0, False, None,
            "ADMIN").success)
        self.assertTrue(self.services.exams.upsert_note(
            id_epreuve_ang, self.inscrits[0], 9.0, False, None,
            "ADMIN").success)
        # MOY_EXAM = (15×2 + 9×1) / 3 = 13.
        result = self.services.exams.generer_resultats(
            self.ID_CLASSE, id_session, "ADMIN")
        self.assertTrue(result.success, result.message)
        # MOYENNE_GEN = 14×40% + 13×60% = 5.6 + 7.8 = 13.4.
        resultat = self.services.exams.get_resultat(self.inscrits[0])
        self.assertIsNotNone(resultat)
        self.assertAlmostEqual(resultat.moy_cc, 14.0, places=4)
        self.assertAlmostEqual(resultat.moy_exam, 13.0, places=4)
        self.assertAlmostEqual(resultat.moyenne_gen, 13.4, places=4)
        self.assertEqual(resultat.decision, "ADMIS")
        self.assertIn(resultat.mention, ("Bien", "Assez Bien"))  # 13.4 → Bien [14[ non → Assez Bien

    def test_resultats_idempotents(self):
        id_session = self._creer_session()
        id_epreuve = self._creer_epreuve(id_session, "FRA")
        self.assertTrue(self.services.exams.upsert_note(
            id_epreuve, self.inscrits[0], 12.0, False, None, "ADMIN").success)
        for _ in range(2):
            result = self.services.exams.generer_resultats(
                self.ID_CLASSE, id_session, "ADMIN")
            self.assertTrue(result.success)
        # Une ligne par inscrit, pas de doublon.
        total = self.services.database.scalar(
            "SELECT COUNT(*) FROM [RESULTAT_FINAL]")
        self.assertEqual(int(total), 3)

    def test_resultat_sans_examen_reprend_cc(self):
        """Aucune note d'examen → MOYENNE_GEN = MOY_CC."""
        id_eval_fra = self._creer_evaluation("FRA")
        self._saisir(id_eval_fra, self.inscrits[0], 12.0)
        self.assertTrue(self.services.bulletins.generer(
            self.ID_CLASSE, self.ID_PERIODE, "ADMIN").success)
        id_session = self._creer_session()
        self.assertTrue(self.services.exams.generer_resultats(
            self.ID_CLASSE, id_session, "ADMIN").success)
        resultat = self.services.exams.get_resultat(self.inscrits[0])
        self.assertAlmostEqual(resultat.moy_cc, 12.0, places=4)
        self.assertIsNone(resultat.moy_exam)
        self.assertAlmostEqual(resultat.moyenne_gen, 12.0, places=4)


if __name__ == "__main__":
    unittest.main()
