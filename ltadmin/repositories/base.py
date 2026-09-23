"""Base des dépôts typés : helpers d'accès et de lecture.

Aucune règle métier ici : uniquement l'accès aux données. Toutes les
requêtes sont paramétrées (jamais de concaténation de valeurs).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Callable, List, Optional, Sequence

from ltadmin.data.access_database import AccessDatabase
from ltadmin.data.schema import quote_identifier


def q(identifier: str) -> str:
    """Protège un identifiant SQL Access par des crochets."""
    return quote_identifier(identifier)


def p(value: Any) -> Any:
    """Paramètre positionnel (None → NULL)."""
    return value


class RepositoryBase:
    """Helpers communs aux dépôts."""

    def __init__(self, database: AccessDatabase):
        self.db = database

    # ----- Lectures -----

    def query_list(self, sql: str, mapper: Callable[[dict], Any],
                   parameters: Optional[Sequence[Any]] = None) -> List[Any]:
        return [mapper(row) for row in self.db.query(sql, parameters)]

    def query_single(self, sql: str, mapper: Callable[[dict], Any],
                     parameters: Optional[Sequence[Any]] = None) -> Optional[Any]:
        rows = self.db.query(sql, parameters)
        if not rows:
            return None
        return mapper(rows[0])

    def query_table(self, sql: str, parameters: Optional[Sequence[Any]] = None) -> List[dict]:
        return self.db.query(sql, parameters)

    # ----- Écritures -----

    def insert_and_get_id(self, sql: str, parameters: Optional[Sequence[Any]] = None) -> int:
        return self.db.insert_and_get_id(sql, parameters)

    def execute(self, sql: str, parameters: Optional[Sequence[Any]] = None) -> int:
        return self.db.execute(sql, parameters)

    # ----- Scalaires -----

    def scalar_int(self, sql: str, parameters: Optional[Sequence[Any]] = None) -> int:
        value = self.db.scalar(sql, parameters)
        if value is None:
            return 0
        try:
            return int(value)
        except (TypeError, ValueError):
            try:
                return int(float(value))
            except (TypeError, ValueError):
                return 0

    def scalar_decimal(self, sql: str, parameters: Optional[Sequence[Any]] = None) -> Optional[Decimal]:
        value = self.db.scalar(sql, parameters)
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return None

    def scalar_double(self, sql: str, parameters: Optional[Sequence[Any]] = None) -> Optional[float]:
        value = self.db.scalar(sql, parameters)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def scalar_string(self, sql: str, parameters: Optional[Sequence[Any]] = None) -> Optional[str]:
        value = self.db.scalar(sql, parameters)
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return str(value)

    def exists(self, sql: str, parameters: Optional[Sequence[Any]] = None) -> bool:
        return self.scalar_int(sql, parameters) > 0
