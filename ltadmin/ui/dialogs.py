"""Boîtes de dialogue modales : enregistrement d'entité, saisie de paiement.

Le formulaire valide tous les champs d'un coup : les erreurs s'affichent en
rouge sous chaque champ + un bandeau récapitulatif (plus de message
« Champ obligatoire » sans savoir lequel). Les valeurs sont retournées dans
un dict indexé par le libellé normalisé (sans l'astérisque obligatoire).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional

from ltadmin.ui.theme import Theme
from ltadmin.ui.widgets import FormField, show_result


class EntityDialog(tk.Toplevel):
    """Formulaire générique modal : champs déclaratifs → dict de valeurs.

    fields : liste de dicts passés à FormField (label, kind, initial, …) ;
    on_submit(values: dict) → Result ; retourne True si l'opération a réussi.
    """

    def __init__(self, parent, title: str,
                 fields: List[Dict[str, Any]],
                 on_submit: Callable[[Dict[str, Any]], Any],
                 submit_label: str = "Enregistrer", two_columns: bool = True):
        super().__init__(parent)
        self.on_submit = on_submit
        self.two_columns = two_columns
        self.success = False
        self.title(title)
        self.resizable(False, False)
        self.configure(bg=Theme.VIEW_BG)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        outer = ttk.Frame(self)
        outer.pack(fill=tk.BOTH, expand=True)

        # Bandeau de validation (masqué tant que tout est correct).
        self._banner = tk.Label(
            outer, text="", bg=Theme.DANGER, fg="#FFFFFF", anchor="w",
            padx=14, pady=7, font=Theme.fonts()["small_bold"], wraplength=520,
            justify="left")

        self._header_frame = ttk.Frame(outer, padding=(18, 14, 18, 6))
        self._header_frame.pack(fill=tk.X)
        ttk.Label(self._header_frame, text=title,
                  style="Subtitle.TLabel").pack(anchor="w")
        ttk.Separator(outer, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=18)

        body = ttk.Frame(outer, padding=18)
        body.pack(fill=tk.BOTH, expand=True)
        self._fields: List[FormField] = []
        self._layout(body, fields)

        buttons = ttk.Frame(outer, padding=(18, 4, 18, 16))
        buttons.pack(fill=tk.X)
        ttk.Button(buttons, text="Annuler", command=self.destroy).pack(
            side=tk.RIGHT)
        self.submit_button = ttk.Button(
            buttons, text=submit_label, style="Accent.TButton",
            command=self._submit)
        self.submit_button.pack(side=tk.RIGHT, padx=(0, 8))
        self.bind("<Return>", self._on_return)
        self.bind("<Escape>", lambda _e: self.destroy())

        self._center_on(parent)
        self.after_idle(self._focus_first)

    def _layout(self, body: ttk.Frame, fields: List[Dict[str, Any]]) -> None:
        rows = {}
        for spec in fields:
            row = spec.pop("row", None)
            if row is None:
                row = len(self._fields) // (2 if self.two_columns else 1)
            column = spec.pop("column", 0)
            if self.two_columns and column == 0 and row in rows and rows[row] == 0:
                column = 1
            rows[row] = column
            field = FormField(body, row=row, column=column, **spec)
            self._fields.append(field)
        for column in (0, 1):
            body.columnconfigure(column * 2, weight=0)
            body.columnconfigure(column * 2 + 1, weight=1)

    def _on_return(self, _event=None):
        """Entrée valide le formulaire — sauf dans une zone de texte libre."""
        widget = self.focus_get()
        if isinstance(widget, tk.Text):
            return
        self._submit()

    def _focus_first(self) -> None:
        if self._fields:
            self._fields[0].focus_target()

    def _center_on(self, parent) -> None:
        self.update_idletasks()
        if parent is not None:
            try:
                x = parent.winfo_rootx() + max(
                    0, (parent.winfo_width() - self.winfo_width()) // 2)
                y = parent.winfo_rooty() + max(
                    0, (parent.winfo_height() - self.winfo_height()) // 3)
                self.geometry(f"+{x}+{y}")
            except tk.TclError:
                pass
        self.grab_set()

    def _submit(self) -> None:
        errors = []
        first_invalid: Optional[FormField] = None
        for field in self._fields:
            error = field.validate()
            field.mark_error(error)
            if error:
                errors.append(field.label_text)
                if first_invalid is None:
                    first_invalid = field
        if errors:
            detail = ", ".join(f"« {name} »" for name in errors[:6])
            if len(errors) > 6:
                detail += ", …"
            self._banner.configure(
                text=f"  ⚠ {len(errors)} champ(s) à corriger : {detail}")
            if not self._banner.winfo_ismapped():
                self._banner.pack(fill=tk.X, before=self._header_frame)
            if first_invalid is not None:
                first_invalid.focus_target()
            return
        if self._banner.winfo_ismapped():
            self._banner.pack_forget()
        # Valeurs indexées par le libellé normalisé (« Nom », « Prénom »…).
        values = {field.label_text: field.value for field in self._fields}
        result = self.on_submit(values)
        if hasattr(result, "success"):
            if show_result(result, parent=self):
                self.success = True
                self.destroy()
        else:
            self.success = True
            self.destroy()


def run_entity_dialog(parent, title: str, fields: List[Dict[str, Any]],
                      on_submit: Callable[[Dict[str, Any]], Any],
                      submit_label: str = "Enregistrer",
                      two_columns: bool = True) -> bool:
    dialog = EntityDialog(parent, title, fields, on_submit, submit_label,
                          two_columns)
    parent.wait_window(dialog)
    return dialog.success
