"""Écran Inscriptions : inscrire, historique, sorties, échéanciers d'écolage."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ltadmin.models.entities import Inscription
from ltadmin.ui.dialogs import run_entity_dialog
from ltadmin.ui.views.base_view import BaseView
from ltadmin.ui.widgets import DataTable, confirm, parse_date, show_info, show_result

INSCRITS_COLUMNS = [
    ("id_inscription", "ID", -1, "w"),
    ("num_inscription", "N° inscription", 130, "w"),
    ("matricule", "Matricule", 120, "w"),
    ("nom_complet", "Étudiant", 240, "w"),
    ("classe", "Classe", 200, "w"),
    ("date_inscription", "Inscription", 110, "center"),
    ("redoublant", "Redoublant", 90, "center"),
    ("statut", "Statut", 90, "w"),
]

ECHEANCES_COLUMNS = [
    ("libelle", "Échéance", 220, "w"),
    ("num_tranche", "N°", 40, "center"),
    ("date_echeance", "Échéance au", 110, "center"),
    ("montant_du", "Montant dû", 110, "e"),
    ("remise", "Remise", 90, "e"),
    ("total_paye", "Payé", 110, "e"),
    ("reste", "Reste", 110, "e"),
    ("statut", "Statut", 90, "center"),
]


class EnrollmentsView(BaseView):
    title = "Inscriptions"
    subtitle = "Inscriptions des étudiants, sorties et échéanciers d’écolage"

    def __init__(self, parent, services, session, **kwargs):
        super().__init__(parent, services, session, **kwargs)
        self._classes = []
        self._inscrits = []

        filters = ttk.Frame(self.content)
        filters.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(filters, text="Classe :").pack(side=tk.LEFT)
        self.classe_var = tk.StringVar()
        self.classe_combo = ttk.Combobox(filters, textvariable=self.classe_var,
                                         state="readonly", width=32)
        self.classe_combo.pack(side=tk.LEFT, padx=8)
        self.classe_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())

        self.inscrits_table = DataTable(
            self.content, INSCRITS_COLUMNS,
            on_double_click=self.show_echeancier,
            on_refresh=self.refresh)
        self.inscrits_table.pack(fill=tk.BOTH, expand=True)

        self.echeances_label = ttk.Label(self.content, text="", style="Muted.TLabel")
        self.echeances_label.pack(anchor="w", pady=(10, 4))
        self.echeances_table = DataTable(self.content, ECHEANCES_COLUMNS)
        self.echeances_table.pack(fill=tk.BOTH, expand=True)

        self.toolbar.add_button("＋ Inscrire un étudiant", self.inscrire, accent=True)
        self.toolbar.add_button("✎ Modifier", self.edit_selected)
        self.toolbar.add_button("⏹ Enregistrer une sortie", self.enregistrer_sortie)
        self.toolbar.add_button("🗑 Supprimer", self.delete_selected)
        self.toolbar.add_button("📋 Échéancier", self.show_echeancier_selected)

    def refresh(self) -> None:
        self._classes = self.services.referentiel.list_classes()
        labels = [f"{c.libelle} (ID {c.id_classe})" for c in self._classes]
        self.classe_combo.configure(values=labels)
        current = self.classe_var.get()
        if current not in labels:
            self.classe_var.set(labels[0] if labels else "")
        rows = []
        classe = self._selected_classe()
        if classe is not None:
            for inscrit in self.services.enrollments.list_by_classe(classe.id_classe):
                rows.append({
                    "id_inscription": inscrit.id_inscription,
                    "num_inscription": inscrit.num_inscription,
                    "matricule": inscrit.matricule,
                    "nom_complet": inscrit.nom_complet,
                    "classe": inscrit.classe,
                    "date_inscription": inscrit.date_inscription,
                    "redoublant": inscrit.redoublant,
                    "statut": inscrit.statut,
                    "__entity__": inscrit,
                })
        self.inscrits_table.set_rows(rows)
        self.echeances_label.configure(
            text="Sélectionnez un inscrit pour voir son échéancier d’écolage.")

    def _selected_classe(self):
        for classe in self._classes:
            if self.classe_var.get() == f"{classe.libelle} (ID {classe.id_classe})":
                return classe
        return None

    # ----- Inscription -----

    def inscrire(self) -> None:
        etudiants = self.services.students.search(None, 2000)
        if not etudiants:
            show_info("Créez d’abord un étudiant dans l’écran Étudiants.",
                      "Aucun étudiant", parent=self)
            return
        etudiant_labels = [f"{e.matricule or ''} — {e.nom_complet}" for e in etudiants]
        classe = self._selected_classe()
        fields = [
            dict(label="Étudiant *", kind="choice", width=40,
                 values=etudiant_labels, row=0, column=0),
            dict(label="Classe *", kind="choice", width=32,
                 values=[f"{c.libelle} (ID {c.id_classe})"
                         for c in self._classes],
                 initial=(f"{classe.libelle} (ID {classe.id_classe})"
                          if classe else None), row=1, column=0),
            dict(label="N° inscription (auto si vide)", kind="text", width=18,
                 row=2, column=0),
            dict(label="Date d’inscription", kind="date",
                 initial=__import__("datetime").datetime.now(), row=2, column=1),
            dict(label="Redoublant", kind="bool", row=3, column=0),
        ]

        def submit(values):
            index = etudiant_labels.index(values["Étudiant"]) \
                if values["Étudiant"] in etudiant_labels else -1
            if index < 0:
                from ltadmin.core.result import Result
                return Result.fail("Sélectionnez un étudiant.", "VALIDATION")
            classe_label = values["Classe"] or ""
            id_classe = None
            for c in self._classes:
                if classe_label == f"{c.libelle} (ID {c.id_classe})":
                    id_classe = c.id_classe
                    break
            try:
                date_inscription = parse_date(values["Date d’inscription"])
            except ValueError as ex:
                return Result.fail(str(ex), "VALIDATION")
            inscription = Inscription(
                id_etudiant=etudiants[index].id_etudiant,
                id_classe=id_classe,
                num_inscription=values["N° inscription (auto si vide)"] or None,
                date_inscription=date_inscription,
                redoublant=values["Redoublant"],
                statut="INSCRIT",
            )
            return self.services.enrollments.inscrire(
                inscription, self.session.login)

        if run_entity_dialog(self, "Inscrire un étudiant", fields, submit,
                             "Inscrire", two_columns=False):
            self.refresh()

    def edit_selected(self) -> None:
        row = self.inscrits_table.require_selection(parent=self)
        if row is None:
            return
        inscrit = row["__entity__"]

        fields = [
            dict(label="N° inscription", kind="text", width=18,
                 initial=inscrit.num_inscription, row=0, column=0),
            dict(label="Date d’inscription", kind="date",
                 initial=inscrit.date_inscription, row=0, column=1),
            dict(label="Statut", kind="choice", width=16,
                 values=["INSCRIT", "SORTI", "TRANSFERÉ"],
                 initial=inscrit.statut, row=1, column=0),
            dict(label="Redoublant", kind="bool", initial=inscrit.redoublant,
                 row=1, column=1),
        ]

        def submit(values):
            try:
                inscrit.date_inscription = parse_date(values["Date d’inscription"])
            except ValueError as ex:
                from ltadmin.core.result import Result
                return Result.fail(str(ex), "VALIDATION")
            inscrit.num_inscription = values["N° inscription"] or None
            inscrit.statut = values["Statut"]
            inscrit.redoublant = values["Redoublant"]
            return self.services.enrollments.update(inscrit,
                                                    self.session.login)

        if run_entity_dialog(self, f"Modifier l’inscription "
                                   f"{inscrit.num_inscription}", fields, submit):
            self.refresh()

    def enregistrer_sortie(self) -> None:
        row = self.inscrits_table.require_selection(parent=self)
        if row is None:
            return
        inscrit = row["__entity__"]
        fields = [
            dict(label="Date de sortie *", kind="date",
                 initial=__import__("datetime").datetime.now(), row=0, column=0,
                 required=True),
            dict(label="Motif de sortie", kind="memo", width=36, row=1, column=0),
        ]

        def submit(values):
            try:
                date_sortie = parse_date(values["Date de sortie"])
            except ValueError as ex:
                from ltadmin.core.result import Result
                return Result.fail(str(ex), "VALIDATION")
            return self.services.enrollments.enregistrer_sortie(
                inscrit.id_inscription, date_sortie, values["Motif de sortie"],
                self.session.login)

        if run_entity_dialog(self, f"Sortie de {inscrit.nom_complet}", fields,
                             submit, "Enregistrer la sortie", two_columns=False):
            self.refresh()

    def delete_selected(self) -> None:
        row = self.inscrits_table.require_selection(parent=self)
        if row is None:
            return
        inscrit = row["__entity__"]
        if not confirm(f"Supprimer l’inscription de « {inscrit.nom_complet} » "
                       f"({inscrit.num_inscription}) ?\n\nLa suppression sera "
                       "refusée par la base si des notes, bulletins ou paiements "
                       "sont rattachés.", "Suppression", parent=self):
            return
        if show_result(self.services.enrollments.delete(
                inscrit.id_inscription, self.session.login), parent=self):
            self.refresh()

    # ----- Échéancier -----

    def show_echeancier_selected(self) -> None:
        row = self.inscrits_table.require_selection(parent=self)
        if row:
            self.show_echeancier(row)

    def show_echeancier(self, row: dict) -> None:
        inscrit = row["__entity__"]
        echeances = self.services.ecolage.list_echeances(inscrit.id_inscription)
        rows = []
        for echeance in echeances:
            rows.append({
                "libelle": echeance.libelle,
                "num_tranche": echeance.num_tranche,
                "date_echeance": echeance.date_echeance,
                "montant_du": echeance.montant_du,
                "remise": echeance.remise,
                "total_paye": echeance.total_paye,
                "reste": echeance.reste,
                "statut": echeance.statut,
            })
        self.echeances_table.set_rows(rows)
        total_du = sum((e.montant_du or 0 for e in echeances))
        total_paye = sum((e.total_paye for e in echeances))
        self.echeances_label.configure(
            text=f"Échéancier de {inscrit.nom_complet} — "
                 f"dû {total_du:,.0f} / payé {total_paye:,.0f} / "
                 f"reste {total_du - total_paye:,.0f}".replace(",", " "))
