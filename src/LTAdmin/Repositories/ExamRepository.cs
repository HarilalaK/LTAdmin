using System.Data;
using LTAdmin.Data;
using LTAdmin.Models.Dto;
using LTAdmin.Models.Entities;

namespace LTAdmin.Repositories;

/// <summary>Dépôt des examens : sessions, épreuves, notes d'examen.</summary>
public sealed class ExamRepository : RepositoryBase
{
    public ExamRepository(AccessDatabase database) : base(database)
    {
    }

    // ----- SESSION_EXAM -----

    public SessionExam? GetSession(int idSession)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.SessionExam)} WHERE {Q("ID_SESSION")} = ?",
            MapSession, P(idSession));

    public List<SessionExam> ListSessions(int? idAnnee = null)
        => idAnnee.HasValue
            ? QueryList($"SELECT * FROM {Q(Tables.SessionExam)} WHERE {Q("ID_ANNEE")} = ? ORDER BY {Q("DATE_DEBUT")}, {Q("LIBELLE")}", MapSession, P(idAnnee.Value))
            : QueryList($"SELECT * FROM {Q(Tables.SessionExam)} ORDER BY {Q("ID_ANNEE")} DESC, {Q("DATE_DEBUT")}", MapSession);

    public int InsertSession(SessionExam session)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.SessionExam)} ({Q("ID_ANNEE")}, {Q("LIBELLE")}, {Q("NATURE")}, {Q("DATE_DEBUT")}, {Q("DATE_FIN")}, {Q("CLOTUREE")}) VALUES (?, ?, ?, ?, ?, ?)",
            P(session.IdAnnee), P(session.Libelle), P(session.Nature),
            P(session.DateDebut), P(session.DateFin), P(session.Cloturee ?? false));

    public int UpdateSession(SessionExam session)
        => Execute(
            $"UPDATE {Q(Tables.SessionExam)} SET {Q("ID_ANNEE")} = ?, {Q("LIBELLE")} = ?, {Q("NATURE")} = ?, {Q("DATE_DEBUT")} = ?, {Q("DATE_FIN")} = ?, {Q("CLOTUREE")} = ? WHERE {Q("ID_SESSION")} = ?",
            P(session.IdAnnee), P(session.Libelle), P(session.Nature),
            P(session.DateDebut), P(session.DateFin), P(session.Cloturee ?? false), P(session.IdSession));

    public int SetSessionCloturee(int idSession, bool cloturee)
        => Execute(
            $"UPDATE {Q(Tables.SessionExam)} SET {Q("CLOTUREE")} = ? WHERE {Q("ID_SESSION")} = ?",
            P(cloturee), P(idSession));

    public int DeleteSession(int idSession)
        => Execute($"DELETE FROM {Q(Tables.SessionExam)} WHERE {Q("ID_SESSION")} = ?", P(idSession));

    // ----- EPREUVE -----

    public Epreuve? GetEpreuve(int idEpreuve)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.Epreuve)} WHERE {Q("ID_EPREUVE")} = ?",
            MapEpreuve, P(idEpreuve));

    public EpreuveDetail? GetEpreuveDetail(int idEpreuve)
        => QuerySingle(EpreuveDetailSql() + $" WHERE EP.{Q("ID_EPREUVE")} = ?", MapEpreuveDetail, P(idEpreuve));

    public List<EpreuveDetail> ListEpreuves(int? idSession = null, int? idClasse = null)
    {
        var conditions = new List<string>();
        var parameters = new List<System.Data.OleDb.OleDbParameter>();
        if (idSession.HasValue) { conditions.Add($"EP.{Q("ID_SESSION")} = ?"); parameters.Add(P(idSession.Value)); }
        if (idClasse.HasValue) { conditions.Add($"EP.{Q("ID_CLASSE")} = ?"); parameters.Add(P(idClasse.Value)); }
        var sql = EpreuveDetailSql();
        if (conditions.Count > 0) sql += " WHERE " + string.Join(" AND ", conditions);
        sql += $" ORDER BY EP.{Q("DATE_EPREUVE")}, EP.{Q("ID_EPREUVE")}";
        return QueryList(sql, MapEpreuveDetail, parameters.ToArray());
    }

    private static string EpreuveDetailSql()
        => $"SELECT EP.*, SE.{Q("LIBELLE")} AS SESSION_LIB, C.{Q("LIBELLE")} AS CLASSE_LIB, " +
           $"M.{Q("MATIERE")} AS MATIERE_LIB, S.{Q("NOM_SALLE")} AS SALLE_LIB " +
           $"FROM (((({Q(Tables.Epreuve)} AS EP " +
           $"INNER JOIN {Q(Tables.SessionExam)} AS SE ON EP.{Q("ID_SESSION")} = SE.{Q("ID_SESSION")}) " +
           $"INNER JOIN {Q(Tables.Classe)} AS C ON EP.{Q("ID_CLASSE")} = C.{Q("ID_CLASSE")}) " +
           $"INNER JOIN {Q(Tables.Matiere)} AS M ON EP.{Q("CODE_MATIERE")} = M.{Q("CODE_MATIERE")}) " +
           $"LEFT JOIN {Q(Tables.Salle)} AS S ON EP.{Q("ID_SALLE")} = S.{Q("ID_SALLE")})";

    public int InsertEpreuve(Epreuve epreuve)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.Epreuve)} ({Q("ID_SESSION")}, {Q("ID_CLASSE")}, {Q("CODE_MATIERE")}, {Q("DATE_EPREUVE")}, " +
            $"{Q("HEURE_DEBUT")}, {Q("DUREE_MN")}, {Q("COEFFICIENT")}, {Q("BAREME")}, {Q("ID_SALLE")}, {Q("SURVEILLANT")}) " +
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            P(epreuve.IdSession), P(epreuve.IdClasse), P(epreuve.CodeMatiere), P(epreuve.DateEpreuve),
            P(epreuve.HeureDebut), P(epreuve.DureeMn), P(epreuve.Coefficient), P(epreuve.Bareme),
            P(epreuve.IdSalle), P(epreuve.Surveillant));

    public int UpdateEpreuve(Epreuve epreuve)
        => Execute(
            $"UPDATE {Q(Tables.Epreuve)} SET {Q("ID_SESSION")} = ?, {Q("ID_CLASSE")} = ?, {Q("CODE_MATIERE")} = ?, {Q("DATE_EPREUVE")} = ?, " +
            $"{Q("HEURE_DEBUT")} = ?, {Q("DUREE_MN")} = ?, {Q("COEFFICIENT")} = ?, {Q("BAREME")} = ?, {Q("ID_SALLE")} = ?, {Q("SURVEILLANT")} = ? " +
            $"WHERE {Q("ID_EPREUVE")} = ?",
            P(epreuve.IdSession), P(epreuve.IdClasse), P(epreuve.CodeMatiere), P(epreuve.DateEpreuve),
            P(epreuve.HeureDebut), P(epreuve.DureeMn), P(epreuve.Coefficient), P(epreuve.Bareme),
            P(epreuve.IdSalle), P(epreuve.Surveillant), P(epreuve.IdEpreuve));

    public int DeleteEpreuve(int idEpreuve)
        => Execute($"DELETE FROM {Q(Tables.Epreuve)} WHERE {Q("ID_EPREUVE")} = ?", P(idEpreuve));

    // ----- NOTE_EXAMEN -----

    public NoteExamen? GetNoteExamen(int idEpreuve, int idInscription)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.NoteExamen)} WHERE {Q("ID_EPREUVE")} = ? AND {Q("ID_INSCRIPTION")} = ?",
            MapNoteExamen, P(idEpreuve), P(idInscription));

    public List<NoteSaisieRow> ListGrilleSaisie(int idEpreuve, int idClasse)
        => QueryList(
            $"SELECT N.{Q("ID_NOTE_EX")} AS ID_NOTE, I.{Q("ID_INSCRIPTION")}, E.{Q("MATRICULE")}, E.{Q("NOM")}, E.{Q("PRENOM")}, " +
            $"N.{Q("VALEUR_NOTE")}, N.{Q("ABSENT")} " +
            $"FROM (({Q(Tables.Inscription)} AS I " +
            $"INNER JOIN {Q(Tables.Etudiant)} AS E ON I.{Q("ID_ETUDIANT")} = E.{Q("ID_ETUDIANT")}) " +
            $"LEFT JOIN {Q(Tables.NoteExamen)} AS N ON N.{Q("ID_INSCRIPTION")} = I.{Q("ID_INSCRIPTION")} AND N.{Q("ID_EPREUVE")} = ?) " +
            $"WHERE I.{Q("ID_CLASSE")} = ? ORDER BY E.{Q("NOM")}, E.{Q("PRENOM")}",
            EvaluationRepository.MapNoteSaisieRow, P(idEpreuve), P(idClasse));

    public int CountNotesByEpreuve(int idEpreuve)
        => ScalarInt($"SELECT COUNT(*) FROM {Q(Tables.NoteExamen)} WHERE {Q("ID_EPREUVE")} = ?", P(idEpreuve));

    public int InsertNoteExamen(NoteExamen note)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.NoteExamen)} ({Q("ID_EPREUVE")}, {Q("ID_INSCRIPTION")}, {Q("VALEUR_NOTE")}, " +
            $"{Q("ABSENT")}, {Q("COPIE_NUM")}, {Q("DATE_SAISIE")}, {Q("CODE_UTR")}) VALUES (?, ?, ?, ?, ?, ?, ?)",
            P(note.IdEpreuve), P(note.IdInscription), P(note.ValeurNote), P(note.Absent ?? false),
            P(note.CopieNum), P(note.DateSaisie ?? DateTime.Now), P(note.CodeUtr));

    public int UpdateNoteExamen(NoteExamen note)
        => Execute(
            $"UPDATE {Q(Tables.NoteExamen)} SET {Q("VALEUR_NOTE")} = ?, {Q("ABSENT")} = ?, {Q("COPIE_NUM")} = ?, " +
            $"{Q("DATE_SAISIE")} = ?, {Q("CODE_UTR")} = ? WHERE {Q("ID_NOTE_EX")} = ?",
            P(note.ValeurNote), P(note.Absent ?? false), P(note.CopieNum),
            P(note.DateSaisie ?? DateTime.Now), P(note.CodeUtr), P(note.IdNoteEx));

    public int DeleteNoteExamen(int idNoteEx)
        => Execute($"DELETE FROM {Q(Tables.NoteExamen)} WHERE {Q("ID_NOTE_EX")} = ?", P(idNoteEx));

    /// <summary>Notes d'examen pondérables d'une classe pour une session (barème et coef inclus).</summary>
    public DataTable ListNotesPonderees(int idClasse, int idSession)
        => QueryTable(
            $"SELECT N.{Q("ID_INSCRIPTION")}, N.{Q("VALEUR_NOTE")}, N.{Q("ABSENT")}, " +
            $"EP.{Q("BAREME")}, EP.{Q("COEFFICIENT")}, EP.{Q("CODE_MATIERE")} " +
            $"FROM {Q(Tables.NoteExamen)} AS N " +
            $"INNER JOIN {Q(Tables.Epreuve)} AS EP ON N.{Q("ID_EPREUVE")} = EP.{Q("ID_EPREUVE")} " +
            $"WHERE EP.{Q("ID_CLASSE")} = ? AND EP.{Q("ID_SESSION")} = ?",
            P(idClasse), P(idSession));

    // ----- Mappers -----

    public static SessionExam MapSession(DataRow row) => new()
    {
        IdSession = DataRowMapper.GetInt32(row, "ID_SESSION"),
        IdAnnee = DataRowMapper.GetInt32(row, "ID_ANNEE"),
        Libelle = DataRowMapper.GetString(row, "LIBELLE"),
        Nature = DataRowMapper.GetString(row, "NATURE"),
        DateDebut = DataRowMapper.GetDateTime(row, "DATE_DEBUT"),
        DateFin = DataRowMapper.GetDateTime(row, "DATE_FIN"),
        Cloturee = DataRowMapper.GetBoolean(row, "CLOTUREE")
    };

    public static Epreuve MapEpreuve(DataRow row) => new()
    {
        IdEpreuve = DataRowMapper.GetInt32(row, "ID_EPREUVE"),
        IdSession = DataRowMapper.GetInt32(row, "ID_SESSION"),
        IdClasse = DataRowMapper.GetInt32(row, "ID_CLASSE"),
        CodeMatiere = DataRowMapper.GetString(row, "CODE_MATIERE"),
        DateEpreuve = DataRowMapper.GetDateTime(row, "DATE_EPREUVE"),
        HeureDebut = DataRowMapper.GetString(row, "HEURE_DEBUT"),
        DureeMn = DataRowMapper.GetInt32(row, "DUREE_MN"),
        Coefficient = DataRowMapper.GetDouble(row, "COEFFICIENT"),
        Bareme = DataRowMapper.GetDouble(row, "BAREME"),
        IdSalle = DataRowMapper.GetInt32(row, "ID_SALLE"),
        Surveillant = DataRowMapper.GetString(row, "SURVEILLANT")
    };

    public static EpreuveDetail MapEpreuveDetail(DataRow row) => new()
    {
        IdEpreuve = DataRowMapper.GetInt32(row, "ID_EPREUVE"),
        IdSession = DataRowMapper.GetInt32(row, "ID_SESSION"),
        Session = DataRowMapper.GetString(row, "SESSION_LIB"),
        IdClasse = DataRowMapper.GetInt32(row, "ID_CLASSE"),
        Classe = DataRowMapper.GetString(row, "CLASSE_LIB"),
        CodeMatiere = DataRowMapper.GetString(row, "CODE_MATIERE"),
        Matiere = DataRowMapper.GetString(row, "MATIERE_LIB"),
        DateEpreuve = DataRowMapper.GetDateTime(row, "DATE_EPREUVE"),
        HeureDebut = DataRowMapper.GetString(row, "HEURE_DEBUT"),
        DureeMn = DataRowMapper.GetInt32(row, "DUREE_MN"),
        Coefficient = DataRowMapper.GetDouble(row, "COEFFICIENT"),
        Bareme = DataRowMapper.GetDouble(row, "BAREME"),
        IdSalle = DataRowMapper.GetInt32(row, "ID_SALLE"),
        Salle = DataRowMapper.GetString(row, "SALLE_LIB"),
        Surveillant = DataRowMapper.GetString(row, "SURVEILLANT")
    };

    public static NoteExamen MapNoteExamen(DataRow row) => new()
    {
        IdNoteEx = DataRowMapper.GetInt32(row, "ID_NOTE_EX"),
        IdEpreuve = DataRowMapper.GetInt32(row, "ID_EPREUVE"),
        IdInscription = DataRowMapper.GetInt32(row, "ID_INSCRIPTION"),
        ValeurNote = DataRowMapper.GetDouble(row, "VALEUR_NOTE"),
        Absent = DataRowMapper.GetBoolean(row, "ABSENT"),
        CopieNum = DataRowMapper.GetString(row, "COPIE_NUM"),
        DateSaisie = DataRowMapper.GetDateTime(row, "DATE_SAISIE"),
        CodeUtr = DataRowMapper.GetString(row, "CODE_UTR")
    };
}
