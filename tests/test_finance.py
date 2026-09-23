"""Tests Écolage et Paie : échéanciers, encaissements, remises, calcul de paie."""

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
    Formateur,
    Inscription,
    Programme,
    Seance,
    Tarif,
)
from test_base import BaseTestCase  # noqa: E402


class EcoBaseTestCase(BaseTestCase):
    """Socle : un étudiant inscrit en classe 1."""

    ID_CLASSE = 1

    def setUp(self):
        super().setUp()
        etudiant = Etudiant(nom="CLIENT", prenom="Test")
        self.assertTrue(self.services.students.create(etudiant, "ADMIN").success)
        inscription = Inscription(id_etudiant=etudiant.id_etudiant,
                                  id_classe=self.ID_CLASSE,
                                  date_inscription=_dt.datetime(2025, 10, 5))
        result = self.services.enrollments.inscrire(inscription, "ADMIN")
        self.assertTrue(result.success)
        self.id_inscription = result.value


class TestEcheanciers(EcoBaseTestCase):

    def _tarif(self, montant="600000", tranches=1) -> int:
        tarif = Tarif(id_classe=self.ID_CLASSE, type_frais="Écolage annuel",
                      montant=Decimal(montant), nb_tranches=tranches,
                      obligatoire=True)
        result = self.services.ecolage.save_tarif(tarif, "ADMIN")
        self.assertTrue(result.success, result.message)
        return tarif.id_tarif

    def test_tarif_invalide_refuse(self):
        tarif = Tarif(id_classe=self.ID_CLASSE, type_frais="Frais",
                      montant=Decimal("-5"))
        result = self.services.ecolage.save_tarif(tarif, "ADMIN")
        self.assertFalse(result.success)
        tarif = Tarif(id_classe=self.ID_CLASSE, type_frais="Frais",
                      montant=Decimal("100"), nb_tranches=30)
        self.assertFalse(self.services.ecolage.save_tarif(tarif, "ADMIN").success)

    def test_echeancier_une_tranche(self):
        id_tarif = self._tarif("600000", 1)
        result = self.services.ecolage.generer_echeancier(
            self.id_inscription, id_tarif, "ADMIN")
        self.assertTrue(result.success, result.message)
        echeances = self.services.ecolage.list_echeances(self.id_inscription)
        self.assertEqual(len(echeances), 1)
        self.assertEqual(echeances[0].montant_du, Decimal("600000"))
        self.assertEqual(echeances[0].statut, "DU")

    def test_echeancier_mensuel_arrondi(self):
        """100 000 / 3 tranches = 33 333.33 ×2 + 33 333.34 (dernière absorbe)."""
        id_tarif = self._tarif("100000", 3)
        result = self.services.ecolage.generer_echeancier(
            self.id_inscription, id_tarif, "ADMIN")
        self.assertTrue(result.success)
        echeances = self.services.ecolage.list_echeances(self.id_inscription)
        self.assertEqual(len(echeances), 3)
        self.assertEqual(echeances[0].montant_du, Decimal("33333.33"))
        self.assertEqual(echeances[1].montant_du, Decimal("33333.33"))
        self.assertEqual(echeances[2].montant_du, Decimal("33333.34"))
        total = sum((e.montant_du for e in echeances), Decimal("0"))
        self.assertEqual(total, Decimal("100000"))
        # Tranches mensuelles : nov, déc, janv (inscription le 05/10/2025).
        self.assertEqual(echeances[0].date_echeance.month, 10)
        self.assertEqual(echeances[1].date_echeance.month, 11)
        self.assertEqual(echeances[2].date_echeance.month, 12)
        self.assertEqual(echeances[2].num_tranche, 3)

    def test_echeancier_idempotent(self):
        id_tarif = self._tarif("50000", 2)
        self.assertTrue(self.services.ecolage.generer_echeancier(
            self.id_inscription, id_tarif, "ADMIN").success)
        result = self.services.ecolage.generer_echeancier(
            self.id_inscription, id_tarif, "ADMIN")
        self.assertFalse(result.success)
        self.assertEqual(result.code, "DOUBLON")


