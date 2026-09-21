using System.Data;
using LTAdmin.Data;
using LTAdmin.Models.Dto;
using LTAdmin.Models.Entities;

namespace LTAdmin.Repositories;

/// <summary>Dépôt des inscriptions (table INSCRIPTION).</summary>
public sealed class EnrollmentRepository : RepositoryBase
{
    public EnrollmentRepository(AccessDatabase database) : base(database)
    {
    }

    public Inscription? GetById(int idInscription)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.Inscription)} WHERE {Q("ID_INSCRIPTION")} = ?",
            MapInscription, P(idInscription));

    public Inscription? GetByEtudiantClasse(int idEtudiant, int idClasse)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.Inscription)} WHERE {Q("ID_ETUDIANT")} = ? AND {Q("ID_CLASSE")} = ?",
            MapInscription, P(idEtudiant), P(idClasse));

    public InscriptionDetail? GetDetail(int idInscription)
        => QuerySingle(DetailSql() + $" WHERE I.{Q("ID_INSCRIPTION")} = ?", MapDetail, P(idInscription));

    public List<InscriptionDetail> ListByClasse(int idClasse)
        => QueryList(DetailSql() + $" WHERE I.{Q("ID_CLASSE")} = ? ORDER BY E.{Q("NOM")}, E.{Q("PRENOM")}",
            MapDetail, P(idClasse));

    public List<InscriptionDetail> ListByEtudiant(int idEtudiant)
        => QueryList(DetailSql() + $" WHERE I.{Q("ID_ETUDIANT")} = ? ORDER BY C.{Q("LIBELLE")}",
            MapDetail, P(idEtudiant));

    public List<InscriptionDetail> ListByAnnee(int idAnnee)
        => QueryList(DetailSql() + $" WHERE C.{Q("ID_ANNEE")} = ? ORDER BY C.{Q("LIBELLE")}, E.{Q("NOM")}, E.{Q("PRENOM")}",
            MapDetail, P(idAnnee));

    private static string DetailSql()
        => $"SELECT I.*, E.{Q("MATRICULE")}, E.{Q("NOM")}, E.{Q("PRENOM")}, C.{Q("LIBELLE")} AS CLASSE_LIB " +
           $"FROM (({Q(Tables.Inscription)} AS I " +
           $"INNER JOIN {Q(Tables.Etudiant)} AS E ON I.{Q("ID_ETUDIANT")} = E.{Q("ID_ETUDIANT")}) " +
           $"INNER JOIN {Q(Tables.Classe)} AS C ON I.{Q("ID_CLASSE")} = C.{Q("ID_CLASSE")})";

    public int CountByClasse(int idClasse)
        => ScalarInt($"SELECT COUNT(*) FROM {Q(Tables.Inscription)} WHERE {Q("ID_CLASSE")} = ?", P(idClasse));

    public int CountByAnnee(int idAnnee)
        => ScalarInt(
            $"SELECT COUNT(*) FROM {Q(Tables.Inscription)} AS I " +
            $"INNER JOIN {Q(Tables.Classe)} AS C ON I.{Q("ID_CLASSE")} = C.{Q("ID_CLASSE")} " +
            $"WHERE C.{Q("ID_ANNEE")} = ?", P(idAnnee));

    public List<string> ListNumeros(string prefixe)
    {
        var table = QueryTable(
            $"SELECT {Q("NUM_INSCRIPTION")} FROM {Q(Tables.Inscription)} WHERE {Q("NUM_INSCRIPTION")} LIKE ?",
            P(prefixe + "%"));
        var result = new List<string>(table.Rows.Count);
        foreach (DataRow row in table.Rows)
        {
            var value = DataRowMapper.GetString(row, "NUM_INSCRIPTION");
            if (!string.IsNullOrWhiteSpace(value)) result.Add(value);
        }
        return result;
    }

    public int Insert(Inscription inscription)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.Inscription)} ({Q("ID_ETUDIANT")}, {Q("ID_CLASSE")}, {Q("NUM_INSCRIPTION")}, " +
            $"{Q("DATE_INSCRIPTION")}, {Q("REDOUBLANT")}, {Q("STATUT")}, {Q("DATE_SORTIE")}, {Q("MOTIF_SORTIE")}) " +
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            P(inscription.IdEtudiant), P(inscription.IdClasse), P(inscription.NumInscription),
            P(inscription.DateInscription), P(inscription.Redoublant ?? false),
            P(inscription.Statut), P(inscription.DateSortie), P(inscription.MotifSortie));

    public int Update(Inscription inscription)
        => Execute(
            $"UPDATE {Q(Tables.Inscription)} SET {Q("ID_ETUDIANT")} = ?, {Q("ID_CLASSE")} = ?, {Q("NUM_INSCRIPTION")} = ?, " +
            $"{Q("DATE_INSCRIPTION")} = ?, {Q("REDOUBLANT")} = ?, {Q("STATUT")} = ?, {Q("DATE_SORTIE")} = ?, {Q("MOTIF_SORTIE")} = ? " +
            $"WHERE {Q("ID_INSCRIPTION")} = ?",
            P(inscription.IdEtudiant), P(inscription.IdClasse), P(inscription.NumInscription),
            P(inscription.DateInscription), P(inscription.Redoublant ?? false),
            P(inscription.Statut), P(inscription.DateSortie), P(inscription.MotifSortie),
            P(inscription.IdInscription));

    public int Delete(int idInscription)
        => Execute($"DELETE FROM {Q(Tables.Inscription)} WHERE {Q("ID_INSCRIPTION")} = ?", P(idInscription));

    public static Inscription MapInscription(DataRow row) => new()
    {
        IdInscription = DataRowMapper.GetInt32(row, "ID_INSCRIPTION"),
        IdEtudiant = DataRowMapper.GetInt32(row, "ID_ETUDIANT"),
        IdClasse = DataRowMapper.GetInt32(row, "ID_CLASSE"),
        NumInscription = DataRowMapper.GetString(row, "NUM_INSCRIPTION"),
        DateInscription = DataRowMapper.GetDateTime(row, "DATE_INSCRIPTION"),
        Redoublant = DataRowMapper.GetBoolean(row, "REDOUBLANT"),
        Statut = DataRowMapper.GetString(row, "STATUT"),
        DateSortie = DataRowMapper.GetDateTime(row, "DATE_SORTIE"),
        MotifSortie = DataRowMapper.GetString(row, "MOTIF_SORTIE")
    };

    public static InscriptionDetail MapDetail(DataRow row) => new()
    {
        IdInscription = DataRowMapper.GetInt32(row, "ID_INSCRIPTION"),
        IdEtudiant = DataRowMapper.GetInt32(row, "ID_ETUDIANT"),
        IdClasse = DataRowMapper.GetInt32(row, "ID_CLASSE"),
        Matricule = DataRowMapper.GetString(row, "MATRICULE"),
        Nom = DataRowMapper.GetString(row, "NOM"),
        Prenom = DataRowMapper.GetString(row, "PRENOM"),
        Classe = DataRowMapper.GetString(row, "CLASSE_LIB"),
        NumInscription = DataRowMapper.GetString(row, "NUM_INSCRIPTION"),
        DateInscription = DataRowMapper.GetDateTime(row, "DATE_INSCRIPTION"),
        Redoublant = DataRowMapper.GetBoolean(row, "REDOUBLANT"),
        Statut = DataRowMapper.GetString(row, "STATUT"),
        DateSortie = DataRowMapper.GetDateTime(row, "DATE_SORTIE"),
        MotifSortie = DataRowMapper.GetString(row, "MOTIF_SORTIE")
    };
}
