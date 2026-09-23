"""Sélecteur de date façon Access (LTA_ADM.accdb).

Affichage JJ/MM/AAAA (le format des champs Date/Heure d'Access en français),
calendrier déroulant — aucune saisie libre : la valeur est toujours une vraie
date, stockée en ``datetime`` comme les paramètres ODBC des champs DATETIME
de la base. Option « heure » (HH:MM) par molettes pour les Date/Heure
complètes (journal, saisies horodatées).
"""

from __future__ import annotations

import calendar as _calendar
import datetime as _dt
import tkinter as tk
from tkinter import ttk
from typing import Optional, Union

from ltadmin.ui.theme import Theme

MOIS_FR = (
    "janvier", "février", "mars", "avril", "mai", "juin", "juillet",
    "août", "septembre", "octobre", "novembre", "décembre",
)
JOURS_FR = ("Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim")

DATE_DISPLAY = "%d/%m/%Y"

DateLike = Union[str, _dt.date, _dt.datetime, None]


def format_date(value: Optional[_dt.datetime]) -> str:
    """JJ/MM/AAAA — identique à l'affichage Access français."""
    if value is None:
        return ""
    return value.strftime(DATE_DISPLAY)


def parse_date(value: DateLike) -> Optional[_dt.datetime]:
    """Analyse une date : None → None ; date/datetime → datetime ; texte
    JJ/MM/AAAA (ou ISO) → datetime. Lève ValueError si le texte est invalide."""
    if value is None:
        return None
    if isinstance(value, _dt.datetime):
        return value
    if isinstance(value, _dt.date):
        return _dt.datetime(value.year, value.month, value.day)
    raw = str(value).strip()
    if not raw:
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S",
                "%d/%m/%Y %H.%M.%S", "%Y-%m-%d", "%Y-%m-%d %H:%M",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return _dt.datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError(f"Date invalide : {raw} (format attendu JJ/MM/AAAA).")


