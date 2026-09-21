using System.Data;
using LTAdmin.Data;
using LTAdmin.Models.Dto;
using LTAdmin.Models.Entities;

namespace LTAdmin.Repositories;

/// <summary>Dépôt du personnel : formateurs et programmes (affectations).</summary>
public sealed class StaffRepository : RepositoryBase
{
    public StaffRepository(AccessDatabase database) : base(database)
    {
    }

    // ----- FORMATEUR -----

    public Formateur? GetFormateur(int idFormateur)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.Formateur)} WHERE {Q("ID_FORMATEUR")} = ?",
            MapFormateur, P(idFormateur));

    public List<Formateur> SearchFormateurs(string? recherche, bool actifsSeulement = false, int maxRows = 500)
    {
        var conditions = new List<string>();
        var parameters = new List<System.Data.OleDb.OleDbParameter>();
        if (actifsSeulement) { conditions.Add($"{Q("ACTIF")} = ?"); parameters.Add(P(true)); }
        if (!string.IsNullOrWhiteSpace(recherche))
        {
            var motif = "%" + recherche.Trim() + "%";
            conditions.Add($"({Q("NOM")} LIKE ? OR {Q("PRENOM")} LIKE ? OR {Q("MATRICULE")} LIKE ?)");
            parameters.Add(P(motif));
            parameters.Add(P(motif));
            parameters.Add(P(motif));
        }
        var sql = $"SELECT TOP {Math.Clamp(maxRows, 1, 5000)} * FROM {Q(Tables.Formateur)}";
        if (conditions.Count > 0) sql += " WHERE " + string.Join(" AND ", conditions);
        sql += $" ORDER BY {Q("NOM")}, {Q("PRENOM")}";
        return QueryList(sql, MapFormateur, parameters.ToArray());
    }

    public int CountFormateurs() => ScalarInt($"SELECT COUNT(*) FROM {Q(Tables.Formateur)}");

    public List<string> ListMatricules(string prefixe)
    {
        var table = QueryTable(
            $"SELECT {Q("MATRICULE")} FROM {Q(Tables.Formateur)} WHERE {Q("MATRICULE")} LIKE ?",
            P(prefixe + "%"));
        var result = new List<string>(table.Rows.Count);
        foreach (DataRow row in table.Rows)
        {
            var value = DataRowMapper.GetString(row, "MATRICULE");
            if (!string.IsNullOrWhiteSpace(value)) result.Add(value);
        }
        return result;
    }

    public int InsertFormateur(Formateur formateur)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.Formateur)} ({Q("MATRICULE")}, {Q("NOM")}, {Q("PRENOM")}, {Q("SEXE")}, " +
            $"{Q("DATE_NAISSANCE")}, {Q("CIN")}, {Q("ADRESSE")}, {Q("TEL")}, {Q("EMAIL")}, {Q("SPECIALITE")}, " +
            $"{Q("DIPLOME")}, {Q("CONTRAT")}, {Q("TAUX_HORAIRE")}, {Q("DATE_EMBAUCHE")}, {Q("PHOTO")}, {Q("ACTIF")}) " +
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            P(formateur.Matricule), P(formateur.Nom), P(formateur.Prenom), P(formateur.Sexe),
            P(formateur.DateNaissance), P(formateur.Cin), P(formateur.Adresse), P(formateur.Tel),
            P(formateur.Email), P(formateur.Specialite), P(formateur.Diplome), P(formateur.Contrat),
            P(formateur.TauxHoraire), P(formateur.DateEmbauche), P(formateur.Photo), P(formateur.Actif ?? true));

    public int UpdateFormateur(Formateur formateur)
        => Execute(
            $"UPDATE {Q(Tables.Formateur)} SET {Q("MATRICULE")} = ?, {Q("NOM")} = ?, {Q("PRENOM")} = ?, {Q("SEXE")} = ?, " +
            $"{Q("DATE_NAISSANCE")} = ?, {Q("CIN")} = ?, {Q("ADRESSE")} = ?, {Q("TEL")} = ?, {Q("EMAIL")} = ?, {Q("SPECIALITE")} = ?, " +
            $"{Q("DIPLOME")} = ?, {Q("CONTRAT")} = ?, {Q("TAUX_HORAIRE")} = ?, {Q("DATE_EMBAUCHE")} = ?, {Q("PHOTO")} = ?, {Q("ACTIF")} = ? " +
            $"WHERE {Q("ID_FORMATEUR")} = ?",
            P(formateur.Matricule), P(formateur.Nom), P(formateur.Prenom), P(formateur.Sexe),
            P(formateur.DateNaissance), P(formateur.Cin), P(formateur.Adresse), P(formateur.Tel),
            P(formateur.Email), P(formateur.Specialite), P(formateur.Diplome), P(formateur.Contrat),
            P(formateur.TauxHoraire), P(formateur.DateEmbauche), P(formateur.Photo), P(formateur.Actif ?? true),
            P(formateur.IdFormateur));

    public int DeleteFormateur(int idFormateur)
        => Execute($"DELETE FROM {Q(Tables.Formateur)} WHERE {Q("ID_FORMATEUR")} = ?", P(idFormateur));

    // ----- PROGRAMME -----

    public Programme? GetProgramme(int idProg)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.Programme)} WHERE {Q("ID_PROG")} = ?",
            MapProgramme, P(idProg));

    public Programme? GetProgrammeByClasseMatiere(int idClasse, string codeMatiere)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.Programme)} WHERE {Q("ID_CLASSE")} = ? AND {Q("CODE_MATIERE")} = ?",
            MapProgramme, P(idClasse), P(codeMatiere));

    public List<ProgrammeDetail> ListByClasse(int idClasse)
        => QueryList(ProgrammeDetailSql() + $" WHERE P.{Q("ID_CLASSE")} = ? ORDER BY M.{Q("ORDRE_MAT")}, M.{Q("CODE_MATIERE")}",
            MapProgrammeDetail, P(idClasse));

    public List<ProgrammeDetail> ListByFormateur(int idFormateur)
        => QueryList(ProgrammeDetailSql() + $" WHERE P.{Q("ID_FORMATEUR")} = ? ORDER BY C.{Q("LIBELLE")}, M.{Q("CODE_MATIERE")}",
            MapProgrammeDetail, P(idFormateur));

    public ProgrammeDetail? GetProgrammeDetail(int idProg)
        => QuerySingle(ProgrammeDetailSql() + $" WHERE P.{Q("ID_PROG")} = ?", MapProgrammeDetail, P(idProg));

    private static string ProgrammeDetailSql()
        => $"SELECT P.*, C.{Q("LIBELLE")} AS CLASSE_LIB, M.{Q("MATIERE")} AS MATIERE_LIB, " +
           $"M.{Q("ORDRE_MAT")} AS ORDRE_MAT, F.{Q("NOM")} AS FORM_NOM, F.{Q("PRENOM")} AS FORM_PRENOM " +
           $"FROM ((({Q(Tables.Programme)} AS P " +
           $"INNER JOIN {Q(Tables.Classe)} AS C ON P.{Q("ID_CLASSE")} = C.{Q("ID_CLASSE")}) " +
           $"INNER JOIN {Q(Tables.Matiere)} AS M ON P.{Q("CODE_MATIERE")} = M.{Q("CODE_MATIERE")}) " +
           $"LEFT JOIN {Q(Tables.Formateur)} AS F ON P.{Q("ID_FORMATEUR")} = F.{Q("ID_FORMATEUR")})";

    public int InsertProgramme(Programme programme)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.Programme)} ({Q("ID_CLASSE")}, {Q("CODE_MATIERE")}, {Q("ID_FORMATEUR")}, " +
            $"{Q("COEFFICIENT")}, {Q("VOL_HORAIRE")}, {Q("NOTE_ELIMIN")}, {Q("OBSERVATION")}) VALUES (?, ?, ?, ?, ?, ?, ?)",
            P(programme.IdClasse), P(programme.CodeMatiere), P(programme.IdFormateur),
            P(programme.Coefficient), P(programme.VolHoraire), P(programme.NoteElimin), P(programme.Observation));

    public int UpdateProgramme(Programme programme)
        => Execute(
            $"UPDATE {Q(Tables.Programme)} SET {Q("ID_CLASSE")} = ?, {Q("CODE_MATIERE")} = ?, {Q("ID_FORMATEUR")} = ?, " +
            $"{Q("COEFFICIENT")} = ?, {Q("VOL_HORAIRE")} = ?, {Q("NOTE_ELIMIN")} = ?, {Q("OBSERVATION")} = ? WHERE {Q("ID_PROG")} = ?",
            P(programme.IdClasse), P(programme.CodeMatiere), P(programme.IdFormateur),
            P(programme.Coefficient), P(programme.VolHoraire), P(programme.NoteElimin),
            P(programme.Observation), P(programme.IdProg));

    public int DeleteProgramme(int idProg)
        => Execute($"DELETE FROM {Q(Tables.Programme)} WHERE {Q("ID_PROG")} = ?", P(idProg));

    // ----- Mappers -----

    public static Formateur MapFormateur(DataRow row) => new()
    {
        IdFormateur = DataRowMapper.GetInt32(row, "ID_FORMATEUR"),
        Matricule = DataRowMapper.GetString(row, "MATRICULE"),
        Nom = DataRowMapper.GetString(row, "NOM"),
        Prenom = DataRowMapper.GetString(row, "PRENOM"),
        Sexe = DataRowMapper.GetString(row, "SEXE"),
        DateNaissance = DataRowMapper.GetDateTime(row, "DATE_NAISSANCE"),
        Cin = DataRowMapper.GetString(row, "CIN"),
        Adresse = DataRowMapper.GetString(row, "ADRESSE"),
        Tel = DataRowMapper.GetString(row, "TEL"),
        Email = DataRowMapper.GetString(row, "EMAIL"),
        Specialite = DataRowMapper.GetString(row, "SPECIALITE"),
        Diplome = DataRowMapper.GetString(row, "DIPLOME"),
        Contrat = DataRowMapper.GetString(row, "CONTRAT"),
        TauxHoraire = DataRowMapper.GetDecimal(row, "TAUX_HORAIRE"),
        DateEmbauche = DataRowMapper.GetDateTime(row, "DATE_EMBAUCHE"),
        Photo = DataRowMapper.GetString(row, "PHOTO"),
        Actif = DataRowMapper.GetBoolean(row, "ACTIF")
    };

    public static Programme MapProgramme(DataRow row) => new()
    {
        IdProg = DataRowMapper.GetInt32(row, "ID_PROG"),
        IdClasse = DataRowMapper.GetInt32(row, "ID_CLASSE"),
        CodeMatiere = DataRowMapper.GetString(row, "CODE_MATIERE"),
        IdFormateur = DataRowMapper.GetInt32(row, "ID_FORMATEUR"),
        Coefficient = DataRowMapper.GetDouble(row, "COEFFICIENT"),
        VolHoraire = DataRowMapper.GetInt32(row, "VOL_HORAIRE"),
        NoteElimin = DataRowMapper.GetDouble(row, "NOTE_ELIMIN"),
        Observation = DataRowMapper.GetString(row, "OBSERVATION")
    };

    public static ProgrammeDetail MapProgrammeDetail(DataRow row)
    {
        var nom = DataRowMapper.GetString(row, "FORM_NOM");
        var prenom = DataRowMapper.GetString(row, "FORM_PRENOM");
        return new ProgrammeDetail
        {
            IdProg = DataRowMapper.GetInt32(row, "ID_PROG"),
            IdClasse = DataRowMapper.GetInt32(row, "ID_CLASSE"),
            Classe = DataRowMapper.GetString(row, "CLASSE_LIB"),
            CodeMatiere = DataRowMapper.GetString(row, "CODE_MATIERE"),
            Matiere = DataRowMapper.GetString(row, "MATIERE_LIB"),
            IdFormateur = DataRowMapper.GetInt32(row, "ID_FORMATEUR"),
            Formateur = string.IsNullOrWhiteSpace(nom) && string.IsNullOrWhiteSpace(prenom)
                ? null : $"{nom} {prenom}".Trim(),
            Coefficient = DataRowMapper.GetDouble(row, "COEFFICIENT"),
            VolHoraire = DataRowMapper.GetInt32(row, "VOL_HORAIRE"),
            NoteElimin = DataRowMapper.GetDouble(row, "NOTE_ELIMIN")
        };
    }
}
