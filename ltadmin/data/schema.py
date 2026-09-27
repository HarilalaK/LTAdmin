"""Noms exacts des tables, requêtes enregistrées et constantes du schéma.

Centralisés ici pour éviter toute faute de frappe dans le SQL des dépôts.
"""

from __future__ import annotations


class Tables:
    """Les 33 tables de LTA_ADM.accdb."""

    UTILISATEUR = "UTILISATEUR"
    PARAMETRE = "PARAMETRE"
    ETABLISSEMENT = "ETABLISSEMENT"
    ANNEE_SCOLAIRE = "ANNEE_SCOLAIRE"
    JOURNAL = "JOURNAL"

    FILIERE = "FILIERE"
    NIVEAU = "NIVEAU"
    SALLE = "SALLE"
    CLASSE = "CLASSE"
    MODULE_FORMATION = "MODULE_FORMATION"
    MATIERE = "MATIERE"

    FORMATEUR = "FORMATEUR"
    PROGRAMME = "PROGRAMME"

    ETUDIANT = "ETUDIANT"
    INSCRIPTION = "INSCRIPTION"

    PERIODE_EVAL = "PERIODE_EVAL"
    EVALUATION = "EVALUATION"
    NOTE = "NOTE"

    SESSION_EXAM = "SESSION_EXAM"
    EPREUVE = "EPREUVE"
    NOTE_EXAMEN = "NOTE_EXAMEN"

    CRENEAU = "CRENEAU"
    EMPLOI_DU_TEMPS = "EMPLOI_DU_TEMPS"
    SEANCE = "SEANCE"
    ABSENCE = "ABSENCE"

    BULLETIN = "BULLETIN"
    BULLETIN_LIGNE = "BULLETIN_LIGNE"
    GRILLE_MENTION = "GRILLE_MENTION"
    RESULTAT_FINAL = "RESULTAT_FINAL"

    TARIF = "TARIF"
    ECHEANCIER = "ECHEANCIER"
    PAIEMENT = "PAIEMENT"
    PAIE_FORMATEUR = "PAIE_FORMATEUR"


class SavedQueries:
    """Les 8 requêtes Access livrées avec la base."""

    LISTE_ETUDIANT = "R_LISTE_ETUDIANT"
    MOYENNE_MATIERE = "R_MOYENNE_MATIERE"
    MOYENNE_PERIODE = "R_MOYENNE_PERIODE"
    BULLETIN_DETAIL = "R_BULLETIN_DETAIL"
    PAIEMENT_ECHEANCE = "R_PAIEMENT_ECHEANCE"
    SITUATION_ECOLAGE = "R_SITUATION_ECOLAGE"
    EDT_CLASSE = "R_EDT_CLASSE"
    ABSENCE_ETUDIANT = "R_ABSENCE_ETUDIANT"


class ParametreKeys:
    """Clés de la table PARAMETRE (règles de gestion centralisées)."""

    BAREME_DEFAUT = "BAREME_DEFAUT"
    MOY_ADMISSION = "MOY_ADMISSION"
    NOTE_ELIMINATOIRE = "NOTE_ELIMINATOIRE"
    POIDS_CC = "POIDS_CC"
    POIDS_EXAMEN = "POIDS_EXAMEN"
    SEUIL_ABSENCE = "SEUIL_ABSENCE"
    DEVISE = "DEVISE"


class Profils:
    """Profils d'habilitation connus (table UTILISATEUR.PROFIL)."""

    ADMIN = "ADMIN"
    ADMINISTRATEUR = "Administrateur"
    DIRECTION = "Direction"
    SCOLARITE = "SCOLARITE"
    SCOLARITE_LIBELLE = "Scolarité"
    FINANCE = "FINANCE"
    COMPTABILITE = "Comptabilité"
    ENSEIGNANT = "Enseignant"


def quote_identifier(identifier: str) -> str:
    """Protège un identifiant Access avec des crochets (mots réservés, espaces)."""
    return "[" + identifier.replace("]", "]]") + "]"
