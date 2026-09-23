"""Accès générique aux tables : moteur de la maintenance générique.

Les écrans métier utilisent les dépôts typés via les services ; cette classe
sert à la maintenance de toutes les tables (réservée aux profils habilités)
et aux états bruts.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ltadmin.data.access_database import AccessDatabase
from ltadmin.data.schema import quote_identifier
from ltadmin.models.db_models import DbTableInfo

# Types texte recherchables (recherche générique dans la maintenance).
_TEXT_KINDS = {"TEXT", "MEMO"}


class DatabaseRepository:

    def __init__(self, database: AccessDatabase):
        self._database = database

    def get_tables(self) -> List[DbTableInfo]:
        return self._database.get_tables()

    def get_saved_queries(self) -> List[str]:
        """Requêtes enregistrées connues (les R_* livrées avec la base)."""
        return sorted({
            "R_LISTE_ETUDIANT",
            "R_MOYENNE_MATIERE",
            "R_MOYENNE_PERIODE",
            "R_BULLETIN_DETAIL",
            "R_PAIEMENT_ECHEANCE",
            "R_SITUATION_ECOLAGE",
            "R_EDT_CLASSE",
            "R_ABSENCE_ETUDIANT",
        })

    def load_saved_query(self, query_name: str) -> List[dict]:
        return self._database.query(f"SELECT * FROM {quote_identifier(query_name)}")

    def load_table(self, table: DbTableInfo, search: Optional[str] = None,
                   max_rows: int = 1000) -> List[dict]:
        max_rows = max(1, min(max_rows, 10000))
        sql = f"SELECT TOP {max_rows} * FROM {quote_identifier(table.name)}"
        parameters: List[Any] = []
        text_columns = [c for c in table.columns
                        if c.kind in _TEXT_KINDS and not c.is_binary]
        if search and search.strip() and text_columns:
            sql += " WHERE " + " OR ".join(
                f"CStr({quote_identifier(c.name)}) LIKE ?" for c in text_columns)
            motif = "%" + search.strip() + "%"
            parameters.extend([motif] * len(text_columns))
        order_column = (table.primary_key_columns or [None])[0] or (
            table.columns[0] if table.columns else None)
        sql += " ORDER BY " + (quote_identifier(order_column.name) if order_column else "1")
        return self._database.query(sql, parameters)

    def insert(self, table: DbTableInfo, values: Dict[str, Any]) -> int:
        columns = [c for c in table.columns
                   if not c.autonumber and not c.is_binary
                   and _has_key(values, c.name)]
        if not columns:
            return 0
        sql = (f"INSERT INTO {quote_identifier(table.name)} "
               + "(" + ", ".join(quote_identifier(c.name) for c in columns) + ") "
               + "VALUES (" + ", ".join(["?"] * len(columns)) + ")")
        return self._database.execute(sql, [_get(values, c.name) for c in columns])

    def update(self, table: DbTableInfo, original_row: Dict[str, Any],
               values: Dict[str, Any]) -> int:
        columns = [c for c in table.columns
                   if not c.autonumber and not c.is_binary and not c.is_primary_key
                   and _has_key(values, c.name)]
        if not columns:
            return 0
        predicates, where_parameters = self._build_row_predicates(table, original_row)
        sql = (f"UPDATE {quote_identifier(table.name)} SET "
               + ", ".join(f"{quote_identifier(c.name)} = ?" for c in columns)
               + " WHERE " + predicates)
        parameters = [_get(values, c.name) for c in columns] + where_parameters
        return self._database.execute(sql, parameters)

    def delete(self, table: DbTableInfo, row: Dict[str, Any]) -> int:
        predicates, parameters = self._build_row_predicates(table, row)
        return self._database.execute(
            f"DELETE FROM {quote_identifier(table.name)} WHERE {predicates}", parameters)

    def count(self, table: DbTableInfo) -> int:
        value = self._database.scalar(f"SELECT COUNT(*) FROM {quote_identifier(table.name)}")
        return 0 if value is None else int(value)

    def recent_rows(self, table: DbTableInfo, count: int = 8) -> List[dict]:
        count = max(1, min(count, 100))
        order = None
        for column in table.columns:
            if "DATE" in column.name.upper():
                order = column
                break
        if order is None:
            order = (table.primary_key_columns or [None])[0] or (
                table.columns[0] if table.columns else None)
        sql = f"SELECT TOP {count} * FROM {quote_identifier(table.name)}"
        if order is not None:
            sql += f" ORDER BY {quote_identifier(order.name)} DESC"
        return self._database.query(sql)

    @staticmethod
    def _build_row_predicates(table: DbTableInfo, row: Dict[str, Any]):
        parameters: List[Any] = []
        key_columns = table.primary_key_columns
        columns = key_columns if key_columns else [c for c in table.columns if not c.is_binary]
        if not columns:
            raise RuntimeError("Cette table ne possède aucune colonne exploitable.")
        predicates = []
        for column in columns:
            value = row.get(column.name)
            if value is None:
                predicates.append(f"{quote_identifier(column.name)} IS NULL")
            else:
                predicates.append(f"{quote_identifier(column.name)} = ?")
                parameters.append(value)
        return " AND ".join(predicates), parameters


def _has_key(values: Dict[str, Any], name: str) -> bool:
    if name in values:
        return True
    upper = name.upper()
    return any(k.upper() == upper for k in values)


def _get(values: Dict[str, Any], name: str) -> Any:
    if name in values:
        return values[name]
    upper = name.upper()
    for key, value in values.items():
        if key.upper() == upper:
            return value
    return None
