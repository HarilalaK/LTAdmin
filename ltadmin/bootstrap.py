"""Démarrage commun : localisation de la base, migration du schéma,
composition des services et création de l'application web.

Utilisé par ``main.py`` (fenêtre pywebview ou mode serveur) et par les
outils en ligne de commande.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from ltadmin.data import schema_ddl, seed_data
from ltadmin.data.database import Database
from ltadmin.services.app_composition import AppServices
from ltadmin.services.infrastructure.database_locator import DatabaseLocator
from ltadmin.services.logging.app_logger import AppLogger
from ltadmin.web.server import LtadminHttpServer, WebApplication


@dataclass
class Startup:
    database_path: str
    services: AppServices
    app: WebApplication
    migration_backup: Optional[str] = None
    created: bool = False


def prepare_database(path: str, logger: Optional[AppLogger] = None,
                     create_if_missing: bool = True) -> tuple[Optional[str], bool]:
    """Crée la base si absente, migre le schéma si nécessaire.

    Retourne ``(chemin_sauvegarde_avant_migration, base_creee)``.
    """
    logger = logger or AppLogger()
    created = False
    backup_path = None
    if not os.path.isfile(path):
        if not create_if_missing:
            raise FileNotFoundError(f"Base introuvable : {path}")
        schema_ddl.create_database(path, seed_data.SEED_ROWS)
        logger.info(f"Base créée avec le référentiel initial : {path}")
        created = True
    elif schema_ddl.needs_migration(path):
        backup_path, copied = schema_ddl.migrate_database(path, backup=True)
        total = sum(copied.values())
        logger.info(f"Schéma renforcé ({total} lignes reprises) ; sauvegarde : {backup_path}")
    return backup_path, created


def start(database_argument: Optional[str] = None, host: str = "127.0.0.1", port: int = 0,
          logger: Optional[AppLogger] = None) -> tuple[Startup, LtadminHttpServer]:
    """Prépare la base, ouvre les services et démarre le serveur HTTP."""
    logger = logger or AppLogger()
    path = DatabaseLocator().locate(database_argument)
    backup_path, created = prepare_database(path, logger)
    services = AppServices(Database(path), logger)
    services.open()
    app = WebApplication(services)
    server = LtadminHttpServer(app, host=host, port=port).start()
    logger.info(f"Serveur LTAdmin démarré sur {server.url} (base : {path})")
    return Startup(path, services, app, backup_path, created), server
