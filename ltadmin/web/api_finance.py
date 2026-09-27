"""API : écolage (tarifs, échéanciers, encaissements, reçus, remises) et
paie des formateurs."""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal
from typing import Any, Dict, List

from ltadmin.models.entities import Tarif
from ltadmin.services.auth.habilitations import Modules
from ltadmin.web.routing import HttpError, Request, Router, ok_response, result_response
from ltadmin.web.serialization import parse_decimal, parse_entity


def _entity(request: Request, cls, base=None):
    try:
        return parse_entity(cls, request.data, base)
    except ValueError as ex:
        raise HttpError(400, "Vérifiez la saisie : " + str(ex), "VALIDATION", [str(ex)])


def _decimal_field(request: Request, name: str, required: bool = False):
    raw = request.field(name, required)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    try:
        return parse_decimal(raw)
    except ValueError as ex:
        raise HttpError(400, f"Champ « {name} » : {ex}")


def _echeance_payload(detail) -> Dict[str, Any]:
    return {
        "id_echeance": detail.id_echeance, "id_inscription": detail.id_inscription,
        "id_tarif": detail.id_tarif, "type_frais": detail.type_frais,
        "num_tranche": detail.num_tranche, "libelle": detail.libelle,
        "montant_du": detail.montant_du, "date_echeance": detail.date_echeance,
        "statut": detail.statut, "remise": detail.remise, "total_paye": detail.total_paye,
        "dernier_paiement": detail.dernier_paiement, "net_du": detail.net_du,
        "reste": detail.reste,
    }


