using System.Data;
using System.Data.OleDb;
using System.Globalization;
using LTAdmin.Models;

namespace LTAdmin.Data;

/// <summary>
/// Adaptateur Access/ACE. La base reste le fichier LTA_ADM.accdb existant :
/// aucune migration, aucune recréation de table, aucune modification de données
/// sans action explicite d'un service. Tous les identifiants sont lus depuis
/// les métadonnées Access et protégés par des crochets ; toutes les valeurs
/// passent par des paramètres positionnels OleDb (jamais de concaténation).
/// </summary>
public sealed class AccessDatabase : IDisposable
{
    private OleDbConnection? _connection;
    private bool _disposed;

    public AccessDatabase(string databasePath)
    {
        DatabasePath = Path.GetFullPath(databasePath);
    }

    public string DatabasePath { get; }
    public bool IsOpen => _connection?.State == ConnectionState.Open;
    public OleDbConnection Connection => EnsureConnection();

    /// <summary>Transaction en cours, ou null hors transaction.</summary>
    public OleDbTransaction? CurrentTransaction { get; private set; }

    public bool InTransaction => CurrentTransaction is not null;

    public void Open()
    {
        ThrowIfDisposed();
        if (IsOpen) return;

        if (!File.Exists(DatabasePath))
            throw new FileNotFoundException("La base Access est introuvable.", DatabasePath);

        var errors = new List<string>();
        // ACE 16 est installé avec les versions récentes d'Office, ACE 12 avec les anciennes.
        foreach (var provider in new[] { "Microsoft.ACE.OLEDB.16.0", "Microsoft.ACE.OLEDB.12.0" })
        {
            OleDbConnection? candidate = null;
            try
            {
                candidate = new OleDbConnection(BuildConnectionString(provider));
                candidate.Open();
                _connection = candidate;
                return;
            }
            catch (Exception ex)
            {
                errors.Add($"{provider}: {ex.Message}");
                candidate?.Dispose();
            }
        }

        throw new InvalidOperationException(
            "Microsoft Access Database Engine (ACE) n’est pas disponible ou sa version ne correspond pas à l’application.\n\n" +
            "Installez le Microsoft Access Database Engine 2016 Redistributable dans la même architecture que l’application, puis relancez LTAdmin.\n\n" +
            string.Join("\n", errors));
    }

    public void Close()
    {
        if (InTransaction)
            throw new InvalidOperationException("Impossible de fermer la connexion pendant une transaction. Validez ou annulez d’abord la transaction.");
        if (_connection is null) return;
        try { _connection.Close(); }
        finally { _connection.Dispose(); _connection = null; }
    }

    /// <summary>Démarre une transaction. Validez avec Complete(), sinon rollback automatique.</summary>
    public AccessTransaction BeginTransaction() => new(this);

    internal void BeginTransactionInternal()
    {
        ThrowIfDisposed();
        if (InTransaction)
            throw new InvalidOperationException("Une transaction est déjà en cours. Les transactions imbriquées ne sont pas prises en charge.");
        CurrentTransaction = EnsureConnection().BeginTransaction();
    }

    internal void CommitInternal()
    {
        try { CurrentTransaction?.Commit(); }
        finally
        {
            CurrentTransaction?.Dispose();
            CurrentTransaction = null;
        }
    }

    internal void RollbackInternal()
    {
        try { CurrentTransaction?.Rollback(); }
        catch { /* Un rollback en échec ne doit pas masquer l'erreur d'origine. */ }
        finally
        {
            try { CurrentTransaction?.Dispose(); }
            catch { /* Ignoré volontairement. */ }
            CurrentTransaction = null;
        }
    }

    public DataTable Query(string sql, IEnumerable<OleDbParameter>? parameters = null)
    {
        using var command = CreateCommand(sql, parameters);
        using var adapter = new OleDbDataAdapter(command);
        var result = new DataTable();
        adapter.Fill(result);
        return result;
    }

    public object? Scalar(string sql, IEnumerable<OleDbParameter>? parameters = null)
    {
        using var command = CreateCommand(sql, parameters);
        var value = command.ExecuteScalar();
        return value is DBNull ? null : value;
    }

