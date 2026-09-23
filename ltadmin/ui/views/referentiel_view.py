"""Écran Référentiel : filières, niveaux, salles, classes, modules, matières."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import List, Optional

from ltadmin.models.entities import (Classe, Filiere, Matiere, ModuleFormation,
                                     Niveau, Salle)
from ltadmin.ui.dialogs import run_entity_dialog
from ltadmin.ui.views.base_view import BaseView
from ltadmin.ui.widgets import DataTable, confirm, show_error, show_result

CLASSE_COLUMNS = [
    ("id_classe", "ID", -1, "w"),
    ("libelle", "Classe", 190, "w"),
    ("annee", "Année", 110, "w"),
    ("filiere", "Filière", 190, "w"),
    ("niveau", "Niveau", 110, "w"),
    ("salle", "Salle principale", 130, "w"),
    ("effectif_max", "Effectif max", 90, "center"),
    ("nb_inscrits", "Inscrits", 80, "center"),
]


class ReferentielView(BaseView):
    title = "Référentiel"
    subtitle = "Filières, niveaux, salles, classes, modules et matières"

    TABS = ("Classes", "Filières", "Niveaux", "Salles", "Modules", "Matières")

    def __init__(self, parent, services, session, **kwargs):
        super().__init__(parent, services, session, **kwargs)
        self.notebook = ttk.Notebook(self.content)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.classe_table = DataTable(self.notebook, CLASSE_COLUMNS,
                                      on_refresh=self.refresh)
        self.notebook.add(self.classe_table, text="Classes")

        self.filiere_table = DataTable(
            self.notebook, [("code", "Code", 90, "w"),
                            ("libelle", "Filière", 240, "w"),
                            ("diplome", "Diplôme", 180, "w"),
                            ("duree", "Durée (ans)", 90, "center"),
                            ("active", "Active", 70, "center")])
        self.notebook.add(self.filiere_table, text="Filières")

        self.niveau_table = DataTable(
            self.notebook, [("code", "Code", 90, "w"),
                            ("libelle", "Niveau", 240, "w"),
                            ("ordre", "Ordre", 80, "center")])
        self.notebook.add(self.niveau_table, text="Niveaux")

        self.salle_table = DataTable(
            self.notebook, [("id", "ID", -1, "w"),
                            ("nom", "Salle", 160, "w"),
                            ("capacite", "Capacité", 90, "center"),
                            ("nature", "Nature", 140, "w"),
                            ("disponible", "Disponible", 100, "center")])
        self.notebook.add(self.salle_table, text="Salles")

        self.module_table = DataTable(
            self.notebook, [("code", "Code", 100, "w"),
                            ("libelle", "Module", 260, "w"),
                            ("filiere", "Filière", 180, "w")])
        self.notebook.add(self.module_table, text="Modules")

        self.matiere_table = DataTable(
            self.notebook, [("code", "Code", 100, "w"),
                            ("libelle", "Matière", 260, "w"),
                            ("module", "Module", 180, "w"),
                            ("nature", "Nature", 120, "w"),
                            ("ordre", "Ordre", 70, "center")])
        self.notebook.add(self.matiere_table, text="Matières")

        self.toolbar.add_button("＋ Nouveau / ✎ Modifier", self.edit_current)
        self.toolbar.add_button("🗑 Supprimer", self.delete_current)

    # ----- Chargement -----

    def refresh(self) -> None:
        self.classe_table.set_rows([{
            "id_classe": c.id_classe,
            "libelle": c.libelle,
            "annee": c.annee,
            "filiere": c.filiere,
            "niveau": c.niveau,
            "salle": c.salle,
            "effectif_max": c.effectif_max,
            "nb_inscrits": c.nb_inscrits,
            "__entity__": c,
        } for c in self.services.referentiel.list_classes_detail()])

        self.filiere_table.set_rows([{
            "code": f.code_filiere,
            "libelle": f.libelle,
            "diplome": f.diplome,
            "duree": f.duree_ans,
            "active": f.active,
            "__entity__": f,
        } for f in self.services.referentiel.list_filieres()])

        self.niveau_table.set_rows([{
            "code": n.code_niveau,
            "libelle": n.libelle,
            "ordre": n.ordre_niv,
            "__entity__": n,
        } for n in self.services.referentiel.list_niveaux()])

        self.salle_table.set_rows([{
            "id": s.id_salle,
            "nom": s.nom_salle,
            "capacite": s.capacite,
            "nature": s.nature_salle,
            "disponible": s.disponible,
            "__entity__": s,
        } for s in self.services.referentiel.list_salles()])

        filieres = {f.code_filiere: f.libelle for f in
                    self.services.referentiel.list_filieres()}
        self.module_table.set_rows([{
            "code": m.code_module,
            "libelle": m.module_lib,
            "filiere": filieres.get(m.code_filiere, m.code_filiere or "Transversal"),
            "__entity__": m,
        } for m in self.services.referentiel.list_modules()])

        modules = {m.code_module: m.module_lib for m in
                   self.services.referentiel.list_modules()}
        self.matiere_table.set_rows([{
            "code": m.code_matiere,
            "libelle": m.libelle,
            "module": modules.get(m.code_module, m.code_module or ""),
            "nature": m.nature,
            "ordre": m.ordre_mat,
            "__entity__": m,
        } for m in self.services.referentiel.list_matieres()])

    def _current_table(self) -> Optional[DataTable]:
        widget = self.notebook.select()
        if not widget:
            return None
        for table in (self.classe_table, self.filiere_table, self.niveau_table,
                      self.salle_table, self.module_table, self.matiere_table):
            if str(table) == widget:
                return table
        return None

    # ----- Édition générique -----

    def edit_current(self) -> None:
        table = self._current_table()
        if table is None:
            return
        row = table.selected_row()
        tab_name = self.notebook.tab(self.notebook.select(), "text")
        if tab_name == "Classes":
            self.edit_classe(row["__entity__"] if row else None)
        elif tab_name == "Filières":
            self.edit_filiere(row["__entity__"] if row else None)
        elif tab_name == "Niveaux":
            self.edit_niveau(row["__entity__"] if row else None)
        elif tab_name == "Salles":
            self.edit_salle(row["__entity__"] if row else None)
        elif tab_name == "Modules":
            self.edit_module(row["__entity__"] if row else None)
        elif tab_name == "Matières":
            self.edit_matiere(row["__entity__"] if row else None)

    def delete_current(self) -> None:
        table = self._current_table()
        if table is None:
            return
        row = table.require_selection(parent=self)
        if row is None:
            return
        tab_name = self.notebook.tab(self.notebook.select(), "text")
        entity = row["__entity__"]
        labels = {"Classes": f"la classe « {entity.libelle} »",
                  "Filières": f"la filière « {entity.libelle} »",
                  "Niveaux": f"le niveau « {entity.libelle} »",
                  "Salles": f"la salle « {entity.nom_salle} »",
                  "Modules": f"le module « {entity.module_lib} »",
                  "Matières": f"la matière « {entity.libelle} »"}
        if not confirm(f"Supprimer {labels.get(tab_name, 'cet élément')} ?",
                       "Suppression", parent=self):
            return
        result = None
        services = self.services.referentiel
        if tab_name == "Classes":
            result = services.delete_classe(entity.id_classe, self.session.login)
        elif tab_name == "Filières":
            result = services.delete_filiere(entity.code_filiere,
                                             self.session.login)
        elif tab_name == "Niveaux":
            result = services.delete_niveau(entity.code_niveau,
                                            self.session.login)
        elif tab_name == "Salles":
            result = services.delete_salle(entity.id_salle,
                                           self.session.login)
        elif tab_name == "Modules":
            result = services.delete_module(entity.code_module,
                                            self.session.login)
        elif tab_name == "Matières":
            result = services.delete_matiere(entity.code_matiere,
                                             self.session.login)
        if result is not None and show_result(result, parent=self):
            self.refresh()

    # ----- Classes -----

    def edit_classe(self, classe=None) -> None:
        classe = classe or Classe()
        filieres = self.services.referentiel.list_filieres()
        niveaux = self.services.referentiel.list_niveaux()
        salles = self.services.referentiel.list_salles()
        filiere_labels = ["(aucune)"] + [f.code_filiere for f in filieres]
        niveau_labels = ["(aucun)"] + [n.code_niveau for n in niveaux]
        salle_labels = ["(aucune)"] + [f"{s.nom_salle} (ID {s.id_salle})"
                                       for s in salles]
        initial_salle = None
        if classe.id_salle:
            for salle in salles:
                if salle.id_salle == classe.id_salle:
                    initial_salle = f"{salle.nom_salle} (ID {salle.id_salle})"
                    break
        fields = [
            dict(label="Libellé *", kind="text", width=28, initial=classe.libelle,
                 required=True, row=0, column=0),
            dict(label="Effectif maximum", kind="int", width=8,
                 initial=classe.effectif_max, row=0, column=1),
            dict(label="Filière", kind="choice", width=20,
                 values=filiere_labels, initial=classe.code_filiere or "(aucune)",
                 row=1, column=0),
            dict(label="Niveau", kind="choice", width=20, values=niveau_labels,
                 initial=classe.code_niveau or "(aucun)", row=1, column=1),
            dict(label="Salle principale", kind="choice", width=24,
                 values=salle_labels, initial=initial_salle or "(aucune)",
                 row=2, column=0),
        ]

        def submit(values):
            classe.libelle = values["Libellé"]
            classe.effectif_max = values["Effectif maximum"]
            classe.code_filiere = values["Filière"] if values["Filière"] not in (
                None, "(aucune)") else None
            classe.code_niveau = values["Niveau"] if values["Niveau"] not in (
                None, "(aucun)") else None
            salle_label = values["Salle principale"] or ""
            classe.id_salle = None
            for salle in salles:
                if salle_label == f"{salle.nom_salle} (ID {salle.id_salle})":
                    classe.id_salle = salle.id_salle
                    break
            return self.services.referentiel.save_classe(classe,
                                                         self.session.login)

        if run_entity_dialog(self, "Classe", fields, submit):
            self.refresh()

    # ----- Filières / niveaux / salles / modules / matières -----

    def edit_filiere(self, filiere=None) -> None:
        filiere = filiere or Filiere()
        fields = [
            dict(label="Code *", kind="text", width=12, required=True,
                 initial=filiere.code_filiere, readonly=filiere.code_filiere
                 is not None, row=0, column=0),
            dict(label="Libellé *", kind="text", width=28, required=True,
                 initial=filiere.libelle, row=0, column=1),
            dict(label="Diplôme", kind="text", width=28, initial=filiere.diplome,
                 row=1, column=0),
            dict(label="Durée (années)", kind="int", width=6,
                 initial=filiere.duree_ans, row=1, column=1),
            dict(label="Active", kind="bool",
                 initial=filiere.active if filiere.active is not None else True,
                 row=2, column=0),
        ]

        def submit(values):
            filiere.code_filiere = values["Code"]
            filiere.libelle = values["Libellé"]
            filiere.diplome = values["Diplôme"]
            filiere.duree_ans = values["Durée (années)"]
            filiere.active = values["Active"]
            return self.services.referentiel.save_filiere(filiere,
                                                          self.session.login)

        if run_entity_dialog(self, "Filière", fields, submit):
            self.refresh()

    def edit_niveau(self, niveau=None) -> None:
        niveau = niveau or Niveau()
        fields = [
            dict(label="Code *", kind="text", width=12, required=True,
                 initial=niveau.code_niveau, readonly=niveau.code_niveau
                 is not None, row=0, column=0),
            dict(label="Libellé *", kind="text", width=28, required=True,
                 initial=niveau.libelle, row=0, column=1),
            dict(label="Ordre", kind="int", width=6, initial=niveau.ordre_niv,
                 row=1, column=0),
        ]

        def submit(values):
            niveau.code_niveau = values["Code"]
            niveau.libelle = values["Libellé"]
            niveau.ordre_niv = values["Ordre"]
            return self.services.referentiel.save_niveau(niveau,
                                                         self.session.login)

        if run_entity_dialog(self, "Niveau", fields, submit):
            self.refresh()

    def edit_salle(self, salle=None) -> None:
        salle = salle or Salle()
        fields = [
            dict(label="Nom *", kind="text", width=22, required=True,
                 initial=salle.nom_salle, row=0, column=0),
            dict(label="Capacité", kind="int", width=8, initial=salle.capacite,
                 row=0, column=1),
            dict(label="Nature", kind="choice", values=["SALLE", "LABO",
                                                        "AMPHI", "ATELIER"],
                 initial=salle.nature_salle or "SALLE", row=1, column=0),
            dict(label="Disponible", kind="bool",
                 initial=salle.disponible if salle.disponible is not None
                 else True, row=1, column=1),
        ]

        def submit(values):
            salle.nom_salle = values["Nom"]
            salle.capacite = values["Capacité"]
            salle.nature_salle = values["Nature"]
            salle.disponible = values["Disponible"]
            return self.services.referentiel.save_salle(salle,
                                                        self.session.login)

        if run_entity_dialog(self, "Salle", fields, submit):
            self.refresh()

    def edit_module(self, module=None) -> None:
        module = module or ModuleFormation()
        filieres = self.services.referentiel.list_filieres()
        filiere_labels = ["(transversal)"] + [f.code_filiere for f in filieres]
        fields = [
            dict(label="Code *", kind="text", width=14, required=True,
                 initial=module.code_module, readonly=module.code_module
                 is not None, row=0, column=0),
            dict(label="Libellé *", kind="text", width=30, required=True,
                 initial=module.module_lib, row=0, column=1),
            dict(label="Filière", kind="choice", width=20,
                 values=filiere_labels, initial=module.code_filiere
                 or "(transversal)", row=1, column=0),
        ]

        def submit(values):
            module.code_module = values["Code"]
            module.module_lib = values["Libellé"]
            module.code_filiere = values["Filière"] if values["Filière"] not in (
                None, "(transversal)") else None
            return self.services.referentiel.save_module(module,
                                                         self.session.login)

        if run_entity_dialog(self, "Module de formation", fields, submit):
            self.refresh()

    def edit_matiere(self, matiere=None) -> None:
        matiere = matiere or Matiere()
        modules = self.services.referentiel.list_modules()
        module_labels = ["(aucun)"] + [m.code_module for m in modules]
        fields = [
            dict(label="Code *", kind="text", width=14, required=True,
                 initial=matiere.code_matiere, readonly=matiere.code_matiere
                 is not None, row=0, column=0),
            dict(label="Libellé *", kind="text", width=30, required=True,
                 initial=matiere.libelle, row=0, column=1),
            dict(label="Module", kind="choice", width=18, values=module_labels,
                 initial=matiere.code_module or "(aucun)", row=1, column=0),
            dict(label="Ordre", kind="int", width=6, initial=matiere.ordre_mat,
                 row=1, column=1),
        ]

        def submit(values):
            matiere.code_matiere = values["Code"]
            matiere.libelle = values["Libellé"]
            matiere.code_module = values["Module"] if values["Module"] not in (
                None, "(aucun)") else None
            matiere.ordre_mat = values["Ordre"]
            return self.services.referentiel.save_matiere(matiere,
                                                          self.session.login)

        if run_entity_dialog(self, "Matière", fields, submit):
            self.refresh()