class DatePicker(tk.Frame):
    """Champ date avec calendrier : [JJ/MM/AAAA] [📅] [✕] (+ heure en option).

    Le champ d'affichage est en lecture seule — la date vient uniquement du
    calendrier (ou du bouton Aujourd'hui), comme le sélecteur d'Access.
    """

    def __init__(self, parent, initial: DateLike = None, required: bool = False,
                 with_time: bool = False, readonly: bool = False,
                 width: int = 12, on_change=None, **kwargs):
        kwargs.setdefault("bg", Theme.CARD_BG)
        kwargs.setdefault("highlightthickness", 1)
        kwargs.setdefault("highlightbackground", Theme.BORDER)
        kwargs.setdefault("highlightcolor", Theme.ACCENT)
        super().__init__(parent, **kwargs)
        self.required = required
        self.readonly = readonly
        self.with_time = with_time
        self.on_change = on_change
        self._popup: Optional[_CalendarPopup] = None
        self._seconds = 0

        self._text = tk.StringVar(value="")
        self._hour = tk.StringVar(value="00")
        self._minute = tk.StringVar(value="00")

        row = tk.Frame(self, bg=Theme.CARD_BG)
        row.pack(fill=tk.X, padx=2, pady=2)

        self.entry = ttk.Entry(row, textvariable=self._text, width=width,
                              state="readonly", justify="center")
        self.entry.pack(side=tk.LEFT, ipady=3)
        self.entry.bind("<Button-1>", lambda _e: self._toggle_calendar())

        self._picker_button = tk.Button(
            row, text="📅", relief="flat", bd=0, cursor="hand2",
            bg=Theme.CARD_BG, activebackground=Theme.ROW_ALT,
            font=(Theme.FONT_FAMILY, 10), padx=4,
            command=self._toggle_calendar)
        self._picker_button.pack(side=tk.LEFT, padx=(2, 0))

        self._clear_button: Optional[tk.Button] = None
        if not required:
            self._clear_button = tk.Button(
                row, text="✕", relief="flat", bd=0, cursor="hand2",
                bg=Theme.CARD_BG, activebackground=Theme.ROW_ALT,
                fg=Theme.TEXT_MUTED, font=(Theme.FONT_FAMILY, 9), padx=4,
                command=self._clear)
            self._clear_button.pack(side=tk.LEFT)

        if with_time:
            ttk.Label(row, text="à", background=Theme.CARD_BG).pack(
                side=tk.LEFT, padx=(6, 2))
            self.hour_spin = ttk.Spinbox(
                row, from_=0, to=23, width=2, wrap=True,
                textvariable=self._hour, justify="center",
                command=self._emit_change)
            self.hour_spin.pack(side=tk.LEFT, ipady=2)
            ttk.Label(row, text=":", background=Theme.CARD_BG).pack(
                side=tk.LEFT)
            self.minute_spin = ttk.Spinbox(
                row, from_=0, to=59, width=2, wrap=True,
                textvariable=self._minute, justify="center",
                command=self._emit_change)
            self.minute_spin.pack(side=tk.LEFT, ipady=2)
            for spin in (self.hour_spin, self.minute_spin):
                spin.bind("<FocusOut>", lambda _e: self._emit_change())
                spin.bind("<Return>", lambda _e: self._emit_change())

        self.set_date(initial)
        if readonly:
            self._set_enabled(False)
        self.bind("<Destroy>", self._on_destroy)

    # ----- Valeur -----

    def get_date(self) -> Optional[_dt.datetime]:
        """La date saisie, ou None si vide. datetime — directement stockable
        dans les champs Date/Heure de LTA_ADM.accdb."""
        raw = self._text.get().strip()
        if not raw:
            return None
        try:
            value = parse_date(raw)
        except ValueError:
            return None
        if value is None or not self.with_time:
            return value
        hour = self._safe_int(self._hour.get(), 0, 23)
        minute = self._safe_int(self._minute.get(), 0, 59)
        return _dt.datetime(value.year, value.month, value.day, hour, minute,
                            self._seconds)

    def set_date(self, value: DateLike) -> None:
        try:
            parsed = parse_date(value)
        except ValueError:
            parsed = None
        if parsed is not None:
            self._seconds = parsed.second
            self._text.set(parsed.strftime(DATE_DISPLAY))
            self._hour.set(f"{parsed.hour:02d}")
            self._minute.set(f"{parsed.minute:02d}")
        else:
            self._seconds = 0
            self._text.set("")
            self._hour.set("00")
            self._minute.set("00")

    def clear(self) -> None:
        self.set_date(None)
        self._emit_change()

    @property
    def is_empty(self) -> bool:
        return not self._text.get().strip()

    # ----- Interactions -----

    def _clear(self) -> None:
        if self.readonly:
            return
        self.clear()
        self.close_calendar()

    def _toggle_calendar(self) -> None:
        if self.readonly:
            return
        if self._popup is not None:
            self.close_calendar()
        else:
            self.open_calendar()

    def open_calendar(self) -> None:
        if self._popup is not None:
            return
        self._popup = _CalendarPopup(self)

    def close_calendar(self) -> None:
        popup, self._popup = self._popup, None
        if popup is not None:
            popup.destroy()

    def _emit_change(self) -> None:
        if self.on_change is not None:
            self.on_change(self.get_date())

    def _on_selected(self, day: _dt.date) -> None:
        hour = self._safe_int(self._hour.get(), 0, 23)
        minute = self._safe_int(self._minute.get(), 0, 59)
        self.set_date(_dt.datetime(day.year, day.month, day.day, hour, minute))
        self.close_calendar()
        self._emit_change()

    def _on_destroy(self, _event=None) -> None:
        self.close_calendar()

    def mark_error(self, active: bool = True) -> None:
        self.configure(highlightbackground=Theme.DANGER if active
                       else Theme.BORDER)

    def focus_target(self) -> None:
        self.entry.focus_set()

    def _set_enabled(self, enabled: bool) -> None:
        state = "readonly" if enabled else "disabled"
        self.entry.configure(state=state)
        self._picker_button.configure(
            state="normal" if enabled else "disabled",
            fg=Theme.TEXT_DARK if enabled else Theme.TEXT_MUTED)
        if self._clear_button is not None:
            self._clear_button.configure(
                state="normal" if enabled else "disabled")
        if self.with_time:
            spin_state = "normal" if enabled else "disabled"
            self.hour_spin.configure(state=spin_state)
            self.minute_spin.configure(state=spin_state)

    @staticmethod
    def _safe_int(raw: str, default: int, maximum: int) -> int:
        try:
            value = int(str(raw).strip())
        except (TypeError, ValueError):
            return default
        return max(0, min(maximum, value))


