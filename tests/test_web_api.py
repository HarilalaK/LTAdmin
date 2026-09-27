"""Tests de la couche web (API JSON) exécutés en mémoire, sans socket.

``WebApplication.handle`` est appelé directement comme le ferait le serveur
HTTP : mêmes en-têtes, mêmes cookies, mêmes corps JSON. Chaque test dispose
d'une base SQLite fraîche (schéma renforcé + référentiel initial).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlite_test_engine import create_test_services  # noqa: E402

from ltadmin.web import serialization  # noqa: E402
from ltadmin.web.routing import Router, PUBLIC  # noqa: E402
from ltadmin.web.server import WebApplication  # noqa: E402
from ltadmin.web.sessions import COOKIE_NAME, SessionStore  # noqa: E402


class _Reply:
    def __init__(self, response):
        self.status = response.status
        self.headers = dict(response.headers or {})
        self.headers.setdefault("Content-Type", response.content_type)
        self.raw = response.raw
        self.body = serialization.to_jsonable(response.body) if response.raw is None else None

    @property
    def value(self):
        return self.body["value"]

    @property
    def ok(self):
        return bool(self.body and self.body.get("ok"))


class WebTestCase(unittest.TestCase):
    """Application web complète sur une base temporaire."""

    @classmethod
    def setUpClass(cls):
        cls._directory = tempfile.mkdtemp(prefix="lta_web_")

    def setUp(self):
        path = os.path.join(self._directory, f"{uuid.uuid4().hex}.sqlite3")
        self.services = create_test_services(path)
        self.app = WebApplication(self.services)
        self.cookie = None

    def tearDown(self):
        self.services.close()

    # ----- Aides -----

    def call(self, method, path, body=None, cookie="auto", raw_body=None, headers=None):
        hdrs = {"content-type": "application/json"}
        if headers:
            hdrs.update(headers)
        if cookie == "auto":
            cookie = self.cookie
        if cookie:
            hdrs["cookie"] = cookie
        if raw_body is not None:
            payload = raw_body
        else:
            payload = json.dumps(body).encode("utf-8") if body is not None else b""
        return _Reply(self.app.handle(method, path, hdrs, payload))

    def login(self, login="ADMIN", password="admin"):
        reply = self.call("POST", "/api/auth/connexion",
                          {"login": login, "mot_de_passe": password}, cookie=None)
        self.assertEqual(reply.status, 200, reply.body)
        self.cookie = reply.headers["Set-Cookie"].split(";")[0]
        return reply

    def ok(self, method, path, body=None, **kw):
        reply = self.call(method, path, body, **kw)
        self.assertEqual(reply.status, 200, (method, path, reply.body))
        self.assertTrue(reply.ok, (method, path, reply.body))
        return reply


# ---------------------------------------------------------------------------
# Sérialisation et analyse des corps de requête
# ---------------------------------------------------------------------------


class TestSerialization(unittest.TestCase):

    def test_to_jsonable_types(self):
        import datetime as dt
        from decimal import Decimal
        from dataclasses import dataclass

        @dataclass
        class Point:
            x: int
            nom: str

        data = {"d": Decimal("12.50"), "e": Decimal("3"), "j": dt.date(2025, 10, 1),
                "dh": dt.datetime(2025, 10, 1, 8, 30), "p": Point(1, "a"), "t": (1, 2),
                "s": {"z", }, "b": b"ab"}
        out = serialization.to_jsonable(data)
        self.assertEqual(out["d"], 12.5)
        self.assertEqual(out["e"], 3)
        self.assertEqual(out["j"], "2025-10-01")
        self.assertEqual(out["dh"], "2025-10-01T08:30:00")
        self.assertEqual(out["p"], {"x": 1, "nom": "a"})
        self.assertEqual(out["t"], [1, 2])
        json.dumps(out)  # ne doit rien lever

    def test_parse_helpers(self):
        import datetime as dt
        from decimal import Decimal
        self.assertEqual(serialization.parse_datetime("2025-10-01"), dt.datetime(2025, 10, 1))
        self.assertEqual(serialization.parse_datetime("01/10/2025"), dt.datetime(2025, 10, 1))
        self.assertIsNone(serialization.parse_datetime(""))
        self.assertEqual(serialization.parse_decimal("1 500 000,50"), Decimal("1500000.50"))
        self.assertIsNone(serialization.parse_decimal(None))
        self.assertTrue(serialization.parse_bool("oui"))
        self.assertFalse(serialization.parse_bool("0"))
        self.assertEqual(serialization.parse_int("12"), 12)
        with self.assertRaises(ValueError):
            serialization.parse_datetime("hier")

    def test_parse_entity_ignores_unknown_and_reports_field(self):
        from ltadmin.models.entities import Etudiant
        entity = serialization.parse_entity(
            Etudiant, {"nom": "Rabe", "date_naissance": "12/05/2004", "inconnu": 1, "tel": ""})
        self.assertEqual(entity.nom, "Rabe")
        self.assertEqual(entity.date_naissance.year, 2004)
        with self.assertRaises(ValueError) as ctx:
            serialization.parse_entity(Etudiant, {"date_naissance": "n'importe quoi"})
        self.assertIn("date_naissance", str(ctx.exception))


# ---------------------------------------------------------------------------
# Routeur, sessions et sécurité
# ---------------------------------------------------------------------------


class TestRouterAndSessions(unittest.TestCase):

    def test_router_matches_params_and_methods(self):
        router = Router()
        router.add("GET", "/api/x/{id}", lambda r: r, None)
        router.add("POST", "/api/x", lambda r: r, PUBLIC)
        route, params, known = router.match("GET", "/api/x/12")
        self.assertIsNotNone(route)
        self.assertEqual(params, {"id": "12"})
        route, params, known = router.match("DELETE", "/api/x/12")
        self.assertIsNone(route)
        self.assertTrue(known)
        route, params, known = router.match("GET", "/api/y")
        self.assertIsNone(route)
        self.assertFalse(known)
        # Les identifiants encodés sont décodés (codes avec accents/espaces).
        router.add("GET", "/api/tables/{name}", lambda r: r, None)
        route, params, _ = router.match("GET", "/api/tables/BTS1%20H%C3%B4tellerie")
        self.assertEqual(params["name"], "BTS1 Hôtellerie")

    def test_session_store(self):
        from ltadmin.models.db_models import UserSession
        store = SessionStore(idle_seconds=3600)
        token = store.create(UserSession("ADMIN", "Admin", "Administrateur"))
        self.assertEqual(store.get(token).login, "ADMIN")
        self.assertIsNone(store.get("inconnu"))
        self.assertIsNone(store.get(None))
        store.revoke_user("admin")
        self.assertIsNone(store.get(token))
        # Expiration par inactivité.
        court = SessionStore(idle_seconds=0)
        token = court.create(UserSession("SCOL", "Scol", "Scolarité"))
        import time
        time.sleep(0.01)
        self.assertIsNone(court.get(token))


class TestSecurity(WebTestCase):

    def test_unauthenticated_requests_are_rejected(self):
        reply = self.call("GET", "/api/etudiants", cookie=None)
        self.assertEqual(reply.status, 401)
        self.assertEqual(reply.body["code"], "AUTHENTIFICATION")
        # /api/sante est public.
        self.assertEqual(self.call("GET", "/api/sante", cookie=None).status, 200)

    def test_login_failure_and_success(self):
        reply = self.call("POST", "/api/auth/connexion",
                          {"login": "ADMIN", "mot_de_passe": "faux"}, cookie=None)
        self.assertEqual(reply.status, 401)
        self.assertNotIn("Set-Cookie", reply.headers)
        reply = self.login()
        self.assertIn(COOKIE_NAME + "=", reply.headers["Set-Cookie"])
        self.assertIn("HttpOnly", reply.headers["Set-Cookie"])
        self.assertEqual(reply.value["role"], "Administrateur")
        self.assertEqual(reply.value["login"], "ADMIN")
        self.assertIn("Administration", reply.value["modules"])
        # Le mot de passe ne circule jamais dans les réponses.
        self.assertNotIn("mot_de_passe", json.dumps(reply.body).lower())

    def test_profile_restrictions(self):
        self.login("CAISSE", "caisse")
        self.assertEqual(self.call("GET", "/api/ecolage/situation?classe=1").status, 200)
        reply = self.call("GET", "/api/etudiants")
        self.assertEqual(reply.status, 403)
        self.assertEqual(reply.body["code"], "HABILITATION")
        self.assertEqual(self.call("GET", "/api/utilisateurs").status, 403)
        self.login("SCOL", "scol")
        self.assertEqual(self.call("GET", "/api/etudiants").status, 200)
        self.assertEqual(self.call("GET", "/api/tarifs").status, 403)
        self.assertEqual(self.call("GET", "/api/paie").status, 403)

    def test_unknown_route_bad_method_bad_json(self):
        self.login()
        self.assertEqual(self.call("GET", "/api/inexistant").status, 404)
        self.assertEqual(self.call("DELETE", "/api/tableau-de-bord").status, 405)
        reply = self.call("POST", "/api/etudiants", raw_body=b"{pas du json")
        self.assertEqual(reply.status, 400)
        self.assertEqual(reply.body["code"], "VALIDATION")

    def test_logout_invalidates_session(self):
        self.login()
        reply = self.ok("POST", "/api/auth/deconnexion")
        self.assertIn("Max-Age=0", reply.headers["Set-Cookie"])
        self.assertEqual(self.call("GET", "/api/auth/session").status, 401)

    def test_deactivating_user_revokes_session(self):
        self.login()
        self.ok("POST", "/api/utilisateurs", {"code_utr": "prof1", "nom_utr": "Prof",
                                              "profil": "Enseignant", "mot_de_passe": "prof",
                                              "actif": True})
        admin_cookie = self.cookie
        self.login("prof1", "prof")
        prof_cookie = self.cookie
        self.assertEqual(self.call("GET", "/api/tableau-de-bord", cookie=prof_cookie).status, 200)
        self.assertEqual(self.call("GET", "/api/etudiants", cookie=prof_cookie).status, 403)
        self.ok("POST", "/api/utilisateurs/prof1/actif", {"actif": False}, cookie=admin_cookie)
        self.assertEqual(self.call("GET", "/api/tableau-de-bord", cookie=prof_cookie).status, 401)
        reply = self.call("POST", "/api/auth/connexion",
                          {"login": "prof1", "mot_de_passe": "prof"}, cookie=None)
        self.assertEqual(reply.status, 401)

    def test_static_files_and_spa_fallback(self):
        content, ctype = self.app.static_file("/")
        self.assertIn(b"<html", content.lower())
        self.assertTrue(ctype.startswith("text/html"))
        content, ctype = self.app.static_file("/views/tableau.js")
        self.assertTrue(ctype.startswith("application/javascript") or ctype.startswith("text/javascript"))
        self.assertIsNone(self.app.static_file("/../main.py"))
        self.assertIsNone(self.app.static_file("/inexistant.js"))


# ---------------------------------------------------------------------------
# Scénario fonctionnel complet à travers l'API
# ---------------------------------------------------------------------------


class TestApiScenario(WebTestCase):

    def setUp(self):
        super().setUp()
        self.login()

    def _inscrire(self, nom="RABE", prenom="Ando", classe=1):
        reply = self.ok("POST", "/api/etudiants", {"nom": nom, "prenom": prenom, "sexe": "M",
                                                   "date_naissance": "2004-05-12"})
        id_etudiant = reply.value
        reply = self.ok("POST", "/api/inscriptions", {"id_etudiant": id_etudiant, "id_classe": classe,
                                                      "date_inscription": "2025-10-01"})
        return id_etudiant, reply.value

    def _programme(self):
        self.ok("POST", "/api/formateurs", {"nom": "RAKOTO", "prenom": "Jean", "taux_horaire": "15 000",
                                            "specialite": "Cuisine", "actif": True})
        reply = self.ok("POST", "/api/programmes", {"id_classe": 1, "code_matiere": "CUI", "id_formateur": 1,
                                                    "coefficient": "3", "vol_horaire": 60})
        return reply.value

    def test_referentiel_and_dashboard(self):
        ref = self.ok("GET", "/api/ref/tout").value
        for key in ("classes", "filieres", "niveaux", "matieres", "modules", "salles",
                    "annees", "periodes", "creneaux", "sessions", "formateurs", "mentions"):
            self.assertIn(key, ref)
        self.assertEqual(len(ref["classes"]), 4)
        dash = self.ok("GET", "/api/tableau-de-bord").value
        self.assertEqual(dash["nb_etudiants"], 0)
        self.assertEqual(dash["annee_libelle"], "2025-2026")
        self.assertEqual(len(dash["effectifs"]), 4)
        self.assertIsInstance(dash["journal_recent"], list)  # administrateur
        self.login("SCOL", "scol")
        self.assertIsNone(self.ok("GET", "/api/tableau-de-bord").value["journal_recent"])

    def test_students_inscriptions_and_validation(self):
        reply = self.call("POST", "/api/etudiants", {"nom": "", "prenom": "X"})
        self.assertEqual(reply.status, 400)
        self.assertTrue(reply.body["errors"] or reply.body["message"])
        id_etudiant, id_inscription = self._inscrire()
        rows = self.ok("GET", "/api/etudiants?q=rabe").value
        self.assertEqual(rows[0]["matricule"][:4], "ETU-")
        self.assertEqual(rows[0]["nom_complet"], "RABE Ando")
        fiche = self.ok("GET", f"/api/etudiants/{id_etudiant}").value
        self.assertEqual(len(fiche["inscriptions"]), 1)
        self.ok("PUT", f"/api/etudiants/{id_etudiant}", {"adresse": "Ankadifotsy", "date_naissance": "12/05/2004"})
        # Double inscription dans la même classe refusée.
        reply = self.call("POST", "/api/inscriptions", {"id_etudiant": id_etudiant, "id_classe": 1})
        self.assertEqual(reply.status, 409, reply.body)
        self.assertEqual(reply.body["code"], "DOUBLON")
        # Suppression impossible tant qu'une inscription existe.
        reply = self.call("DELETE", f"/api/etudiants/{id_etudiant}")
        self.assertNotEqual(reply.status, 200)
        sortie = self.ok("POST", f"/api/inscriptions/{id_inscription}/sortie",
                         {"date_sortie": "2026-01-15", "motif": "Déménagement"})
        self.assertTrue(sortie.ok)
        rows = self.ok("GET", "/api/inscriptions?classe=1&statut=tous").value
        self.assertEqual(rows[0]["statut"], "SORTI")

    def test_notes_bulletins_and_exams(self):
        _, id_inscription = self._inscrire()
        _, id_inscription2 = self._inscrire("RAZAFY", "Hery")
        id_prog = self._programme()
        reply = self.ok("POST", "/api/evaluations", {"id_periode": 1, "id_prog": id_prog, "intitule": "Devoir 1",
                                                     "nature": "DEVOIR", "date_eval": "2025-11-10", "bareme": 20,
                                                     "poids": 1})
        id_eval = reply.value
        grille = self.ok("GET", f"/api/evaluations/{id_eval}").value
        self.assertEqual(len(grille["notes"]), 2)
        # Note au-dessus du barème : refusée ligne à ligne (saisie partielle possible).
        reply = self.ok("POST", f"/api/evaluations/{id_eval}/notes",
                        {"notes": [{"id_inscription": id_inscription, "valeur_note": "25"}]})
        self.assertEqual(reply.value["enregistrees"], 0)
        self.assertEqual(len(reply.value["erreurs"]), 1)
        self.ok("POST", f"/api/evaluations/{id_eval}/notes",
                {"notes": [{"id_inscription": id_inscription, "valeur_note": "14,5"},
                           {"id_inscription": id_inscription2, "valeur_note": "9"}]})
        moyennes = self.ok("GET", "/api/moyennes?classe=1&periode=1").value
        self.assertEqual(len(moyennes["periodes"]), 2)
        gen = self.ok("POST", "/api/bulletins/generer", {"id_classe": 1, "id_periode": 1})
        self.assertIn("2 bulletin", gen.body["message"])
        bulletins = self.ok("GET", "/api/bulletins?classe=1&periode=1").value
        self.assertEqual([b["rang"] for b in bulletins], [1, 2])
        detail = self.ok("GET", f"/api/bulletins/{bulletins[0]['id_bulletin']}").value
        self.assertEqual(detail["lignes"][0]["code_matiere"], "CUI")
        self.assertEqual(float(detail["resume"]["moyenne"]), 14.5)
        # Examens : session, épreuve, notes, résultats (CC 40 % / examen 60 %).
        id_session = self.ok("POST", "/api/sessions", {"libelle": "Session 1", "date_debut": "2026-01-10",
                                                       "date_fin": "2026-01-20"}).value
        id_epreuve = self.ok("POST", "/api/epreuves", {"id_session": id_session, "id_classe": 1,
                                                       "code_matiere": "CUI", "date_epreuve": "2026-01-12",
                                                       "heure_debut": "08:00", "duree_min": 120,
                                                       "bareme": 20}).value
        self.ok("POST", f"/api/epreuves/{id_epreuve}/notes",
                {"notes": [{"id_inscription": id_inscription, "valeur_note": "12"},
                           {"id_inscription": id_inscription2, "valeur_note": "8"}]})
        self.ok("POST", "/api/resultats/generer", {"id_session": id_session, "id_classe": 1})
        resultats = self.ok("GET", f"/api/resultats?session={id_session}&classe=1").value
        self.assertEqual(len(resultats), 2)
        premier = resultats[0]["resultat"]
        self.assertAlmostEqual(float(premier["moyenne_gen"]), 14.5 * 0.4 + 12 * 0.6, places=2)
        self.assertEqual(premier["decision"], "ADMIS")
        self.assertEqual(premier["mention"], "Assez Bien")
        self.assertEqual(resultats[1]["resultat"]["decision"], "AJOURNE")

    def test_ecolage_flow(self):
        _, id_inscription = self._inscrire()
        id_tarif = self.ok("POST", "/api/tarifs", {"id_classe": 1, "type_frais": "ECOLAGE", "montant": "900 000",
                                                   "nb_tranches": 3, "obligatoire": True}).value
        self.ok("POST", "/api/echeanciers/generer", {"id_inscription": id_inscription, "id_tarif": id_tarif})
        dossier = self.ok("GET", f"/api/inscriptions/{id_inscription}/echeances").value
        self.assertEqual(len(dossier["echeances"]), 3)
        self.assertEqual(float(dossier["total_du"]), 900000)
        first = dossier["echeances"][0]
        reply = self.call("POST", f"/api/echeances/{first['id_echeance']}/encaisser",
                          {"montant": "500000", "mode_paie": "ESPECES"})
        self.assertEqual(reply.status, 400, reply.body)  # dépasse le reste dû
        enc = self.ok("POST", f"/api/echeances/{first['id_echeance']}/encaisser",
                      {"montant": "150000", "mode_paie": "ESPECES"}).value
        self.assertTrue(enc["num_recu"].startswith("REC-"))
        self.assertEqual(enc["nouveau_statut"], "PARTIEL")
        recu = self.ok("GET", f"/api/paiements/{enc['id_paiement']}").value
        self.assertEqual(recu["paiement"]["num_recu"], enc["num_recu"])
        self.assertEqual(recu["devise"], "MGA")
        self.ok("POST", f"/api/echeances/{first['id_echeance']}/remise", {"remise": "150000"})
        dossier = self.ok("GET", f"/api/inscriptions/{id_inscription}/echeances").value
        self.assertEqual(dossier["echeances"][0]["statut"], "SOLDE")
        situation = self.ok("GET", "/api/ecolage/situation?classe=1").value
        self.assertEqual(len(situation), 1)
        self.assertEqual(float(situation[0]["total_paye"]), 150000)
        # Suppression de l'échéancier refusée quand un paiement existe.
        reply = self.call("POST", "/api/echeanciers/supprimer", {"id_inscription": id_inscription,
                                                                 "type_frais": "ECOLAGE"})
        self.assertNotEqual(reply.status, 200)

    def test_edt_seances_absences_and_paie(self):
        _, id_inscription = self._inscrire()
        id_prog = self._programme()
        id_edt = self.ok("POST", "/api/edt", {"id_prog": id_prog, "id_creneau": 1, "jour": "LUNDI",
                                              "id_salle": 1, "date_debut": "2025-10-01"}).value
        conflit = self.call("POST", "/api/edt", {"id_prog": id_prog, "id_creneau": 1, "jour": "LUNDI",
                                                 "id_salle": 1, "date_debut": "2025-10-01"})
        self.assertEqual(conflit.status, 409, conflit.body)
        self.assertIn("conflit", conflit.body["message"].lower() + " ".join(conflit.body["errors"]).lower())
        edt = self.ok("GET", "/api/edt?classe=1").value
        self.assertEqual(edt[0]["salle"], "Salle A1")
        self.ok("POST", "/api/seances", {"id_edt": id_edt, "date_seance": "2025-10-06",
                                         "contenu": "Introduction", "nb_heures": 2, "statut": "FAITE"})
        seances = self.ok("GET", f"/api/seances?edt={id_edt}").value
        self.assertEqual(len(seances), 1)
        id_seance = seances[0]["id_seance"]
        self.ok("POST", "/api/absences", {"id_seance": id_seance, "id_inscription": id_inscription,
                                          "nature": "ABSENCE", "nb_heures": 2, "justifiee": False})
        synthese = self.ok("GET", "/api/absences/synthese").value
        self.assertEqual(float(synthese[0]["TOTAL_HEURES"]), 2)
        heures = self.ok("GET", "/api/paie/heures?formateur=1&debut=2025-10-01&fin=2025-10-31").value
        self.assertEqual(float(heures["heures"]), 2)
        paie = self.ok("POST", "/api/paie/calculer", {"id_formateur": 1, "periode": "2025-10",
                                                      "debut": "2025-10-01", "fin": "2025-10-31"})
        self.assertIn("30000", paie.body["message"].replace(" ", ""))
        rows = self.ok("GET", "/api/paie?periode=2025-10").value
        self.assertEqual(float(rows[0]["paie"]["montant"]), 30000)
        self.ok("POST", f"/api/paie/{rows[0]['paie']['id_paie']}/payer", {"date_paie": "2025-11-05"})
        rows = self.ok("GET", "/api/paie?periode=2025-10").value
        self.assertTrue(rows[0]["paie"]["paye"])

    def test_reports_csv_statistics(self):
        self._inscrire()
        defs = self.ok("GET", "/api/rapports").value
        self.assertEqual(len(defs), 8)
        keys = {d["key"] for d in defs}
        self.assertIn("liste_etudiants", keys)
        report = self.ok("GET", "/api/rapports/liste_etudiants?classe=BTS1%20Hotellerie").value
        self.assertEqual(report["count"], 1)
        reply = self.call("GET", "/api/rapports/liste_etudiants/csv?classe=BTS1%20Hotellerie")
        self.assertEqual(reply.status, 200)
        self.assertIn("text/csv", reply.headers.get("Content-Type", ""))
        self.assertIn("attachment", reply.headers.get("Content-Disposition", ""))
        self.assertTrue(reply.raw.startswith(b"\xef\xbb\xbf"))  # BOM UTF-8 pour Excel
        self.assertIn(b";", reply.raw)
        stats = self.ok("GET", "/api/statistiques").value
        for key in ("effectifs", "sexe", "resultats", "encaissements"):
            self.assertIn(key, stats)

    def test_administration_endpoints(self):
        info = self.ok("GET", "/api/admin/info").value
        self.assertEqual(info["nb_tables"], 33)
        params = self.ok("GET", "/api/admin/parametres").value
        self.assertEqual({p["cle"] for p in params} >= {"POIDS_CC", "POIDS_EXAMEN", "DEVISE"}, True)
        self.ok("PUT", "/api/admin/parametres/SEUIL_ABSENCE", {"valeur": "25"})
        reply = self.call("PUT", "/api/admin/parametres/POIDS_CC", {"valeur": "abc"})
        self.assertEqual(reply.status, 400, reply.body)
        etab = self.ok("GET", "/api/admin/etablissement").value
        self.assertTrue(etab["nom_etab"])
        self.ok("PUT", "/api/admin/etablissement", dict(etab, tel="034 00 000 00"))
        id_annee = self.ok("POST", "/api/admin/annees", {"libelle": "2026-2027", "date_debut": "2026-10-01",
                                                          "date_fin": "2027-07-31"}).value
        self.ok("POST", f"/api/admin/annees/{id_annee}/activer")
        annees = self.ok("GET", "/api/ref/annees").value
        self.assertEqual([a["libelle"] for a in annees if a["active"]], ["2026-2027"])
        journal = self.ok("GET", "/api/admin/journal?max=5").value
        self.assertTrue(journal)
        # Sauvegardes : création, liste, purge.
        self.ok("POST", "/api/admin/sauvegardes")
        liste = self.ok("GET", "/api/admin/sauvegardes").value["sauvegardes"]
        self.assertGreaterEqual(len(liste), 1)
        self.ok("POST", "/api/admin/sauvegardes/purger", {"conserver": 0})
        # Maintenance générique : lecture d'une table, garde-fou UTILISATEUR.
        table = self.ok("GET", "/api/tables/SALLE").value
        self.assertEqual(len(table["rows"]), 5)
        users = self.ok("GET", "/api/tables/UTILISATEUR").value
        self.assertTrue(all(row["MOT_PASSE"] == "••••••" for row in users["rows"]))  # jamais en clair
        reply = self.call("POST", "/api/tables/UTILISATEUR", {"values": {"CODE_UTR": "X"}})
        self.assertNotEqual(reply.status, 200)
        # Comptes : création, mot de passe trop court refusé, changement de mot de passe.
        reply = self.call("POST", "/api/utilisateurs", {"code_utr": "dir", "nom_utr": "Direction",
                                                        "profil": "Direction", "mot_de_passe": "ab"})
        self.assertEqual(reply.status, 400, reply.body)
        self.ok("POST", "/api/utilisateurs", {"code_utr": "dir", "nom_utr": "Direction",
                                              "profil": "Direction", "mot_de_passe": "dir1234", "actif": True})
        self.login("dir", "dir1234")
        self.assertEqual(self.call("GET", "/api/admin/info").status, 403)
        reply = self.call("POST", "/api/auth/mot-de-passe", {"ancien": "faux", "nouveau": "dir9999"})
        self.assertEqual(reply.status, 400, reply.body)
        self.ok("POST", "/api/auth/mot-de-passe", {"ancien": "dir1234", "nouveau": "dir9999"})
        self.login("dir", "dir9999")


if __name__ == "__main__":
    unittest.main()
