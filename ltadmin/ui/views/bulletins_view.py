"""Écran Bulletins : génération par classe × période, consultation, décision."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ltadmin.ui.views.base_view import BaseView
from ltadmin.ui.widgets import DataTable, confirm, show_error, show_result, \
    ask_save_csv

BULLETIN_COLUMNS = [
    ("id_bulletin", "ID", -1, "w"),
    ("matricule", "Matricule", 110, "w"),
    ("nom_complet", "Étudiant", 220, "w"),
    ("classe", "Classe", 150, "w"),
    ("periode", "Période", 130, "w"),
    ("moyenne", "Moyenne", 90, "e"),
    ("rang", "Rang", 60, "center"),
    ("effectif", "Effectif", 70, "center"),
    ("moy_classe", "Moy. classe", 90, "e"),
    ("decision", "Décision", 90, "w"),
]

LIGNE_COLUMNS = [
    ("code_matiere", "Code", 80, "w"),
    ("matiere", "Matière", 200, "w"),
    ("moyenne_mat", "Moyenne", 90, "e"),
    ("coefficient", "Coef", 60, "e"),
    ("points", "Points", 80, "e"),
    ("rang_mat", "Rang", 60, "center"),
    ("moy_min", "Min", 70, "e"),
    ("moy_max", "Max", 70, "e"),
    ("appreciation", "Appréciation", 220, "w"),
]


class BulletinsView(BaseView):
    title = "Bulletins"
    subtitle = "Génération et consultation des bulletins par classe et période"

    def __init__(self, parent, services, session, **kwargs):
        super().__init__(parent, services, session, **kwargs)
        self._classes = []
        self._periodes = []
        self._selected_bulletin_id = None

        filters = ttk.Frame(self.content)
        filters.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(filters, text="Classe :").pack(side=tk.LEFT)
        self.classe_var = tk.StringVar()
        self.classe_combo = ttk.Combobox(filters, textvariable=self.classe_var,
                                         state="readonly", width=30)
        self.classe_combo.pack(side=tk.LEFT, padx=(8, 16))
        self.classe_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        ttk.Label(filters, text="Période :").pack(side=tk.LEFT)
        self.periode_var = tk.StringVar()
        self.periode_combo = ttk.Combobox(filters, textvariable=self.periode_var,
                                          state="readonly", width=30)
        self.periode_combo.pack(side=tk.LEFT, padx=8)
        self.periode_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())

        self.bulletin_table = DataTable(self.content, BULLETIN_COLUMNS,
                                        on_refresh=self.refresh)
        self.bulletin_table.pack(fill=tk.BOTH, expand=True)
        self.bulletin_table.tree.bind("<<TreeviewSelect>>",
                                      lambda _e: self._load_lignes())

        ttk.Label(self.content, text="Lignes du bulletin sélectionné",
                  style="Muted.TLabel").pack(anchor="w", pady=(10, 4))
        self.ligne_table = DataTable(self.content, LIGNE_COLUMNS)
        self.ligne_table.pack(fill=tk.BOTH, expand=True)

        self.toolbar.add_button("⚡ Générer / régénérer", self.generer, accent=True)
        self.toolbar.add_button("✎ Appréciation", self.edit_appreciation)
        self.toolbar.add_button("⬇ Exporter (CSV)", self.exporter)

    def refresh(self) -> None:
        self._classes = self.services.referentiel.list_classes()
        classe_labels = [f"{c.libelle} (ID {c.id_classe})" for c in self._classes]
        self.classe_combo.configure(values=classe_labels)
        if self.classe_var.get() not in classe_labels:
            self.classe_var.set(classe_labels[0] if classe_labels else "")

        self._periodes = self.services.evaluations.list_periodes()
        periode_labels = [f"{p.libelle or p.code_periode} (ID {p.id_periode})"
                          for p in self._periodes]
        self.periode_combo.configure(values=periode_labels)
        if self.periode_var.get() not in periode_labels:
            self.periode_var.set(periode_labels[0] if periode_labels else "")

        self._load_bulletins()

    def _ids(self) -> "tuple[Optional[int], Optional[int]]":
        id_classe = id_periode = None
        for classe in self._classes:
            if self.classe_var.get() == f"{classe.libelle} (ID {classe.id_classe})":
                id_classe = classe.id_classe
        for periode in self._periodes:
            if self.periode_var.get() == f"{periode.libelle or periode.code_periode} (ID {periode.id_periode})":
                id_periode = periode.id_periode
        return id_classe, id_periode

    def _load_bulletins(self) -> None:
        id_classe, id_periode = self._ids()
        rows = []
        if id_classe is not None and id_periode is not None:
            for resume in self.services.bulletins.list_resumes(id_classe, id_periode):
                rows.append({
                    "id_bulletin": resume.id_bulletin,
                    "matricule": resume.matricule,
                    "nom_complet": f"{resume.nom or ''} {resume.prenom or ''}".strip(),
                    "classe": resume.classe,
                    "periode": resume.periode,
                    "moyenne": resume.moyenne,
                    "rang": resume.rang,
                    "effectif": resume.effectif,
                    "decision": resume.decision,
                })
        self.bulletin_table.set_rows(rows)

    def _load_lignes(self) -> None:
        row = self.bulletin_table.selected_row()
        if row is None:
            self.ligne_table.set_rows([])
            self._selected_bulletin_id = None
            return
        id_bulletin = row["id_bulletin"]
        self._selected_bulletin_id = id_bulletin
        matieres = {m.code_matiere: (m.libelle or m.code_matiere)
                    for m in self.services.referentiel.list_matieres()}
        rows = []
        for ligne in self.services.bulletins.list_lignes(id_bulletin):
            rows.append({
                "code_matiere": ligne.code_matiere,
                "matiere": matieres.get(ligne.code_matiere, ligne.code_matiere),
                "moyenne_mat": ligne.moyenne_mat,
                "coefficient": ligne.coefficient,
                "points": ligne.points,
                "rang_mat": ligne.rang_mat,
                "moy_min": ligne.moy_min,
                "moy_max": ligne.moy_max,
                "appreciation": ligne.appreciation,
            })
        self.ligne_table.set_rows(rows)

    def generer(self) -> None:
        id_classe, id_periode = self._ids()
        if id_classe is None or id_periode is None:
            show_error("Sélectionnez une classe et une période.",
                       "Filtres requis", parent=self)
            return
        if not confirm("Générer (ou régénérer) les bulletins ?\n\nLes bulletins "
                       "existants de cette combinaison classe × période seront "
                       "supprimés puis recréés.", "Génération", parent=self):
            return
        if show_result(self.services.bulletins.generer(
                id_classe, id_periode, self.session.login), parent=self):
            self._load_bulletins()

    def edit_appreciation(self) -> None:
        row = self.bulletin_table.require_selection(parent=self)
        if row is None:
            return
        id_bulletin = row["id_bulletin"]
        if not self.services.bulletins.list_lignes(id_bulletin):
            show_error("Bulletin introuvable.", "Erreur", parent=self)
            return
        from ltadmin.models.entities import Bulletin
        from ltadmin.ui.dialogs import run_entity_dialog

        # Le résumé ne porte pas l'appréciation : on reconstruit un Bulletin
        # minimal pour la mise à jour.
        bulletin = Bulletin(id_bulletin=id_bulletin)
        fields = [
            dict(label="Appréciation générale", kind="memo", width=42,
                 initial="", row=0, column=0),
        ]

        def submit(values):
            bulletin.appreciation = values["Appréciation générale"]
            return self.services.bulletins.update_appreciation(
                bulletin, self.session.login)

        if run_entity_dialog(self, "Modifier l’appréciation", fields, submit,
                             "Enregistrer", two_columns=False):
            self._load_bulletins()

    def exporter(self) -> None:
        """Export CSV de l'état « détail des bulletins » pour la classe."""
        classe_label = None
        for classe in self._classes:
            if self.classe_var.get() == f"{classe.libelle} (ID {classe.id_classe})":
                classe_label = classe.libelle
                break
        if not classe_label:
            show_error("Sélectionnez une classe.", "Aucune classe", parent=self)
            return
        from ltadmin.services.reports.csv_exporter import CsvExporter
        path = ask_save_csv(CsvExporter.default_file_name("bulletins_detail"),
                            parent=self)
        if not path:
            return
        ok, message = self.services.reports.export(
            "bulletin_detail", path, classe=classe_label)
        if ok:
            from ltadmin.ui.widgets import show_info
            show_info("Export réussi", message, parent=self)
        else:
            show_error(message, "Export impossible", parent=self)
