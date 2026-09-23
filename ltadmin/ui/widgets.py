"""Composants UI partagés : tableaux, formulaires, boîtes de dialogue.

Les champs date utilisent le sélecteur DatePicker (JJ/MM/AAAA comme dans
LTA_ADM.accdb) — aucune saisie libre. Les messages de validation nomment
toujours le champ fautif et sont affichés en ligne sous le champ.
"""

from __future__ import annotations

import datetime as _dt
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from ltadmin.core.result import Result
from ltadmin.ui.date_picker import DatePicker
from ltadmin.ui.date_picker import parse_date as _parse_date_like
from ltadmin.ui.theme import Theme

__all__ = [
    "show_result", "show_info", "show_error", "confirm", "DataTable",
    "Toolbar", "FormField", "parse_date", "ask_save_csv", "DatePicker",
]


def parse_date(value):
    """Analyse une date saisie ou lue : None → None ; date/datetime →
    datetime ; texte JJ/MM/AAAA (ou ISO) → datetime. Lève ValueError si le
    texte est invalide. Source unique : ltadmin.ui.date_picker.parse_date."""
    return _parse_date_like(value)


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

def show_result(result: Result, parent: Optional[tk.Widget] = None) -> bool:
    """Affiche le résultat d'une opération ; True si succès."""
    if result.success:
        messagebox.showinfo("Succès", result.message, parent=parent)
        return True
    detail = ""
    if result.errors:
        detail = "\n\n" + "\n".join(f"• {e}" for e in result.errors[:8])
        if len(result.errors) > 8:
            detail += f"\n• … ({len(result.errors) - 8} autre(s))"
    messagebox.showerror("Opération impossible", result.message + detail,
                         parent=parent)
    return False


def show_info(title: str, message: str, parent=None) -> None:
    messagebox.showinfo(title, message, parent=parent)


def show_error(message: str, title: str = "Erreur", parent=None) -> None:
    messagebox.showerror(title, message, parent=parent)


def confirm(message: str, title: str = "Confirmation", parent=None) -> bool:
    return messagebox.askyesno(title, message, parent=parent, icon="question")


# ---------------------------------------------------------------------------
# Tableau de données (grille)
# ---------------------------------------------------------------------------

