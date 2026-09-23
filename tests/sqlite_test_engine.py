"""Moteur SQLite pour les tests : même interface que PyodbcEngine.

Permet de tester toute la pile (dépôts + services) sans Access ni pyodbc.
Adaptations de dialecte : TOP n → LIMIT n, @@IDENTITY → lastrowid,
CStr() enregistrée comme fonction Python.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sqlite3
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from ltadmin.data.schema_catalog import TABLES
from ltadmin.models.db_models import DbColumnInfo, DbTableInfo

_TOP_RE = re.compile(r"^\s*SELECT\s+TOP\s+(\d+)\s+(.*)$", re.IGNORECASE | re.DOTALL)

_KIND_TO_SQLITE = {
    "TEXT": "TEXT",
    "MEMO": "TEXT",
    "LONG": "INTEGER",
    "DOUBLE": "REAL",
    "CURRENCY": "REAL",
    "DATETIME": "TEXT",
    "BOOLEAN": "INTEGER",
}


def _cstr(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value)


class SqliteEngine:
    """Moteur de test : interface open/close/fetch_all/execute/… identique."""

    def __init__(self):
        self._connections: List[sqlite3.Connection] = []

    def open(self, path: str):
        connection = sqlite3.connect(path)
        connection.isolation_level = None  # autocommit explicite
        connection.create_function("CStr", 1, _cstr)
        # Access : UCASE/LCASE (SQLite natif : upper/lower).
        connection.create_function(
            "UCASE", 1, lambda v: v.upper() if isinstance(v, str) else v)
        connection.create_function(
            "LCASE", 1, lambda v: v.lower() if isinstance(v, str) else v)
        self._connections.append(connection)
        return connection

    def close(self, connection) -> None:
        try:
            connection.close()
        finally:
            if connection in self._connections:
                self._connections.remove(connection)

    # ----- SQL -----

    @staticmethod
    def _translate(sql: str) -> str:
        match = _TOP_RE.match(sql)
        if match:
            sql = f"SELECT {match.group(2)} LIMIT {match.group(1)}"
        # @@IDENTITY est géré par insert_and_get_id (jamais envoyé ici).
        return sql

    def _cursor_execute(self, connection, sql: str, params: Sequence[Any]):
        cursor = connection.cursor()
        try:
            cursor.execute(self._translate(sql),
                           [self._adapt(p) for p in params])
            return cursor
        except Exception:
            cursor.close()
            raise

    @staticmethod
    def _adapt(value: Any) -> Any:
        """SQLite n'accepte ni Decimal ni date : conversion explicite."""
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (_dt.datetime, _dt.date)):
            return value.isoformat(sep=" ") \
                if isinstance(value, _dt.datetime) else value.isoformat()
        return value

    def fetch_all(self, connection, sql: str, params: Sequence[Any]) \
            -> List[Dict[str, Any]]:
        cursor = self._cursor_execute(connection, sql, params)
        try:
            columns = [d[0] for d in (cursor.description or [])]
            rows: List[Dict[str, Any]] = []
            for row in cursor.fetchall():
                record: Dict[str, Any] = {}
                for name, value in zip(columns, row):
                    if name not in record:
                        record[name] = value
                rows.append(record)
            return rows
        finally:
            cursor.close()

    def execute(self, connection, sql: str, params: Sequence[Any]) -> int:
        cursor = self._cursor_execute(connection, sql, params)
        try:
            return cursor.rowcount if cursor.rowcount is not None else 0
        finally:
            cursor.close()

    def insert_and_get_id(self, connection, sql: str,
                          params: Sequence[Any]) -> int:
        cursor = self._cursor_execute(connection, sql, params)
        try:
            return int(cursor.lastrowid or 0)
        finally:
            cursor.close()

    def begin(self, connection) -> None:
        connection.execute("BEGIN")

    def commit(self, connection) -> None:
        connection.execute("COMMIT")

    def rollback(self, connection) -> None:
        try:
            connection.execute("ROLLBACK")
        except sqlite3.OperationalError:
            pass

    # ----- Métadonnées -----

    def list_tables(self, connection) -> List[str]:
        cursor = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name")
        return [row[0] for row in cursor.fetchall()]

    def list_columns(self, connection, table: str) -> List[DbColumnInfo]:
        catalog = TABLES.get(table.upper())
        if catalog:
            return [DbColumnInfo(
                name=name, kind=kind, size=size, nullable=nullable,
                autonumber=autonumber,
                is_primary_key=name in catalog["pk"],
            ) for name, kind, size, nullable, autonumber in catalog["columns"]]
        cursor = connection.execute(f"PRAGMA table_info([{table}])")
        return [DbColumnInfo(name=row[1], kind="TEXT", size=0,
                             nullable=not row[3], autonumber=False,
                             is_primary_key=bool(row[5]))
                for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Création de la base de test
# ---------------------------------------------------------------------------

SAVED_QUERY_VIEWS = {
    "R_PAIEMENT_ECHEANCE": """
        SELECT ID_ECHEANCE, SUM(MONTANT) AS TOTAL_PAYE,
               MAX(DATE_PAIEMENT) AS DERNIER_PAIEMENT
        FROM PAIEMENT GROUP BY ID_ECHEANCE
    """,
    "R_MOYENNE_MATIERE": """
        SELECT I.ID_INSCRIPTION, EV.ID_PERIODE, P.ID_CLASSE, P.CODE_MATIERE,
               P.COEFFICIENT, P.ID_FORMATEUR,
               SUM(N.VALEUR_NOTE / EV.BAREME * 20 * EV.POIDS) / SUM(EV.POIDS)
                   AS MOYENNE_MAT
        FROM NOTE AS N
        INNER JOIN EVALUATION AS EV ON N.ID_EVALUATION = EV.ID_EVALUATION
        INNER JOIN PROGRAMME AS P ON EV.ID_PROG = P.ID_PROG
        INNER JOIN INSCRIPTION AS I ON N.ID_INSCRIPTION = I.ID_INSCRIPTION
        WHERE N.ABSENT = FALSE AND N.VALEUR_NOTE IS NOT NULL
        GROUP BY I.ID_INSCRIPTION, EV.ID_PERIODE, P.ID_CLASSE, P.CODE_MATIERE,
                 P.COEFFICIENT, P.ID_FORMATEUR
    """,
    "R_MOYENNE_PERIODE": """
        SELECT ID_INSCRIPTION, ID_PERIODE, ID_CLASSE,
               SUM(MOYENNE_MAT * COEFFICIENT) AS TOTAL_POINTS,
               SUM(COEFFICIENT) AS TOTAL_COEF,
               SUM(MOYENNE_MAT * COEFFICIENT) / SUM(COEFFICIENT) AS MOYENNE
        FROM R_MOYENNE_MATIERE
        GROUP BY ID_INSCRIPTION, ID_PERIODE, ID_CLASSE
    """,
    "R_LISTE_ETUDIANT": """
        SELECT I.ID_INSCRIPTION, E.MATRICULE, E.NOM, E.PRENOM, E.SEXE,
               E.DATE_NAISSANCE, E.TEL, C.LIBELLE AS CLASSE, F.FILIERE,
               N.NIVEAU, A.LIBELLE AS ANNEE, I.STATUT
        FROM INSCRIPTION AS I
        INNER JOIN ETUDIANT AS E ON I.ID_ETUDIANT = E.ID_ETUDIANT
        INNER JOIN CLASSE AS C ON I.ID_CLASSE = C.ID_CLASSE
        INNER JOIN FILIERE AS F ON C.CODE_FILIERE = F.CODE_FILIERE
        INNER JOIN NIVEAU AS N ON C.CODE_NIVEAU = N.CODE_NIVEAU
        INNER JOIN ANNEE_SCOLAIRE AS A ON C.ID_ANNEE = A.ID_ANNEE
    """,
    "R_BULLETIN_DETAIL": """
        SELECT E.MATRICULE, E.NOM, E.PRENOM, C.LIBELLE AS CLASSE,
               PE.LIBELLE AS PERIODE, M.MATIERE, BL.MOYENNE_MAT,
               BL.COEFFICIENT, BL.POINTS, BL.RANG_MAT, B.MOYENNE, B.RANG,
               B.EFFECTIF, B.DECISION
        FROM BULLETIN AS B
        INNER JOIN BULLETIN_LIGNE AS BL ON B.ID_BULLETIN = BL.ID_BULLETIN
        INNER JOIN MATIERE AS M ON BL.CODE_MATIERE = M.CODE_MATIERE
        INNER JOIN INSCRIPTION AS I ON B.ID_INSCRIPTION = I.ID_INSCRIPTION
        INNER JOIN ETUDIANT AS E ON I.ID_ETUDIANT = E.ID_ETUDIANT
        INNER JOIN CLASSE AS C ON I.ID_CLASSE = C.ID_CLASSE
        INNER JOIN PERIODE_EVAL AS PE ON B.ID_PERIODE = PE.ID_PERIODE
    """,
    "R_SITUATION_ECOLAGE": """
        SELECT E.MATRICULE, E.NOM, E.PRENOM, C.LIBELLE AS CLASSE,
               I.ID_INSCRIPTION,
               SUM(ECH.MONTANT_DU - IFNULL(ECH.REMISE, 0)) AS TOTAL_DU,
               SUM(IFNULL(PE.TOTAL_PAYE, 0)) AS TOTAL_PAYE,
               SUM(ECH.MONTANT_DU - IFNULL(ECH.REMISE, 0))
                   - SUM(IFNULL(PE.TOTAL_PAYE, 0)) AS RESTE
        FROM ECHEANCIER AS ECH
        LEFT JOIN R_PAIEMENT_ECHEANCE AS PE ON ECH.ID_ECHEANCE = PE.ID_ECHEANCE
        INNER JOIN INSCRIPTION AS I ON ECH.ID_INSCRIPTION = I.ID_INSCRIPTION
        INNER JOIN ETUDIANT AS E ON I.ID_ETUDIANT = E.ID_ETUDIANT
        INNER JOIN CLASSE AS C ON I.ID_CLASSE = C.ID_CLASSE
        GROUP BY E.MATRICULE, E.NOM, E.PRENOM, C.LIBELLE, I.ID_INSCRIPTION
    """,
    "R_EDT_CLASSE": """
        SELECT C.LIBELLE AS CLASSE, EDT.JOUR, CR.ORDRE_CRE, CR.HEURE_DEBUT,
               CR.HEURE_FIN, M.MATIERE,
               (F.NOM || ' ' || F.PRENOM) AS FORMATEUR, S.NOM_SALLE
        FROM EMPLOI_DU_TEMPS AS EDT
        INNER JOIN CRENEAU AS CR ON EDT.ID_CRENEAU = CR.ID_CRENEAU
        INNER JOIN PROGRAMME AS P ON EDT.ID_PROG = P.ID_PROG
        INNER JOIN CLASSE AS C ON P.ID_CLASSE = C.ID_CLASSE
        INNER JOIN MATIERE AS M ON P.CODE_MATIERE = M.CODE_MATIERE
        LEFT JOIN FORMATEUR AS F ON P.ID_FORMATEUR = F.ID_FORMATEUR
        LEFT JOIN SALLE AS S ON EDT.ID_SALLE = S.ID_SALLE
        WHERE EDT.ACTIF = TRUE
    """,
    "R_ABSENCE_ETUDIANT": """
        SELECT I.ID_INSCRIPTION, E.MATRICULE, E.NOM, E.PRENOM,
               C.LIBELLE AS CLASSE, SUM(A.NB_HEURES) AS TOTAL_HEURES,
               SUM(iif(A.JUSTIFIEE = TRUE, A.NB_HEURES, 0)) AS HEURES_JUSTIFIEES
        FROM ABSENCE AS A
        INNER JOIN INSCRIPTION AS I ON A.ID_INSCRIPTION = I.ID_INSCRIPTION
        INNER JOIN ETUDIANT AS E ON I.ID_ETUDIANT = E.ID_ETUDIANT
        INNER JOIN CLASSE AS C ON I.ID_CLASSE = C.ID_CLASSE
        GROUP BY I.ID_INSCRIPTION, E.MATRICULE, E.NOM, E.PRENOM, C.LIBELLE
    """,
}


def _ddl_for_table(table_name: str) -> str:
    catalog = TABLES[table_name]
    definitions = []
    for name, kind, _size, _nullable, autonumber in catalog["columns"]:
        sqlite_type = _KIND_TO_SQLITE.get(kind, "TEXT")
        if autonumber:
            sqlite_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
        definitions.append(f"[{name}] {sqlite_type}")
    primary_keys = [key for key in catalog["pk"]
                    if not any(name == key and autonumber
                               for name, _k, _s, _n, autonumber
                               in catalog["columns"])]
    if primary_keys:
        definitions.append("PRIMARY KEY (" + ", ".join(
            f"[{key}]" for key in primary_keys) + ")")
    return f"CREATE TABLE [{table_name}] (" + ", ".join(definitions) + ")"


def create_test_database(path: str,
                         extraction_json: Optional[str] = None) -> str:
    """Crée la base SQLite de test : 33 tables + données initiales + vues."""
    if os.path.exists(path):
        os.remove(path)
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        for table_name in TABLES:
            connection.execute(_ddl_for_table(table_name))
        # Données initiales réelles de LTA_ADM.accdb.
        if extraction_json is None:
            extraction_json = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "analysis", "extraction_complete.json")
        if os.path.isfile(extraction_json):
            with open(extraction_json, encoding="utf-8") as handle:
                extraction = json.load(handle)
            for table_name, rows in extraction.get("data", {}).items():
                if not rows or table_name.upper() not in TABLES:
                    continue
                columns = [c[0] for c in TABLES[table_name.upper()]["columns"]]
                for row in rows:
                    values = [row.get(column) for column in columns]
                    placeholders = ", ".join("?" * len(columns))
                    names = ", ".join(f"[{c}]" for c in columns)
                    try:
                        connection.execute(
                            f"INSERT INTO [{table_name}] ({names}) "
                            f"VALUES ({placeholders})", values)
                    except sqlite3.IntegrityError:
                        pass  # données d'extraction dupliquées : ignorer
        # Vues équivalant aux 8 requêtes enregistrées Access.
        for view_name, view_sql in SAVED_QUERY_VIEWS.items():
            connection.execute(f"CREATE VIEW [{view_name}] AS {view_sql}")
        connection.commit()
    finally:
        connection.close()
    return path


def create_test_services(path: str):
    """Base + composition de services prête pour les tests."""
    from ltadmin.data.access_database import AccessDatabase
    from ltadmin.services.app_composition import AppServices

    create_test_database(path)
    database = AccessDatabase(path, engine=SqliteEngine())
    database.open()
    return AppServices(database)
