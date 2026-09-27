"""Accès à la base SQLite ``LTA_ADM.sqlite3`` (module ``sqlite3`` standard).

Une seule connexion partagée, protégée par un verrou réentrant : le serveur
HTTP local est multi-threads mais les opérations (et surtout les
transactions) sont sérialisées, ce qui reproduit le modèle « une
application, une connexion » de l'ancienne version.

Conventions de stockage :

- dates/heures en texte ``AAAA-MM-JJ HH:MM:SS`` (comparables en SQL) ;
- booléens en entiers 0/1 ;
- montants (CURRENCY) en réels, convertis en ``Decimal`` par les dépôts ;
- SQL paramétré positionnel (``?``), identifiants protégés par ``[crochets]``.
"""

from __future__ import annotations

import datetime as _dt
import os
import sqlite3
import threading
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from ltadmin.data import schema_catalog
from ltadmin.data.schema import quote_identifier
from ltadmin.models.db_models import DbColumnInfo, DbTableInfo

DATABASE_FILE_NAME = "LTA_ADM.sqlite3"


def adapt_parameter(value: Any) -> Any:
    """Convertit une valeur Python en valeur acceptée par sqlite3."""
    if value is None or isinstance(value, (int, float, str, bytes)):
        return value
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, _dt.datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, _dt.date):
        return value.strftime("%Y-%m-%d") + " 00:00:00"
    if isinstance(value, _dt.time):
        return value.strftime("%H:%M")
    return str(value)


def _declared_kind(declared_type: str) -> str:
    text = (declared_type or "").upper()
    if "INT" in text:
        return "LONG"
    if "BOOL" in text:
        return "BOOLEAN"
    if "DATE" in text or "TIME" in text:
        return "DATETIME"
    if "REAL" in text or "DOUB" in text or "FLOA" in text or "NUM" in text:
        return "DOUBLE"
    if "CURR" in text or "MONEY" in text:
        return "CURRENCY"
    if text == "TEXT" or "CLOB" in text or "MEMO" in text:
        return "MEMO"
    if "BLOB" in text:
        return "BINARY"
    return "TEXT"


def _declared_size(declared_type: str) -> int:
    text = declared_type or ""
    if "(" in text and text.endswith(")"):
        try:
            return int(text[text.index("(") + 1:-1])
        except ValueError:
            return 0
    return 0


