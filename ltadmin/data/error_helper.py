"""Traduction des erreurs du moteur SQLite en erreurs métier compréhensibles.

``sqlite3`` lève des ``IntegrityError`` dont le message identifie la
contrainte violée (``UNIQUE constraint failed: ETUDIANT.MATRICULE``,
``FOREIGN KEY constraint failed``, ``NOT NULL constraint failed: …``) et des
``OperationalError`` pour les verrous (``database is locked``). On mappe ces
messages vers les codes stables de :mod:`ltadmin.core.result`, avec un repli
sur des mots-clés FR/EN pour les autres cas.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ltadmin.core import result as codes


@dataclass(frozen=True)
class DatabaseError:
    """Erreur de base de données interprétée : code stable + message français."""

    code: str
    message: str
    native_error: int = 0


_SQLITE_PATTERNS = (
    ("unique constraint failed",
     (codes.UNIQUE_VIOLATION,
      "Doublon interdit : un enregistrement avec les mêmes valeurs existe déjà.")),
    ("primary key constraint failed",
     (codes.UNIQUE_VIOLATION,
      "Doublon interdit : un enregistrement avec les mêmes valeurs existe déjà.")),
    ("foreign key constraint failed",
     (codes.FOREIGN_KEY_VIOLATION,
      "Opération refusée : cet enregistrement est lié à d’autres données "
      "(ou référence un enregistrement inexistant).")),
    ("not null constraint failed",
     (codes.REQUIRED_FIELD, "Une valeur obligatoire est manquante.")),
    ("check constraint failed",
     (codes.VALIDATION, "Valeur refusée par une règle de la base de données.")),
    ("database is locked",
     (codes.LOCKED, "La base de données est verrouillée. Réessayez dans un instant.")),
    ("readonly database",
     (codes.LOCKED, "La base de données est en lecture seule (droits insuffisants sur le fichier).")),
    ("attempt to write a readonly database",
     (codes.LOCKED, "La base de données est en lecture seule (droits insuffisants sur le fichier).")),
    ("unable to open database file",
     (codes.TECHNICAL, "Impossible d’ouvrir le fichier de base de données.")),
    ("no such table",
     (codes.TECHNICAL, "Table introuvable dans la base de données (schéma incomplet ?).")),
    ("no such column",
     (codes.TECHNICAL, "Colonne introuvable dans la base de données (schéma incomplet ?).")),
    ("datatype mismatch",
     (codes.VALIDATION, "Type de donnée incorrect pour l’un des champs.")),
)

_KEYWORD_GROUPS = (
    (("doublon", "duplicate", "unique", "clé primaire", "primary key"),
     (codes.UNIQUE_VIOLATION, "Doublon interdit : un enregistrement avec les mêmes valeurs existe déjà.")),
    (("related record", "enregistrement lié", "référentielle", "referential", "intégrité", "integrity", "foreign key"),
     (codes.FOREIGN_KEY_VIOLATION, "Opération refusée par une règle de liaison entre les tables.")),
    (("trop long", "too long"),
     (codes.DATA_TOO_LONG, "Texte trop long pour l’un des champs.")),
    (("null",),
     (codes.REQUIRED_FIELD, "Une valeur obligatoire est manquante.")),
    (("verrou", "lock", "exclusif", "exclusive", "en cours d’utilisation", "already in use"),
     (codes.LOCKED, "La base de données est verrouillée. Réessayez dans un instant.")),
)


def _message_of(exception: BaseException) -> str:
    parts = [str(exception)]
    cause = getattr(exception, "__cause__", None)
    seen = {id(exception)}
    while cause is not None and id(cause) not in seen:
        parts.append(str(cause))
        seen.add(id(cause))
        cause = getattr(cause, "__cause__", None)
    return " : ".join(p for p in parts if p)


def interpret(exception: BaseException) -> DatabaseError:
    """Interprète une exception de base de données en erreur métier."""
    text = _message_of(exception)
    lowered = text.lower()

    # 1) Messages natifs SQLite.
    for needle, (code, message) in _SQLITE_PATTERNS:
        if needle in lowered:
            return DatabaseError(code, message)

    # 2) Classes d'exception sqlite3 sans message reconnu.
    if isinstance(exception, sqlite3.IntegrityError):
        return DatabaseError(codes.FOREIGN_KEY_VIOLATION,
                             "Opération refusée par une contrainte d’intégrité : " + text)
    if isinstance(exception, sqlite3.OperationalError):
        return DatabaseError(codes.TECHNICAL,
                             "Opération sur la base de données impossible : " + text)

    # 3) Mots-clés FR/EN.
    for keywords, (code, message) in _KEYWORD_GROUPS:
        for keyword in keywords:
            if keyword in lowered:
                return DatabaseError(code, message)

    return DatabaseError(codes.TECHNICAL,
                         "Opération sur la base de données impossible : " + text)


def is_unique_violation(exception: BaseException) -> bool:
    return interpret(exception).code == codes.UNIQUE_VIOLATION


def is_foreign_key_violation(exception: BaseException) -> bool:
    return interpret(exception).code == codes.FOREIGN_KEY_VIOLATION
