"""Les 33 entités mappées 1:1 sur le schéma LTA_ADM.accdb.

Types alignés sur Access : TEXT→str, LONG→int, DOUBLE→float,
CURRENCY→Decimal, DATETIME→datetime, BOOLEAN→bool, MEMO→str.
Tous les champs sont optionnels (lecture défensive, colonnes NULL).
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


# --------------------------------------------------------------------------
# Bloc Administration : UTILISATEUR, PARAMETRE, ETABLISSEMENT, ANNEE_SCOLAIRE, JOURNAL
# --------------------------------------------------------------------------


@dataclass
class Utilisateur:
    """Compte de connexion (clé naturelle CODE_UTR, mot de passe en clair dans la base historique)."""

    code_utr: Optional[str] = None
    nom_utr: Optional[str] = None
    mot_passe: Optional[str] = None
    profil: Optional[str] = None
    actif: Optional[bool] = None


@dataclass
class Parametre:
    """Règle de gestion centralisée (clé naturelle CLE, valeur stockée en texte)."""

    cle: Optional[str] = None
    valeur: Optional[str] = None
    description: Optional[str] = None


@dataclass
class Etablissement:
    """Identité de l'établissement (une seule ligne attendue)."""

    code_etab: Optional[str] = None
    nom_etab: Optional[str] = None
    sigle: Optional[str] = None
    adresse: Optional[str] = None
    tel: Optional[str] = None
    email: Optional[str] = None
    site_web: Optional[str] = None
    directeur: Optional[str] = None
    logo: Optional[str] = None


@dataclass
class AnneeScolaire:
    """Année scolaire. Une seule année doit être ACTIVE à la fois."""

    id_annee: Optional[int] = None
    libelle: Optional[str] = None
    date_debut: Optional[_dt.datetime] = None
    date_fin: Optional[_dt.datetime] = None
    active: Optional[bool] = None


@dataclass
class JournalEntry:
    """Trace d'audit (CODE_UTR sans relation : l'historique survit aux comptes)."""

    id_log: Optional[int] = None
    date_log: Optional[_dt.datetime] = None
    code_utr: Optional[str] = None
    action_log: Optional[str] = None
    table_cible: Optional[str] = None
    id_cible: Optional[int] = None
    detail: Optional[str] = None


# --------------------------------------------------------------------------
# Bloc Référentiel : FILIERE, NIVEAU, SALLE, CLASSE, MODULE_FORMATION, MATIERE
# --------------------------------------------------------------------------


@dataclass
class Filiere:
    code_filiere: Optional[str] = None
    libelle: Optional[str] = None  # colonne FILIERE
    diplome: Optional[str] = None
    duree_ans: Optional[int] = None
    active: Optional[bool] = None


@dataclass
class Niveau:
    code_niveau: Optional[str] = None
    libelle: Optional[str] = None  # colonne NIVEAU
    ordre_niv: Optional[int] = None


@dataclass
class Salle:
    id_salle: Optional[int] = None
    nom_salle: Optional[str] = None
    capacite: Optional[int] = None
    nature_salle: Optional[str] = None
    disponible: Optional[bool] = None


@dataclass
class Classe:
    """Classe : année × filière × niveau (+ salle principale)."""

    id_classe: Optional[int] = None
    libelle: Optional[str] = None
    id_annee: Optional[int] = None
    code_filiere: Optional[str] = None
    code_niveau: Optional[str] = None
    id_salle: Optional[int] = None
    effectif_max: Optional[int] = None
    id_responsable: Optional[int] = None


@dataclass
class ModuleFormation:
    """Module de formation (filière vide = module transversal)."""

    code_module: Optional[str] = None
    module_lib: Optional[str] = None
    code_filiere: Optional[str] = None


@dataclass
class Matiere:
    code_matiere: Optional[str] = None
    libelle: Optional[str] = None  # colonne MATIERE
    code_module: Optional[str] = None
    nature: Optional[str] = None
    ordre_mat: Optional[int] = None


# --------------------------------------------------------------------------
# Bloc Personnel : FORMATEUR, PROGRAMME
# --------------------------------------------------------------------------


