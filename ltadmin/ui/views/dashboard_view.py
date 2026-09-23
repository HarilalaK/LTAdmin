"""Tableau de bord : compteurs rapides et alertes de l'année active."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ltadmin.services.statistics.statistics_service import DashboardData
from ltadmin.ui.theme import Theme
from ltadmin.ui.views.base_view import BaseView


class _StatCard(ttk.Frame):

    def __init__(self, parent, label: str, value: str, hint: str = "",
                 color: str = Theme.ACCENT):
        super().__init__(parent, style="Card.TFrame", padding=(16, 14))
        ttk.Label(self, text=label, style="Muted.TLabel",
                  background=Theme.CARD_BG, font=Theme.fonts()["small"]).pack(anchor="w")
        ttk.Label(self, text=value, background=Theme.CARD_BG,
                  font=(Theme.FONT_FAMILY, 18, "bold"), foreground=color).pack(
            anchor="w", pady=(4, 0))
        if hint:
            ttk.Label(self, text=hint, style="Muted.TLabel",
                      background=Theme.CARD_BG,
                      font=Theme.fonts()["small"]).pack(anchor="w")


class DashboardView(BaseView):
    title = "Tableau de bord"
    subtitle = "Vue d’ensemble de l’année scolaire active"

    def refresh(self) -> None:
        for child in self.content.winfo_children():
            child.destroy()
        data: DashboardData = self.services.statistics.dashboard()

        ttk.Label(self.content, text=data.annee_libelle or "Aucune année active",
                  style="Subtitle.TLabel").pack(anchor="w", pady=(0, 10))

        row = ttk.Frame(self.content)
        row.pack(fill=tk.X)
        cards = [
            ("Classes", str(data.nb_classes), "", Theme.ACCENT),
            ("Étudiants inscrits", str(data.nb_etudiants),
             "Dédoublonné par étudiant", Theme.ACCENT),
            ("Formateurs", str(data.nb_formateurs), "", Theme.ACCENT),
            ("Encaissements (année)",
             f"{data.total_encaisse:,.0f} {data.devise}".replace(",", " "),
             "Tous modes confondus", Theme.SUCCESS),
            ("Échéances échues",
             str(data.nb_echeances_echues),
             f"{data.montant_echeances_echues:,.0f} {data.devise} restants".replace(",", " "),
             Theme.WARNING if data.nb_echeances_echues else Theme.SUCCESS),
        ]
        for label, value, hint, color in cards:
            _StatCard(row, label, value, hint, color).pack(
                side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        row.pack_propagate(False)

        alerts = ttk.Frame(self.content, style="Card.TFrame", padding=(16, 12))
        alerts.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        ttk.Label(alerts, text="Alertes absences", style="Subtitle.TLabel",
                  background=Theme.CARD_BG).pack(anchor="w")
        if data.alertes_absences:
            ttk.Label(alerts, style="Muted.TLabel", background=Theme.CARD_BG,
                      text=f"Étudiants au-dessus du seuil "
                           f"({data.seuil_absence:g} heures) :").pack(anchor="w",
                                                                    pady=(4, 6))
            columns = ("matricule", "nom", "heures")
            tree = ttk.Treeview(alerts, columns=columns, show="headings", height=6)
            tree.heading("matricule", text="Matricule")
            tree.heading("nom", text="Étudiant")
            tree.heading("heures", text="Heures d’absence")
            tree.column("matricule", width=140)
            tree.column("nom", width=280)
            tree.column("heures", width=120, anchor="e")
            for matricule, nom, heures in data.alertes_absences[:20]:
                tree.insert("", tk.END, values=(matricule, nom, f"{heures:g} h"))
            tree.pack(fill=tk.BOTH, expand=True)
        else:
            ttk.Label(alerts, style="Muted.TLabel", background=Theme.CARD_BG,
                      text=f"Aucun étudiant au-dessus du seuil d’absences "
                           f"({data.seuil_absence:g} heures).").pack(anchor="w",
                                                                    pady=6)
