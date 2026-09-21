using System.Data;
using System.Data.OleDb;

namespace LTAdmin.Models;

/// <summary>Metadata for one Access table column. The application deliberately uses metadata so it can manage all business tables without a form per table.</summary>
public sealed class DbColumnInfo
{
    public required string Name { get; init; }
    public OleDbType DataType { get; init; } = OleDbType.VarWChar;
    public int Ordinal { get; init; }
    public int Size { get; init; }
    public bool IsNullable { get; init; }
    public bool IsAutoIncrement { get; set; }
    public bool IsPrimaryKey { get; set; }
    public bool IsBinary => DataType is OleDbType.Binary or OleDbType.VarBinary or OleDbType.LongVarBinary;
    public bool IsDate => DataType is OleDbType.Date or OleDbType.DBDate or OleDbType.DBTime or OleDbType.DBTimeStamp;
    public bool IsBoolean => DataType == OleDbType.Boolean;
    public bool IsNumeric => DataType is OleDbType.BigInt or OleDbType.Integer or OleDbType.SmallInt or OleDbType.TinyInt
        or OleDbType.UnsignedBigInt or OleDbType.UnsignedInt or OleDbType.UnsignedSmallInt or OleDbType.UnsignedTinyInt
        or OleDbType.Decimal or OleDbType.Numeric or OleDbType.Currency or OleDbType.Single or OleDbType.Double
        or OleDbType.VarNumeric;
    public bool IsLongText => (DataType is OleDbType.LongVarWChar or OleDbType.LongVarChar or OleDbType.LongVarBinary) || Size > 255;
}

public sealed class DbTableInfo
{
    public required string Name { get; init; }
    public List<DbColumnInfo> Columns { get; } = new();
    public IEnumerable<DbColumnInfo> PrimaryKeyColumns => Columns.Where(c => c.IsPrimaryKey);
    public override string ToString() => Name;
}

public sealed record UserSession(string Login, string DisplayName, string Role);

public sealed record NavigationItem(string Label, string? TableName, string Group, string Description);

public static class DatabaseCatalog
{
    public static readonly IReadOnlyList<NavigationItem> Items = new[]
    {
        new NavigationItem("Tableau de bord", null, "ACCUEIL", "Vue d’ensemble de votre établissement"),
        new NavigationItem("Étudiants", "ETUDIANT", "SCOLARITÉ", "Dossiers et informations des étudiants"),
        new NavigationItem("Inscriptions", "INSCRIPTION", "SCOLARITÉ", "Historique des inscriptions par année"),
        new NavigationItem("Formateurs", "FORMATEUR", "SCOLARITÉ", "Personnel enseignant"),
        new NavigationItem("Filières", "FILIERE", "RÉFÉRENTIEL", "Filières et spécialités"),
        new NavigationItem("Niveaux", "NIVEAU", "RÉFÉRENTIEL", "Niveaux de formation"),
        new NavigationItem("Classes", "CLASSE", "RÉFÉRENTIEL", "Classes et groupes"),
        new NavigationItem("Matières", "MATIERE", "RÉFÉRENTIEL", "Matières enseignées"),
        new NavigationItem("Modules", "MODULE_FORMATION", "RÉFÉRENTIEL", "Modules de formation"),
        new NavigationItem("Salles", "SALLE", "RÉFÉRENTIEL", "Salles et capacités"),
        new NavigationItem("Programmes", "PROGRAMME", "PÉDAGOGIE", "Affectations matière / classe / formateur"),
        new NavigationItem("Périodes", "PERIODE_EVAL", "PÉDAGOGIE", "Périodes d’évaluation"),
        new NavigationItem("Évaluations", "EVALUATION", "PÉDAGOGIE", "Contrôles et évaluations"),
        new NavigationItem("Notes", "NOTE", "PÉDAGOGIE", "Saisie et suivi des notes"),
        new NavigationItem("Emplois du temps", "EMPLOI_DU_TEMPS", "PLANNING", "Planning des classes"),
        new NavigationItem("Créneaux", "CRENEAU", "PLANNING", "Créneaux horaires"),
        new NavigationItem("Séances", "SEANCE", "PLANNING", "Cahier de texte"),
        new NavigationItem("Absences", "ABSENCE", "PLANNING", "Absences et retards"),
        new NavigationItem("Examens", "EPREUVE", "EXAMENS", "Épreuves et sessions"),
        new NavigationItem("Sessions d’examen", "SESSION_EXAM", "EXAMENS", "Sessions d’examen"),
        new NavigationItem("Résultats finaux", "RESULTAT_FINAL", "EXAMENS", "Décisions et résultats"),
        new NavigationItem("Bulletins", "BULLETIN", "BULLETINS", "Bulletins de notes"),
        new NavigationItem("Lignes de bulletin", "BULLETIN_LIGNE", "BULLETINS", "Détail des bulletins"),
        new NavigationItem("Tarifs", "TARIF", "FINANCES", "Tarifs d’écolage"),
        new NavigationItem("Échéanciers", "ECHEANCIER", "FINANCES", "Échéanciers de paiement"),
        new NavigationItem("Paiements", "PAIEMENT", "FINANCES", "Encaissements et reçus"),
        new NavigationItem("Paie formateurs", "PAIE_FORMATEUR", "FINANCES", "Rémunération des formateurs"),
        new NavigationItem("Utilisateurs", "UTILISATEUR", "ADMINISTRATION", "Comptes et droits d’accès"),
        new NavigationItem("Paramètres", "PARAMETRE", "ADMINISTRATION", "Règles de gestion"),
        new NavigationItem("Établissement", "ETABLISSEMENT", "ADMINISTRATION", "Informations de l’établissement"),
        new NavigationItem("Années scolaires", "ANNEE_SCOLAIRE", "ADMINISTRATION", "Années scolaires"),
        new NavigationItem("Journal", "JOURNAL", "ADMINISTRATION", "Traçabilité des opérations"),
    };

    public static readonly string[] PreferredTableOrder =
    {
        "ETUDIANT", "INSCRIPTION", "FORMATEUR", "FILIERE", "NIVEAU", "CLASSE", "MATIERE",
        "MODULE_FORMATION", "SALLE", "PROGRAMME", "PERIODE_EVAL", "EVALUATION", "NOTE",
        "EMPLOI_DU_TEMPS", "CRENEAU", "SEANCE", "ABSENCE", "SESSION_EXAM", "EPREUVE",
        "NOTE_EXAMEN", "RESULTAT_FINAL", "BULLETIN", "BULLETIN_LIGNE", "TARIF", "ECHEANCIER",
        "PAIEMENT", "PAIE_FORMATEUR", "UTILISATEUR", "PARAMETRE", "ETABLISSEMENT", "ANNEE_SCOLAIRE", "JOURNAL"
    };

    public static string DisplayName(string name)
    {
        var item = Items.FirstOrDefault(i => string.Equals(i.TableName, name, StringComparison.OrdinalIgnoreCase));
        return item?.Label ?? name.Replace('_', ' ');
    }
}
