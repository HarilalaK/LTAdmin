"""Écran Rapports : les 8 états avec filtres et export CSV."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import List, Optional

from ltadmin.services.reports.csv_exporter import CsvExporter
from ltadmin.services.reports.report_service import REPORT_CATALOG
from ltadmin.ui.views.base_view import BaseView
from ltadmin.ui.widgets import DataTable, ask_save_csv, show_error, show_info

RESULT_COLUMNS = [("colonne", "Colonne", 220, "w")]


class ReportsView(BaseView):
    title = "Rapports"
    subtitle = "États de la base et export CSV (séparateur « ; », UTF-8)"

    def __init__(self, parent, services, session, **kwargs):
        super().__init__(parent, services, session, **kwargs)
        self._definition = None
        self._columns: List[str] = []
        self._rows: List[dict] = []

        top = ttk.Frame(self.content)
        top.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(top, text="État :").pack(side=tk.LEFT)
        self.report_var = tk.StringVar()
        self.report_combo = ttk.Combobox(top, textvariable=self.report_var,
                                         state="readonly", width=40,
                                         values=[d.title for d in
                                                 REPORT_CATALOG])
        self.report_combo.pack(side=tk.LEFT, padx=8)
        self.report_combo.bind("<<ComboboxSelected>>",
                               lambda _e: self._build_filters())

        self.filters_frame = ttk.Frame(top)
        self.filters_frame.pack(side=tk.LEFT, padx=(16, 0))
        self.classe_var = tk.StringVar()
        self.periode_var = tk.StringVar()
        self.matricule_var = tk.StringVar()

        self.table = DataTable(self.content, RESULT_COLUMNS)
        self.table.pack(fill=tk.BOTH, expand=True)

        self.toolbar.add_button("▶ Exécuter", self.run_report, accent=True)
        self.toolbar.add_button("⬇ Exporter en CSV", self.export_csv)
        self.report_combo.current(0)
        self._build_filters()

    def _current_definition(self):
        for definition in REPORT_CATALOG:
            if definition.title == self.report_var.get():
                return definition
        return REPORT_CATALOG[0]

    def _build_filters(self) -> None:
        for child in self.filters_frame.winfo_children():
            child.destroy()
        self._definition = self._current_definition()
        kind = self._definition.filter_kind
        if kind in ("classe_libelle", "classe_periode"):
            ttk.Label(self.filters_frame, text="Classe :").pack(side=tk.LEFT)
            classes = [c.libelle for c in
                       self.services.referentiel.list_classes()]
            combo = ttk.Combobox(self.filters_frame,
                                 textvariable=self.classe_var,
                                 state="readonly", width=28, values=classes)
            combo.pack(side=tk.LEFT, padx=(4, 12))
            if classes:
                combo.current(0)
        if kind == "classe_periode":
            ttk.Label(self.filters_frame, text="Période :").pack(side=tk.LEFT)
            periodes = self.services.evaluations.list_periodes()
            labels = [f"{p.libelle or p.code_periode} (ID {p.id_periode})"
                      for p in periodes]
            combo = ttk.Combobox(self.filters_frame,
                                 textvariable=self.periode_var,
                                 state="readonly", width=28, values=labels)
            combo.pack(side=tk.LEFT, padx=4)
            if labels:
                combo.current(0)
        if kind == "matricule":
            ttk.Label(self.filters_frame, text="Matricule :").pack(side=tk.LEFT)
            ttk.Entry(self.filters_frame, textvariable=self.matricule_var,
                      width=18).pack(side=tk.LEFT, padx=4)
        if kind == "inscription":
            ttk.Label(self.filters_frame,
                      text="ID inscription :").pack(side=tk.LEFT)
            self.inscription_var = tk.StringVar()
            ttk.Entry(self.filters_frame, textvariable=self.inscription_var,
                      width=10).pack(side=tk.LEFT, padx=4)

    def _filters(self) -> dict:
        kind = self._definition.filter_kind if self._definition else "none"
        filters = {}
        if kind in ("classe_libelle", "classe_periode"):
            filters["classe"] = self.classe_var.get()
        if kind == "classe_periode":
            # La requête enregistrée filtre par identifiants, pas par libellé.
            for periode in self.services.evaluations.list_periodes():
                if self.periode_var.get() == f"{periode.libelle or periode.code_periode} (ID {periode.id_periode})":
                    filters["id_periode"] = periode.id_periode
                    break
            for classe in self.services.referentiel.list_classes_detail():
                if classe.libelle == self.classe_var.get():
                    filters["id_classe"] = classe.id_classe
                    break
        if kind == "matricule":
            filters["matricule"] = self.matricule_var.get()
        if kind == "inscription":
            try:
                filters["id_inscription"] = int(self.inscription_var.get())
            except (ValueError, AttributeError):
                filters["id_inscription"] = None
        return filters

    def run_report(self) -> None:
        definition = self._current_definition()
        filters = self._filters()
        if not filters and definition.filter_kind != "none":
            show_error("Renseignez les critères de l’état.", "Critères manquants",
                       parent=self)
            return
        columns, rows = self.services.reports.build(definition.key, **filters)
        self._columns = columns
        self._rows = rows
        if columns:
            # build() renvoie des noms de colonnes ; DataTable attend
            # (clé, en-tête, largeur, ancrage).
            self.table.set_columns(
                [(name, name, 170, "w") for name in columns])
        self.table.set_rows(rows)

    def export_csv(self) -> None:
        if not self._rows:
            show_error("Exécutez d’abord l’état (bouton « Exécuter »).",
                       "Aucune donnée", parent=self)
            return
        definition = self._current_definition()
        path = ask_save_csv(CsvExporter.default_file_name(definition.key),
                            parent=self)
        if not path:
            return
        try:
            CsvExporter.write(path, self._columns, self._rows)
            show_info("Export réussi",
                      f"{len(self._rows)} ligne(s) exportée(s) vers "
                      f"{path}", parent=self)
        except Exception as ex:
            show_error("Export impossible : " + str(ex), "Erreur", parent=self)
