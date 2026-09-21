namespace LTAdmin.Models.Entities;

// Bloc Bulletins / résultats : BULLETIN, BULLETIN_LIGNE, GRILLE_MENTION, RESULTAT_FINAL.

/// <summary>Bulletin d'un inscrit pour une période. Unique (inscription, période).</summary>
public sealed class Bulletin
{
    public int? IdBulletin { get; set; }
    public int? IdInscription { get; set; }
    public int? IdPeriode { get; set; }
    public double? Moyenne { get; set; }
    public double? TotalPoints { get; set; }
    public double? TotalCoef { get; set; }
    public int? Rang { get; set; }
    public int? Effectif { get; set; }
    public double? MoyClasse { get; set; }
    public double? NbAbsence { get; set; }
    public string? Appreciation { get; set; }
    public string? Decision { get; set; }
    public DateTime? DateEdition { get; set; }
}

/// <summary>Ligne matière d'un bulletin (moyenne, coef, points, min/max, rang).</summary>
public sealed class BulletinLigne
{
    public int? IdLigne { get; set; }
    public int? IdBulletin { get; set; }
    public string? CodeMatiere { get; set; }
    public double? MoyenneMat { get; set; }
    public double? Coefficient { get; set; }
    public double? Points { get; set; }
    public int? RangMat { get; set; }
    public double? MoyMin { get; set; }
    public double? MoyMax { get; set; }
    public string? Appreciation { get; set; }
    public int? IdFormateur { get; set; }
}

/// <summary>Barème des mentions (intervalles [INF, SUP[ sauf maximum inclus).</summary>
public sealed class GrilleMention
{
    public int? IdMention { get; set; }
    public double? Inf { get; set; }
    public double? Sup { get; set; }
    public string? Mention { get; set; }
    public bool? Admis { get; set; }
}

/// <summary>
/// Résultat final d'un inscrit (moyenne CC + examen, mention, décision).
/// Attention : le schéma ne porte pas de colonne session — une seule ligne
/// de résultat par inscription (voir ExamService pour la règle d'idempotence).
/// </summary>
public sealed class ResultatFinal
{
    public int? IdResultat { get; set; }
    public int? IdInscription { get; set; }
    public double? MoyCc { get; set; }
    public double? MoyExam { get; set; }
    public double? MoyenneGen { get; set; }
    public int? Rang { get; set; }
    public string? Mention { get; set; }
    public string? Decision { get; set; }
    public int? CreditValide { get; set; }
    public DateTime? DateDelib { get; set; }
    public string? Observation { get; set; }
}
