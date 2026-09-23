"""Écran Administration : paramètres, établissement, années, journal, sauvegardes."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ltadmin.models.entities import AnneeScolaire, Etablissement
from ltadmin.ui.dialogs import run_entity_dialog
from ltadmin.ui.views.base_view import BaseView
from ltadmin.ui.widgets import DataTable, confirm, show_info, show_result

PARAM_COLUMNS = [
    ("cle", "Clé", 200, "w"),
    ("valeur", "Valeur", 140, "w"),
    ("description", "Description", 320, "w"),
]

ANNEE_COLUMNS = [
    ("id_annee", "ID", -1, "w"),
    ("libelle", "Année", 140, "w"),
    ("date_debut", "Début", 110, "center"),
    ("date_fin", "Fin", 110, "center"),
    ("active", "Active", 70, "center"),
]

JOURNAL_COLUMNS = [
    ("date_log", "Date", 130, "center"),
    ("code_utr", "Utilisateur", 110, "w"),
    ("action_log", "Action", 170, "w"),
    ("table_cible", "Table", 140, "w"),
    ("id_cible", "ID", 60, "center"),
    ("detail", "Détail", 260, "w"),
]


class AdminView(BaseView):
    title = "Administration"
    subtitle = "Paramètres, établissement, années scolaires, journal et sauvegardes"

    def __init__(self, parent, services, session, **kwargs):
        super().__init__(parent, services, session, **kwargs)
        self.notebook = ttk.Notebook(self.content)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # --- Paramètres ---
        param_tab = ttk.Frame(self.notebook)
        self.notebook.add(param_tab, text="Paramètres")
        self.param_table = DataTable(param_tab, PARAM_COLUMNS)
        self.param_table.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        param_buttons = ttk.Frame(param_tab)
        param_buttons.pack(fill=tk.X, pady=8)
        ttk.Button(param_buttons, text="✎ Modifier la valeur",
                   command=self.edit_parametre).pack(side=tk.LEFT)

        # --- Établissement ---
        etab_tab = ttk.Frame(self.notebook)
        self.notebook.add(etab_tab, text="Établissement")
        self._etab_fields_vars = {}
        self._build_etablissement(etab_tab)

        # --- Années scolaires ---
        annee_tab = ttk.Frame(self.notebook)
        self.notebook.add(annee_tab, text="Années scolaires")
        self.annee_table = DataTable(annee_tab, ANNEE_COLUMNS,
                                     on_refresh=self.refresh)
        self.annee_table.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        annee_buttons = ttk.Frame(annee_tab)
        annee_buttons.pack(fill=tk.X, pady=8)
        ttk.Button(annee_buttons, text="＋ Nouvelle année",
                   command=self.create_annee).pack(side=tk.LEFT)
        ttk.Button(annee_buttons, text="✎ Modifier",
                   command=self.edit_annee).pack(side=tk.LEFT, padx=8)
        ttk.Button(annee_buttons, text="✔ Activer",
                   command=self.activer_annee).pack(side=tk.LEFT)

        # --- Journal ---
        journal_tab = ttk.Frame(self.notebook)
        self.notebook.add(journal_tab, text="Journal")
        journal_filters = ttk.Frame(journal_tab)
        journal_filters.pack(fill=tk.X, pady=(8, 4))
        ttk.Label(journal_filters, text="Action contient :").pack(side=tk.LEFT)
        self.journal_action_var = tk.StringVar()
        ttk.Entry(journal_filters, textvariable=self.journal_action_var,
                  width=20).pack(side=tk.LEFT, padx=(4, 16))
        ttk.Button(journal_filters, text="Filtrer",
                   command=self.refresh).pack(side=tk.LEFT)
        self.journal_table = DataTable(journal_tab, JOURNAL_COLUMNS)
        self.journal_table.pack(fill=tk.BOTH, expand=True)

        # --- Sauvegardes ---
        backup_tab = ttk.Frame(self.notebook)
        self.notebook.add(backup_tab, text="Sauvegardes")
        backup_buttons = ttk.Frame(backup_tab)
        backup_buttons.pack(fill=tk.X, pady=(8, 4))
        ttk.Button(backup_buttons, text="💾 Créer une sauvegarde",
                   style="Accent.TButton",
                   command=self.create_backup).pack(side=tk.LEFT)
        ttk.Button(backup_buttons, text="♻ Restaurer",
                   command=self.restore_backup).pack(side=tk.LEFT, padx=8)
        ttk.Button(backup_buttons, text="🧹 Purger (garder 10)",
                   command=self.purge_backups).pack(side=tk.LEFT)
        self.backup_list = tk.Listbox(backup_tab, height=10)
        self.backup_list.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        self.toolbar.add_label("Actions réservées au profil Administrateur")

    def _build_etablissement(self, parent) -> None:
        frame = ttk.Frame(parent, style="Card.TFrame", padding=16)
        frame.pack(fill=tk.BOTH, expand=True, pady=8)
        etablissement = self.services.admin.get_etablissement()
        specs = [("Code *", "code_etab"), ("Nom *", "nom_etab"),
                 ("Sigle", "sigle"), ("Adresse", "adresse"),
                 ("Téléphone", "tel"), ("E-mail", "email"),
                 ("Site web", "site_web"), ("Directeur", "directeur")]
        for index, (label, attribute) in enumerate(specs):
            row, column = index // 2, index % 2
            base = label.rstrip(" *")
            display = base + (" *" if label.endswith("*") else "")
            ttk.Label(frame, text=display,
                      style="Card.TLabel").grid(row=row, column=column * 2,
                                                sticky="w", padx=(0, 8), pady=4)
            variable = tk.StringVar(value=getattr(etablissement, attribute)
                                    or "")
            ttk.Entry(frame, textvariable=variable, width=28).grid(
                row=row, column=column * 2 + 1, sticky="w", padx=(0, 24),
                pady=4)
            self._etab_fields_vars[attribute] = (variable, base)
        ttk.Button(frame, text="Enregistrer l’établissement",
                   style="Accent.TButton",
                   command=self.save_etablissement).grid(row=4 + 1, column=0,
                                                         pady=(12, 0))

    def refresh(self) -> None:
        # Paramètres
        self.param_table.set_rows([{
            "cle": p.cle,
            "valeur": p.valeur,
            "description": p.description,
        } for p in self.services.parametres.list_parametres()])
        # Années
        self.annee_table.set_rows([{
            "id_annee": a.id_annee,
            "libelle": a.libelle,
            "date_debut": a.date_debut,
            "date_fin": a.date_fin,
            "active": a.active,
            "__entity__": a,
        } for a in self.services.admin.list_annees()])
        # Journal
        action = self.journal_action_var.get().strip() or None
        self.journal_table.set_rows([{
            "date_log": entry.date_log,
            "code_utr": entry.code_utr,
            "action_log": entry.action_log,
            "table_cible": entry.table_cible,
            "id_cible": entry.id_cible,
            "detail": entry.detail,
        } for entry in self.services.journal.consulter(action=action)])
        # Sauvegardes
        self.backup_list.delete(0, tk.END)
        from ltadmin.services.infrastructure.backup_service import BackupService
        for info in self.services.backups.list_backups():
            self.backup_list.insert(tk.END, BackupService.describe(info))

    # ----- Paramètres -----

    def edit_parametre(self) -> None:
        row = self.param_table.require_selection(
            parent=self, message="Sélectionnez d’abord un paramètre.")
        if row is None:
            return
        cle = row["cle"]
        fields = [
            dict(label=f"Valeur de {cle} *", kind="text", width=24,
                 initial=row["valeur"], required=True, row=0, column=0),
        ]

        def submit(values):
            return self.services.parametres.set_value(
                cle, values[f"Valeur de {cle}"], self.session.login)

        if run_entity_dialog(self, f"Paramètre {cle}", fields, submit,
                             "Enregistrer", two_columns=False):
            self.services.parametres.invalidate()
            self.refresh()

    # ----- Établissement -----

    def save_etablissement(self) -> None:
        etablissement = Etablissement()
        missing = []
        for attribute, (variable, label) in self._etab_fields_vars.items():
            value = variable.get().strip() or None
            setattr(etablissement, attribute, value)
            if attribute in ("code_etab", "nom_etab") and not value:
                missing.append(label)
        if missing:
            from ltadmin.ui.widgets import show_error
            show_error("Champ(s) obligatoire(s) : "
                       + ", ".join(f"« {name} »" for name in missing)
                       + " — renseignez la valeur.",
                       "Saisie incomplète", parent=self)
            return
        if show_result(self.services.admin.save_etablissement(
                etablissement, self.session.login), parent=self):
            self.refresh()

    # ----- Années scolaires -----

    def _annee_fields(self, annee: Optional[AnneeScolaire]) -> list:
        a = annee or AnneeScolaire()
        return [
            dict(label="Libellé *", kind="text", width=16, required=True,
                 initial=a.libelle, row=0, column=0),
            dict(label="Active", kind="bool",
                 initial=a.active if a.active is not None else False,
                 row=0, column=1),
            dict(label="Date de début", kind="date", initial=a.date_debut,
                 row=1, column=0),
            dict(label="Date de fin", kind="date", initial=a.date_fin,
                 row=1, column=1),
        ]

    def create_annee(self) -> None:
        def submit(values):
            from ltadmin.core.result import Result
            from ltadmin.ui.widgets import parse_date
            annee = AnneeScolaire(libelle=values["Libellé"],
                                  active=values["Active"])
            try:
                annee.date_debut = parse_date(values["Date de début"])
                annee.date_fin = parse_date(values["Date de fin"])
            except ValueError as ex:
                return Result.fail(str(ex), "VALIDATION")
            return self.services.admin.save_annee(annee,
                                                  self.session.login)

        if run_entity_dialog(self, "Nouvelle année scolaire",
                             self._annee_fields(None), submit, "Créer"):
            self.refresh()

    def edit_annee(self) -> None:
        row = self.annee_table.require_selection(parent=self)
        if row is None:
            return
        annee = row["__entity__"]

        def submit(values):
            from ltadmin.core.result import Result
            from ltadmin.ui.widgets import parse_date
            annee.libelle = values["Libellé"]
            annee.active = values["Active"]
            try:
                annee.date_debut = parse_date(values["Date de début"])
                annee.date_fin = parse_date(values["Date de fin"])
            except ValueError as ex:
                return Result.fail(str(ex), "VALIDATION")
            return self.services.admin.save_annee(annee,
                                                  self.session.login)

        if run_entity_dialog(self, f"Année {annee.libelle}",
                             self._annee_fields(annee), submit):
            self.refresh()

    def activer_annee(self) -> None:
        row = self.annee_table.require_selection(parent=self)
        if row is None:
            return
        annee = row["__entity__"]
        if show_result(self.services.admin.activer_annee(
                annee.id_annee, self.session.login), parent=self):
            self.refresh()

    # ----- Sauvegardes -----

    def create_backup(self) -> None:
        if show_result(self.services.backups.create_backup(), parent=self):
            self.refresh()

    def restore_backup(self) -> None:
        selection = self.backup_list.curselection()
        if not selection:
            show_info("Sélectionnez d’abord une sauvegarde dans la liste.",
                      "Aucune sélection", parent=self)
            return
        line = self.backup_list.get(selection[0])
        file_name = line.split(" — ")[0]
        from pathlib import Path
        path = str(Path(self.services.backups.backup_directory) / file_name)
        if not confirm(f"Restaurer la base depuis « {file_name} » ?\n\n"
                       "Une copie de sécurité de la base actuelle sera "
                       "conservée avant l’écrasement.", "Restauration",
                       parent=self):
            return
        if show_result(self.services.backups.restore_backup(path),
                       parent=self):
            self.services.refresh()
            self.refresh()

    def purge_backups(self) -> None:
        if not confirm("Supprimer les sauvegardes au-delà des 10 plus "
                       "récentes ?", "Purge", parent=self):
            return
        if show_result(self.services.backups.purge_backups(10), parent=self):
            self.refresh()
