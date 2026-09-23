"""Écran Notes : périodes, évaluations et grille de saisie des notes.

La grille est éditable ligne à ligne ; une période clôturée fige la saisie.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ltadmin.models.entities import Evaluation, PeriodeEval
from ltadmin.ui.dialogs import run_entity_dialog
from ltadmin.ui.views.base_view import BaseView
from ltadmin.ui.widgets import DataTable, confirm, show_error, show_result

EVAL_COLUMNS = [
    ("id_evaluation", "ID", -1, "w"),
    ("intitule", "Intitulé", 200, "w"),
    ("matiere", "Matière", 160, "w"),
    ("nature", "Nature", 90, "w"),
    ("bareme", "Barème", 60, "e"),
    ("poids", "Poids", 60, "e"),
    ("publiee", "Publiée", 70, "center"),
    ("periode_cloturee", "Période clôturée", 110, "center"),
]

NOTE_COLUMNS = [
    ("id_inscription", "ID", -1, "w"),
    ("matricule", "Matricule", 120, "w"),
    ("nom_complet", "Étudiant", 240, "w"),
    ("valeur_note", "Note", 80, "e"),
    ("absent", "Absent", 70, "center"),
    ("observation", "Observation", 200, "w"),
]


class GradesView(BaseView):
    title = "Notes et évaluations"
    subtitle = "Périodes d’évaluation, devoirs et saisie des notes"

    def __init__(self, parent, services, session, **kwargs):
        super().__init__(parent, services, session, **kwargs)
        self._classes = []
        self._periodes = []
        self._evaluations = []
        self._grille = []
        self._selected_evaluation = None

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

        panes = ttk.PanedWindow(self.content, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(panes)
        self.eval_table = DataTable(left, EVAL_COLUMNS,
                                    on_refresh=self.refresh)
        self.eval_table.pack(fill=tk.BOTH, expand=True)
        self.eval_table.tree.bind("<<TreeviewSelect>>",
                                  lambda _e: self._load_grille())
        panes.add(left, weight=1)

        right = ttk.Frame(panes)
        self.note_table = DataTable(right, NOTE_COLUMNS)
        self.note_table.pack(fill=tk.BOTH, expand=True)
        self._build_quick_editor(right)
        panes.add(right, weight=2)

        self.toolbar.add_button("＋ Nouvelle période", self.create_periode)
        self.toolbar.add_button("🔒 Clôturer / rouvrir la période",
                                self.toggle_periode)
        self.toolbar.add_button("＋ Nouvelle évaluation", self.create_evaluation,
                                accent=True)
        self.toolbar.add_button("📣 Publier / retirer", self.toggle_publiee)
        self.toolbar.add_button("🗑 Supprimer l’évaluation", self.delete_evaluation)

    def _build_quick_editor(self, parent) -> None:
        editor = ttk.Frame(parent, style="Card.TFrame", padding=(12, 10))
        editor.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(editor, text="Saisie rapide (ligne sélectionnée) :",
                  style="Card.TLabel").pack(anchor="w")
        row = ttk.Frame(editor)
        row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(row, text="Note :").pack(side=tk.LEFT)
        self.note_var = tk.StringVar()
        note_entry = ttk.Entry(row, textvariable=self.note_var, width=8)
        note_entry.pack(side=tk.LEFT, padx=(4, 12))
        note_entry.bind("<Return>", lambda _e: self.save_note())
        self.absent_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row, text="Absent", variable=self.absent_var).pack(side=tk.LEFT)
        ttk.Label(row, text="Observation :").pack(side=tk.LEFT, padx=(12, 4))
        self.observation_var = tk.StringVar()
        observation_entry = ttk.Entry(row, textvariable=self.observation_var,
                                      width=24)
        observation_entry.pack(side=tk.LEFT)
        observation_entry.bind("<Return>", lambda _e: self.save_note())
        ttk.Button(row, text="Enregistrer", style="Accent.TButton",
                   command=self.save_note).pack(side=tk.LEFT, padx=12)

    # ----- Chargement -----

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

        id_classe = self._id_classe()
        id_periode = self._id_periode()
        self._evaluations = self.services.evaluations.list_evaluations(
            id_periode=id_periode, id_classe=id_classe)
        rows = []
        for evaluation in self._evaluations:
            rows.append({
                "id_evaluation": evaluation.id_evaluation,
                "intitule": evaluation.intitule,
                "matiere": evaluation.matiere,
                "nature": evaluation.nature,
                "bareme": evaluation.bareme,
                "poids": evaluation.poids,
                "publiee": evaluation.publiee,
                "periode_cloturee": evaluation.periode_cloturee,
                "__entity__": evaluation,
            })
        self.eval_table.set_rows(rows)
        self._selected_evaluation = None
        self.note_table.set_rows([])

    def _id_classe(self) -> Optional[int]:
        for classe in self._classes:
            if self.classe_var.get() == f"{classe.libelle} (ID {classe.id_classe})":
                return classe.id_classe
        return None

    def _id_periode(self) -> Optional[int]:
        for periode in self._periodes:
            if self.periode_var.get() == f"{periode.libelle or periode.code_periode} (ID {periode.id_periode})":
                return periode.id_periode
        return None

    def _load_grille(self) -> None:
        row = self.eval_table.selected_row()
        if row is None:
            return
        evaluation = row["__entity__"]
        self._selected_evaluation = evaluation
        self._grille = self.services.grades.get_grille_saisie(
            evaluation.id_evaluation)
        rows = []
        for saisie in self._grille:
            rows.append({
                "id_inscription": saisie.id_inscription,
                "matricule": saisie.matricule,
                "nom_complet": f"{saisie.nom or ''} {saisie.prenom or ''}".strip(),
                "valeur_note": saisie.valeur_note,
                "absent": saisie.absent,
                "observation": saisie.observation,
            })
        self.note_table.set_rows(rows)

    # ----- Périodes -----

    def create_periode(self) -> None:
        fields = [
            dict(label="Code période *", kind="text", width=12, required=True,
                 row=0, column=0),
            dict(label="Libellé", kind="text", width=24, row=0, column=1),
            dict(label="Pondération", kind="float", width=8, initial=1.0,
                 row=1, column=0),
            dict(label="Ordre", kind="int", width=6, row=1, column=1),
            dict(label="Date de début", kind="date", row=2, column=0),
            dict(label="Date de fin", kind="date", row=2, column=1),
        ]

        def submit(values):
            periode = PeriodeEval(
                id_annee=None,  # le service rattache à l'année active
                code_periode=values["Code période *"],
                libelle=values["Libellé"],
                ponderation=values["Pondération"],
            )
            return self.services.evaluations.create_periode(
                periode, self.session.login)

        if run_entity_dialog(self, "Nouvelle période d’évaluation", fields,
                             submit, "Créer la période"):
            self.refresh()

    def toggle_periode(self) -> None:
        id_periode = self._id_periode()
        if id_periode is None:
            show_error("Sélectionnez d’abord une période.", "Aucune période",
                       parent=self)
            return
        periode = self.services.evaluations.get_periode(id_periode)
        cloturee = bool(periode and periode.cloturee)
        if not confirm(("Rouvrir" if cloturee else "Clôturer")
                       + f" la période « {periode.libelle} » ?"
                       + ("" if cloturee
                          else "\n\nLes notes déjà saisies seront figées."),
                       "Confirmation", parent=self):
            return
        if show_result(self.services.evaluations.set_periode_cloturee(
                id_periode, not cloturee, self.session.login), parent=self):
            self.refresh()

    # ----- Évaluations -----

    def create_evaluation(self) -> None:
        id_classe = self._id_classe()
        id_periode = self._id_periode()
        if id_classe is None or id_periode is None:
            show_error("Sélectionnez une classe et une période.", "Filtres requis",
                       parent=self)
            return
        programmes = self.services.referentiel.list_classes_detail()
        # Programmes = matière × classe : on passe par le dépôt via les
        # détails de programme de la classe.
        programmes_classe = []
        for classe_detail in programmes:
            if classe_detail.id_classe == id_classe:
                programmes_classe = self._programmes_of(classe_detail.id_classe)
                break
        if not programmes_classe:
            show_info_message = "Aucune matière programmée pour cette classe : " \
                                "définissez d’abord le programme (Formateurs)."
            show_error(show_info_message, "Programme vide", parent=self)
            return
        programme_labels = [f"{p.matiere or p.code_matiere} (coef "
                            f"{p.coefficient or '?'})" for p in programmes_classe]
        fields = [
            dict(label="Programme (matière) *", kind="choice", width=36,
                 values=programme_labels, row=0, column=0),
            dict(label="Intitulé *", kind="text", width=30, required=True,
                 row=1, column=0),
            dict(label="Nature", kind="choice", values=["DEVOIR", "INTERRO",
                                                        "TP", "PROJET"],
                 initial="DEVOIR", row=1, column=1),
            dict(label="Barème", kind="float", width=8, initial=20.0,
                 row=2, column=0),
            dict(label="Poids", kind="float", width=8, initial=1.0,
                 row=2, column=1),
        ]

        def submit(values):
            index = programme_labels.index(values["Programme (matière) *"]) \
                if values["Programme (matière) *"] in programme_labels else -1
            if index < 0:
                from ltadmin.core.result import Result
                return Result.fail("Sélectionnez une matière.", "VALIDATION")
            evaluation = Evaluation(
                id_periode=id_periode,
                id_prog=programmes_classe[index].id_prog,
                intitule=values["Intitulé *"],
                nature=values["Nature"],
                bareme=values["Barème"],
                poids=values["Poids"],
                publiee=False,
            )
            return self.services.evaluations.create_evaluation(
                evaluation, self.session.login)

        if run_entity_dialog(self, "Nouvelle évaluation", fields, submit,
                             "Créer l’évaluation"):
            self.refresh()

    def _programmes_of(self, id_classe: int):
        """Programmes (matière × classe) pour le combo d'évaluation."""
        try:
            from ltadmin.repositories.staff_repository import StaffRepository
            repo = StaffRepository(self.services.database)
            return repo.list_by_classe(id_classe)
        except Exception:
            return []

    def toggle_publiee(self) -> None:
        row = self.eval_table.require_selection(parent=self)
        if row is None:
            return
        evaluation = row["__entity__"]
        publiee = bool(evaluation.publiee)
        if show_result(self.services.evaluations.set_publiee(
                evaluation.id_evaluation, not publiee,
                self.session.login), parent=self):
            self.refresh()

    def delete_evaluation(self) -> None:
        row = self.eval_table.require_selection(parent=self)
        if row is None:
            return
        evaluation = row["__entity__"]
        if not confirm(f"Supprimer l’évaluation « {evaluation.intitule} » ?",
                       "Suppression", parent=self):
            return
        if show_result(self.services.evaluations.delete_evaluation(
                evaluation.id_evaluation, self.session.login), parent=self):
            self.refresh()

    # ----- Saisie des notes -----

    def save_note(self) -> None:
        if self._selected_evaluation is None:
            show_error("Sélectionnez d’abord une évaluation à gauche.",
                       "Aucune évaluation", parent=self)
            return
        row = self.note_table.selected_row()
        if row is None:
            show_error("Sélectionnez l’étudiant dans la grille.",
                       "Aucune sélection", parent=self)
            return
        raw = self.note_var.get().strip()
        valeur = None
        if raw:
            try:
                valeur = float(raw.replace(",", "."))
            except ValueError:
                show_error("Note invalide : saisissez un nombre "
                           "(ou cochez « absent »).", "Saisie", parent=self)
                return
        absent = bool(self.absent_var.get())
        result = self.services.grades.upsert_note(
            self._selected_evaluation.id_evaluation,
            row["id_inscription"], valeur, absent,
            self.observation_var.get() or None, self.session.login)
        if show_result(result, parent=self):
            self._load_grille()
            # Ligne suivante : avancer la sélection pour la saisie suivante.
            selection = self.note_table.tree.selection()
            if selection:
                suivant = self.note_table.tree.next(selection[0])
                if suivant:
                    self.note_table.tree.selection_set(suivant)
                    self.note_table.tree.see(suivant)
            self.note_var.set("")
            self.absent_var.set(False)
            self.observation_var.set("")
            self.note_table.focus_set()
