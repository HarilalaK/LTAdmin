"""Adaptateur Access. La base reste le fichier LTA_ADM.accdb existant :
aucune migration, aucune recréation de table, aucune modification de données
sans action explicite d'un service.

Le SQL est en dialecte ACE (paramètres positionnels ``?``, identifiants entre
crochets, ``TOP``, ``SELECT @@IDENTITY``) et s'exécute via pyodbc sur le
pilote « Microsoft Access Driver (*.mdb, *.accdb) » installé avec
Office/ACE. Le moteur d'exécution est injectable, ce qui permet de tester
toute l'application hors Windows avec un moteur alternatif (voir tests/).
"""

from __future__ import annotations

import datetime as _dt
import os
import shutil
from typing import Any, Dict, Iterable, List, Optional, Sequence

from ltadmin.data import schema_catalog
from ltadmin.data.schema import quote_identifier
from ltadmin.models.db_models import DbColumnInfo, DbTableInfo

# Pilotes ODBC Access connus, par ordre de préférence (ACE 16 puis ACE 12,
# variantes FR). Le pilote doit avoir la même architecture (32/64 bits) que
# Python.
_ACCESS_DRIVERS = (
    "Microsoft Access Driver (*.mdb, *.accdb)",
    "Driver do Microsoft Access (*.mdb, *.accdb)",
    "Microsoft Access Driver (*.mdb)",
    "Driver do Microsoft Access (*.mdb)",
)


def _as_params(parameters: Optional[Sequence[Any]]) -> List[Any]:
    if parameters is None:
        return []
    return [p for p in parameters]


class PyodbcEngine:
    """Moteur de production : pyodbc + pilote ODBC Microsoft Access.

    Interface minimale attendue par :class:`AccessDatabase` :
    ``open``, ``close``, ``fetch_all``, ``execute``, ``insert_and_get_id``,
    ``begin``, ``commit``, ``rollback``, ``list_tables``, ``list_columns``.
    """

    def _connect_string(self, driver: str, path: str) -> str:
        return f"DRIVER={{{driver}}};DBQ={path};"

    def open(self, path: str):
        import pyodbc  # import différé : permet les tests sans pyodbc

        errors: List[str] = []
        for driver in _ACCESS_DRIVERS:
            try:
                return pyodbc.connect(
                    self._connect_string(driver, path), timeout=10, autocommit=True
                )
            except Exception as ex:  # pilote absent ou architecture différente
                errors.append(f"{driver} : {ex}")
        raise RuntimeError(
            "Le pilote ODBC Microsoft Access (ACE) n’est pas disponible ou son "
            "architecture ne correspond pas à celle de Python.\n\n"
            "Installez le « Microsoft Access Database Engine 2016 Redistributable » "
            "dans la même architecture que Python (64 bits avec un Python 64 bits), "
            "puis relancez LTAdmin.\n\n" + "\n".join(errors)
        )

    def close(self, connection) -> None:
        connection.close()

    def _cursor_execute(self, connection, sql: str, params: Sequence[Any]):
        cursor = connection.cursor()
        try:
            if params:
                cursor.execute(sql, list(params))
            else:
                cursor.execute(sql)
            return cursor
        except Exception:
            cursor.close()
            raise

    def fetch_all(self, connection, sql: str, params: Sequence[Any]) -> List[Dict[str, Any]]:
        cursor = self._cursor_execute(connection, sql, params)
        try:
            columns = [d[0] for d in (cursor.description or [])]
            rows: List[Dict[str, Any]] = []
            for row in cursor.fetchall():
                # Premier-gagnant : reproduit DataTable (colonne dupliquée → la 1re).
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

    def insert_and_get_id(self, connection, sql: str, params: Sequence[Any]) -> int:
        cursor = self._cursor_execute(connection, sql, params)
        try:
            cursor.execute("SELECT @@IDENTITY")
            row = cursor.fetchone()
            if row is None or row[0] is None:
                return 0
            return int(row[0])
        finally:
            cursor.close()

    def begin(self, connection) -> None:
        connection.autocommit = False

    def commit(self, connection) -> None:
        connection.commit()
        connection.autocommit = True

    def rollback(self, connection) -> None:
        try:
            connection.rollback()
        finally:
            connection.autocommit = True

    def list_tables(self, connection) -> List[str]:
        cursor = connection.cursor()
        try:
            names = []
            for row in cursor.tables(tableType="TABLE"):
                name = row.table_name
                if name and not name.upper().startswith(("MSYS", "F_")):
                    names.append(str(name))
            return names
        finally:
            cursor.close()

    # Codes de type ODBC → kinds internes (TEXT, LONG, DOUBLE, CURRENCY…).
    _ODBC_KINDS = {
        2: "CURRENCY",
        3: "CURRENCY",
        4: "LONG",
        5: "LONG",
        -5: "LONG",
        6: "DOUBLE",
        7: "DOUBLE",
        8: "DOUBLE",
        11: "DATETIME",
        9: "DATETIME",
        93: "DATETIME",
        12: "TEXT",
        1: "TEXT",
        -8: "TEXT",
        -1: "MEMO",
        -10: "MEMO",
        -7: "BOOLEAN",
        -2: "BINARY",
        -3: "BINARY",
        -4: "BINARY",
    }

    def list_columns(self, connection, table: str) -> List[DbColumnInfo]:
        cursor = connection.cursor()
        try:
            columns: List[DbColumnInfo] = []
            for row in cursor.columns(table=table):
                name = row.column_name
                if not name:
                    continue
                type_code = int(row.data_type or 12)
                type_name = str(row.type_name or "").upper()
                kind = "COUNTER" if type_name == "COUNTER" else self._ODBC_KINDS.get(type_code, "TEXT")
                size = int(row.column_size or 0)
                is_nullable = str(row.is_nullable or "YES").upper() == "YES"
                ordinal = int(row.ordinal_position or 0)
                columns.append(
                    DbColumnInfo(
                        name=str(name),
                        kind=kind,
                        size=size,
                        nullable=is_nullable,
                        autonumber=kind == "COUNTER",
                        ordinal=ordinal,
                    )
                )
            columns.sort(key=lambda c: c.ordinal)
            return columns
        finally:
            cursor.close()


