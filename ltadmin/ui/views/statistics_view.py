"""Écran Statistiques : indicateurs de pilotage de l'année active."""

from __future__ import annotations

from tkinter import ttk
from typing import Optional

from ltadmin.ui.views.base_view import BaseView
from ltadmin.ui.widgets import DataTable

EFFECTIF_COLUMNS = [
    ("classe", "Classe", 200, "w"),
    ("filiere", "Filière", 200, "w"),
    ("effectif_max", "Effectif max", 100, "center"),
    ("nb_inscrits", "Inscrits", 90, "center"),
    ("remplissage", "Remplissage", 110, "center"),
]

AVANCEMENT_COLUMNS = [
    ("classe", "Classe", 140, "w"),
    ("periode", "Période", 120, "w"),
    ("matiere", "Matière", 160, "w"),
    ("intitule", "Évaluation", 180, "w"),
    ("nb_inscrits", "Inscrits", 80, "center"),
    ("nb_notes", "Notes saisies", 100, "center"),
    ("pourcentage", "Avancement", 110, "center"),
]


class StatisticsView(BaseView):
    title = "Statistiques"
    subtitle = "Effectifs, répartitions, avancement des saisies, encaissements"

    def __init__(self, parent, services, session, **kwargs):
        super().__init__(parent, services, session, **kwargs)
        self._id_annee: Optional[int] = None
        annee = self.services.admin.get_annee_active()
        if annee:
            self._id_annee = annee.id_annee

        self.notebook = ttk.Notebook(self.content)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.effectif_table = DataTable(self.notebook, EFFECTIF_COLUMNS)
        self.notebook.add(self.effectif_table, text="Effectifs par classe")

        self.avancement_table = DataTable(self.notebook, AVANCEMENT_COLUMNS)
        self.notebook.add(self.avancement_table, text="Avancement des saisies")

        self.repartition_table = DataTable(
            self.notebook, [("libelle", "Catégorie", 240, "w"),
                            ("valeur", "Nombre", 120, "center")])
        self.notebook.add(self.repartition_table, text="Répartitions")

        self.encaissement_table = DataTable(
            self.notebook, [("mode_paie", "Mode de paiement", 200, "w"),
                            ("nb_paiements", "Paiements", 110, "center"),
                            ("total", "Total", 160, "e")])
        self.notebook.add(self.encaissement_table, text="Encaissements")

        self.echeance_table = DataTable(
            self.notebook, [("matricule", "Matricule", 110, "w"),
                            ("nom_complet", "Étudiant", 220, "w"),
                            ("classe", "Classe", 150, "w"),
                            ("libelle", "Échéance", 190, "w"),
                            ("date_echeance", "Échéance au", 110, "center"),
                            ("reste", "Reste", 120, "e")])
        self.notebook.add(self.echeance_table, text="Échéances échues")

        self.toolbar.add_label("Indicateurs de l’année scolaire active — "
                               "F5 pour actualiser")

    def refresh(self) -> None:
        annee = self.services.admin.get_annee_active()
        self._id_annee = annee.id_annee if annee else None

        self.effectif_table.set_rows([{
            "classe": r.classe,
            "filiere": r.filiere,
            "effectif_max": r.effectif_max,
            "nb_inscrits": r.nb_inscrits,
            "remplissage": (f"{r.remplissage:.0f} %"
                            if r.remplissage is not None else "—"),
        } for r in self.services.statistics.effectifs_par_classe(self._id_annee)])

        self.avancement_table.set_rows([{
            "classe": r.classe,
            "periode": r.periode,
            "matiere": r.matiere,
            "intitule": r.intitule,
            "nb_inscrits": r.nb_inscrits,
            "nb_notes": r.nb_notes,
            "pourcentage": f"{r.pourcentage:.0f} %",
        } for r in self.services.statistics.avancement_saisie()])

        repartitions = [
            ("Sexe", self.services.statistics.repartition_sexe(self._id_annee)),
            ("Redoublants", self.services.statistics.repartition_redoublants(
                self._id_annee)),
            ("Décisions", self.services.statistics.repartition_resultats(
                self._id_annee)),
            ("Mentions", self.services.statistics.repartition_mentions(
                self._id_annee)),
        ]
        rows = []
        for titre, donnees in repartitions:
            for ligne in donnees:
                libelle = ligne.libelle
                if libelle == "True":
                    libelle = "Oui"
                elif libelle == "False":
                    libelle = "Non"
                rows.append({"libelle": f"{titre} — {libelle}",
                             "valeur": ligne.valeur})
        self.repartition_table.set_rows(rows)

        devise = self.services.parametres.devise
        self.encaissement_table.set_rows([{
            "mode_paie": r.mode_paie,
            "nb_paiements": r.nb_paiements,
            "total": f"{r.total:,.0f} {devise}".replace(",", " "),
        } for r in self.services.statistics.encaissements_par_mode()])

        self.echeance_table.set_rows([{
            "matricule": r.matricule,
            "nom_complet": f"{r.nom} {r.prenom}".strip(),
            "classe": r.classe,
            "libelle": r.libelle,
            "date_echeance": r.date_echeance,
            "reste": r.reste,
        } for r in self.services.statistics.echeances_echues(self._id_annee)])