class TestEncaissements(EcoBaseTestCase):

    def setUp(self):
        super().setUp()
        tarif = Tarif(id_classe=self.ID_CLASSE, type_frais="Écolage",
                      montant=Decimal("100000"), nb_tranches=2)
        self.assertTrue(self.services.ecolage.save_tarif(tarif, "ADMIN").success)
        self.id_tarif = tarif.id_tarif
        self.assertTrue(self.services.ecolage.generer_echeancier(
            self.id_inscription, self.id_tarif, "ADMIN").success)
        self.echeances = self.services.ecolage.list_echeances(
            self.id_inscription)
        self.assertEqual(len(self.echeances), 2)

    def test_encaissement_partiel_puis_solde(self):
        echeance = self.echeances[0]
        self.assertEqual(echeance.montant_du, Decimal("50000"))
        result = self.services.ecolage.encaisser(
            echeance.id_echeance, Decimal("20000"), "Espèces", None, None,
            "CAISSE")
        self.assertTrue(result.success, result.message)
        cree = result.value
        self.assertRegex(cree.num_recu, r"^REC-\d{4}-\d{6}$")
        self.assertEqual(cree.nouveau_statut, "PARTIEL")
        # Le reste ne peut pas dépasser 30 000 + 0,01.
        trop = self.services.ecolage.encaisser(
            echeance.id_echeance, Decimal("35000"), "Espèces", None, None,
            "CAISSE")
        self.assertFalse(trop.success)
        # Solder.
        result = self.services.ecolage.encaisser(
            echeance.id_echeance, Decimal("30000"), "Virement", "VIR-9", None,
            "CAISSE")
        self.assertTrue(result.success)
        self.assertEqual(result.value.nouveau_statut, "SOLDE")
        # Un encaissement de plus est refusé.
        encore = self.services.ecolage.encaisser(
            echeance.id_echeance, Decimal("1"), "Espèces", None, None, "CAISSE")
        self.assertFalse(encore.success)

    def test_reçu_unique_et_numérotation(self):
        echeance = self.echeances[0]
        result1 = self.services.ecolage.encaisser(
            echeance.id_echeance, Decimal("1000"), "Espèces", None, None, "A")
        result2 = self.services.ecolage.encaisser(
            echeance.id_echeance, Decimal("1000"), "Espèces", None, None, "A")
        self.assertTrue(result1.success and result2.success)
        self.assertNotEqual(result1.value.num_recu, result2.value.num_recu)

    def test_montant_negatif_ou_nul_refuse(self):
        echeance = self.echeances[0]
        for montant in (Decimal("0"), Decimal("-10")):
            result = self.services.ecolage.encaisser(
                echeance.id_echeance, montant, "Espèces", None, None, "A")
            self.assertFalse(result.success)

    def test_annulation_paiement_recalcule_statut(self):
        echeance = self.echeances[0]
        result = self.services.ecolage.encaisser(
            echeance.id_echeance, Decimal("50000"), "Espèces", None, None,
            "CAISSE")
        self.assertTrue(result.success)
        self.assertEqual(result.value.nouveau_statut, "SOLDE")
        id_paiement = result.value.id_paiement
        self.assertTrue(self.services.ecolage.annuler_paiement(
            id_paiement, "ADMIN").success)
        echeances = self.services.ecolage.list_echeances(self.id_inscription)
        self.assertEqual(echeances[0].statut, "DU")
        self.assertEqual(echeances[0].total_paye, Decimal("0"))

    def test_remise(self):
        echeance = self.echeances[0]
        # Remise supérieure au dû refusée.
        self.assertFalse(self.services.ecolage.accorder_remise(
            echeance.id_echeance, Decimal("60000"), "ADMIN").success)
        self.assertTrue(self.services.ecolage.accorder_remise(
            echeance.id_echeance, Decimal("10000"), "ADMIN").success)
        detail = self.services.ecolage.get_echeance_detail(echeance.id_echeance)
        self.assertEqual(detail.net_du, Decimal("40000"))
        self.assertEqual(detail.statut, "DU")
        # 40 000 encaissés → soldé grâce à la remise.
        self.assertTrue(self.services.ecolage.encaisser(
            echeance.id_echeance, Decimal("40000"), "Chèque", None, None,
            "CAISSE").success)
        detail = self.services.ecolage.get_echeance_detail(echeance.id_echeance)
        self.assertEqual(detail.statut, "SOLDE")


