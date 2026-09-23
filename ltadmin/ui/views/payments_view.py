"""Écran Écolage : tarifs, échéances, encaissements et remises."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from decimal import Decimal
from typing import Optional

from ltadmin.models.entities import Tarif
from ltadmin.ui.dialogs import run_entity_dialog
from ltadmin.ui.views.base_view import BaseView
from ltadmin.ui.widgets import DataTable, confirm, show_error, show_result

TARIF_COLUMNS = [
    ("id_tarif", "ID", -1, "w"),
    ("type_frais", "Type de frais", 200, "w"),
    ("montant", "Montant", 120, "e"),
    ("nb_tranches", "Tranches", 80, "center"),
    ("obligatoire", "Obligatoire", 90, "center"),
]

ECHEANCE_COLUMNS = [
    ("id_echeance", "ID", -1, "w"),
    ("matricule", "Matricule", 110, "w"),
    ("nom_complet", "Étudiant", 200, "w"),
    ("libelle", "Échéance", 200, "w"),
    ("date_echeance", "Échéance au", 100, "center"),
    ("montant_du", "Dû", 100, "e"),
    ("remise", "Remise", 80, "e"),
    ("total_paye", "Payé", 100, "e"),
    ("reste", "Reste", 100, "e"),
    ("statut", "Statut", 80, "center"),
]

PAIEMENT_COLUMNS = [
    ("id_paiement", "ID", -1, "w"),
    ("num_recu", "Reçu", 140, "w"),
    ("date_paiement", "Date", 130, "center"),
    ("montant", "Montant", 110, "e"),
    ("mode_paie", "Mode", 110, "w"),
    ("ref_externe", "Référence", 120, "w"),
    ("code_utr", "Caissier", 90, "w"),
]


class PaymentsView(BaseView):
    title = "Écolage"
    subtitle = "Tarifs, échéanciers, encaissements et remises"

    def __init__(self, parent, services, session, **kwargs):
        super().__init__(parent, services, session, **kwargs)
        self._classes = []
        self._tarifs = []
        self._echeances = []
        self._selected_echeance = None

        filters = ttk.Frame(self.content)
        filters.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(filters, text="Classe :").pack(side=tk.LEFT)
        self.classe_var = tk.StringVar()
        self.classe_combo = ttk.Combobox(filters, textvariable=self.classe_var,
                                         state="readonly", width=30)
        self.classe_combo.pack(side=tk.LEFT, padx=8)
        self.classe_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())

        self.tarif_table = DataTable(self.content, TARIF_COLUMNS)
        self.tarif_table.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(self.content, text="Échéances des inscrits de la classe :",
                  style="Muted.TLabel").pack(anchor="w", pady=(0, 4))
        self.echeance_table = DataTable(self.content, ECHEANCE_COLUMNS,
                                        on_refresh=self.refresh)
        self.echeance_table.pack(fill=tk.BOTH, expand=True)
        self.echeance_table.tree.bind(
            "<<TreeviewSelect>>", lambda _e: self._load_paiements())
        ttk.Label(self.content, text="Paiements de l’échéance sélectionnée :",
                  style="Muted.TLabel").pack(anchor="w", pady=(8, 4))
        self.paiement_table = DataTable(self.content, PAIEMENT_COLUMNS)
        self.paiement_table.pack(fill=tk.X)

        self.toolbar.add_button("＋ Nouveau tarif", self.create_tarif, accent=True)
        self.toolbar.add_button("📋 Générer échéancier", self.generer_echeancier)
        self.toolbar.add_button("💵 Encaisser", self.encaisser)
        self.toolbar.add_button("− Remise", self.accorder_remise)
        self.toolbar.add_button("🗑 Annuler paiement", self.annuler_paiement)
        self.toolbar.add_label("Devise : " + self.services.parametres.devise)

    def refresh(self) -> None:
        self._classes = self.services.referentiel.list_classes()
        labels = [f"{c.libelle} (ID {c.id_classe})" for c in self._classes]
        self.classe_combo.configure(values=labels)
        if self.classe_var.get() not in labels:
            self.classe_var.set(labels[0] if labels else "")
        classe = self._selected_classe()
        self._tarifs = self.services.ecolage.list_tarifs(
            classe.id_classe) if classe else []
        self.tarif_table.set_rows([{
            "id_tarif": t.id_tarif,
            "type_frais": t.type_frais,
            "montant": t.montant,
            "nb_tranches": t.nb_tranches,
            "obligatoire": t.obligatoire,
            "__entity__": t,
        } for t in self._tarifs])
        self._load_echeances()
        self.paiement_table.set_rows([])

    def _selected_classe(self):
        for classe in self._classes:
            if self.classe_var.get() == f"{classe.libelle} (ID {classe.id_classe})":
                return classe
        return None

    def _load_echeances(self) -> None:
        classe = self._selected_classe()
        rows = []
        self._echeances = []
        if classe is not None:
            for inscrit in self.services.enrollments.list_by_classe(classe.id_classe):
                for echeance in self.services.ecolage.list_echeances(
                        inscrit.id_inscription):
                    self._echeances.append(echeance)
                    rows.append({
                        "id_echeance": echeance.id_echeance,
                        "matricule": inscrit.matricule,
                        "nom_complet": inscrit.nom_complet,
                        "libelle": echeance.libelle,
                        "date_echeance": echeance.date_echeance,
                        "montant_du": echeance.montant_du,
                        "remise": echeance.remise,
                        "total_paye": echeance.total_paye,
                        "reste": echeance.reste,
                        "statut": echeance.statut,
                        "__entity__": echeance,
                    })
        self.echeance_table.set_rows(rows)

    def _load_paiements(self) -> None:
        row = self.echeance_table.selected_row()
        if row is None:
            self.paiement_table.set_rows([])
            return
        echeance = row["__entity__"]
        self._selected_echeance = echeance
        paiements = self.services.ecolage.list_paiements(echeance.id_echeance)
        self.paiement_table.set_rows([{
            "id_paiement": p.id_paiement,
            "num_recu": p.num_recu,
            "date_paiement": p.date_paiement,
            "montant": p.montant,
            "mode_paie": p.mode_paie,
            "ref_externe": p.ref_externe,
            "code_utr": p.code_utr,
            "__entity__": p,
        } for p in paiements])

    # ----- Tarifs et échéanciers -----

    def create_tarif(self) -> None:
        classe = self._selected_classe()
        if classe is None:
            show_error("Sélectionnez une classe.", "Aucune classe", parent=self)
            return
        fields = [
            dict(label="Type de frais *", kind="text", width=24, required=True,
                 row=0, column=0),
            dict(label="Montant *", kind="float", width=14, required=True,
                 row=0, column=1),
            dict(label="Nombre de tranches (1-24)", kind="int", width=8,
                 initial=1, row=1, column=0),
            dict(label="Obligatoire", kind="bool", initial=True, row=1,
                 column=1),
            dict(label="Observation", kind="memo", width=32, row=2, column=0),
        ]

        def submit(values):
            tarif = Tarif(
                id_classe=classe.id_classe,
                type_frais=values["Type de frais"],
                montant=Decimal(str(values["Montant"] or 0)),
                nb_tranches=values["Nombre de tranches (1-24)"] or 1,
                obligatoire=values["Obligatoire"],
                observation=values["Observation"],
            )
            return self.services.ecolage.save_tarif(tarif,
                                                    self.session.login)

        if run_entity_dialog(self, f"Nouveau tarif — {classe.libelle}", fields,
                             submit, "Enregistrer le tarif"):
            self.refresh()

    def generer_echeancier(self) -> None:
        tarif_row = self.tarif_table.require_selection(parent=self,
                                                       message="Sélectionnez d’abord un tarif.")
        if tarif_row is None:
            return
        tarif = tarif_row["__entity__"]
        classe = self._selected_classe()
        if classe is None:
            return
        inscrits = self.services.enrollments.list_by_classe(classe.id_classe)
        if not inscrits:
            show_error("Aucun étudiant inscrit dans cette classe.", "Classe vide",
                       parent=self)
            return
        labels = [f"{i.num_inscription or i.id_inscription} — {i.nom_complet}"
                  for i in inscrits]
        fields = [
            dict(label="Inscription *", kind="choice", width=42, values=labels,
                 row=0, column=0),
        ]

        def submit(values):
            index = labels.index(values["Inscription"])
            return self.services.ecolage.generer_echeancier(
                inscrits[index].id_inscription, tarif.id_tarif,
                self.session.login)

        if run_entity_dialog(self, f"Générer l’échéancier — {tarif.type_frais}",
                             fields, submit, "Générer", two_columns=False):
            self.refresh()

    # ----- Encaissements -----

    def encaisser(self) -> None:
        row = self.echeance_table.require_selection(
            parent=self, message="Sélectionnez d’abord une échéance.")
        if row is None:
            return
        echeance = row["__entity__"]
        reste = echeance.reste

        from ltadmin.services.business.eco_service import MODES_PAIEMENT
        montant_label = f"Montant (reste : {reste:,.0f})".replace(",", " ")
        fields = [
            dict(label=montant_label + " *",
                 kind="float", width=14, initial=float(reste),
                 required=True, row=0, column=0),
            dict(label="Mode de paiement *", kind="choice", width=18,
                 values=list(MODES_PAIEMENT), initial=MODES_PAIEMENT[0],
                 required=True, row=0, column=1),
            dict(label="Référence (chèque, transaction…)", kind="text", width=22,
                 row=1, column=0),
            dict(label="Observation", kind="text", width=22, row=1, column=1),
        ]

        def submit(values):
            montant = Decimal(str(values[montant_label] or 0))
            return self.services.ecolage.encaisser(
                echeance.id_echeance, montant, values["Mode de paiement"],
                values["Référence (chèque, transaction…)"],
                values["Observation"], self.session.login)

        if run_entity_dialog(self, "Encaisser un paiement", fields, submit,
                             "Encaisser"):
            self._load_echeances()
            self._load_paiements()

    def accorder_remise(self) -> None:
        row = self.echeance_table.require_selection(
            parent=self, message="Sélectionnez d’abord une échéance.")
        if row is None:
            return
        echeance = row["__entity__"]
        fields = [
            dict(label=f"Remise (dû : {echeance.montant_du or 0:,.0f})".replace(",", " "),
                 kind="float", width=14, initial=float(echeance.remise or 0),
                 row=0, column=0),
        ]

        def submit(values):
            remise = values[list(values.keys())[0]]
            return self.services.ecolage.accorder_remise(
                echeance.id_echeance,
                Decimal(str(remise)) if remise is not None else Decimal("0"),
                self.session.login)

        if run_entity_dialog(self, "Accorder une remise", fields, submit,
                             "Accorder", two_columns=False):
            self._load_echeances()

    def annuler_paiement(self) -> None:
        row = self.paiement_table.require_selection(
            parent=self, message="Sélectionnez d’abord un paiement.")
        if row is None:
            return
        paiement = row["__entity__"]
        if not confirm(f"Annuler le paiement {paiement.num_recu} "
                       f"de {paiement.montant} ?", "Annulation", parent=self):
            return
        if show_result(self.services.ecolage.annuler_paiement(
                paiement.id_paiement, self.session.login), parent=self):
            self._load_echeances()
            self._load_paiements()
