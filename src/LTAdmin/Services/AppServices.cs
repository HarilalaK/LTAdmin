using System.Data;
using LTAdmin.Data;
using LTAdmin.Models;

namespace LTAdmin.Services;

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

        // Useful when running bin\Debug\net8.0-windows from the repository.
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        for (var i = 0; i < 5 && directory is not null; i++, directory = directory.Parent)
            candidates.Add(Path.Combine(directory.FullName, "LTA_ADM.accdb"));

        return candidates.Select(Path.GetFullPath).FirstOrDefault(File.Exists);
    }
}

public sealed class AuthenticationService
{
    private readonly DatabaseRepository _repository;
    private readonly AccessDatabase _database;

    public AuthenticationService(AccessDatabase database)
    {
        _database = database;
        _repository = new DatabaseRepository(database);
    }

    public UserSession? Authenticate(string login, string password)
    {
        var table = _database.GetTables().FirstOrDefault(t =>
            string.Equals(t.Name, "UTILISATEUR", StringComparison.OrdinalIgnoreCase));
        if (table is null) return null;

        // The original Access schema is user-editable. We resolve common French and English field
        // names instead of hard-coding one exact version of the table.
        var loginColumn = FindColumn(table, "LOGIN", "IDENTIFIANT", "NOM_UTILISATEUR", "USERNAME", "USER_NAME", "CODE_UTILISATEUR", "CODE_UTR");
        var passwordColumn = FindColumn(table, "MOT_DE_PASSE", "MOTDEPASSE", "MOT_PASSE", "PASSWORD", "MDP", "PASS", "CODE_SECRET");
        if (loginColumn is null || passwordColumn is null) return null;

        var rows = _repository.LoadTable(table, maxRows: 10000);
        foreach (DataRow row in rows.Rows)
        {
            var storedLogin = Value(row, loginColumn.Name);
            var storedPassword = Value(row, passwordColumn.Name);
            if (!string.Equals(storedLogin, login.Trim(), StringComparison.OrdinalIgnoreCase) ||
                !string.Equals(storedPassword, password, StringComparison.Ordinal)) continue;

            var nameColumn = FindColumn(table, "NOM_COMPLET", "NOM", "NOM_UTR", "LIBELLE", "PRENOM");
            var roleColumn = FindColumn(table, "ROLE", "PROFIL", "NIVEAU_ACCES", "DROIT");
            var displayName = nameColumn is null ? storedLogin : Value(row, nameColumn.Name);
            var role = roleColumn is null ? "Administrateur" : Value(row, roleColumn.Name);
            return new UserSession(storedLogin, string.IsNullOrWhiteSpace(displayName) ? storedLogin : displayName,
                string.IsNullOrWhiteSpace(role) ? "Utilisateur" : role);
        }
        return null;
    }

    private static DbColumnInfo? FindColumn(DbTableInfo table, params string[] names)
        => names.Select(name => table.Columns.FirstOrDefault(c =>
                string.Equals(c.Name, name, StringComparison.OrdinalIgnoreCase)))
            .FirstOrDefault(column => column is not null);

    private static string Value(DataRow row, string name)
        => row.Table.Columns.Contains(name) && row[name] is not DBNull ? Convert.ToString(row[name]) ?? "" : "";
}

public static class CsvExporter
{
    public static void Export(DataTable table, string filePath)
    {
        using var writer = new StreamWriter(filePath, false, new System.Text.UTF8Encoding(encoderShouldEmitUTF8Identifier: true));
        writer.WriteLine(string.Join(";", table.Columns.Cast<DataColumn>().Select(c => Escape(c.ColumnName))));
        foreach (DataRow row in table.Rows)
        {
            writer.WriteLine(string.Join(";", table.Columns.Cast<DataColumn>().Select(c =>
                Escape(row[c] is DBNull ? "" : Format(row[c])))));
        }
    }

    private static string Format(object value)
        => value switch
        {
            DateTime date => date.ToString("yyyy-MM-dd HH:mm:ss"),
            byte[] bytes => $"<{bytes.Length} octets>",
            _ => Convert.ToString(value, System.Globalization.CultureInfo.CurrentCulture) ?? ""
        };

    private static string Escape(string value)
        => "\"" + value.Replace("\"", "\"\"", StringComparison.Ordinal).Replace("\r", " ").Replace("\n", " ") + "\"";
}
