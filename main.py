#!/usr/bin/env python3
"""LTAdmin — point d'entrée de l'application desktop.

Usage : python main.py [chemin vers LTA_ADM.accdb]
La base est recherchée : argument CLI → variable LTADMIN_DB → dossier de
l'exécutable → dossier courant → 5 dossiers parents.
"""

from __future__ import annotations

import os
import sys
import traceback

# Permet le lancement direct (python main.py) sans installation.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _fail(message: str) -> None:
    """Message d'erreur bloquant : console puis boîte de dialogue si possible."""
    print("LTAdmin — " + message, file=sys.stderr)
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("LTAdmin", message)
        root.destroy()
    except Exception:
        pass


def _import_modules():
    from ltadmin.data.access_database import AccessDatabase
    from ltadmin.services.app_composition import AppServices
    from ltadmin.services.auth import habilitations
    from ltadmin.services.infrastructure.database_locator import DatabaseLocator
    from ltadmin.ui.login_dialog import LoginDialog
    from ltadmin.ui.main_window import MainWindow
    return (AccessDatabase, AppServices, habilitations, DatabaseLocator,
            LoginDialog, MainWindow)


def _register_views(window, habilitations) -> None:
    from ltadmin.ui.views.admin_view import AdminView
    from ltadmin.ui.views.bulletins_view import BulletinsView
    from ltadmin.ui.views.dashboard_view import DashboardView
    from ltadmin.ui.views.enrollments_view import EnrollmentsView
    from ltadmin.ui.views.exams_view import ExamsView
    from ltadmin.ui.views.grades_view import GradesView
    from ltadmin.ui.views.payments_view import PaymentsView
    from ltadmin.ui.views.referentiel_view import ReferentielView
    from ltadmin.ui.views.reports_view import ReportsView
    from ltadmin.ui.views.schedule_view import ScheduleView
    from ltadmin.ui.views.staff_view import StaffView
    from ltadmin.ui.views.statistics_view import StatisticsView
    from ltadmin.ui.views.students_view import StudentsView
    from ltadmin.ui.views.table_manager_view import TableManagerView
    from ltadmin.ui.views.users_view import UsersView

    m = habilitations.Modules
    window.register_view(m.TABLEAU_DE_BORD, DashboardView)
    window.register_view(m.ETUDIANTS, StudentsView)
    window.register_view(m.INSCRIPTIONS, EnrollmentsView)
    window.register_view(m.REFERENTIEL, ReferentielView)
    window.register_view(m.FORMATEURS, StaffView)
    window.register_view(m.NOTES, GradesView)
    window.register_view(m.BULLETINS, BulletinsView)
    window.register_view(m.EXAMENS, ExamsView)
    window.register_view(m.EMPLOI_DU_TEMPS, ScheduleView)
    window.register_view(m.ECOLAGE, PaymentsView)
    window.register_view(m.STATISTIQUES, StatisticsView)
    window.register_view(m.RAPPORTS, ReportsView)
    window.register_view(m.ADMINISTRATION, AdminView)
    window.register_view(m.UTILISATEURS, UsersView)
    window.register_view(m.TABLES, TableManagerView)
    # ABSENCES partage l'écran EDT (onglets Séances / Absences).
    window.register_view(m.ABSENCES, ScheduleView)
    # PAIE partage l'écran Formateurs (onglets Programmes / Paie).
    window.register_view(m.PAIE, StaffView)


def _main() -> int:
    try:
        (AccessDatabase, AppServices, habilitations, DatabaseLocator,
         LoginDialog, MainWindow) = _import_modules()
    except Exception as ex:
        _fail("Démarrage impossible : " + str(ex))
        return 1

    database_path = DatabaseLocator().locate(
        sys.argv[1] if len(sys.argv) > 1 else None)
    if not os.path.isfile(database_path):
        _fail("Base de données introuvable : " + database_path
              + "\n\nPlacez LTA_ADM.accdb près de l’application, ou "
              "indiquez son chemin en argument, ou définissez la variable "
              "d’environnement LTADMIN_DB.")
        return 1

    database = AccessDatabase(database_path)
    try:
        database.open()
    except Exception as ex:
        _fail("Connexion à la base impossible : " + str(ex)
              + "\n\nVérifiez que le fichier n’est pas ouvert en exclusif "
              "dans Microsoft Access et que le pilote ODBC (Microsoft ACE "
              "OLEDB/ODBC) est installé (même architecture 32/64 bits que "
              "Python).")
        return 1

    import tkinter as tk
    boot = tk.Tk()
    boot.withdraw()
    from ltadmin.ui.theme import Theme
    Theme.apply_ttk_styles(boot)

    services = AppServices(database)
    try:
        while True:
            session = LoginDialog.run(boot, services)
            if session is None:
                break
            boot.withdraw()
            window = MainWindow(services, session)
            _register_views(window, habilitations)
            window.mainloop()
            # Déconnexion : nouvelle boucle de connexion ; fermeture : sortie.
            try:
                if not window.winfo_exists():
                    break
            except Exception:
                break
    except Exception as ex:
        services.logger.error("Démarrage", ex)
        _fail("Erreur inattendue :\n" + traceback.format_exc(limit=5))
        return 1
    finally:
        services.close()
    return 0


if __name__ == "__main__":
    sys.exit(_main())
