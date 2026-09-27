"""Conversion JSON ⇄ objets métier (dataclasses, Decimal, datetime).

- Sortie : dataclasses → dictionnaires, ``Decimal`` → nombre, ``datetime`` →
  ``AAAA-MM-JJTHH:MM:SS`` (``AAAA-MM-JJ`` si l'heure est nulle), ``date`` →
  ``AAAA-MM-JJ``. Les propriétés calculées ``nom_complet`` sont ajoutées.
- Entrée : :func:`parse_entity` construit une dataclass à partir d'un
  dictionnaire JSON en convertissant chaque champ selon son annotation
  (``int``, ``float``, ``bool``, ``Decimal``, ``datetime``), les chaînes
  vides devenant ``None``.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import json
import typing
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Mapping, Optional, Type, TypeVar

T = TypeVar("T")

_DATE_FORMATS = (
    "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y",
)


# ---------------------------------------------------------------------------
# Sortie
# ---------------------------------------------------------------------------


def to_jsonable(value: Any) -> Any:
    """Convertit récursivement une valeur en structure sérialisable JSON."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        return float(value)
    if isinstance(value, _dt.datetime):
        if value.hour == 0 and value.minute == 0 and value.second == 0:
            return value.strftime("%Y-%m-%d")
        return value.strftime("%Y-%m-%dT%H:%M:%S")
    if isinstance(value, _dt.date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, _dt.time):
        return value.strftime("%H:%M")
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        result: Dict[str, Any] = {}
        for field in dataclasses.fields(value):
            result[field.name] = to_jsonable(getattr(value, field.name))
        # Propriétés calculées utiles à l'affichage.
        for extra in ("nom_complet",):
            if hasattr(type(value), extra):
                try:
                    result[extra] = to_jsonable(getattr(value, extra))
                except Exception:
                    pass
        return result
    if isinstance(value, Mapping):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_jsonable(v) for v in value]
    return str(value)


def dumps(value: Any) -> str:
    return json.dumps(to_jsonable(value), ensure_ascii=False)


# ---------------------------------------------------------------------------
# Entrée
# ---------------------------------------------------------------------------


def parse_datetime(value: Any) -> Optional[_dt.datetime]:
    if value is None:
        return None
    if isinstance(value, _dt.datetime):
        return value
    if isinstance(value, _dt.date):
        return _dt.datetime(value.year, value.month, value.day)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1]
    for fmt in _DATE_FORMATS:
        try:
            return _dt.datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"Date invalide : « {value} » (attendu AAAA-MM-JJ ou JJ/MM/AAAA).")


def parse_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    if text in ("", "null"):
        return None
    if text in ("1", "true", "vrai", "oui", "yes", "on", "-1"):
        return True
    if text in ("0", "false", "faux", "non", "no", "off"):
        return False
    raise ValueError(f"Booléen invalide : « {value} ».")


def parse_number_text(value: Any) -> str:
    """Normalise « 200 000,50 » → « 200000.50 »."""
    text = str(value).strip().replace("\u202f", "").replace("\xa0", "").replace(" ", "")
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    elif "," in text and "." in text:
        text = text.replace(",", "")
    return text


def parse_int(value: Any) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None if value is None else int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = parse_number_text(value)
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return int(float(text))


def parse_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = parse_number_text(value)
    if not text:
        return None
    return float(text)


def parse_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return Decimal(str(value))
    text = parse_number_text(value)
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation as ex:
        raise ValueError(f"Montant invalide : « {value} ».") from ex


def _unwrap_optional(annotation: Any) -> Any:
    origin = typing.get_origin(annotation)
    if origin is typing.Union:
        args = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


def coerce(value: Any, annotation: Any) -> Any:
    """Convertit ``value`` vers le type annoté (``None`` pour une chaîne vide)."""
    target = _unwrap_optional(annotation)
    if value is None:
        return None
    if isinstance(value, str) and not value.strip() and target is not str:
        return None
    if target is str:
        return value if isinstance(value, str) else str(value)
    if target is bool:
        return parse_bool(value)
    if target is int:
        return parse_int(value)
    if target is float:
        return parse_float(value)
    if target is Decimal:
        return parse_decimal(value)
    if target is _dt.datetime or target is _dt.date:
        return parse_datetime(value)
    return value


_HINTS_CACHE: Dict[type, Dict[str, Any]] = {}


def type_hints(cls: type) -> Dict[str, Any]:
    hints = _HINTS_CACHE.get(cls)
    if hints is None:
        hints = typing.get_type_hints(cls)
        _HINTS_CACHE[cls] = hints
    return hints


def parse_entity(cls: Type[T], data: Mapping[str, Any],
                 base: Optional[T] = None) -> T:
    """Construit (ou complète ``base``) une dataclass depuis un dictionnaire.

    Les clés inconnues sont ignorées ; les erreurs de conversion lèvent une
    ``ValueError`` avec le nom du champ.
    """
    hints = type_hints(cls)
    values: Dict[str, Any] = {}
    if base is not None:
        for field in dataclasses.fields(cls):
            values[field.name] = getattr(base, field.name)
    for field in dataclasses.fields(cls):
        if field.name not in data:
            continue
        raw = data[field.name]
        try:
            values[field.name] = coerce(raw, hints.get(field.name, Any))
        except (ValueError, TypeError) as ex:
            raise ValueError(f"{field.name} : {ex}") from ex
    if base is not None:
        for name, value in values.items():
            setattr(base, name, value)
        return base
    return cls(**values)  # type: ignore[arg-type]