class Database:
    """Connexion unique SQLite + transactions + métadonnées + sauvegarde."""

    def __init__(self, database_path: str):
        self.database_path = os.path.abspath(database_path)
        self._connection: Optional[sqlite3.Connection] = None
        self._lock = threading.RLock()
        self._in_transaction = False
        self._disposed = False

    # ----- État -----

    @property
    def is_open(self) -> bool:
        return self._connection is not None

    @property
    def in_transaction(self) -> bool:
        return self._in_transaction

    @property
    def lock(self) -> threading.RLock:
        return self._lock

    def _ensure_connection(self) -> sqlite3.Connection:
        if self._disposed:
            raise RuntimeError("La connexion à la base a été fermée.")
        if self._connection is None:
            self.open()
        assert self._connection is not None
        return self._connection

    # ----- Ouverture / fermeture -----

    def open(self) -> None:
        with self._lock:
            if self._disposed:
                raise RuntimeError("La connexion à la base a été fermée.")
            if self.is_open:
                return
            if not os.path.exists(self.database_path):
                raise FileNotFoundError(
                    "La base de données est introuvable : " + self.database_path)
            connection = sqlite3.connect(
                self.database_path, check_same_thread=False, timeout=10,
                isolation_level=None)  # autocommit ; BEGIN/COMMIT explicites
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 5000")
            connection.create_function("UCASE", 1, _ucase)
            connection.create_function("LCASE", 1, _lcase)
            connection.create_function("CStr", 1, _cstr)
            self._connection = connection

    def close(self) -> None:
        with self._lock:
            if self.in_transaction:
                raise RuntimeError(
                    "Impossible de fermer la connexion pendant une transaction. "
                    "Validez ou annulez d’abord la transaction.")
            if self._connection is None:
                return
            connection, self._connection = self._connection, None
            connection.close()

    def dispose(self) -> None:
        with self._lock:
            if self._disposed:
                return
            if self.in_transaction:
                self._rollback_internal()
            try:
                self.close()
            except Exception:
                pass
            self._disposed = True

    # ----- Transactions -----

    def begin_transaction(self) -> "_TransactionScope":
        """``with db.begin_transaction(): ...`` — commit en sortie normale, rollback sur exception."""
        return _TransactionScope(self)

    def _begin_internal(self) -> None:
        self._lock.acquire()
        try:
            if self._in_transaction:
                raise RuntimeError(
                    "Une transaction est déjà en cours. Les transactions imbriquées "
                    "ne sont pas prises en charge.")
            self._ensure_connection().execute("BEGIN")
            self._in_transaction = True
        except Exception:
            self._lock.release()
            raise

    def _commit_internal(self) -> None:
        try:
            if self._connection is not None:
                self._connection.execute("COMMIT")
        finally:
            self._in_transaction = False
            self._lock.release()

    def _rollback_internal(self) -> None:
        try:
            if self._connection is not None:
                self._connection.execute("ROLLBACK")
        except sqlite3.OperationalError:
            pass
        finally:
            self._in_transaction = False
            self._lock.release()

    # ----- Exécution -----

    def _execute(self, sql: str, parameters: Optional[Sequence[Any]]) -> sqlite3.Cursor:
        connection = self._ensure_connection()
        params = [adapt_parameter(p) for p in (parameters or [])]
        return connection.execute(sql, params)

    def query(self, sql: str, parameters: Optional[Sequence[Any]] = None) -> List[Dict[str, Any]]:
        """Exécute un SELECT et retourne les lignes sous forme de dictionnaires."""
        with self._lock:
            cursor = self._execute(sql, parameters)
            try:
                columns = [d[0] for d in (cursor.description or [])]
                rows: List[Dict[str, Any]] = []
                for row in cursor.fetchall():
                    record: Dict[str, Any] = {}
                    for name, value in zip(columns, row):
                        if name not in record:  # colonne dupliquée → la première
                            record[name] = value
                    rows.append(record)
                return rows
            finally:
                cursor.close()

    def scalar(self, sql: str, parameters: Optional[Sequence[Any]] = None) -> Any:
        rows = self.query(sql, parameters)
        if not rows:
            return None
        for value in rows[0].values():
            return value
        return None

    def execute(self, sql: str, parameters: Optional[Sequence[Any]] = None) -> int:
        """INSERT/UPDATE/DELETE : retourne le nombre de lignes affectées."""
        with self._lock:
            cursor = self._execute(sql, parameters)
            try:
                return cursor.rowcount if cursor.rowcount is not None else 0
            finally:
                cursor.close()

    def insert_and_get_id(self, sql: str, parameters: Optional[Sequence[Any]] = None) -> int:
        """INSERT puis identifiant auto-généré (``lastrowid``)."""
        with self._lock:
            cursor = self._execute(sql, parameters)
            try:
                return int(cursor.lastrowid or 0)
            finally:
                cursor.close()

    def execute_script(self, script: str) -> None:
        with self._lock:
            self._ensure_connection().executescript(script)

    # ----- Métadonnées -----

    def list_table_names(self) -> List[str]:
        with self._lock:
            rows = self._ensure_connection().execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
            return [r[0] for r in rows]

    def list_view_names(self) -> List[str]:
        with self._lock:
            rows = self._ensure_connection().execute(
                "SELECT name FROM sqlite_master WHERE type = 'view' ORDER BY name").fetchall()
            return [r[0] for r in rows]

    def get_tables(self) -> List[DbTableInfo]:
        tables: List[DbTableInfo] = []
        for name in self.list_table_names():
            try:
                tables.append(self.get_table(name))
            except Exception:
                continue
        order = {n.upper(): i for i, n in enumerate(_PREFERRED_TABLE_ORDER)}
        tables.sort(key=lambda t: (order.get(t.name.upper(), 1000), t.name.upper()))
        return tables

    def get_table(self, table_name: str) -> DbTableInfo:
        """Colonnes d'une table : PRAGMA table_info croisé avec le catalogue statique."""
        static = schema_catalog.TABLES.get(table_name.upper())
        static_columns = {}
        if static is not None:
            for name, kind, size, nullable, autonumber in static["columns"]:
                static_columns[name.upper()] = (name, kind, size, nullable, autonumber)
        with self._lock:
            rows = self._ensure_connection().execute(
                f"PRAGMA table_info({quote_identifier(table_name)})").fetchall()
        if not rows:
            raise RuntimeError("Table introuvable : " + table_name)
        table = DbTableInfo(name=table_name)
        pk_columns = {row[1].upper() for row in rows if row[5]}
        for cid, name, declared, notnull, _default, pk in rows:
            known = static_columns.get(name.upper())
            if known is not None:
                _n, kind, size, nullable, autonumber = known
            else:
                kind = _declared_kind(declared)
                size = _declared_size(declared)
                nullable = not notnull
                autonumber = False
            is_pk = name.upper() in pk_columns
            if is_pk and (declared or "").upper().startswith("INTEGER") and len(pk_columns) == 1:
                autonumber = True
            table.columns.append(DbColumnInfo(
                name=name, kind=kind, size=size, nullable=nullable,
                autonumber=autonumber, ordinal=cid, is_primary_key=is_pk))
        table.columns.sort(key=lambda c: c.ordinal)
        return table

    # ----- Sauvegarde fichier -----

    def create_backup(self, destination: Optional[str] = None) -> str:
        """Copie cohérente de la base (API de sauvegarde SQLite, base ouverte ou non)."""
        if self._disposed:
            raise RuntimeError("La connexion à la base a été fermée.")
        with self._lock:
            if self.in_transaction:
                raise RuntimeError("Impossible de sauvegarder pendant une transaction.")
            if destination is None:
                folder = os.path.join(
                    os.path.dirname(self.database_path) or os.getcwd(), "Sauvegardes")
                os.makedirs(folder, exist_ok=True)
                base = os.path.splitext(os.path.basename(self.database_path))[0]
                destination = os.path.join(
                    folder, "{}_{:%Y%m%d_%H%M%S}.sqlite3".format(base, _dt.datetime.now()))
            source = self._ensure_connection()
            target = sqlite3.connect(destination)
            try:
                source.backup(target)
            finally:
                target.close()
            return destination

    # ----- Helpers statiques (compatibilité) -----

    @staticmethod
    def quote(identifier: str) -> str:
        return quote_identifier(identifier)

    @staticmethod
    def parameter(value: Any) -> Any:
        return value


