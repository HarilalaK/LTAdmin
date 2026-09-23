"""Résultats d'opérations et codes d'erreur stables.

Les services ne lèvent jamais d'exception vers l'interface pour les cas
gérés : ils retournent un ``Result`` (ou ``ResultValue``) portant un message
en français affichable et un code stable parmi :const:`ERROR_CODES`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Iterable, List, Optional, TypeVar

T = TypeVar("T")

VALIDATION = "VALIDATION"
BUSINESS_RULE = "GESTION"
NOT_FOUND = "INTROUVABLE"
UNIQUE_VIOLATION = "DOUBLON"
FOREIGN_KEY_VIOLATION = "LIAISON"
REQUIRED_FIELD = "REQUIS"
DATA_TOO_LONG = "TROP_LONG"
NUMERIC_OVERFLOW = "DEPASSEMENT"
LOCKED = "VERROUILLE"
AUTHENTICATION = "AUTHENTIFICATION"
AUTHORIZATION = "HABILITATION"
TECHNICAL = "TECHNIQUE"


@dataclass
class Result:
    """Résultat d'une opération de service, sans valeur de retour."""

    is_success: bool = True
    message: str = ""
    code: Optional[str] = None
    errors: List[str] = field(default_factory=list)

    @property
    def is_failure(self) -> bool:
        return not self.is_success

    @property
    def success(self) -> bool:
        """Alias lisible (utilisé par l'interface)."""
        return self.is_success

    @classmethod
    def ok(cls, message: str = "") -> "Result":
        return cls(is_success=True, message=message, code=None, errors=[])

    @classmethod
    def fail(
        cls,
        message: str,
        code: Optional[str] = None,
        errors: Optional[Iterable[str]] = None,
    ) -> "Result":
        return cls(
            is_success=False,
            message=message,
            code=code or BUSINESS_RULE,
            errors=list(errors) if errors else [],
        )

    def full_message(self) -> str:
        if not self.errors:
            return self.message
        detail = "\n".join(self.errors)
        if not self.message.strip():
            return detail
        return self.message + "\n" + detail


@dataclass
class ResultValue(Result, Generic[T]):
    """Résultat d'une opération de service avec valeur de retour."""

    value: Any = None

    @classmethod
    def ok(cls, value: T, message: str = "") -> "ResultValue[T]":
        return cls(is_success=True, value=value, message=message, code=None, errors=[])

    @classmethod
    def fail(
        cls,
        message: str,
        code: Optional[str] = None,
        errors: Optional[Iterable[str]] = None,
    ) -> "ResultValue[T]":
        return cls(
            is_success=False,
            value=None,
            message=message,
            code=code or BUSINESS_RULE,
            errors=list(errors) if errors else [],
        )