    public int Execute(string sql, IEnumerable<OleDbParameter>? parameters = null)
    {
        using var command = CreateCommand(sql, parameters);
        return command.ExecuteNonQuery();
    }

    /// <summary>
    /// Exécute un INSERT puis retourne la valeur AutoNumber générée (SELECT @@IDENTITY
    /// sur la même connexion). Retourne 0 si l'identité est indisponible.
    /// </summary>
    public int InsertAndGetId(string sql, IEnumerable<OleDbParameter>? parameters = null)
    {
        using var command = CreateCommand(sql, parameters);
        command.ExecuteNonQuery();
        command.CommandText = "SELECT @@IDENTITY";
        command.Parameters.Clear();
        var value = command.ExecuteScalar();
        if (value is null or DBNull) return 0;
        return Convert.ToInt32(value, CultureInfo.InvariantCulture);
    }

    public OleDbCommand CreateCommand(string sql, IEnumerable<OleDbParameter>? parameters = null)
    {
        var command = new OleDbCommand(sql, EnsureConnection());
        if (CurrentTransaction is not null)
            command.Transaction = CurrentTransaction;
        if (parameters is not null)
            foreach (var parameter in parameters) command.Parameters.Add(parameter);
        return command;
    }

    public IReadOnlyList<DbTableInfo> GetTables()
    {
        var schema = Connection.GetOleDbSchemaTable(
            OleDbSchemaGuid.Tables,
            new object?[] { null, null, null, "TABLE" });

        var tables = new List<DbTableInfo>();
        if (schema is null) return tables;

        foreach (DataRow row in schema.Rows)
        {
            var name = row["TABLE_NAME"]?.ToString();
            if (string.IsNullOrWhiteSpace(name) || IsSystemTable(name)) continue;
            try { tables.Add(GetTable(name)); }
            catch { /* Un objet système mal formé ne doit pas masquer les autres tables. */ }
        }

        return tables.OrderBy(t => TableOrder(t.Name)).ThenBy(t => t.Name).ToList();
    }

    public DbTableInfo GetTable(string tableName)
    {
        var schema = Connection.GetOleDbSchemaTable(
            OleDbSchemaGuid.Columns,
            new object?[] { null, null, tableName, null });
        if (schema is null) throw new InvalidOperationException($"Table introuvable : {tableName}");

        var table = new DbTableInfo { Name = tableName };
        foreach (DataRow row in schema.Rows)
        {
            var name = ReadString(row, "COLUMN_NAME");
            if (string.IsNullOrWhiteSpace(name)) continue;
            var type = ReadOleDbType(row, "DATA_TYPE");
            table.Columns.Add(new DbColumnInfo
            {
                Name = name,
                DataType = type,
                Ordinal = ReadInt(row, "ORDINAL_POSITION"),
                Size = ReadInt(row, "CHARACTER_MAXIMUM_LENGTH", "COLUMN_SIZE"),
                IsNullable = ReadBool(row, "IS_NULLABLE", defaultValue: true),
                IsAutoIncrement = ReadBool(row, "IS_AUTOINCREMENT") || ReadBool(row, "AUTOINCREMENT")
            });
        }

        table.Columns.Sort((a, b) => a.Ordinal.CompareTo(b.Ordinal));
        MarkPrimaryKeys(table);
        return table;
    }

    public string CreateBackup()
    {
        ThrowIfDisposed();
        if (InTransaction)
            throw new InvalidOperationException("Impossible de sauvegarder pendant une transaction.");
        var folder = Path.Combine(Path.GetDirectoryName(DatabasePath) ?? AppContext.BaseDirectory, "Sauvegardes");
        Directory.CreateDirectory(folder);
        var destination = Path.Combine(folder, $"LTA_ADM_{DateTime.Now:yyyyMMdd_HHmmss}.accdb");
        var wasOpen = IsOpen;
        Close();
        try
        {
            File.Copy(DatabasePath, destination, overwrite: false);
            return destination;
        }
        finally
        {
            if (wasOpen) Open();
        }
    }

    public static string QuoteIdentifier(string identifier)
        => "[" + identifier.Replace("]", "]]", StringComparison.Ordinal) + "]";

