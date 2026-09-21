namespace LTAdmin.Models.Dto;

// Lignes « à plat » pour les listes et grilles : chaque DTO correspond à une
// jointure SQL précise réalisée dans un dépôt. Aucune donnée simulée :
// toutes les propriétés sont lues depuis la base.

/// <summary>Classe avec libellés de l'année, la filière, le niveau et la salle.</summary>
public sealed class ClasseDetail
{
    public int? IdClasse { get; set; }
    public string? Libelle { get; set; }
    public int? IdAnnee { get; set; }
    public string? Annee { get; set; }
    public string? CodeFiliere { get; set; }
    public string? Filiere { get; set; }
    public string? CodeNiveau { get; set; }
    public string? Niveau { get; set; }
    public int? IdSalle { get; set; }
    public string? Salle { get; set; }
    public int? EffectifMax { get; set; }
    public int NbInscrits { get; set; }
}

/// <summary>Inscription avec identité de l'étudiant et libellé de la classe.</summary>
public sealed class InscriptionDetail
{
    public int? IdInscription { get; set; }
    public int? IdEtudiant { get; set; }
    public int? IdClasse { get; set; }
    public string? Matricule { get; set; }
    public string? Nom { get; set; }
    public string? Prenom { get; set; }
    public string? Classe { get; set; }
    public string? NumInscription { get; set; }
    public DateTime? DateInscription { get; set; }
    public bool? Redoublant { get; set; }
    public string? Statut { get; set; }
    public DateTime? DateSortie { get; set; }
    public string? MotifSortie { get; set; }

    public string NomComplet => $"{Nom} {Prenom}".Trim();
}

/// <summary>Programme avec libellés classe / matière / formateur.</summary>
public sealed class ProgrammeDetail
{
    public int? IdProg { get; set; }
    public int? IdClasse { get; set; }
    public string? Classe { get; set; }
    public string? CodeMatiere { get; set; }
    public string? Matiere { get; set; }
    public int? IdFormateur { get; set; }
    public string? Formateur { get; set; }
    public double? Coefficient { get; set; }
    public int? VolHoraire { get; set; }
    public double? NoteElimin { get; set; }
}

/// <summary>Évaluation avec classe, matière, période et barème.</summary>
public sealed class EvaluationDetail
{
    public int? IdEvaluation { get; set; }
    public int? IdPeriode { get; set; }
    public string? Periode { get; set; }
    public int? IdProg { get; set; }
    public int? IdClasse { get; set; }
    public string? Classe { get; set; }
    public string? CodeMatiere { get; set; }
    public string? Matiere { get; set; }
    public string? Intitule { get; set; }
    public string? Nature { get; set; }
    public DateTime? DateEval { get; set; }
    public double? Bareme { get; set; }
    public double? Poids { get; set; }
    public bool? Publiee { get; set; }
    public bool? PeriodeCloturee { get; set; }
}

/// <summary>Ligne de saisie de notes : un inscrit + sa note éventuelle.</summary>
public sealed class NoteSaisieRow
{
    public int? IdNote { get; set; }
    public int? IdInscription { get; set; }
    public string? Matricule { get; set; }
    public string? Nom { get; set; }
    public string? Prenom { get; set; }
    public double? ValeurNote { get; set; }
    public bool Absent { get; set; }
    public string? Observation { get; set; }
}

/// <summary>Épreuve avec libellés session / classe / matière / salle.</summary>
public sealed class EpreuveDetail
{
    public int? IdEpreuve { get; set; }
    public int? IdSession { get; set; }
    public string? Session { get; set; }
    public int? IdClasse { get; set; }
    public string? Classe { get; set; }
    public string? CodeMatiere { get; set; }
    public string? Matiere { get; set; }
    public DateTime? DateEpreuve { get; set; }
    public string? HeureDebut { get; set; }
    public int? DureeMn { get; set; }
    public double? Coefficient { get; set; }
    public double? Bareme { get; set; }
    public int? IdSalle { get; set; }
    public string? Salle { get; set; }
    public string? Surveillant { get; set; }
}