class DataTable(ttk.Frame):
    """Grille générique : colonnes, tri par clic d'en-tête, double-clic."""

    def __init__(self, parent, columns: Sequence[Tuple[str, str, int, str]],
                 on_double_click: Optional[Callable[[Dict[str, Any]], None]] = None,
                 on_delete: Optional[Callable[[Dict[str, Any]], None]] = None,
                 on_refresh: Optional[Callable[[], None]] = None,
                 **kwargs):
        """columns : liste de (clé, en-tête, largeur_px, ancrage) — ancrage 'w' ou
        'center' ; largeur négative = colonne masquée (identifiants).
        """
        super().__init__(parent, **kwargs)
        visible = [c for c in columns if c[2] > 0]
        self._columns = columns
        self._rows: List[Dict[str, Any]] = []
        self._sort_state: Dict[str, bool] = {}

        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(
            container, columns=[c[0] for c in visible], show="headings",
            selectmode="browse")
        for key, header, width, anchor in visible:
            self.tree.heading(key, text=header,
                              command=lambda k=key: self.sort_by(k))
            stretch = width >= 180
            self.tree.column(key, width=abs(width), anchor=anchor or "w",
                             stretch=stretch)
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL,
                                  command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        if on_double_click:
            self.tree.bind("<Double-1>",
                           lambda _e: self._fire(on_double_click))
        if on_delete:
            self.tree.bind("<Delete>", lambda _e: self._fire(on_delete))
        if on_refresh:
            self.tree.bind("<F5>", lambda _e: on_refresh())

        self._counter = ttk.Label(self, text="0 ligne", style="Muted.TLabel")
        self._counter.pack(anchor="w", pady=(4, 0))

    # ----- API -----

    def set_columns(self, columns: Sequence[Tuple[str, str, int, str]]) -> None:
        """Remplace les colonnes à la volée (états dynamiques)."""
        self._columns = list(columns)
        visible = [c for c in columns if c[2] > 0]
        self.tree.configure(columns=[c[0] for c in visible])
        for key, header, width, anchor in visible:
            self.tree.heading(key, text=header,
                              command=lambda k=key: self.sort_by(k))
            self.tree.column(key, width=abs(width), anchor=anchor or "w",
                             stretch=width >= 180)
        self._rows = []
        self.tree.delete(*self.tree.get_children())
        self._counter.configure(text="Aucune ligne")

    def set_rows(self, rows: List[Dict[str, Any]]) -> None:
        self._rows = rows
        self.tree.delete(*self.tree.get_children())
        for index, row in enumerate(rows):
            values = [self._cell(row.get(key)) for key, _, width, _ in
                      self._columns if width > 0]
            tag = "alt" if index % 2 else ""
            self.tree.insert("", tk.END, values=values, tags=(tag,))
        self.tree.tag_configure("alt", background=Theme.ROW_ALT)
        self._counter.configure(
            text=f"{len(rows)} ligne(s)" if rows else "Aucune ligne")

    def selected_row(self) -> Optional[Dict[str, Any]]:
        selection = self.tree.selection()
        if not selection:
            return None
        index = self.tree.index(selection[0])
        if 0 <= index < len(self._rows):
            return self._rows[index]
        return None

    def require_selection(self, parent=None,
                          message: str = "Sélectionnez d’abord une ligne.") -> Optional[Dict[str, Any]]:
        row = self.selected_row()
        if row is None:
            show_error(message, "Aucune sélection", parent=parent)
        return row

    def sort_by(self, key: str) -> None:
        ascending = not self._sort_state.get(key, False)
        self._sort_state = {key: ascending}

        def sort_value(row):
            raw = row.get(key)
            if raw is None:
                return (3, 0.0, "")
            if isinstance(raw, bool):
                return (0, float(raw), "")
            if isinstance(raw, (int, float)):
                return (0, float(raw), "")
            if isinstance(raw, _dt.datetime):
                return (1, raw.timestamp(), "")
            text = str(raw)
            try:
                parsed = parse_date(text)
            except ValueError:
                parsed = None
            if parsed is not None:
                return (1, parsed.timestamp(), "")
            return (2, 0.0, text.lower())

        self._rows.sort(key=sort_value, reverse=not ascending)
        self.set_rows(self._rows)

    @staticmethod
    def _cell(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "Oui" if value else "Non"
        if isinstance(value, _dt.datetime):
            # JJ/MM/AAAA comme Access ; heure uniquement si elle est renseignée.
            if (value.hour, value.minute, value.second, value.microsecond) \
                    == (0, 0, 0, 0):
                return value.strftime("%d/%m/%Y")
            return value.strftime("%d/%m/%Y %H:%M")
        if isinstance(value, _dt.date):
            return value.strftime("%d/%m/%Y")
        if hasattr(value, "quantize"):  # Decimal
            return f"{value:,.2f}".replace(",", " ").replace(".", ",")
        return str(value)

    def _fire(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        row = self.selected_row()
        if row is not None:
            callback(row)


# ---------------------------------------------------------------------------
# Barre d'outils standard
# ---------------------------------------------------------------------------

class Toolbar(ttk.Frame):

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._left = ttk.Frame(self)
        self._left.pack(side=tk.LEFT)
        self._right = ttk.Frame(self)
        self._right.pack(side=tk.RIGHT)
        self._left_index = 0

    def add_button(self, text: str, command: Callable[[], None],
                   accent: bool = False, side: str = "left") -> ttk.Button:
        style = "Accent.TButton" if accent else "TButton"
        target = self._left if side == "left" else self._right
        button = ttk.Button(target, text=text, command=command, style=style)
        if side == "left":
            button.pack(side=tk.LEFT, padx=(0, 8))
        else:
            button.pack(side=tk.RIGHT, padx=(8, 0))
        return button

    def add_label(self, text: str, side: str = "left") -> ttk.Label:
        target = self._left if side == "left" else self._right
        label = ttk.Label(target, text=text, style="Muted.TLabel")
        if side == "left":
            label.pack(side=tk.LEFT, padx=(0, 10))
        else:
            label.pack(side=tk.RIGHT, padx=(10, 0))
        return label


# ---------------------------------------------------------------------------
# Champs de formulaire
# ---------------------------------------------------------------------------

def _normalize_label(label: str) -> Tuple[str, bool]:
    """« Nom * » → (« Nom », True) : la clé du champ perd l'astérisque
    obligatoire, qui reste affiché dans le libellé."""
    raw = (label or "").strip()
    if raw.endswith("*"):
        return raw[:-1].rstrip(), True
    return raw, False


def _to_number(raw: str, integer: bool) -> Optional[Any]:
    """« 200 000,50 » / « 200000.50 » → nombre ; None si illisible.
    Espaces (normaux, finesse, insécables) et virgule décimale acceptés."""
    cleaned = (raw.replace("\u202f", "").replace("\u00a0", "")
               .replace(" ", "").replace(",", "."))
    if not cleaned:
        return None
    try:
        return int(cleaned) if integer else float(cleaned)
    except ValueError:
        return None


class FormField:
    """Champ label + widget, avec valeur typée, validation en ligne et
    verrouillage. Les dates passent par le sélecteur DatePicker."""

    def __init__(self, parent, label: str, kind: str = "text", width: int = 30,
                 values: Optional[List[str]] = None, required: bool = False,
                 max_length: Optional[int] = None, readonly: bool = False,
                 secret: bool = False, initial: Any = None, row: int = 0,
                 column: int = 0, sticky: str = "w", multiline: bool = False):
        self.kind = kind
        self.values = values or []
        base, starred = _normalize_label(label)
        self.label_text = base
        self.required = bool(required or starred)
        self.max_length = max_length

        label_display = base + (" *" if self.required else "")
        self.label_widget = ttk.Label(parent, text=label_display)
        self.label_widget.grid(row=row, column=column * 2, sticky="ne",
                               padx=(0, 8), pady=4)
        self.frame = ttk.Frame(parent)
        self.frame.grid(row=row, column=column * 2 + 1, sticky=sticky + "ew",
                        pady=4)
        self._error_label = ttk.Label(self.frame, text="", style="Error.TLabel",
                                      wraplength=280, justify="left")

        if kind == "bool":
            self.variable = tk.BooleanVar(value=bool(initial))
            self.widget: tk.Widget = ttk.Checkbutton(
                self.frame, variable=self.variable,
                state="disabled" if readonly else "normal")
            self.widget.pack(anchor="w")
            self._focus_widget = self.widget
        elif kind == "choice":
            self.variable = tk.StringVar(
                value=initial if initial is not None else "")
            self.widget = ttk.Combobox(
                self.frame, textvariable=self.variable, values=self.values,
                width=width, state="disabled" if readonly else "readonly")
            self.widget.pack(anchor="w")
            self._focus_widget = self.widget
        elif kind == "date":
            # Sélecteur calendrier (JJ/MM/AAAA) — pas de champ texte libre.
            self.picker = DatePicker(self.frame, initial=initial,
                                     required=self.required,
                                     readonly=readonly)
            self.picker.pack(anchor="w")
            self.widget = self.picker
            self._focus_widget = self.picker
        elif kind == "memo":
            self.variable = tk.StringVar(
                value=initial if initial is not None else "")
            self.widget = tk.Text(self.frame, width=width, height=4,
                                  wrap=tk.WORD)
            if initial is not None:
                self.widget.insert("1.0", str(initial))
            self.widget.pack(anchor="w")
            if readonly:
                self.widget.configure(state="disabled")
            self._focus_widget = self.widget
        else:  # text / int / float
            show = "*" if secret else ""
            self.variable = tk.StringVar(
                value="" if initial is None else str(initial))
            self.widget = ttk.Entry(self.frame, textvariable=self.variable,
                                    width=width, show=show)
            self.widget.pack(anchor="w")
            if readonly:
                self.widget.configure(state="disabled")
            self._focus_widget = self.widget

    @property
    def value(self) -> Any:
        if self.kind == "bool":
            return self.variable.get()
        if self.kind == "choice":
            return self.variable.get() or None
        if self.kind == "date":
            return self.picker.get_date()
        if self.kind == "memo":
            return self.widget.get("1.0", "end").strip() or None
        raw = self.variable.get().strip()
        if raw == "":
            return None
        if self.kind == "int":
            return _to_number(raw, integer=True)
        if self.kind in ("float", "decimal"):
            return _to_number(raw, integer=False)
        return raw

    @value.setter
    def value(self, new_value: Any) -> None:
        if self.kind == "bool":
            self.variable.set(bool(new_value))
        elif self.kind == "date":
            self.picker.set_date(new_value)
        elif self.kind == "memo":
            self.widget.delete("1.0", "end")
            if new_value is not None:
                self.widget.insert("1.0", str(new_value))
        else:
            self.variable.set("" if new_value is None else str(new_value))

    def validate(self) -> Optional[str]:
        """Contrôle local : requis, formats, longueur. Retourne un message
        nommant le champ, ou None si la saisie est correcte."""
        name = f"« {self.label_text} »"
        if self.kind == "bool":
            return None  # Non est une valeur valide, jamais « manquante ».
        if self.kind == "date":
            if self.picker.get_date() is None and self.required:
                return (f"{name} : champ obligatoire — sélectionnez une date "
                        "avec le calendrier (JJ/MM/AAAA).")
            return None
        if self.kind == "choice":
            if self.required and not (self.variable.get() or "").strip():
                return (f"{name} : champ obligatoire — sélectionnez une valeur "
                        "dans la liste.")
            return None
        if self.kind == "memo":
            if self.required and not self.widget.get("1.0", "end").strip():
                return f"{name} : champ obligatoire — renseignez la valeur."
            return None
        raw = self.variable.get().strip()
        if raw == "":
            if self.required:
                return f"{name} : champ obligatoire — renseignez la valeur."
            return None
        if self.kind == "int" and _to_number(raw, integer=True) is None:
            return f"{name} : nombre entier attendu (ex. 120)."
        if self.kind in ("float", "decimal") \
                and _to_number(raw, integer=False) is None:
            return (f"{name} : nombre attendu — la virgule et l’espace sont "
                    "acceptés (ex. 200 000,50).")
        if self.max_length and len(raw) > self.max_length:
            return f"{name} : {self.max_length} caractères maximum."
        return None

    def mark_error(self, message: Optional[str] = None) -> None:
        """Affiche (ou efface) le message d'erreur sous le champ."""
        if message:
            self._error_label.configure(text=message)
            self.label_widget.configure(foreground=Theme.DANGER)
            if not self._error_label.winfo_ismapped():
                self._error_label.pack(anchor="w", fill=tk.X)
        else:
            self._error_label.configure(text="")
            self.label_widget.configure(foreground=Theme.TEXT_DARK)
            if self._error_label.winfo_ismapped():
                self._error_label.pack_forget()
        if isinstance(self.widget, DatePicker):
            self.widget.mark_error(bool(message))

    def clear_error(self) -> None:
        self.mark_error(None)

    def focus_target(self) -> None:
        """Place le curseur sur le premier champ utile."""
        self._focus_widget.focus_set()
        if isinstance(self.widget, DatePicker):
            self.widget.focus_target()


def ask_save_csv(default_name: str, parent=None) -> Optional[str]:
    path = filedialog.asksaveasfilename(
        parent=parent, defaultextension=".csv", initialfile=default_name,
        filetypes=[("Fichier CSV", "*.csv"), ("Tous les fichiers", "*.*")])
    return path or None
