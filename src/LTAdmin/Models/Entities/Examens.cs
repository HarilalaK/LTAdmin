namespace LTAdmin.Models.Entities;

// Bloc Examens : SESSION_EXAM, EPREUVE, NOTE_EXAMEN.

/// <summary>Session d'examen (finale, rattrapage…).</summary>
public sealed class SessionExam
{
    public int? IdSession { get; set; }
    public int? IdAnnee { get; set; }
    public string? Libelle { get; set; }
    public string? Nature { get; set; }
    public DateTime? DateDebut { get; set; }
    public DateTime? DateFin { get; set; }
    public bool? Cloturee { get; set; }
}

/// <summary>Épreuve planifiée : session × classe × matière, salle, surveillant.</summary>
public sealed class Epreuve
{
    public int? IdEpreuve { get; set; }
    public int? IdSession { get; set; }
    public int? IdClasse { get; set; }
    public string? CodeMatiere { get; set; }
    public DateTime? DateEpreuve { get; set; }
    public string? HeureDebut { get; set; }
    public int? DureeMn { get; set; }
    public double? Coefficient { get; set; }
    public double? Bareme { get; set; }
    public int? IdSalle { get; set; }
    public string? Surveillant { get; set; }
}

/// <summary>Note d'examen d'un inscrit. Unique (épreuve, inscription).</summary>
public sealed class NoteExamen
{
    public int? IdNoteEx { get; set; }
    public int? IdEpreuve { get; set; }
    public int? IdInscription { get; set; }
    public double? ValeurNote { get; set; }
    public bool? Absent { get; set; }
    public string? CopieNum { get; set; }
    public DateTime? DateSaisie { get; set; }
    public string? CodeUtr { get; set; }
}
