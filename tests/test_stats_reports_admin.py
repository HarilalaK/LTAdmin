"""Tests Statistiques, Rapports/CSV et Administration (users, années, backup)."""

from __future__ import annotations

import datetime as _dt
import os
import sys
import tempfile
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ltadmin.models.entities import (  # noqa: E402
    Etudiant,
    Etablissement,
    Inscription,
    Tarif,
    Utilisateur,
)
from test_base import BaseTestCase  # noqa: E402


class StatsBaseTestCase(BaseTestCase):

    def setUp(self):
        super().setUp()
        # 2 étudiants inscrits en classe 1, écolage 100 000 en 2 tranches,
        # un encaissement de 30 000 espèces.
        self.inscrits = []
        for nom in ("STAT", "ISTI"):
            etudiant = Etudiant(nom=nom, prenom="Test")
            self.assertTrue(self.services.students.create(
                etudiant, "ADMIN").success)
            inscription = Inscription(id_etudiant=etudiant.id_etudiant,
                                      id_classe=1,
                                      date_inscription=_dt.datetime(2025, 10, 5))
            result = self.services.enrollments.inscrire(inscription, "ADMIN")
            self.assertTrue(result.success)
            self.inscrits.append(result.value)
        tarif = Tarif(id_classe=1, type_frais="Écolage",
                      montant=Decimal("100000"), nb_tranches=2)
        self.assertTrue(self.services.ecolage.save_tarif(tarif, "ADMIN").success)
        for id_inscription in self.inscrits:
            self.assertTrue(self.services.ecolage.generer_echeancier(
                id_inscription, tarif.id_tarif, "ADMIN").success)
        echeances = self.services.ecolage.list_echeances(self.inscrits[0])
        self.assertTrue(self.services.ecolage.encaisser(
            echeances[0].id_echeance, Decimal("30000"), "Espèces", None, None,
            "CAISSE").success)
        # Dates déterministes : tout à l'avenir sauf une échéance échue
        # non soldée (pour les relances et le tableau de bord).
        self.services.database.execute(
            "UPDATE [ECHEANCIER] SET [DATE_ECHEANCE] = ?",
            [_dt.datetime(2030, 1, 1)])
        self.services.database.execute(
            "UPDATE [ECHEANCIER] SET [DATE_ECHEANCE] = ? "
            "WHERE [ID_ECHEANCE] = ?",
            [_dt.datetime(2020, 1, 1), echeances[1].id_echeance])


class TestStatistiques(StatsBaseTestCase):

    def test_dashboard(self):
        dashboard = self.services.statistics.dashboard()
        self.assertEqual(dashboard.annee_libelle, "2025-2026")
        self.assertEqual(dashboard.nb_classes, 4)
        self.assertEqual(dashboard.nb_etudiants, 2)
        self.assertEqual(dashboard.total_encaisse, Decimal("30000"))
        self.assertEqual(dashboard.nb_echeances_echues, 1)

    def test_effectifs_par_classe(self):
        rows = self.services.statistics.effectifs_par_classe()
        self.assertEqual(len(rows), 4)
        classe1 = next(r for r in rows if "BTS1 Hotellerie" in r.classe
                       or "BTS1 Hotellerie" == r.classe)
        self.assertEqual(classe1.nb_inscrits, 2)

    def test_repartition_sexe(self):
        rows = self.services.statistics.repartition_sexe()
        total = sum(r.valeur for r in rows)
        self.assertEqual(total, 2)

    def test_encaissements_par_mode(self):
        rows = self.services.statistics.encaissements_par_mode()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].mode_paie, "Espèces")
        self.assertEqual(rows[0].total, Decimal("30000"))
        self.assertEqual(rows[0].nb_paiements, 1)

    def test_echeances_echues(self):
        rows = self.services.statistics.echeances_echues()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].reste, Decimal("50000"))

    def test_avancement_saisie(self):
        rows = self.services.statistics.avancement_saisie()
        self.assertEqual(rows, [])  # aucune évaluation créée


