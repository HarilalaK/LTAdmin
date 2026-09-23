"""Les 8 états de l'application, adossés aux requêtes enregistrées de la base.

Filtres : R_MOYENNE_MATIERE / R_MOYENNE_PERIODE / R_PAIEMENT_ECHEANCE par
identifiants ; R_LISTE_ETUDIANT / R_SITUATION_ECOLAGE / R_EDT_CLASSE par
libellé de classe ; R_BULLETIN_DETAIL par bulletin ; R_ABSENCE_ETUDIANT par
matricule. Chaque état est exportable en CSV (« ; », UTF-8 BOM).
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from ltadmin.data.access_database import AccessDatabase
from ltadmin.data.schema import SavedQueries, quote_identifier as q
from ltadmin.services.logging.app_logger import AppLogger
from ltadmin.services.reports.csv_exporter import CsvExporter


@dataclass
class ReportDefinition:
    key: str
    title: str
    description: str = ""
    filter_kind: str = "none"  # none | classe_libelle | classe_periode | bulletin | inscription | matricule


REPORT_CATALOG: Tuple[ReportDefinition, ...] = (
    ReportDefinition(
        "liste_etudiants", "Liste des étudiants",
        "Inscrits avec classe, filière, niveau, année et statut.",
        filter_kind="classe_libelle"),
    ReportDefinition(
        "moyennes_matiere", "Moyennes par matière",
        "Moyennes sur 20 par étudiant et par matière (notes non absentes).",
        filter_kind="classe_periode"),
    ReportDefinition(
        "moyennes_periode", "Moyennes générales par période",
        "Moyennes pondérées par les coefficients, par étudiant et période.",
        filter_kind="classe_periode"),
    ReportDefinition(
        "bulletin_detail", "Détail des bulletins",
        "Lignes de bulletins : moyennes, coefficients, points, rangs, décision.",
        filter_kind="classe_libelle"),
    ReportDefinition(
        "paiement_echeance", "Paiements par échéance",
        "Total payé et dernier paiement pour chaque échéance d'une inscription.",
        filter_kind="inscription"),
    ReportDefinition(
        "situation_ecolage", "Situation d'écolage",
        "Dû, payé et reste par étudiant (échéanciers de la classe).",
        filter_kind="classe_libelle"),
    ReportDefinition(
        "edt_classe", "Emploi du temps d'une classe",
        "Créneaux hebdomadaires actifs : matière, formateur, salle.",
        filter_kind="classe_libelle"),
    ReportDefinition(
        "absences_etudiant", "Absences par étudiant",
        "Heures d'absence totales et justifiées par étudiant.",
        filter_kind="matricule"),
)

_FILTER_LABELS = {
    "classe_libelle": "Classe (libellé)",
    "classe_periode": "Classe + période",
    "bulletin": "Bulletin",
    "inscription": "Inscription",
    "matricule": "Matricule étudiant",
}


class ReportService:

    def __init__(self, database: AccessDatabase, logger: AppLogger):
        self._database = database
        self._logger = logger

    @staticmethod
    def list_definitions() -> List[ReportDefinition]:
        return list(REPORT_CATALOG)

    @staticmethod
    def filter_label(definition: ReportDefinition) -> str:
        return _FILTER_LABELS.get(definition.filter_kind, "")

    def build(self, key: str, **filters) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Exécute l'état et retourne (colonnes, lignes) ; erreurs → listes vides."""
        try:
            definition = next((d for d in REPORT_CATALOG if d.key == key), None)
            if definition is None:
                return [], []
            sql, parameters = self._build_query(key, filters)
            if sql is None:
                return [], []
            rows = self._database.query(sql, parameters)
            columns = self._columns(rows, key)
            return columns, rows
        except Exception as ex:
            self._logger.error(f"Exécution de l’état {key}", ex)
            return [], []

    def export(self, key: str, path: str, **filters) -> Tuple[bool, str]:
        """Exécute l'état puis l'exporte en CSV. Retourne (succès, message)."""
        try:
            columns, rows = self.build(key, **filters)
            if not rows:
                return False, "Aucune donnée à exporter pour ces critères."
            summary = CsvExporter.write(path, columns, rows)
            return True, summary
        except Exception as ex:
            self._logger.error(f"Export de l’état {key}", ex)
            return False, "Export impossible : " + str(ex)

    # ----- Construction des requêtes (SELECT * FROM requête + WHERE) -----

    def _build_query(self, key: str, filters: Dict[str, Any]):
        if key == "liste_etudiants":
            return self._by_classe_libelle(SavedQueries.LISTE_ETUDIANT, filters)
        if key == "moyennes_matiere":
            return self._by_classe_periode(SavedQueries.MOYENNE_MATIERE, filters)
        if key == "moyennes_periode":
            return self._by_classe_periode(SavedQueries.MOYENNE_PERIODE, filters)
        if key == "bulletin_detail":
            return self._by_classe_libelle(SavedQueries.BULLETIN_DETAIL, filters)
        if key == "paiement_echeance":
            return self._by_inscription(SavedQueries.PAIEMENT_ECHEANCE, filters)
        if key == "situation_ecolage":
            return self._by_classe_libelle(SavedQueries.SITUATION_ECOLAGE, filters)
        if key == "edt_classe":
            return self._by_classe_libelle(SavedQueries.EDT_CLASSE, filters)
        if key == "absences_etudiant":
            return self._by_matricule(SavedQueries.ABSENCE_ETUDIANT, filters)
        return None, None

    @staticmethod
    def _by_classe_libelle(query_name: str, filters: Dict[str, Any]):
        classe = (filters.get("classe") or "").strip()
        if not classe:
            return None, None
        return (f"SELECT * FROM {q(query_name)} WHERE {q('CLASSE')} = ? "
                f"ORDER BY 1", [classe])

    @staticmethod
    def _by_classe_periode(query_name: str, filters: Dict[str, Any]):
        conditions, parameters = [], []
        id_classe = filters.get("id_classe")
        id_periode = filters.get("id_periode")
        if id_classe is not None:
            conditions.append(f"{q('ID_CLASSE')} = ?")
            parameters.append(id_classe)
        if id_periode is not None:
            conditions.append(f"{q('ID_PERIODE')} = ?")
            parameters.append(id_periode)
        if not conditions:
            return None, None
        sql = f"SELECT * FROM {q(query_name)} WHERE " + " AND ".join(conditions)
        return sql, parameters

    @staticmethod
    def _by_inscription(query_name: str, filters: Dict[str, Any]):
        id_inscription = filters.get("id_inscription")
        if id_inscription is None:
            return None, None
        return f"SELECT * FROM {q(query_name)} WHERE {q('ID_INSCRIPTION')} = ?", \
            [id_inscription]

    @staticmethod
    def _by_matricule(query_name: str, filters: Dict[str, Any]):
        matricule = (filters.get("matricule") or "").strip()
        if not matricule:
            return None, None
        return f"SELECT * FROM {q(query_name)} WHERE {q('MATRICULE')} = ?", [matricule]

    @staticmethod
    def _columns(rows: List[Dict[str, Any]], key: str) -> List[str]:
        if rows:
            return list(rows[0].keys())
        return list(_FALLBACK_COLUMNS.get(key, []))


