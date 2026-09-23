"""Traduction des erreurs du moteur ACE en erreurs métier compréhensibles.

Les messages du pilote dépendent de la langue d'Office : on mappe d'abord
les numéros d'erreur natifs Jet/ACE (3022 doublon, 3200/3201 intégrité
référentielle, 3314/3058 null interdit, 3163 champ trop petit…), puis en
repli des mots-clés FR/EN.

Avec pyodbc, l'erreur native apparaît dans le message du diagnostic, par
exemple ``... [Microsoft][Pilote ODBC Microsoft Access] ... (-3022)`` ;
on l'extrait par expression régulière.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from ltadmin.core import result as codes

_NATIVE_RE = re.compile(r"\((-?\d{3,5})\)")


@dataclass(frozen=True)
class DatabaseError:
    """Erreur de base de données interprétée : code stable + message français."""

    code: str
    message: str
    native_error: int


_MESSAGES = {
    3022: (codes.UNIQUE_VIOLATION, "Doublon interdit : un enregistrement avec les mêmes valeurs existe déjà."),
    # 3201 : enregistrement lié introuvable (insertion avec clé absente).
    3201: (codes.FOREIGN_KEY_VIOLATION, "Enregistrement lié introuvable : vérifiez les liens (classe, étudiant, matière…)."),
    # 3200/3202 : suppression/modification refusée (enregistrements liés).
    3200: (codes.FOREIGN_KEY_VIOLATION, "Suppression impossible : cet enregistrement est utilisé par d’autres données."),
    3202: (codes.FOREIGN_KEY_VIOLATION, "Suppression impossible : cet enregistrement est utilisé par d’autres données."),
    # Champ requis vide.
    3314: (codes.REQUIRED_FIELD, "Une valeur obligatoire est manquante."),
    3058: (codes.REQUIRED_FIELD, "Une valeur obligatoire est manquante."),
    # Texte trop long pour le champ.
    3163: (codes.DATA_TOO_LONG, "Texte trop long pour l’un des champs."),
    # Dépassement numérique.
    3349: (codes.NUMERIC_OVERFLOW, "Valeur numérique hors limites pour l’un des champs."),
    6: (codes.NUMERIC_OVERFLOW, "Valeur numérique hors limites pour l’un des champs."),
    # Aucun enregistrement courant.
    3021: (codes.NOT_FOUND, "Enregistrement introuvable : il a peut-être été supprimé."),
    # Données modifiées entre-temps / verrous.
    3197: (codes.LOCKED, "Données verrouillées ou modifiées par un autre utilisateur. Réessayez."),
    3260: (codes.LOCKED, "Données verrouillées ou modifiées par un autre utilisateur. Réessayez."),
    3261: (codes.LOCKED, "Données verrouillées ou modifiées par un autre utilisateur. Réessayez."),
    3262: (codes.LOCKED, "Données verrouillées ou modifiées par un autre utilisateur. Réessayez."),
    # Fichier verrouillé / accès exclusif / réseau.
    3043: (codes.LOCKED, "La base de données est verrouillée ou inaccessible (fichier ouvert en exclusif, droits insuffisants)."),
    3050: (codes.LOCKED, "La base de données est verrouillée ou inaccessible (fichier ouvert en exclusif, droits insuffisants)."),
    3051: (codes.LOCKED, "La base de données est verrouillée ou inaccessible (fichier ouvert en exclusif, droits insuffisants)."),
}

_KEYWORD_GROUPS = (
    (("doublon", "duplicate", "doubles", "unique", "clé primaire", "primary key"),
     (codes.UNIQUE_VIOLATION, "Doublon interdit : un enregistrement avec les mêmes valeurs existe déjà.")),
    (("related record", "enregistrement lié", "référentielle", "referential", "intégrité", "integrity"),
     (codes.FOREIGN_KEY_VIOLATION, "Opération refusée par une règle de liaison entre les tables.")),
    (("trop long", "too small", "too long"),
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

    # 1) Numéros natifs Jet/ACE extraits du texte du diagnostic ODBC.
    for match in _NATIVE_RE.finditer(text):
        native = abs(int(match.group(1)))
        mapped = _MESSAGES.get(native)
        if mapped:
            return DatabaseError(mapped[0], mapped[1], native)

    # 2) Attribut natif éventuel (pyodbc : args / odbc_error non standard).
    native_attr = getattr(exception, "native_error", None)
    if isinstance(native_attr, int):
        mapped = _MESSAGES.get(abs(native_attr))
        if mapped:
            return DatabaseError(mapped[0], mapped[1], abs(native_attr))

    # 3) Mots-clés FR/EN (les messages dépendent de la langue d'Office).
    lowered = text.lower()
    for keywords, (code, message) in _KEYWORD_GROUPS:
        for keyword in keywords:
            if keyword in lowered:
                return DatabaseError(code, message, 0)

    return DatabaseError(codes.TECHNICAL, "Opération sur la base de données impossible : " + text, 0)


def is_unique_violation(exception: BaseException) -> bool:
    return interpret(exception).code == codes.UNIQUE_VIOLATION


def is_foreign_key_violation(exception: BaseException) -> bool:
    return interpret(exception).code == codes.FOREIGN_KEY_VIOLATION
