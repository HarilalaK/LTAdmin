using System.Data;
using LTAdmin.Data;
using LTAdmin.Models.Dto;
using LTAdmin.Models.Entities;

namespace LTAdmin.Repositories;

/// <summary>Dépôt du référentiel : filières, niveaux, salles, classes, modules, matières.</summary>
public sealed class ReferentielRepository : RepositoryBase
{
    public ReferentielRepository(AccessDatabase database) : base(database)
    {
    }

    // ----- FILIERE -----

    public List<Filiere> ListFilieres(bool activesSeulement = false)
        => activesSeulement
            ? QueryList($"SELECT * FROM {Q(Tables.Filiere)} WHERE {Q("ACTIVE")} = ? ORDER BY {Q("CODE_FILIERE")}", MapFiliere, P(true))
            : QueryList($"SELECT * FROM {Q(Tables.Filiere)} ORDER BY {Q("CODE_FILIERE")}", MapFiliere);

    public Filiere? GetFiliere(string code)
        => QuerySingle($"SELECT * FROM {Q(Tables.Filiere)} WHERE {Q("CODE_FILIERE")} = ?", MapFiliere, P(code));

    public void InsertFiliere(Filiere filiere)
        => Execute(
            $"INSERT INTO {Q(Tables.Filiere)} ({Q("CODE_FILIERE")}, {Q("FILIERE")}, {Q("DIPLOME")}, {Q("DUREE_ANS")}, {Q("ACTIVE")}) VALUES (?, ?, ?, ?, ?)",
            P(filiere.CodeFiliere), P(filiere.Libelle), P(filiere.Diplome), P(filiere.DureeAns), P(filiere.Active ?? true));

    public int UpdateFiliere(Filiere filiere)
        => Execute(
            $"UPDATE {Q(Tables.Filiere)} SET {Q("FILIERE")} = ?, {Q("DIPLOME")} = ?, {Q("DUREE_ANS")} = ?, {Q("ACTIVE")} = ? WHERE {Q("CODE_FILIERE")} = ?",
            P(filiere.Libelle), P(filiere.Diplome), P(filiere.DureeAns), P(filiere.Active ?? true), P(filiere.CodeFiliere));

    public int DeleteFiliere(string code)
        => Execute($"DELETE FROM {Q(Tables.Filiere)} WHERE {Q("CODE_FILIERE")} = ?", P(code));

    // ----- NIVEAU -----

    public List<Niveau> ListNiveaux()
        => QueryList($"SELECT * FROM {Q(Tables.Niveau)} ORDER BY {Q("ORDRE_NIV")}, {Q("CODE_NIVEAU")}", MapNiveau);

    public Niveau? GetNiveau(string code)
        => QuerySingle($"SELECT * FROM {Q(Tables.Niveau)} WHERE {Q("CODE_NIVEAU")} = ?", MapNiveau, P(code));

    public void InsertNiveau(Niveau niveau)
        => Execute(
            $"INSERT INTO {Q(Tables.Niveau)} ({Q("CODE_NIVEAU")}, {Q("NIVEAU")}, {Q("ORDRE_NIV")}) VALUES (?, ?, ?)",
            P(niveau.CodeNiveau), P(niveau.Libelle), P(niveau.OrdreNiv));

    public int UpdateNiveau(Niveau niveau)
        => Execute(
            $"UPDATE {Q(Tables.Niveau)} SET {Q("NIVEAU")} = ?, {Q("ORDRE_NIV")} = ? WHERE {Q("CODE_NIVEAU")} = ?",
            P(niveau.Libelle), P(niveau.OrdreNiv), P(niveau.CodeNiveau));

    public int DeleteNiveau(string code)
        => Execute($"DELETE FROM {Q(Tables.Niveau)} WHERE {Q("CODE_NIVEAU")} = ?", P(code));

    // ----- SALLE -----

    public List<Salle> ListSalles(bool disponiblesSeulement = false)
        => disponiblesSeulement
            ? QueryList($"SELECT * FROM {Q(Tables.Salle)} WHERE {Q("DISPONIBLE")} = ? ORDER BY {Q("NOM_SALLE")}", MapSalle, P(true))
            : QueryList($"SELECT * FROM {Q(Tables.Salle)} ORDER BY {Q("NOM_SALLE")}", MapSalle);

    public Salle? GetSalle(int idSalle)
        => QuerySingle($"SELECT * FROM {Q(Tables.Salle)} WHERE {Q("ID_SALLE")} = ?", MapSalle, P(idSalle));

