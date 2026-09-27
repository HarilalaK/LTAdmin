"""API : rapports (états R_* + CSV), administration (paramètres,
établissement, années, journal, sauvegardes), utilisateurs et maintenance
générique des tables."""

from __future__ import annotations

import datetime as _dt
import os
import platform
import sqlite3
import sys
from typing import Any, Dict, List

from ltadmin import __version__
from ltadmin.core.result import Result
from ltadmin.models.entities import AnneeScolaire, Etablissement, Utilisateur
from ltadmin.services.auth import habilitations
from ltadmin.services.auth.habilitations import Modules
from ltadmin.services.reports.csv_exporter import CsvExporter
from ltadmin.web.routing import HttpError, Request, Response, Router, ok_response, result_response
from ltadmin.web.serialization import parse_decimal, parse_entity


def _entity(request: Request, cls, base=None):
    try:
        return parse_entity(cls, request.data, base)
    except ValueError as ex:
        raise HttpError(400, "Vérifiez la saisie : " + str(ex), "VALIDATION", [str(ex)])


def _user_payload(user: Utilisateur) -> Dict[str, Any]:
    return {
        "code_utr": user.code_utr, "nom_utr": user.nom_utr, "profil": user.profil,
        "profil_normalise": habilitations.normalize_profil(user.profil),
        "actif": user.actif,
    }


def _report_filters(request: Request) -> Dict[str, Any]:
    filters: Dict[str, Any] = {}
    if request.param("classe"):
        filters["classe"] = request.param("classe")
    if request.param_int("id_classe") is not None:
        filters["id_classe"] = request.param_int("id_classe")
    if request.param_int("id_periode") is not None:
        filters["id_periode"] = request.param_int("id_periode")
    if request.param_int("id_inscription") is not None:
        filters["id_inscription"] = request.param_int("id_inscription")
    if request.param("matricule"):
        filters["matricule"] = request.param("matricule")
    return filters


def _table_info(request: Request, name: str):
    tables = {t.name.upper(): t for t in request.services.tables.get_tables()}
    table = tables.get((name or "").upper())
    if table is None:
        raise HttpError(404, f"Table « {name} » introuvable.", "INTROUVABLE")
    return table


# Paramètres dont la valeur doit être numérique (contrôlée côté API).
PARAMETRES_NUMERIQUES = frozenset({
    "BAREME_DEFAUT", "MOY_ADMISSION", "NOTE_ELIMINATOIRE", "POIDS_CC", "POIDS_EXAMEN",
    "SEUIL_ABSENCE",
})