class AccessDatabase:
    """Connexion unique à la base Access + transactions + sauvegarde fichier."""

    def __init__(self, database_path: str, engine: Optional[Any] = None):
        self.database_path = os.path.abspath(database_path)
        self._engine = engine if engine is not None else PyodbcEngine()
        self._connection: Optional[Any] = None
        self._in_transaction = False
        self._disposed = False

    # ----- État -----

    @property
    def is_open(self) -> bool:
        return self._connection is not None

    @property
    def in_transaction(self) -> bool:
        return self._in_transaction

    def _ensure_connection(self):
        if self._disposed:
            raise RuntimeError("La connexion à la base a été fermée.")
        if self._connection is None:
            self.open()
        return self._connection

    # ----- Ouverture / fermeture -----

    def open(self) -> None:
        if self._disposed:
            raise RuntimeError("La connexion à la base a été fermée.")
        if self.is_open:
            return
        if not os.path.exists(self.database_path):
            raise FileNotFoundError("La base Access est introuvable : " + self.database_path)
        self._connection = self._engine.open(self.database_path)

    def close(self) -> None:
        if self.in_transaction:
            raise RuntimeError(
                "Impossible de fermer la connexion pendant une transaction. "
                "Validez ou annulez d’abord la transaction."
            )
        if self._connection is None:
            return
        connection, self._connection = self._connection, None
        try:
            self._engine.close(connection)
        except Exception:
            self._connection = None
            raise

    # ----- Transactions -----

    def begin_transaction(self) -> "_TransactionScope":
        """Portée de transaction : ``with db.begin_transaction(): ...`` valide en sortie normale, annule sur exception."""
        return _TransactionScope(self)

    def _begin_internal(self) -> None:
        if self._disposed:
            raise RuntimeError("La connexion à la base a été fermée.")
        if self._in_transaction:
            raise RuntimeError(
                "Une transaction est déjà en cours. Les transactions imbriquées "
                "ne sont pas prises en charge."
            )
        self._ensure_connection()
        self._engine.begin(self._connection)
        self._in_transaction = True

    def _commit_internal(self) -> None:
        try:
            if self._connection is not None:
                self._engine.commit(self._connection)
        finally:
            self._in_transaction = False

    def _rollback_internal(self) -> None:
        try:
            if self._connection is not None:
                self._engine.rollback(self._connection)
        except Exception:
            # Un rollback en échec ne doit pas masquer l'erreur d'origine.
            pass
        finally:
            self._in_transaction = False

    # ----- Exécution -----

    def query(self, sql: str, parameters: Optional[Sequence[Any]] = None) -> List[Dict[str, Any]]:
        """Exécute un SELECT et retourne les lignes (dictionnaires ordonnés)."""
        return self._engine.fetch_all(self._ensure_connection(), sql, _as_params(parameters))

    def scalar(self, sql: str, parameters: Optional[Sequence[Any]] = None) -> Any:
        """Retourne la première colonne de la première ligne, ou None."""
        rows = self.query(sql, parameters)
        if not rows:
            return None
        first = rows[0]
        for value in first.values():
            return value
        return None

    def execute(self, sql: str, parameters: Optional[Sequence[Any]] = None) -> int:
        """Exécute un INSERT/UPDATE/DELETE et retourne le nombre de lignes."""
        return self._engine.execute(self._ensure_connection(), sql, _as_params(parameters))

    def insert_and_get_id(self, sql: str, parameters: Optional[Sequence[Any]] = None) -> int:
        """INSERT puis SELECT @@IDENTITY sur la même connexion (AutoNumber)."""
        return self._engine.insert_and_get_id(
            self._ensure_connection(), sql, _as_params(parameters)
        )

    # ----- Métadonnées -----

    def get_tables(self) -> List[DbTableInfo]:
        """Liste les tables (ordre métier) avec leurs colonnes."""
        tables: List[DbTableInfo] = []
        try:
            names = self._engine.list_tables(self._ensure_connection())
        except Exception:
            names = list(schema_catalog.TABLES.keys())
        for name in names:
            try:
                tables.append(self.get_table(name))
            except Exception:
                # Un objet système mal formé ne doit pas masquer les autres tables.
                continue

        order = {n.upper(): i for i, n in enumerate(_PREFERRED_TABLE_ORDER)}
        tables.sort(key=lambda t: (order.get(t.name.upper(), 1000), t.name.upper()))
        return tables

    def get_table(self, table_name: str) -> DbTableInfo:
        """Colonnes d'une table : catalogue statique croisé avec le pilote ODBC."""
        static = schema_catalog.TABLES.get(table_name.upper())
        columns: Dict[str, DbColumnInfo] = {}
        if static is not None:
            for name, kind, size, nullable, autonumber in static["columns"]:
                columns[name.upper()] = DbColumnInfo(
                    name=name, kind=kind, size=size, nullable=nullable, autonumber=autonumber
                )
        try:
            # Le pilote voit les tables ajoutées manuellement dans Access :
            # ses informations remplissent les trous et confirment AutoNumber.
            for column in self._engine.list_columns(self._ensure_connection(), table_name):
                existing = columns.get(column.name.upper())
                if existing is None:
                    columns[column.name.upper()] = column
                else:
                    existing.ordinal = column.ordinal
                    if column.kind != "TEXT" or existing.kind == "TEXT":
                        # On garde le kind statique (plus fiable) sauf s'il est
                        # un TEXT générique alors que le pilote sait mieux.
                        if existing.kind == "TEXT" and column.kind in (
                            "COUNTER",
                            "BOOLEAN",
                            "DATETIME",
                            "CURRENCY",
                            "MEMO",
                            "DOUBLE",
                            "LONG",
                        ):
                            existing.kind = column.kind
                    if column.autonumber:
                        existing.autonumber = True
        except Exception:
            if static is None:
                raise RuntimeError("Table introuvable : " + table_name)

        if not columns:
            raise RuntimeError("Table introuvable : " + table_name)

        table = DbTableInfo(name=table_name)
        table.columns = sorted(columns.values(), key=lambda c: c.ordinal)
        primary_keys = set(static["pk"]) if static else set()
        if not primary_keys:
            # Repli heuristique pour les tables inconnues : première colonne
            # nommée ID_* / ID, sinon première colonne.
            for column in table.columns:
                if column.name.upper().startswith("ID_") or column.name.upper() == "ID":
                    primary_keys = {column.name}
                    break
            if not primary_keys and table.columns:
                primary_keys = {table.columns[0].name}
        for column in table.columns:
            if column.name in primary_keys:
                column.is_primary_key = True
                # Access omet parfois AutoNumber : clé ID_* LONG → AutoNumber.
                if column.name.upper().startswith("ID_") and column.kind == "LONG":
                    column.autonumber = True
        return table

    # ----- Sauvegarde fichier -----

    def create_backup(self) -> str:
        if self._disposed:
            raise RuntimeError("La connexion à la base a été fermée.")
        if self.in_transaction:
            raise RuntimeError("Impossible de sauvegarder pendant une transaction.")
        folder = os.path.join(
            os.path.dirname(self.database_path) or os.getcwd(), "Sauvegardes"
        )
        os.makedirs(folder, exist_ok=True)
        destination = os.path.join(
            folder,
            "LTA_ADM_{:%Y%m%d_%H%M%S}.accdb".format(_dt.datetime.now()),
        )
        was_open = self.is_open
        self.close()
        try:
            shutil.copyfile(self.database_path, destination)
            return destination
        finally:
            if was_open:
                self.open()

    def dispose(self) -> None:
        if self._disposed:
            return
        if self.in_transaction:
            self._rollback_internal()
        try:
            self.close()
        except Exception:
            pass
        self._disposed = True

    # ----- Helpers statiques (compatibilité portage) -----

    @staticmethod
    def quote(identifier: str) -> str:
        return quote_identifier(identifier)

    @staticmethod
    def parameter(value: Any) -> Any:
        """Équivalent d'OleDbParameter : None devient NULL côté pilote."""
        return value