class TestReports(StatsBaseTestCase):

    def test_catalogue_8_etats(self):
        definitions = self.services.reports.list_definitions()
        self.assertEqual(len(definitions), 8)
        titres = {d.title for d in definitions}
        self.assertIn("Liste des étudiants", titres)
        self.assertIn("Situation d'écolage", titres)

    def test_liste_etudiants_par_classe(self):
        colonnes, lignes = self.services.reports.build(
            "liste_etudiants", classe="BTS1 Hotellerie")
        self.assertEqual(len(lignes), 2)
        self.assertIn("MATRICULE", colonnes)

    def test_liste_etudiants_sans_critere(self):
        colonnes, lignes = self.services.reports.build("liste_etudiants")
        self.assertEqual((colonnes, lignes), ([], []))

    def test_situation_ecolage(self):
        colonnes, lignes = self.services.reports.build(
            "situation_ecolage", classe="BTS1 Hotellerie")
        self.assertEqual(len(lignes), 2)
        ligne = next(l for l in lignes if l["MATRICULE"])
        self.assertIn("TOTAL_DU", ligne)
        self.assertEqual(float(ligne["TOTAL_DU"]), 100000.0)
        self.assertEqual(float(ligne["TOTAL_PAYE"]), 30000.0)

    def test_moyennes_par_periode(self):
        colonnes, lignes = self.services.reports.build(
            "moyennes_periode", id_classe=1, id_periode=1)
        self.assertEqual(lignes, [])  # aucune note

    def test_export_csv(self):
        path = os.path.join(tempfile.mkdtemp(), "etat.csv")
        ok, message = self.services.reports.export(
            "liste_etudiants", path, classe="BTS1 Hotellerie")
        self.assertTrue(ok, message)
        with open(path, "rb") as handle:
            contenu = handle.read()
        self.assertTrue(contenu.startswith(b"\xef\xbb\xbf"))  # UTF-8 BOM
        texte = contenu.decode("utf-8-sig")
        lignes = texte.strip().split("\n")
        self.assertEqual(len(lignes), 3)  # en-tête + 2 étudiants
        self.assertIn(";", lignes[0])


