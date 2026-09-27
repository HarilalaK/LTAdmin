"""Modules du menu et habilitations par profil (portage de Habilitations.cs)."""

from __future__ import annotations

from typing import List, Optional

from ltadmin.data.schema import Profils


class Modules:
    """Libellés métier du menu (jamais de noms de tables)."""

    TABLEAU_DE_BORD = "Tableau de bord"
    ETUDIANTS = "Étudiants"
    INSCRIPTIONS = "Inscriptions"
    REFERENTIEL = "Référentiel"
    FORMATEURS = "Formateurs"
    NOTES = "Notes et évaluations"
    BULLETINS = "Bulletins"
    EXAMENS = "Examens"
    EMPLOI_DU_TEMPS = "Emploi du temps"
    ABSENCES = "Absences"
    ECOLAGE = "Écolage"
    PAIE = "Paie des formateurs"
    STATISTIQUES = "Statistiques"
    RAPPORTS = "Rapports"
    ADMINISTRATION = "Administration"
    UTILISATEURS = "Profils utilisateurs"
    TABLES = "Tables (maintenance)"


MENU_ORDER = (
    Modules.TABLEAU_DE_BORD,
    Modules.ETUDIANTS,
    Modules.INSCRIPTIONS,
    Modules.REFERENTIEL,
    Modules.FORMATEURS,
    Modules.NOTES,
    Modules.BULLETINS,
    Modules.EXAMENS,
    Modules.EMPLOI_DU_TEMPS,
    Modules.ABSENCES,
    Modules.ECOLAGE,
    Modules.PAIE,
    Modules.STATISTIQUES,
    Modules.RAPPORTS,
    Modules.ADMINISTRATION,
    Modules.UTILISATEURS,
    Modules.TABLES,
)

_DROITS = {
    Profils.ADMINISTRATEUR: None,  # tout
    Profils.DIRECTION: {
        Modules.ETUDIANTS, Modules.INSCRIPTIONS, Modules.REFERENTIEL, Modules.FORMATEURS,
        Modules.NOTES, Modules.BULLETINS, Modules.EXAMENS, Modules.EMPLOI_DU_TEMPS,
        Modules.ABSENCES, Modules.ECOLAGE, Modules.PAIE, Modules.STATISTIQUES,
        Modules.RAPPORTS,
    },
    Profils.SCOLARITE_LIBELLE: {
        Modules.ETUDIANTS, Modules.INSCRIPTIONS, Modules.REFERENTIEL, Modules.FORMATEURS,
        Modules.NOTES, Modules.BULLETINS, Modules.EXAMENS, Modules.EMPLOI_DU_TEMPS,
        Modules.ABSENCES, Modules.STATISTIQUES, Modules.RAPPORTS,
    },
    Profils.COMPTABILITE: {
        Modules.ECOLAGE, Modules.PAIE, Modules.STATISTIQUES, Modules.RAPPORTS,
    },
    Profils.ENSEIGNANT: {
        Modules.NOTES, Modules.BULLETINS, Modules.EXAMENS, Modules.EMPLOI_DU_TEMPS,
        Modules.ABSENCES, Modules.FORMATEURS,
    },
}

PROFILS_CONNUS = (
    Profils.ADMINISTRATEUR,
    Profils.DIRECTION,
    Profils.SCOLARITE_LIBELLE,
    Profils.COMPTABILITE,
    Profils.ENSEIGNANT,
)


def normalize_profil(profil: Optional[str]) -> str:
    """Ramène les libellés de la base aux profils normalisés."""
    p = (profil or "").strip()
    low = p.lower()
    if low in ("admin", "administrateur"):
        return Profils.ADMINISTRATEUR
    if low in ("direction",):
        return Profils.DIRECTION
    if low in ("scolarite", "scolarité"):
        return Profils.SCOLARITE_LIBELLE
    if low in ("finance", "comptabilite", "comptabilité", "caisse"):
        return Profils.COMPTABILITE
    if low in ("enseignant", "formateur"):
        return Profils.ENSEIGNANT
    return p if p.strip() else "Utilisateur"


def can_access(profil: Optional[str], module: str) -> bool:
    """Le profil peut-il ouvrir ce module ? (tableau de bord ouvert à tous)"""
    if module == Modules.TABLEAU_DE_BORD:
        return True
    role = normalize_profil(profil)
    droits = _DROITS.get(role)
    if droits is None and role == Profils.ADMINISTRATEUR:
        return True
    if droits is None:
        return False
    return module in droits