class TestPaie(BaseTestCase):

    def test_calcul_paie(self):
        from ltadmin.repositories.staff_repository import StaffRepository
        formateur = Formateur(matricule="FOR-P-0001", nom="PAIE", prenom="Test",
                              actif=True, taux_horaire=Decimal("15000"))
        id_formateur = StaffRepository(self.services.database).insert_formateur(
            formateur)
        # Un programme en classe 1 pour rattacher l'EDT.
        programme = Programme(id_classe=1, code_matiere="FRA",
                              id_formateur=id_formateur, coefficient=1.0)
        id_prog = StaffRepository(self.services.database).insert_programme(
            programme)
        # Créneau + EDT + 2 séances de 2 h et 1 h (semaine du 10/11).
        from ltadmin.models.entities import Creneau, EmploiDuTemps
        planning = self.services.schedule
        creneau = Creneau(libelle="S1", heure_debut="08:00", heure_fin="10:00",
                          ordre_cre=1)
        self.assertTrue(planning.save_creneau(creneau, "ADMIN").success)
        slot = EmploiDuTemps(id_prog=id_prog, id_creneau=creneau.id_creneau,
                             jour="Lundi", actif=True)
        result = planning.create_slot(slot, "ADMIN")
        self.assertTrue(result.success, result.message)
        for date_seance, heures in ((_dt.datetime(2025, 11, 10), 2.0),
                                    (_dt.datetime(2025, 11, 17), 2.0),
                                    (_dt.datetime(2025, 11, 24), 1.0)):
            seance = Seance(id_edt=slot.id_edt, date_seance=date_seance,
                            nb_heures=heures, statut="REALISEE")
            self.assertTrue(planning.save_seance(seance, "ADMIN").success)
        # Calcul : novembre 2025 → 5 h × 15 000 = 75 000.
        result = self.services.payroll.calculer_paie(
            id_formateur, "11/2025", _dt.datetime(2025, 11, 1),
            _dt.datetime(2025, 11, 30), "ADMIN")
        self.assertTrue(result.success, result.message)
        paies = self.services.payroll.list_paies_by_formateur(id_formateur)
        self.assertEqual(len(paies), 1)
        self.assertAlmostEqual(paies[0].nb_heures, 5.0)
        self.assertEqual(paies[0].montant, Decimal("75000"))
        # Doublon de période refusé.
        self.assertFalse(self.services.payroll.calculer_paie(
            id_formateur, "11/2025", _dt.datetime(2025, 11, 1),
            _dt.datetime(2025, 11, 30), "ADMIN").success)
        # Marquer payée, puis suppression refusée.
        self.assertTrue(self.services.payroll.marquer_payee(
            paies[0].id_paie, True, None, "ADMIN").success)
        self.assertFalse(self.services.payroll.delete_paie(
            paies[0].id_paie, "ADMIN").success)

    def test_heures_hors_periode_non_comptees(self):
        """Vérifie la borne fin < fin+1j (début ≤ date < fin+1)."""
        from ltadmin.repositories.planning_repository import PlanningRepository
        from ltadmin.repositories.staff_repository import StaffRepository
        formateur = Formateur(matricule="FOR-Q", nom="QUANT", prenom="Test",
                              taux_horaire=Decimal("1000"))
        id_formateur = StaffRepository(self.services.database).insert_formateur(
            formateur)
        planning = PlanningRepository(self.services.database)
        total = planning.sum_heures_formateur(
            id_formateur, _dt.datetime(2025, 1, 1), _dt.datetime(2025, 12, 31))
        self.assertEqual(total, 0.0)


