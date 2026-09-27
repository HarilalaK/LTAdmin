"""API : authentification, tableau de bord, référentiel, étudiants,
inscriptions, formateurs et programmes."""

from __future__ import annotations

import datetime as _dt
import os
from typing import Any, Dict, List

from ltadmin import __version__
from ltadmin.core.result import Result
from ltadmin.models.entities import (AnneeScolaire, Classe, Etudiant, Filiere, Formateur,
                                     Inscription, Matiere, ModuleFormation, Niveau,
                                     Programme, Salle)
from ltadmin.services.auth import habilitations
from ltadmin.services.auth.habilitations import Modules
from ltadmin.web.routing import (PUBLIC, HttpError, Request, Response, Router,
                                 ok_response, result_response)
from ltadmin.web.serialization import parse_entity
from ltadmin.web.sessions import COOKIE_NAME


def _entity(request: Request, cls, base=None):
    try:
        return parse_entity(cls, request.data, base)
    except ValueError as ex:
        raise HttpError(400, "Vérifiez la saisie : " + str(ex), "VALIDATION", [str(ex)])


def _session_payload(request: Request, session) -> Dict[str, Any]:
    services = request.services
    modules = [m for m in habilitations.MENU_ORDER
               if habilitations.can_access(session.role, m)]
    annee = services.admin.get_annee_active()
    etab = services.admin.get_etablissement()
    return {
        "login": session.login,
        "display_name": session.display_name,
        "role": session.role,
        "modules": modules,
        "annee_active": annee,
        "etablissement": etab,
        "parametres": services.parametres.get_all(),
        "version": __version__,
        "database": os.path.basename(services.database.database_path),
    }


