#!/usr/bin/env python3
"""Renforce le schéma d'une base LTA_ADM.sqlite3 (clés primaires, clés
étrangères, index, vues) en conservant toutes les données.

Usage :
    python tools/migrate_schema.py [CHEMIN_BASE] [--sans-sauvegarde] [--verifier]

Sans argument, la base est localisée comme au démarrage de l'application.
Une sauvegarde ``Sauvegardes/<base>_avant_migration_<horodatage>.sqlite3``
est créée avant toute modification (sauf ``--sans-sauvegarde``).
``--verifier`` indique seulement si une migration est nécessaire (code de
retour 3 si oui, 0 sinon).

L'application effectue elle-même cette migration à son premier démarrage ;
cet outil permet de la réaliser (ou de la vérifier) explicitement.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ltadmin.data import schema_ddl  # noqa: E402
from ltadmin.services.infrastructure.database_locator import DatabaseLocator  # noqa: E402


def verifier(path: str) -> int:
    with sqlite3.connect(path) as conn:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        fk = conn.execute("PRAGMA foreign_key_check").fetchall()
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        tables = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()[0]
        views = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='view'").fetchone()[0]
        indexes = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'").fetchone()[0]
    print(f"Intégrité : {integrity} · violations FK : {len(fk)} · version schéma : {version} · "
          f"{tables} tables, {views} vues, {indexes} index")
    return 0 if integrity == "ok" and not fk else 4


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Migration du schéma LTA_ADM.sqlite3")
    parser.add_argument("base", nargs="?", help="chemin de la base (défaut : recherche automatique)")
    parser.add_argument("--sans-sauvegarde", action="store_true", help="ne pas créer de copie avant migration")
    parser.add_argument("--verifier", action="store_true", help="vérifier seulement, sans modifier")
    args = parser.parse_args(argv)

    path = DatabaseLocator().locate(args.base)
    if not os.path.isfile(path):
        print(f"Base introuvable : {path}", file=sys.stderr)
        return 2
    print(f"Base : {path}")
    besoin = schema_ddl.needs_migration(path)
    if args.verifier:
        print("Migration nécessaire." if besoin else "Schéma déjà renforcé : aucune migration nécessaire.")
        verifier(path)
        return 3 if besoin else 0
    if not besoin:
        print("Schéma déjà renforcé : rien à faire.")
        return verifier(path)
    backup, copied = schema_ddl.migrate_database(path, backup=not args.sans_sauvegarde)
    if backup:
        print(f"Sauvegarde de l'original : {backup}")
    total = sum(copied.values())
    print(f"{total} ligne(s) reprises dans {len(copied)} tables :")
    for name in sorted(copied):
        if copied[name]:
            print(f"  - {name:<18} {copied[name]:>6}")
    return verifier(path)


if __name__ == "__main__":
    sys.exit(main())
