namespace LTAdmin.Models.Entities;

// Bloc Évaluations (contrôle continu) : PERIODE_EVAL, EVALUATION, NOTE.
// Chaque évaluation a son BAREME et son POIDS : un devoir /40 coef 2 peut
// se mélanger avec une interro /10 (normalisation sur 20, voir R_MOYENNE_MATIERE).

/// <summary>Période d'évaluation dynamique (1ère/2ème éval, rattrapage, examen blanc…).</summary>
public sealed class PeriodeEval
{
    public int? IdPeriode { get; set; }
    public int? IdAnnee { get; set; }
    public string? CodePeriode { get; set; }
    public string? Libelle { get; set; }
    public int? OrdrePer { get; set; }
    public double? Ponderation { get; set; }
    public DateTime? DateDebut { get; set; }
    public DateTime? DateFin { get; set; }
    public bool? Cloturee { get; set; }
}

/// <summary>Devoir, interro ou contrôle rattaché à une période et un programme.</summary>
public sealed class Evaluation
{
    public int? IdEvaluation { get; set; }
    public int? IdPeriode { get; set; }
    public int? IdProg { get; set; }
    public string? Intitule { get; set; }
    public string? Nature { get; set; }
    public DateTime? DateEval { get; set; }
    public double? Bareme { get; set; }
    public double? Poids { get; set; }
    public bool? Publiee { get; set; }
}

/// <summary>Note d'un inscrit à une évaluation. Unique (évaluation, inscription).</summary>
public sealed class Note
{
    public int? IdNote { get; set; }
    public int? IdEvaluation { get; set; }
    public int? IdInscription { get; set; }
    public double? ValeurNote { get; set; }
    public bool? Absent { get; set; }
    public string? Observation { get; set; }
    public DateTime? DateSaisie { get; set; }
    public string? CodeUtr { get; set; }
}
