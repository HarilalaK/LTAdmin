"""Lecture défensive des lignes issues de la base.

Les colonnes absentes et les valeurs NULL sont converties en valeurs par
défaut au lieu de lever des exceptions (portage du DataRowMapper C#).
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Optional

_TRUE = {"1", "YES", "TRUE", "VRAI", "-1"}
_FALSE = {"0", "NO", "FALSE", "FAUX", "0.0"}


def has_column(row: Mapping[str, Any], column: str) -> bool:
    return column in row


def get_string(row: Mapping[str, Any], column: str) -> Optional[str]:
    if column not in row or row[column] is None:
        return None
    value = row[column]
    if isinstance(value, str):
        return value
    if isinstance(value, _dt.datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, _dt.date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def get_string_or(row: Mapping[str, Any], column: str, default: str) -> str:
    value = get_string(row, column)
    return default if value is None else value


def get_int(row: Mapping[str, Any], column: str) -> Optional[int]:
    value = row.get(column)
    if value is None:
        return None
    try:
        if isinstance(value, bool):
            return int(value)
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None


def get_int_or(row: Mapping[str, Any], column: str, default: int) -> int:
    value = get_int(row, column)
    return default if value is None else value


def get_double(row: Mapping[str, Any], column: str) -> Optional[float]:
    value = row.get(column)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_double_or(row: Mapping[str, Any], column: str, default: float) -> float:
    value = get_double(row, column)
    return default if value is None else value


def get_decimal(row: Mapping[str, Any], column: str) -> Optional[Decimal]:
    value = row.get(column)
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def get_decimal_or(row: Mapping[str, Any], column: str, default: Decimal) -> Decimal:
    value = get_decimal(row, column)
    return default if value is None else value


def get_bool(row: Mapping[str, Any], column: str) -> Optional[bool]:
    value = row.get(column)
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, Decimal):
        return value != 0
    if isinstance(value, str):
        text = value.strip().upper()
        if text in _TRUE:
            return True
        if text in _FALSE:
            return False
    return None


def get_bool_or(row: Mapping[str, Any], column: str, default: bool) -> bool:
    value = get_bool(row, column)
    return default if value is None else value


def get_datetime(row: Mapping[str, Any], column: str) -> Optional[_dt.datetime]:
    value = row.get(column)
    if value is None:
        return None
    if isinstance(value, _dt.datetime):
        return value
    if isinstance(value, _dt.date):
        return _dt.datetime(value.year, value.month, value.day)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y",
        ):
            try:
                return _dt.datetime.strptime(text, fmt)
            except ValueError:
                continue
    return None
