namespace LTAdmin.Models.Entities;

// Bloc Emploi du temps : CRENEAU, EMPLOI_DU_TEMPS (slots hebdomadaires),
// SEANCE (cahier de texte daté), ABSENCE.

/// <summary>Créneau horaire (heures stockées en texte « HH:mm » dans la base).</summary>
public sealed class Creneau
{
    public int? IdCreneau { get; set; }
    public string? Libelle { get; set; }
    public string? HeureDebut { get; set; }
    public string? HeureFin { get; set; }
    public int? OrdreCre { get; set; }
}

/// <summary>Slot hebdomadaire : programme × créneau × jour × salle.</summary>
public sealed class EmploiDuTemps
{
    public int? IdEdt { get; set; }
    public int? IdProg { get; set; }
    public int? IdCreneau { get; set; }
    public string? Jour { get; set; }
    public int? IdSalle { get; set; }
    public DateTime? DateDebut { get; set; }
    public DateTime? DateFin { get; set; }
    public bool? Actif { get; set; }
}

/// <summary>Séance réalisée (cahier de texte) : date, contenu, heures, statut.</summary>
public sealed class Seance
{
    public int? IdSeance { get; set; }
    public int? IdEdt { get; set; }
    public DateTime? DateSeance { get; set; }
    public string? Contenu { get; set; }
    public double? NbHeures { get; set; }
    public string? Statut { get; set; }
    public int? IdFormateurRemp { get; set; }
}

/// <summary>Absence (ou retard) d'un inscrit à une séance.</summary>
public sealed class Absence
{
    public int? IdAbsence { get; set; }
    public int? IdSeance { get; set; }
    public int? IdInscription { get; set; }
    public string? Nature { get; set; }
    public double? NbHeures { get; set; }
    public bool? Justifiee { get; set; }
    public string? Motif { get; set; }
    public DateTime? DateSaisie { get; set; }
}
