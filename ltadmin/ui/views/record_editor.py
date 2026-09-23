"""Éditeur d'enregistrement générique (toutes tables).

Colonnes autonumber et binaires en lecture seule ; BOOLEAN → case à cocher ;
DATETIME → sélecteur de date JJ/MM/AAAA (calendrier + heure, comme les champs
Date/Heure de LTA_ADM.accdb) ; MEMO → zone multiligne ; colonnes dont le nom
évoque un secret (PASS, MDP, SECRET) → saisie masquée.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, Optional

from ltadmin.core.result import Result
from ltadmin.data import error_helper
from ltadmin.models.db_models import DbTableInfo
from ltadmin.services.app_composition import AppServices
from ltadmin.ui.date_picker import DatePicker
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
        self._error_labels: Dict[str, ttk.Label] = {}
        mode = "Modification" if original else "Création"
        self.title(f"{mode} — {table.name}")
        self.geometry("680x620")
        self.minsize(560, 460)
        self.configure(bg=Theme.VIEW_BG)
        self.transient(parent)

        outer = ttk.Frame(self)
        outer.pack(fill=tk.BOTH, expand=True)

        self._banner = tk.Label(
            outer, text="", bg=Theme.DANGER, fg="#FFFFFF", anchor="w",
            padx=14, pady=7, font=Theme.fonts()["small_bold"], wraplength=560,
            justify="left")
        self._header_frame = ttk.Frame(outer, padding=(16, 12, 16, 4))
        self._header_frame.pack(fill=tk.X)
        ttk.Label(self._header_frame, text=f"Table « {table.name} »",
                  style="Subtitle.TLabel").pack(anchor="w")
        ttk.Label(self._header_frame,
                  text="Les dates s’ouvrent dans le calendrier (JJ/MM/AAAA) — "
                       "format des champs Date/Heure de la base Access.",
                  style="Muted.TLabel").pack(anchor="w", pady=(2, 0))
        ttk.Separator(outer, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=16)

        body_container = ttk.Frame(outer)
        body_container.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(body_container, highlightthickness=0,
                           bg=Theme.VIEW_BG)
        scrollbar = ttk.Scrollbar(body_container, orient=tk.VERTICAL,
                                  command=canvas.yview)
        self.body = ttk.Frame(canvas, padding=(16, 8))
        self.body.bind("<Configure>", lambda _e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.body, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        # Le bind sur la fenêtre reçoit les événements de tous ses enfants.
        self.bind("<MouseWheel>",
                  lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        for index, column in enumerate(table.columns):
            self._build_field(index, column)

        buttons = ttk.Frame(outer, padding=(16, 4, 16, 14))
        buttons.pack(fill=tk.X)
        ttk.Button(buttons, text="Annuler", command=self.destroy).pack(
            side=tk.RIGHT)
        ttk.Button(buttons, text="Enregistrer", style="Accent.TButton",
                   command=self._save).pack(side=tk.RIGHT, padx=(0, 8))
        self.bind("<Escape>", lambda _e: self.destroy())
        self.after_idle(self._focus_first)

    # ----- Construction des champs -----

    def _build_field(self, index: int, column) -> None:
        row = index // 2
        col = index % 2
        readonly = column.autonumber or column.is_binary
        required = not column.nullable and not readonly
        initial = (self.original or {}).get(column.name)
        label = column.name
        if column.autonumber:
            label = "⟳ " + label + " (auto)"
        elif column.is_primary_key and self.original:
            label = "🔑 " + label
        elif column.kind == "MEMO":
            label = "¶ " + label
        if required:
            label = label + " *"
        cell = ttk.Frame(self.body)
        cell.grid(row=row, column=col, sticky="new", padx=(0, 12), pady=4)
        cell.columnconfigure(0, weight=1)

        label_widget = ttk.Label(cell, text=label, style="Field.TLabel")
        label_widget.pack(anchor="w")
        frame = ttk.Frame(cell)
        frame.pack(anchor="w", fill=tk.X)
        error_label = ttk.Label(cell, text="", style="Error.TLabel",
                                wraplength=260, justify="left")
        self._error_labels[column.name] = (error_label, label_widget)

        if column.kind == "BOOLEAN":
            variable = tk.BooleanVar(value=bool(initial))
            widget = ttk.Checkbutton(frame, variable=variable,
                                     state="disabled" if readonly
                                     else "normal")
            widget.pack(anchor="w")
            self._widgets[column.name] = ("bool", variable, readonly, required)
        elif column.kind == "MEMO":
            widget = tk.Text(frame, width=34, height=4, wrap=tk.WORD)
            if initial is not None:
                widget.insert("1.0", self._memo_text(initial))
            if readonly:
                widget.configure(state="disabled")
            widget.pack(anchor="w")
            self._widgets[column.name] = ("memo", widget, readonly, required)
        elif column.kind == "DATETIME":
            picker = DatePicker(frame, initial=initial, required=required,
                                with_time=True, readonly=readonly, width=11)
            picker.pack(anchor="w")
            self._widgets[column.name] = ("date", picker, readonly, required)
        else:
            secret = _is_secret(column.name)
            variable = tk.StringVar(value="" if initial is None
                                    else str(initial))
            entry = ttk.Entry(frame, textvariable=variable, width=32,
                              show="*" if secret and not readonly else "")
            entry.pack(anchor="w")
            if readonly:
                entry.configure(state="disabled")
            kind = "long" if column.kind in ("LONG",) else (
                "double" if column.kind in ("DOUBLE", "CURRENCY") else "text")
            self._widgets[column.name] = (kind, variable, readonly, required)

    @staticmethod
    def _memo_text(value) -> str:
        if isinstance(value, bytes):
            return f"(binaire : {len(value)} octets)"
        return str(value)

    def _focus_first(self) -> None:
        for name, spec in self._widgets.items():
            kind, widget, readonly, _required = spec
            if readonly:
                continue
            if kind == "date":
                widget.entry.focus_set()
            else:
                widget.focus_set()
            return

    # ----- Messages en ligne -----

    def _mark_error(self, name: str, message: Optional[str]) -> None:
        error_label, label_widget = self._error_labels.get(name, (None, None))
        if error_label is None:
            return
        if message:
            error_label.configure(text=message)
            label_widget.configure(foreground=Theme.DANGER)
            if not error_label.winfo_ismapped():
                error_label.pack(anchor="w", fill=tk.X)
        else:
            error_label.configure(text="")
            label_widget.configure(foreground=Theme.TEXT_DARK)
            if error_label.winfo_ismapped():
                error_label.pack_forget()

    def _show_banner(self, count: int, names) -> None:
        detail = ", ".join(f"« {name} »" for name in list(names)[:6])
        self._banner.configure(
            text=f"  ⚠ {count} champ(s) à corriger : {detail}")
        if not self._banner.winfo_ismapped():
            self._banner.pack(fill=tk.X, before=self._header_frame)

    def _hide_banner(self) -> None:
        if self._banner.winfo_ismapped():
            self._banner.pack_forget()

    # ----- Enregistrement -----

    def _collect(self) -> Optional[Dict[str, Any]]:
        values: Dict[str, Any] = {}
        problems = []
        first_bad = None
        for column in self.table.columns:
            spec = self._widgets.get(column.name)
            if spec is None:
                continue
            kind, widget, readonly, required = spec
            if readonly:
                continue
            name = column.name
            if kind == "bool":
                values[name] = bool(widget.get())
                self._mark_error(name, None)
                continue
            if kind == "memo":
                text = widget.get("1.0", "end").strip()
                values[name] = text or None
                error = None
                if required and not text:
                    error = f"« {name} » : champ obligatoire — renseignez la valeur."
            elif kind == "date":
                value = widget.get_date()
                values[name] = value
                error = None
                if required and value is None:
                    error = (f"« {name} » : champ obligatoire — sélectionnez "
                             "une date avec le calendrier (JJ/MM/AAAA).")
            else:
                raw = widget.get().strip()
                error = None
                if raw == "":
                    values[name] = None
                    if required:
                        error = (f"« {name} » : champ obligatoire — "
                                 "renseignez la valeur.")
                elif kind == "long":
                    cleaned = raw.replace("\u202f", "").replace("\u00a0", "") \
                        .replace(" ", "").replace(",", ".")
                    try:
                        values[name] = int(cleaned)
                    except ValueError:
                        values[name] = None
                        error = f"« {name} » : nombre entier attendu (ex. 120)."
                elif kind == "double":
                    cleaned = raw.replace("\u202f", "").replace("\u00a0", "") \
                        .replace(" ", "").replace(",", ".")
                    try:
                        values[name] = float(cleaned)
                    except ValueError:
                        values[name] = None
                        error = (f"« {name} » : nombre attendu — la virgule "
                                 "et l’espace sont acceptés (ex. 200 000,50).")
                else:
                    values[name] = raw or None
            self._mark_error(name, error)
            if error:
                problems.append(name)
                if first_bad is None:
                    first_bad = name
        if problems:
            self._show_banner(len(problems), problems)
            self._focus_field(first_bad)
            return None
        self._hide_banner()
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
        too_long = []
        for column in self.table.columns:
            value = values.get(column.name)
            if isinstance(value, str) and column.size \
                    and len(value) > column.size:
                self._mark_error(
                    column.name,
                    f"« {column.name} » : {column.size} caractères maximum "
                    f"(actuellement {len(value)}).")
                too_long.append(column.name)
            else:
                self._mark_error(column.name, None)
        if too_long:
            self._show_banner(len(too_long), too_long)
            return False
        self._hide_banner()
        return True

    def services_session_code(self) -> Optional[str]:
        # Le code utilisateur est injecté par la vue appelante via session.
        owner = self.master
        session = getattr(owner, "session", None)
        return session.login if session else None
