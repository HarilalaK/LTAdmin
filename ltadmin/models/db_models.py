"""Métadonnées de tables, session utilisateur et catalogue de navigation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DbColumnInfo:
    """Une colonne Access : nom, type, taille, contraintes."""

    name: str
    kind: str = "TEXT"  # TEXT, LONG, DOUBLE, CURRENCY, DATETIME, BOOLEAN, MEMO, BINARY, COUNTER
    size: int = 0
    nullable: bool = True
    autonumber: bool = False
    ordinal: int = 0
    is_primary_key: bool = False

    @property
    def is_binary(self) -> bool:
        return self.kind == "BINARY"

    @property
    def is_date(self) -> bool:
        return self.kind == "DATETIME"

    @property
    def is_boolean(self) -> bool:
        return self.kind == "BOOLEAN"

    @property
    def is_numeric(self) -> bool:
        return self.kind in ("LONG", "DOUBLE", "CURRENCY")

    @property
    def is_long_text(self) -> bool:
        return self.kind == "MEMO" or self.size > 255

    @property
    def is_integer(self) -> bool:
        return self.kind == "LONG"

    @property
    def is_decimal(self) -> bool:
        return self.kind in ("CURRENCY", "DOUBLE")


@dataclass
class DbTableInfo:
    """Une table Access et ses colonnes (maintenance générique)."""

    name: str
    columns: List[DbColumnInfo] = field(default_factory=list)

    @property
    def primary_key_columns(self) -> List[DbColumnInfo]:
        return [c for c in self.columns if c.is_primary_key]

    def column(self, name: str) -> Optional[DbColumnInfo]:
        upper = name.upper()
        for candidate in self.columns:
            if candidate.name.upper() == upper:
                return candidate
        return None


@dataclass(frozen=True)
class UserSession:
    """Session utilisateur ouverte après authentification."""

    login: str
    display_name: str
    role: str


@dataclass(frozen=True)
class NavigationItem:
    """Entrée du catalogue de navigation (module ↔ table)."""

    label: str
    table_name: Optional[str]
    group: str
    description: str


NAVIGATION_ITEMS = (
    NavigationItem("Tableau de bord", None, "ACCUEIL", "Vue d’ensemble de votre établissement"),
    NavigationItem("Étudiants", "ETUDIANT", "SCOLARITÉ", "Dossiers et informations des étudiants"),
    NavigationItem("Inscriptions", "INSCRIPTION", "SCOLARITÉ", "Historique des inscriptions par année"),
    NavigationItem("Formateurs", "FORMATEUR", "SCOLARITÉ", "Personnel enseignant"),
    NavigationItem("Filières", "FILIERE", "RÉFÉRENTIEL", "Filières et spécialités"),
    NavigationItem("Niveaux", "NIVEAU", "RÉFÉRENTIEL", "Niveaux de formation"),
    NavigationItem("Classes", "CLASSE", "RÉFÉRENTIEL", "Classes et groupes"),
    NavigationItem("Matières", "MATIERE", "RÉFÉRENTIEL", "Matières enseignées"),
    NavigationItem("Modules", "MODULE_FORMATION", "RÉFÉRENTIEL", "Modules de formation"),
    NavigationItem("Salles", "SALLE", "RÉFÉRENTIEL", "Salles et capacités"),
    NavigationItem("Programmes", "PROGRAMME", "PÉDAGOGIE", "Affectations matière / classe / formateur"),
    NavigationItem("Périodes", "PERIODE_EVAL", "PÉDAGOGIE", "Périodes d’évaluation"),
    NavigationItem("Évaluations", "EVALUATION", "PÉDAGOGIE", "Contrôles et évaluations"),
    NavigationItem("Notes", "NOTE", "PÉDAGOGIE", "Saisie et suivi des notes"),
    NavigationItem("Emplois du temps", "EMPLOI_DU_TEMPS", "PLANNING", "Planning des classes"),
    NavigationItem("Créneaux", "CRENEAU", "PLANNING", "Créneaux horaires"),
    NavigationItem("Séances", "SEANCE", "PLANNING", "Cahier de texte"),
    NavigationItem("Absences", "ABSENCE", "PLANNING", "Absences et retards"),
    NavigationItem("Examens", "EPREUVE", "EXAMENS", "Épreuves et sessions"),
    NavigationItem("Sessions d’examen", "SESSION_EXAM", "EXAMENS", "Sessions d’examen"),
    NavigationItem("Résultats finaux", "RESULTAT_FINAL", "EXAMENS", "Décisions et résultats"),
    NavigationItem("Bulletins", "BULLETIN", "BULLETINS", "Bulletins de notes"),
    NavigationItem("Lignes de bulletin", "BULLETIN_LIGNE", "BULLETINS", "Détail des bulletins"),
    NavigationItem("Tarifs", "TARIF", "FINANCES", "Tarifs d’écolage"),
    NavigationItem("Échéanciers", "ECHEANCIER", "FINANCES", "Échéanciers de paiement"),
    NavigationItem("Paiements", "PAIEMENT", "FINANCES", "Encaissements et reçus"),
    NavigationItem("Paie formateurs", "PAIE_FORMATEUR", "FINANCES", "Rémunération des formateurs"),
    NavigationItem("Utilisateurs", "UTILISATEUR", "ADMINISTRATION", "Comptes et droits d’accès"),
    NavigationItem("Paramètres", "PARAMETRE", "ADMINISTRATION", "Règles de gestion"),
    NavigationItem("Établissement", "ETABLISSEMENT", "ADMINISTRATION", "Informations de l’établissement"),
    NavigationItem("Années scolaires", "ANNEE_SCOLAIRE", "ADMINISTRATION", "Années scolaires"),
    NavigationItem("Journal", "JOURNAL", "ADMINISTRATION", "Traçabilité des opérations"),
)


def display_name(name: str) -> str:
    """Libellé métier d'une table pour la navigation et la maintenance."""
    for item in NAVIGATION_ITEMS:
        if item.table_name and item.table_name.upper() == name.upper():
            return item.label
    return name.replace("_", " ")
