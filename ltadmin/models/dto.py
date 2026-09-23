"""Lignes « à plat » pour les listes et grilles (jointures des dépôts).

Toutes les propriétés sont lues depuis la base : aucune donnée simulée.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


@dataclass
class ClasseDetail:
    """Classe avec libellés de l'année, la filière, le niveau et la salle."""

    id_classe: Optional[int] = None
    libelle: Optional[str] = None
    id_annee: Optional[int] = None
    annee: Optional[str] = None
    code_filiere: Optional[str] = None
    filiere: Optional[str] = None
    code_niveau: Optional[str] = None
    niveau: Optional[str] = None
    id_salle: Optional[int] = None
    salle: Optional[str] = None
    effectif_max: Optional[int] = None
    nb_inscrits: int = 0


@dataclass
class InscriptionDetail:
    """Inscription avec identité de l'étudiant et libellé de la classe."""

    id_inscription: Optional[int] = None
    id_etudiant: Optional[int] = None
    id_classe: Optional[int] = None
    matricule: Optional[str] = None
    nom: Optional[str] = None
    prenom: Optional[str] = None
    classe: Optional[str] = None
    num_inscription: Optional[str] = None
    date_inscription: Optional[_dt.datetime] = None
    redoublant: Optional[bool] = None
    statut: Optional[str] = None
    date_sortie: Optional[_dt.datetime] = None
    motif_sortie: Optional[str] = None

    @property
    def nom_complet(self) -> str:
        return f"{self.nom or ''} {self.prenom or ''}".strip()


@dataclass
class ProgrammeDetail:
    """Programme avec libellés classe / matière / formateur."""

    id_prog: Optional[int] = None
    id_classe: Optional[int] = None
    classe: Optional[str] = None
    code_matiere: Optional[str] = None
    matiere: Optional[str] = None
    id_formateur: Optional[int] = None
    formateur: Optional[str] = None
    coefficient: Optional[float] = None
    vol_horaire: Optional[int] = None
    note_elimin: Optional[float] = None


@dataclass
class EvaluationDetail:
    """Évaluation avec classe, matière, période et barème."""

    id_evaluation: Optional[int] = None
    id_periode: Optional[int] = None
    periode: Optional[str] = None
    id_prog: Optional[int] = None
    id_classe: Optional[int] = None
    classe: Optional[str] = None
    code_matiere: Optional[str] = None
    matiere: Optional[str] = None
    intitule: Optional[str] = None
    nature: Optional[str] = None
    date_eval: Optional[_dt.datetime] = None
    bareme: Optional[float] = None
    poids: Optional[float] = None
    publiee: Optional[bool] = None
    periode_cloturee: Optional[bool] = None


@dataclass
class NoteSaisieRow:
    """Ligne de saisie de notes : un inscrit + sa note éventuelle."""

    id_note: Optional[int] = None
    id_inscription: Optional[int] = None
    matricule: Optional[str] = None
    nom: Optional[str] = None
    prenom: Optional[str] = None
    valeur_note: Optional[float] = None
    absent: bool = False
    observation: Optional[str] = None


@dataclass
class EpreuveDetail:
    """Épreuve avec libellés session / classe / matière / salle."""

    id_epreuve: Optional[int] = None
    id_session: Optional[int] = None
    session: Optional[str] = None
    id_classe: Optional[int] = None
    classe: Optional[str] = None
    code_matiere: Optional[str] = None
    matiere: Optional[str] = None
    date_epreuve: Optional[_dt.datetime] = None
    heure_debut: Optional[str] = None
    duree_mn: Optional[int] = None
    coefficient: Optional[float] = None
    bareme: Optional[float] = None
    id_salle: Optional[int] = None
    salle: Optional[str] = None
    surveillant: Optional[str] = None


