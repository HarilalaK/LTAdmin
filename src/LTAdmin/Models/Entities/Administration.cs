namespace LTAdmin.Models.Entities;

// Bloc Administration : UTILISATEUR, PARAMETRE, ETABLISSEMENT, ANNEE_SCOLAIRE, JOURNAL.
// Les types correspondent au schéma Access (TEXT -> string?, LONG -> int?,
// DOUBLE -> double?, CURRENCY -> decimal?, DATETIME -> DateTime?, BOOLEAN -> bool?).

/// <summary>Compte de connexion (clé naturelle CODE_UTR, mot de passe en clair dans la base historique).</summary>
public sealed class Utilisateur
{
    public string? CodeUtr { get; set; }
    public string? NomUtr { get; set; }
    public string? MotPasse { get; set; }
    public string? Profil { get; set; }
    public bool? Actif { get; set; }
}

/// <summary>Règle de gestion centralisée (clé naturelle CLE, valeur stockée en texte).</summary>
public sealed class Parametre
{
    public string? Cle { get; set; }
    public string? Valeur { get; set; }
    public string? Description { get; set; }
}

/// <summary>Identité de l'établissement (une seule ligne attendue).</summary>
public sealed class Etablissement
{
    public string? CodeEtab { get; set; }
    public string? NomEtab { get; set; }
    public string? Sigle { get; set; }
    public string? Adresse { get; set; }
    public string? Tel { get; set; }
    public string? Email { get; set; }
    public string? SiteWeb { get; set; }
    public string? Directeur { get; set; }
    public string? Logo { get; set; }
}

/// <summary>Année scolaire. Une seule année doit être ACTIVE à la fois.</summary>
public sealed class AnneeScolaire
{
    public int? IdAnnee { get; set; }
    public string? Libelle { get; set; }
    public DateTime? DateDebut { get; set; }
    public DateTime? DateFin { get; set; }
    public bool? Active { get; set; }
}

/// <summary>Trace d'audit (CODE_UTR sans relation : l'historique survit aux comptes).</summary>
public sealed class JournalEntry
{
    public int? IdLog { get; set; }
    public DateTime? DateLog { get; set; }
    public string? CodeUtr { get; set; }
    public string? ActionLog { get; set; }
    public string? TableCible { get; set; }
    public int? IdCible { get; set; }
    public string? Detail { get; set; }
}
