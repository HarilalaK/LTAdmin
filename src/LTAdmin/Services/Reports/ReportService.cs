using System.Data;
using LTAdmin.Core;
using LTAdmin.Data;
using LTAdmin.Services.Common;
using LTAdmin.Services.Logging;
using LTAdmin.Services.Referentiel;

namespace LTAdmin.Services.Reports;

/// <summary>Définition d'un état adossé à une requête Access enregistrée.</summary>
public sealed record ReportDefinition(
    string Name,
    string Title,
    string Description,
    bool FilterByClasse,
    bool FilterByPeriode,
    bool ClasseIsId,
    bool PeriodeIsId);

/// <summary>Filtres optionnels d'un état (classe et/ou période).</summary>
public sealed class ReportFilter
{
    public int? IdClasse { get; set; }
    public string? ClasseLibelle { get; set; }
    public int? IdPeriode { get; set; }
    public string? PeriodeLibelle { get; set; }
}

/// <summary>
/// États et requêtes : exécute les 8 requêtes Access livrées avec la base,
/// avec filtres optionnels classe / période et export CSV.
/// Note de compatibilité OleDb : R_SITUATION_ECOLAGE utilise la fonction VBA
/// Nz(), indisponible hors Access — en cas d'échec, un SQL équivalent basé
/// sur IIf()/IsNull() (fonctions du moteur, utilisables via OleDb) est rejoué.
/// </summary>
public sealed class ReportService : ServiceBase
{
    private static readonly List<ReportDefinition> Catalog = new()
    {
        new ReportDefinition(SavedQueries.ListeEtudiant, "Liste des étudiants",
            "Inscrits avec classe, filière, niveau et année.", true, false, false, false),
        new ReportDefinition(SavedQueries.MoyenneMatiere, "Moyennes par matière",
            "Moyennes sur 20 par matière et par période (barèmes hétérogènes gérés).", true, true, true, true),
        new ReportDefinition(SavedQueries.MoyennePeriode, "Moyennes par période",
            "Moyennes générales pondérées par les coefficients.", true, true, true, true),
        new ReportDefinition(SavedQueries.BulletinDetail, "Détail des bulletins",
            "Contenu imprimable des bulletins : lignes matières, moyennes, rangs.", true, true, false, false),
        new ReportDefinition(SavedQueries.PaiementEcheance, "Paiements par échéance",
            "Total payé et dernier paiement de chaque échéance.", false, false, false, false),
        new ReportDefinition(SavedQueries.SituationEcolage, "Situation d’écolage",
            "Dû / payé / reste par étudiant.", true, false, false, false),
        new ReportDefinition(SavedQueries.EdtClasse, "Emplois du temps",
            "Grille hebdomadaire par classe (slots actifs).", true, false, false, false),
        new ReportDefinition(SavedQueries.AbsenceEtudiant, "Absences par étudiant",
            "Heures d’absence totales et justifiées.", true, false, false, false)
    };

    public ReportService(AccessDatabase database, AppLogger logger, JournalService journal, ParametreService parametres)
        : base(database, logger, journal, parametres)
    {
    }

    public IReadOnlyList<ReportDefinition> ListReports() => Catalog;

    public ReportDefinition? GetDefinition(string name)
        => Catalog.FirstOrDefault(d => string.Equals(d.Name, name, StringComparison.OrdinalIgnoreCase));

    /// <summary>Exécute un état avec ses filtres et retourne les lignes.</summary>
    public Result<DataTable> GetReportData(string name, ReportFilter? filter = null)
    {
        var definition = GetDefinition(name);
        if (definition is null)
            return Result<DataTable>.Fail($"État « {name} » introuvable.", ErrorCodes.NotFound);
        filter ??= new ReportFilter();

        try
        {
            var table = ExecuteSavedQuery(definition, filter);
            return Result<DataTable>.Ok(table, $"{table.Rows.Count:N0} ligne(s).");
        }
        catch (Exception ex)
        {
            // Repli documenté pour R_SITUATION_ECOLAGE (Nz indisponible via OleDb).
            if (string.Equals(definition.Name, SavedQueries.SituationEcolage, StringComparison.OrdinalIgnoreCase))
            {
                try
                {
                    Logger.Warning("R_SITUATION_ECOLAGE via OleDb impossible (« " + ex.Message + " ») : repli sur SQL équivalent.");
                    var table = ExecuteSituationFallback(filter);
                    return Result<DataTable>.Ok(table, $"{table.Rows.Count:N0} ligne(s).");
                }
                catch (Exception fallbackEx)
                {
                    return Failure<DataTable>("État « Situation d’écolage »", fallbackEx);
                }
            }
            return Failure<DataTable>($"État « {definition.Title} »", ex);
        }
    }