class _TransactionScope:

    def __init__(self, database: Database):
        self._database = database
        self._active = False

    def __enter__(self) -> "_TransactionScope":
        self._database._begin_internal()
        self._active = True
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        if not self._active:
            return False
        self._active = False
        if exc_type is None:
            self._database._commit_internal()
        else:
            self._database._rollback_internal()
        return False

    def complete(self) -> None:
        """Validation explicite anticipée."""
        if self._active and self._database.in_transaction:
            self._active = False
            self._database._commit_internal()


def _ucase(value):
    return value.upper() if isinstance(value, str) else value


def _lcase(value):
    return value.lower() if isinstance(value, str) else value


def _cstr(value):
    if value is None:
        return ""
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value)


_PREFERRED_TABLE_ORDER = (
    "ETUDIANT", "INSCRIPTION", "FORMATEUR", "FILIERE", "NIVEAU", "CLASSE",
    "MATIERE", "MODULE_FORMATION", "SALLE", "PROGRAMME", "PERIODE_EVAL",
    "EVALUATION", "NOTE", "EMPLOI_DU_TEMPS", "CRENEAU", "SEANCE", "ABSENCE",
    "SESSION_EXAM", "EPREUVE", "NOTE_EXAMEN", "RESULTAT_FINAL", "BULLETIN",
    "BULLETIN_LIGNE", "GRILLE_MENTION", "TARIF", "ECHEANCIER", "PAIEMENT",
    "PAIE_FORMATEUR", "UTILISATEUR", "PARAMETRE", "ETABLISSEMENT",
    "ANNEE_SCOLAIRE", "JOURNAL",
)