    public static OleDbParameter Parameter(object? value)
        => new() { Value = value ?? DBNull.Value };

    public static OleDbParameter Parameter(OleDbType type, object? value)
        => new() { OleDbType = type, Value = value ?? DBNull.Value };

    private OleDbConnection EnsureConnection()
    {
        ThrowIfDisposed();
        if (!IsOpen) Open();
        return _connection!;
    }

    private string BuildConnectionString(string provider)
        => $"Provider={provider};Data Source={DatabasePath};Persist Security Info=False;";

    private void MarkPrimaryKeys(DbTableInfo table)
    {
        try
        {
            var keys = Connection.GetOleDbSchemaTable(
                OleDbSchemaGuid.Primary_Keys,
                new object?[] { null, null, table.Name });
            if (keys is null) return;
            foreach (DataRow row in keys.Rows)
            {
                var columnName = ReadString(row, "COLUMN_NAME");
                var column = table.Columns.FirstOrDefault(c => string.Equals(c.Name, columnName, StringComparison.OrdinalIgnoreCase));
                if (column is not null) column.IsPrimaryKey = true;
            }
        }
        catch
        {
            // Certaines versions d'ACE n'exposent pas Primary_Keys. L'interface reste utilisable.
        }

        // Repli pour les bases dont le schéma de clés primaires n'est pas exposé.
        if (!table.Columns.Any(c => c.IsPrimaryKey))
        {
            var likely = table.Columns.FirstOrDefault(c =>
                c.Name.StartsWith("ID_", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(c.Name, "ID", StringComparison.OrdinalIgnoreCase));
            if (likely is not null) likely.IsPrimaryKey = true;
        }

        // Access omet parfois IS_AUTOINCREMENT pour une clé primaire AutoNumber.
        foreach (var column in table.Columns.Where(c => c.IsPrimaryKey && c.Name.StartsWith("ID_", StringComparison.OrdinalIgnoreCase)))
        {
            if (column.DataType is OleDbType.Integer or OleDbType.BigInt or OleDbType.SmallInt)
                column.IsAutoIncrement = true;
        }
    }

    private static bool IsSystemTable(string name)
        => name.StartsWith("MSys", StringComparison.OrdinalIgnoreCase) || name.StartsWith("f_", StringComparison.OrdinalIgnoreCase);

    private static int TableOrder(string name)
    {
        var index = Array.FindIndex(DatabaseCatalog.PreferredTableOrder,
            n => string.Equals(n, name, StringComparison.OrdinalIgnoreCase));
        return index < 0 ? 1000 : index;
    }

    private static string ReadString(DataRow row, params string[] names)
    {
        foreach (var name in names)
            if (row.Table.Columns.Contains(name) && row[name] is not DBNull)
                return Convert.ToString(row[name]) ?? string.Empty;
        return string.Empty;
    }

    private static int ReadInt(DataRow row, params string[] names)
    {
        var text = ReadString(row, names);
        return int.TryParse(text, out var value) ? value : 0;
    }

    private static bool ReadBool(DataRow row, string name, bool defaultValue = false)
    {
        if (!row.Table.Columns.Contains(name) || row[name] is DBNull) return defaultValue;
        var value = row[name];
        if (value is bool boolean) return boolean;
        var text = Convert.ToString(value);
        if (string.Equals(text, "YES", StringComparison.OrdinalIgnoreCase) || text == "1") return true;
        if (string.Equals(text, "NO", StringComparison.OrdinalIgnoreCase) || text == "0") return false;
        return bool.TryParse(text, out var result) ? result : defaultValue;
    }

    private static OleDbType ReadOleDbType(DataRow row, string name)
    {
        if (!row.Table.Columns.Contains(name) || row[name] is DBNull) return OleDbType.VarWChar;
        try { return (OleDbType)Convert.ToInt16(row[name]); }
        catch { return OleDbType.VarWChar; }
    }

    private void ThrowIfDisposed()
    {
        if (_disposed) throw new ObjectDisposedException(nameof(AccessDatabase));
    }

    public void Dispose()
    {
        if (_disposed) return;
        if (InTransaction) RollbackInternal();
        Close();
        _disposed = true;
    }
}
