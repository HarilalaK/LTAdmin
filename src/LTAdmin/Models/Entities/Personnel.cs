namespace LTAdmin.Models.Entities;

// Bloc Personnel : FORMATEUR, PROGRAMME (classe × matière × formateur × coefficient).

/// <summary>Formateur. PHOTO et LOGO sont des chemins (TEXT), pas des binaires.</summary>
public sealed class Formateur
{
    public int? IdFormateur { get; set; }
    public string? Matricule { get; set; }
    public string? Nom { get; set; }
    public string? Prenom { get; set; }
    public string? Sexe { get; set; }
    public DateTime? DateNaissance { get; set; }
    public string? Cin { get; set; }
    public string? Adresse { get; set; }
    public string? Tel { get; set; }
    public string? Email { get; set; }
    public string? Specialite { get; set; }
    public string? Diplome { get; set; }
    public string? Contrat { get; set; }
    public decimal? TauxHoraire { get; set; }
    public DateTime? DateEmbauche { get; set; }
    public string? Photo { get; set; }
    public bool? Actif { get; set; }

    public string NomComplet => $"{Nom} {Prenom}".Trim();
}

/// <summary>Affectation pédagogique : une matière dans une classe, un formateur, un coefficient.</summary>
public sealed class Programme
{
    public int? IdProg { get; set; }
    public int? IdClasse { get; set; }
    public string? CodeMatiere { get; set; }
    public int? IdFormateur { get; set; }
    public double? Coefficient { get; set; }
    public int? VolHoraire { get; set; }
    public double? NoteElimin { get; set; }
    public string? Observation { get; set; }
}
