"""Écran de connexion : identifiant + mot de passe, journalisation en base."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ltadmin.models.db_models import UserSession
from ltadmin.services.app_composition import AppServices
from ltadmin.ui.theme import Theme


class LoginDialog(tk.Toplevel):

    def __init__(self, parent, services: AppServices):
        super().__init__(parent)
        self.services = services
        self.session: Optional[UserSession] = None
        self.title("LTAdmin — Connexion")
        self.resizable(False, False)
        self.configure(bg=Theme.SIDEBAR_BG)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Return>", lambda _e: self._authenticate())
        self._build()
        self.grab_set()

    def _build(self) -> None:
        card = tk.Frame(self, bg=Theme.CARD_BG)
        card.pack(padx=24, pady=24)
        inner = ttk.Frame(card, style="Card.TFrame", padding=(28, 24))
        inner.pack()

        ttk.Label(inner, text="LTAdmin", style="Title.TLabel",
                  background=Theme.CARD_BG).pack(anchor="w")
        ttk.Label(inner, text="Gestion scolaire — Lycée Technique d’Antanimena",
                  style="Muted.TLabel", background=Theme.CARD_BG).pack(anchor="w",
                                                                      pady=(2, 14))

        ttk.Label(inner, text="Identifiant", background=Theme.CARD_BG).pack(
            anchor="w", pady=(6, 2))
        self.login_var = tk.StringVar()
        login_entry = ttk.Entry(inner, textvariable=self.login_var, width=28)
        login_entry.pack(anchor="w", ipady=3)
        login_entry.focus_set()

        ttk.Label(inner, text="Mot de passe", background=Theme.CARD_BG).pack(
            anchor="w", pady=(10, 2))
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(inner, textvariable=self.password_var,
                                   width=28, show="•")
        password_entry.pack(anchor="w", ipady=3)

        self.message = ttk.Label(inner, text="", foreground=Theme.DANGER,
                                 background=Theme.CARD_BG, wraplength=240)
        self.message.pack(anchor="w", pady=(10, 4))

        buttons = ttk.Frame(inner, style="Card.TFrame")
        buttons.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(buttons, text="Annuler", command=self._cancel).pack(
            side=tk.RIGHT)
        ttk.Button(buttons, text="Se connecter", style="Accent.TButton",
                   command=self._authenticate).pack(side=tk.RIGHT, padx=(0, 8))

    def _authenticate(self) -> None:
        result = self.services.authentication.authenticate(
            self.login_var.get(), self.password_var.get())
        if result.success and result.value is not None:
            self.session = result.value
            self.grab_release()
            self.destroy()
        else:
            self.message.configure(text=result.message)
            self.password_var.set("")

    def _cancel(self) -> None:
        self.session = None
        self.grab_release()
        self.destroy()

    @staticmethod
    def run(parent, services: AppServices) -> Optional[UserSession]:
        dialog = LoginDialog(parent, services)
        parent.wait_window(dialog)
        return dialog.session