@dataclass
class Formateur:
    """Formateur. PHOTO est un chemin (TEXT), pas un binaire."""

    id_formateur: Optional[int] = None
    matricule: Optional[str] = None
    nom: Optional[str] = None
    prenom: Optional[str] = None
    sexe: Optional[str] = None
    date_naissance: Optional[_dt.datetime] = None
    cin: Optional[str] = None
    adresse: Optional[str] = None
    tel: Optional[str] = None
    email: Optional[str] = None
    specialite: Optional[str] = None
    diplome: Optional[str] = None
    contrat: Optional[str] = None
    taux_horaire: Optional[Decimal] = None
    date_embauche: Optional[_dt.datetime] = None
    photo: Optional[str] = None
    actif: Optional[bool] = None

    @property
    def nom_complet(self) -> str:
        return f"{self.nom or ''} {self.prenom or ''}".strip()


@dataclass
class Programme:
    """Affectation pédagogique : matière × classe × formateur × coefficient."""

    id_prog: Optional[int] = None
    id_classe: Optional[int] = None
    code_matiere: Optional[str] = None
    id_formateur: Optional[int] = None
    coefficient: Optional[float] = None
    vol_horaire: Optional[int] = None
    note_elimin: Optional[float] = None
    observation: Optional[str] = None


# --------------------------------------------------------------------------
# Bloc Étudiants : ETUDIANT + INSCRIPTION
# --------------------------------------------------------------------------


@dataclass
class Etudiant:
    """Dossier personne d'un étudiant. MATRICULE unique (IX_ETU_MAT)."""

    id_etudiant: Optional[int] = None
    matricule: Optional[str] = None
    nom: Optional[str] = None
    prenom: Optional[str] = None
    sexe: Optional[str] = None
    date_naissance: Optional[_dt.datetime] = None
    lieu_naissance: Optional[str] = None
    cin: Optional[str] = None
    nationalite: Optional[str] = None
    adresse: Optional[str] = None
    tel: Optional[str] = None
    email: Optional[str] = None
    nom_tuteur: Optional[str] = None
    tel_tuteur: Optional[str] = None
    profession_tuteur: Optional[str] = None
    serie_bacc: Optional[str] = None
    annee_bacc: Optional[int] = None
    etab_origine: Optional[str] = None
    photo: Optional[str] = None
    date_creation: Optional[_dt.datetime] = None
    statut: Optional[str] = None

    @property
    def nom_complet(self) -> str:
        return f"{self.nom or ''} {self.prenom or ''}".strip()


@dataclass
class Inscription:
    """Inscription d'un étudiant dans une classe. Unique (étudiant, classe)."""

    id_inscription: Optional[int] = None
    id_etudiant: Optional[int] = None
    id_classe: Optional[int] = None
    num_inscription: Optional[str] = None
    date_inscription: Optional[_dt.datetime] = None
    redoublant: Optional[bool] = None
    statut: Optional[str] = None
    date_sortie: Optional[_dt.datetime] = None
    motif_sortie: Optional[str] = None


# --------------------------------------------------------------------------
# Bloc Évaluations (contrôle continu) : PERIODE_EVAL, EVALUATION, NOTE
# --------------------------------------------------------------------------


@dataclass
class PeriodeEval:
    """Période d'évaluation dynamique (1ère/2ème éval, rattrapage, examen blanc…)."""

    id_periode: Optional[int] = None
    id_annee: Optional[int] = None
    code_periode: Optional[str] = None
    libelle: Optional[str] = None
    ordre_per: Optional[int] = None
    ponderation: Optional[float] = None
    date_debut: Optional[_dt.datetime] = None
    date_fin: Optional[_dt.datetime] = None
    cloturee: Optional[bool] = None


@dataclass
class Evaluation:
    """Devoir, interro ou contrôle rattaché à une période et un programme."""

    id_evaluation: Optional[int] = None
    id_periode: Optional[int] = None
    id_prog: Optional[int] = None
    intitule: Optional[str] = None
    nature: Optional[str] = None
    date_eval: Optional[_dt.datetime] = None
    bareme: Optional[float] = None
    poids: Optional[float] = None
    publiee: Optional[bool] = None