/// <summary>Slot d'emploi du temps avec classe, matière, formateur, salle et créneau.</summary>
public sealed class EdtSlotDetail
{
    public int? IdEdt { get; set; }
    public int? IdProg { get; set; }
    public int? IdClasse { get; set; }
    public string? Classe { get; set; }
    public string? CodeMatiere { get; set; }
    public string? Matiere { get; set; }
    public int? IdFormateur { get; set; }
    public string? Formateur { get; set; }
    public int? IdCreneau { get; set; }
    public string? Creneau { get; set; }
    public string? HeureDebut { get; set; }
    public string? HeureFin { get; set; }
    public string? Jour { get; set; }
    public int? IdSalle { get; set; }
    public string? Salle { get; set; }
    public DateTime? DateDebut { get; set; }
    public DateTime? DateFin { get; set; }
    public bool? Actif { get; set; }
}

/// <summary>Séance avec contexte (classe, matière, créneau, jour).</summary>
public sealed class SeanceDetail
{
    public int? IdSeance { get; set; }
    public int? IdEdt { get; set; }
    public string? Classe { get; set; }
    public string? Matiere { get; set; }
    public string? Jour { get; set; }
    public string? Creneau { get; set; }
    public DateTime? DateSeance { get; set; }
    public double? NbHeures { get; set; }
    public string? Statut { get; set; }
}

/// <summary>Échéance avec tarif, total payé et reste (calculés).</summary>
public sealed class EcheanceDetail
{
    public int? IdEcheance { get; set; }
    public int? IdInscription { get; set; }
    public int? IdTarif { get; set; }
    public string? TypeFrais { get; set; }
    public int? NumTranche { get; set; }
    public string? Libelle { get; set; }
    public decimal? MontantDu { get; set; }
    public DateTime? DateEcheance { get; set; }
    public string? Statut { get; set; }
    public decimal? Remise { get; set; }
    public decimal TotalPaye { get; set; }
    public DateTime? DernierPaiement { get; set; }

    public decimal NetDu => (MontantDu ?? 0m) - (Remise ?? 0m);
    public decimal Reste => NetDu - TotalPaye;
}

/// <summary>Situation d'écolage d'une inscription (dû / payé / reste).</summary>
public sealed class SituationEcolageRow
{
    public int? IdInscription { get; set; }
    public string? Matricule { get; set; }
    public string? Nom { get; set; }
    public string? Prenom { get; set; }
    public string? Classe { get; set; }
    public decimal TotalDu { get; set; }
    public decimal TotalPaye { get; set; }
    public decimal Reste => TotalDu - TotalPaye;
}

/// <summary>Moyenne sur 20 par matière et par période (forme de R_MOYENNE_MATIERE).</summary>
public sealed class MoyenneMatiereRow
{
    public int? IdInscription { get; set; }
    public int? IdPeriode { get; set; }
    public int? IdClasse { get; set; }
    public string? CodeMatiere { get; set; }
    public double? Coefficient { get; set; }
    public int? IdFormateur { get; set; }
    public double? MoyenneMat { get; set; }
}

/// <summary>Moyenne générale pondérée par période (forme de R_MOYENNE_PERIODE).</summary>
public sealed class MoyennePeriodeRow
{
    public int? IdInscription { get; set; }
    public int? IdPeriode { get; set; }
    public int? IdClasse { get; set; }
    public double? TotalPoints { get; set; }
    public double? TotalCoef { get; set; }
    public double? Moyenne { get; set; }
}

/// <summary>Bulletin avec identité de l'étudiant, classe et période.</summary>
public sealed class BulletinResume
{
    public int? IdBulletin { get; set; }
    public int? IdInscription { get; set; }
    public string? Matricule { get; set; }
    public string? Nom { get; set; }
    public string? Prenom { get; set; }
    public string? Classe { get; set; }
    public int? IdPeriode { get; set; }
    public string? Periode { get; set; }
    public double? Moyenne { get; set; }
    public int? Rang { get; set; }
    public int? Effectif { get; set; }
    public string? Decision { get; set; }
}

/// <summary>Paiement créé : identifiant, reçu et nouveau statut de l'échéance.</summary>
public sealed class PaiementCree
{
    public int IdPaiement { get; set; }
    public string NumRecu { get; set; } = string.Empty;
    public string NouveauStatut { get; set; } = string.Empty;
}

/// <summary>Informations d'une sauvegarde de la base.</summary>
public sealed class BackupInfo
{
    public string FilePath { get; set; } = string.Empty;
    public string FileName { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; }
    public long SizeBytes { get; set; }
}
