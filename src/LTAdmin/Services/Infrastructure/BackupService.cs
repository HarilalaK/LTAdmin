using LTAdmin.Core;
using LTAdmin.Data;
using LTAdmin.Models.Dto;
using LTAdmin.Services.Common;
using LTAdmin.Services.Logging;
using LTAdmin.Services.Referentiel;

namespace LTAdmin.Services.Infrastructure;

/// <summary>
/// Sauvegardes du fichier LTA_ADM.accdb : copies horodatées dans le dossier
/// « Sauvegardes », inventaire, restauration explicite (avec copie de
/// sécurité préalable) et purge des anciennes copies. La restauration exige
/// une confirmation côté écran : elle remplace le fichier de travail.
/// </summary>
public sealed class BackupService : ServiceBase
{
    public BackupService(AccessDatabase database, AppLogger logger, JournalService journal, ParametreService parametres)
        : base(database, logger, journal, parametres)
    {
    }

    public string BackupsFolder
        => Path.Combine(Path.GetDirectoryName(Db.DatabasePath) ?? AppContext.BaseDirectory, "Sauvegardes");

    /// <summary>Crée une sauvegarde horodatée et retourne son chemin.</summary>
    public Result<string> CreateBackup(string codeUtr)
    {
        try
        {
            if (!File.Exists(Db.DatabasePath))
                return Result<string>.Fail("Base de données introuvable : " + Db.DatabasePath, ErrorCodes.NotFound);
            var destination = Db.CreateBackup();
            var size = new FileInfo(destination).Length;
            if (size == 0)
                return Result<string>.Fail("La sauvegarde créée est vide : vérifiez l’espace disque.", ErrorCodes.Technical);
            Journal.LogOperation(codeUtr, "SAUVEGARDE", null, null, Path.GetFileName(destination));
            Logger.Info("Sauvegarde créée : " + destination);
            return Result<string>.Ok(destination, "Sauvegarde créée : " + Path.GetFileName(destination));
        }
        catch (Exception ex) { return Failure<string>("Sauvegarde de la base", ex); }
    }

    public List<BackupInfo> ListBackups()
    {
        var result = new List<BackupInfo>();
        try
        {
            if (!Directory.Exists(BackupsFolder)) return result;
            foreach (var file in Directory.GetFiles(BackupsFolder, "LTA_ADM_*.accdb"))
            {
                try
                {
                    var info = new FileInfo(file);
                    result.Add(new BackupInfo
                    {
                        FilePath = info.FullName,
                        FileName = info.Name,
                        CreatedAt = info.CreationTime,
                        SizeBytes = info.Length
                    });
                }
                catch { /* Un fichier illisible ne bloque pas l'inventaire. */ }
            }
        }
        catch (Exception ex) { Logger.Error("Inventaire des sauvegardes", ex); }
        return result.OrderByDescending(b => b.CreatedAt).ToList();
    }

    /// <summary>
    /// Restaure une sauvegarde (action explicite irréversible côté données :
    /// une copie de sécurité du fichier courant est conservée avant écrasement).
    /// </summary>
    public Result RestoreBackup(string backupPath, string codeUtr)
    {
        try
        {
            if (string.IsNullOrWhiteSpace(backupPath) || !File.Exists(backupPath))
                return Result.Fail("Fichier de sauvegarde introuvable.", ErrorCodes.NotFound);
            if (!backupPath.EndsWith(".accdb", StringComparison.OrdinalIgnoreCase))
                return Result.Fail("Seuls les fichiers .accdb peuvent être restaurés.", ErrorCodes.Validation);
            if (string.Equals(Path.GetFullPath(backupPath), Path.GetFullPath(Db.DatabasePath), StringComparison.OrdinalIgnoreCase))
                return Result.Fail("Cette sauvegarde est le fichier de travail lui-même.", ErrorCodes.Validation);
            if (Db.InTransaction)
                return Result.Fail("Restauration impossible pendant une transaction.", ErrorCodes.BusinessRule);

            var livePath = Db.DatabasePath;
            Logger.Info($"Restauration demandée par {codeUtr} : {backupPath} -> {livePath}");

            var wasOpen = Db.IsOpen;
            Db.Close();
            try
            {
                // Copie de sécurité du fichier courant avant écrasement.
                if (File.Exists(livePath))
                {
                    Directory.CreateDirectory(BackupsFolder);
                    var safety = Path.Combine(BackupsFolder, $"LTA_ADM_avant_restauration_{DateTime.Now:yyyyMMdd_HHmmss}.accdb");
                    File.Copy(livePath, safety, overwrite: false);
                    Logger.Info("Copie de sécurité avant restauration : " + safety);
                }
                File.Copy(backupPath, livePath, overwrite: true);
            }
            finally
            {
                if (wasOpen) Db.Open();
            }

            Journal.LogOperation(codeUtr, "RESTAURATION", null, null, Path.GetFileName(backupPath));
            return Result.Ok("Base restaurée depuis : " + Path.GetFileName(backupPath));
        }
        catch (Exception ex) { return Failure("Restauration d’une sauvegarde", ex); }
    }

    /// <summary>Supprime les sauvegardes les plus anciennes au-delà du quota conservé.</summary>
    public Result<int> PurgeOldBackups(int keepCount, string codeUtr)
    {
        if (keepCount < 1)
            return Result<int>.Fail("Conservez au moins une sauvegarde.", ErrorCodes.Validation);
        try
        {
            var backups = ListBackups();
            var deleted = 0;
            foreach (var backup in backups.Skip(keepCount))
            {
                try
                {
                    File.Delete(backup.FilePath);
                    deleted++;
                }
                catch (Exception ex)
                {
                    Logger.Warning("Purge impossible pour " + backup.FileName + " : " + ex.Message);
                }
            }
            if (deleted > 0)
                Journal.LogOperation(codeUtr, "PURGE_SAUVEGARDES", null, null, $"{deleted} ancienne(s) sauvegarde(s) supprimée(s).");
            return Result<int>.Ok(deleted, deleted == 0 ? "Aucune sauvegarde à purger." : $"{deleted} sauvegarde(s) purgée(s).");
        }
        catch (Exception ex) { return Failure<int>("Purge des sauvegardes", ex); }
    }
}
