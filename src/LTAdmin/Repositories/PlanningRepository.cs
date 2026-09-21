using System.Data;
using LTAdmin.Data;
using LTAdmin.Models.Dto;
using LTAdmin.Models.Entities;

namespace LTAdmin.Repositories;

/// <summary>Dépôt du planning : créneaux, emplois du temps, séances, absences.</summary>
public sealed class PlanningRepository : RepositoryBase
{
    public PlanningRepository(AccessDatabase database) : base(database)
    {
    }

    // ----- CRENEAU -----

    public List<Creneau> ListCreneaux()
        => QueryList(
            $"SELECT * FROM {Q(Tables.Creneau)} ORDER BY {Q("ORDRE_CRE")}, {Q("ID_CRENEAU")}",
            MapCreneau);

    public Creneau? GetCreneau(int idCreneau)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.Creneau)} WHERE {Q("ID_CRENEAU")} = ?",
            MapCreneau, P(idCreneau));

    public int InsertCreneau(Creneau creneau)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.Creneau)} ({Q("LIBELLE")}, {Q("HEURE_DEBUT")}, {Q("HEURE_FIN")}, {Q("ORDRE_CRE")}) VALUES (?, ?, ?, ?)",
            P(creneau.Libelle), P(creneau.HeureDebut), P(creneau.HeureFin), P(creneau.OrdreCre));

    public int UpdateCreneau(Creneau creneau)
        => Execute(
            $"UPDATE {Q(Tables.Creneau)} SET {Q("LIBELLE")} = ?, {Q("HEURE_DEBUT")} = ?, {Q("HEURE_FIN")} = ?, {Q("ORDRE_CRE")} = ? WHERE {Q("ID_CRENEAU")} = ?",
            P(creneau.Libelle), P(creneau.HeureDebut), P(creneau.HeureFin), P(creneau.OrdreCre), P(creneau.IdCreneau));

    public int DeleteCreneau(int idCreneau)
        => Execute($"DELETE FROM {Q(Tables.Creneau)} WHERE {Q("ID_CRENEAU")} = ?", P(idCreneau));

    // ----- EMPLOI_DU_TEMPS -----

    public EmploiDuTemps? GetSlot(int idEdt)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.EmploiDuTemps)} WHERE {Q("ID_EDT")} = ?",
            MapSlot, P(idEdt));

    public EdtSlotDetail? GetSlotDetail(int idEdt)
        => QuerySingle(SlotDetailSql() + $" WHERE EDT.{Q("ID_EDT")} = ?", MapSlotDetail, P(idEdt));

    public List<EdtSlotDetail> ListSlotsByClasse(int idClasse, bool actifsSeulement = true)
    {
        var sql = SlotDetailSql() + $" WHERE P.{Q("ID_CLASSE")} = ?";
        if (actifsSeulement) sql += $" AND EDT.{Q("ACTIF")} = ?";
        sql += $" ORDER BY CR.{Q("ORDRE_CRE")}";
        return actifsSeulement
            ? QueryList(sql, MapSlotDetail, P(idClasse), P(true))
            : QueryList(sql, MapSlotDetail, P(idClasse));
    }

    public List<EdtSlotDetail> ListSlotsByProg(int idProg)
        => QueryList(SlotDetailSql() + $" WHERE EDT.{Q("ID_PROG")} = ? ORDER BY CR.{Q("ORDRE_CRE")}",
            MapSlotDetail, P(idProg));

    /// <summary>
    /// Slots actifs concurrents : même jour + même créneau (hors slot exclu).
    /// Le service évalue ensuite le conflit salle / formateur (EDT_CONFLIT).
    /// </summary>
    public List<EdtSlotDetail> ListSlotsConcurrents(string jour, int idCreneau, int? excludeIdEdt = null)
    {
        var sql = SlotDetailSql() + $" WHERE EDT.{Q("JOUR")} = ? AND EDT.{Q("ID_CRENEAU")} = ? AND EDT.{Q("ACTIF")} = ?";
        if (excludeIdEdt.HasValue)
            return QueryList(sql + $" AND EDT.{Q("ID_EDT")} <> ?", MapSlotDetail,
                P(jour), P(idCreneau), P(true), P(excludeIdEdt.Value));
        return QueryList(sql, MapSlotDetail, P(jour), P(idCreneau), P(true));
    }

    private static string SlotDetailSql()
        => $"SELECT EDT.*, P.{Q("ID_CLASSE")} AS ID_CLASSE, C.{Q("LIBELLE")} AS CLASSE_LIB, " +
           $"P.{Q("CODE_MATIERE")} AS CODE_MATIERE, M.{Q("MATIERE")} AS MATIERE_LIB, " +
           $"P.{Q("ID_FORMATEUR")} AS ID_FORMATEUR, F.{Q("NOM")} AS FORM_NOM, F.{Q("PRENOM")} AS FORM_PRENOM, " +
           $"CR.{Q("LIBELLE")} AS CRENEAU_LIB, CR.{Q("HEURE_DEBUT")} AS CR_DEBUT, CR.{Q("HEURE_FIN")} AS CR_FIN, " +
           $"S.{Q("NOM_SALLE")} AS SALLE_LIB " +
           $"FROM (((((({Q(Tables.EmploiDuTemps)} AS EDT " +
           $"INNER JOIN {Q(Tables.Programme)} AS P ON EDT.{Q("ID_PROG")} = P.{Q("ID_PROG")}) " +
           $"INNER JOIN {Q(Tables.Classe)} AS C ON P.{Q("ID_CLASSE")} = C.{Q("ID_CLASSE")}) " +
           $"INNER JOIN {Q(Tables.Matiere)} AS M ON P.{Q("CODE_MATIERE")} = M.{Q("CODE_MATIERE")}) " +
           $"INNER JOIN {Q(Tables.Creneau)} AS CR ON EDT.{Q("ID_CRENEAU")} = CR.{Q("ID_CRENEAU")}) " +
           $"LEFT JOIN {Q(Tables.Formateur)} AS F ON P.{Q("ID_FORMATEUR")} = F.{Q("ID_FORMATEUR")}) " +
           $"LEFT JOIN {Q(Tables.Salle)} AS S ON EDT.{Q("ID_SALLE")} = S.{Q("ID_SALLE")})";

    public int InsertSlot(EmploiDuTemps slot)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.EmploiDuTemps)} ({Q("ID_PROG")}, {Q("ID_CRENEAU")}, {Q("JOUR")}, {Q("ID_SALLE")}, " +
            $"{Q("DATE_DEBUT")}, {Q("DATE_FIN")}, {Q("ACTIF")}) VALUES (?, ?, ?, ?, ?, ?, ?)",
            P(slot.IdProg), P(slot.IdCreneau), P(slot.Jour), P(slot.IdSalle),
            P(slot.DateDebut), P(slot.DateFin), P(slot.Actif ?? true));

    public int UpdateSlot(EmploiDuTemps slot)
        => Execute(
            $"UPDATE {Q(Tables.EmploiDuTemps)} SET {Q("ID_PROG")} = ?, {Q("ID_CRENEAU")} = ?, {Q("JOUR")} = ?, {Q("ID_SALLE")} = ?, " +
            $"{Q("DATE_DEBUT")} = ?, {Q("DATE_FIN")} = ?, {Q("ACTIF")} = ? WHERE {Q("ID_EDT")} = ?",
            P(slot.IdProg), P(slot.IdCreneau), P(slot.Jour), P(slot.IdSalle),
            P(slot.DateDebut), P(slot.DateFin), P(slot.Actif ?? true), P(slot.IdEdt));

    public int SetSlotActif(int idEdt, bool actif)
        => Execute(
            $"UPDATE {Q(Tables.EmploiDuTemps)} SET {Q("ACTIF")} = ? WHERE {Q("ID_EDT")} = ?",
            P(actif), P(idEdt));

    public int DeleteSlot(int idEdt)
        => Execute($"DELETE FROM {Q(Tables.EmploiDuTemps)} WHERE {Q("ID_EDT")} = ?", P(idEdt));

    // ----- SEANCE -----

    public Seance? GetSeance(int idSeance)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.Seance)} WHERE {Q("ID_SEANCE")} = ?",
            MapSeance, P(idSeance));

    public List<Seance> ListSeancesByEdt(int idEdt)
        => QueryList(
            $"SELECT * FROM {Q(Tables.Seance)} WHERE {Q("ID_EDT")} = ? ORDER BY {Q("DATE_SEANCE")} DESC",
            MapSeance, P(idEdt));

    public List<SeanceDetail> ListSeances(DateTime? debut, DateTime? fin, int? idClasse = null)
    {
        var conditions = new List<string>();
        var parameters = new List<System.Data.OleDb.OleDbParameter>();
        if (debut.HasValue) { conditions.Add($"SEA.{Q("DATE_SEANCE")} >= ?"); parameters.Add(P(debut.Value)); }
        if (fin.HasValue) { conditions.Add($"SEA.{Q("DATE_SEANCE")} < ?"); parameters.Add(P(fin.Value.Date.AddDays(1))); }
        if (idClasse.HasValue) { conditions.Add($"P.{Q("ID_CLASSE")} = ?"); parameters.Add(P(idClasse.Value)); }
        var sql = SeanceDetailSql();
        if (conditions.Count > 0) sql += " WHERE " + string.Join(" AND ", conditions);
        sql += $" ORDER BY SEA.{Q("DATE_SEANCE")} DESC";
        return QueryList(sql, MapSeanceDetail, parameters.ToArray());
    }

    private static string SeanceDetailSql()
        => $"SELECT SEA.*, EDT.{Q("JOUR")} AS JOUR, CR.{Q("LIBELLE")} AS CRENEAU_LIB, " +
           $"C.{Q("LIBELLE")} AS CLASSE_LIB, M.{Q("MATIERE")} AS MATIERE_LIB " +
           $"FROM ((((({Q(Tables.Seance)} AS SEA " +
           $"INNER JOIN {Q(Tables.EmploiDuTemps)} AS EDT ON SEA.{Q("ID_EDT")} = EDT.{Q("ID_EDT")}) " +
           $"INNER JOIN {Q(Tables.Programme)} AS P ON EDT.{Q("ID_PROG")} = P.{Q("ID_PROG")}) " +
           $"INNER JOIN {Q(Tables.Classe)} AS C ON P.{Q("ID_CLASSE")} = C.{Q("ID_CLASSE")}) " +
           $"INNER JOIN {Q(Tables.Matiere)} AS M ON P.{Q("CODE_MATIERE")} = M.{Q("CODE_MATIERE")}) " +
           $"INNER JOIN {Q(Tables.Creneau)} AS CR ON EDT.{Q("ID_CRENEAU")} = CR.{Q("ID_CRENEAU")})";

    public int InsertSeance(Seance seance)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.Seance)} ({Q("ID_EDT")}, {Q("DATE_SEANCE")}, {Q("CONTENU")}, {Q("NB_HEURES")}, " +
            $"{Q("STATUT")}, {Q("ID_FORMATEUR_REMP")}) VALUES (?, ?, ?, ?, ?, ?)",
            P(seance.IdEdt), P(seance.DateSeance), P(seance.Contenu), P(seance.NbHeures),
            P(seance.Statut), P(seance.IdFormateurRemp));

    public int UpdateSeance(Seance seance)
        => Execute(
            $"UPDATE {Q(Tables.Seance)} SET {Q("ID_EDT")} = ?, {Q("DATE_SEANCE")} = ?, {Q("CONTENU")} = ?, {Q("NB_HEURES")} = ?, " +
            $"{Q("STATUT")} = ?, {Q("ID_FORMATEUR_REMP")} = ? WHERE {Q("ID_SEANCE")} = ?",
            P(seance.IdEdt), P(seance.DateSeance), P(seance.Contenu), P(seance.NbHeures),
            P(seance.Statut), P(seance.IdFormateurRemp), P(seance.IdSeance));

    public int DeleteSeance(int idSeance)
        => Execute($"DELETE FROM {Q(Tables.Seance)} WHERE {Q("ID_SEANCE")} = ?", P(idSeance));

    /// <summary>Heures réalisées par un formateur sur une période (paie).</summary>
    public double SumHeuresFormateur(int idFormateur, DateTime debut, DateTime fin)
        => ScalarDouble(
            $"SELECT SUM(SEA.{Q("NB_HEURES")}) " +
            $"FROM (({Q(Tables.Seance)} AS SEA " +
            $"INNER JOIN {Q(Tables.EmploiDuTemps)} AS EDT ON SEA.{Q("ID_EDT")} = EDT.{Q("ID_EDT")}) " +
            $"INNER JOIN {Q(Tables.Programme)} AS P ON EDT.{Q("ID_PROG")} = P.{Q("ID_PROG")}) " +
            $"WHERE P.{Q("ID_FORMATEUR")} = ? AND SEA.{Q("DATE_SEANCE")} >= ? AND SEA.{Q("DATE_SEANCE")} < ?",
            P(idFormateur), P(debut), P(fin.Date.AddDays(1))) ?? 0d;

    // ----- ABSENCE -----

    public Absence? GetAbsence(int idAbsence)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.Absence)} WHERE {Q("ID_ABSENCE")} = ?",
            MapAbsence, P(idAbsence));

    public List<Absence> ListAbsencesBySeance(int idSeance)
        => QueryList(
            $"SELECT * FROM {Q(Tables.Absence)} WHERE {Q("ID_SEANCE")} = ?",
            MapAbsence, P(idSeance));

    public List<Absence> ListAbsencesByInscription(int idInscription)
        => QueryList(
            $"SELECT * FROM {Q(Tables.Absence)} WHERE {Q("ID_INSCRIPTION")} = ?",
            MapAbsence, P(idInscription));

    public double SumHeuresAbsence(int idInscription)
        => ScalarDouble(
            $"SELECT SUM({Q("NB_HEURES")}) FROM {Q(Tables.Absence)} WHERE {Q("ID_INSCRIPTION")} = ?",
            P(idInscription)) ?? 0d;

    public int InsertAbsence(Absence absence)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.Absence)} ({Q("ID_SEANCE")}, {Q("ID_INSCRIPTION")}, {Q("NATURE")}, {Q("NB_HEURES")}, " +
            $"{Q("JUSTIFIEE")}, {Q("MOTIF")}, {Q("DATE_SAISIE")}) VALUES (?, ?, ?, ?, ?, ?, ?)",
            P(absence.IdSeance), P(absence.IdInscription), P(absence.Nature), P(absence.NbHeures),
            P(absence.Justifiee ?? false), P(absence.Motif), P(absence.DateSaisie ?? DateTime.Now));

    public int UpdateAbsence(Absence absence)
        => Execute(
            $"UPDATE {Q(Tables.Absence)} SET {Q("ID_SEANCE")} = ?, {Q("ID_INSCRIPTION")} = ?, {Q("NATURE")} = ?, {Q("NB_HEURES")} = ?, " +
            $"{Q("JUSTIFIEE")} = ?, {Q("MOTIF")} = ?, {Q("DATE_SAISIE")} = ? WHERE {Q("ID_ABSENCE")} = ?",
            P(absence.IdSeance), P(absence.IdInscription), P(absence.Nature), P(absence.NbHeures),
            P(absence.Justifiee ?? false), P(absence.Motif), P(absence.DateSaisie ?? DateTime.Now),
            P(absence.IdAbsence));

    public int DeleteAbsence(int idAbsence)
        => Execute($"DELETE FROM {Q(Tables.Absence)} WHERE {Q("ID_ABSENCE")} = ?", P(idAbsence));

    // ----- Mappers -----

    public static Creneau MapCreneau(DataRow row) => new()
    {
        IdCreneau = DataRowMapper.GetInt32(row, "ID_CRENEAU"),
        Libelle = DataRowMapper.GetString(row, "LIBELLE"),
        HeureDebut = DataRowMapper.GetString(row, "HEURE_DEBUT"),
        HeureFin = DataRowMapper.GetString(row, "HEURE_FIN"),
        OrdreCre = DataRowMapper.GetInt32(row, "ORDRE_CRE")
    };

    public static EmploiDuTemps MapSlot(DataRow row) => new()
    {
        IdEdt = DataRowMapper.GetInt32(row, "ID_EDT"),
        IdProg = DataRowMapper.GetInt32(row, "ID_PROG"),
        IdCreneau = DataRowMapper.GetInt32(row, "ID_CRENEAU"),
        Jour = DataRowMapper.GetString(row, "JOUR"),
        IdSalle = DataRowMapper.GetInt32(row, "ID_SALLE"),
        DateDebut = DataRowMapper.GetDateTime(row, "DATE_DEBUT"),
        DateFin = DataRowMapper.GetDateTime(row, "DATE_FIN"),
        Actif = DataRowMapper.GetBoolean(row, "ACTIF")
    };

    public static EdtSlotDetail MapSlotDetail(DataRow row)
    {
        var nom = DataRowMapper.GetString(row, "FORM_NOM");
        var prenom = DataRowMapper.GetString(row, "FORM_PRENOM");
        return new EdtSlotDetail
        {
            IdEdt = DataRowMapper.GetInt32(row, "ID_EDT"),
            IdProg = DataRowMapper.GetInt32(row, "ID_PROG"),
            IdClasse = DataRowMapper.GetInt32(row, "ID_CLASSE"),
            Classe = DataRowMapper.GetString(row, "CLASSE_LIB"),
            CodeMatiere = DataRowMapper.GetString(row, "CODE_MATIERE"),
            Matiere = DataRowMapper.GetString(row, "MATIERE_LIB"),
            IdFormateur = DataRowMapper.GetInt32(row, "ID_FORMATEUR"),
            Formateur = string.IsNullOrWhiteSpace(nom) && string.IsNullOrWhiteSpace(prenom)
                ? null : $"{nom} {prenom}".Trim(),
            IdCreneau = DataRowMapper.GetInt32(row, "ID_CRENEAU"),
            Creneau = DataRowMapper.GetString(row, "CRENEAU_LIB"),
            HeureDebut = DataRowMapper.GetString(row, "CR_DEBUT"),
            HeureFin = DataRowMapper.GetString(row, "CR_FIN"),
            Jour = DataRowMapper.GetString(row, "JOUR"),
            IdSalle = DataRowMapper.GetInt32(row, "ID_SALLE"),
            Salle = DataRowMapper.GetString(row, "SALLE_LIB"),
            DateDebut = DataRowMapper.GetDateTime(row, "DATE_DEBUT"),
            DateFin = DataRowMapper.GetDateTime(row, "DATE_FIN"),
            Actif = DataRowMapper.GetBoolean(row, "ACTIF")
        };
    }

    public static Seance MapSeance(DataRow row) => new()
    {
        IdSeance = DataRowMapper.GetInt32(row, "ID_SEANCE"),
        IdEdt = DataRowMapper.GetInt32(row, "ID_EDT"),
        DateSeance = DataRowMapper.GetDateTime(row, "DATE_SEANCE"),
        Contenu = DataRowMapper.GetString(row, "CONTENU"),
        NbHeures = DataRowMapper.GetDouble(row, "NB_HEURES"),
        Statut = DataRowMapper.GetString(row, "STATUT"),
        IdFormateurRemp = DataRowMapper.GetInt32(row, "ID_FORMATEUR_REMP")
    };

    public static SeanceDetail MapSeanceDetail(DataRow row) => new()
    {
        IdSeance = DataRowMapper.GetInt32(row, "ID_SEANCE"),
        IdEdt = DataRowMapper.GetInt32(row, "ID_EDT"),
        Classe = DataRowMapper.GetString(row, "CLASSE_LIB"),
        Matiere = DataRowMapper.GetString(row, "MATIERE_LIB"),
        Jour = DataRowMapper.GetString(row, "JOUR"),
        Creneau = DataRowMapper.GetString(row, "CRENEAU_LIB"),
        DateSeance = DataRowMapper.GetDateTime(row, "DATE_SEANCE"),
        NbHeures = DataRowMapper.GetDouble(row, "NB_HEURES"),
        Statut = DataRowMapper.GetString(row, "STATUT")
    };

    public static Absence MapAbsence(DataRow row) => new()
    {
        IdAbsence = DataRowMapper.GetInt32(row, "ID_ABSENCE"),
        IdSeance = DataRowMapper.GetInt32(row, "ID_SEANCE"),
        IdInscription = DataRowMapper.GetInt32(row, "ID_INSCRIPTION"),
        Nature = DataRowMapper.GetString(row, "NATURE"),
        NbHeures = DataRowMapper.GetDouble(row, "NB_HEURES"),
        Justifiee = DataRowMapper.GetBoolean(row, "JUSTIFIEE"),
        Motif = DataRowMapper.GetString(row, "MOTIF"),
        DateSaisie = DataRowMapper.GetDateTime(row, "DATE_SAISIE")
    };
}
