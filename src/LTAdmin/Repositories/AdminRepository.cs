using System.Data;
using LTAdmin.Data;
using LTAdmin.Models.Entities;

namespace LTAdmin.Repositories;

/// <summary>Dépôt du bloc Administration (utilisateurs, paramètres, établissement, années, journal).</summary>
public sealed class AdminRepository : RepositoryBase
{
    public AdminRepository(AccessDatabase database) : base(database)
    {
    }

    // ----- UTILISATEUR -----

    public Utilisateur? GetUtilisateur(string codeUtr)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.Utilisateur)} WHERE {Q("CODE_UTR")} = ?",
            MapUtilisateur, P(codeUtr));

    public List<Utilisateur> ListUtilisateurs()
        => QueryList(
            $"SELECT * FROM {Q(Tables.Utilisateur)} ORDER BY {Q("CODE_UTR")}",
            MapUtilisateur);

    public void InsertUtilisateur(Utilisateur user)
    {
        Execute(
            $"INSERT INTO {Q(Tables.Utilisateur)} ({Q("CODE_UTR")}, {Q("NOM_UTR")}, {Q("MOT_PASSE")}, {Q("PROFIL")}, {Q("ACTIF")}) VALUES (?, ?, ?, ?, ?)",
            P(user.CodeUtr), P(user.NomUtr), P(user.MotPasse), P(user.Profil), P(user.Actif ?? true));
    }

    public int UpdateUtilisateur(Utilisateur user)
        => Execute(
            $"UPDATE {Q(Tables.Utilisateur)} SET {Q("NOM_UTR")} = ?, {Q("PROFIL")} = ?, {Q("ACTIF")} = ? WHERE {Q("CODE_UTR")} = ?",
            P(user.NomUtr), P(user.Profil), P(user.Actif ?? true), P(user.CodeUtr));

    public int UpdateMotPasse(string codeUtr, string nouveauMotPasse)
        => Execute(
            $"UPDATE {Q(Tables.Utilisateur)} SET {Q("MOT_PASSE")} = ? WHERE {Q("CODE_UTR")} = ?",
            P(nouveauMotPasse), P(codeUtr));

    public int SetUtilisateurActif(string codeUtr, bool actif)
        => Execute(
            $"UPDATE {Q(Tables.Utilisateur)} SET {Q("ACTIF")} = ? WHERE {Q("CODE_UTR")} = ?",
            P(actif), P(codeUtr));

    public int DeleteUtilisateur(string codeUtr)
        => Execute(
            $"DELETE FROM {Q(Tables.Utilisateur)} WHERE {Q("CODE_UTR")} = ?",
            P(codeUtr));

    // ----- PARAMETRE -----

    public List<Parametre> ListParametres()
        => QueryList(
            $"SELECT * FROM {Q(Tables.Parametre)} ORDER BY {Q("CLE")}",
            MapParametre);

    public string? GetValeur(string cle)
        => ScalarString(
            $"SELECT {Q("VALEUR")} FROM {Q(Tables.Parametre)} WHERE {Q("CLE")} = ?",
            P(cle));

    public int UpdateValeur(string cle, string valeur)
        => Execute(
            $"UPDATE {Q(Tables.Parametre)} SET {Q("VALEUR")} = ? WHERE {Q("CLE")} = ?",
            P(valeur), P(cle));

    // ----- ETABLISSEMENT -----

    public Etablissement? GetEtablissement()
        => QuerySingle(
            $"SELECT TOP 1 * FROM {Q(Tables.Etablissement)} ORDER BY {Q("CODE_ETAB")}",
            MapEtablissement);

    public int UpdateEtablissement(Etablissement etablissement)
        => Execute(
            $"UPDATE {Q(Tables.Etablissement)} SET {Q("NOM_ETAB")} = ?, {Q("SIGLE")} = ?, {Q("ADRESSE")} = ?, " +
            $"{Q("TEL")} = ?, {Q("EMAIL")} = ?, {Q("SITE_WEB")} = ?, {Q("DIRECTEUR")} = ?, {Q("LOGO")} = ? " +
            $"WHERE {Q("CODE_ETAB")} = ?",
            P(etablissement.NomEtab), P(etablissement.Sigle), P(etablissement.Adresse),
            P(etablissement.Tel), P(etablissement.Email), P(etablissement.SiteWeb),
            P(etablissement.Directeur), P(etablissement.Logo), P(etablissement.CodeEtab));

    // ----- ANNEE_SCOLAIRE -----

    public List<AnneeScolaire> ListAnnees()
        => QueryList(
            $"SELECT * FROM {Q(Tables.AnneeScolaire)} ORDER BY {Q("LIBELLE")} DESC",
            MapAnnee);

    public AnneeScolaire? GetAnnee(int idAnnee)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.AnneeScolaire)} WHERE {Q("ID_ANNEE")} = ?",
            MapAnnee, P(idAnnee));

    public AnneeScolaire? GetAnneeActive()
        => QuerySingle(
            $"SELECT TOP 1 * FROM {Q(Tables.AnneeScolaire)} WHERE {Q("ACTIVE")} = ? ORDER BY {Q("ID_ANNEE")} DESC",
            MapAnnee, P(true));

    public int InsertAnnee(AnneeScolaire annee)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.AnneeScolaire)} ({Q("LIBELLE")}, {Q("DATE_DEBUT")}, {Q("DATE_FIN")}, {Q("ACTIVE")}) VALUES (?, ?, ?, ?)",
            P(annee.Libelle), P(annee.DateDebut), P(annee.DateFin), P(annee.Active ?? false));

    public int UpdateAnnee(AnneeScolaire annee)
        => Execute(
            $"UPDATE {Q(Tables.AnneeScolaire)} SET {Q("LIBELLE")} = ?, {Q("DATE_DEBUT")} = ?, {Q("DATE_FIN")} = ?, {Q("ACTIVE")} = ? WHERE {Q("ID_ANNEE")} = ?",
            P(annee.Libelle), P(annee.DateDebut), P(annee.DateFin), P(annee.Active ?? false), P(annee.IdAnnee));

    /// <summary>Active une année et désactive les autres, en transaction.</summary>
    public void SetAnneeActive(int idAnnee)
    {
        using var tx = Db.BeginTransaction();
        Execute($"UPDATE {Q(Tables.AnneeScolaire)} SET {Q("ACTIVE")} = ?", P(false));
        Execute($"UPDATE {Q(Tables.AnneeScolaire)} SET {Q("ACTIVE")} = ? WHERE {Q("ID_ANNEE")} = ?", P(true), P(idAnnee));
        tx.Complete();
    }

    // ----- JOURNAL -----

    public int InsertJournal(JournalEntry entry)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.Journal)} ({Q("DATE_LOG")}, {Q("CODE_UTR")}, {Q("ACTION_LOG")}, {Q("TABLE_CIBLE")}, {Q("ID_CIBLE")}, {Q("DETAIL")}) VALUES (?, ?, ?, ?, ?, ?)",
            P(entry.DateLog ?? DateTime.Now), P(entry.CodeUtr), P(entry.ActionLog),
            P(entry.TableCible), P(entry.IdCible), P(entry.Detail));

    public List<JournalEntry> ListJournal(DateTime? depuis, string? codeUtr, string? action, int maxRows)
    {
        var sql = $"SELECT TOP {Math.Clamp(maxRows, 1, 5000)} * FROM {Q(Tables.Journal)}";
        var conditions = new List<string>();
        var parameters = new List<System.Data.OleDb.OleDbParameter>();
        if (depuis.HasValue) { conditions.Add($"{Q("DATE_LOG")} >= ?"); parameters.Add(P(depuis.Value)); }
        if (!string.IsNullOrWhiteSpace(codeUtr)) { conditions.Add($"{Q("CODE_UTR")} = ?"); parameters.Add(P(codeUtr.Trim())); }
        if (!string.IsNullOrWhiteSpace(action)) { conditions.Add($"{Q("ACTION_LOG")} = ?"); parameters.Add(P(action.Trim())); }
        if (conditions.Count > 0) sql += " WHERE " + string.Join(" AND ", conditions);
        sql += $" ORDER BY {Q("ID_LOG")} DESC";
        return QueryList(sql, MapJournal, parameters.ToArray());
    }

    public int CountJournal() => ScalarInt($"SELECT COUNT(*) FROM {Q(Tables.Journal)}");

    // ----- Mappers -----

    public static Utilisateur MapUtilisateur(DataRow row) => new()
    {
        CodeUtr = DataRowMapper.GetString(row, "CODE_UTR"),
        NomUtr = DataRowMapper.GetString(row, "NOM_UTR"),
        MotPasse = DataRowMapper.GetString(row, "MOT_PASSE"),
        Profil = DataRowMapper.GetString(row, "PROFIL"),
        Actif = DataRowMapper.GetBoolean(row, "ACTIF")
    };

    public static Parametre MapParametre(DataRow row) => new()
    {
        Cle = DataRowMapper.GetString(row, "CLE"),
        Valeur = DataRowMapper.GetString(row, "VALEUR"),
        Description = DataRowMapper.GetString(row, "DESCRIPTION_P")
    };

    public static Etablissement MapEtablissement(DataRow row) => new()
    {
        CodeEtab = DataRowMapper.GetString(row, "CODE_ETAB"),
        NomEtab = DataRowMapper.GetString(row, "NOM_ETAB"),
        Sigle = DataRowMapper.GetString(row, "SIGLE"),
        Adresse = DataRowMapper.GetString(row, "ADRESSE"),
        Tel = DataRowMapper.GetString(row, "TEL"),
        Email = DataRowMapper.GetString(row, "EMAIL"),
        SiteWeb = DataRowMapper.GetString(row, "SITE_WEB"),
        Directeur = DataRowMapper.GetString(row, "DIRECTEUR"),
        Logo = DataRowMapper.GetString(row, "LOGO")
    };

    public static AnneeScolaire MapAnnee(DataRow row) => new()
    {
        IdAnnee = DataRowMapper.GetInt32(row, "ID_ANNEE"),
        Libelle = DataRowMapper.GetString(row, "LIBELLE"),
        DateDebut = DataRowMapper.GetDateTime(row, "DATE_DEBUT"),
        DateFin = DataRowMapper.GetDateTime(row, "DATE_FIN"),
        Active = DataRowMapper.GetBoolean(row, "ACTIVE")
    };

    public static JournalEntry MapJournal(DataRow row) => new()
    {
        IdLog = DataRowMapper.GetInt32(row, "ID_LOG"),
        DateLog = DataRowMapper.GetDateTime(row, "DATE_LOG"),
        CodeUtr = DataRowMapper.GetString(row, "CODE_UTR"),
        ActionLog = DataRowMapper.GetString(row, "ACTION_LOG"),
        TableCible = DataRowMapper.GetString(row, "TABLE_CIBLE"),
        IdCible = DataRowMapper.GetInt32(row, "ID_CIBLE"),
        Detail = DataRowMapper.GetString(row, "DETAIL")
    };
}