class TestPlanning(BaseTestCase):

    def test_conflit_salle(self):
        """Deux slots actifs même (jour, créneau) même salle → refus."""
        from ltadmin.models.entities import Creneau, EmploiDuTemps, Formateur, \
            Programme
        from ltadmin.repositories.staff_repository import StaffRepository
        staff = StaffRepository(self.services.database)
        formateur1 = Formateur(matricule="FOR-C1", nom="UN", prenom="Test")
        formateur2 = Formateur(matricule="FOR-C2", nom="DEUX", prenom="Test")
        id_f1 = staff.insert_formateur(formateur1)
        id_f2 = staff.insert_formateur(formateur2)
        prog1 = Programme(id_classe=1, code_matiere="FRA", id_formateur=id_f1,
                          coefficient=1.0)
        prog2 = Programme(id_classe=1, code_matiere="ANG", id_formateur=id_f2,
                          coefficient=1.0)
        id_p1 = staff.insert_programme(prog1)
        id_p2 = staff.insert_programme(prog2)
        salle = self.services.referentiel.list_salles()[0]
        creneau = Creneau(libelle="Matin", heure_debut="08:00",
                          heure_fin="10:00", ordre_cre=1)
        self.assertTrue(self.services.schedule.save_creneau(
            creneau, "ADMIN").success)
        slot1 = EmploiDuTemps(id_prog=id_p1, id_creneau=creneau.id_creneau,
                              jour="Lundi", id_salle=salle.id_salle, actif=True)
        self.assertTrue(self.services.schedule.create_slot(
            slot1, "ADMIN").success)
        slot2 = EmploiDuTemps(id_prog=id_p2, id_creneau=creneau.id_creneau,
                              jour="Lundi", id_salle=salle.id_salle, actif=True)
        result = self.services.schedule.create_slot(slot2, "ADMIN")
        self.assertFalse(result.success)
        self.assertEqual(result.code, "GESTION")
        self.assertIn("salle", result.message.lower())

    def test_conflit_formateur(self):
        """Même formateur sur deux classes au même créneau → refus."""
        from ltadmin.models.entities import Creneau, EmploiDuTemps, Formateur, \
            Programme
        from ltadmin.repositories.staff_repository import StaffRepository
        staff = StaffRepository(self.services.database)
        formateur = Formateur(matricule="FOR-CF", nom="OCCUPE", prenom="Test")
        id_f = staff.insert_formateur(formateur)
        prog1 = Programme(id_classe=1, code_matiere="FRA", id_formateur=id_f,
                          coefficient=1.0)
        prog2 = Programme(id_classe=3, code_matiere="ANG", id_formateur=id_f,
                          coefficient=1.0)
        id_p1 = staff.insert_programme(prog1)
        id_p2 = staff.insert_programme(prog2)
        creneau = Creneau(libelle="AM", heure_debut="08:00", heure_fin="10:00")
        self.assertTrue(self.services.schedule.save_creneau(
            creneau, "ADMIN").success)
        slot1 = EmploiDuTemps(id_prog=id_p1, id_creneau=creneau.id_creneau,
                              jour="Mardi", actif=True)
        self.assertTrue(self.services.schedule.create_slot(
            slot1, "ADMIN").success)
        slot2 = EmploiDuTemps(id_prog=id_p2, id_creneau=creneau.id_creneau,
                              jour="Mardi", actif=True)
        result = self.services.schedule.create_slot(slot2, "ADMIN")
        self.assertFalse(result.success)
        self.assertIn("formateur", result.message.lower())

    def test_salle_indisponible_refusee(self):
        from ltadmin.models.entities import Creneau, EmploiDuTemps, Formateur, \
            Programme
        from ltadmin.repositories.staff_repository import StaffRepository
        staff = StaffRepository(self.services.database)
        formateur = Formateur(matricule="FOR-SD", nom="SALLE", prenom="Test")
        id_f = staff.insert_formateur(formateur)
        id_prog = staff.insert_programme(Programme(
            id_classe=1, code_matiere="FRA", id_formateur=id_f, coefficient=1.0))
        salles = self.services.referentiel.list_salles()
        salles[0].disponible = False
        self.assertTrue(self.services.referentiel.save_salle(
            salles[0], "ADMIN").success)
        creneau = Creneau(libelle="X", heure_debut="08:00", heure_fin="10:00")
        self.assertTrue(self.services.schedule.save_creneau(
            creneau, "ADMIN").success)
        slot = EmploiDuTemps(id_prog=id_prog, id_creneau=creneau.id_creneau,
                             jour="Jeudi", id_salle=salles[0].id_salle,
                             actif=True)
        result = self.services.schedule.create_slot(slot, "ADMIN")
        self.assertFalse(result.success)


if __name__ == "__main__":
    unittest.main()