@dataclass
class Note:
    """Note d'un inscrit à une évaluation. Unique (évaluation, inscription)."""

    id_note: Optional[int] = None
    id_evaluation: Optional[int] = None
    id_inscription: Optional[int] = None
    valeur_note: Optional[float] = None
    absent: Optional[bool] = None
    observation: Optional[str] = None
    date_saisie: Optional[_dt.datetime] = None
    code_utr: Optional[str] = None


# --------------------------------------------------------------------------
# Bloc Examens : SESSION_EXAM, EPREUVE, NOTE_EXAMEN
# --------------------------------------------------------------------------


@dataclass
class SessionExam:
    id_session: Optional[int] = None
    id_annee: Optional[int] = None
    libelle: Optional[str] = None
    nature: Optional[str] = None
    date_debut: Optional[_dt.datetime] = None
    date_fin: Optional[_dt.datetime] = None
    cloturee: Optional[bool] = None


@dataclass
class Epreuve:
    """Épreuve planifiée : session × classe × matière, salle, surveillant."""

    id_epreuve: Optional[int] = None
    id_session: Optional[int] = None
    id_classe: Optional[int] = None
    code_matiere: Optional[str] = None
    date_epreuve: Optional[_dt.datetime] = None
    heure_debut: Optional[str] = None
    duree_mn: Optional[int] = None
    coefficient: Optional[float] = None
    bareme: Optional[float] = None
    id_salle: Optional[int] = None
    surveillant: Optional[str] = None


@dataclass
class NoteExamen:
    """Note d'examen d'un inscrit. Unique (épreuve, inscription)."""

    id_note_ex: Optional[int] = None
    id_epreuve: Optional[int] = None
    id_inscription: Optional[int] = None
    valeur_note: Optional[float] = None
    absent: Optional[bool] = None
    copie_num: Optional[str] = None
    date_saisie: Optional[_dt.datetime] = None
    code_utr: Optional[str] = None


# --------------------------------------------------------------------------
# Bloc Emploi du temps : CRENEAU, EMPLOI_DU_TEMPS, SEANCE, ABSENCE
# --------------------------------------------------------------------------


@dataclass
class Creneau:
    """Créneau horaire (heures stockées en texte « HH:mm » dans la base)."""

    id_creneau: Optional[int] = None
    libelle: Optional[str] = None
    heure_debut: Optional[str] = None
    heure_fin: Optional[str] = None
    ordre_cre: Optional[int] = None


@dataclass
class EmploiDuTemps:
    """Slot hebdomadaire : programme × créneau × jour × salle."""

    id_edt: Optional[int] = None
    id_prog: Optional[int] = None
    id_creneau: Optional[int] = None
    jour: Optional[str] = None
    id_salle: Optional[int] = None
    date_debut: Optional[_dt.datetime] = None
    date_fin: Optional[_dt.datetime] = None
    actif: Optional[bool] = None


@dataclass
class Seance:
    """Séance réalisée (cahier de texte) : date, contenu, heures, statut."""

    id_seance: Optional[int] = None
    id_edt: Optional[int] = None
    date_seance: Optional[_dt.datetime] = None
    contenu: Optional[str] = None
    nb_heures: Optional[float] = None
    statut: Optional[str] = None
    id_formateur_remp: Optional[int] = None


@dataclass
class Absence:
    """Absence (ou retard) d'un inscrit à une séance."""

    id_absence: Optional[int] = None
    id_seance: Optional[int] = None
    id_inscription: Optional[int] = None
    nature: Optional[str] = None
    nb_heures: Optional[float] = None
    justifiee: Optional[bool] = None
    motif: Optional[str] = None
    date_saisie: Optional[_dt.datetime] = None


# --------------------------------------------------------------------------
# Bloc Bulletins / résultats : BULLETIN, BULLETIN_LIGNE, GRILLE_MENTION, RESULTAT_FINAL
# --------------------------------------------------------------------------


