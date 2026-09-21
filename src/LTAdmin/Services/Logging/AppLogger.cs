using System.Text;

namespace LTAdmin.Services.Logging;

/// <summary>
/// Journal technique sur fichier (logs/ltadmin-AAAAMMJJ.log). Complète le journal
/// applicatif en base (table JOURNAL) : ici les erreurs techniques et la trace
/// de démarrage, là-bas les opérations métier par utilisateur.
/// </summary>
public sealed class AppLogger
{
    private readonly object _sync = new();
    private readonly string _logDirectory;

    public AppLogger() : this(DefaultLogDirectory())
    {
    }

    public AppLogger(string logDirectory)
    {
        _logDirectory = logDirectory;
    }

    public void Info(string message) => Write("INFO", message, null);

    public void Warning(string message) => Write("AVERT", message, null);

    public void Error(string operation, Exception exception)
        => Write("ERREUR", operation + " : " + exception.Message, exception.ToString());

    private void Write(string level, string message, string? detail)
    {
        try
        {
            Directory.CreateDirectory(_logDirectory);
            var file = Path.Combine(_logDirectory, $"ltadmin-{DateTime.Now:yyyyMMdd}.log");
            var line = new StringBuilder();
            line.Append(DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"));
            line.Append(" [").Append(level).Append("] ");
            line.AppendLine(message);
            if (!string.IsNullOrWhiteSpace(detail))
                line.AppendLine(detail);
            lock (_sync)
            {
                File.AppendAllText(file, line.ToString(), Encoding.UTF8);
            }
        }
        catch
        {
            // La journalisation ne doit jamais faire échouer l'application.
        }
    }

    private static string DefaultLogDirectory()
    {
        try
        {
            var directory = Path.Combine(AppContext.BaseDirectory, "logs");
            Directory.CreateDirectory(directory);
            return directory;
        }
        catch
        {
            return Path.Combine(Path.GetTempPath(), "LTAdmin-logs");
        }
    }
}
