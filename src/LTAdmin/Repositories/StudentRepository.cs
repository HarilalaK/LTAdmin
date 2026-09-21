using System.Data;
using LTAdmin.Data;
using LTAdmin.Models.Entities;

namespace LTAdmin.Repositories;

/// <summary>Dépôt des dossiers étudiants (table ETUDIANT).</summary>
public sealed class StudentRepository : RepositoryBase
{
    public StudentRepository(AccessDatabase database) : base(database)
    {
    }

    public Etudiant? GetById(int idEtudiant)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.Etudiant)} WHERE {Q("ID_ETUDIANT")} = ?",
            MapEtudiant, P(idEtudiant));

    public Etudiant? GetByMatricule(string matricule)
        => QuerySingle(
            $"SELECT * FROM {Q(Tables.Etudiant)} WHERE {Q("MATRICULE")} = ?",
            MapEtudiant, P(matricule));

    public List<Etudiant> Search(string? recherche, int maxRows = 500)
    {
        if (string.IsNullOrWhiteSpace(recherche))
            return QueryList(
                $"SELECT TOP {Math.Clamp(maxRows, 1, 5000)} * FROM {Q(Tables.Etudiant)} ORDER BY {Q("NOM")}, {Q("PRENOM")}",
                MapEtudiant);
        var motif = "%" + recherche.Trim() + "%";
        return QueryList(
            $"SELECT TOP {Math.Clamp(maxRows, 1, 5000)} * FROM {Q(Tables.Etudiant)} " +
            $"WHERE {Q("NOM")} LIKE ? OR {Q("PRENOM")} LIKE ? OR {Q("MATRICULE")} LIKE ? " +
            $"ORDER BY {Q("NOM")}, {Q("PRENOM")}",
            MapEtudiant, P(motif), P(motif), P(motif));
    }

    public int Count() => ScalarInt($"SELECT COUNT(*) FROM {Q(Tables.Etudiant)}");

    public bool MatriculeExiste(string matricule)
        => Exists($"SELECT COUNT(*) FROM {Q(Tables.Etudiant)} WHERE {Q("MATRICULE")} = ?", P(matricule));

    public List<string> ListMatricules(string prefixe)
    {
        var table = QueryTable(
            $"SELECT {Q("MATRICULE")} FROM {Q(Tables.Etudiant)} WHERE {Q("MATRICULE")} LIKE ?",
            P(prefixe + "%"));
        var result = new List<string>(table.Rows.Count);
        foreach (DataRow row in table.Rows)
        {
            var value = DataRowMapper.GetString(row, "MATRICULE");
            if (!string.IsNullOrWhiteSpace(value)) result.Add(value);
        }
        return result;
    }

    public int Insert(Etudiant etudiant)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.Etudiant)} ({Q("MATRICULE")}, {Q("NOM")}, {Q("PRENOM")}, {Q("SEXE")}, " +
            $"{Q("DATE_NAISSANCE")}, {Q("LIEU_NAISSANCE")}, {Q("CIN")}, {Q("NATIONALITE")}, {Q("ADRESSE")}, " +
            $"{Q("TEL")}, {Q("EMAIL")}, {Q("NOM_TUTEUR")}, {Q("TEL_TUTEUR")}, {Q("PROFESSION_TUTEUR")}, " +
            $"{Q("SERIE_BACC")}, {Q("ANNEE_BACC")}, {Q("ETAB_ORIGINE")}, {Q("PHOTO")}, {Q("DATE_CREATION")}, {Q("STATUT")}) " +
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            P(etudiant.Matricule), P(etudiant.Nom), P(etudiant.Prenom), P(etudiant.Sexe),
            P(etudiant.DateNaissance), P(etudiant.LieuNaissance), P(etudiant.Cin), P(etudiant.Nationalite),
            P(etudiant.Adresse), P(etudiant.Tel), P(etudiant.Email), P(etudiant.NomTuteur),
            P(etudiant.TelTuteur), P(etudiant.ProfessionTuteur), P(etudiant.SerieBacc),
            P(etudiant.AnneeBacc), P(etudiant.EtabOrigine), P(etudiant.Photo),
            P(etudiant.DateCreation), P(etudiant.Statut));

    public int Update(Etudiant etudiant)
        => Execute(
            $"UPDATE {Q(Tables.Etudiant)} SET {Q("MATRICULE")} = ?, {Q("NOM")} = ?, {Q("PRENOM")} = ?, {Q("SEXE")} = ?, " +
            $"{Q("DATE_NAISSANCE")} = ?, {Q("LIEU_NAISSANCE")} = ?, {Q("CIN")} = ?, {Q("NATIONALITE")} = ?, {Q("ADRESSE")} = ?, " +
            $"{Q("TEL")} = ?, {Q("EMAIL")} = ?, {Q("NOM_TUTEUR")} = ?, {Q("TEL_TUTEUR")} = ?, {Q("PROFESSION_TUTEUR")} = ?, " +
            $"{Q("SERIE_BACC")} = ?, {Q("ANNEE_BACC")} = ?, {Q("ETAB_ORIGINE")} = ?, {Q("PHOTO")} = ?, {Q("STATUT")} = ? " +
            $"WHERE {Q("ID_ETUDIANT")} = ?",
            P(etudiant.Matricule), P(etudiant.Nom), P(etudiant.Prenom), P(etudiant.Sexe),
            P(etudiant.DateNaissance), P(etudiant.LieuNaissance), P(etudiant.Cin), P(etudiant.Nationalite),
            P(etudiant.Adresse), P(etudiant.Tel), P(etudiant.Email), P(etudiant.NomTuteur),
            P(etudiant.TelTuteur), P(etudiant.ProfessionTuteur), P(etudiant.SerieBacc),
            P(etudiant.AnneeBacc), P(etudiant.EtabOrigine), P(etudiant.Photo),
            P(etudiant.Statut), P(etudiant.IdEtudiant));

    public int Delete(int idEtudiant)
        => Execute($"DELETE FROM {Q(Tables.Etudiant)} WHERE {Q("ID_ETUDIANT")} = ?", P(idEtudiant));

    public static Etudiant MapEtudiant(DataRow row) => new()
    {
        IdEtudiant = DataRowMapper.GetInt32(row, "ID_ETUDIANT"),
        Matricule = DataRowMapper.GetString(row, "MATRICULE"),
        Nom = DataRowMapper.GetString(row, "NOM"),
        Prenom = DataRowMapper.GetString(row, "PRENOM"),
        Sexe = DataRowMapper.GetString(row, "SEXE"),
        DateNaissance = DataRowMapper.GetDateTime(row, "DATE_NAISSANCE"),
        LieuNaissance = DataRowMapper.GetString(row, "LIEU_NAISSANCE"),
        Cin = DataRowMapper.GetString(row, "CIN"),
        Nationalite = DataRowMapper.GetString(row, "NATIONALITE"),
        Adresse = DataRowMapper.GetString(row, "ADRESSE"),
        Tel = DataRowMapper.GetString(row, "TEL"),
        Email = DataRowMapper.GetString(row, "EMAIL"),
        NomTuteur = DataRowMapper.GetString(row, "NOM_TUTEUR"),
        TelTuteur = DataRowMapper.GetString(row, "TEL_TUTEUR"),
        ProfessionTuteur = DataRowMapper.GetString(row, "PROFESSION_TUTEUR"),
        SerieBacc = DataRowMapper.GetString(row, "SERIE_BACC"),
        AnneeBacc = DataRowMapper.GetInt32(row, "ANNEE_BACC"),
        EtabOrigine = DataRowMapper.GetString(row, "ETAB_ORIGINE"),
        Photo = DataRowMapper.GetString(row, "PHOTO"),
        DateCreation = DataRowMapper.GetDateTime(row, "DATE_CREATION"),
        Statut = DataRowMapper.GetString(row, "STATUT")
    };
}
