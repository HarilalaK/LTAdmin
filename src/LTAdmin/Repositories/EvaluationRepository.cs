using System.Data;
using LTAdmin.Data;
using LTAdmin.Models.Dto;
using LTAdmin.Models.Entities;

namespace LTAdmin.Repositories;

/// <summary>Dépôt des évaluations et des notes de contrôle continu.</summary>
public sealed class EvaluationRepository : RepositoryBase
{
    public EvaluationRepository(AccessDatabase database) : base(database)
    {
    }

    // ----- PERIODE_EVAL -----

    public PeriodeEval? GetPeriode(int idPeriode)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.PeriodeEval)} WHERE {Q("ID_PERIODE")} = ?",
            MapPeriode, P(idPeriode));

    public List<PeriodeEval> ListPeriodes(int? idAnnee = null)
        => idAnnee.HasValue
            ? QueryList($"SELECT * FROM {Q(Tables.PeriodeEval)} WHERE {Q("ID_ANNEE")} = ? ORDER BY {Q("ORDRE_PER")}", MapPeriode, P(idAnnee.Value))
            : QueryList($"SELECT * FROM {Q(Tables.PeriodeEval)} ORDER BY {Q("ID_ANNEE")}, {Q("ORDRE_PER")}", MapPeriode);

    public int InsertPeriode(PeriodeEval periode)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.PeriodeEval)} ({Q("ID_ANNEE")}, {Q("CODE_PERIODE")}, {Q("LIBELLE")}, {Q("ORDRE_PER")}, " +
            $"{Q("PONDERATION")}, {Q("DATE_DEBUT")}, {Q("DATE_FIN")}, {Q("CLOTUREE")}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            P(periode.IdAnnee), P(periode.CodePeriode), P(periode.Libelle), P(periode.OrdrePer),
            P(periode.Ponderation), P(periode.DateDebut), P(periode.DateFin), P(periode.Cloturee ?? false));

    public int UpdatePeriode(PeriodeEval periode)
        => Execute(
            $"UPDATE {Q(Tables.PeriodeEval)} SET {Q("ID_ANNEE")} = ?, {Q("CODE_PERIODE")} = ?, {Q("LIBELLE")} = ?, {Q("ORDRE_PER")} = ?, " +
            $"{Q("PONDERATION")} = ?, {Q("DATE_DEBUT")} = ?, {Q("DATE_FIN")} = ?, {Q("CLOTUREE")} = ? WHERE {Q("ID_PERIODE")} = ?",
            P(periode.IdAnnee), P(periode.CodePeriode), P(periode.Libelle), P(periode.OrdrePer),
            P(periode.Ponderation), P(periode.DateDebut), P(periode.DateFin), P(periode.Cloturee ?? false),
            P(periode.IdPeriode));

    public int SetPeriodeCloturee(int idPeriode, bool cloturee)
        => Execute(
            $"UPDATE {Q(Tables.PeriodeEval)} SET {Q("CLOTUREE")} = ? WHERE {Q("ID_PERIODE")} = ?",
            P(cloturee), P(idPeriode));

    public int DeletePeriode(int idPeriode)
        => Execute($"DELETE FROM {Q(Tables.PeriodeEval)} WHERE {Q("ID_PERIODE")} = ?", P(idPeriode));

    // ----- EVALUATION -----

    public Evaluation? GetEvaluation(int idEvaluation)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.Evaluation)} WHERE {Q("ID_EVALUATION")} = ?",
            MapEvaluation, P(idEvaluation));

    public EvaluationDetail? GetEvaluationDetail(int idEvaluation)
        => QuerySingle(EvaluationDetailSql() + $" WHERE EV.{Q("ID_EVALUATION")} = ?", MapEvaluationDetail, P(idEvaluation));

    public List<EvaluationDetail> ListEvaluations(int? idPeriode = null, int? idClasse = null, int? idProg = null)
    {
        var conditions = new List<string>();
        var parameters = new List<System.Data.OleDb.OleDbParameter>();
        if (idPeriode.HasValue) { conditions.Add($"EV.{Q("ID_PERIODE")} = ?"); parameters.Add(P(idPeriode.Value)); }
        if (idClasse.HasValue) { conditions.Add($"P.{Q("ID_CLASSE")} = ?"); parameters.Add(P(idClasse.Value)); }
        if (idProg.HasValue) { conditions.Add($"EV.{Q("ID_PROG")} = ?"); parameters.Add(P(idProg.Value)); }
        var sql = EvaluationDetailSql();
        if (conditions.Count > 0) sql += " WHERE " + string.Join(" AND ", conditions);
        sql += $" ORDER BY EV.{Q("DATE_EVAL")}, EV.{Q("ID_EVALUATION")}";
        return QueryList(sql, MapEvaluationDetail, parameters.ToArray());
    }

    private static string EvaluationDetailSql()
        => $"SELECT EV.*, PE.{Q("LIBELLE")} AS PERIODE_LIB, PE.{Q("CLOTUREE")} AS PERIODE_CLOTUREE, " +
           $"P.{Q("ID_CLASSE")} AS ID_CLASSE, C.{Q("LIBELLE")} AS CLASSE_LIB, " +
           $"P.{Q("CODE_MATIERE")} AS CODE_MATIERE, M.{Q("MATIERE")} AS MATIERE_LIB " +
           $"FROM (((({Q(Tables.Evaluation)} AS EV " +
           $"INNER JOIN {Q(Tables.PeriodeEval)} AS PE ON EV.{Q("ID_PERIODE")} = PE.{Q("ID_PERIODE")}) " +
           $"INNER JOIN {Q(Tables.Programme)} AS P ON EV.{Q("ID_PROG")} = P.{Q("ID_PROG")}) " +
           $"INNER JOIN {Q(Tables.Classe)} AS C ON P.{Q("ID_CLASSE")} = C.{Q("ID_CLASSE")}) " +
           $"INNER JOIN {Q(Tables.Matiere)} AS M ON P.{Q("CODE_MATIERE")} = M.{Q("CODE_MATIERE")})";

    public int InsertEvaluation(Evaluation evaluation)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.Evaluation)} ({Q("ID_PERIODE")}, {Q("ID_PROG")}, {Q("INTITULE")}, {Q("NATURE")}, " +
            $"{Q("DATE_EVAL")}, {Q("BAREME")}, {Q("POIDS")}, {Q("PUBLIEE")}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            P(evaluation.IdPeriode), P(evaluation.IdProg), P(evaluation.Intitule), P(evaluation.Nature),
            P(evaluation.DateEval), P(evaluation.Bareme), P(evaluation.Poids), P(evaluation.Publiee ?? false));

    public int UpdateEvaluation(Evaluation evaluation)
        => Execute(
            $"UPDATE {Q(Tables.Evaluation)} SET {Q("ID_PERIODE")} = ?, {Q("ID_PROG")} = ?, {Q("INTITULE")} = ?, {Q("NATURE")} = ?, " +
            $"{Q("DATE_EVAL")} = ?, {Q("BAREME")} = ?, {Q("POIDS")} = ?, {Q("PUBLIEE")} = ? WHERE {Q("ID_EVALUATION")} = ?",
            P(evaluation.IdPeriode), P(evaluation.IdProg), P(evaluation.Intitule), P(evaluation.Nature),
            P(evaluation.DateEval), P(evaluation.Bareme), P(evaluation.Poids), P(evaluation.Publiee ?? false),
            P(evaluation.IdEvaluation));

    public int SetEvaluationPubliee(int idEvaluation, bool publiee)
        => Execute(
            $"UPDATE {Q(Tables.Evaluation)} SET {Q("PUBLIEE")} = ? WHERE {Q("ID_EVALUATION")} = ?",
            P(publiee), P(idEvaluation));

    public int DeleteEvaluation(int idEvaluation)
        => Execute($"DELETE FROM {Q(Tables.Evaluation)} WHERE {Q("ID_EVALUATION")} = ?", P(idEvaluation));

    // ----- NOTE -----

    public Note? GetNote(int idEvaluation, int idInscription)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.Note)} WHERE {Q("ID_EVALUATION")} = ? AND {Q("ID_INSCRIPTION")} = ?",
            MapNote, P(idEvaluation), P(idInscription));

    /// <summary>Grille de saisie : tous les inscrits de la classe + leur note éventuelle.</summary>
    public List<NoteSaisieRow> ListGrilleSaisie(int idEvaluation, int idClasse)
        => QueryList(
            $"SELECT N.{Q("ID_NOTE")}, I.{Q("ID_INSCRIPTION")}, E.{Q("MATRICULE")}, E.{Q("NOM")}, E.{Q("PRENOM")}, " +
            $"N.{Q("VALEUR_NOTE")}, N.{Q("ABSENT")}, N.{Q("OBSERVATION")} " +
            $"FROM (({Q(Tables.Inscription)} AS I " +
            $"INNER JOIN {Q(Tables.Etudiant)} AS E ON I.{Q("ID_ETUDIANT")} = E.{Q("ID_ETUDIANT")}) " +
            $"LEFT JOIN {Q(Tables.Note)} AS N ON N.{Q("ID_INSCRIPTION")} = I.{Q("ID_INSCRIPTION")} AND N.{Q("ID_EVALUATION")} = ?) " +
            $"WHERE I.{Q("ID_CLASSE")} = ? ORDER BY E.{Q("NOM")}, E.{Q("PRENOM")}",
            MapNoteSaisieRow, P(idEvaluation), P(idClasse));

    public int CountNotesByEvaluation(int idEvaluation)
        => ScalarInt($"SELECT COUNT(*) FROM {Q(Tables.Note)} WHERE {Q("ID_EVALUATION")} = ?", P(idEvaluation));

    public int InsertNote(Note note)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.Note)} ({Q("ID_EVALUATION")}, {Q("ID_INSCRIPTION")}, {Q("VALEUR_NOTE")}, " +
            $"{Q("ABSENT")}, {Q("OBSERVATION")}, {Q("DATE_SAISIE")}, {Q("CODE_UTR")}) VALUES (?, ?, ?, ?, ?, ?, ?)",
            P(note.IdEvaluation), P(note.IdInscription), P(note.ValeurNote), P(note.Absent ?? false),
            P(note.Observation), P(note.DateSaisie ?? DateTime.Now), P(note.CodeUtr));

    public int UpdateNote(Note note)
        => Execute(
            $"UPDATE {Q(Tables.Note)} SET {Q("VALEUR_NOTE")} = ?, {Q("ABSENT")} = ?, {Q("OBSERVATION")} = ?, " +
            $"{Q("DATE_SAISIE")} = ?, {Q("CODE_UTR")} = ? WHERE {Q("ID_NOTE")} = ?",
            P(note.ValeurNote), P(note.Absent ?? false), P(note.Observation),
            P(note.DateSaisie ?? DateTime.Now), P(note.CodeUtr), P(note.IdNote));

    public int DeleteNote(int idNote)
        => Execute($"DELETE FROM {Q(Tables.Note)} WHERE {Q("ID_NOTE")} = ?", P(idNote));

    /// <summary>Moyennes sur 20 par matière (requête R_MOYENNE_MATIERE, calcul vérifié).</summary>
    public List<MoyenneMatiereRow> ListMoyennesMatiere(int? idClasse = null, int? idPeriode = null, int? idInscription = null)
    {
        var conditions = new List<string>();
        var parameters = new List<System.Data.OleDb.OleDbParameter>();
        if (idClasse.HasValue) { conditions.Add(Q("ID_CLASSE") + " = ?"); parameters.Add(P(idClasse.Value)); }
        if (idPeriode.HasValue) { conditions.Add(Q("ID_PERIODE") + " = ?"); parameters.Add(P(idPeriode.Value)); }
        if (idInscription.HasValue) { conditions.Add(Q("ID_INSCRIPTION") + " = ?"); parameters.Add(P(idInscription.Value)); }
        var sql = $"SELECT * FROM {Q(SavedQueries.MoyenneMatiere)}";
        if (conditions.Count > 0) sql += " WHERE " + string.Join(" AND ", conditions);
        return QueryList(sql, MapMoyenneMatiere, parameters.ToArray());
    }

    /// <summary>Moyennes générales pondérées par période (requête R_MOYENNE_PERIODE).</summary>
    public List<MoyennePeriodeRow> ListMoyennesPeriode(int? idClasse = null, int? idPeriode = null)
    {
        var conditions = new List<string>();
        var parameters = new List<System.Data.OleDb.OleDbParameter>();
        if (idClasse.HasValue) { conditions.Add(Q("ID_CLASSE") + " = ?"); parameters.Add(P(idClasse.Value)); }
        if (idPeriode.HasValue) { conditions.Add(Q("ID_PERIODE") + " = ?"); parameters.Add(P(idPeriode.Value)); }
        var sql = $"SELECT * FROM {Q(SavedQueries.MoyennePeriode)}";
        if (conditions.Count > 0) sql += " WHERE " + string.Join(" AND ", conditions);
        return QueryList(sql, MapMoyennePeriode, parameters.ToArray());
    }

    // ----- Mappers -----

    public static PeriodeEval MapPeriode(DataRow row) => new()
    {
        IdPeriode = DataRowMapper.GetInt32(row, "ID_PERIODE"),
        IdAnnee = DataRowMapper.GetInt32(row, "ID_ANNEE"),
        CodePeriode = DataRowMapper.GetString(row, "CODE_PERIODE"),
        Libelle = DataRowMapper.GetString(row, "LIBELLE"),
        OrdrePer = DataRowMapper.GetInt32(row, "ORDRE_PER"),
        Ponderation = DataRowMapper.GetDouble(row, "PONDERATION"),
        DateDebut = DataRowMapper.GetDateTime(row, "DATE_DEBUT"),
        DateFin = DataRowMapper.GetDateTime(row, "DATE_FIN"),
        Cloturee = DataRowMapper.GetBoolean(row, "CLOTUREE")
    };

    public static Evaluation MapEvaluation(DataRow row) => new()
    {
        IdEvaluation = DataRowMapper.GetInt32(row, "ID_EVALUATION"),
        IdPeriode = DataRowMapper.GetInt32(row, "ID_PERIODE"),
        IdProg = DataRowMapper.GetInt32(row, "ID_PROG"),
        Intitule = DataRowMapper.GetString(row, "INTITULE"),
        Nature = DataRowMapper.GetString(row, "NATURE"),
        DateEval = DataRowMapper.GetDateTime(row, "DATE_EVAL"),
        Bareme = DataRowMapper.GetDouble(row, "BAREME"),
        Poids = DataRowMapper.GetDouble(row, "POIDS"),
        Publiee = DataRowMapper.GetBoolean(row, "PUBLIEE")
    };

    public static EvaluationDetail MapEvaluationDetail(DataRow row) => new()
    {
        IdEvaluation = DataRowMapper.GetInt32(row, "ID_EVALUATION"),
        IdPeriode = DataRowMapper.GetInt32(row, "ID_PERIODE"),
        Periode = DataRowMapper.GetString(row, "PERIODE_LIB"),
        IdProg = DataRowMapper.GetInt32(row, "ID_PROG"),
        IdClasse = DataRowMapper.GetInt32(row, "ID_CLASSE"),
        Classe = DataRowMapper.GetString(row, "CLASSE_LIB"),
        CodeMatiere = DataRowMapper.GetString(row, "CODE_MATIERE"),
        Matiere = DataRowMapper.GetString(row, "MATIERE_LIB"),
        Intitule = DataRowMapper.GetString(row, "INTITULE"),
        Nature = DataRowMapper.GetString(row, "NATURE"),
        DateEval = DataRowMapper.GetDateTime(row, "DATE_EVAL"),
        Bareme = DataRowMapper.GetDouble(row, "BAREME"),
        Poids = DataRowMapper.GetDouble(row, "POIDS"),
        Publiee = DataRowMapper.GetBoolean(row, "PUBLIEE"),
        PeriodeCloturee = DataRowMapper.GetBoolean(row, "PERIODE_CLOTUREE")
    };

    public static Note MapNote(DataRow row) => new()
    {
        IdNote = DataRowMapper.GetInt32(row, "ID_NOTE"),
        IdEvaluation = DataRowMapper.GetInt32(row, "ID_EVALUATION"),
        IdInscription = DataRowMapper.GetInt32(row, "ID_INSCRIPTION"),
        ValeurNote = DataRowMapper.GetDouble(row, "VALEUR_NOTE"),
        Absent = DataRowMapper.GetBoolean(row, "ABSENT"),
        Observation = DataRowMapper.GetString(row, "OBSERVATION"),
        DateSaisie = DataRowMapper.GetDateTime(row, "DATE_SAISIE"),
        CodeUtr = DataRowMapper.GetString(row, "CODE_UTR")
    };

    public static NoteSaisieRow MapNoteSaisieRow(DataRow row) => new()
    {
        IdNote = DataRowMapper.GetInt32(row, "ID_NOTE"),
        IdInscription = DataRowMapper.GetInt32(row, "ID_INSCRIPTION"),
        Matricule = DataRowMapper.GetString(row, "MATRICULE"),
        Nom = DataRowMapper.GetString(row, "NOM"),
        Prenom = DataRowMapper.GetString(row, "PRENOM"),
        ValeurNote = DataRowMapper.GetDouble(row, "VALEUR_NOTE"),
        Absent = DataRowMapper.GetBoolean(row, "ABSENT", false),
        Observation = DataRowMapper.GetString(row, "OBSERVATION")
    };

    public static MoyenneMatiereRow MapMoyenneMatiere(DataRow row) => new()
    {
        IdInscription = DataRowMapper.GetInt32(row, "ID_INSCRIPTION"),
        IdPeriode = DataRowMapper.GetInt32(row, "ID_PERIODE"),
        IdClasse = DataRowMapper.GetInt32(row, "ID_CLASSE"),
        CodeMatiere = DataRowMapper.GetString(row, "CODE_MATIERE"),
        Coefficient = DataRowMapper.GetDouble(row, "COEFFICIENT"),
        IdFormateur = DataRowMapper.GetInt32(row, "ID_FORMATEUR"),
        MoyenneMat = DataRowMapper.GetDouble(row, "MOYENNE_MAT")
    };

    public static MoyennePeriodeRow MapMoyennePeriode(DataRow row) => new()
    {
        IdInscription = DataRowMapper.GetInt32(row, "ID_INSCRIPTION"),
        IdPeriode = DataRowMapper.GetInt32(row, "ID_PERIODE"),
        IdClasse = DataRowMapper.GetInt32(row, "ID_CLASSE"),
        TotalPoints = DataRowMapper.GetDouble(row, "TOTAL_POINTS"),
        TotalCoef = DataRowMapper.GetDouble(row, "TOTAL_COEF"),
        Moyenne = DataRowMapper.GetDouble(row, "MOYENNE")
    };
}
