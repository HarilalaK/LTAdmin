namespace LTAdmin.Services.Statistics;

// Objets de statistiques : tous calculés depuis la base, sans données simulées.

/// <summary>Effectif d'une classe et taux de remplissage.</summary>
public sealed class EffectifClasseStat
{
    public int? IdClasse { get; set; }
    public string? Classe { get; set; }
    public string? Filiere { get; set; }
    public string? Niveau { get; set; }
    public int Inscrits { get; set; }
    public int? EffectifMax { get; set; }
    public double? TauxRemplissage { get; set; }
}

/// <summary>Répartition simple (libellé → nombre).</summary>
public sealed class RepartitionStat
{
    public string Libelle { get; set; } = string.Empty;
    public int Nombre { get; set; }
}

/// <summary>Avancement de la saisie des notes pour une évaluation.</summary>
public sealed class AvancementSaisieStat
{
    public int? IdEvaluation { get; set; }
    public string? Intitule { get; set; }
    public string? Matiere { get; set; }
    public string? Classe { get; set; }
    public int Attendues { get; set; }
    public int Saisies { get; set; }
    public double Taux => Attendues == 0 ? 100d : Math.Round(Saisies * 100d / Attendues, 1);
}

/// <summary>Recouvrement global : montants bruts, remises, payé, reste.</summary>
public sealed class RecouvrementStat
{
    public decimal TotalDuBrut { get; set; }
    public decimal TotalRemise { get; set; }
    public decimal TotalPaye { get; set; }
    public decimal NetDu => TotalDuBrut - TotalRemise;
    public decimal Reste => NetDu - TotalPaye;
    public double Taux => NetDu <= 0 ? 100d : Math.Round((double)(TotalPaye * 100m / NetDu), 1);
}

/// <summary>Recouvrement par classe.</summary>
public sealed class RecouvrementClasseStat
{
    public string? Classe { get; set; }
    public decimal TotalDu { get; set; }
    public decimal TotalPaye { get; set; }
    public decimal Reste => TotalDu - TotalPaye;
    public double Taux => TotalDu <= 0 ? 100d : Math.Round((double)(TotalPaye * 100m / TotalDu), 1);
}

/// <summary>Encaissements par mode de paiement.</summary>
public sealed class EncaissementModeStat
{
    public string? Mode { get; set; }
    public int Nombre { get; set; }
    public decimal Total { get; set; }
}

/// <summary>Échéance échue non soldée.</summary>
public sealed class EcheanceRetardStat
{
    public int? IdEcheance { get; set; }
    public string? Matricule { get; set; }
    public string? Nom { get; set; }
    public string? Prenom { get; set; }
    public string? Classe { get; set; }
    public string? Libelle { get; set; }
    public decimal Reste { get; set; }
    public DateTime? DateEcheance { get; set; }
    public int JoursRetard { get; set; }
}

/// <summary>Absentéisme cumulé d'une classe.</summary>
public sealed class AbsenteismeClasseStat
{
    public string? Classe { get; set; }
    public double HeuresAbsence { get; set; }
    public double HeuresJustifiees { get; set; }
    public int NbConcernes { get; set; }
}

/// <summary>Étudiant au-delà du seuil d'absence.</summary>
public sealed class EtudiantSeuilStat
{
    public string? Matricule { get; set; }
    public string? Nom { get; set; }
    public string? Prenom { get; set; }
    public string? Classe { get; set; }
    public double TotalHeures { get; set; }
}

/// <summary>Répartition des mentions d'une classe pour une période.</summary>
public sealed class MentionStat
{
    public string? Mention { get; set; }
    public bool Admis { get; set; }
    public int Nombre { get; set; }
}

/// <summary>Résumé des moyennes d'une classe pour une période.</summary>
public sealed class ClasseResultatStat
{
    public int Effectif { get; set; }
    public int AvecMoyenne { get; set; }
    public double? Moyenne { get; set; }
    public double? Min { get; set; }
    public double? Max { get; set; }
}

/// <summary>Indicateurs du tableau de bord.</summary>
public sealed class DashboardStat
{
    public string? AnneeLibelle { get; set; }
    public int NbEtudiants { get; set; }
    public int NbFormateurs { get; set; }
    public int NbInscriptions { get; set; }
    public int NbClasses { get; set; }
    public decimal TotalDu { get; set; }
    public decimal TotalPaye { get; set; }
    public decimal Reste => TotalDu - TotalPaye;
    public double TauxRecouvrement => TotalDu <= 0 ? 100d : Math.Round((double)(TotalPaye * 100m / TotalDu), 1);
    public int NbEcheancesEchues { get; set; }
    public int NbAlertesAbsence { get; set; }
}
