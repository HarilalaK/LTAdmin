"""Sécurité : hachage des mots de passe et habilitations côté services."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlite_test_engine import create_test_services  # noqa: E402

from ltadmin.services.auth import password_hashing  # noqa: E402
from ltadmin.services.auth.habilitations import Modules  # noqa: E402


class SecurityTestCase(unittest.TestCase):
    """Chaque test obtient une base fraîche avec les données initiales."""

    @classmethod
    def setUpClass(cls):
        cls._directory = tempfile.mkdtemp(prefix="lta_sec_")

    def setUp(self):
        import uuid
        path = os.path.join(self._directory, f"{uuid.uuid4().hex}.db")
        self.services = create_test_services(path)

    def tearDown(self):
        self.services.close()


class TestHachageMotsDePasse(SecurityTestCase):

    def test_format_pbkdf2(self):
        hache = password_hashing.hash_password("secret")
        self.assertTrue(hache.startswith("pbkdf2_sha256$"))
        self.assertNotIn("secret", hache)

    def test_sels_uniques(self):
        self.assertNotEqual(
            password_hashing.hash_password("secret"),
            password_hashing.hash_password("secret"))

    def test_verify_accepte_clair_historique(self):
        # Valeur en clair de la base fournie (ADMIN/admin).
        self.assertTrue(password_hashing.verify("admin", "admin"))
        self.assertFalse(password_hashing.verify("autre", "admin"))

    def test_verify_accepte_format_hache(self):
        hache = password_hashing.hash_password("secret")
        self.assertTrue(password_hashing.verify("secret", hache))
        self.assertFalse(password_hashing.verify("faux", hache))

    def test_valeur_vide_refusee(self):
        self.assertFalse(password_hashing.verify("x", ""))
        self.assertFalse(password_hashing.verify("", ""))


class TestMigrationTransparente(SecurityTestCase):

    def test_connexion_reussie_migre_le_mot_de_passe(self):
        result = self.services.authentication.authenticate("ADMIN", "admin")
        self.assertTrue(result.success)
        relu = self.services.admin.get_utilisateur("ADMIN")
        self.assertTrue(password_hashing.is_hashed(relu.mot_passe))
        # L'ancien comme le nouveau mot de passe continuent de fonctionner.
        self.assertTrue(self.services.authentication.authenticate(
            "ADMIN", "admin").success)

    def test_comptes_non_connectes_restant_en_clair(self):
        relu = self.services.admin.get_utilisateur("SCOL")
        self.assertFalse(password_hashing.is_hashed(relu.mot_passe))

    def test_change_password_stocke_un_hachage(self):
        result = self.services.authentication.change_password(
            "ADMIN", "admin", "nouveau")
        self.assertTrue(result.success)
        relu = self.services.admin.get_utilisateur("ADMIN")
        self.assertTrue(password_hashing.is_hashed(relu.mot_passe))
        self.assertTrue(self.services.authentication.authenticate(
            "ADMIN", "nouveau").success)


class TestHabilitationsServices(SecurityTestCase):
    """Défense en profondeur : les services refusent les profils non autorisés."""

    def test_scolarite_ne_peut_pas_creer_de_compte(self):
        from ltadmin.models.entities import Utilisateur
        compte = Utilisateur(code_utr="X", nom_utr="X", profil="Scolarité",
                             actif=True)
        result = self.services.admin.save_utilisateur(compte, "1234", "SCOL")
        self.assertFalse(result.success)
        self.assertEqual(result.code, "HABILITATION")

    def test_scolarite_ne_peut_pas_modifier_les_parametres(self):
        result = self.services.parametres.set_value("DEVISE", "EUR", "SCOL")
        self.assertFalse(result.success)
        self.assertEqual(result.code, "HABILITATION")

    def test_caisse_ne_peut_pas_inscrire(self):
        from ltadmin.models.entities import Inscription
        result = self.services.enrollments.inscrire(
            Inscription(id_etudiant=1, id_classe=1, date_inscription=None),
            "CAISSE")
        self.assertFalse(result.success)
        self.assertEqual(result.code, "HABILITATION")

    def test_caisse_ne_peut_pas_generer_de_bulletin(self):
        result = self.services.bulletins.generer(1, 1, "CAISSE")
        self.assertFalse(result.success)
        self.assertEqual(result.code, "HABILITATION")

    def test_enseignant_ne_peut_pas_creer_de_tarif(self):
        from ltadmin.models.entities import Tarif
        result = self.services.ecolage.save_tarif(Tarif(), "ENSEIGNANT")
        self.assertFalse(result.success)
        self.assertEqual(result.code, "HABILITATION")

    def test_admin_passe_partout(self):
        # Lecture de contrôle : l'administrateur n'est jamais bloqué par la garde.
        self.assertTrue(self.services.bulletins.generer(999, 999, "ADMIN").success
                        or self.services.bulletins.generer(999, 999, "ADMIN").is_failure
                        and self.services.bulletins.generer(999, 999, "ADMIN").code
                        != "HABILITATION")

    def test_modules_cibles_des_gardes(self):
        # Le garde s'appuie sur les noms de modules métier.
        self.assertEqual(Modules.ECOLAGE, "Écolage")
        self.assertEqual(Modules.NOTES, "Notes et évaluations")


if __name__ == "__main__":
    unittest.main()
