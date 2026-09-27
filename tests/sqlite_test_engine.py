"""Base SQLite temporaire pour les tests : schéma renforcé + référentiel initial.

Toute la pile (dépôts + services + API web) est testée sur un vrai fichier
SQLite créé par :func:`ltadmin.data.schema_ddl.create_database`, exactement
comme en production. Aucune dépendance externe.
"""

from __future__ import annotations

import os
from typing import Optional

from ltadmin.data.database import Database
from ltadmin.data.schema_ddl import create_database
from ltadmin.data.seed_data import SEED_ROWS


def create_test_database(path: str, seed: Optional[dict] = None) -> str:
    """Crée (ou recrée) la base de test au chemin donné."""
    if os.path.exists(path):
        os.remove(path)
    return create_database(path, seed_rows=SEED_ROWS if seed is None else seed,
                           overwrite=True)


def create_test_services(path: str):
    """Base + composition de services prête pour les tests."""
    from ltadmin.services.app_composition import AppServices

    create_test_database(path)
    database = Database(path)
    database.open()
    return AppServices(database)
