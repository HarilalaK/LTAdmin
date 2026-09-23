"""Vue de base : en-tête, barre d'outils, zone de contenu, rafraîchissement."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ltadmin.models.db_models import UserSession
from ltadmin.services.app_composition import AppServices
from ltadmin.ui.theme import Theme
from ltadmin.ui.widgets import Toolbar


class BaseView(ttk.Frame):
    """Toutes les vues héritent ici : titre, sous-titre, toolbar, contenu."""

    title: str = ""
    subtitle: str = ""

    def __init__(self, parent, services: AppServices, session: UserSession,
                 **kwargs):
        super().__init__(parent, **kwargs)
        self.services = services
        self.session = session
        self._toolbar: Optional[Toolbar] = None

        header = ttk.Frame(self, style="Card.TFrame",
                           padding=(16, 12, 16, 8))
        header.pack(fill=tk.X)
        ttk.Label(header, text=self.title, style="Title.TLabel",
                  background=Theme.CARD_BG).pack(anchor="w")
        if self.subtitle:
            ttk.Label(header, text=self.subtitle, style="Muted.TLabel",
                      background=Theme.CARD_BG).pack(anchor="w", pady=(2, 0))

        self.toolbar_area = ttk.Frame(self)
        self.toolbar_area.pack(fill=tk.X, padx=16, pady=(8, 4))
        self._toolbar = Toolbar(self.toolbar_area)
        self._toolbar.pack(fill=tk.X)

        self.content = ttk.Frame(self)
        self.content.pack(fill=tk.BOTH, expand=True, padx=16, pady=(4, 16))

    @property
    def toolbar(self) -> Toolbar:
        return self._toolbar

    def refresh(self) -> None:
        """Recharge les données affichées (bouton Actualiser / F5 / ouverture)."""
