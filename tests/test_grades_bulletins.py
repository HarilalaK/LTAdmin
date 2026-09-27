"""Tests Notes → Moyennes → Bulletins : parcours complet du contrôle continu."""

from __future__ import annotations

import datetime as _dt
import os
import sys
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ltadmin.models.entities import (  # noqa: E402
    Etudiant,
    Evaluation,
    Formateur,
    Inscription,
    PeriodeEval,
    Programme,
)
from test_base import BaseTestCase  # noqa: E402


class GradeFlowTestCase(BaseTestCase):
    """Socle commun : 1 classe, 2 matières, 3 étudiants, 1 période (EV1)."""

    ID_CLASSE = 1
    ID_PERIODE = 1

    def setUp(self):
        super().setUp()
        self.formateur = Formateur(matricule="FOR-T-0001", nom="ENSEIGNANT",
                                   prenom="Test", actif=True,
                                   taux_horaire=Decimal("20000"))
        from ltadmin.repositories.staff_repository import StaffRepository
        self.id_formateur = StaffRepository(
            self.services.database).insert_formateur(self.formateur)
        # Programme : 2 matières avec coefficients 2 et 1.
        self.programmes = {}
        for code_matiere, coefficient in (("FRA", 2.0), ("ANG", 1.0)):
            programme = Programme(id_classe=self.ID_CLASSE,
                                  code_matiere=code_matiere,
                                  id_formateur=self.id_formateur,
                                  coefficient=coefficient)
            self.programmes[code_matiere] = StaffRepository(
                self.services.database).insert_programme(programme)
        # 3 étudiants inscrits.
        self.inscrits = []
        for index, (nom, prenom) in enumerate(
                (("BEKOE", "Alain"), ("CHEUNG", "Bora"), ("DIALLO", "Céline"))):
            etudiant = Etudiant(nom=nom, prenom=prenom, sexe="F" if index == 2
                                else "M")
            result = self.services.students.create(etudiant, "ADMIN")
            self.assertTrue(result.success)
            inscription = Inscription(id_etudiant=etudiant.id_etudiant,
                                      id_classe=self.ID_CLASSE)
            result = self.services.enrollments.inscrire(inscription, "ADMIN")
            self.assertTrue(result.success)
            self.inscrits.append(result.value)

    def _creer_evaluation(self, code_matiere: str, bareme: float = 20.0,
                          poids: float = 1.0) -> int:
        evaluation = Evaluation(
            id_periode=self.ID_PERIODE,
            id_prog=self.programmes[code_matiere],
            intitule=f"Devoir {code_matiere}",
            nature="DEVOIR",
            bareme=bareme,
            poids=poids,
            publiee=False,
        )
        result = self.services.evaluations.create_evaluation(evaluation, "ADMIN")
        self.assertTrue(result.success, result.message)
        return evaluation.id_evaluation

    def _saisir(self, id_evaluation: int, id_inscription: int, note, absent=False):
        result = self.services.grades.upsert_note(
            id_evaluation, id_inscription, note, absent, None, "ADMIN")
        self.assertTrue(result.success, result.message)


class TestEvaluations(GradeFlowTestCase):

    def test_creation_evaluation_et_barre_defaut(self):
        evaluation = Evaluation(id_periode=self.ID_PERIODE,
                                id_prog=self.programmes["FRA"],
                                intitule="Interro surprise", nature="INTERRO")
        result = self.services.evaluations.create_evaluation(evaluation, "ADMIN")
        self.assertTrue(result.success)
        relu = self.services.evaluations.get_evaluation_detail(
            evaluation.id_evaluation)
        self.assertEqual(relu.bareme, 20.0)  # BAREME_DEFAUT
        self.assertEqual(relu.poids, 1.0)

    def test_validation_bareme_positif(self):
        """Barème ≤ 0 → remplacé par BAREME_DEFAUT (comportement C#)."""
        evaluation = Evaluation(id_periode=self.ID_PERIODE,
                                id_prog=self.programmes["FRA"],
                                intitule="Bug", bareme=0, poids=1.0)
        result = self.services.evaluations.create_evaluation(evaluation, "ADMIN")
        self.assertTrue(result.success, result.message)
        relu = self.services.evaluations.get_evaluation_detail(
            evaluation.id_evaluation)
        self.assertEqual(relu.bareme, 20.0)

    def test_periode_cloturee_fige_tout(self):
        evaluation = Evaluation(
            id_periode=self.ID_PERIODE, id_prog=self.programmes["FRA"],
            intitule="Verrou", nature="DEVOIR", bareme=20.0, poids=1.0)
        self.assertTrue(self.services.evaluations.create_evaluation(
            evaluation, "ADMIN").success)
        # Clôture de la période.
        self.assertTrue(self.services.evaluations.set_periode_cloturee(
            self.ID_PERIODE, True, "ADMIN").success)
        # Nouvelle note refusée.
        result = self.services.grades.upsert_note(
            evaluation.id_evaluation, self.inscrits[0], 12.0, False, None,
            "ADMIN")
        self.assertFalse(result.success)
        self.assertEqual(result.code, "GESTION")
        # Nouvelle évaluation refusée.
        autre = Evaluation(id_periode=self.ID_PERIODE,
                           id_prog=self.programmes["ANG"], intitule="Blocage")
        self.assertFalse(self.services.evaluations.create_evaluation(
            autre, "ADMIN").success)
        # Réouverture : la saisie redevient possible.
        self.assertTrue(self.services.evaluations.set_periode_cloturee(
            self.ID_PERIODE, False, "ADMIN").success)
        self.assertTrue(self.services.grades.upsert_note(
            evaluation.id_evaluation, self.inscrits[0], 12.0, False, None,
            "ADMIN").success)


