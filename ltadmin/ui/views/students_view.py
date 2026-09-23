"""Écran Étudiants : recherche, création, modification, suppression."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ltadmin.models.entities import Etudiant
from ltadmin.ui.dialogs import run_entity_dialog
from ltadmin.ui.views.base_view import BaseView
from ltadmin.ui.widgets import (DataTable, confirm, parse_date, show_error,
                                show_result)

COLUMNS = [
    ("id_etudiant", "ID", -1, "w"),
    ("matricule", "Matricule", 130, "w"),
    ("nom_complet", "Nom et prénom", 260, "w"),
    ("sexe", "Sexe", 60, "center"),
    ("date_naissance", "Naissance", 100, "center"),
    ("tel", "Téléphone", 120, "w"),
    ("email", "E-mail", 180, "w"),
    ("statut", "Statut", 100, "w"),
]


class StudentsView(BaseView):
    title = "Étudiants"
    subtitle = "Dossiers étudiants : création, modification, suppression"

    def __init__(self, parent, services, session, **kwargs):
        super().__init__(parent, services, session, **kwargs)
        self.search_var = tk.StringVar()
        search_frame = ttk.Frame(self.content)
        search_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(search_frame, text="Recherche :").pack(side=tk.LEFT)
        entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        entry.pack(side=tk.LEFT, padx=8, ipady=2)
        entry.bind("<Return>", lambda _e: self.refresh())
        ttk.Button(search_frame, text="Rechercher",
                   command=self.refresh).pack(side=tk.LEFT)

        self.table = DataTable(self.content, COLUMNS,
                               on_double_click=self.edit_student,
                               on_delete=self.delete_student,
                               on_refresh=self.refresh)
        self.table.pack(fill=tk.BOTH, expand=True)

        self.toolbar.add_button("＋ Nouvel étudiant", self.create_student,
                                accent=True)
        self.toolbar.add_button("✎ Modifier", self.edit_student_selected)
        self.toolbar.add_button("🗑 Supprimer", self.delete_student_selected)
        self.toolbar.add_label("Double-clic : modifier — Suppr : supprimer — "
                               "F5 : actualiser")

    def refresh(self) -> None:
        rows = []
        for etudiant in self.services.students.search(self.search_var.get() or None):
            rows.append({
                "id_etudiant": etudiant.id_etudiant,
                "matricule": etudiant.matricule,
                "nom_complet": etudiant.nom_complet,
                "sexe": etudiant.sexe,
                "date_naissance": etudiant.date_naissance,
                "tel": etudiant.tel,
                "email": etudiant.email,
                "statut": etudiant.statut,
                "__entity__": etudiant,
            })
        self.table.set_rows(rows)

    # ----- Actions -----

    def _student_fields(self, etudiant: Optional[Etudiant]) -> list:
        e = etudiant or Etudiant()
        return [
            dict(label="Matricule (auto si vide)", kind="text", width=18,
                 initial=e.matricule, row=0, column=0),
            dict(label="Statut", kind="choice", values=["ACTIF", "INACTIF", "DIPLOMÉ",
                                                        "EXCLU"],
                 initial=e.statut or "ACTIF", row=0, column=1),
            dict(label="Nom *", kind="text", width=26, initial=e.nom,
                 required=True, row=1, column=0),
            dict(label="Prénom *", kind="text", width=26, initial=e.prenom,
                 required=True, row=1, column=1),
            dict(label="Sexe", kind="choice", values=["M", "F"], initial=e.sexe,
                 row=2, column=0),
            dict(label="Date de naissance", kind="date",
                 initial=e.date_naissance, row=2, column=1),
            dict(label="Lieu de naissance", kind="text", width=26,
                 initial=e.lieu_naissance, row=3, column=0),
            dict(label="CIN", kind="text", width=18, initial=e.cin,
                 row=3, column=1),
            dict(label="Nationalité", kind="text", width=26,
                 initial=e.nationalite, row=4, column=0),
            dict(label="Année du bac", kind="int", width=8,
                 initial=e.annee_bacc, row=4, column=1),
            dict(label="Série du bac", kind="text", width=18,
                 initial=e.serie_bacc, row=5, column=0),
            dict(label="Établissement d’origine", kind="text", width=26,
                 initial=e.etab_origine, row=5, column=1),
            dict(label="Adresse", kind="text", width=26, initial=e.adresse,
                 row=6, column=0),
            dict(label="Téléphone", kind="text", width=18, initial=e.tel,
                 row=6, column=1),
            dict(label="E-mail", kind="text", width=26, initial=e.email,
                 row=7, column=0),
            dict(label="Nom du tuteur", kind="text", width=26,
                 initial=e.nom_tuteur, row=7, column=1),
            dict(label="Téléphone tuteur", kind="text", width=18,
                 initial=e.tel_tuteur, row=8, column=0),
            dict(label="Profession tuteur", kind="text", width=26,
                 initial=e.profession_tuteur, row=8, column=1),
        ]

    def create_student(self) -> None:
        def submit(values):
            etudiant = self._from_values(None, values)
            result = self.services.students.create(etudiant, self.session.login)
            return result
        if run_entity_dialog(self, "Nouvel étudiant", self._student_fields(None),
                             submit, "Créer l’étudiant"):
            self.refresh()

    def edit_student_selected(self) -> None:
        row = self.table.require_selection(parent=self)
        if row:
            self.edit_student(row)

    def edit_student(self, row: dict) -> None:
        etudiant = row.get("__entity__")
        if etudiant is None:
            return

        def submit(values):
            updated = self._from_values(etudiant, values)
            return self.services.students.update(updated, self.session.login)
        if run_entity_dialog(self, f"Modifier {etudiant.matricule or 'l’étudiant'}",
                             self._student_fields(etudiant), submit):
            self.refresh()

    def delete_student_selected(self) -> None:
        row = self.table.require_selection(parent=self)
        if row:
            self.delete_student(row)

    def delete_student(self, row: dict) -> None:
        etudiant = row.get("__entity__")
        if etudiant is None:
            return
        if not confirm(f"Supprimer définitivement l’étudiant "
                       f"« {etudiant.nom_complet} » ({etudiant.matricule}) ?\n\n"
                       "Ses inscriptions et données liées seront conservées "
                       "si la base l’interdit (liaisons Access).",
                       "Suppression", parent=self):
            return
        if show_result(self.services.students.delete(
                etudiant.id_etudiant, self.session.login), parent=self):
            self.refresh()

    def _from_values(self, existing: Optional[Etudiant],
                     values: dict) -> Etudiant:
        etudiant = existing or Etudiant()
        etudiant.matricule = values.get("Matricule (auto si vide)") or None
        etudiant.statut = values.get("Statut")
        etudiant.nom = values.get("Nom")
        etudiant.prenom = values.get("Prénom")
        etudiant.sexe = values.get("Sexe")
        try:
            etudiant.date_naissance = parse_date(values.get("Date de naissance"))
        except ValueError as ex:
            show_error(str(ex), parent=self)
        etudiant.lieu_naissance = values.get("Lieu de naissance")
        etudiant.cin = values.get("CIN")
        etudiant.nationalite = values.get("Nationalité")
        etudiant.annee_bacc = values.get("Année du bac")
        etudiant.serie_bacc = values.get("Série du bac")
        etudiant.etab_origine = values.get("Établissement d’origine")
        etudiant.adresse = values.get("Adresse")
        etudiant.tel = values.get("Téléphone")
        etudiant.email = values.get("E-mail")
        etudiant.nom_tuteur = values.get("Nom du tuteur")
        etudiant.tel_tuteur = values.get("Téléphone tuteur")
        etudiant.profession_tuteur = values.get("Profession tuteur")
        return etudiant
