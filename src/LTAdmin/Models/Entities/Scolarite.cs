namespace LTAdmin.Models.Entities;

// Bloc Étudiants : ETUDIANT (dossier personne) + INSCRIPTION
// (une ligne par classe : historique et redoublements).

/// <summary>Dossier personne d'un étudiant. MATRICULE unique (IX_ETU_MAT).</summary>
public sealed class Etudiant
{
    public int? IdEtudiant { get; set; }
    public string? Matricule { get; set; }
    public string? Nom { get; set; }
    public string? Prenom { get; set; }
    public string? Sexe { get; set; }
    public DateTime? DateNaissance { get; set; }
    public string? LieuNaissance { get; set; }
    public string? Cin { get; set; }
    public string? Nationalite { get; set; }
    public string? Adresse { get; set; }
    public string? Tel { get; set; }
    public string? Email { get; set; }
    public string? NomTuteur { get; set; }
    public string? TelTuteur { get; set; }
    public string? ProfessionTuteur { get; set; }
    public string? SerieBacc { get; set; }
    public int? AnneeBacc { get; set; }
    public string? EtabOrigine { get; set; }
    public string? Photo { get; set; }
    public DateTime? DateCreation { get; set; }
    public string? Statut { get; set; }

    public string NomComplet => $"{Nom} {Prenom}".Trim();
}

/// <summary>Inscription d'un étudiant dans une classe. Unique (étudiant, classe).</summary>
public sealed class Inscription
{
    public int? IdInscription { get; set; }
    public int? IdEtudiant { get; set; }
    public int? IdClasse { get; set; }
    public string? NumInscription { get; set; }
    public DateTime? DateInscription { get; set; }
    public bool? Redoublant { get; set; }
    public string? Statut { get; set; }
    public DateTime? DateSortie { get; set; }
    public string? MotifSortie { get; set; }
}
