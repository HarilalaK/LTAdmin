namespace LTAdmin.Models.Entities;

// Bloc Référentiel : FILIERE, NIVEAU, SALLE, CLASSE, MODULE_FORMATION, MATIERE.

/// <summary>Filière (clé naturelle CODE_FILIERE, ex. HOT, TOU).</summary>
public sealed class Filiere
{
    public string? CodeFiliere { get; set; }
    public string? Libelle { get; set; }
    public string? Diplome { get; set; }
    public int? DureeAns { get; set; }
    public bool? Active { get; set; }
}

/// <summary>Niveau de formation (clé naturelle CODE_NIVEAU, ex. BTS1, BTS2).</summary>
public sealed class Niveau
{
    public string? CodeNiveau { get; set; }
    public string? Libelle { get; set; }
    public int? OrdreNiv { get; set; }
}

/// <summary>Salle (cours, informatique, atelier…).</summary>
public sealed class Salle
{
    public int? IdSalle { get; set; }
    public string? NomSalle { get; set; }
    public int? Capacite { get; set; }
    public string? NatureSalle { get; set; }
    public bool? Disponible { get; set; }
}

/// <summary>Classe : année × filière × niveau (+ salle principale).</summary>
public sealed class Classe
{
    public int? IdClasse { get; set; }
    public string? Libelle { get; set; }
    public int? IdAnnee { get; set; }
    public string? CodeFiliere { get; set; }
    public string? CodeNiveau { get; set; }
    public int? IdSalle { get; set; }
    public int? EffectifMax { get; set; }
    public int? IdResponsable { get; set; }
}

/// <summary>Module de formation (filière vide = module transversal).</summary>
public sealed class ModuleFormation
{
    public string? CodeModule { get; set; }
    public string? ModuleLib { get; set; }
    public string? CodeFiliere { get; set; }
}

/// <summary>Matière enseignée (clé naturelle CODE_MATIERE).</summary>
public sealed class Matiere
{
    public string? CodeMatiere { get; set; }
    public string? Libelle { get; set; }
    public string? CodeModule { get; set; }
    public string? Nature { get; set; }
    public int? OrdreMat { get; set; }
}
