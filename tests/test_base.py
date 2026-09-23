"""Tests de socle : moteur SQLite, catalogue, authentification, habilitations."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlite_test_engine import create_test_services  # noqa: E402


class BaseTestCase(unittest.TestCase):
    """Chaque test obtient une base fraîche avec les données initiales."""

    @classmethod
    def setUpClass(cls):
        cls._directory = tempfile.mkdtemp(prefix="lta_test_")

    def setUp(self):
        import uuid
        path = os.path.join(self._directory, f"{uuid.uuid4().hex}.db")
        self.services = create_test_services(path)

    def tearDown(self):
        self.services.close()


class TestInfrastructure(BaseTestCase):

    def test_33_tables_presentes(self):
        tables = self.services.database.get_tables()
        self.assertEqual(len(tables), 33)
        names = {table.name for table in tables}
        for attendu in ("ETUDIANT", "INSCRIPTION", "BULLETIN", "ECHEANCIER",
                        "PAIEMENT", "PAIE_FORMATEUR", "GRILLE_MENTION",
                        "RESULTAT_FINAL"):
            self.assertIn(attendu, names)

    def test_vues_requetes_enregistrees(self):
        rows = self.services.database.query("SELECT * FROM [R_PAIEMENT_ECHEANCE]")
        self.assertEqual(rows, [])  # base initiale : aucun paiement
        rows = self.services.database.query(
            "SELECT * FROM [R_MOYENNE_MATIERE]")
        self.assertEqual(rows, [])

    def test_parametres_defauts(self):
        self.assertEqual(self.services.parametres.bareme_defaut, 20.0)
        self.assertEqual(self.services.parametres.moy_admission, 10.0)
        self.assertEqual(self.services.parametres.note_eliminatoire, 5.0)
        self.assertEqual(self.services.parametres.poids_cc, 40.0)
        self.assertEqual(self.services.parametres.poids_examen, 60.0)
        self.assertEqual(self.services.parametres.seuil_absence, 30.0)
        self.assertEqual(self.services.parametres.devise, "MGA")

    def test_parametre_inconnu_valeur_defaut(self):
        self.assertEqual(self.services.parametres.get_string("INCONNU", "X"), "X")

    def test_authentification_reussie_insensible_casse(self):
        for login in ("ADMIN", "admin", "Admin"):
            result = self.services.authentication.authenticate(login, "admin")
            self.assertTrue(result.success, login)
            self.assertEqual(result.value.login, "ADMIN")
            self.assertEqual(result.value.role, "Administrateur")

    def test_authentification_refusee(self):
        result = self.services.authentication.authenticate("ADMIN", "faux")
        self.assertFalse(result.success)
        self.assertEqual(result.code, "AUTHENTIFICATION")
        result = self.services.authentication.authenticate("INCONNU", "admin")
        self.assertFalse(result.success)

    def test_changement_mot_de_passe(self):
        result = self.services.authentication.change_password("ADMIN", "admin", "nouveau")
        self.assertTrue(result.success)
        self.assertTrue(self.services.authentication.authenticate(
            "ADMIN", "nouveau").success)
        # ancien mot de passe refusé
        self.assertFalse(self.services.authentication.authenticate(
            "ADMIN", "admin").success)

    def test_journal_connexion(self):
        self.services.authentication.authenticate("ADMIN", "admin")
        self.services.authentication.authenticate("ADMIN", "faux")
        entries = self.services.journal.consulter(code_utr="ADMIN")
        actions = [entry.action_log for entry in entries]
        self.assertIn("CONNEXION", actions)
        self.assertIn("CONNEXION_REFUSEE", actions)

    def test_transaction_rollback(self):
        database = self.services.database
        database.execute("DELETE FROM [ETUDIANT]")
        try:
            with database.begin_transaction():
                database.execute(
                    "INSERT INTO [ETUDIANT] ([MATRICULE], [NOM], [PRENOM]) "
                    "VALUES (?, ?, ?)", ["ETU-X", "Test", "Rollback"])
                raise RuntimeError("annulation volontaire")
        except RuntimeError:
            pass
        count = database.scalar("SELECT COUNT(*) FROM [ETUDIANT]")
        self.assertEqual(int(count), 0)

    def test_transaction_commit(self):
        database = self.services.database
        with database.begin_transaction():
            database.execute(
                "INSERT INTO [ETUDIANT] ([MATRICULE], [NOM], [PRENOM]) "
                "VALUES (?, ?, ?)", ["ETU-Y", "Test", "Commit"])
        count = database.scalar("SELECT COUNT(*) FROM [ETUDIANT]")
        self.assertEqual(int(count), 1)


class TestHabilitations(unittest.TestCase):

    def test_admin_tout(self):
        from ltadmin.services.auth import habilitations
        from ltadmin.services.auth.habilitations import Modules
        for module in habilitations.MENU_ORDER:
            if module in (Modules.UTILISATEURS, Modules.TABLES):
                continue
            self.assertTrue(habilitations.can_access("Administrateur", module),
                            module)

    def test_direction_pas_administration(self):
        from ltadmin.services.auth import habilitations
        from ltadmin.services.auth.habilitations import Modules
        self.assertTrue(habilitations.can_access("Direction", Modules.ECOLAGE))
        self.assertTrue(habilitations.can_access("Direction", Modules.PAIE))
        self.assertFalse(habilitations.can_access("Direction",
                                                  Modules.ADMINISTRATION))
        self.assertFalse(habilitations.can_access("Direction", Modules.TABLES))

    def test_scolarite_pas_ecolage(self):
        from ltadmin.services.auth import habilitations
        from ltadmin.services.auth.habilitations import Modules
        self.assertTrue(habilitations.can_access("Scolarité", Modules.NOTES))
        self.assertFalse(habilitations.can_access("Scolarité", Modules.ECOLAGE))
        self.assertFalse(habilitations.can_access("Scolarité", Modules.PAIE))

    def test_comptabilite_ecolage_paie_stats(self):
        from ltadmin.services.auth import habilitations
        from ltadmin.services.auth.habilitations import Modules
        self.assertTrue(habilitations.can_access("Comptabilité", Modules.ECOLAGE))
        self.assertTrue(habilitations.can_access("Comptabilité", Modules.PAIE))
        self.assertTrue(habilitations.can_access("Comptabilité",
                                                 Modules.STATISTIQUES))
        self.assertFalse(habilitations.can_access("Comptabilité", Modules.NOTES))

    def test_enseignant_limité(self):
        from ltadmin.services.auth import habilitations
        from ltadmin.services.auth.habilitations import Modules
        self.assertTrue(habilitations.can_access("Enseignant", Modules.NOTES))
        self.assertTrue(habilitations.can_access("Enseignant", Modules.ABSENCES))
        self.assertFalse(habilitations.can_access("Enseignant", Modules.ETUDIANTS))
        self.assertFalse(habilitations.can_access("Enseignant", Modules.ECOLAGE))

    def test_profil_inconnu_tableau_de_bord(self):
        from ltadmin.services.auth import habilitations
        from ltadmin.services.auth.habilitations import Modules
        self.assertTrue(habilitations.can_access("Vacataire",
                                                 Modules.TABLEAU_DE_BORD))
        self.assertFalse(habilitations.can_access("Vacataire", Modules.NOTES))

    def test_profils_base_normalises(self):
        from ltadmin.services.auth.habilitations import normalize_profil
        self.assertEqual(normalize_profil("ADMIN"), "Administrateur")
        self.assertEqual(normalize_profil("SCOLARITE"), "Scolarité")
        self.assertEqual(normalize_profil("FINANCE"), "Comptabilité")


if __name__ == "__main__":
    unittest.main()
