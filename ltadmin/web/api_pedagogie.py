"""API : périodes, évaluations, notes, bulletins, sessions d'examen,
épreuves, notes d'examen, résultats finaux, emploi du temps, séances et
absences."""

from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List

from ltadmin.models.entities import (Absence, Bulletin, Creneau, EmploiDuTemps, Epreuve,
                                     Evaluation, PeriodeEval, Seance, SessionExam)
from ltadmin.services.auth.habilitations import Modules
from ltadmin.web.routing import HttpError, Request, Router, ok_response, result_response
from ltadmin.web.serialization import parse_entity, parse_float


def _entity(request: Request, cls, base=None):
    try:
        return parse_entity(cls, request.data, base)
    except ValueError as ex:
        raise HttpError(400, "Vérifiez la saisie : " + str(ex), "VALIDATION", [str(ex)])


def _note_value(request: Request):
    raw = request.field("valeur_note")
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    try:
        return parse_float(raw)
    except (ValueError, TypeError):
        raise HttpError(400, "Note : nombre attendu (ex. 12,5).")


def register(router: Router) -> None:

    # ------------------------------------------------------------------
    # Périodes d'évaluation
    # ------------------------------------------------------------------

    @router.get("/api/periodes")
    def periodes(request: Request):
        return ok_response(request.services.evaluations.list_periodes(request.param_int("annee")))

    @router.post("/api/periodes", module=Modules.NOTES)
    def save_periode(request: Request):
        periode = _entity(request, PeriodeEval)
        if periode.id_periode:
            existing = request.services.evaluations.get_periode(periode.id_periode)
            if existing is None:
                raise HttpError(404, "Période introuvable.", "INTROUVABLE")
            periode = _entity(request, PeriodeEval, existing)
            return result_response(request.services.evaluations.update_periode(periode, request.login))
        return result_response(request.services.evaluations.create_periode(periode, request.login))

    @router.post("/api/periodes/{id}/cloture", module=Modules.NOTES)
    def cloture_periode(request: Request):
        return result_response(request.services.evaluations.set_periode_cloturee(
            request.path_int("id"), request.field_bool("cloturee", True), request.login))

    # ------------------------------------------------------------------
    # Évaluations et notes
    # ------------------------------------------------------------------

    @router.get("/api/evaluations", module=Modules.NOTES)
    def evaluations(request: Request):
        return ok_response(request.services.evaluations.list_evaluations(
            request.param_int("periode"), request.param_int("classe"), request.param_int("programme")))

    @router.get("/api/evaluations/{id}", module=Modules.NOTES)
    def get_evaluation(request: Request):
        detail = request.services.evaluations.get_evaluation_detail(request.path_int("id"))
        if detail is None:
            raise HttpError(404, "Évaluation introuvable.", "INTROUVABLE")
        return ok_response({
            "evaluation": detail,
            "notes": request.services.grades.get_grille_saisie(detail.id_evaluation),
        })

    @router.post("/api/evaluations", module=Modules.NOTES)
    def save_evaluation(request: Request):
        evaluation = _entity(request, Evaluation)
        if evaluation.id_evaluation:
            detail = request.services.evaluations.get_evaluation_detail(evaluation.id_evaluation)
            if detail is None:
                raise HttpError(404, "Évaluation introuvable.", "INTROUVABLE")
            base = Evaluation(id_evaluation=detail.id_evaluation, id_periode=detail.id_periode,
                              id_prog=detail.id_prog, intitule=detail.intitule,
                              nature=detail.nature, date_eval=detail.date_eval,
                              bareme=detail.bareme, poids=detail.poids, publiee=detail.publiee)
            evaluation = _entity(request, Evaluation, base)
            return result_response(request.services.evaluations.update_evaluation(
                evaluation, request.login))
        return result_response(request.services.evaluations.create_evaluation(
            evaluation, request.login))

    @router.post("/api/evaluations/{id}/publication", module=Modules.NOTES)
    def publication(request: Request):
        return result_response(request.services.evaluations.set_publiee(
            request.path_int("id"), request.field_bool("publiee", True), request.login))

    @router.delete("/api/evaluations/{id}", module=Modules.NOTES)
    def delete_evaluation(request: Request):
        return result_response(request.services.evaluations.delete_evaluation(
            request.path_int("id"), request.login))

    @router.get("/api/evaluations/{id}/notes", module=Modules.NOTES)
    def notes(request: Request):
        return ok_response(request.services.grades.get_grille_saisie(request.path_int("id")))

    @router.put("/api/evaluations/{id}/notes/{inscription}", module=Modules.NOTES)
    def upsert_note(request: Request):
        return result_response(request.services.grades.upsert_note(
            request.path_int("id"), request.path_int("inscription"), _note_value(request),
            request.field_bool("absent"), request.field("observation"), request.login))

    @router.post("/api/evaluations/{id}/notes", module=Modules.NOTES)
    def upsert_notes_lot(request: Request):
        """Saisie en lot : ``{"notes": [{id_inscription, valeur_note, absent, observation}]}``."""
        id_evaluation = request.path_int("id")
        lignes = request.data.get("notes") or []
        if not isinstance(lignes, list):
            raise HttpError(400, "Liste « notes » attendue.")
        erreurs: List[str] = []
        enregistrees = 0
        for ligne in lignes:
            if not isinstance(ligne, dict):
                continue
            try:
                id_inscription = int(ligne.get("id_inscription"))
            except (TypeError, ValueError):
                continue
            raw = ligne.get("valeur_note")
            try:
                valeur = None if raw in (None, "") else parse_float(raw)
            except (ValueError, TypeError):
                erreurs.append(f"Inscription {id_inscription} : note illisible « {raw} ».")
                continue
            absent = bool(ligne.get("absent"))
            result = request.services.grades.upsert_note(
                id_evaluation, id_inscription, valeur, absent, ligne.get("observation"),
                request.login)
            if result.success:
                enregistrees += 1
            else:
                erreurs.append(f"Inscription {id_inscription} : {result.full_message()}")
        payload = {"enregistrees": enregistrees, "erreurs": erreurs}
        if erreurs and not enregistrees:
            return ok_response(payload, "Aucune note enregistrée.")
        return ok_response(payload, f"{enregistrees} note(s) enregistrée(s)."
                           + (f" {len(erreurs)} erreur(s)." if erreurs else ""))

    @router.delete("/api/notes/{id}", module=Modules.NOTES)
    def delete_note(request: Request):
        return result_response(request.services.grades.delete_note(
            request.path_int("id"), request.login))

    @router.get("/api/moyennes", module=Modules.NOTES)
    def moyennes(request: Request):
        return ok_response({
            "matieres": request.services.grades.get_moyennes_matiere(
                request.param_int("classe"), request.param_int("periode")),
            "periodes": request.services.grades.get_moyennes_periode(
                request.param_int("classe"), request.param_int("periode")),
        })

    # ------------------------------------------------------------------
    # Bulletins
    # ------------------------------------------------------------------

    @router.get("/api/bulletins", module=Modules.BULLETINS)
    def bulletins(request: Request):
        return ok_response(request.services.bulletins.list_resumes(
            request.param_int("classe"), request.param_int("periode")))

    @router.get("/api/bulletins/{id}", module=Modules.BULLETINS)
    def get_bulletin(request: Request):
        id_bulletin = request.path_int("id")
        resume = next((r for r in request.services.bulletins.list_resumes()
                       if r.id_bulletin == id_bulletin), None)
        if resume is None:
            raise HttpError(404, "Bulletin introuvable.", "INTROUVABLE")
        bulletin = request.services.bulletins.get_by_inscription_periode(
            resume.id_inscription, resume.id_periode)
        matieres = {m.code_matiere: m for m in request.services.referentiel.list_matieres()}
        formateurs = {f.id_formateur: f for f in request.services.staff.list_formateurs()}
        lignes: List[Dict[str, Any]] = []
        for ligne in request.services.bulletins.list_lignes(id_bulletin):
            matiere = matieres.get(ligne.code_matiere)
            formateur = formateurs.get(ligne.id_formateur)
            lignes.append({
                "id_ligne": ligne.id_ligne, "code_matiere": ligne.code_matiere,
                "matiere": matiere.libelle if matiere else ligne.code_matiere,
                "module": matiere.code_module if matiere else None,
                "moyenne_mat": ligne.moyenne_mat, "coefficient": ligne.coefficient,
                "points": ligne.points, "rang_mat": ligne.rang_mat,
                "moy_min": ligne.moy_min, "moy_max": ligne.moy_max,
                "appreciation": ligne.appreciation,
                "formateur": formateur.nom_complet if formateur else None,
            })
        inscription = request.services.enrollments.get_detail(resume.id_inscription)
        etudiant = request.services.students.get(inscription.id_etudiant) if inscription else None
        return ok_response({
            "resume": resume, "bulletin": bulletin, "lignes": lignes,
            "inscription": inscription, "etudiant": etudiant,
            "etablissement": request.services.admin.get_etablissement(),
            "annee": request.services.admin.get_annee_active(),
            "absences_heures": request.services.schedule.total_heures_absence(resume.id_inscription),
        })

    @router.put("/api/bulletins/{id}", module=Modules.BULLETINS)
    def update_bulletin(request: Request):
        id_bulletin = request.path_int("id")
        resume = next((r for r in request.services.bulletins.list_resumes()
                       if r.id_bulletin == id_bulletin), None)
        if resume is None:
            raise HttpError(404, "Bulletin introuvable.", "INTROUVABLE")
        bulletin = request.services.bulletins.get_by_inscription_periode(
            resume.id_inscription, resume.id_periode)
        if bulletin is None:
            raise HttpError(404, "Bulletin introuvable.", "INTROUVABLE")
        return result_response(request.services.bulletins.update_appreciation(
            bulletin, request.field("appreciation"), request.login))

    @router.post("/api/bulletins/generer", module=Modules.BULLETINS)
    def generer_bulletins(request: Request):
        return result_response(request.services.bulletins.generer(
            request.field_int("id_classe", required=True),
            request.field_int("id_periode", required=True), request.login))

    @router.get("/api/mentions")
    def mentions(request: Request):
        return ok_response(request.services.bulletins.get_grille_mentions())

    # ------------------------------------------------------------------
    # Examens
    # ------------------------------------------------------------------

    @router.get("/api/sessions")
    def sessions(request: Request):
        return ok_response(request.services.exams.list_sessions(request.param_int("annee")))

    @router.post("/api/sessions", module=Modules.EXAMENS)
    def save_session(request: Request):
        session = _entity(request, SessionExam)
        if session.id_session:
            existing = request.services.exams.get_session(session.id_session)
            if existing is None:
                raise HttpError(404, "Session introuvable.", "INTROUVABLE")
            session = _entity(request, SessionExam, existing)
            return result_response(request.services.exams.update_session(session, request.login))
        return result_response(request.services.exams.create_session(session, request.login))

    @router.post("/api/sessions/{id}/cloture", module=Modules.EXAMENS)
    def cloture_session(request: Request):
        return result_response(request.services.exams.set_session_cloturee(
            request.path_int("id"), request.field_bool("cloturee", True), request.login))

    @router.delete("/api/sessions/{id}", module=Modules.EXAMENS)
    def delete_session(request: Request):
        return result_response(request.services.exams.delete_session(
            request.path_int("id"), request.login))

    @router.get("/api/epreuves", module=Modules.EXAMENS)
    def epreuves(request: Request):
        return ok_response(request.services.exams.list_epreuves(
            request.param_int("session"), request.param_int("classe")))

    @router.get("/api/epreuves/{id}", module=Modules.EXAMENS)
    def get_epreuve(request: Request):
        detail = request.services.exams.get_epreuve_detail(request.path_int("id"))
        if detail is None:
            raise HttpError(404, "Épreuve introuvable.", "INTROUVABLE")
        return ok_response({"epreuve": detail,
                            "notes": request.services.exams.get_grille_saisie(detail.id_epreuve)})

    @router.post("/api/epreuves", module=Modules.EXAMENS)
    def save_epreuve(request: Request):
        epreuve = _entity(request, Epreuve)
        if epreuve.id_epreuve:
            existing = request.services.exams.get_epreuve(epreuve.id_epreuve)
            if existing is None:
                raise HttpError(404, "Épreuve introuvable.", "INTROUVABLE")
            epreuve = _entity(request, Epreuve, existing)
            return result_response(request.services.exams.update_epreuve(epreuve, request.login))
        return result_response(request.services.exams.create_epreuve(epreuve, request.login))

    @router.delete("/api/epreuves/{id}", module=Modules.EXAMENS)
    def delete_epreuve(request: Request):
        return result_response(request.services.exams.delete_epreuve(
            request.path_int("id"), request.login))

    @router.get("/api/epreuves/{id}/notes", module=Modules.EXAMENS)
    def notes_epreuve(request: Request):
        return ok_response(request.services.exams.get_grille_saisie(request.path_int("id")))

    @router.put("/api/epreuves/{id}/notes/{inscription}", module=Modules.EXAMENS)
    def upsert_note_examen(request: Request):
        return result_response(request.services.exams.upsert_note(
            request.path_int("id"), request.path_int("inscription"), _note_value(request),
            request.field_bool("absent"), request.field("copie_num"), request.login))

    @router.post("/api/epreuves/{id}/notes", module=Modules.EXAMENS)
    def upsert_notes_examen_lot(request: Request):
        id_epreuve = request.path_int("id")
        lignes = request.data.get("notes") or []
        if not isinstance(lignes, list):
            raise HttpError(400, "Liste « notes » attendue.")
        erreurs: List[str] = []
        enregistrees = 0
        for ligne in lignes:
            if not isinstance(ligne, dict):
                continue
            try:
                id_inscription = int(ligne.get("id_inscription"))
            except (TypeError, ValueError):
                continue
            raw = ligne.get("valeur_note")
            try:
                valeur = None if raw in (None, "") else parse_float(raw)
            except (ValueError, TypeError):
                erreurs.append(f"Inscription {id_inscription} : note illisible « {raw} ».")
                continue
            result = request.services.exams.upsert_note(
                id_epreuve, id_inscription, valeur, bool(ligne.get("absent")),
                ligne.get("copie_num") or ligne.get("observation"), request.login)
            if result.success:
                enregistrees += 1
            else:
                erreurs.append(f"Inscription {id_inscription} : {result.full_message()}")
        return ok_response({"enregistrees": enregistrees, "erreurs": erreurs},
                           f"{enregistrees} note(s) enregistrée(s)."
                           + (f" {len(erreurs)} erreur(s)." if erreurs else ""))

    @router.get("/api/resultats", module=Modules.EXAMENS)
    def resultats(request: Request):
        id_classe = request.param_int("classe")
        if id_classe is None:
            raise HttpError(400, "Précisez une classe.")
        inscrits = {i.id_inscription: i for i in request.services.enrollments.list_by_classe(id_classe)}
        rows = []
        for resultat in request.services.exams.list_resultats(id_classe):
            inscription = inscrits.get(resultat.id_inscription)
            rows.append({
                "resultat": resultat,
                "matricule": inscription.matricule if inscription else None,
                "nom": inscription.nom if inscription else None,
                "prenom": inscription.prenom if inscription else None,
            })
        return ok_response(rows)

    @router.post("/api/resultats/generer", module=Modules.EXAMENS)
    def generer_resultats(request: Request):
        return result_response(request.services.exams.generer_resultats(
            request.field_int("id_classe", required=True),
            request.field_int("id_session", required=True), request.login))

    # ------------------------------------------------------------------
    # Emploi du temps
    # ------------------------------------------------------------------

    @router.get("/api/creneaux")
    def creneaux(request: Request):
        return ok_response(request.services.schedule.list_creneaux())

    @router.post("/api/creneaux", module=Modules.EMPLOI_DU_TEMPS)
    def save_creneau(request: Request):
        creneau = _entity(request, Creneau)
        if creneau.id_creneau:
            existing = request.services.schedule.get_creneau(creneau.id_creneau)
            if existing is None:
                raise HttpError(404, "Créneau introuvable.", "INTROUVABLE")
            creneau = _entity(request, Creneau, existing)
        return result_response(request.services.schedule.save_creneau(creneau, request.login))

    @router.delete("/api/creneaux/{id}", module=Modules.EMPLOI_DU_TEMPS)
    def delete_creneau(request: Request):
        return result_response(request.services.schedule.delete_creneau(
            request.path_int("id"), request.login))

    @router.get("/api/edt", module=Modules.EMPLOI_DU_TEMPS)
    def edt(request: Request):
        return ok_response(request.services.schedule.list_slots(request.param_int("classe")))

    @router.get("/api/edt/{id}", module=Modules.EMPLOI_DU_TEMPS)
    def get_slot(request: Request):
        slot = request.services.schedule.get_slot(request.path_int("id"))
        if slot is None:
            raise HttpError(404, "Créneau d’emploi du temps introuvable.", "INTROUVABLE")
        return ok_response({"slot": slot,
                            "seances": request.services.schedule.list_seances_by_edt(slot.id_edt)})

    @router.post("/api/edt", module=Modules.EMPLOI_DU_TEMPS)
    def save_slot(request: Request):
        slot = _entity(request, EmploiDuTemps)
        if slot.id_edt:
            detail = request.services.schedule.get_slot(slot.id_edt)
            if detail is None:
                raise HttpError(404, "Créneau d’emploi du temps introuvable.", "INTROUVABLE")
            base = EmploiDuTemps(id_edt=detail.id_edt, id_prog=detail.id_prog,
                                 id_creneau=detail.id_creneau, jour=detail.jour,
                                 id_salle=detail.id_salle, date_debut=detail.date_debut,
                                 date_fin=detail.date_fin, actif=detail.actif)
            slot = _entity(request, EmploiDuTemps, base)
            return result_response(request.services.schedule.update_slot(slot, request.login))
        return result_response(request.services.schedule.create_slot(slot, request.login))

    @router.delete("/api/edt/{id}", module=Modules.EMPLOI_DU_TEMPS)
    def delete_slot(request: Request):
        return result_response(request.services.schedule.delete_slot(
            request.path_int("id"), request.login))

    # ------------------------------------------------------------------
    # Séances (cahier de texte)
    # ------------------------------------------------------------------

    @router.get("/api/seances", module=Modules.EMPLOI_DU_TEMPS)
    def seances(request: Request):
        id_edt = request.param_int("edt")
        if id_edt is not None:
            return ok_response(request.services.schedule.list_seances_by_edt(id_edt))
        return ok_response(request.services.schedule.list_seances(
            request.param_date("debut"), request.param_date("fin"), request.param_int("classe")))

    @router.get("/api/seances/{id}", module=Modules.EMPLOI_DU_TEMPS)
    def get_seance(request: Request):
        seance = request.services.schedule.get_seance(request.path_int("id"))
        if seance is None:
            raise HttpError(404, "Séance introuvable.", "INTROUVABLE")
        return ok_response({"seance": seance,
                            "slot": request.services.schedule.get_slot(seance.id_edt),
                            "absences": request.services.schedule.list_absences_by_seance(seance.id_seance)})

    @router.post("/api/seances", module=Modules.EMPLOI_DU_TEMPS)
    def save_seance(request: Request):
        seance = _entity(request, Seance)
        if seance.id_seance:
            existing = request.services.schedule.get_seance(seance.id_seance)
            if existing is None:
                raise HttpError(404, "Séance introuvable.", "INTROUVABLE")
            seance = _entity(request, Seance, existing)
        return result_response(request.services.schedule.save_seance(seance, request.login))

    @router.delete("/api/seances/{id}", module=Modules.EMPLOI_DU_TEMPS)
    def delete_seance(request: Request):
        return result_response(request.services.schedule.delete_seance(
            request.path_int("id"), request.login))

    # ------------------------------------------------------------------
    # Absences
    # ------------------------------------------------------------------

    @router.get("/api/absences", module=Modules.ABSENCES)
    def absences(request: Request):
        id_seance = request.param_int("seance")
        id_inscription = request.param_int("inscription")
        if id_seance is not None:
            return ok_response(request.services.schedule.list_absences_by_seance(id_seance))
        if id_inscription is not None:
            return ok_response({
                "absences": request.services.schedule.list_absences_by_inscription(id_inscription),
                "total_heures": request.services.schedule.total_heures_absence(id_inscription),
                "seuil": request.services.parametres.seuil_absence,
            })
        raise HttpError(400, "Précisez une séance ou une inscription.")

    @router.get("/api/absences/synthese", module=Modules.ABSENCES)
    def synthese_absences(request: Request):
        """Synthèse par étudiant (vue R_ABSENCE_ETUDIANT), filtrable par classe."""
        classe = request.param("classe")
        rows = request.services.tables.load_saved_query("R_ABSENCE_ETUDIANT")
        if classe:
            rows = [r for r in rows if str(r.get("CLASSE") or "") == classe]
        return ok_response(rows)

    @router.post("/api/absences", module=Modules.ABSENCES)
    def save_absence(request: Request):
        absence = _entity(request, Absence)
        if absence.id_absence:
            existing = next((a for a in request.services.schedule.list_absences_by_seance(
                absence.id_seance or 0) if a.id_absence == absence.id_absence), None)
            if existing is None:
                raise HttpError(404, "Absence introuvable.", "INTROUVABLE")
            absence = _entity(request, Absence, existing)
        if absence.date_saisie is None:
            absence.date_saisie = _dt.datetime.now()
        return result_response(request.services.schedule.save_absence(absence, request.login))

    @router.delete("/api/absences/{id}", module=Modules.ABSENCES)
    def delete_absence(request: Request):
        return result_response(request.services.schedule.delete_absence(
            request.path_int("id"), request.login))