def register(router: Router) -> None:

    # ------------------------------------------------------------------
    # Santé / session
    # ------------------------------------------------------------------

    @router.get("/api/sante", module=PUBLIC)
    def sante(request: Request):
        return ok_response({"statut": "ok", "version": __version__,
                            "heure": _dt.datetime.now()})

    @router.post("/api/auth/connexion", module=PUBLIC)
    def connexion(request: Request):
        login = str(request.field("login", required=True)).strip()
        password = str(request.field("mot_de_passe", required=True))
        result = request.services.authentication.authenticate(login, password)
        if not result.success:
            return result_response(result)
        token = request.app.sessions.create(result.value)
        response = ok_response(_session_payload(request, result.value), result.message)
        response.headers["Set-Cookie"] = request.app.session_cookie(token)
        return response

    @router.post("/api/auth/deconnexion", module=PUBLIC)
    def deconnexion(request: Request):
        if request.session is not None:
            request.services.journal.log_operation(
                request.login, "DECONNEXION", "UTILISATEUR", None, "Fermeture de session.")
        request.app.sessions.revoke(request.session_token)
        response = ok_response(None, "Session fermée.")
        response.headers["Set-Cookie"] = request.app.session_cookie("", expire=True)
        return response

    @router.get("/api/auth/session", module=PUBLIC)
    def session(request: Request):
        if request.session is None:
            return Response(body={"ok": False, "code": "AUTHENTIFICATION",
                                  "message": "Aucune session ouverte.", "errors": [],
                                  "value": None}, status=401)
        return ok_response(_session_payload(request, request.session))

    @router.post("/api/auth/mot-de-passe")
    def mot_de_passe(request: Request):
        response = result_response(request.services.authentication.change_password(
            request.login, str(request.field("ancien", default="") or ""),
            str(request.field("nouveau", required=True))))
        if response.status == 401:
            # Ancien mot de passe erroné : erreur de saisie, la session reste valide
            # (401 signifierait « session perdue » pour l'interface).
            response.status = 400
        return response

    # ------------------------------------------------------------------
    # Tableau de bord et statistiques
    # ------------------------------------------------------------------

    @router.get("/api/tableau-de-bord")
    def tableau_de_bord(request: Request):
        stats = request.services.statistics
        annee = request.param_int("annee")
        data = stats.dashboard(annee)
        alertes = [{"matricule": a[0], "nom": a[1], "heures": a[2]}
                   for a in (data.alertes_absences or []) if len(a) >= 3]
        return ok_response({
            "annee_libelle": data.annee_libelle,
            "nb_classes": data.nb_classes,
            "nb_etudiants": data.nb_etudiants,
            "nb_formateurs": data.nb_formateurs,
            "total_encaisse": data.total_encaisse,
            "nb_echeances_echues": data.nb_echeances_echues,
            "montant_echeances_echues": data.montant_echeances_echues,
            "alertes_absences": alertes,
            "seuil_absence": data.seuil_absence,
            "devise": data.devise,
            "effectifs": stats.effectifs_par_classe(annee),
            "repartition_sexe": stats.repartition_sexe(annee),
            "journal_recent": (request.services.journal.consulter(max_rows=8)
                               if habilitations.can_access(request.role, Modules.ADMINISTRATION)
                               else None),
        })

    @router.get("/api/statistiques", module=Modules.STATISTIQUES)
    def statistiques(request: Request):
        stats = request.services.statistics
        annee = request.param_int("annee")
        return ok_response({
            "effectifs": stats.effectifs_par_classe(annee),
            "sexe": stats.repartition_sexe(annee),
            "redoublants": stats.repartition_redoublants(annee),
            "resultats": stats.repartition_resultats(annee),
            "mentions": stats.repartition_mentions(annee),
            "avancement": stats.avancement_saisie(request.param_int("classe"),
                                                  request.param_int("periode")),
            "total_absences": stats.total_absences(annee),
            "encaissements": stats.encaissements_par_mode(request.param_date("debut"),
                                                          request.param_date("fin")),
            "echeances_echues": stats.echeances_echues(annee),
        })

    # ------------------------------------------------------------------
    # Référentiel (lecture ouverte à tous les profils connectés)
    # ------------------------------------------------------------------

    @router.get("/api/ref/tout")
    def ref_tout(request: Request):
        ref = request.services.referentiel
        return ok_response({
            "annees": request.services.admin.list_annees(),
            "filieres": ref.list_filieres(),
            "niveaux": ref.list_niveaux(),
            "salles": ref.list_salles(),
            "classes": ref.list_classes_detail(),
            "modules": ref.list_modules(),
            "matieres": ref.list_matieres(),
            "creneaux": request.services.schedule.list_creneaux(),
            "periodes": request.services.evaluations.list_periodes(),
            "sessions": request.services.exams.list_sessions(),
            "formateurs": request.services.staff.list_formateurs(),
            "mentions": request.services.bulletins.get_grille_mentions(),
        })

    @router.get("/api/ref/filieres")
    def filieres(request: Request):
        return ok_response(request.services.referentiel.list_filieres(
            request.param_bool("actives")))

    @router.post("/api/ref/filieres", module=Modules.REFERENTIEL)
    def save_filiere(request: Request):
        return result_response(request.services.referentiel.save_filiere(
            _entity(request, Filiere), request.login))

    @router.delete("/api/ref/filieres/{code}", module=Modules.REFERENTIEL)
    def delete_filiere(request: Request):
        return result_response(request.services.referentiel.delete_filiere(
            request.path_str("code"), request.login))

    @router.get("/api/ref/niveaux")
    def niveaux(request: Request):
        return ok_response(request.services.referentiel.list_niveaux())

    @router.post("/api/ref/niveaux", module=Modules.REFERENTIEL)
    def save_niveau(request: Request):
        return result_response(request.services.referentiel.save_niveau(
            _entity(request, Niveau), request.login))

    @router.delete("/api/ref/niveaux/{code}", module=Modules.REFERENTIEL)
    def delete_niveau(request: Request):
        return result_response(request.services.referentiel.delete_niveau(
            request.path_str("code"), request.login))

    @router.get("/api/ref/salles")
    def salles(request: Request):
        return ok_response(request.services.referentiel.list_salles(
            request.param_bool("disponibles")))

    @router.post("/api/ref/salles", module=Modules.REFERENTIEL)
    def save_salle(request: Request):
        return result_response(request.services.referentiel.save_salle(
            _entity(request, Salle), request.login))

    @router.delete("/api/ref/salles/{id}", module=Modules.REFERENTIEL)
    def delete_salle(request: Request):
        return result_response(request.services.referentiel.delete_salle(
            request.path_int("id"), request.login))

    @router.get("/api/ref/classes")
    def classes(request: Request):
        return ok_response(request.services.referentiel.list_classes_detail(
            request.param_int("annee")))

    @router.get("/api/ref/classes/{id}")
    def get_classe(request: Request):
        classe = request.services.referentiel.get_classe(request.path_int("id"))
        if classe is None:
            raise HttpError(404, "Classe introuvable.", "INTROUVABLE")
        return ok_response(classe)

    @router.post("/api/ref/classes", module=Modules.REFERENTIEL)
    def save_classe(request: Request):
        return result_response(request.services.referentiel.save_classe(
            _entity(request, Classe), request.login))

    @router.delete("/api/ref/classes/{id}", module=Modules.REFERENTIEL)
    def delete_classe(request: Request):
        return result_response(request.services.referentiel.delete_classe(
            request.path_int("id"), request.login))

    @router.get("/api/ref/modules")
    def modules(request: Request):
        return ok_response(request.services.referentiel.list_modules(
            request.param("filiere")))

    @router.post("/api/ref/modules", module=Modules.REFERENTIEL)
    def save_module(request: Request):
        return result_response(request.services.referentiel.save_module(
            _entity(request, ModuleFormation), request.login))

    @router.delete("/api/ref/modules/{code}", module=Modules.REFERENTIEL)
    def delete_module(request: Request):
        return result_response(request.services.referentiel.delete_module(
            request.path_str("code"), request.login))

    @router.get("/api/ref/matieres")
    def matieres(request: Request):
        return ok_response(request.services.referentiel.list_matieres(
            request.param("module")))

    @router.post("/api/ref/matieres", module=Modules.REFERENTIEL)
    def save_matiere(request: Request):
        return result_response(request.services.referentiel.save_matiere(
            _entity(request, Matiere), request.login))

    @router.delete("/api/ref/matieres/{code}", module=Modules.REFERENTIEL)
    def delete_matiere(request: Request):
        return result_response(request.services.referentiel.delete_matiere(
            request.path_str("code"), request.login))

    @router.get("/api/ref/annees")
    def annees(request: Request):
        return ok_response(request.services.admin.list_annees())

    # ------------------------------------------------------------------
    # Étudiants
    # ------------------------------------------------------------------

    @router.get("/api/etudiants", module=Modules.ETUDIANTS)
    def etudiants(request: Request):
        return ok_response(request.services.students.search(
            request.param("q"), request.param_int("max", 500) or 500))

    @router.get("/api/etudiants/{id}", module=Modules.ETUDIANTS)
    def get_etudiant(request: Request):
        etudiant = request.services.students.get(request.path_int("id"))
        if etudiant is None:
            raise HttpError(404, "Étudiant introuvable.", "INTROUVABLE")
        return ok_response({
            "etudiant": etudiant,
            "inscriptions": request.services.enrollments.list_by_etudiant(etudiant.id_etudiant),
        })

    @router.post("/api/etudiants", module=Modules.ETUDIANTS)
    def create_etudiant(request: Request):
        etudiant = _entity(request, Etudiant)
        etudiant.id_etudiant = None
        return result_response(request.services.students.create(etudiant, request.login))

    @router.put("/api/etudiants/{id}", module=Modules.ETUDIANTS)
    def update_etudiant(request: Request):
        existing = request.services.students.get(request.path_int("id"))
        if existing is None:
            raise HttpError(404, "Étudiant introuvable.", "INTROUVABLE")
        etudiant = _entity(request, Etudiant, existing)
        etudiant.id_etudiant = request.path_int("id")
        return result_response(request.services.students.update(etudiant, request.login))

    @router.delete("/api/etudiants/{id}", module=Modules.ETUDIANTS)
    def delete_etudiant(request: Request):
        return result_response(request.services.students.delete(
            request.path_int("id"), request.login))

    @router.get("/api/etudiants/{id}/inscriptions", module=Modules.ETUDIANTS)
    def inscriptions_etudiant(request: Request):
        return ok_response(request.services.enrollments.list_by_etudiant(
            request.path_int("id")))

    # ------------------------------------------------------------------
    # Inscriptions
    # ------------------------------------------------------------------

    @router.get("/api/inscriptions")
    def inscriptions(request: Request):
        # Lecture partagée : écolage, notes, EDT ont besoin des inscrits d'une classe.
        id_classe = request.param_int("classe")
        id_etudiant = request.param_int("etudiant")
        if id_classe is not None:
            return ok_response(request.services.enrollments.list_by_classe(id_classe))
        if id_etudiant is not None:
            return ok_response(request.services.enrollments.list_by_etudiant(id_etudiant))
        raise HttpError(400, "Précisez une classe ou un étudiant.")

    @router.get("/api/inscriptions/{id}")
    def get_inscription(request: Request):
        detail = request.services.enrollments.get_detail(request.path_int("id"))
        if detail is None:
            raise HttpError(404, "Inscription introuvable.", "INTROUVABLE")
        return ok_response(detail)

    @router.post("/api/inscriptions", module=Modules.INSCRIPTIONS)
    def inscrire(request: Request):
        inscription = _entity(request, Inscription)
        inscription.id_inscription = None
        return result_response(request.services.enrollments.inscrire(inscription, request.login))

    @router.put("/api/inscriptions/{id}", module=Modules.INSCRIPTIONS)
    def update_inscription(request: Request):
        existing = request.services.enrollments.get(request.path_int("id"))
        if existing is None:
            raise HttpError(404, "Inscription introuvable.", "INTROUVABLE")
        inscription = _entity(request, Inscription, existing)
        inscription.id_inscription = request.path_int("id")
        return result_response(request.services.enrollments.update(inscription, request.login))

    @router.post("/api/inscriptions/{id}/sortie", module=Modules.INSCRIPTIONS)
    def sortie(request: Request):
        return result_response(request.services.enrollments.enregistrer_sortie(
            request.path_int("id"), request.field_date("date_sortie") or _dt.datetime.now(),
            request.field("motif_sortie"), request.login))

    @router.delete("/api/inscriptions/{id}", module=Modules.INSCRIPTIONS)
    def delete_inscription(request: Request):
        return result_response(request.services.enrollments.delete(
            request.path_int("id"), request.login))

    # ------------------------------------------------------------------
    # Formateurs et programmes
    # ------------------------------------------------------------------

    @router.get("/api/formateurs")
    def formateurs(request: Request):
        return ok_response(request.services.staff.list_formateurs(
            request.param("q"), request.param_bool("actifs")))

    @router.get("/api/formateurs/{id}", module=Modules.FORMATEURS)
    def get_formateur(request: Request):
        formateur = request.services.staff.get_formateur(request.path_int("id"))
        if formateur is None:
            raise HttpError(404, "Formateur introuvable.", "INTROUVABLE")
        return ok_response({
            "formateur": formateur,
            "programmes": request.services.staff.list_programmes(id_formateur=formateur.id_formateur),
            "paies": request.services.payroll.list_paies_by_formateur(formateur.id_formateur)
            if habilitations.can_access(request.role, Modules.PAIE) else [],
        })

    @router.post("/api/formateurs", module=Modules.FORMATEURS)
    def create_formateur(request: Request):
        formateur = _entity(request, Formateur)
        formateur.id_formateur = None
        return result_response(request.services.staff.create_formateur(formateur, request.login))

    @router.put("/api/formateurs/{id}", module=Modules.FORMATEURS)
    def update_formateur(request: Request):
        existing = request.services.staff.get_formateur(request.path_int("id"))
        if existing is None:
            raise HttpError(404, "Formateur introuvable.", "INTROUVABLE")
        formateur = _entity(request, Formateur, existing)
        formateur.id_formateur = request.path_int("id")
        return result_response(request.services.staff.update_formateur(formateur, request.login))

    @router.delete("/api/formateurs/{id}", module=Modules.FORMATEURS)
    def delete_formateur(request: Request):
        return result_response(request.services.staff.delete_formateur(
            request.path_int("id"), request.login))

    @router.get("/api/programmes")
    def programmes(request: Request):
        return ok_response(request.services.staff.list_programmes(
            request.param_int("classe"), request.param_int("formateur")))

    @router.post("/api/programmes", module=Modules.FORMATEURS)
    def save_programme(request: Request):
        programme = _entity(request, Programme)
        if programme.id_prog:
            existing = request.services.staff.get_programme(programme.id_prog)
            if existing is None:
                raise HttpError(404, "Programme introuvable.", "INTROUVABLE")
            programme = _entity(request, Programme, existing)
        return result_response(request.services.staff.save_programme(programme, request.login))

    @router.delete("/api/programmes/{id}", module=Modules.FORMATEURS)
    def delete_programme(request: Request):
        return result_response(request.services.staff.delete_programme(
            request.path_int("id"), request.login))
