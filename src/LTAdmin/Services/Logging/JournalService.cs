using LTAdmin.Data;
using LTAdmin.Models.Entities;
using LTAdmin.Repositories;

namespace LTAdmin.Services.Logging;

/// <summary>
/// Journal applicatif en base (table JOURNAL) : qui a fait quoi, quand, sur quoi.
/// Toutes les écritures sont « au mieux » : un échec de journalisation est
/// tracé dans le fichier technique mais ne fait jamais échouer l'opération.
/// </summary>
public sealed class JournalService
{
    private readonly AdminRepository _admin;
    private readonly AppLogger _logger;

    public JournalService(AccessDatabase database, AppLogger logger)
    {
        _admin = new AdminRepository(database);
        _logger = logger;
    }

    public void Log(string? codeUtr, string action, string? tableCible = null, int? idCible = null, string? detail = null)
    {
        try
        {
            _admin.InsertJournal(new JournalEntry
            {
                DateLog = DateTime.Now,
                CodeUtr = string.IsNullOrWhiteSpace(codeUtr) ? null : codeUtr.Trim(),
                ActionLog = Truncate(action, 80),
                TableCible = string.IsNullOrWhiteSpace(tableCible) ? null : Truncate(tableCible, 80),
                IdCible = idCible,
                Detail = detail
            });
        }
        catch (Exception ex)
        {
            _logger.Warning("Journalisation impossible (" + action + ") : " + ex.Message);
        }
    }

    public void LogConnexion(string codeUtr, bool reussie)
        => Log(codeUtr, reussie ? "CONNEXION" : "CONNEXION_REFUSEE",
            Tables.Utilisateur, null, reussie ? "Ouverture de session." : "Identifiant ou mot de passe incorrect.");

    public void LogCreation(string codeUtr, string table, int? id, string? detail = null)
        => Log(codeUtr, "CREATION", table, id, detail);

    public void LogModification(string codeUtr, string table, int? id, string? detail = null)
        => Log(codeUtr, "MODIFICATION", table, id, detail);

    public void LogSuppression(string codeUtr, string table, int? id, string? detail = null)
        => Log(codeUtr, "SUPPRESSION", table, id, detail);

    public void LogOperation(string codeUtr, string operation, string? table, int? id, string? detail = null)
        => Log(codeUtr, operation, table, id, detail);

    public List<JournalEntry> Consulter(DateTime? depuis, string? codeUtr, string? action, int maxRows = 500)
    {
        try { return _admin.ListJournal(depuis, codeUtr, action, maxRows); }
        catch (Exception ex)
        {
            _logger.Error("Consultation du journal", ex);
            return new List<JournalEntry>();
        }
    }

    private static string Truncate(string value, int maxLength)
        => value.Length <= maxLength ? value : value.Substring(0, maxLength);
}