def register(router: Router) -> None:

    # ------------------------------------------------------------------
    # Tarifs
    # ------------------------------------------------------------------

    @router.get("/api/tarifs", module=Modules.ECOLAGE)
    def tarifs(request: Request):
        id_classe = request.param_int("classe")
        if id_classe is None:
            raise HttpError(400, "Précisez une classe.")
        return ok_response(request.services.ecolage.list_tarifs(id_classe))

    @router.post("/api/tarifs", module=Modules.ECOLAGE)
    def save_tarif(request: Request):
        tarif = _entity(request, Tarif)
        if tarif.id_tarif:
            existing = next((t for t in request.services.ecolage.list_tarifs(tarif.id_classe or 0)
                             if t.id_tarif == tarif.id_tarif), None)
            if existing is None:
                raise HttpError(404, "Tarif introuvable.", "INTROUVABLE")
            tarif = _entity(request, Tarif, existing)
        return result_response(request.services.ecolage.save_tarif(tarif, request.login))

    @router.delete("/api/tarifs/{id}", module=Modules.ECOLAGE)
    def delete_tarif(request: Request):
        return result_response(request.services.ecolage.delete_tarif(
            request.path_int("id"), request.login))

    # ------------------------------------------------------------------
    # Échéanciers et échéances
    # ------------------------------------------------------------------

    @router.get("/api/inscriptions/{id}/echeances", module=Modules.ECOLAGE)
    def echeances(request: Request):
        id_inscription = request.path_int("id")
        details = request.services.ecolage.list_echeances(id_inscription)
        total_du = sum((d.net_du for d in details), Decimal("0"))
        total_paye = sum((d.total_paye for d in details), Decimal("0"))
        return ok_response({
            "inscription": request.services.enrollments.get_detail(id_inscription),
            "echeances": [_echeance_payload(d) for d in details],
            "total_du": total_du, "total_paye": total_paye, "reste": total_du - total_paye,
        })

    @router.post("/api/echeanciers/generer", module=Modules.ECOLAGE)
    def generer_echeancier(request: Request):
        return result_response(request.services.ecolage.generer_echeancier(
            request.field_int("id_inscription", required=True),
            request.field_int("id_tarif", required=True), request.login))

    @router.post("/api/echeanciers/supprimer", module=Modules.ECOLAGE)
    def supprimer_echeancier(request: Request):
        return result_response(request.services.ecolage.supprimer_echeancier(
            request.field_int("id_inscription", required=True),
            request.field_int("id_tarif", required=True), request.login))

    @router.get("/api/echeances/{id}", module=Modules.ECOLAGE)
    def get_echeance(request: Request):
        detail = request.services.ecolage.get_echeance_detail(request.path_int("id"))
        if detail is None:
            raise HttpError(404, "Échéance introuvable.", "INTROUVABLE")
        return ok_response({
            "echeance": _echeance_payload(detail),
            "paiements": request.services.ecolage.list_paiements(detail.id_echeance),
        })

    @router.get("/api/echeances/{id}/paiements", module=Modules.ECOLAGE)
    def paiements(request: Request):
        return ok_response(request.services.ecolage.list_paiements(request.path_int("id")))

    @router.post("/api/echeances/{id}/encaisser", module=Modules.ECOLAGE)
    def encaisser(request: Request):
        montant = _decimal_field(request, "montant", required=True)
        return result_response(request.services.ecolage.encaisser(
            request.path_int("id"), montant, request.field("mode_paie"),
            request.field("ref_externe"), request.field("observation"), request.login))

    @router.post("/api/echeances/{id}/remise", module=Modules.ECOLAGE)
    def remise(request: Request):
        return result_response(request.services.ecolage.accorder_remise(
            request.path_int("id"), _decimal_field(request, "remise"), request.login))

    @router.get("/api/paiements/{id}", module=Modules.ECOLAGE)
    def get_paiement(request: Request):
        """Données complètes d'un reçu (paiement, échéance, étudiant, établissement)."""
        paiement = request.services.ecolage.get_paiement(request.path_int("id"))
        if paiement is None:
            raise HttpError(404, "Paiement introuvable.", "INTROUVABLE")
        echeance = request.services.ecolage.get_echeance_detail(paiement.id_echeance)
        inscription = (request.services.enrollments.get_detail(echeance.id_inscription)
                       if echeance else None)
        return ok_response({
            "paiement": paiement,
            "echeance": _echeance_payload(echeance) if echeance else None,
            "inscription": inscription,
            "etablissement": request.services.admin.get_etablissement(),
            "devise": request.services.parametres.devise,
            "caissier": request.services.admin.get_utilisateur(paiement.code_utr or ""),
        })

    @router.delete("/api/paiements/{id}", module=Modules.ECOLAGE)
    def annuler_paiement(request: Request):
        return result_response(request.services.ecolage.annuler_paiement(
            request.path_int("id"), request.login))

    @router.get("/api/ecolage/situation", module=Modules.ECOLAGE)
    def situation(request: Request):
        """Situation d'écolage de toute une classe (une ligne par inscription)."""
        id_classe = request.param_int("classe")
        if id_classe is None:
            raise HttpError(400, "Précisez une classe.")
        rows: List[Dict[str, Any]] = []
        for inscription in request.services.enrollments.list_by_classe(id_classe):
            details = request.services.ecolage.list_echeances(inscription.id_inscription)
            total_du = sum((d.net_du for d in details), Decimal("0"))
            total_paye = sum((d.total_paye for d in details), Decimal("0"))
            aujourd_hui = _dt.datetime.now()
            echues = [d for d in details
                      if d.statut != "SOLDE" and d.date_echeance is not None
                      and d.date_echeance < aujourd_hui]
            rows.append({
                "id_inscription": inscription.id_inscription,
                "matricule": inscription.matricule, "nom": inscription.nom,
                "prenom": inscription.prenom, "statut_inscription": inscription.statut,
                "nb_echeances": len(details), "total_du": total_du,
                "total_paye": total_paye, "reste": total_du - total_paye,
                "nb_echues": len(echues),
                "montant_echu": sum((d.reste for d in echues), Decimal("0")),
                "statut": ("SANS ÉCHÉANCIER" if not details else
                           "SOLDE" if total_du - total_paye <= 0 else
                           "PARTIEL" if total_paye > 0 else "DU"),
            })
        return ok_response(rows)

    # ------------------------------------------------------------------
    # Paie des formateurs
    # ------------------------------------------------------------------

    @router.get("/api/paie", module=Modules.PAIE)
    def paie(request: Request):
        periode = request.param("periode")
        id_formateur = request.param_int("formateur")
        if id_formateur is not None:
            paies = request.services.payroll.list_paies_by_formateur(id_formateur)
        elif periode:
            paies = request.services.payroll.list_paies_by_periode(periode)
        else:
            raise HttpError(400, "Précisez une période (AAAA-MM) ou un formateur.")
        formateurs = {f.id_formateur: f for f in request.services.staff.list_formateurs()}
        rows = []
        for p in paies:
            formateur = formateurs.get(p.id_formateur)
            rows.append({
                "paie": p,
                "formateur": formateur.nom_complet if formateur else f"#{p.id_formateur}",
                "matricule": formateur.matricule if formateur else None,
            })
        return ok_response(rows)

    @router.get("/api/paie/heures", module=Modules.PAIE)
    def heures(request: Request):
        id_formateur = request.param_int("formateur")
        debut = request.param_date("debut")
        fin = request.param_date("fin")
        if id_formateur is None or debut is None or fin is None:
            raise HttpError(400, "Formateur, début et fin sont obligatoires.")
        return ok_response({"heures": request.services.payroll.heures_realisees(
            id_formateur, debut, fin)})

    @router.post("/api/paie/calculer", module=Modules.PAIE)
    def calculer(request: Request):
        return result_response(request.services.payroll.calculer_paie(
            request.field_int("id_formateur", required=True),
            str(request.field("periode", required=True)).strip(),
            request.field_date("debut", required=True), request.field_date("fin", required=True),
            request.login))

    @router.post("/api/paie/{id}/payer", module=Modules.PAIE)
    def payer(request: Request):
        paye = request.field_bool("paye", True)
        date_paie = request.field_date("date_paie") or (_dt.datetime.now() if paye else None)
        return result_response(request.services.payroll.marquer_payee(
            request.path_int("id"), paye, date_paie, request.login))

    @router.put("/api/paie/{id}", module=Modules.PAIE)
    def observation(request: Request):
        id_paie = request.path_int("id")
        id_formateur = request.field_int("id_formateur")
        candidates = (request.services.payroll.list_paies_by_formateur(id_formateur)
                      if id_formateur else [])
        paie = next((p for p in candidates if p.id_paie == id_paie), None)
        if paie is None:
            raise HttpError(404, "Paie introuvable.", "INTROUVABLE")
        return result_response(request.services.payroll.update_observation(
            paie, request.field("observation"), request.login))

    @router.delete("/api/paie/{id}", module=Modules.PAIE)
    def delete_paie(request: Request):
        return result_response(request.services.payroll.delete_paie(
            request.path_int("id"), request.login))
