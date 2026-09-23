"""Thème visuel de l'application (portage des couleurs WinForms)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class Theme:
    """Palette et styles. Sombre pour la coque, clair pour les vues."""

    # Palette principale
    SIDEBAR_BG = "#131F34"
    SIDEBAR_HOVER = "#1B2B47"
    TOPBAR_BG = "#1B2940"
    ACCENT = "#1E69D9"
    ACCENT_HOVER = "#1554B0"
    SUCCESS = "#0F8A60"
    WARNING = "#CD7E16"
    DANGER = "#B3372F"
    VIEW_BG = "#F5F7FA"
    CARD_BG = "#FFFFFF"
    TEXT_LIGHT = "#E8EDF5"
    TEXT_MUTED = "#93A1B8"
    TEXT_DARK = "#1D2733"
    BORDER = "#D7DEE8"
    ROW_ALT = "#EEF2F7"
    ROW_SELECTED = "#D6E6FB"

    # Dimensions
    SIDEBAR_WIDTH = 268
    SIDEBAR_WIDTH_COMPACT = 220
    COMPACT_BREAKPOINT = 1100
    TOPBAR_HEIGHT = 56

    FONT_FAMILY = "Segoe UI"
    FONT_SIZE = 10

    @classmethod
    def fonts(cls):
        return {
            "normal": (cls.FONT_FAMILY, cls.FONT_SIZE),
            "bold": (cls.FONT_FAMILY, cls.FONT_SIZE, "bold"),
            "small": (cls.FONT_FAMILY, 9),
            "small_bold": (cls.FONT_FAMILY, 9, "bold"),
            "title": (cls.FONT_FAMILY, 14, "bold"),
            "subtitle": (cls.FONT_FAMILY, 11, "bold"),
            "button": (cls.FONT_FAMILY, 10, "bold"),
        }

    @classmethod
    def apply_ttk_styles(cls, root: tk.Tk) -> None:
        """Enregistre les styles ttk utilisés par toutes les vues."""
        style = ttk.Style(root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=cls.VIEW_BG, foreground=cls.TEXT_DARK,
                        font=cls.fonts()["normal"])
        style.configure("TFrame", background=cls.VIEW_BG)
        style.configure("Card.TFrame", background=cls.CARD_BG)
        style.configure("TLabel", background=cls.VIEW_BG, foreground=cls.TEXT_DARK)
        style.configure("Card.TLabel", background=cls.CARD_BG, foreground=cls.TEXT_DARK)
        style.configure("Muted.TLabel", foreground=cls.TEXT_MUTED)
        style.configure("Title.TLabel", font=cls.fonts()["title"])
        style.configure("Subtitle.TLabel", font=cls.fonts()["subtitle"])
        style.configure("Field.TLabel", font=cls.fonts()["small_bold"])
        style.configure("Error.TLabel", foreground=cls.DANGER,
                        font=cls.fonts()["small"])
        style.configure("Treeview", background=cls.CARD_BG, fieldbackground=cls.CARD_BG,
                        foreground=cls.TEXT_DARK, rowheight=26, font=cls.fonts()["normal"])
        style.configure("Treeview.Heading", font=cls.fonts()["small_bold"],
                        background="#E4EAF2", foreground=cls.TEXT_DARK, relief="flat")
        style.map("Treeview",
                  background=[("selected", cls.ROW_SELECTED)],
                  foreground=[("selected", cls.TEXT_DARK)])
        style.configure("TButton", font=cls.fonts()["small_bold"], padding=(10, 5))
        style.configure("Accent.TButton", foreground="#FFFFFF", padding=(14, 6))
        style.map("Accent.TButton",
                  background=[("active", cls.ACCENT_HOVER), ("!disabled", cls.ACCENT)],
                  foreground=[("!disabled", "#FFFFFF")])
        style.configure("TEntry", padding=4)
        style.configure("TCombobox", padding=4)
        style.configure("TSpinbox", padding=3, arrowsize=13)
        style.configure("TCheckbutton", background=cls.CARD_BG)
        style.map("TCheckbutton", background=[("active", cls.CARD_BG)])
        style.configure("TNotebook.Tab", padding=(12, 6))
        style.configure("Status.TLabel", background=cls.TOPBAR_BG,
                        foreground=cls.TEXT_LIGHT)