@dataclass
class Bulletin:
    """Bulletin d'un inscrit pour une période. Unique (inscription, période)."""

    id_bulletin: Optional[int] = None
    id_inscription: Optional[int] = None
    id_periode: Optional[int] = None
    moyenne: Optional[float] = None
    total_points: Optional[float] = None
    total_coef: Optional[float] = None
    rang: Optional[int] = None
    effectif: Optional[int] = None
    moy_classe: Optional[float] = None
    nb_absence: Optional[float] = None
    appreciation: Optional[str] = None
    decision: Optional[str] = None
    date_edition: Optional[_dt.datetime] = None


@dataclass
class BulletinLigne:
    """Ligne matière d'un bulletin (moyenne, coef, points, min/max, rang)."""

    id_ligne: Optional[int] = None
    id_bulletin: Optional[int] = None
    code_matiere: Optional[str] = None
    moyenne_mat: Optional[float] = None
    coefficient: Optional[float] = None
    points: Optional[float] = None
    rang_mat: Optional[int] = None
    moy_min: Optional[float] = None
    moy_max: Optional[float] = None
    appreciation: Optional[str] = None
    id_formateur: Optional[int] = None


@dataclass
class GrilleMention:
    """Barème des mentions (intervalles [INF, SUP[ sauf maximum inclus)."""

    id_mention: Optional[int] = None
    inf: Optional[float] = None
    sup: Optional[float] = None
    mention: Optional[str] = None
    admis: Optional[bool] = None


@dataclass
class ResultatFinal:
    """Résultat final d'un inscrit (moyenne CC + examen, mention, décision).

    Le schéma ne porte pas de colonne session : une seule ligne de résultat
    par inscription (règle d'idempotence dans ExamService).
    """

    id_resultat: Optional[int] = None
    id_inscription: Optional[int] = None
    moy_cc: Optional[float] = None
    moy_exam: Optional[float] = None
    moyenne_gen: Optional[float] = None
    rang: Optional[int] = None
    mention: Optional[str] = None
    decision: Optional[str] = None
    credit_valide: Optional[int] = None
    date_delib: Optional[_dt.datetime] = None
    observation: Optional[str] = None


# --------------------------------------------------------------------------
# Bloc Écolage & paie : TARIF, ECHEANCIER, PAIEMENT, PAIE_FORMATEUR
# --------------------------------------------------------------------------


@dataclass
class Tarif:
    """Tarif de frais pour une classe, découpé en tranches."""

    id_tarif: Optional[int] = None
    id_classe: Optional[int] = None
    type_frais: Optional[str] = None
    montant: Optional[Decimal] = None
    nb_tranches: Optional[int] = None
    obligatoire: Optional[bool] = None
    observation: Optional[str] = None


@dataclass
class Echeancier:
    """Tranche d'échéancier d'une inscription. STATUT : DU / PARTIEL / SOLDE."""

    id_echeance: Optional[int] = None
    id_inscription: Optional[int] = None
    id_tarif: Optional[int] = None
    num_tranche: Optional[int] = None
    libelle: Optional[str] = None
    montant_du: Optional[Decimal] = None
    date_echeance: Optional[_dt.datetime] = None
    statut: Optional[str] = None
    remise: Optional[Decimal] = None


@dataclass
class Paiement:
    """Encaissement sur une échéance. NUM_RECU unique (IX_PAI_RECU)."""

    id_paiement: Optional[int] = None
    id_echeance: Optional[int] = None
    num_recu: Optional[str] = None
    date_paiement: Optional[_dt.datetime] = None
    montant: Optional[Decimal] = None
    mode_paie: Optional[str] = None
    ref_externe: Optional[str] = None
    code_utr: Optional[str] = None
    observation: Optional[str] = None


@dataclass
class PaieFormateur:
    """Paie d'un formateur : heures réalisées × taux horaire."""

    id_paie: Optional[int] = None
    id_formateur: Optional[int] = None
    periode: Optional[str] = None
    nb_heures: Optional[float] = None
    taux: Optional[Decimal] = None
    montant: Optional[Decimal] = None
    paye: Optional[bool] = None
    date_paie: Optional[_dt.datetime] = None
    observation: Optional[str] = None
