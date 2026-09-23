"""Composants UI partagés : tableaux, formulaires, boîtes de dialogue."""

from __future__ import annotations

import datetime as _dt
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from ltadmin.core.result import Result
from ltadmin.ui.theme import Theme


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
            detail += f"\n• … ({len(result.errors) - 8} autre(s))"  # noqa: E501
    messagebox.showerror("Opération impossible", result.message + detail, parent=parent)
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
        """
        columns : liste de (clé, en-tête, largeur_px, ancrage) — ancrage 'w' ou
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
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.tree.yview)
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
            values = [self._cell(row.get(key)) for key, _, width, _ in self._columns
                      if width > 0]
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
                return (1, "")
            if isinstance(raw, (int, float)):
                return (0, raw)
            if isinstance(raw, _dt.datetime):
                return (0, raw)
            return (0, str(raw).lower())

        self._rows.sort(key=sort_value, reverse=not ascending)
        self.set_rows(self._rows)

    @staticmethod
    def _cell(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "Oui" if value else "Non"
        if isinstance(value, _dt.datetime):
            return value.strftime("%d/%m/%Y %H:%M")
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

class FormField:
    """Champ label + widget, avec valeur typée et verrouillage."""

    def __init__(self, parent, label: str, kind: str = "text", width: int = 30,
                 values: Optional[List[str]] = None, required: bool = False,
                 max_length: Optional[int] = None, readonly: bool = False,
                 secret: bool = False, initial: Any = None, row: int = 0,
                 column: int = 0, sticky: str = "w", multiline: bool = False):
        self.kind = kind
        self.values = values or []
        self.required = required
        self.max_length = max_length

        label_text = label + (" *" if required else "")
        self.label_text = label
        ttk.Label(parent, text=label_text).grid(
            row=row, column=column * 2, sticky="ne", padx=(0, 8), pady=4)
        self.frame = ttk.Frame(parent)
        self.frame.grid(row=row, column=column * 2 + 1, sticky=sticky + "ew",
                        pady=4)

        if kind == "bool":
            self.variable = tk.BooleanVar(value=bool(initial))
            self.widget: tk.Widget = ttk.Checkbutton(
                self.frame, variable=self.variable, state="disabled" if readonly else "normal")
            self.widget.pack(anchor="w")
        elif kind == "choice":
            self.variable = tk.StringVar(value=initial if initial is not None else "")
            self.widget = ttk.Combobox(
                self.frame, textvariable=self.variable, values=self.values,
                width=width, state="disabled" if readonly else "readonly")
            self.widget.pack(anchor="w")
        elif kind == "date":
            # Date + case à cocher « renseignée » (équivalent ShowCheckBox).
            self.variable = tk.StringVar(
                value=initial.strftime("%d/%m/%Y") if isinstance(initial, _dt.datetime)
                else (initial or ""))
            self.checkbox = tk.BooleanVar(value=initial is not None)
            self.widget = ttk.Frame(self.frame)
            entry = ttk.Entry(self.widget, textvariable=self.variable, width=14)
            entry.pack(side=tk.LEFT)
            ttk.Checkbutton(self.widget, text="", variable=self.checkbox).pack(
                side=tk.LEFT, padx=(6, 0))
            self.widget.pack(anchor="w")
        elif kind == "memo":
            self.variable = tk.StringVar(
                value=initial if initial is not None else "")
            self.widget = tk.Text(self.frame, width=width, height=4, wrap=tk.WORD)
            if initial is not None:
                self.widget.insert("1.0", str(initial))
            self.widget.pack(anchor="w")
            if readonly:
                self.widget.configure(state="disabled")
        else:  # text / int / float
            show = "*" if secret else ""
            self.variable = tk.StringVar(
                value="" if initial is None else str(initial))
            self.widget = ttk.Entry(self.frame, textvariable=self.variable,
                                    width=width, show=show)
            self.widget.pack(anchor="w")
            if readonly:
                self.widget.configure(state="disabled")

    @property
    def value(self) -> Any:
        if self.kind == "bool":
            return self.variable.get()
        if self.kind == "choice":
            return self.variable.get() or None
        if self.kind == "date":
            if not getattr(self, "checkbox", tk.BooleanVar(value=False)).get():
                return None
            return self.variable.get().strip() or None
        if self.kind == "memo":
            return self.widget.get("1.0", "end").strip() or None
        raw = self.variable.get().strip()
        if raw == "":
            return None
        if self.kind == "int":
            try:
                return int(raw.replace(" ", "").replace(",", "."))
            except ValueError:
                return None
        if self.kind in ("float", "decimal"):
            try:
                return float(raw.replace(",", "."))
            except ValueError:
                return None
        return raw

    @value.setter
    def value(self, new_value: Any) -> None:
        if self.kind == "bool":
            self.variable.set(bool(new_value))
        elif self.kind == "memo":
            self.widget.delete("1.0", "end")
            if new_value is not None:
                self.widget.insert("1.0", str(new_value))
        else:
            self.variable.set("" if new_value is None else str(new_value))

    def validate(self) -> Optional[str]:
        """Contrôle local : requis, formats, longueur (les règles métier sont
        dans les validateurs des services)."""
        value = self.value
        if self.required and (value is None or value == "" or value is False):
            return "Champ obligatoire : renseignez la valeur."
        if self.kind == "date" and isinstance(value, str):
            try:
                _dt.datetime.strptime(value, "%d/%m/%Y")
            except ValueError:
                return "Date invalide : format attendu JJ/MM/AAAA."
        if self.kind == "int" and value is not None and not isinstance(value, int):
            return "Nombre entier attendu."
        if self.kind in ("float", "decimal") and value is not None \
                and not isinstance(value, float):
            return "Nombre attendu (la virgule est acceptée)."
        if self.max_length and isinstance(value, str) and len(value) > self.max_length:
            return f"{self.max_length} caractères maximum."
        return None


def parse_date(text: Optional[str]) -> Optional[_dt.datetime]:
    """Analyse JJ/MM/AAAA (ou AAAA-MM-JJ) en datetime ; None si vide/invalide."""
    if not text or not str(text).strip():
        return None
    raw = str(text).strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S",
                "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return _dt.datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError(f"Date invalide : {raw} (format attendu JJ/MM/AAAA).")


def ask_save_csv(default_name: str, parent=None) -> Optional[str]:
    path = filedialog.asksaveasfilename(
        parent=parent, defaultextension=".csv", initialfile=default_name,
        filetypes=[("Fichier CSV", "*.csv"), ("Tous les fichiers", "*.*")])
    return path or None
