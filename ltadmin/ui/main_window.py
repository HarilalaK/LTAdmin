"""Fenêtre principale : barre latérale (menu habilité), barre supérieure
(année active, Actualiser, déconnexion) et zone de vues."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional, Type

from ltadmin.models.db_models import UserSession
from ltadmin.services.app_composition import AppServices
from ltadmin.services.auth import habilitations
from ltadmin.ui.theme import Theme
from ltadmin.ui.views.base_view import BaseView


class MainWindow(tk.Tk):

    def __init__(self, services: AppServices, session: UserSession):
        super().__init__()
        self.services = services
        self.session = session
        self.title(f"LTAdmin — Gestion scolaire ({session.display_name})")
        self.geometry("1280x800")
        self.minsize(980, 620)
        self.configure(bg=Theme.VIEW_BG)
        Theme.apply_ttk_styles(self)

        self._view_classes: Dict[str, Type[BaseView]] = {}
        self._current_view: Optional[BaseView] = None
        self._current_module: Optional[str] = None
        self._sidebar_buttons: Dict[str, tk.Widget] = {}

        self._build_shell()
        self._build_sidebar()
        self._select_default_module()
        self.bind("<Configure>", self._on_resize)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ----- Coque -----

    def _build_shell(self) -> None:
        self.sidebar = tk.Frame(self, bg=Theme.SIDEBAR_BG, width=Theme.SIDEBAR_WIDTH)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        right = tk.Frame(self, bg=Theme.VIEW_BG)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.topbar = tk.Frame(right, bg=Theme.TOPBAR_BG, height=Theme.TOPBAR_HEIGHT)
        self.topbar.pack(fill=tk.X)
        self.topbar.pack_propagate(False)
        self._build_topbar(right)

    def _build_topbar(self, parent) -> None:
        self.annee_label = tk.Label(
            self.topbar, text="", bg=Theme.TOPBAR_BG, fg=Theme.TEXT_LIGHT,
            font=Theme.fonts()["small_bold"])
        self.annee_label.pack(side=tk.RIGHT, padx=(8, 16))

        user_label = tk.Label(
            self.topbar,
            text=f"{self.session.display_name} — {self.session.role}",
            bg=Theme.TOPBAR_BG, fg=Theme.TEXT_MUTED, font=Theme.fonts()["small"])
        user_label.pack(side=tk.RIGHT, padx=8)

        disconnect = tk.Label(
            self.topbar, text="⏻ Déconnexion", bg=Theme.TOPBAR_BG,
            fg=Theme.TEXT_LIGHT, font=Theme.fonts()["small_bold"], cursor="hand2")
        disconnect.pack(side=tk.RIGHT, padx=8)
        disconnect.bind("<Button-1>", lambda _e: self._logout())

        refresh = tk.Label(
            self.topbar, text="⟳ Actualiser", bg=Theme.TOPBAR_BG,
            fg=Theme.TEXT_LIGHT, font=Theme.fonts()["small_bold"], cursor="hand2")
        refresh.pack(side=tk.RIGHT, padx=8)
        refresh.bind("<Button-1>", lambda _e: self.refresh_current())

    def _build_sidebar(self) -> None:
        brand = tk.Label(self.sidebar, text="LTAdmin", bg=Theme.SIDEBAR_BG,
                         fg=Theme.ACCENT, font=(Theme.FONT_FAMILY, 16, "bold"))
        brand.pack(anchor="w", padx=20, pady=(20, 2))
        subtitle = tk.Label(self.sidebar, text="Gestion scolaire",
                            bg=Theme.SIDEBAR_BG, fg=Theme.TEXT_MUTED,
                            font=Theme.fonts()["small"])
        subtitle.pack(anchor="w", padx=20, pady=(0, 16))

        for module in habilitations.MENU_ORDER:
            if not habilitations.can_access(self.session.role, module):
                continue
            button = tk.Label(
                self.sidebar, text="  " + module, anchor="w",
                bg=Theme.SIDEBAR_BG, fg=Theme.TEXT_LIGHT,
                font=Theme.fonts()["normal"], padx=14, pady=9, cursor="hand2")
            button.pack(fill=tk.X)
            button.bind("<Enter>", lambda _e, b=button: self._hover(b, True))
            button.bind("<Leave>", lambda _e, b=button: self._hover(b, False))
            button.bind("<Button-1>", lambda _e, m=module: self.open_module(m))
            self._sidebar_buttons[module] = button

    def _select_default_module(self) -> None:
        self.open_module(habilitations.Modules.TABLEAU_DE_BORD)
        self.refresh_annee_label()

    def _hover(self, button: tk.Label, entering: bool) -> None:
        if button.cget("text").strip() == self._current_module:
            return
        button.configure(bg=Theme.SIDEBAR_HOVER if entering else Theme.SIDEBAR_BG)

    def _highlight_sidebar(self) -> None:
        for module, button in self._sidebar_buttons.items():
            if module == self._current_module:
                button.configure(bg=Theme.ACCENT, fg="#FFFFFF")
            else:
                button.configure(bg=Theme.SIDEBAR_BG, fg=Theme.TEXT_LIGHT)

    def _on_resize(self, event) -> None:
        if event.widget is not self:
            return
        width = Theme.SIDEBAR_WIDTH_COMPACT \
            if event.width < Theme.COMPACT_BREAKPOINT else Theme.SIDEBAR_WIDTH
        try:
            self.sidebar.configure(width=width)
        except tk.TclError:
            pass

    # ----- Navigation -----

    def register_view(self, module: str, view_class: Type[BaseView]) -> None:
        self._view_classes[module] = view_class

    def open_module(self, module: str) -> None:
        view_class = self._view_classes.get(module)
        if view_class is None:
            return
        if self._current_view is not None:
            self._current_view.destroy()
        self._current_module = module
        self._current_view = view_class(self, self.services, self.session)
        self._current_view.pack(fill=tk.BOTH, expand=True)
        self._highlight_sidebar()
        self.refresh_annee_label()
        try:
            self._current_view.refresh()
        except Exception:
            pass

    def refresh_current(self) -> None:
        if self._current_view is not None:
            self._current_view.refresh()
        self.refresh_annee_label()

    def refresh_annee_label(self) -> None:
        try:
            annee = self.services.admin.get_annee_active()
            self.annee_label.configure(
                text=f"Année active : {annee.libelle}" if annee
                else "Aucune année active")
        except Exception:
            self.annee_label.configure(text="Année active : —")

    # ----- Session -----

    def _logout(self) -> None:
        from ltadmin.ui.widgets import confirm
        if not confirm("Voulez-vous vraiment vous déconnecter ?", "Déconnexion",
                       parent=self):
            return
        self.destroy()

    def _on_close(self) -> None:
        self.destroy()