def register(router: Router) -> None:

    # ------------------------------------------------------------------
    # Rapports
    # ------------------------------------------------------------------

    @router.get("/api/rapports", module=Modules.RAPPORTS)
    def rapports(request: Request):
        service = request.services.reports
        return ok_response([{
            "key": d.key, "title": d.title, "description": d.description,
            "filter_kind": d.filter_kind, "filter_label": service.filter_label(d),
        } for d in service.list_definitions()])

    @router.get("/api/rapports/{key}", module=Modules.RAPPORTS)
    def rapport(request: Request):
        key = request.path_str("key")
        columns, rows = request.services.reports.build(key, **_report_filters(request))
        return ok_response({"columns": columns, "rows": rows, "count": len(rows)})

    @router.get("/api/rapports/{key}/csv", module=Modules.RAPPORTS)
    def rapport_csv(request: Request):
        key = request.path_str("key")
        columns, rows = request.services.reports.build(key, **_report_filters(request))
        if not rows:
            raise HttpError(404, "Aucune donnée à exporter pour ces critères.", "INTROUVABLE")
        text = CsvExporter.to_text(columns, rows)
        filename = f"{key}_{_dt.datetime.now():%Y%m%d_%H%M}.csv"
        request.services.journal.log_operation(
            request.login, "EXPORT", None, None, f"Export CSV de l’état {key} ({len(rows)} lignes).")
        return Response(raw=text.encode("utf-8-sig"), content_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'})

    # ------------------------------------------------------------------
    # Administration
    # ------------------------------------------------------------------

    @router.get("/api/admin/info", module=Modules.ADMINISTRATION)
    def info(request: Request):
        services = request.services
        database_path = services.database.database_path
        taille = os.path.getsize(database_path) if os.path.isfile(database_path) else 0
        tables = services.tables.get_tables()
        compte = {t.name: services.tables.count(t) for t in tables}
        return ok_response({
            "version": __version__,
            "python": sys.version.split()[0],
            "sqlite": sqlite3.sqlite_version,
            "systeme": f"{platform.system()} {platform.release()}",
            "base": database_path,
            "taille_base": taille,
            "taille_base_texte": services.backups.format_size(taille),
            "nb_tables": len(tables),
            "lignes_par_table": compte,
            "dossier_sauvegardes": services.backups.backup_directory,
            "sessions_actives": len(request.app.sessions),
            "demarrage": request.app.started_at,
        })

    @router.get("/api/admin/parametres", module=Modules.ADMINISTRATION)
    def parametres(request: Request):
        return ok_response(request.services.parametres.list_parametres())

    @router.put("/api/admin/parametres/{cle}", module=Modules.ADMINISTRATION)
    def set_parametre(request: Request):
        cle = request.path_str("cle").strip().upper()
        valeur = str(request.field("valeur", required=True)).strip()
        if cle in PARAMETRES_NUMERIQUES:
            try:
                nombre = parse_decimal(valeur)
            except (ValueError, TypeError):
                nombre = None
            if nombre is None or nombre < 0:
                raise HttpError(400, f"Le paramètre « {cle} » attend un nombre positif "
                                     f"(reçu : « {valeur} »).")
            if cle in ("POIDS_CC", "POIDS_EXAMEN") and nombre > 100:
                raise HttpError(400, "Un poids s’exprime en pourcentage (0 à 100).")
            if cle in ("MOY_ADMISSION", "NOTE_ELIMINATOIRE") and nombre > 20:
                raise HttpError(400, f"« {cle} » doit rester entre 0 et 20.")
            valeur = format(nombre.normalize(), "f")
        return result_response(request.services.parametres.set_value(cle, valeur, request.login))

    @router.get("/api/admin/etablissement")
    def etablissement(request: Request):
        return ok_response(request.services.admin.get_etablissement())

    @router.put("/api/admin/etablissement", module=Modules.ADMINISTRATION)
    def save_etablissement(request: Request):
        existing = request.services.admin.get_etablissement()
        return result_response(request.services.admin.save_etablissement(
            _entity(request, Etablissement, existing), request.login))

    @router.post("/api/admin/annees", module=Modules.ADMINISTRATION)
    def save_annee(request: Request):
        annee = _entity(request, AnneeScolaire)
        if annee.id_annee:
            existing = next((a for a in request.services.admin.list_annees()
                             if a.id_annee == annee.id_annee), None)
            if existing is None:
                raise HttpError(404, "Année introuvable.", "INTROUVABLE")
            annee = _entity(request, AnneeScolaire, existing)
        return result_response(request.services.admin.save_annee(annee, request.login))

    @router.post("/api/admin/annees/{id}/activer", module=Modules.ADMINISTRATION)
    def activer_annee(request: Request):
        return result_response(request.services.admin.activer_annee(
            request.path_int("id"), request.login))

    @router.get("/api/admin/journal", module=Modules.ADMINISTRATION)
    def journal(request: Request):
        return ok_response(request.services.journal.consulter(
            request.param_date("depuis"), request.param("utilisateur"), request.param("action"),
            request.param_int("max", 500) or 500))

    @router.get("/api/admin/sauvegardes", module=Modules.ADMINISTRATION)
    def sauvegardes(request: Request):
        service = request.services.backups
        infos = service.list_backups(request.param_bool("securite"))
        return ok_response({
            "dossier": service.backup_directory,
            "sauvegardes": [{
                "file_path": i.file_path, "file_name": i.file_name, "created_at": i.created_at,
                "size_bytes": i.size_bytes, "size_text": service.format_size(i.size_bytes),
                "description": service.describe(i),
            } for i in infos],
        })

    @router.post("/api/admin/sauvegardes", module=Modules.ADMINISTRATION)
    def creer_sauvegarde(request: Request):
        result = request.services.backups.create_backup()
        if result.is_success:
            request.services.journal.log_operation(
                request.login, "SAUVEGARDE", None, None, result.message)
        return result_response(result)

    @router.post("/api/admin/sauvegardes/restaurer", module=Modules.ADMINISTRATION)
    def restaurer(request: Request):
        chemin = str(request.field("file_path", required=True))
        service = request.services.backups
        autorises = {i.file_path for i in service.list_backups(include_safety_copies=True)}
        if os.path.abspath(chemin) not in {os.path.abspath(a) for a in autorises}:
            raise HttpError(400, "Choisissez une sauvegarde listée dans le dossier Sauvegardes.")
        result = service.restore_backup(chemin)
        if result.is_success:
            request.services.refresh()
            request.services.journal.log_operation(
                request.login, "RESTAURATION", None, None, result.message)
        return result_response(result)

    @router.post("/api/admin/sauvegardes/purger", module=Modules.ADMINISTRATION)
    def purger(request: Request):
        keep = request.field_int("conserver") or 10
        return result_response(request.services.backups.purge_backups(keep))

    # ------------------------------------------------------------------
    # Utilisateurs
    # ------------------------------------------------------------------

    @router.get("/api/utilisateurs", module=Modules.UTILISATEURS)
    def utilisateurs(request: Request):
        return ok_response([_user_payload(u) for u in request.services.admin.list_utilisateurs()])

    @router.get("/api/profils")
    def profils(request: Request):
        return ok_response([{
            "libelle": p,
            "modules": [m for m in habilitations.MENU_ORDER if habilitations.can_access(p, m)],
        } for p in habilitations.PROFILS_CONNUS])

    @router.post("/api/utilisateurs", module=Modules.UTILISATEURS)
    def save_utilisateur(request: Request):
        data = request.data
        code = str(data.get("code_utr") or "").strip().upper()
        existing = request.services.admin.get_utilisateur(code) if code else None
        utilisateur = _entity(request, Utilisateur, existing)
        utilisateur.code_utr = code
        mot_de_passe = data.get("mot_de_passe")
        if isinstance(mot_de_passe, str) and not mot_de_passe.strip():
            mot_de_passe = None
        result = request.services.admin.save_utilisateur(utilisateur, mot_de_passe, request.login)
        if result.is_success and existing is not None and utilisateur.actif is False:
            request.app.sessions.revoke_user(code)
        return result_response(result)

    @router.post("/api/utilisateurs/{code}/actif", module=Modules.UTILISATEURS)
    def set_actif(request: Request):
        code = request.path_str("code")
        actif = request.field_bool("actif", True)
        result = request.services.admin.set_actif(code, actif, request.login)
        if result.is_success and not actif:
            request.app.sessions.revoke_user(code)
        return result_response(result)

    @router.delete("/api/utilisateurs/{code}", module=Modules.UTILISATEURS)
    def delete_utilisateur(request: Request):
        code = request.path_str("code")
        result = request.services.admin.delete_utilisateur(code, request.login)
        if result.is_success:
            request.app.sessions.revoke_user(code)
        return result_response(result)

    # ------------------------------------------------------------------
    # Maintenance générique des tables
    # ------------------------------------------------------------------

    @router.get("/api/tables", module=Modules.TABLES)
    def tables(request: Request):
        service = request.services.tables
        return ok_response([{
            "name": t.name, "count": service.count(t),
            "columns": [{"name": c.name, "kind": c.kind, "size": c.size, "nullable": c.nullable,
                         "autonumber": c.autonumber, "is_primary_key": c.is_primary_key}
                        for c in t.columns],
        } for t in service.get_tables()])

    @router.get("/api/tables/{name}", module=Modules.TABLES)
    def table_rows(request: Request):
        table = _table_info(request, request.path_str("name"))
        rows = request.services.tables.load_table(table, request.param("q"),
                                                  request.param_int("max", 500) or 500)
        if table.name.upper() == "UTILISATEUR":
            for row in rows:
                if "MOT_PASSE" in row:
                    row["MOT_PASSE"] = "••••••"
        return ok_response({
            "name": table.name,
            "columns": [{"name": c.name, "kind": c.kind, "size": c.size, "nullable": c.nullable,
                         "autonumber": c.autonumber, "is_primary_key": c.is_primary_key}
                        for c in table.columns],
            "rows": rows, "count": request.services.tables.count(table),
        })

    def _guard_table_write(request: Request, table) -> None:
        if table.name.upper() == "UTILISATEUR":
            raise HttpError(409, "Gérez les comptes via l’écran « Profils utilisateurs ».", "GESTION")

    @router.post("/api/tables/{name}", module=Modules.TABLES)
    def table_insert(request: Request):
        table = _table_info(request, request.path_str("name"))
        _guard_table_write(request, table)
        values = request.data.get("values")
        if not isinstance(values, dict):
            raise HttpError(400, "Objet « values » attendu.")
        try:
            count = request.services.tables.insert(table, values)
        except Exception as ex:
            return result_response(Result.fail(_sql_message(ex), "VALIDATION"))
        request.services.journal.log_creation(request.login, table.name, None,
                                              f"Maintenance : insertion ({count} ligne).")
        return ok_response({"count": count}, f"{count} ligne insérée.")

    @router.put("/api/tables/{name}", module=Modules.TABLES)
    def table_update(request: Request):
        table = _table_info(request, request.path_str("name"))
        _guard_table_write(request, table)
        original = request.data.get("original")
        values = request.data.get("values")
        if not isinstance(original, dict) or not isinstance(values, dict):
            raise HttpError(400, "Objets « original » et « values » attendus.")
        try:
            count = request.services.tables.update(table, original, values)
        except Exception as ex:
            return result_response(Result.fail(_sql_message(ex), "VALIDATION"))
        request.services.journal.log_modification(request.login, table.name, None,
                                                  f"Maintenance : mise à jour ({count} ligne).")
        return ok_response({"count": count}, f"{count} ligne modifiée.")

    @router.post("/api/tables/{name}/supprimer", module=Modules.TABLES)
    def table_delete(request: Request):
        table = _table_info(request, request.path_str("name"))
        _guard_table_write(request, table)
        row = request.data.get("row")
        if not isinstance(row, dict):
            raise HttpError(400, "Objet « row » attendu.")
        try:
            count = request.services.tables.delete(table, row)
        except Exception as ex:
            return result_response(Result.fail(_sql_message(ex), "LIAISON"))
        request.services.journal.log_suppression(request.login, table.name, None,
                                                 f"Maintenance : suppression ({count} ligne).")
        return ok_response({"count": count}, f"{count} ligne supprimée.")


def _sql_message(ex: Exception) -> str:
    from ltadmin.data import error_helper
    try:
        return error_helper.interpret(ex).message
    except Exception:
        return str(ex)