class _CalendarPopup(tk.Toplevel):
    """Calendrier mensuel déroulant (mois/années français, semaine Lundi→Dim)."""

    CELL_W = 3
    PAD = 2

    def __init__(self, picker: DatePicker):
        super().__init__(picker.winfo_toplevel())
        self.picker = picker
        self.overrideredirect(True)
        self.transient(picker.winfo_toplevel())
        self.configure(bg=Theme.BORDER, padx=1, pady=1)

        selected = picker.get_date() or _dt.datetime.now()
        self._view_year = selected.year
        self._view_month = selected.month

        self._build_header()
        self._days_frame = tk.Frame(self, bg=Theme.CARD_BG)
        self._days_frame.pack(fill=tk.BOTH, padx=6, pady=(0, 4))
        for column in range(7):
            tk.Label(self._days_frame, text=JOURS_FR[column], width=self.CELL_W,
                     bg=Theme.CARD_BG, fg=Theme.TEXT_MUTED,
                     font=Theme.fonts()["small_bold"]).grid(
                row=0, column=column, padx=self.PAD, pady=(4, 2))
        self._build_footer()
        self._refresh_days()
        self._place_near_picker()

        self.bind("<Escape>", lambda _e: self.picker.close_calendar())
        self.bind("<FocusOut>", self._on_focus_out)
        self.after_idle(self.focus_force)

    # ----- Construction -----

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=Theme.CARD_BG)
        header.pack(fill=tk.X, padx=6, pady=6)
        for text, delta_months in (("«", -12), ("‹", -1)):
            button = tk.Button(
                header, text=text, relief="flat", bd=0, cursor="hand2",
                bg=Theme.CARD_BG, activebackground=Theme.ROW_ALT,
                font=(Theme.FONT_FAMILY, 9), padx=5,
                command=lambda d=delta_months: self._shift(d))
            button.pack(side=tk.LEFT)
        self._month_label = tk.Label(
            header, text="", bg=Theme.CARD_BG, fg=Theme.TEXT_DARK,
            font=Theme.fonts()["small_bold"], width=16)
        self._month_label.pack(side=tk.LEFT, expand=True)
        for text, delta_months in (("›", 1), ("»", 12)):
            button = tk.Button(
                header, text=text, relief="flat", bd=0, cursor="hand2",
                bg=Theme.CARD_BG, activebackground=Theme.ROW_ALT,
                font=(Theme.FONT_FAMILY, 9), padx=5,
                command=lambda d=delta_months: self._shift(d))
            button.pack(side=tk.LEFT)

    def _build_footer(self) -> None:
        footer = tk.Frame(self, bg=Theme.CARD_BG)
        footer.pack(fill=tk.X, padx=6, pady=(0, 6))
        today = tk.Button(
            footer, text="Aujourd’hui", relief="flat", bd=0, cursor="hand2",
            bg=Theme.CARD_BG, fg=Theme.ACCENT, activebackground=Theme.ROW_ALT,
            font=Theme.fonts()["small_bold"], padx=4,
            command=lambda: self.picker._on_selected(_dt.date.today()))
        today.pack(side=tk.LEFT)
        close = tk.Button(
            footer, text="Fermer", relief="flat", bd=0, cursor="hand2",
            bg=Theme.CARD_BG, fg=Theme.TEXT_MUTED,
            activebackground=Theme.ROW_ALT,
            font=Theme.fonts()["small"], padx=4,
            command=self.picker.close_calendar)
        close.pack(side=tk.RIGHT)

    def _refresh_days(self) -> None:
        self._month_label.configure(
            text=f"{MOIS_FR[self._view_month - 1]} {self._view_year}")
        for child in self._days_frame.winfo_children():
            if int(child.grid_info()["row"] or 0) > 0:
                child.destroy()
        today = _dt.date.today()
        selected = self.picker.get_date()
        selected_day = selected.date() if selected else None
        weeks = _calendar.Calendar(firstweekday=0).monthdatescalendar(
            self._view_year, self._view_month)
        for row_index, week in enumerate(weeks[:6], start=1):
            for column, day in enumerate(week):
                in_month = day.month == self._view_month
                bg, fg = Theme.CARD_BG, Theme.TEXT_DARK
                font = Theme.fonts()["small"]
                if not in_month:
                    fg = "#C3CBD8"
                if day == selected_day:
                    bg, fg = Theme.ACCENT, "#FFFFFF"
                    font = Theme.fonts()["small_bold"]
                elif day == today:
                    bg, fg = Theme.ROW_SELECTED, Theme.ACCENT
                    font = Theme.fonts()["small_bold"]
                cell = tk.Label(
                    self._days_frame, text=str(day.day), width=self.CELL_W,
                    bg=bg, fg=fg, font=font, cursor="hand2",
                    activebackground=Theme.ROW_ALT)
                cell.grid(row=row_index, column=column, padx=self.PAD, pady=1)
                cell.bind("<Enter>",
                          lambda e, b=bg: e.widget.configure(bg=Theme.ROW_ALT))
                cell.bind("<Leave>",
                          lambda e, b=bg: e.widget.configure(bg=b))
                cell.bind("<Button-1>",
                          lambda _e, d=day: self.picker._on_selected(d))

    def _shift(self, delta_months: int) -> None:
        month_index = self._view_year * 12 + (self._view_month - 1) \
            + delta_months
        self._view_year, month_index = divmod(month_index, 12)
        self._view_month = month_index + 1
        self._refresh_days()

    # ----- Placement et fermeture -----

    def _place_near_picker(self) -> None:
        self.update_idletasks()
        x = self.picker.entry.winfo_rootx()
        y = self.picker.winfo_rooty() + self.picker.winfo_height() + 4
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        if x + width > screen_w - 8:
            x = max(8, screen_w - width - 8)
        if y + height > screen_h - 8:
            y = max(8, self.picker.winfo_rooty() - height - 4)
        self.geometry(f"+{x}+{y}")

    def _on_focus_out(self, _event=None) -> None:
        self.after(60, self._check_focus)

    def _check_focus(self) -> None:
        """Ferme le calendrier dès que le focus part ailleurs (clic extérieur)."""
        try:
            if self.picker._popup is not self:
                return
            focused = self.focus_get()
            inside = focused is not None and (
                str(focused).startswith(str(self))
                or str(focused).startswith(str(self.picker)))
        except tk.TclError:
            return
        if not inside:
            self.picker.close_calendar()
