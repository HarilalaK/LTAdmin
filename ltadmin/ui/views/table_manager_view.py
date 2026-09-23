"""Maintenance générique des tables (réservée à l'administration).

Parcours des 33 tables : TOP 1000 lignes, recherche plein texte (CStr LIKE),
suppression (Suppr), actualisation (F5), édition via RecordEditor.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import List, Optional

from ltadmin.models.db_models import DbTableInfo
from ltadmin.ui.views.base_view import BaseView
from ltadmin.ui.views.record_editor import RecordEditor
from ltadmin.ui.widgets import DataTable, confirm, show_error, show_result

MAX_ROWS = 1000


class TableManagerView(BaseView):
    title = "Tables"
    subtitle = "Maintenance générique des tables de la base (administration)"

    def __init__(self, parent, services, session, **kwargs):
        super().__init__(parent, services, session, **kwargs)
        self._tables: List[DbTableInfo] = []
        self._table: Optional[DbTableInfo] = None
        self._rows: List[dict] = []

        left = ttk.Frame(self.content)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))

        ttk.Label(left, text="Tables").pack(anchor="w")
        self.table_list = tk.Listbox(left, width=34, height=28)
        self.table_list.pack(fill=tk.Y, expand=True, pady=(4, 0))
        self.table_list.bind("<<ListboxSelect>>",
                             lambda _e: self._load_selected_table())

        right = ttk.Frame(self.content)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        search = ttk.Frame(right)
        search.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(search, text="Recherche :").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        entry = ttk.Entry(search, textvariable=self.search_var, width=32)
        entry.pack(side=tk.LEFT, padx=8)
        entry.bind("<Return>", lambda _e: self._reload())
        ttk.Button(search, text="Rechercher",
                   command=self._reload).pack(side=tk.LEFT)

        self.data_table = DataTable(right, [("__vide__", "—", 120, "w")],
                                    on_delete=self.delete_row,
                                    on_refresh=self._reload)
        self.data_table.pack(fill=tk.BOTH, expand=True)
        self.data_table.tree.bind("<Double-1>",
                                  lambda _e: self.edit_selected_row())
        self.data_table.tree.bind("<Return>",
                                  lambda _e: self.edit_selected_row())

        self.toolbar.add_button("＋ Nouvel enregistrement", self.create_row,
                                accent=True)
        self.toolbar.add_label("Double-clic / Entrée : modifier — Suppr : "
                               "supprimer — F5 : actualiser — 1000 lignes max")

    def refresh(self) -> None:
        self._tables = self.services.tables.get_tables()
        self.table_list.delete(0, tk.END)
        names = [table.name for table in self._tables]
        for name in names:
            self.table_list.insert(tk.END, name)
        if not self.table_list.curselection() and names:
            self.table_list.selection_set(0)
            self.table_list.activate(0)
            self._load_selected_table()

    def _load_selected_table(self) -> None:
        selection = self.table_list.curselection()
        if not selection:
            return
        index = selection[0]
        if index >= len(self._tables):
            return
        self._table = self._tables[index]
        self._reload()

    def _reload(self) -> None:
        if self._table is None:
            return
        try:
            self._rows = self.services.tables.load_table(
                self._table, self.search_var.get() or None, MAX_ROWS)
        except Exception as ex:
            show_error("Lecture impossible : " + str(ex), "Erreur",
                       parent=self)
            self._rows = []
        columns = [("__rowid__", "#", 50, "center")]
        for column in self._table.columns:
            header = column.name
            if column.is_primary_key:
                header = "🔑 " + header
            elif column.autonumber:
                header = "⟳ " + header
            width = 160 if column.kind in ("TEXT", "MEMO") else 110
            columns.append((column.name, header, width,
                            "w" if column.kind in ("TEXT", "MEMO") else "center"))
        self.data_table.set_columns(columns)
        display_rows = []
        for index, row in enumerate(self._rows, start=1):
            enriched = dict(row)
            enriched["__rowid__"] = index
            display_rows.append(enriched)
        self.data_table.set_rows(display_rows)

    # ----- Édition -----

    def create_row(self) -> None:
        if self._table is None:
            show_error("Sélectionnez d’abord une table.", "Aucune table",
                       parent=self)
            return
        editor = RecordEditor(self, self.services, self._table, None)
        self.wait_window(editor)
        self._reload()

    def edit_selected_row(self) -> None:
        if self._table is None:
            return
        row = self.data_table.selected_row()
        if row is None:
            show_error("Sélectionnez d’abord une ligne.", "Aucune sélection",
                       parent=self)
            return
        original = {k: v for k, v in row.items() if k != "__rowid__"}
        editor = RecordEditor(self, self.services, self._table, original)
        self.wait_window(editor)
        self._reload()

    def delete_row(self, row: dict) -> None:
        if self._table is None:
            return
        original = {k: v for k, v in row.items() if k != "__rowid__"}
        if not confirm(f"Supprimer cet enregistrement de la table "
                       f"« {self._table.name} » ?\n\nLa base refusera la "
                       "suppression si des données liées l’empêchent.",
                       "Suppression", parent=self):
            return
        try:
            self.services.tables.delete(self._table, original)
            self.services.journal.log_suppression(
                self.session.login, self._table.name, None, None)
            show_result(__import__("ltadmin.core.result",
                                   fromlist=["Result"]).Result.ok(
                "Enregistrement supprimé."), parent=self)
        except Exception as ex:
            from ltadmin.data import error_helper
            error = error_helper.interpret(ex)
            show_error(error.message, "Suppression impossible", parent=self)
        self._reload()
