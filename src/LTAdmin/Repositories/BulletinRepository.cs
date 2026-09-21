using System.Data;
using LTAdmin.Data;
using LTAdmin.Models.Dto;
using LTAdmin.Models.Entities;

namespace LTAdmin.Repositories;

/// <summary>Dépôt des bulletins, lignes, mentions et résultats finaux.</summary>
public sealed class BulletinRepository : RepositoryBase
{
    public BulletinRepository(AccessDatabase database) : base(database)
    {
    }

    // ----- BULLETIN -----

    public Bulletin? GetByInscriptionPeriode(int idInscription, int idPeriode)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.Bulletin)} WHERE {Q("ID_INSCRIPTION")} = ? AND {Q("ID_PERIODE")} = ?",
            MapBulletin, P(idInscription), P(idPeriode));

    public List<Bulletin> ListByClassePeriode(int idClasse, int idPeriode)
        => QueryList(
            $"SELECT B.* FROM {Q(Tables.Bulletin)} AS B " +
            $"INNER JOIN {Q(Tables.Inscription)} AS I ON B.{Q("ID_INSCRIPTION")} = I.{Q("ID_INSCRIPTION")} " +
            $"WHERE I.{Q("ID_CLASSE")} = ? AND B.{Q("ID_PERIODE")} = ? ORDER BY B.{Q("RANG")}",
            MapBulletin, P(idClasse), P(idPeriode));

    public List<BulletinResume> ListResumes(int? idClasse = null, int? idPeriode = null)
    {
        var conditions = new List<string>();
        var parameters = new List<System.Data.OleDb.OleDbParameter>();
        if (idClasse.HasValue) { conditions.Add($"I.{Q("ID_CLASSE")} = ?"); parameters.Add(P(idClasse.Value)); }
        if (idPeriode.HasValue) { conditions.Add($"B.{Q("ID_PERIODE")} = ?"); parameters.Add(P(idPeriode.Value)); }
        var sql = BulletinResumeSql();
        if (conditions.Count > 0) sql += " WHERE " + string.Join(" AND ", conditions);
        sql += $" ORDER BY C.{Q("LIBELLE")}, B.{Q("RANG")}";
        return QueryList(sql, MapBulletinResume, parameters.ToArray());
    }

    private static string BulletinResumeSql()
        => $"SELECT B.*, E.{Q("MATRICULE")}, E.{Q("NOM")}, E.{Q("PRENOM")}, " +
           $"C.{Q("LIBELLE")} AS CLASSE_LIB, PE.{Q("LIBELLE")} AS PERIODE_LIB " +
           $"FROM (((({Q(Tables.Bulletin)} AS B " +
           $"INNER JOIN {Q(Tables.Inscription)} AS I ON B.{Q("ID_INSCRIPTION")} = I.{Q("ID_INSCRIPTION")}) " +
           $"INNER JOIN {Q(Tables.Etudiant)} AS E ON I.{Q("ID_ETUDIANT")} = E.{Q("ID_ETUDIANT")}) " +
           $"INNER JOIN {Q(Tables.Classe)} AS C ON I.{Q("ID_CLASSE")} = C.{Q("ID_CLASSE")}) " +
           $"INNER JOIN {Q(Tables.PeriodeEval)} AS PE ON B.{Q("ID_PERIODE")} = PE.{Q("ID_PERIODE")})";

    public List<double> ListMoyennesByInscription(int idInscription)
    {
        var table = QueryTable(
            $"SELECT {Q("MOYENNE")} FROM {Q(Tables.Bulletin)} WHERE {Q("ID_INSCRIPTION")} = ? AND {Q("MOYENNE")} IS NOT NULL",
            P(idInscription));
        var result = new List<double>(table.Rows.Count);
        foreach (DataRow row in table.Rows)
        {
            var value = DataRowMapper.GetDouble(row, "MOYENNE");
            if (value.HasValue) result.Add(value.Value);
        }
        return result;
    }

    public int InsertBulletin(Bulletin bulletin)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.Bulletin)} ({Q("ID_INSCRIPTION")}, {Q("ID_PERIODE")}, {Q("MOYENNE")}, " +
            $"{Q("TOTAL_POINTS")}, {Q("TOTAL_COEF")}, {Q("RANG")}, {Q("EFFECTIF")}, {Q("MOY_CLASSE")}, " +
            $"{Q("NB_ABSENCE")}, {Q("APPRECIATION")}, {Q("DECISION")}, {Q("DATE_EDITION")}) " +
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            P(bulletin.IdInscription), P(bulletin.IdPeriode), P(bulletin.Moyenne),
            P(bulletin.TotalPoints), P(bulletin.TotalCoef), P(bulletin.Rang), P(bulletin.Effectif),
            P(bulletin.MoyClasse), P(bulletin.NbAbsence), P(bulletin.Appreciation),
            P(bulletin.Decision), P(bulletin.DateEdition));

    public int UpdateRang(Bulletin bulletin)
        => Execute(
            $"UPDATE {Q(Tables.Bulletin)} SET {Q("RANG")} = ?, {Q("EFFECTIF")} = ?, {Q("MOY_CLASSE")} = ? WHERE {Q("ID_BULLETIN")} = ?",
            P(bulletin.Rang), P(bulletin.Effectif), P(bulletin.MoyClasse), P(bulletin.IdBulletin));

    /// <summary>Identifiants des bulletins existants pour régénération ciblée.</summary>
    public List<int> ListIdsByClassePeriode(int idClasse, int idPeriode)
    {
        var table = QueryTable(
            $"SELECT B.{Q("ID_BULLETIN")} FROM {Q(Tables.Bulletin)} AS B " +
            $"INNER JOIN {Q(Tables.Inscription)} AS I ON B.{Q("ID_INSCRIPTION")} = I.{Q("ID_INSCRIPTION")} " +
            $"WHERE I.{Q("ID_CLASSE")} = ? AND B.{Q("ID_PERIODE")} = ?",
            P(idClasse), P(idPeriode));
        var result = new List<int>(table.Rows.Count);
        foreach (DataRow row in table.Rows)
        {
            var value = DataRowMapper.GetInt32(row, "ID_BULLETIN");
            if (value.HasValue) result.Add(value.Value);
        }
        return result;
    }

    public int DeleteBulletin(int idBulletin)
        => Execute($"DELETE FROM {Q(Tables.Bulletin)} WHERE {Q("ID_BULLETIN")} = ?", P(idBulletin));

    // ----- BULLETIN_LIGNE -----

    public List<BulletinLigne> ListLignes(int idBulletin)
        => QueryList(
            $"SELECT * FROM {Q(Tables.BulletinLigne)} WHERE {Q("ID_BULLETIN")} = ?",
            MapLigne, P(idBulletin));

    public int InsertLigne(BulletinLigne ligne)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.BulletinLigne)} ({Q("ID_BULLETIN")}, {Q("CODE_MATIERE")}, {Q("MOYENNE_MAT")}, " +
            $"{Q("COEFFICIENT")}, {Q("POINTS")}, {Q("RANG_MAT")}, {Q("MOY_MIN")}, {Q("MOY_MAX")}, " +
            $"{Q("APPRECIATION")}, {Q("ID_FORMATEUR")}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            P(ligne.IdBulletin), P(ligne.CodeMatiere), P(ligne.MoyenneMat),
            P(ligne.Coefficient), P(ligne.Points), P(ligne.RangMat), P(ligne.MoyMin), P(ligne.MoyMax),
            P(ligne.Appreciation), P(ligne.IdFormateur));

    public int UpdateLigneStats(BulletinLigne ligne)
        => Execute(
            $"UPDATE {Q(Tables.BulletinLigne)} SET {Q("RANG_MAT")} = ?, {Q("MOY_MIN")} = ?, {Q("MOY_MAX")} = ? WHERE {Q("ID_LIGNE")} = ?",
            P(ligne.RangMat), P(ligne.MoyMin), P(ligne.MoyMax), P(ligne.IdLigne));

    public int DeleteLignesByBulletin(int idBulletin)
        => Execute($"DELETE FROM {Q(Tables.BulletinLigne)} WHERE {Q("ID_BULLETIN")} = ?", P(idBulletin));

    // ----- GRILLE_MENTION -----

    public List<GrilleMention> ListMentions()
        => QueryList(
            $"SELECT * FROM {Q(Tables.GrilleMention)} ORDER BY {Q("INF")} DESC",
            MapMention);

    // ----- RESULTAT_FINAL -----

    public ResultatFinal? GetByInscription(int idInscription)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.ResultatFinal)} WHERE {Q("ID_INSCRIPTION")} = ?",
            MapResultat, P(idInscription));

    public List<ResultatFinal> ListByClasse(int idClasse)
        => QueryList(
            $"SELECT R.* FROM {Q(Tables.ResultatFinal)} AS R " +
            $"INNER JOIN {Q(Tables.Inscription)} AS I ON R.{Q("ID_INSCRIPTION")} = I.{Q("ID_INSCRIPTION")} " +
            $"WHERE I.{Q("ID_CLASSE")} = ? ORDER BY R.{Q("RANG")}",
            MapResultat, P(idClasse));

    public int InsertResultat(ResultatFinal resultat)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.ResultatFinal)} ({Q("ID_INSCRIPTION")}, {Q("MOY_CC")}, {Q("MOY_EXAM")}, " +
            $"{Q("MOYENNE_GEN")}, {Q("RANG")}, {Q("MENTION")}, {Q("DECISION")}, {Q("CREDIT_VALIDE")}, " +
            $"{Q("DATE_DELIB")}, {Q("OBSERVATION")}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            P(resultat.IdInscription), P(resultat.MoyCc), P(resultat.MoyExam),
            P(resultat.MoyenneGen), P(resultat.Rang), P(resultat.Mention), P(resultat.Decision),
            P(resultat.CreditValide), P(resultat.DateDelib), P(resultat.Observation));

    public int UpdateResultatRang(ResultatFinal resultat)
        => Execute(
            $"UPDATE {Q(Tables.ResultatFinal)} SET {Q("RANG")} = ? WHERE {Q("ID_RESULTAT")} = ?",
            P(resultat.Rang), P(resultat.IdResultat));

    public int DeleteByInscription(int idInscription)
        => Execute($"DELETE FROM {Q(Tables.ResultatFinal)} WHERE {Q("ID_INSCRIPTION")} = ?", P(idInscription));

    // ----- Mappers -----

    public static Bulletin MapBulletin(DataRow row) => new()
    {
        IdBulletin = DataRowMapper.GetInt32(row, "ID_BULLETIN"),
        IdInscription = DataRowMapper.GetInt32(row, "ID_INSCRIPTION"),
        IdPeriode = DataRowMapper.GetInt32(row, "ID_PERIODE"),
        Moyenne = DataRowMapper.GetDouble(row, "MOYENNE"),
        TotalPoints = DataRowMapper.GetDouble(row, "TOTAL_POINTS"),
        TotalCoef = DataRowMapper.GetDouble(row, "TOTAL_COEF"),
        Rang = DataRowMapper.GetInt32(row, "RANG"),
        Effectif = DataRowMapper.GetInt32(row, "EFFECTIF"),
        MoyClasse = DataRowMapper.GetDouble(row, "MOY_CLASSE"),
        NbAbsence = DataRowMapper.GetDouble(row, "NB_ABSENCE"),
        Appreciation = DataRowMapper.GetString(row, "APPRECIATION"),
        Decision = DataRowMapper.GetString(row, "DECISION"),
        DateEdition = DataRowMapper.GetDateTime(row, "DATE_EDITION")
    };

    public static BulletinResume MapBulletinResume(DataRow row) => new()
    {
        IdBulletin = DataRowMapper.GetInt32(row, "ID_BULLETIN"),
        IdInscription = DataRowMapper.GetInt32(row, "ID_INSCRIPTION"),
        Matricule = DataRowMapper.GetString(row, "MATRICULE"),
        Nom = DataRowMapper.GetString(row, "NOM"),
        Prenom = DataRowMapper.GetString(row, "PRENOM"),
        Classe = DataRowMapper.GetString(row, "CLASSE_LIB"),
        IdPeriode = DataRowMapper.GetInt32(row, "ID_PERIODE"),
        Periode = DataRowMapper.GetString(row, "PERIODE_LIB"),
        Moyenne = DataRowMapper.GetDouble(row, "MOYENNE"),
        Rang = DataRowMapper.GetInt32(row, "RANG"),
        Effectif = DataRowMapper.GetInt32(row, "EFFECTIF"),
        Decision = DataRowMapper.GetString(row, "DECISION")
    };

    public static BulletinLigne MapLigne(DataRow row) => new()
    {
        IdLigne = DataRowMapper.GetInt32(row, "ID_LIGNE"),
        IdBulletin = DataRowMapper.GetInt32(row, "ID_BULLETIN"),
        CodeMatiere = DataRowMapper.GetString(row, "CODE_MATIERE"),
        MoyenneMat = DataRowMapper.GetDouble(row, "MOYENNE_MAT"),
        Coefficient = DataRowMapper.GetDouble(row, "COEFFICIENT"),
        Points = DataRowMapper.GetDouble(row, "POINTS"),
        RangMat = DataRowMapper.GetInt32(row, "RANG_MAT"),
        MoyMin = DataRowMapper.GetDouble(row, "MOY_MIN"),
        MoyMax = DataRowMapper.GetDouble(row, "MOY_MAX"),
        Appreciation = DataRowMapper.GetString(row, "APPRECIATION"),
        IdFormateur = DataRowMapper.GetInt32(row, "ID_FORMATEUR")
    };

    public static GrilleMention MapMention(DataRow row) => new()
    {
        IdMention = DataRowMapper.GetInt32(row, "ID_MENTION"),
        Inf = DataRowMapper.GetDouble(row, "INF"),
        Sup = DataRowMapper.GetDouble(row, "SUP"),
        Mention = DataRowMapper.GetString(row, "MENTION"),
        Admis = DataRowMapper.GetBoolean(row, "ADMIS")
    };

    public static ResultatFinal MapResultat(DataRow row) => new()
    {
        IdResultat = DataRowMapper.GetInt32(row, "ID_RESULTAT"),
        IdInscription = DataRowMapper.GetInt32(row, "ID_INSCRIPTION"),
        MoyCc = DataRowMapper.GetDouble(row, "MOY_CC"),
        MoyExam = DataRowMapper.GetDouble(row, "MOY_EXAM"),
        MoyenneGen = DataRowMapper.GetDouble(row, "MOYENNE_GEN"),
        Rang = DataRowMapper.GetInt32(row, "RANG"),
        Mention = DataRowMapper.GetString(row, "MENTION"),
        Decision = DataRowMapper.GetString(row, "DECISION"),
        CreditValide = DataRowMapper.GetInt32(row, "CREDIT_VALIDE"),
        DateDelib = DataRowMapper.GetDateTime(row, "DATE_DELIB"),
        Observation = DataRowMapper.GetString(row, "OBSERVATION")
    };
}