@dataclass
class EdtSlotDetail:
    """Slot d'emploi du temps avec classe, matière, formateur, salle et créneau."""

    id_edt: Optional[int] = None
    id_prog: Optional[int] = None
    id_classe: Optional[int] = None
    classe: Optional[str] = None
    code_matiere: Optional[str] = None
    matiere: Optional[str] = None
    id_formateur: Optional[int] = None
    formateur: Optional[str] = None
    id_creneau: Optional[int] = None
    creneau: Optional[str] = None
    heure_debut: Optional[str] = None
    heure_fin: Optional[str] = None
    jour: Optional[str] = None
    id_salle: Optional[int] = None
    salle: Optional[str] = None
    date_debut: Optional[_dt.datetime] = None
    date_fin: Optional[_dt.datetime] = None
    actif: Optional[bool] = None


@dataclass
class SeanceDetail:
    """Séance avec contexte (classe, matière, créneau, jour)."""

    id_seance: Optional[int] = None
    id_edt: Optional[int] = None
    classe: Optional[str] = None
    matiere: Optional[str] = None
    jour: Optional[str] = None
    creneau: Optional[str] = None
    date_seance: Optional[_dt.datetime] = None
    nb_heures: Optional[float] = None
    statut: Optional[str] = None


@dataclass
class EcheanceDetail:
    """Échéance avec tarif, total payé et reste (calculés)."""

    id_echeance: Optional[int] = None
    id_inscription: Optional[int] = None
    id_tarif: Optional[int] = None
    type_frais: Optional[str] = None
    num_tranche: Optional[int] = None
    libelle: Optional[str] = None
    montant_du: Optional[Decimal] = None
    date_echeance: Optional[_dt.datetime] = None
    statut: Optional[str] = None
    remise: Optional[Decimal] = None
    total_paye: Decimal = Decimal("0")
    dernier_paiement: Optional[_dt.datetime] = None

    @property
    def net_du(self) -> Decimal:
        return (self.montant_du or Decimal("0")) - (self.remise or Decimal("0"))

    @property
    def reste(self) -> Decimal:
        return self.net_du - self.total_paye


@dataclass
class SituationEcolageRow:
    """Situation d'écolage d'une inscription (dû / payé / reste)."""

    id_inscription: Optional[int] = None
    matricule: Optional[str] = None
    nom: Optional[str] = None
    prenom: Optional[str] = None
    classe: Optional[str] = None
    total_du: Decimal = Decimal("0")
    total_paye: Decimal = Decimal("0")

    @property
    def reste(self) -> Decimal:
        return self.total_du - self.total_paye


@dataclass
class MoyenneMatiereRow:
    """Moyenne sur 20 par matière et par période (forme de R_MOYENNE_MATIERE)."""

    id_inscription: Optional[int] = None
    id_periode: Optional[int] = None
    id_classe: Optional[int] = None
    code_matiere: Optional[str] = None
    coefficient: Optional[float] = None
    id_formateur: Optional[int] = None
    moyenne_mat: Optional[float] = None


@dataclass
class MoyennePeriodeRow:
    """Moyenne générale pondérée par période (forme de R_MOYENNE_PERIODE)."""

    id_inscription: Optional[int] = None
    id_periode: Optional[int] = None
    id_classe: Optional[int] = None
    total_points: Optional[float] = None
    total_coef: Optional[float] = None
    moyenne: Optional[float] = None


@dataclass
class BulletinResume:
    """Bulletin avec identité de l'étudiant, classe et période."""

    id_bulletin: Optional[int] = None
    id_inscription: Optional[int] = None
    matricule: Optional[str] = None
    nom: Optional[str] = None
    prenom: Optional[str] = None
    classe: Optional[str] = None
    id_periode: Optional[int] = None
    periode: Optional[str] = None
    moyenne: Optional[float] = None
    rang: Optional[int] = None
    effectif: Optional[int] = None
    decision: Optional[str] = None


@dataclass
class PaiementCree:
    """Paiement créé : identifiant, reçu et nouveau statut de l'échéance."""

    id_paiement: int = 0
    num_recu: str = ""
    nouveau_statut: str = ""


@dataclass
class BackupInfo:
    """Informations d'une sauvegarde de la base."""

    file_path: str = ""
    file_name: str = ""
    created_at: Optional[_dt.datetime] = None
    size_bytes: int = 0