class _TransactionScope:
    """Portée de transaction : commit à la sortie normale, rollback sur exception."""

    def __init__(self, database: AccessDatabase):
        self._database = database

    def __enter__(self) -> "_TransactionScope":
        self._database._begin_internal()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        if exc_type is None:
            self._database._commit_internal()
        else:
            self._database._rollback_internal()
        return False

    def complete(self) -> None:
        """Validation explicite anticipée (équivalent tx.Complete())."""
        if self._database.in_transaction:
            self._database._commit_internal()


_PREFERRED_TABLE_ORDER = (
    "ETUDIANT",
    "INSCRIPTION",
    "FORMATEUR",
    "FILIERE",
    "NIVEAU",
    "CLASSE",
    "MATIERE",
    "MODULE_FORMATION",
    "SALLE",
    "PROGRAMME",
    "PERIODE_EVAL",
    "EVALUATION",
    "NOTE",
    "EMPLOI_DU_TEMPS",
    "CRENEAU",
    "SEANCE",
    "ABSENCE",
    "SESSION_EXAM",
    "EPREUVE",
    "NOTE_EXAMEN",
    "RESULTAT_FINAL",
    "BULLETIN",
    "BULLETIN_LIGNE",
    "TARIF",
    "ECHEANCIER",
    "PAIEMENT",
    "PAIE_FORMATEUR",
    "UTILISATEUR",
    "PARAMETRE",
    "ETABLISSEMENT",
    "ANNEE_SCOLAIRE",
    "JOURNAL",
)
