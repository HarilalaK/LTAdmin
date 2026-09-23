"""Écran Profils utilisateurs : comptes, profils, activation."""

from __future__ import annotations

import tkinter as tk

from ltadmin.models.entities import Utilisateur
from ltadmin.services.auth.habilitations import PROFILS_CONNUS
from ltadmin.ui.dialogs import run_entity_dialog
from ltadmin.ui.views.base_view import BaseView
from ltadmin.ui.widgets import DataTable, confirm, show_result

COLUMNS = [
    ("code_utr", "Identifiant", 140, "w"),
    ("nom_utr", "Nom", 240, "w"),
    ("profil", "Profil", 160, "w"),
    ("actif", "Actif", 70, "center"),
]


class UsersView(BaseView):
    title = "Profils utilisateurs"
    subtitle = "Comptes de connexion, profils et habilitations"

    def __init__(self, parent, services, session, **kwargs):
        super().__init__(parent, services, session, **kwargs)
        self.table = DataTable(self.content, COLUMNS, on_refresh=self.refresh)
        self.table.pack(fill=tk.BOTH, expand=True)
        self.toolbar.add_button("＋ Nouveau compte", self.create_user, accent=True)
        self.toolbar.add_button("✎ Modifier", self.edit_user)
        self.toolbar.add_button("🔑 Changer le mot de passe", self.change_password)
        self.toolbar.add_button("✔ Activer / désactiver", self.toggle_actif)
        self.toolbar.add_button("🗑 Supprimer", self.delete_user)
        self.toolbar.add_label("Habilitations : Administrateur = tout ; "
                               "Direction = tout sauf Administration ; "
                               "Scolarité = pédagogie ; Comptabilité = "
                               "Écolage + Paie ; Enseignant = notes et EDT.")

    def refresh(self) -> None:
        self.table.set_rows([{
            "code_utr": u.code_utr,
            "nom_utr": u.nom_utr,
            "profil": u.profil,
            "actif": u.actif,
            "__entity__": u,
        } for u in self.services.admin.list_utilisateurs()])

    def _fields(self, user: Utilisateur) -> list:
        return [
            dict(label="Identifiant *", kind="text", width=16, required=True,
                 initial=user.code_utr,
                 readonly=user.code_utr is not None, row=0, column=0),
            dict(label="Nom *", kind="text", width=28, required=True,
                 initial=user.nom_utr, row=0, column=1),
            dict(label="Profil *", kind="choice", width=22,
                 values=list(PROFILS_CONNUS), initial=user.profil
                 or PROFILS_CONNUS[0], required=True, row=1, column=0),
            dict(label="Actif", kind="bool",
                 initial=user.actif if user.actif is not None else True,
                 row=1, column=1),
            dict(label="Mot de passe (vide = inchangé)", kind="text",
                 width=20, secret=True, row=2, column=0),
        ]

    def create_user(self) -> None:
        user = Utilisateur()

        def submit(values):
            user.code_utr = values["Identifiant *"]
            user.nom_utr = values["Nom *"]
            user.profil = values["Profil *"]
            user.actif = values["Actif"]
            mot_de_passe = values["Mot de passe (vide = inchangé)"]
            return self.services.admin.save_utilisateur(
                user, mot_de_passe, self.session.login)

        if run_entity_dialog(self, "Nouveau compte", self._fields(user),
                             submit, "Créer le compte"):
            self.refresh()

    def edit_user(self) -> None:
        row = self.table.require_selection(parent=self)
        if row is None:
            return
        user = row["__entity__"]

        def submit(values):
            user.nom_utr = values["Nom *"]
            user.profil = values["Profil *"]
            user.actif = values["Actif"]
            mot_de_passe = values["Mot de passe (vide = inchangé)"]
            return self.services.admin.save_utilisateur(
                user, mot_de_passe, self.session.login)

        if run_entity_dialog(self, f"Modifier « {user.code_utr} »",
                             self._fields(user), submit):
            self.refresh()

    def change_password(self) -> None:
        row = self.table.require_selection(parent=self)
        if row is None:
            return
        user = row["__entity__"]
        fields = [
            dict(label="Ancien mot de passe *", kind="text", width=20,
                 secret=True, required=True, row=0, column=0),
            dict(label="Nouveau mot de passe *", kind="text", width=20,
                 secret=True, required=True, row=1, column=0),
            dict(label="Confirmation *", kind="text", width=20, secret=True,
                 required=True, row=2, column=0),
        ]

        def submit(values):
            if values["Nouveau mot de passe *"] != values["Confirmation *"]:
                from ltadmin.core.result import Result
                return Result.fail("La confirmation ne correspond pas au "
                                   "nouveau mot de passe.", "VALIDATION")
            return self.services.authentication.change_password(
                user.code_utr, values["Ancien mot de passe *"],
                values["Nouveau mot de passe *"])

        if run_entity_dialog(self, f"Mot de passe — {user.code_utr}", fields,
                             submit, "Modifier", two_columns=False):
            self.refresh()

    def toggle_actif(self) -> None:
        row = self.table.require_selection(parent=self)
        if row is None:
            return
        user = row["__entity__"]
        cible = not bool(user.actif)
        if show_result(self.services.admin.set_actif(
                user.code_utr, cible, self.session.login), parent=self):
            self.refresh()

    def delete_user(self) -> None:
        row = self.table.require_selection(parent=self)
        if row is None:
            return
        user = row["__entity__"]
        if not confirm(f"Supprimer le compte « {user.code_utr} » ?", "Suppression",
                       parent=self):
            return
        if show_result(self.services.admin.delete_utilisateur(
                user.code_utr, self.session.login), parent=self):
            self.refresh()
