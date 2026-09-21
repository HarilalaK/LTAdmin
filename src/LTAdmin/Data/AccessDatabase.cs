using System.Data;
using System.Data.OleDb;
using LTAdmin.Models;

namespace LTAdmin.Data;

/// <summary>
/// Small Access/ACE adapter. The database remains the existing LTA_ADM.accdb file; no migration or
/// replacement database is created. All identifiers are obtained from Access metadata and quoted.
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

    public void Open()
    {
        ThrowIfDisposed();
        if (IsOpen) return;

        if (!File.Exists(DatabasePath))
            throw new FileNotFoundException("La base Access est introuvable.", DatabasePath);

        var errors = new List<string>();
        // ACE 16 is installed with recent Office versions, ACE 12 with older Office/Access Runtime.
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
        if (_connection is null) return;
        try { _connection.Close(); }
        finally { _connection.Dispose(); _connection = null; }
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

    public OleDbCommand CreateCommand(string sql, IEnumerable<OleDbParameter>? parameters = null)
    {
        var command = new OleDbCommand(sql, EnsureConnection());
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
            catch { /* One malformed/system object must not hide all other tables. */ }
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
            // Some ACE versions do not expose Primary_Keys. The UI still works with row-value matching.
        }

        // A fallback for databases whose primary-key schema is not exposed by the installed ACE provider.
        if (!table.Columns.Any(c => c.IsPrimaryKey))
        {
            var likely = table.Columns.FirstOrDefault(c =>
                c.Name.StartsWith("ID_", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(c.Name, "ID", StringComparison.OrdinalIgnoreCase));
            if (likely is not null) likely.IsPrimaryKey = true;
        }

        // Access sometimes omits IS_AUTOINCREMENT for an AutoNumber primary key.
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
        Close();
        _disposed = true;
    }
}