    public int InsertSalle(Salle salle)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.Salle)} ({Q("NOM_SALLE")}, {Q("CAPACITE")}, {Q("NATURE_SALLE")}, {Q("DISPONIBLE")}) VALUES (?, ?, ?, ?)",
            P(salle.NomSalle), P(salle.Capacite), P(salle.NatureSalle), P(salle.Disponible ?? true));

    public int UpdateSalle(Salle salle)
        => Execute(
            $"UPDATE {Q(Tables.Salle)} SET {Q("NOM_SALLE")} = ?, {Q("CAPACITE")} = ?, {Q("NATURE_SALLE")} = ?, {Q("DISPONIBLE")} = ? WHERE {Q("ID_SALLE")} = ?",
            P(salle.NomSalle), P(salle.Capacite), P(salle.NatureSalle), P(salle.Disponible ?? true), P(salle.IdSalle));

    public int DeleteSalle(int idSalle)
        => Execute($"DELETE FROM {Q(Tables.Salle)} WHERE {Q("ID_SALLE")} = ?", P(idSalle));

    // ----- CLASSE -----

    public List<Classe> ListClasses(int? idAnnee = null)
        => idAnnee.HasValue
            ? QueryList($"SELECT * FROM {Q(Tables.Classe)} WHERE {Q("ID_ANNEE")} = ? ORDER BY {Q("LIBELLE")}", MapClasse, P(idAnnee.Value))
            : QueryList($"SELECT * FROM {Q(Tables.Classe)} ORDER BY {Q("LIBELLE")}", MapClasse);

    public Classe? GetClasse(int idClasse)
        => QuerySingle($"SELECT * FROM {Q(Tables.Classe)} WHERE {Q("ID_CLASSE")} = ?", MapClasse, P(idClasse));

    public ClasseDetail? GetClasseDetail(int idClasse)
        => QuerySingle(ClasseDetailSql() + $" WHERE C.{Q("ID_CLASSE")} = ?", MapClasseDetail, P(idClasse));

    public List<ClasseDetail> ListClassesDetail(int? idAnnee = null)
        => idAnnee.HasValue
            ? QueryList(ClasseDetailSql() + $" WHERE C.{Q("ID_ANNEE")} = ? ORDER BY C.{Q("LIBELLE")}", MapClasseDetail, P(idAnnee.Value))
            : QueryList(ClasseDetailSql() + $" ORDER BY C.{Q("LIBELLE")}", MapClasseDetail);

    private static string ClasseDetailSql()
        => $"SELECT C.*, A.{Q("LIBELLE")} AS ANNEE_LIB, F.{Q("FILIERE")} AS FILIERE_LIB, " +
           $"N.{Q("NIVEAU")} AS NIVEAU_LIB, S.{Q("NOM_SALLE")} AS SALLE_LIB " +
           $"FROM (((({Q(Tables.Classe)} AS C " +
           $"LEFT JOIN {Q(Tables.AnneeScolaire)} AS A ON C.{Q("ID_ANNEE")} = A.{Q("ID_ANNEE")}) " +
           $"LEFT JOIN {Q(Tables.Filiere)} AS F ON C.{Q("CODE_FILIERE")} = F.{Q("CODE_FILIERE")}) " +
           $"LEFT JOIN {Q(Tables.Niveau)} AS N ON C.{Q("CODE_NIVEAU")} = N.{Q("CODE_NIVEAU")}) " +
           $"LEFT JOIN {Q(Tables.Salle)} AS S ON C.{Q("ID_SALLE")} = S.{Q("ID_SALLE")})";

    public int InsertClasse(Classe classe)
        => InsertAndGetId(
            $"INSERT INTO {Q(Tables.Classe)} ({Q("LIBELLE")}, {Q("ID_ANNEE")}, {Q("CODE_FILIERE")}, {Q("CODE_NIVEAU")}, {Q("ID_SALLE")}, {Q("EFFECTIF_MAX")}, {Q("ID_RESPONSABLE")}) VALUES (?, ?, ?, ?, ?, ?, ?)",
            P(classe.Libelle), P(classe.IdAnnee), P(classe.CodeFiliere), P(classe.CodeNiveau),
            P(classe.IdSalle), P(classe.EffectifMax), P(classe.IdResponsable));

    public int UpdateClasse(Classe classe)
        => Execute(
            $"UPDATE {Q(Tables.Classe)} SET {Q("LIBELLE")} = ?, {Q("ID_ANNEE")} = ?, {Q("CODE_FILIERE")} = ?, {Q("CODE_NIVEAU")} = ?, {Q("ID_SALLE")} = ?, {Q("EFFECTIF_MAX")} = ?, {Q("ID_RESPONSABLE")} = ? WHERE {Q("ID_CLASSE")} = ?",
            P(classe.Libelle), P(classe.IdAnnee), P(classe.CodeFiliere), P(classe.CodeNiveau),
            P(classe.IdSalle), P(classe.EffectifMax), P(classe.IdResponsable), P(classe.IdClasse));

    public int DeleteClasse(int idClasse)
        => Execute($"DELETE FROM {Q(Tables.Classe)} WHERE {Q("ID_CLASSE")} = ?", P(idClasse));

    public int CountInscrits(int idClasse)
        => ScalarInt($"SELECT COUNT(*) FROM {Q(Tables.Inscription)} WHERE {Q("ID_CLASSE")} = ?", P(idClasse));

    // ----- MODULE_FORMATION -----

    public List<ModuleFormation> ListModules(string? codeFiliere = null)
        => string.IsNullOrWhiteSpace(codeFiliere)
            ? QueryList($"SELECT * FROM {Q(Tables.ModuleFormation)} ORDER BY {Q("CODE_MODULE")}", MapModule)
            : QueryList($"SELECT * FROM {Q(Tables.ModuleFormation)} WHERE {Q("CODE_FILIERE")} = ? ORDER BY {Q("CODE_MODULE")}", MapModule, P(codeFiliere));

    public ModuleFormation? GetModule(string code)
        => QuerySingle($"SELECT * FROM {Q(Tables.ModuleFormation)} WHERE {Q("CODE_MODULE")} = ?", MapModule, P(code));

    public void InsertModule(ModuleFormation module)
        => Execute(
            $"INSERT INTO {Q(Tables.ModuleFormation)} ({Q("CODE_MODULE")}, {Q("MODULE_LIB")}, {Q("CODE_FILIERE")}) VALUES (?, ?, ?)",
            P(module.CodeModule), P(module.ModuleLib), P(module.CodeFiliere));

    public int UpdateModule(ModuleFormation module)
        => Execute(
            $"UPDATE {Q(Tables.ModuleFormation)} SET {Q("MODULE_LIB")} = ?, {Q("CODE_FILIERE")} = ? WHERE {Q("CODE_MODULE")} = ?",
            P(module.ModuleLib), P(module.CodeFiliere), P(module.CodeModule));

    public int DeleteModule(string code)
        => Execute($"DELETE FROM {Q(Tables.ModuleFormation)} WHERE {Q("CODE_MODULE")} = ?", P(code));

    // ----- MATIERE -----

    public List<Matiere> ListMatieres(string? codeModule = null)
        => string.IsNullOrWhiteSpace(codeModule)
            ? QueryList($"SELECT * FROM {Q(Tables.Matiere)} ORDER BY {Q("ORDRE_MAT")}, {Q("CODE_MATIERE")}", MapMatiere)
            : QueryList($"SELECT * FROM {Q(Tables.Matiere)} WHERE {Q("CODE_MODULE")} = ? ORDER BY {Q("ORDRE_MAT")}, {Q("CODE_MATIERE")}", MapMatiere, P(codeModule));

    public Matiere? GetMatiere(string code)
        => QuerySingle($"SELECT * FROM {Q(Tables.Matiere)} WHERE {Q("CODE_MATIERE")} = ?", MapMatiere, P(code));

    public void InsertMatiere(Matiere matiere)
        => Execute(
            $"INSERT INTO {Q(Tables.Matiere)} ({Q("CODE_MATIERE")}, {Q("MATIERE")}, {Q("CODE_MODULE")}, {Q("NATURE")}, {Q("ORDRE_MAT")}) VALUES (?, ?, ?, ?, ?)",
            P(matiere.CodeMatiere), P(matiere.Libelle), P(matiere.CodeModule), P(matiere.Nature), P(matiere.OrdreMat));

    public int UpdateMatiere(Matiere matiere)
        => Execute(
            $"UPDATE {Q(Tables.Matiere)} SET {Q("MATIERE")} = ?, {Q("CODE_MODULE")} = ?, {Q("NATURE")} = ?, {Q("ORDRE_MAT")} = ? WHERE {Q("CODE_MATIERE")} = ?",
            P(matiere.Libelle), P(matiere.CodeModule), P(matiere.Nature), P(matiere.OrdreMat), P(matiere.CodeMatiere));

    public int DeleteMatiere(string code)
        => Execute($"DELETE FROM {Q(Tables.Matiere)} WHERE {Q("CODE_MATIERE")} = ?", P(code));

    // ----- Mappers -----

    public static Filiere MapFiliere(DataRow row) => new()
    {
        CodeFiliere = DataRowMapper.GetString(row, "CODE_FILIERE"),
        Libelle = DataRowMapper.GetString(row, "FILIERE"),
        Diplome = DataRowMapper.GetString(row, "DIPLOME"),
        DureeAns = DataRowMapper.GetInt32(row, "DUREE_ANS"),
        Active = DataRowMapper.GetBoolean(row, "ACTIVE")
    };

    public static Niveau MapNiveau(DataRow row) => new()
    {
        CodeNiveau = DataRowMapper.GetString(row, "CODE_NIVEAU"),
        Libelle = DataRowMapper.GetString(row, "NIVEAU"),
        OrdreNiv = DataRowMapper.GetInt32(row, "ORDRE_NIV")
    };

    public static Salle MapSalle(DataRow row) => new()
    {
        IdSalle = DataRowMapper.GetInt32(row, "ID_SALLE"),
        NomSalle = DataRowMapper.GetString(row, "NOM_SALLE"),
        Capacite = DataRowMapper.GetInt32(row, "CAPACITE"),
        NatureSalle = DataRowMapper.GetString(row, "NATURE_SALLE"),
        Disponible = DataRowMapper.GetBoolean(row, "DISPONIBLE")
    };

    public static Classe MapClasse(DataRow row) => new()
    {
        IdClasse = DataRowMapper.GetInt32(row, "ID_CLASSE"),
        Libelle = DataRowMapper.GetString(row, "LIBELLE"),
        IdAnnee = DataRowMapper.GetInt32(row, "ID_ANNEE"),
        CodeFiliere = DataRowMapper.GetString(row, "CODE_FILIERE"),
        CodeNiveau = DataRowMapper.GetString(row, "CODE_NIVEAU"),
        IdSalle = DataRowMapper.GetInt32(row, "ID_SALLE"),
        EffectifMax = DataRowMapper.GetInt32(row, "EFFECTIF_MAX"),
        IdResponsable = DataRowMapper.GetInt32(row, "ID_RESPONSABLE")
    };

    public static ClasseDetail MapClasseDetail(DataRow row) => new()
    {
        IdClasse = DataRowMapper.GetInt32(row, "ID_CLASSE"),
        Libelle = DataRowMapper.GetString(row, "LIBELLE"),
        IdAnnee = DataRowMapper.GetInt32(row, "ID_ANNEE"),
        Annee = DataRowMapper.GetString(row, "ANNEE_LIB"),
        CodeFiliere = DataRowMapper.GetString(row, "CODE_FILIERE"),
        Filiere = DataRowMapper.GetString(row, "FILIERE_LIB"),
        CodeNiveau = DataRowMapper.GetString(row, "CODE_NIVEAU"),
        Niveau = DataRowMapper.GetString(row, "NIVEAU_LIB"),
        IdSalle = DataRowMapper.GetInt32(row, "ID_SALLE"),
        Salle = DataRowMapper.GetString(row, "SALLE_LIB"),
        EffectifMax = DataRowMapper.GetInt32(row, "EFFECTIF_MAX")
    };

    public static ModuleFormation MapModule(DataRow row) => new()
    {
        CodeModule = DataRowMapper.GetString(row, "CODE_MODULE"),
        ModuleLib = DataRowMapper.GetString(row, "MODULE_LIB"),
        CodeFiliere = DataRowMapper.GetString(row, "CODE_FILIERE")
    };

    public static Matiere MapMatiere(DataRow row) => new()
    {
        CodeMatiere = DataRowMapper.GetString(row, "CODE_MATIERE"),
        Libelle = DataRowMapper.GetString(row, "MATIERE"),
        CodeModule = DataRowMapper.GetString(row, "CODE_MODULE"),
        Nature = DataRowMapper.GetString(row, "NATURE"),
        OrdreMat = DataRowMapper.GetInt32(row, "ORDRE_MAT")
    };
}