_FALLBACK_COLUMNS: Dict[str, List[str]] = {
    "liste_etudiants": ["MATRICULE", "NOM", "PRENOM", "SEXE", "DATE_NAISSANCE",
                        "TEL", "CLASSE", "FILIERE", "NIVEAU", "ANNEE", "STATUT"],
    "moyennes_matiere": ["ID_INSCRIPTION", "ID_PERIODE", "ID_CLASSE", "CODE_MATIERE",
                         "COEFFICIENT", "MOYENNE_MAT"],
    "moyennes_periode": ["ID_INSCRIPTION", "ID_PERIODE", "ID_CLASSE", "TOTAL_POINTS",
                         "TOTAL_COEF", "MOYENNE"],
    "bulletin_detail": ["MATRICULE", "NOM", "PRENOM", "CLASSE", "PERIODE", "MATIERE",
                        "MOYENNE_MAT", "COEFFICIENT", "POINTS", "RANG_MAT", "MOYENNE",
                        "RANG", "EFFECTIF", "DECISION"],
    "paiement_echeance": ["ID_ECHEANCE", "TOTAL_PAYE", "DERNIER_PAIEMENT"],
    "situation_ecolage": ["MATRICULE", "NOM", "PRENOM", "CLASSE", "ID_INSCRIPTION",
                          "TOTAL_DU", "TOTAL_PAYE", "RESTE"],
    "edt_classe": ["CLASSE", "JOUR", "ORDRE_CRE", "HEURE_DEBUT", "HEURE_FIN", "MATIERE",
                   "FORMATEUR", "NOM_SALLE"],
    "absences_etudiant": ["ID_INSCRIPTION", "MATRICULE", "NOM", "PRENOM", "CLASSE",
                          "TOTAL_HEURES", "HEURES_JUSTIFIEES"],
}
