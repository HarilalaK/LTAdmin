using System.Globalization;
using LTAdmin.Core;
using LTAdmin.Data;
using LTAdmin.Repositories;
using LTAdmin.Services.Logging;

namespace LTAdmin.Services.Referentiel;

/// <summary>
/// Accès typé aux règles de gestion de la table PARAMETRE (valeurs stockées
/// en texte dans Access). Les valeurs sont mises en cache et rechargées à
/// chaque modification explicite. En cas de valeur absente ou illisible,
/// les défauts documentés de la base sont utilisés.
/// </summary>
public sealed class ParametreService
{
    private readonly AdminRepository _admin;
    private readonly JournalService _journal;
    private readonly AppLogger _logger;
    private Dictionary<string, string> _cache = new(StringComparer.OrdinalIgnoreCase);
    private bool _loaded;

    public ParametreService(AccessDatabase database, JournalService journal, AppLogger logger)
    {
        _admin = new AdminRepository(database);
        _journal = journal;
        _logger = logger;
    }

    public double BaremeDefaut => GetDouble(ParametreKeys.BaremeDefaut, 20d);
    public double MoyAdmission => GetDouble(ParametreKeys.MoyAdmission, 10d);
    public double NoteEliminatoire => GetDouble(ParametreKeys.NoteEliminatoire, 5d);
    public double PoidsCc => GetDouble(ParametreKeys.PoidsCc, 40d);
    public double PoidsExamen => GetDouble(ParametreKeys.PoidsExamen, 60d);
    public double SeuilAbsence => GetDouble(ParametreKeys.SeuilAbsence, 30d);
    public string Devise => GetString(ParametreKeys.Devise, "MGA");

    public IReadOnlyDictionary<string, string> GetAll()
    {
        EnsureLoaded();
        return _cache;
    }

    public string GetString(string cle, string defaut)
    {
        EnsureLoaded();
        return _cache.TryGetValue(cle, out var valeur) && !string.IsNullOrWhiteSpace(valeur)
            ? valeur.Trim() : defaut;
    }

    public double GetDouble(string cle, double defaut)
    {
        var text = GetString(cle, string.Empty).Replace(',', '.');
        return double.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out var value)
            ? value : defaut;
    }

    /// <summary>Modifie une règle de gestion (action explicite, journalisée).</summary>
    public Result SetValue(string cle, string valeur, string codeUtr)
    {
        if (string.IsNullOrWhiteSpace(cle))
            return Result.Fail("Clé de paramètre obligatoire.", ErrorCodes.Validation);
        if ((valeur ?? string.Empty).Length > 510)
            return Result.Fail("Valeur trop longue (510 caractères maximum).", ErrorCodes.Validation);

        try
        {
            var updated = _admin.UpdateValeur(cle.Trim(), (valeur ?? string.Empty).Trim());
            if (updated == 0)
                return Result.Fail($"Paramètre « {cle} » introuvable.", ErrorCodes.NotFound);
            Invalidate();
            _journal.LogModification(codeUtr, Tables.Parametre, null, $"{cle} = {valeur}");
            return Result.Ok("Paramètre enregistré.");
        }
        catch (Exception ex)
        {
            var error = OleDbExceptionHelper.Interpret(ex);
            _logger.Error("Modification de paramètre", ex);
            return Result.Fail(error.Message, error.Code);
        }
    }

    public void Invalidate()
    {
        _loaded = false;
        _cache = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
    }

    private void EnsureLoaded()
    {
        if (_loaded) return;
        try
        {
            foreach (var parametre in _admin.ListParametres())
            {
                if (!string.IsNullOrWhiteSpace(parametre.Cle))
                    _cache[parametre.Cle!] = parametre.Valeur ?? string.Empty;
            }
        }
        catch (Exception ex)
        {
            _logger.Error("Chargement des paramètres", ex);
        }
        _loaded = true;
    }
}
