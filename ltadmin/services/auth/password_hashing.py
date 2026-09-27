"""Hachage et vérification des mots de passe (bibliothèque standard uniquement).

Format stocké dans ``UTILISATEUR.MOT_PASSE`` : ``pbkdf2_sha256$<itérations>$<sel hex>$<empreinte hex>``.

Migration transparente : la base fournie contient des mots de passe en clair
(héritage historique). ``verify_and_upgrade`` accepte ces valeurs, puis
``AuthenticationService`` les réécrit hachées à la première connexion réussie.
Les comptes créés ou modifiés via l'administration sont hachés immédiatement.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 120_000
SEED_LENGTH = 16  # octets de sel
MARKER = ALGORITHM + "$"


def hash_password(plain: str) -> str:
    """Hache un mot de passe en clair avec un sel aléatoire."""
    salt = secrets.token_hex(SEED_LENGTH)
    digest = hashlib.pbkdf2_hmac(
        "sha256", (plain or "").encode("utf-8"), salt.encode("ascii"), ITERATIONS)
    return f"{MARKER}{ITERATIONS}${salt}${digest.hex()}"


def is_hashed(stored: str) -> bool:
    """Le mot de passe stocké est-il déjà au format haché ?"""
    return (stored or "").startswith(MARKER)


def verify(plain: str, stored: str) -> bool:
    """Vérifie un mot de passe en clair contre la valeur stockée.

    Accepte le format haché et, pour la migration, le clair historique.
    """
    stored = stored or ""
    if not stored:
        return False
    if not is_hashed(stored):
        # Valeur historique en clair (base fournie) : comparaison directe.
        return hmac.compare_digest(stored, plain or "")
    try:
        _, iterations, salt, expected_hex = stored.split("$", 3)
        digest = hashlib.pbkdf2_hmac(
            "sha256", (plain or "").encode("utf-8"), salt.encode("ascii"),
            int(iterations))
        return hmac.compare_digest(digest.hex(), expected_hex)
    except (ValueError, TypeError):
        return False


def needs_upgrade(stored: str) -> bool:
    """Vrai si la valeur stockée doit être remplacée par un hachage."""
    return bool(stored) and not is_hashed(stored)
