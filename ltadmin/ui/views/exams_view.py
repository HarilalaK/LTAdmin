"""Écran Examens : sessions, épreuves, saisie des notes et résultats finaux."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ltadmin.models.entities import Epreuve, SessionExam
from ltadmin.ui.dialogs import run_entity_dialog
from ltadmin.ui.views.base_view import BaseView
from ltadmin.ui.widgets import DataTable, confirm, show_error, show_result

SESSION_COLUMNS = [
    ("id_session", "ID", -1, "w"),
    ("libelle", "Session", 200, "w"),
    ("nature", "Nature", 110, "w"),
    ("date_debut", "Du", 100, "center"),
    ("date_fin", "Au", 100, "center"),
    ("cloturee", "Clôturée", 80, "center"),
]

EPREUVE_COLUMNS = [
    ("id_epreuve", "ID", -1, "w"),
    ("classe", "Classe", 160, "w"),
    ("matiere", "Matière", 160, "w"),
    ("date_epreuve", "Date", 100, "center"),
    ("heure_debut", "Heure", 80, "center"),
    ("duree_mn", "Durée", 60, "center"),
    ("coefficient", "Coef", 60, "e"),
    ("bareme", "Barème", 60, "e"),
    ("salle", "Salle", 100, "w"),
]

NOTE_EXAM_COLUMNS = [
    ("id_inscription", "ID", -1, "w"),
    ("matricule", "Matricule", 120, "w"),
    ("nom_complet", "Étudiant", 240, "w"),
    ("valeur_note", "Note", 80, "e"),
    ("absent", "Absent", 70, "center"),
]

RESULTAT_COLUMNS = [
    ("id_inscription", "ID", -1, "w"),
    ("matricule", "Matricule", 110, "w"),
    ("nom_complet", "Étudiant", 220, "w"),
    ("moy_cc", "Moy. CC", 90, "e"),
    ("moy_exam", "Moy. examen", 100, "e"),
    ("moyenne_gen", "Moy. générale", 110, "e"),
    ("rang", "Rang", 60, "center"),
    ("mention", "Mention", 110, "w"),
    ("decision", "Décision", 90, "w"),
]


class ExamsView(BaseView):
    title = "Examens"
    subtitle = "Sessions, épreuves, notes d’examen et résultats finaux"

    def __init__(self, parent, services, session, **kwargs):
        super().__init__(parent, services, session, **kwargs)
        self._sessions = []
        self._classes = []
        self._selected_epreuve = None

        top = ttk.Frame(self.content)
        top.pack(fill=tk.X)
        ttk.Label(top, text="Sessions d’examen", style="Subtitle.TLabel").pack(
            anchor="w", pady=(0, 4))
        self.session_table = DataTable(top, SESSION_COLUMNS)
        self.session_table.pack(fill=tk.X)
        self.session_table.tree.bind("<<TreeviewSelect>>",
                                     lambda _e: self._load_epreuves())

        panes = ttk.PanedWindow(self.content, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        left = ttk.Frame(panes)
        ttk.Label(left, text="Épreuves", style="Muted.TLabel").pack(anchor="w")
        self.epreuve_table = DataTable(left, EPREUVE_COLUMNS)
        self.epreuve_table.pack(fill=tk.BOTH, expand=True)
        self.epreuve_table.tree.bind("<<TreeviewSelect>>",
                                     lambda _e: self._load_notes())
        panes.add(left, weight=3)

        right = ttk.Frame(panes)
        ttk.Label(right, text="Notes de l’épreuve sélectionnée",
                  style="Muted.TLabel").pack(anchor="w")
        self.note_table = DataTable(right, NOTE_EXAM_COLUMNS)
        self.note_table.pack(fill=tk.BOTH, expand=True)
        editor = ttk.Frame(right, style="Card.TFrame", padding=(10, 8))
        editor.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(editor, text="Note :", style="Card.TLabel").pack(side=tk.LEFT)
        self.note_var = tk.StringVar()
        entry = ttk.Entry(editor, textvariable=self.note_var, width=8)
        entry.pack(side=tk.LEFT, padx=(4, 12))
        entry.bind("<Return>", lambda _e: self.save_note())
        self.absent_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(editor, text="Absent",
                        variable=self.absent_var).pack(side=tk.LEFT)
        ttk.Label(editor, text="N° copie :", style="Card.TLabel").pack(
            side=tk.LEFT, padx=(12, 4))
        self.copie_var = tk.StringVar()
        ttk.Entry(editor, textvariable=self.copie_var, width=10).pack(side=tk.LEFT)
        ttk.Button(editor, text="Enregistrer", style="Accent.TButton",
                   command=self.save_note).pack(side=tk.LEFT, padx=12)
        panes.add(right, weight=2)

        ttk.Label(self.content, text="Résultats finaux (classe sélectionnée)",
                  style="Muted.TLabel").pack(anchor="w", pady=(10, 4))
        result_frame = ttk.Frame(self.content)
        result_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(result_frame, text="Classe :").pack(side=tk.LEFT)
        self.classe_var = tk.StringVar()
        self.classe_combo = ttk.Combobox(result_frame, textvariable=self.classe_var,
                                         state="readonly", width=30)
        self.classe_combo.pack(side=tk.LEFT, padx=8)
        self.classe_combo.bind("<<ComboboxSelected>>",
                               lambda _e: self._load_resultats())
        self.resultat_table = DataTable(result_frame, RESULTAT_COLUMNS)
        self.resultat_table.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        self.toolbar.add_button("＋ Nouvelle session", self.create_session)
        self.toolbar.add_button("🔒 Clôturer / rouvrir", self.toggle_session)
        self.toolbar.add_button("＋ Nouvelle épreuve", self.create_epreuve,
                                accent=True)
        self.toolbar.add_button("🗑 Supprimer l’épreuve", self.delete_epreuve)
        self.toolbar.add_button("🏁 Calculer les résultats finaux",
                                self.generer_resultats)

    def refresh(self) -> None:
        self._sessions = self.services.exams.list_sessions()
        self.session_table.set_rows([{
            "id_session": s.id_session,
            "libelle": s.libelle,
            "nature": s.nature,
            "date_debut": s.date_debut,
            "date_fin": s.date_fin,
            "cloturee": s.cloturee,
            "__entity__": s,
        } for s in self._sessions])
        self._classes = self.services.referentiel.list_classes()
        labels = [f"{c.libelle} (ID {c.id_classe})" for c in self._classes]
        self.classe_combo.configure(values=labels)
        if self.classe_var.get() not in labels:
            self.classe_var.set(labels[0] if labels else "")
        self._load_epreuves()
        self._load_resultats()

    def _selected_session(self):
        row = self.session_table.selected_row()
        return row["__entity__"] if row else None

    def _selected_classe_id(self) -> Optional[int]:
        for classe in self._classes:
            if self.classe_var.get() == f"{classe.libelle} (ID {classe.id_classe})":
                return classe.id_classe
        return None

    def _load_epreuves(self) -> None:
        session = self._selected_session()
        epreuves = self.services.exams.list_epreuves(
            id_session=session.id_session if session else None)
        self.epreuve_table.set_rows([{
            "id_epreuve": e.id_epreuve,
            "classe": e.classe,
            "matiere": e.matiere,
            "date_epreuve": e.date_epreuve,
            "heure_debut": e.heure_debut,
            "duree_mn": e.duree_mn,
            "coefficient": e.coefficient,
            "bareme": e.bareme,
            "salle": e.salle,
            "__entity__": e,
        } for e in epreuves])
        self._load_notes()

    def _load_notes(self) -> None:
        row = self.epreuve_table.selected_row()
        if row is None:
            self.note_table.set_rows([])
            self._selected_epreuve = None
            return
        epreuve = row["__entity__"]
        self._selected_epreuve = epreuve
        grille = self.services.exams.get_grille_saisie(epreuve.id_epreuve)
        self.note_table.set_rows([{
            "id_inscription": g.id_inscription,
            "matricule": g.matricule,
            "nom_complet": f"{g.nom or ''} {g.prenom or ''}".strip(),
            "valeur_note": g.valeur_note,
            "absent": g.absent,
        } for g in grille])

    def _load_resultats(self) -> None:
        id_classe = self._selected_classe_id()
        rows = []
        if id_classe is not None:
            inscrits = {i.id_inscription: i for i in
                        self.services.enrollments.list_by_classe(id_classe)}
            for resultat in self.services.exams.list_resultats(id_classe):
                inscrit = inscrits.get(resultat.id_inscription)
                rows.append({
                    "id_inscription": resultat.id_inscription,
                    "matricule": inscrit.matricule if inscrit else "",
                    "nom_complet": inscrit.nom_complet if inscrit else "",
                    "moy_cc": resultat.moy_cc,
                    "moy_exam": resultat.moy_exam,
                    "moyenne_gen": resultat.moyenne_gen,
                    "rang": resultat.rang,
                    "mention": resultat.mention,
                    "decision": resultat.decision,
                })
        self.resultat_table.set_rows(rows)

    # ----- Sessions -----

    def create_session(self) -> None:
        fields = [
            dict(label="Libellé *", kind="text", width=28, required=True,
                 row=0, column=0),
            dict(label="Nature", kind="choice", values=["EXAMEN FINAL",
                                                        "EXAMEN BLANC",
                                                        "RATTRAPAGE"],
                 initial="EXAMEN FINAL", row=0, column=1),
            dict(label="Date de début", kind="date", row=1, column=0),
            dict(label="Date de fin", kind="date", row=1, column=1),
        ]

        def submit(values):
            from ltadmin.ui.widgets import parse_date
            try:
                session = SessionExam(
                    libelle=values["Libellé"],
                    nature=values["Nature"],
                    date_debut=parse_date(values["Date de début"]),
                    date_fin=parse_date(values["Date de fin"]),
                )
            except ValueError as ex:
                from ltadmin.core.result import Result
                return Result.fail(str(ex), "VALIDATION")
            return self.services.exams.create_session(session,
                                                      self.session.login)

        if run_entity_dialog(self, "Nouvelle session d’examen", fields, submit,
                             "Créer la session"):
            self.refresh()

    def toggle_session(self) -> None:
        session = self._selected_session()
        if session is None:
            show_error("Sélectionnez d’abord une session.", "Aucune sélection",
                       parent=self)
            return
        cloturee = bool(session.cloturee)
        if not confirm(("Rouvrir" if cloturee else "Clôturer")
                       + f" la session « {session.libelle} » ?",
                       "Confirmation", parent=self):
            return
        if show_result(self.services.exams.set_session_cloturee(
                session.id_session, not cloturee, self.session.login),
                parent=self):
            self.refresh()

    # ----- Épreuves -----

    def create_epreuve(self) -> None:
        session = self._selected_session()
        if session is None:
            show_error("Sélectionnez d’abord une session.", "Aucune session",
                       parent=self)
            return
        salles = self.services.referentiel.list_salles()
        salle_labels = ["(aucune)"] + [f"{s.nom_salle} (ID {s.id_salle})"
                                       for s in salles]
        classes = self.services.referentiel.list_classes()
        classe_labels = [f"{c.libelle} (ID {c.id_classe})" for c in classes]
        matieres = self.services.referentiel.list_matieres()
        matiere_labels = [f"{m.libelle or m.code_matiere} ({m.code_matiere})"
                          for m in matieres]
        fields = [
            dict(label="Classe *", kind="choice", width=30, values=classe_labels,
                 required=True, row=0, column=0),
            dict(label="Matière *", kind="choice", width=30, values=matiere_labels,
                 required=True, row=0, column=1),
            dict(label="Date de l’épreuve", kind="date", row=1, column=0),
            dict(label="Heure de début (HH:mm)", kind="text", width=8,
                 initial="08:00", row=1, column=1),
            dict(label="Durée (minutes)", kind="int", width=8, initial=120,
                 row=2, column=0),
            dict(label="Salle", kind="choice", width=24, values=salle_labels,
                 row=2, column=1),
            dict(label="Coefficient", kind="float", width=8, initial=1.0,
                 row=3, column=0),
            dict(label="Barème", kind="float", width=8, initial=20.0,
                 row=3, column=1),
            dict(label="Surveillant", kind="text", width=28, row=4, column=0),
        ]

        def submit(values):
            from ltadmin.core.result import Result
            from ltadmin.ui.widgets import parse_date
            classe_label = values["Classe"] or ""
            id_classe = None
            for classe in classes:
                if classe_label == f"{classe.libelle} (ID {classe.id_classe})":
                    id_classe = classe.id_classe
                    break
            matiere_label = values["Matière"] or ""
            code_matiere = None
            for matiere in matieres:
                if matiere_label == f"{matiere.libelle or matiere.code_matiere} ({matiere.code_matiere})":
                    code_matiere = matiere.code_matiere
                    break
            if id_classe is None or code_matiere is None:
                return Result.fail("Sélectionnez une classe et une matière.",
                                   "VALIDATION")
            salle_label = values["Salle"] or ""
            id_salle = None
            for salle in salles:
                if salle_label == f"{salle.nom_salle} (ID {salle.id_salle})":
                    id_salle = salle.id_salle
                    break
            try:
                date_epreuve = parse_date(values["Date de l’épreuve"])
            except ValueError as ex:
                return Result.fail(str(ex), "VALIDATION")
            epreuve = Epreuve(
                id_session=session.id_session,
                id_classe=id_classe,
                code_matiere=code_matiere,
                date_epreuve=date_epreuve,
                heure_debut=values["Heure de début (HH:mm)"],
                duree_mn=values["Durée (minutes)"],
                coefficient=values["Coefficient"],
                bareme=values["Barème"],
                id_salle=id_salle,
                surveillant=values["Surveillant"],
            )
            return self.services.exams.create_epreuve(epreuve,
                                                     self.session.login)

        if run_entity_dialog(self, "Nouvelle épreuve", fields, submit,
                             "Créer l’épreuve"):
            self._load_epreuves()

    def delete_epreuve(self) -> None:
        row = self.epreuve_table.require_selection(parent=self)
        if row is None:
            return
        epreuve = row["__entity__"]
        if not confirm(f"Supprimer l’épreuve « {epreuve.matiere} » ?",
                       "Suppression", parent=self):
            return
        if show_result(self.services.exams.delete_epreuve(
                epreuve.id_epreuve, self.session.login), parent=self):
            self._load_epreuves()

    # ----- Notes et résultats -----

    def save_note(self) -> None:
        if self._selected_epreuve is None:
            show_error("Sélectionnez d’abord une épreuve.", "Aucune épreuve",
                       parent=self)
            return
        row = self.note_table.selected_row()
        if row is None:
            show_error("Sélectionnez un étudiant dans la grille.",
                       "Aucune sélection", parent=self)
            return
        raw = self.note_var.get().strip()
        valeur = None
        if raw:
            try:
                valeur = float(raw.replace(",", "."))
            except ValueError:
                show_error("Note invalide : saisissez un nombre.",
                           "Saisie", parent=self)
                return
        result = self.services.exams.upsert_note(
            self._selected_epreuve.id_epreuve, row["id_inscription"],
            valeur, bool(self.absent_var.get()),
            self.copie_var.get() or None, self.session.login)
        if show_result(result, parent=self):
            self._load_notes()
            self.note_var.set("")
            self.absent_var.set(False)
            self.copie_var.set("")

    def generer_resultats(self) -> None:
        session = self._selected_session()
        id_classe = self._selected_classe_id()
        if session is None or id_classe is None:
            show_error("Sélectionnez une session (grille du haut) et une classe "
                       "(grille des résultats).", "Sélections requises",
                       parent=self)
            return
        if not confirm("Calculer (ou recalculer) les résultats finaux de la "
                       "classe pour cette session ?\n\nMoyenne CC = moyennes "
                       "des bulletins ; moyenne examen = notes d’examen "
                       "pondérées.", "Calcul des résultats", parent=self):
            return
        if show_result(self.services.exams.generer_resultats(
                id_classe, session.id_session, self.session.login),
                parent=self):
            self._load_resultats()
