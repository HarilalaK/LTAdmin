#!/usr/bin/env python3
"""LTAdmin — point d'entrée.

Par défaut, ouvre l'application dans une fenêtre native (pywebview) adossée
à un serveur local Python (``127.0.0.1``, port libre choisi automatiquement).

Options :
  --serve            mode serveur seul (ouvrir l'adresse affichée dans un navigateur)
  --host 0.0.0.0     écouter sur toutes les interfaces (réseau local / aperçu)
  --port 8765        port fixe (0 = automatique)
  --db CHEMIN        chemin de la base LTA_ADM.sqlite3 (sinon recherche automatique)
  --no-browser       en mode --serve, ne pas ouvrir le navigateur
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import threading
import webbrowser

# Permet « python main.py » depuis n'importe quel dossier.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ltadmin import __version__  # noqa: E402
from ltadmin.services.logging.app_logger import AppLogger  # noqa: E402


def parse_args(argv):
    parser = argparse.ArgumentParser(prog="LTAdmin", description="Gestion scolaire — Institut LTA")
    parser.add_argument("--serve", action="store_true", help="mode serveur (navigateur) au lieu de la fenêtre native")
    parser.add_argument("--host", default=None, help="adresse d'écoute (défaut : 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="port d'écoute (défaut : automatique)")
    parser.add_argument("--db", default=None, help="chemin de la base SQLite")
    parser.add_argument("--no-browser", action="store_true", help="ne pas ouvrir le navigateur en mode --serve")
    parser.add_argument("--version", action="version", version=f"LTAdmin {__version__}")
    return parser.parse_args(argv)


def run_desktop(startup, server, logger: AppLogger) -> int:
    try:
        import webview  # pywebview
    except ImportError:
        print("pywebview n'est pas installé : « pip install pywebview », ou lancez « python main.py --serve ».",
              file=sys.stderr)
        return run_server(startup, server, logger, open_browser=True)
    titre = "LTAdmin — " + (startup.services.admin.get_etablissement().sigle or "Gestion scolaire")
    window = webview.create_window(titre, server.url, width=1360, height=860, min_size=(1024, 680),
                                   text_select=True)

    def on_closed():
        try:
            server.stop()
        finally:
            startup.services.close()

    window.events.closed += on_closed
    webview.start(private_mode=False)
    return 0


def run_server(startup, server, logger: AppLogger, open_browser: bool) -> int:
    print(f"LTAdmin {__version__} — base : {startup.database_path}")
    if startup.migration_backup:
        print(f"Schéma renforcé ; sauvegarde de l'original : {startup.migration_backup}")
    if startup.created:
        print("Base créée avec le référentiel initial (comptes ADMIN/admin, SCOL/scol, CAISSE/caisse).")
    print(f"Interface disponible sur {server.url}  (Ctrl+C pour arrêter)")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(server.url)).start()
    stop = threading.Event()

    def handle_signal(signum, frame):
        stop.set()

    signal.signal(signal.SIGINT, handle_signal)
    try:
        signal.signal(signal.SIGTERM, handle_signal)
    except (AttributeError, ValueError):
        pass
    try:
        while not stop.wait(0.5):
            pass
    finally:
        server.stop()
        startup.services.close()
        print("Serveur arrêté.")
    return 0


def main(argv=None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    logger = AppLogger()
    from ltadmin import bootstrap
    host = args.host or ("127.0.0.1")
    port = args.port if args.port is not None else (0 if not args.serve else 8765)
    try:
        startup, server = bootstrap.start(args.db, host=host, port=port, logger=logger)
    except Exception as ex:  # base illisible, port occupé, etc.
        logger.error("Démarrage", ex)
        print(f"Impossible de démarrer LTAdmin : {ex}", file=sys.stderr)
        return 1
    if args.serve:
        return run_server(startup, server, logger, open_browser=not args.no_browser)
    return run_desktop(startup, server, logger)


if __name__ == "__main__":
    sys.exit(main())
