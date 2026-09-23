"""Écran Emploi du temps : planification, séances et absences."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ltadmin.models.entities import Absence, EmploiDuTemps, Seance
from ltadmin.ui.dialogs import run_entity_dialog
from ltadmin.ui.views.base_view import BaseView
from ltadmin.ui.widgets import DataTable, confirm, show_error, show_result

from ltadmin.services.validation.validation import JOURS_AUTORISES

SLOT_COLUMNS = [
    ("id_edt", "ID", -1, "w"),
    ("jour", "Jour", 90, "w"),
    ("creneau", "Créneau", 130, "w"),
    ("classe", "Classe", 160, "w"),
    ("matiere", "Matière", 160, "w"),
    ("formateur", "Formateur", 180, "w"),
    ("salle", "Salle", 110, "w"),
    ("actif", "Actif", 60, "center"),
]

SEANCE_COLUMNS = [
    ("id_seance", "ID", -1, "w"),
    ("date_seance", "Date", 110, "center"),
    ("classe", "Classe", 150, "w"),
    ("matiere", "Matière", 150, "w"),
    ("creneau", "Créneau", 130, "w"),
    ("nb_heures", "Heures", 70, "e"),
    ("statut", "Statut", 90, "w"),
]


class ScheduleView(BaseView):
    title = "Emploi du temps"
    subtitle = "Planification hebdomadaire, séances réalisées et absences"

    def __init__(self, parent, services, session, **kwargs):
        super().__init__(parent, services, session, **kwargs)
        self._classes = []

        filters = ttk.Frame(self.content)
        filters.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(filters, text="Classe :").pack(side=tk.LEFT)
        self.classe_var = tk.StringVar()
        self.classe_combo = ttk.Combobox(filters, textvariable=self.classe_var,
                                         state="readonly", width=30)
        self.classe_combo.pack(side=tk.LEFT, padx=8)
        self.classe_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())

        self.slot_table = DataTable(self.content, SLOT_COLUMNS,
                                    on_refresh=self.refresh)
        self.slot_table.pack(fill=tk.BOTH, expand=True)

        ttk.Label(self.content, text="Séances réalisées (cahier de texte)",
                  style="Muted.TLabel").pack(anchor="w", pady=(10, 4))
        self.seance_table = DataTable(self.content, SEANCE_COLUMNS)
        self.seance_table.pack(fill=tk.BOTH, expand=True)

        self.toolbar.add_button("＋ Planifier un créneau", self.create_slot,
                                accent=True)
        self.toolbar.add_button("✎ Modifier", self.edit_slot)
        self.toolbar.add_button("🗑 Supprimer", self.delete_slot)
        self.toolbar.add_button("🕐 Séance réalisée", self.create_seance)
        self.toolbar.add_button("❌ Saisir une absence", self.create_absence)

    def refresh(self) -> None:
        self._classes = self.services.referentiel.list_classes()
        labels = ["(toutes)"] + [f"{c.libelle} (ID {c.id_classe})"
                                 for c in self._classes]
        self.classe_combo.configure(values=labels)
        if self.classe_var.get() not in labels:
            self.classe_var.set(labels[0] if labels else "")
        self._load_slots()
        self._load_seances()

    def _id_classe(self) -> Optional[int]:
        for classe in self._classes:
            if self.classe_var.get() == f"{classe.libelle} (ID {classe.id_classe})":
                return classe.id_classe
        return None

    def _load_slots(self) -> None:
        id_classe = self._id_classe()
        slots = self.services.schedule.list_slots(
            id_classe) if id_classe else self._all_slots()
        self.slot_table.set_rows([{
            "id_edt": s.id_edt,
            "jour": s.jour,
            "creneau": f"{s.heure_debut or ''} - {s.heure_fin or ''}".strip(" -")
            or s.creneau,
            "classe": s.classe,
            "matiere": s.matiere,
            "formateur": s.formateur,
            "salle": s.salle,
            "actif": s.actif,
            "__entity__": s,
        } for s in slots])

    def _all_slots(self):
        rows = []
        for classe in self._classes:
            rows.extend(self.services.schedule.list_slots(classe.id_classe))
        return rows

    def _load_seances(self) -> None:
        id_classe = self._id_classe()
        seances = self.services.schedule.list_seances(id_classe=id_classe)
        self.seance_table.set_rows([{
            "id_seance": s.id_seance,
            "date_seance": s.date_seance,
            "classe": getattr(s, "classe", None),
            "matiere": getattr(s, "matiere", None),
            "creneau": getattr(s, "creneau", None),
            "nb_heures": s.nb_heures,
            "statut": s.statut,
            "__entity__": s,
        } for s in seances])

    # ----- Planification -----

    def _slot_fields(self, slot: Optional[EmploiDuTemps]) -> list:
        programmes = []
        for classe in self._classes:
            programmes.extend(self._programmes_of(classe.id_classe))
        programme_labels = [f"{p.classe or ''} — {p.matiere or p.code_matiere}"
                            for p in programmes]
        creneaux = self.services.schedule.list_creneaux()
        creneau_labels = [f"{c.libelle or ''} ({c.heure_debut}-{c.heure_fin})"
                          for c in creneaux]
        salles = self.services.referentiel.list_salles()
        salle_labels = ["(aucune)"] + [f"{s.nom_salle} (ID {s.id_salle})"
                                       for s in salles]
        initial_programme = None
        if slot is not None:
            for programme in programmes:
                if programme.id_prog == slot.id_prog:
                    initial_programme = f"{programme.classe or ''} — {programme.matiere or programme.code_matiere}"
                    break
        initial_creneau = None
        if slot is not None:
            for creneau in creneaux:
                if creneau.id_creneau == slot.id_creneau:
                    initial_creneau = f"{creneau.libelle or ''} ({creneau.heure_debut}-{creneau.heure_fin})"
                    break
        return [
            dict(label="Programme (classe × matière) *", kind="choice", width=40,
                 values=programme_labels, initial=initial_programme,
                 required=True, row=0, column=0),
            dict(label="Jour *", kind="choice", values=list(JOURS_AUTORISES),
                 initial=slot.jour if slot else "Lundi", required=True,
                 row=1, column=0),
            dict(label="Créneau *", kind="choice", width=26,
                 values=creneau_labels, initial=initial_creneau,
                 required=True, row=1, column=1),
            dict(label="Salle", kind="choice", width=24, values=salle_labels,
                 row=2, column=0),
            dict(label="Créneau actif", kind="bool",
                 initial=slot.actif if slot else True, row=2, column=1),
            dict(label="Valable du", kind="date",
                 initial=slot.date_debut if slot else None, row=3, column=0),
            dict(label="au", kind="date", initial=slot.date_fin if slot else None,
                 row=3, column=1),
        ], (programmes, programme_labels), (creneaux, creneau_labels), \
            (salles, salle_labels)

    def _programmes_of(self, id_classe: int):
        try:
            from ltadmin.repositories.staff_repository import StaffRepository
            return StaffRepository(self.services.database).list_by_classe(id_classe)
        except Exception:
            return []

    def create_slot(self) -> None:
        fields, (programmes, programme_labels), (creneaux, creneau_labels), \
            (salles, salle_labels) = self._slot_fields(None)

        def submit(values):
            from ltadmin.core.result import Result
            index = programme_labels.index(values["Programme (classe × matière) *"]) \
                if values["Programme (classe × matière) *"] in programme_labels else -1
            if index < 0:
                return Result.fail("Sélectionnez un programme.", "VALIDATION")
            creneau_index = creneau_labels.index(values["Créneau *"]) \
                if values["Créneau *"] in creneau_labels else -1
            if creneau_index < 0:
                return Result.fail("Sélectionnez un créneau.", "VALIDATION")
            id_salle = None
            salle_label = values["Salle"] or ""
            for salle in salles:
                if salle_label == f"{salle.nom_salle} (ID {salle.id_salle})":
                    id_salle = salle.id_salle
                    break
            from ltadmin.ui.widgets import parse_date
            try:
                date_debut = parse_date(values["Valable du"])
                date_fin = parse_date(values["au"])
            except ValueError as ex:
                return Result.fail(str(ex), "VALIDATION")
            slot = EmploiDuTemps(
                id_prog=programmes[index].id_prog,
                id_creneau=creneaux[creneau_index].id_creneau,
                jour=values["Jour *"],
                id_salle=id_salle,
                date_debut=date_debut,
                date_fin=date_fin,
                actif=values["Créneau actif"],
            )
            return self.services.schedule.create_slot(slot,
                                                      self.session.login)

        if run_entity_dialog(self, "Planifier un créneau", fields, submit,
                             "Planifier"):
            self._load_slots()

    def edit_slot(self) -> None:
        row = self.slot_table.require_selection(parent=self)
        if row is None:
            return
        slot = row["__entity__"]
        # Reconstruire l'entité de base depuis le détail.
        base = EmploiDuTemps(
            id_edt=slot.id_edt, id_prog=slot.id_prog,
            id_creneau=slot.id_creneau, jour=slot.jour,
            id_salle=slot.id_salle, date_debut=slot.date_debut,
            date_fin=slot.date_fin, actif=slot.actif)
        fields, _programmes, _creneaux, _salles = self._slot_fields(base)

        def submit(values):
            from ltadmin.core.result import Result
            creneau_label = values["Créneau *"] or ""
            id_creneau = base.id_creneau
            creneaux = self.services.schedule.list_creneaux()
            for creneau in creneaux:
                if creneau_label == f"{creneau.libelle or ''} ({creneau.heure_debut}-{creneau.heure_fin})":
                    id_creneau = creneau.id_creneau
                    break
            from ltadmin.ui.widgets import parse_date
            try:
                base.date_debut = parse_date(values["Valable du"])
                base.date_fin = parse_date(values["au"])
            except ValueError as ex:
                return Result.fail(str(ex), "VALIDATION")
            base.jour = values["Jour *"]
            base.actif = values["Créneau actif"]
            return self.services.schedule.update_slot(base,
                                                      self.session.login)

        if run_entity_dialog(self, "Modifier le créneau", fields, submit):
            self._load_slots()

    def delete_slot(self) -> None:
        row = self.slot_table.require_selection(parent=self)
        if row is None:
            return
        slot = row["__entity__"]
        if not confirm(f"Supprimer le créneau {slot.jour} "
                       f"({slot.matiere}, {slot.classe}) ?", "Suppression",
                       parent=self):
            return
        if show_result(self.services.schedule.delete_slot(
                slot.id_edt, self.session.login), parent=self):
            self._load_slots()

    # ----- Séances et absences -----

    def create_seance(self) -> None:
        slots = []
        for classe in self._classes:
            slots.extend(self.services.schedule.list_slots(classe.id_classe))
        if not slots:
            show_error("Planifiez d’abord des créneaux dans l’emploi du temps.",
                       "Aucun créneau", parent=self)
            return
        slot_labels = [f"{s.jour} — {s.classe or ''} — {s.matiere or ''} "
                       f"({s.heure_debut}-{s.heure_fin})" for s in slots]
        fields = [
            dict(label="Créneau d’EDT *", kind="choice", width=44,
                 values=slot_labels, required=True, row=0, column=0),
            dict(label="Date de séance *", kind="date",
                 initial=__import__("datetime").datetime.now(), required=True,
                 row=1, column=0),
            dict(label="Nombre d’heures", kind="float", width=8, initial=2.0,
                 row=1, column=1),
            dict(label="Statut", kind="choice", values=["REALISEE", "ANNULEE",
                                                        "REMPLACEMENT"],
                 initial="REALISEE", row=2, column=0),
            dict(label="Contenu (cahier de texte)", kind="memo", width=36,
                 row=3, column=0),
        ]

        def submit(values):
            from ltadmin.core.result import Result
            from ltadmin.ui.widgets import parse_date
            index = slot_labels.index(values["Créneau d’EDT *"]) \
                if values["Créneau d’EDT *"] in slot_labels else -1
            if index < 0:
                return Result.fail("Sélectionnez un créneau d’EDT.", "VALIDATION")
            try:
                date_seance = parse_date(values["Date de séance *"])
            except ValueError as ex:
                return Result.fail(str(ex), "VALIDATION")
            seance = Seance(
                id_edt=slots[index].id_edt,
                date_seance=date_seance,
                nb_heures=values["Nombre d’heures"],
                statut=values["Statut"],
                contenu=values["Contenu (cahier de texte)"],
            )
            return self.services.schedule.save_seance(seance,
                                                      self.session.login)

        if run_entity_dialog(self, "Séance réalisée", fields, submit,
                             "Enregistrer"):
            self._load_seances()

    def create_absence(self) -> None:
        seance_row = self.seance_table.require_selection(
            parent=self, message="Sélectionnez d’abord une séance.")
        if seance_row is None:
            return
        seance = seance_row["__entity__"]
        # Inscrits de la classe concernée par la séance.
        inscrits = []
        try:
            slot = self.services.schedule.get_slot(seance.id_edt)
            if slot and slot.id_classe:
                inscrits = self.services.enrollments.list_by_classe(slot.id_classe)
        except Exception:
            inscrits = []
        if not inscrits:
            show_error("Aucun inscrit trouvé pour la classe de cette séance.",
                       "Classe vide", parent=self)
            return
        inscrit_labels = [f"{i.matricule or ''} — {i.nom_complet}"
                          for i in inscrits]
        fields = [
            dict(label="Étudiant *", kind="choice", width=40,
                 values=inscrit_labels, required=True, row=0, column=0),
            dict(label="Nature", kind="choice", values=["ABSENCE", "RETARD"],
                 initial="ABSENCE", row=1, column=0),
            dict(label="Nombre d’heures *", kind="float", width=8, initial=2.0,
                 required=True, row=1, column=1),
            dict(label="Justifiée", kind="bool", row=2, column=0),
            dict(label="Motif", kind="memo", width=36, row=3, column=0),
        ]

        def submit(values):
            from ltadmin.core.result import Result
            index = inscrit_labels.index(values["Étudiant *"]) \
                if values["Étudiant *"] in inscrit_labels else -1
            if index < 0:
                return Result.fail("Sélectionnez un étudiant.", "VALIDATION")
            absence = Absence(
                id_seance=seance.id_seance,
                id_inscription=inscrits[index].id_inscription,
                nature=values["Nature"],
                nb_heures=values["Nombre d’heures *"],
                justifiee=values["Justifiée"],
                motif=values["Motif"],
            )
            return self.services.schedule.save_absence(absence,
                                                       self.session.login)

        if run_entity_dialog(self, "Saisir une absence", fields, submit,
                             "Enregistrer"):
            self._load_seances()