    public Result ExportCsv(string name, ReportFilter? filter, string filePath)
    {
        var data = GetReportData(name, filter);
        if (data.IsFailure || data.Value is null)
            return Result.Fail(data.FullMessage(), data.Code);
        try
        {
            CsvExporter.Export(data.Value, filePath);
            return Result.Ok("Export CSV terminé.");
        }
        catch (Exception ex)
        {
            Logger.Error("Export CSV d’un état", ex);
            return Result.Fail("Exportation impossible : " + ex.Message, ErrorCodes.Technical);
        }
    }

    private DataTable ExecuteSavedQuery(ReportDefinition definition, ReportFilter filter)
    {
        var conditions = new List<string>();
        var parameters = new List<System.Data.OleDb.OleDbParameter>();

        if (definition.FilterByClasse)
        {
            if (definition.ClasseIsId && filter.IdClasse.HasValue)
            {
                conditions.Add($"{Q("ID_CLASSE")} = ?");
                parameters.Add(P(filter.IdClasse.Value));
            }
            else if (!definition.ClasseIsId && !string.IsNullOrWhiteSpace(filter.ClasseLibelle))
            {
                conditions.Add($"{Q("CLASSE")} = ?");
                parameters.Add(P(filter.ClasseLibelle));
            }
        }
        if (definition.FilterByPeriode)
        {
            if (definition.PeriodeIsId && filter.IdPeriode.HasValue)
            {
                conditions.Add($"{Q("ID_PERIODE")} = ?");
                parameters.Add(P(filter.IdPeriode.Value));
            }
            else if (!definition.PeriodeIsId && !string.IsNullOrWhiteSpace(filter.PeriodeLibelle))
            {
                conditions.Add($"{Q("PERIODE")} = ?");
                parameters.Add(P(filter.PeriodeLibelle));
            }
        }

        var sql = $"SELECT * FROM {Q(definition.Name)}";
        if (conditions.Count > 0) sql += " WHERE " + string.Join(" AND ", conditions);
        return Db.Query(sql, parameters);
    }

    private DataTable ExecuteSituationFallback(ReportFilter filter)
    {
        var sql =
            $"SELECT E.{Q("MATRICULE")}, E.{Q("NOM")}, E.{Q("PRENOM")}, C.{Q("LIBELLE")} AS CLASSE, I.{Q("ID_INSCRIPTION")}, " +
            $"SUM(ECH.{Q("MONTANT_DU")} - IIf(ECH.{Q("REMISE")} IS NULL, 0, ECH.{Q("REMISE")})) AS TOTAL_DU, " +
            $"SUM(IIf(PE.{Q("TOTAL_PAYE")} IS NULL, 0, PE.{Q("TOTAL_PAYE")})) AS TOTAL_PAYE, " +
            $"SUM(ECH.{Q("MONTANT_DU")} - IIf(ECH.{Q("REMISE")} IS NULL, 0, ECH.{Q("REMISE")})) " +
            $"- SUM(IIf(PE.{Q("TOTAL_PAYE")} IS NULL, 0, PE.{Q("TOTAL_PAYE")})) AS RESTE " +
            $"FROM (((( {Q(Tables.Echeancier)} AS ECH " +
            $"LEFT JOIN {Q(SavedQueries.PaiementEcheance)} AS PE ON ECH.{Q("ID_ECHEANCE")} = PE.{Q("ID_ECHEANCE")}) " +
            $"INNER JOIN {Q(Tables.Inscription)} AS I ON ECH.{Q("ID_INSCRIPTION")} = I.{Q("ID_INSCRIPTION")}) " +
            $"INNER JOIN {Q(Tables.Etudiant)} AS E ON I.{Q("ID_ETUDIANT")} = E.{Q("ID_ETUDIANT")}) " +
            $"INNER JOIN {Q(Tables.Classe)} AS C ON I.{Q("ID_CLASSE")} = C.{Q("ID_CLASSE")}) ";
        var parameters = new List<System.Data.OleDb.OleDbParameter>();
        if (!string.IsNullOrWhiteSpace(filter.ClasseLibelle))
        {
            sql += $"WHERE C.{Q("LIBELLE")} = ? ";
            parameters.Add(P(filter.ClasseLibelle));
        }
        sql += $"GROUP BY E.{Q("MATRICULE")}, E.{Q("NOM")}, E.{Q("PRENOM")}, C.{Q("LIBELLE")}, I.{Q("ID_INSCRIPTION")}";
        return Db.Query(sql, parameters);
    }

    private static string Q(string identifier) => AccessDatabase.QuoteIdentifier(identifier);

    private static System.Data.OleDb.OleDbParameter P(object? value) => AccessDatabase.Parameter(value);
}
