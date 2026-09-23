"""Boîtes de dialogue modales : enregistrement d'entité, saisie de paiement."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional, Tuple

from ltadmin.ui.theme import Theme
from ltadmin.ui.widgets import FormField, confirm, show_error, show_result


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

        body = ttk.Frame(self, padding=18)
        body.pack(fill=tk.BOTH, expand=True)
        self._fields: List[FormField] = []
        self._layout(body, fields)

        buttons = ttk.Frame(self, padding=(18, 0, 18, 16))
        buttons.pack(fill=tk.X)
        ttk.Button(buttons, text="Annuler", command=self.destroy).pack(side=tk.RIGHT)
        self.submit_button = ttk.Button(
            buttons, text=submit_label, style="Accent.TButton",
            command=self._submit)
        self.submit_button.pack(side=tk.RIGHT, padx=(0, 8))
        self.bind("<Return>", lambda _e: self._submit())
        self.bind("<Escape>", lambda _e: self.destroy())

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
        max_row = max(rows.keys()) if rows else 0
        for column in (0, 1):
            body.columnconfigure(column * 2, weight=0)
            body.columnconfigure(column * 2 + 1, weight=1)

    def _submit(self) -> None:
        for field in self._fields:
            error = field.validate()
            if error:
                show_error(error, "Saisie incomplète", parent=self)
                return
        # Les valeurs sont retournées sous forme de dict { libellé: valeur },
        # dans l'ordre de déclaration des champs.
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
