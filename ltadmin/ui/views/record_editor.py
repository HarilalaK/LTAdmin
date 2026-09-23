"""Éditeur d'enregistrement générique (toutes tables).

Colonnes autonumber et binaires en lecture seule ; BOOL → case à cocher ;
DATETIME → saisie + case « renseignée » ; MEMO → zone multiligne ; colonnes
dont le nom évoque un secret (PASS, MDP, SECRET) → saisie masquée.
"""

from __future__ import annotations

import datetime as _dt
import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, Optional

from ltadmin.core.result import Result
from ltadmin.data import error_helper
from ltadmin.models.db_models import DbTableInfo
from ltadmin.services.app_composition import AppServices
from ltadmin.ui.theme import Theme

SECRET_HINTS = ("PASS", "MDP", "SECRET")


def _is_secret(column_name: str) -> bool:
    upper = column_name.upper()
    return any(hint in upper for hint in SECRET_HINTS)


class RecordEditor(tk.Toplevel):

    def __init__(self, parent, services: AppServices, table: DbTableInfo,
                 original: Optional[Dict[str, Any]]):
        super().__init__(parent)
        self.services = services
        self.table = table
        self.original = original
        self._widgets: Dict[str, Any] = {}
        mode = "Modification" if original else "Création"
        self.title(f"{mode} — {table.name}")
        self.geometry("640x640")
        self.minsize(560, 480)
        self.configure(bg=Theme.VIEW_BG)

        body_container = ttk.Frame(self)
        body_container.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(body_container, highlightthickness=0,
                           bg=Theme.VIEW_BG)
        scrollbar = ttk.Scrollbar(body_container, orient=tk.VERTICAL,
                                  command=canvas.yview)
        self.body = ttk.Frame(canvas)
        self.body.bind("<Configure>", lambda _e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.body, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1 * (e.delta // 120),
                                                      "units"))

        for index, column in enumerate(table.columns):
            self._build_field(index, column)

        buttons = ttk.Frame(self, padding=(16, 0, 16, 14))
        buttons.pack(fill=tk.X)
        ttk.Button(buttons, text="Annuler", command=self.destroy).pack(
            side=tk.RIGHT)
        ttk.Button(buttons, text="Enregistrer", style="Accent.TButton",
                   command=self._save).pack(side=tk.RIGHT, padx=(0, 8))
        self.bind("<Escape>", lambda _e: self.destroy())

    # ----- Construction des champs -----

    def _build_field(self, index: int, column) -> None:
        row = index // 2
        col = index % 2
        readonly = column.autonumber or column.is_binary
        initial = (self.original or {}).get(column.name)
        label = column.name
        if column.autonumber:
            label = "⟳ " + label + " (auto)"
        elif column.is_primary_key and self.original:
            label = "🔑 " + label
        elif column.kind == "MEMO":
            label = "¶ " + label
        ttk.Label(self.body, text=label).grid(
            row=row, column=col * 2, sticky="ne", padx=(0, 8), pady=5)

        frame = ttk.Frame(self.body)
        frame.grid(row=row, column=col * 2 + 1, sticky="ew", pady=5)

        if column.kind == "BOOLEAN":
            variable = tk.BooleanVar(value=bool(initial))
            widget = ttk.Checkbutton(frame, variable=variable,
                                     state="disabled" if readonly
                                     else "normal")
            widget.pack(anchor="w")
            self._widgets[column.name] = ("bool", variable, readonly)
        elif column.kind == "MEMO":
            widget = tk.Text(frame, width=30, height=4, wrap=tk.WORD)
            if initial is not None:
                widget.insert("1.0", self._memo_text(initial))
            if readonly:
                widget.configure(state="disabled")
            widget.pack(anchor="w")
            self._widgets[column.name] = ("memo", widget, readonly)
        elif column.kind == "DATETIME":
            variable = tk.StringVar(value=self._date_text(initial))
            check = tk.BooleanVar(value=initial is not None)
            if readonly:
                ttk.Label(frame, text=variable.get() or "(vide)").pack(
                    anchor="w")
                self._widgets[column.name] = ("readonly_text", variable,
                                              True)
            else:
                box = ttk.Frame(frame)
                box.pack(anchor="w")
                ttk.Entry(box, textvariable=variable, width=16).pack(
                    side=tk.LEFT)
                ttk.Checkbutton(box, text="renseignée",
                                variable=check).pack(side=tk.LEFT, padx=(6, 0))
                self._widgets[column.name] = ("date", (variable, check),
                                              readonly)
        else:
            secret = _is_secret(column.name)
            variable = tk.StringVar(value="" if initial is None
                                    else str(initial))
            entry = ttk.Entry(frame, textvariable=variable, width=30,
                              show="*" if secret and not readonly else "")
            entry.pack(anchor="w")
            if readonly:
                entry.configure(state="disabled")
            self._widgets[column.name] = ("text", variable, readonly)

    @staticmethod
    def _date_text(value) -> str:
        if isinstance(value, _dt.datetime):
            return value.strftime("%d/%m/%Y %H:%M:%S")
        return str(value) if value is not None else ""

    @staticmethod
    def _memo_text(value) -> str:
        if isinstance(value, bytes):
            return f"(binaire : {len(value)} octets)"
        return str(value)

    # ----- Enregistrement -----

    def _collect(self) -> Optional[Dict[str, Any]]:
        values: Dict[str, Any] = {}
        for column in self.table.columns:
            kind, widget, readonly = self._widgets.get(
                column.name, (None, None, True))
            if readonly or kind is None:
                continue
            if kind == "bool":
                values[column.name] = bool(widget.get())
            elif kind == "memo":
                text = widget.get("1.0", "end").strip()
                values[column.name] = text or None
            elif kind == "date":
                variable, check = widget
                if not check.get():
                    values[column.name] = None
                else:
                    raw = variable.get().strip()
                    try:
                        values[column.name] = _dt.datetime.strptime(
                            raw, "%d/%m/%Y %H:%M:%S")
                    except ValueError:
                        try:
                            values[column.name] = _dt.datetime.strptime(
                                raw, "%d/%m/%Y")
                        except ValueError:
                            from ltadmin.ui.widgets import show_error
                            show_error(f"{column.name} : date invalide "
                                       "(JJ/MM/AAAA ou JJ/MM/AAAA HH:MM:SS).",
                                       "Saisie invalide", parent=self)
                            return None
            else:
                raw = widget.get().strip()
                if column.kind in ("LONG",):
                    try:
                        values[column.name] = int(raw) if raw else None
                    except ValueError:
                        from ltadmin.ui.widgets import show_error
                        show_error(f"{column.name} : nombre entier attendu.",
                                   "Saisie invalide", parent=self)
                        return None
                elif column.kind in ("DOUBLE", "CURRENCY"):
                    try:
                        values[column.name] = float(raw.replace(",", ".")) \
                            if raw else None
                    except ValueError:
                        from ltadmin.ui.widgets import show_error
                        show_error(f"{column.name} : nombre attendu.",
                                   "Saisie invalide", parent=self)
                        return None
                else:
                    values[column.name] = raw or None
        return values

    def _save(self) -> None:
        values = self._collect()
        if values is None:
            return
        if not self._validate_lengths(values):
            return
        try:
            if self.original is None:
                self.services.tables.insert(self.table, values)
                self.services.journal.log_creation(
                    self.services_session_code(), self.table.name, None, None)
            else:
                self.services.tables.update(self.table, self.original, values)
                self.services.journal.log_modification(
                    self.services_session_code(), self.table.name, None, None)
            from ltadmin.ui.widgets import show_result
            show_result(Result.ok("Enregistrement enregistré."), parent=self)
            self.destroy()
        except Exception as ex:
            error = error_helper.interpret(ex)
            from ltadmin.ui.widgets import show_error
            show_error(error.message, "Enregistrement impossible",
                       parent=self)

    def _validate_lengths(self, values: Dict[str, Any]) -> bool:
        for column in self.table.columns:
            value = values.get(column.name)
            if isinstance(value, str) and column.size \
                    and len(value) > column.size:
                from ltadmin.ui.widgets import show_error
                show_error(f"{column.name} : {column.size} caractères "
                           f"maximum (actuellement {len(value)}).",
                           "Saisie trop longue", parent=self)
                return False
        return True

    def services_session_code(self) -> Optional[str]:
        # Le code utilisateur est injecté par la vue appelante via session.
        owner = self.master
        session = getattr(owner, "session", None)
        return session.login if session else None
