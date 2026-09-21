namespace LTAdmin.Services.Infrastructure;

/// <summary>
/// Localise le fichier LTA_ADM.accdb : argument de ligne de commande,
/// variable d'environnement LTADMIN_DB, dossier de l'application, dossier
/// courant, puis parents (utile depuis bin\Debug\net8.0-windows du dépôt).
/// </summary>
public static class DatabaseLocator
{
    public static string? Find(string? requestedPath = null)
    {
        var candidates = new List<string>();
        if (!string.IsNullOrWhiteSpace(requestedPath)) candidates.Add(requestedPath);
        var env = Environment.GetEnvironmentVariable("LTADMIN_DB");
        if (!string.IsNullOrWhiteSpace(env)) candidates.Add(env);
        candidates.Add(Path.Combine(AppContext.BaseDirectory, "LTA_ADM.accdb"));
        candidates.Add(Path.Combine(Environment.CurrentDirectory, "LTA_ADM.accdb"));

        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        for (var i = 0; i < 5 && directory is not null; i++, directory = directory.Parent)
            candidates.Add(Path.Combine(directory.FullName, "LTA_ADM.accdb"));

        return candidates.Select(Path.GetFullPath).FirstOrDefault(File.Exists);
    }
}
