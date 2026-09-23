"""Écran Formateurs : dossiers, programmes (matières × classes) et paie."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from decimal import Decimal
from typing import Optional

from ltadmin.models.entities import Formateur, Programme
from ltadmin.ui.dialogs import run_entity_dialog
from ltadmin.ui.views.base_view import BaseView
from ltadmin.ui.widgets import DataTable, confirm, parse_date, show_error, \
    show_result

FORMATEUR_COLUMNS = [
    ("id_formateur", "ID", -1, "w"),
    ("matricule", "Matricule", 110, "w"),
    ("nom_complet", "Nom et prénom", 220, "w"),
    ("specialite", "Spécialité", 180, "w"),
    ("tel", "Téléphone", 110, "w"),
    ("taux_horaire", "Taux horaire", 110, "e"),
    ("actif", "Actif", 60, "center"),
]

PROGRAMME_COLUMNS = [
    ("id_prog", "ID", -1, "w"),
    ("classe", "Classe", 170, "w"),
    ("matiere", "Matière", 190, "w"),
    ("formateur", "Formateur", 190, "w"),
    ("coefficient", "Coef", 60, "e"),
    ("vol_horaire", "Volume", 70, "e"),
    ("note_elimin", "Élim.", 60, "e"),
]

PAIE_COLUMNS = [
    ("id_paie", "ID", -1, "w"),
    ("periode", "Période", 130, "w"),
    ("nb_heures", "Heures", 80, "e"),
    ("taux", "Taux", 100, "e"),
    ("montant", "Montant", 120, "e"),
    ("paye", "Payée", 60, "center"),
    ("date_paie", "Payée le", 110, "center"),
]


class StaffView(BaseView):
    title = "Formateurs"
    subtitle = "Dossiers formateurs, programmes pédagogiques et paie"

    def __init__(self, parent, services, session, **kwargs):
        super().__init__(parent, services, session, **kwargs)
        self._formateurs = []

        self.formateur_table = DataTable(self.content, FORMATEUR_COLUMNS,
                                         on_refresh=self.refresh)
        self.formateur_table.pack(fill=tk.BOTH, expand=True)

        ttk.Label(self.content, text="Programmes (matières × classes)",
                  style="Muted.TLabel").pack(anchor="w", pady=(10, 4))
        self.programme_table = DataTable(self.content, PROGRAMME_COLUMNS)
        self.programme_table.pack(fill=tk.BOTH, expand=True)

        ttk.Label(self.content, text="Paies du formateur sélectionné",
                  style="Muted.TLabel").pack(anchor="w", pady=(10, 4))
        self.paie_table = DataTable(self.content, PAIE_COLUMNS)
        self.paie_table.pack(fill=tk.BOTH, expand=True)
        self.formateur_table.tree.bind(
            "<<TreeviewSelect>>", lambda _e: self._load_formateur_details())

        self.toolbar.add_button("＋ Nouveau formateur", self.create_formateur,
                                accent=True)
        self.toolbar.add_button("✎ Modifier", self.edit_formateur)
        self.toolbar.add_button("🗑 Supprimer", self.delete_formateur)
        self.toolbar.add_button("＋ Programme", self.create_programme)
        self.toolbar.add_button("🗑 Supprimer le programme",
                                self.delete_programme)
        self.toolbar.add_button("💰 Calculer une paie", self.calculer_paie)
        self.toolbar.add_button("✔ Marquer payée", self.marquer_payee)

    def refresh(self) -> None:
        self._formateurs = self.services.payroll.list_formateurs()
        self.formateur_table.set_rows([{
            "id_formateur": f.id_formateur,
            "matricule": f.matricule,
            "nom_complet": f.nom_complet,
            "specialite": f.specialite,
            "tel": f.tel,
            "taux_horaire": f.taux_horaire,
            "actif": f.actif,
            "__entity__": f,
        } for f in self._formateurs])
        self._load_programmes()
        self.paie_table.set_rows([])

    def _selected_formateur(self) -> Optional[Formateur]:
        row = self.formateur_table.selected_row()
        return row["__entity__"] if row else None

    def _load_formateur_details(self) -> None:
        formateur = self._selected_formateur()
        if formateur is None:
            return
        self._load_programmes(formateur.id_formateur)
        self.paie_table.set_rows([{
            "id_paie": p.id_paie,
            "periode": p.periode,
            "nb_heures": p.nb_heures,
            "taux": p.taux,
            "montant": p.montant,
            "paye": p.paye,
            "date_paie": p.date_paie,
            "__entity__": p,
        } for p in self.services.payroll.list_paies_by_formateur(
            formateur.id_formateur)])

    def _load_programmes(self, id_formateur: Optional[int] = None) -> None:
        try:
            from ltadmin.repositories.staff_repository import StaffRepository
            repo = StaffRepository(self.services.database)
            if id_formateur is None:
                rows = []
                for classe in self.services.referentiel.list_classes():
                    rows.extend(repo.list_by_classe(classe.id_classe))
            else:
                rows = repo.list_by_formateur(id_formateur)
        except Exception:
            rows = []
        self.programme_table.set_rows([{
            "id_prog": p.id_prog,
            "classe": p.classe,
            "matiere": p.matiere or p.code_matiere,
            "formateur": p.formateur,
            "coefficient": p.coefficient,
            "vol_horaire": p.vol_horaire,
            "note_elimin": p.note_elimin,
            "__entity__": p,
        } for p in rows])

    # ----- Formateurs -----

    def _formateur_fields(self, formateur: Optional[Formateur]) -> list:
        f = formateur or Formateur()
        return [
            dict(label="Matricule", kind="text", width=16, initial=f.matricule,
                 row=0, column=0),
            dict(label="Contrat", kind="choice", values=["CDI", "CDD", "VACATAIRE"],
                 initial=f.contrat or "VACATAIRE", row=0, column=1),
            dict(label="Nom *", kind="text", width=26, initial=f.nom,
                 required=True, row=1, column=0),
            dict(label="Prénom *", kind="text", width=26, initial=f.prenom,
                 required=True, row=1, column=1),
            dict(label="Sexe", kind="choice", values=["M", "F"],
                 initial=f.sexe, row=2, column=0),
            dict(label="Date de naissance", kind="date",
                 initial=f.date_naissance, row=2, column=1),
            dict(label="CIN", kind="text", width=18, initial=f.cin,
                 row=3, column=0),
            dict(label="Téléphone", kind="text", width=18, initial=f.tel,
                 row=3, column=1),
            dict(label="E-mail", kind="text", width=26, initial=f.email,
                 row=4, column=0),
            dict(label="Spécialité", kind="text", width=26,
                 initial=f.specialite, row=4, column=1),
            dict(label="Diplôme", kind="text", width=26, initial=f.diplome,
                 row=5, column=0),
            dict(label="Taux horaire", kind="float", width=10,
                 initial=float(f.taux_horaire) if f.taux_horaire else None,
                 row=5, column=1),
            dict(label="Adresse", kind="text", width=26, initial=f.adresse,
                 row=6, column=0),
            dict(label="Actif", kind="bool",
                 initial=f.actif if f.actif is not None else True,
                 row=6, column=1),
        ]

    def create_formateur(self) -> None:
        # Création via le dépôt du personnel (formateurs).
        def submit_real(values):
            formateur = self._from_values(None, values)
            from ltadmin.core.result import Result, ResultValue
            from ltadmin.services.validation.validation import StaffValidator
            validation = StaffValidator.validate_formateur(formateur)
            if not validation.is_valid:
                return Result.fail("Vérifiez la saisie :", "VALIDATION",
                                   validation.errors)
            try:
                from ltadmin.repositories.staff_repository import StaffRepository
                if not (formateur.matricule or "").strip():
                    formateur.matricule = self._generer_matricule()
                if formateur.date_embauche is None:
                    formateur.date_embauche = None
                id_formateur = StaffRepository(
                    self.services.database).insert_formateur(formateur)
                self.services.journal.log_creation(
                    self.session.login, "FORMATEUR", id_formateur,
                    formateur.nom_complet)
                return ResultValue.ok(id_formateur, "Formateur créé.")
            except Exception as ex:
                from ltadmin.services.common import ServiceBase
                return Result.fail(
                    "Enregistrement impossible : " + str(ex), "TECHNIQUE")
        if run_entity_dialog(self, "Nouveau formateur",
                             self._formateur_fields(None), submit_real,
                             "Créer le formateur"):
            self.refresh()

    def edit_formateur(self) -> None:
        formateur = self._selected_formateur()
        if formateur is None:
            show_error("Sélectionnez d’abord un formateur.", "Aucune sélection",
                       parent=self)
            return

        def submit(values):
            updated = self._from_values(formateur, values)
            from ltadmin.core.result import Result
            from ltadmin.services.validation.validation import StaffValidator
            validation = StaffValidator.validate_formateur(updated)
            if not validation.is_valid:
                return Result.fail("Vérifiez la saisie :", "VALIDATION",
                                   validation.errors)
            try:
                from ltadmin.repositories.staff_repository import StaffRepository
                StaffRepository(self.services.database).update_formateur(updated)
                self.services.journal.log_modification(
                    self.session.login, "FORMATEUR", updated.id_formateur,
                    updated.nom_complet)
                return Result.ok("Formateur enregistré.")
            except Exception as ex:
                return Result.fail("Enregistrement impossible : " + str(ex),
                                   "TECHNIQUE")

        if run_entity_dialog(self, f"Modifier {formateur.nom_complet}",
                             self._formateur_fields(formateur), submit):
            self.refresh()

    def delete_formateur(self) -> None:
        formateur = self._selected_formateur()
        if formateur is None:
            show_error("Sélectionnez d’abord un formateur.", "Aucune sélection",
                       parent=self)
            return
        if not confirm(f"Supprimer le formateur « {formateur.nom_complet} » ?",
                       "Suppression", parent=self):
            return
        try:
            from ltadmin.repositories.staff_repository import StaffRepository
            StaffRepository(self.services.database).delete_formateur(
                formateur.id_formateur)
            self.services.journal.log_suppression(
                self.session.login, "FORMATEUR", formateur.id_formateur,
                formateur.nom_complet)
            from ltadmin.ui.widgets import show_info
            show_info("Succès", "Formateur supprimé.", parent=self)
        except Exception as ex:
            from ltadmin.data import error_helper
            error = error_helper.interpret(ex)
            show_error(error.message, "Suppression impossible", parent=self)
        self.refresh()

    def _generer_matricule(self) -> str:
        import datetime as _dt
        from ltadmin.repositories.staff_repository import StaffRepository
        repo = StaffRepository(self.services.database)
        prefixe = f"FOR-{_dt.date.today().year}-"
        existants = {m.upper() for m in repo.list_matricules(prefixe)}
        sequence = 0
        for matricule in existants:
            try:
                value = int(matricule[len(prefixe):])
                sequence = max(sequence, value)
            except ValueError:
                continue
        while True:
            sequence += 1
            candidat = prefixe + f"{sequence:04d}"
            if candidat.upper() not in existants:
                return candidat

    def _from_values(self, existing: Optional[Formateur],
                     values: dict) -> Formateur:
        formateur = existing or Formateur()
        formateur.matricule = values.get("Matricule") or None
        formateur.contrat = values.get("Contrat")
        formateur.nom = values.get("Nom")
        formateur.prenom = values.get("Prénom")
        formateur.sexe = values.get("Sexe")
        try:
            formateur.date_naissance = parse_date(values.get("Date de naissance"))
        except ValueError:
            pass
        formateur.cin = values.get("CIN")
        formateur.tel = values.get("Téléphone")
        formateur.email = values.get("E-mail")
        formateur.specialite = values.get("Spécialité")
        formateur.diplome = values.get("Diplôme")
        taux = values.get("Taux horaire")
        formateur.taux_horaire = Decimal(str(taux)) if taux is not None else None
        formateur.adresse = values.get("Adresse")
        formateur.actif = values.get("Actif")
        return formateur

    # ----- Programmes -----

    def create_programme(self) -> None:
        classes = self.services.referentiel.list_classes()
        matieres = self.services.referentiel.list_matieres()
        formateur_labels = [f"{f.nom_complet} (ID {f.id_formateur})"
                            for f in self._formateurs]
        fields = [
            dict(label="Classe *", kind="choice", width=30,
                 values=[f"{c.libelle} (ID {c.id_classe})" for c in classes],
                 required=True, row=0, column=0),
            dict(label="Matière *", kind="choice", width=30,
                 values=[f"{m.libelle or m.code_matiere} ({m.code_matiere})"
                         for m in matieres], required=True, row=0, column=1),
            dict(label="Formateur", kind="choice", width=34,
                 values=["(non affecté)"] + formateur_labels, row=1, column=0),
            dict(label="Coefficient *", kind="float", width=8, initial=1.0,
                 required=True, row=1, column=1),
            dict(label="Volume horaire", kind="int", width=8, row=2, column=0),
            dict(label="Note éliminatoire", kind="float", width=8, row=2,
                 column=1),
            dict(label="Observation", kind="text", width=30, row=3, column=0),
        ]

        def submit(values):
            from ltadmin.core.result import Result
            from ltadmin.services.validation.validation import StaffValidator
            id_classe = None
            for classe in classes:
                if values["Classe"] == f"{classe.libelle} (ID {classe.id_classe})":
                    id_classe = classe.id_classe
                    break
            code_matiere = None
            for matiere in matieres:
                if values["Matière"] == f"{matiere.libelle or matiere.code_matiere} ({matiere.code_matiere})":
                    code_matiere = matiere.code_matiere
                    break
            if id_classe is None or code_matiere is None:
                return Result.fail("Sélectionnez une classe et une matière.",
                                   "VALIDATION")
            id_formateur = None
            label = values["Formateur"] or ""
            for formateur in self._formateurs:
                if label == f"{formateur.nom_complet} (ID {formateur.id_formateur})":
                    id_formateur = formateur.id_formateur
                    break
            programme = Programme(
                id_classe=id_classe,
                code_matiere=code_matiere,
                id_formateur=id_formateur,
                coefficient=values["Coefficient"],
                vol_horaire=values["Volume horaire"],
                note_elimin=values["Note éliminatoire"],
                observation=values["Observation"],
            )
            validation = StaffValidator.validate_programme(programme)
            if not validation.is_valid:
                return Result.fail("Vérifiez la saisie :", "VALIDATION",
                                   validation.errors)
            try:
                from ltadmin.repositories.staff_repository import StaffRepository
                existing = StaffRepository(
                    self.services.database).get_programme_by_classe_matiere(
                    id_classe, code_matiere)
                if existing is not None:
                    return Result.fail(
                        "Cette matière est déjà programmée pour cette classe.",
                        "DOUBLON")
                id_prog = StaffRepository(
                    self.services.database).insert_programme(programme)
                self.services.journal.log_creation(
                    self.session.login, "PROGRAMME", id_prog,
                    f"{code_matiere} → classe {id_classe}")
                return Result.ok("Programme enregistré.")
            except Exception as ex:
                return Result.fail("Enregistrement impossible : " + str(ex),
                                   "TECHNIQUE")

        if run_entity_dialog(self, "Nouveau programme", fields, submit,
                             "Enregistrer"):
            self._load_programmes()

    def delete_programme(self) -> None:
        row = self.programme_table.require_selection(parent=self)
        if row is None:
            return
        programme = row["__entity__"]
        if not confirm(f"Supprimer le programme « {programme.matiere} » de "
                       f"« {programme.classe} » ?", "Suppression",
                       parent=self):
            return
        try:
            from ltadmin.repositories.staff_repository import StaffRepository
            StaffRepository(self.services.database).delete_programme(
                programme.id_prog)
            self.services.journal.log_suppression(
                self.session.login, "PROGRAMME", programme.id_prog, None)
            from ltadmin.ui.widgets import show_info
            show_info("Succès", "Programme supprimé.", parent=self)
        except Exception as ex:
            from ltadmin.data import error_helper
            show_error(error_helper.interpret(ex).message,
                       "Suppression impossible", parent=self)
        self._load_programmes()

    # ----- Paie -----

    def calculer_paie(self) -> None:
        formateur = self._selected_formateur()
        if formateur is None:
            show_error("Sélectionnez d’abord un formateur.", "Aucune sélection",
                       parent=self)
            return
        import datetime as _dt
        fields = [
            dict(label="Période (libellé) *", kind="text", width=18,
                 initial=_dt.date.today().strftime("%m/%Y"), required=True,
                 row=0, column=0),
            dict(label="Du *", kind="date",
                 initial=_dt.datetime(_dt.date.today().year,
                                      _dt.date.today().month, 1),
                 required=True, row=1, column=0),
            dict(label="Au *", kind="date",
                 initial=_dt.datetime.now(), required=True, row=1, column=1),
        ]

        def submit(values):
            try:
                debut = parse_date(values["Du"])
                fin = parse_date(values["Au"])
            except ValueError as ex:
                from ltadmin.core.result import Result
                return Result.fail(str(ex), "VALIDATION")
            return self.services.payroll.calculer_paie(
                formateur.id_formateur, values["Période (libellé)"],
                debut, fin, self.session.login)

        if run_entity_dialog(self, f"Calculer la paie — {formateur.nom_complet}",
                             fields, submit, "Calculer", two_columns=False):
            self._load_formateur_details()

    def marquer_payee(self) -> None:
        row = self.paie_table.require_selection(
            parent=self, message="Sélectionnez d’abord une paie.")
        if row is None:
            return
        paie = row["__entity__"]
        paye = not bool(paie.paye)
        if show_result(self.services.payroll.marquer_payee(
                paie.id_paie, paye, None, self.session.login), parent=self):
            self._load_formateur_details()