class TestNotes(GradeFlowTestCase):

    def test_note_hors_bareme_refusee(self):
        id_evaluation = self._creer_evaluation("FRA")
        result = self.services.grades.upsert_note(
            id_evaluation, self.inscrits[0], 25.0, False, None, "ADMIN")
        self.assertFalse(result.success)
        self.assertEqual(result.code, "VALIDATION")

    def test_note_negative_refusee(self):
        id_evaluation = self._creer_evaluation("FRA")
        result = self.services.grades.upsert_note(
            id_evaluation, self.inscrits[0], -1.0, False, None, "ADMIN")
        self.assertFalse(result.success)

    def test_absent_puis_modification(self):
        id_evaluation = self._creer_evaluation("FRA")
        self._saisir(id_evaluation, self.inscrits[0], None, absent=True)
        grille = self.services.grades.get_grille_saisie(id_evaluation)
        ligne = next(r for r in grille if r.id_inscription == self.inscrits[0])
        self.assertTrue(ligne.absent)
        self.assertIsNone(ligne.valeur_note)
        # Remplacement par une note.
        self._saisir(id_evaluation, self.inscrits[0], 14.0)
        grille = self.services.grades.get_grille_saisie(id_evaluation)
        ligne = next(r for r in grille if r.id_inscription == self.inscrits[0])
        self.assertFalse(ligne.absent)
        self.assertEqual(ligne.valeur_note, 14.0)

    def test_moyenne_matiere_ponderee(self):
        """R_MOYENNE_MATIERE : note1/bareme×20×poids + note2/bareme×20×poids
        divisé par la somme des poids."""
        # Devoir 1 : bareme 10, poids 1, notes 8/10 et 6/10.
        id_eval1 = self._creer_evaluation("FRA", bareme=10.0, poids=1.0)
        # Devoir 2 : bareme 20, poids 3.
        id_eval2 = self._creer_evaluation("FRA", bareme=20.0, poids=3.0)
        id_inscription = self.inscrits[0]
        self._saisir(id_eval1, id_inscription, 8.0)
        self._saisir(id_eval2, id_inscription, 6.0)
        # (8/10×20×1 + 6/20×20×3) / (1+3) = (16 + 18) / 4 = 8.5
        moyennes = self.services.grades.get_moyennes_matiere(
            id_classe=self.ID_CLASSE, id_periode=self.ID_PERIODE)
        ligne = next(m for m in moyennes
                     if m.id_inscription == id_inscription
                     and m.code_matiere == "FRA")
        self.assertAlmostEqual(ligne.moyenne_mat, 8.5, places=5)

    def test_absent_exclu_de_la_moyenne(self):
        id_eval1 = self._creer_evaluation("FRA", bareme=20.0, poids=1.0)
        id_eval2 = self._creer_evaluation("FRA", bareme=20.0, poids=1.0)
        id_inscription = self.inscrits[0]
        self._saisir(id_eval1, id_inscription, 10.0)
        self._saisir(id_eval2, id_inscription, None, absent=True)
        # Seule la note 10 compte : moyenne = 10.
        moyennes = self.services.grades.get_moyennes_matiere(
            id_classe=self.ID_CLASSE, id_periode=self.ID_PERIODE)
        ligne = next(m for m in moyennes
                     if m.id_inscription == id_inscription
                     and m.code_matiere == "FRA")
        self.assertAlmostEqual(ligne.moyenne_mat, 10.0, places=5)