class TestAdmin(BaseTestCase):

    def test_utilisateurs_crud(self):
        compte = Utilisateur(code_utr="TEST", nom_utr="Compte test",
                             profil="Scolarité", actif=True)
        result = self.services.admin.save_utilisateur(compte, "secret123",
                                                      "ADMIN")
        self.assertTrue(result.success, result.message)
        relu = self.services.admin.get_utilisateur("TEST")
        self.assertEqual(relu.mot_passe, "secret123")
        # Modification sans changer le mot de passe.
        relu.nom_utr = "Compte modifié"
        result = self.services.admin.save_utilisateur(relu, None, "ADMIN")
        self.assertTrue(result.success)
        self.assertEqual(self.services.admin.get_utilisateur("TEST").mot_passe,
                         "secret123")
        # Profil inconnu refusé.
        relu.profil = "Magicien"
        self.assertFalse(self.services.admin.save_utilisateur(
            relu, None, "ADMIN").success)
        # Suppression de soi-même refusée.
        self.assertFalse(self.services.admin.delete_utilisateur(
            "ADMIN", "ADMIN").success)
        self.assertTrue(self.services.admin.delete_utilisateur("TEST", "ADMIN").success)

    def test_activer_annee(self):
        annees = self.services.admin.list_annees()
        self.assertTrue(any(a.active for a in annees))
        active = self.services.admin.get_annee_active()
        self.assertEqual(active.libelle, "2025-2026")
        # Création d'une nouvelle année active → l'ancienne est désactivée.
        from ltadmin.models.entities import AnneeScolaire
        nouvelle = AnneeScolaire(libelle="2026-2027", active=True)
        result = self.services.admin.save_annee(nouvelle, "ADMIN")
        self.assertTrue(result.success)
        active = self.services.admin.get_annee_active()
        self.assertEqual(active.libelle, "2026-2027")
        actives = [a for a in self.services.admin.list_annees() if a.active]
        self.assertEqual(len(actives), 1)

    def test_etablissement(self):
        etablissement = Etablissement(code_etab="LTA", nom_etab="Lycée Test",
                                      tel="034 00 000")
        self.assertTrue(self.services.admin.save_etablissement(
            etablissement, "ADMIN").success)
        relu = self.services.admin.get_etablissement()
        self.assertEqual(relu.nom_etab, "Lycée Test")

    def test_parametre_modification_et_cache(self):
        self.assertEqual(self.services.parametres.moy_admission, 10.0)
        result = self.services.parametres.set_value("MOY_ADMISSION", "12",
                                                    "ADMIN")
        self.assertTrue(result.success)
        self.assertEqual(self.services.parametres.moy_admission, 12.0)
        # Paramètre inconnu refusé.
        self.assertFalse(self.services.parametres.set_value(
            "INCONNU", "1", "ADMIN").success)

    def test_sauvegarde_et_restauration(self):
        # Créer une donnée à restaurer.
        etudiant = Etudiant(nom="BACKUP", prenom="Test")
        self.assertTrue(self.services.students.create(etudiant, "ADMIN").success)
        resultat_sauvegarde = self.services.backups.create_backup()
        self.assertTrue(resultat_sauvegarde.success, resultat_sauvegarde.message)
        sauvegardes = self.services.backups.list_backups()
        self.assertEqual(len(sauvegardes), 1)
        # Modifier la base, puis restaurer.
        self.services.students.delete(etudiant.id_etudiant, "ADMIN")
        self.assertIsNone(self.services.students.get(etudiant.id_etudiant))
        restauration = self.services.backups.restore_backup(
            sauvegardes[0].file_path)
        self.assertTrue(restauration.success, restauration.message)
        self.services.refresh()
        relu = self.services.students.get(etudiant.id_etudiant)
        self.assertIsNotNone(relu)
        self.assertEqual(relu.nom, "BACKUP")
        # La copie de sécurité « avant restauration » existe.
        toutes = self.services.backups.list_backups(include_safety_copies=True)
        self.assertEqual(len(toutes), 2)

    def test_maintenance_generique_tables(self):
        """CRUD générique via DatabaseRepository (écran Tables)."""
        tables = self.services.tables.get_tables()
        self.assertEqual(len(tables), 33)
        etudiant_table = next(t for t in tables if t.name == "ETUDIANT")
        # Insertion.
        valeurs = {"MATRICULE": "ETU-GEN-1", "NOM": "GENERIQUE",
                   "PRENOM": "Test", "SEXE": "M", "STATUT": "ACTIF"}
        id_etudiant = self.services.tables.insert(etudiant_table, valeurs)
        self.assertGreater(id_etudiant, 0)
        # Lecture + recherche.
        lignes = self.services.tables.load_table(etudiant_table, "GENERIQUE")
        self.assertEqual(len(lignes), 1)
        self.assertEqual(lignes[0]["NOM"], "GENERIQUE")
        # Modification.
        lignes[0]["NOM"] = "MODIFIE"
        self.assertEqual(self.services.tables.update(
            etudiant_table, {"ID_ETUDIANT": id_etudiant, "NOM": "GENERIQUE",
                             "PRENOM": "Test"},
            {"ID_ETUDIANT": id_etudiant, "NOM": "MODIFIE", "PRENOM": "Test"}), 1)
        lignes = self.services.tables.load_table(etudiant_table, "MODIFIE")
        self.assertEqual(len(lignes), 1)
        # Suppression.
        self.assertEqual(self.services.tables.delete(
            etudiant_table, {"ID_ETUDIANT": id_etudiant, "NOM": "MODIFIE",
                             "PRENOM": "Test"}), 1)
        lignes = self.services.tables.load_table(etudiant_table, "MODIFIE")
        self.assertEqual(len(lignes), 0)

    def test_localisateur_base(self):
        from ltadmin.services.infrastructure.database_locator import \
            DatabaseLocator
        locator = DatabaseLocator()
        # Argument CLI prioritaire.
        import shutil as _shutil
        temp_dir = tempfile.mkdtemp()
        base = os.path.join(temp_dir, "LTA_ADM.accdb")
        _shutil.copyfile(self.services.database.database_path, base)
        self.assertEqual(os.path.abspath(locator.locate(base)), base)
        # Priorité à l'existant ; sinon retour par défaut.
        chemin_defaut = locator.locate("/inexistant/machin.accdb")
        self.assertTrue(os.path.isabs(chemin_defaut))


if __name__ == "__main__":
    unittest.main()