class TestBulletins(GradeFlowTestCase):

    def _remplir_notes(self):
        """FRA coef 2 : 16, 14, 10 — ANG coef 1 : 10, 12, 8."""
        notes_fra = {self.inscrits[0]: 16.0, self.inscrits[1]: 14.0,
                     self.inscrits[2]: 10.0}
        notes_ang = {self.inscrits[0]: 10.0, self.inscrits[1]: 12.0,
                     self.inscrits[2]: 8.0}
        id_eval_fra = self._creer_evaluation("FRA")
        id_eval_ang = self._creer_evaluation("ANG")
        for id_inscription, note in notes_fra.items():
            self._saisir(id_eval_fra, id_inscription, note)
        for id_inscription, note in notes_ang.items():
            self._saisir(id_eval_ang, id_inscription, note)

    def test_generation_bulletins(self):
        self._remplir_notes()
        result = self.services.bulletins.generer(
            self.ID_CLASSE, self.ID_PERIODE, "ADMIN")
        self.assertTrue(result.success, result.message)
        self.assertEqual(result.value, 3)
        bulletins = self.services.bulletins.list_resumes(
            self.ID_CLASSE, self.ID_PERIODE)
        self.assertEqual(len(bulletins), 3)
        # Moyennes attendues : (16×2+10)/3 = 14 ; (14×2+12)/3 ≈ 13.33 ;
        # (10×2+8)/3 = 9.33.
        par_inscrit = {}
        inscrits = self.services.enrollments.list_by_classe(self.ID_CLASSE)
        for bulletin in bulletins:
            par_inscrit[bulletin.id_inscription] = bulletin
        attendus = {self.inscrits[0]: 14.0, self.inscrits[1]: 40.0 / 3.0,
                    self.inscrits[2]: 28.0 / 3.0}
        for id_inscription, moyenne in attendus.items():
            self.assertAlmostEqual(par_inscrit[id_inscription].moyenne,
                                   moyenne, places=4)
        # Rangs « competition » : 1, 2, 3 ; effectif 3.
        self.assertEqual(par_inscrit[self.inscrits[0]].rang, 1)
        self.assertEqual(par_inscrit[self.inscrits[1]].rang, 2)
        self.assertEqual(par_inscrit[self.inscrits[2]].rang, 3)
        for bulletin in bulletins:
            self.assertEqual(bulletin.effectif, 3)
        # Décisions : MOY_ADMISSION = 10 → ADMIS, ADMIS, AJOURNE.
        self.assertEqual(par_inscrit[self.inscrits[0]].decision, "ADMIS")
        self.assertEqual(par_inscrit[self.inscrits[2]].decision, "AJOURNE")

    def test_rang_competition_ex_aequo(self):
        """Deux ex æquo en tête → rangs 1, 1, 3 (competition ranking)."""
        id_eval_fra = self._creer_evaluation("FRA")
        id_eval_ang = self._creer_evaluation("ANG")
        # Inscrits 1 et 2 identiques ; inscrit 3 plus faible.
        for id_inscription, (fra, ang) in {
                self.inscrits[0]: (14.0, 12.0),
                self.inscrits[1]: (14.0, 12.0),
                self.inscrits[2]: (8.0, 10.0)}.items():
            self._saisir(id_eval_fra, id_inscription, fra)
            self._saisir(id_eval_ang, id_inscription, ang)
        self.assertTrue(self.services.bulletins.generer(
            self.ID_CLASSE, self.ID_PERIODE, "ADMIN").success)
        bulletins = {b.id_inscription: b for b in
                     self.services.bulletins.list_resumes(
                         self.ID_CLASSE, self.ID_PERIODE)}
        self.assertEqual(bulletins[self.inscrits[0]].rang, 1)
        self.assertEqual(bulletins[self.inscrits[1]].rang, 1)  # ex æquo
        # Avec deux ex æquo en tête, le suivant est 3 (competition ranking).
        self.assertEqual(bulletins[self.inscrits[2]].rang, 3)

    def test_mentions_grille(self):
        """Moyenne 14 → « Bien » (grille initiale [14, 16[)."""
        from ltadmin.services.business.mention_helper import trouver
        grille = self.services.bulletins.get_grille_mentions()
        self.assertGreaterEqual(len(grille), 5)
        mention = trouver(grille, 15.0)
        self.assertIsNotNone(mention)
        self.assertEqual(mention.mention, "Bien")
        mention = trouver(grille, 20.0)  # borne max incluse
        self.assertEqual(mention.mention, "Tres Bien")
        mention = trouver(grille, 9.0)
        self.assertEqual(mention.mention, "Ajourne")

    def test_regeneration_idempotente(self):
        """La régénération ne duplique pas les bulletins."""
        self._remplir_notes()
        self.assertTrue(self.services.bulletins.generer(
            self.ID_CLASSE, self.ID_PERIODE, "ADMIN").success)
        self.assertTrue(self.services.bulletins.generer(
            self.ID_CLASSE, self.ID_PERIODE, "ADMIN").success)
        bulletins = self.services.bulletins.list_resumes(
            self.ID_CLASSE, self.ID_PERIODE)
        self.assertEqual(len(bulletins), 3)

    def test_lignes_min_max_rang_par_matiere(self):
        self._remplir_notes()
        self.assertTrue(self.services.bulletins.generer(
            self.ID_CLASSE, self.ID_PERIODE, "ADMIN").success)
        resumes = self.services.bulletins.list_resumes(
            self.ID_CLASSE, self.ID_PERIODE)
        premier = next(b for b in resumes if b.rang == 1)
        lignes = self.services.bulletins.list_lignes(premier.id_bulletin)
        self.assertEqual(len(lignes), 2)
        fra = next(l for l in lignes if l.code_matiere == "FRA")
        self.assertEqual(fra.moy_min, 10.0)
        self.assertEqual(fra.moy_max, 16.0)
        self.assertEqual(fra.rang_mat, 1)
        self.assertAlmostEqual(fra.points, 32.0)  # 16 × coef 2
        self.assertAlmostEqual(fra.coefficient, 2.0)


if __name__ == "__main__":
    unittest.main()
