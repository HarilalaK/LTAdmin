using System.Data;
using System.Data.OleDb;
using System.Globalization;
using LTAdmin.Models;

namespace LTAdmin.Data;

public sealed class DatabaseRepository
{
    private readonly AccessDatabase _database;

    public DatabaseRepository(AccessDatabase database) => _database = database;

    public IReadOnlyList<DbTableInfo> GetTables() => _database.GetTables();

    public IReadOnlyList<string> GetSavedQueries()
    {
        var names = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        try
        {
            var schema = _database.Connection.GetOleDbSchemaTable(OleDbSchemaGuid.Views, new object?[] { null, null, null });
            if (schema is not null)
            foreach (DataRow row in schema.Rows)
            {
                var name = schema.Columns.Contains("TABLE_NAME") ? row["TABLE_NAME"]?.ToString()
                    : schema.Columns.Contains("VIEW_NAME") ? row["VIEW_NAME"]?.ToString() : null;
                if (!string.IsNullOrWhiteSpace(name) && !name.StartsWith("MSys", StringComparison.OrdinalIgnoreCase)) names.Add(name);
            }
        }
        catch { /* ACE versions differ in the Views schema. Known reports are added below. */ }

        foreach (var known in new[]
        {
            "R_LISTE_ETUDIANT", "R_MOYENNE_MATIERE", "R_MOYENNE_PERIODE", "R_BULLETIN_DETAIL",
            "R_PAIEMENT_ECHEANCE", "R_SITUATION_ECOLAGE", "R_EDT_CLASSE", "R_ABSENCE_ETUDIANT"
        }) names.Add(known);
        return names.OrderBy(n => n).ToArray();
    }

    public DataTable LoadSavedQuery(string queryName)
        => _database.Query($"SELECT * FROM {AccessDatabase.QuoteIdentifier(queryName)}");

    public DataTable LoadTable(DbTableInfo table, string? search = null, int maxRows = 1000)
    {
        var sql = $"SELECT TOP {Math.Clamp(maxRows, 1, 10000)} * FROM {AccessDatabase.QuoteIdentifier(table.Name)}";
        var parameters = new List<OleDbParameter>();
        var textColumns = table.Columns.Where(IsSearchable).ToArray();
        if (!string.IsNullOrWhiteSpace(search) && textColumns.Length > 0)
        {
            sql += " WHERE " + string.Join(" OR ", textColumns.Select(c =>
                $"CStr({AccessDatabase.QuoteIdentifier(c.Name)}) LIKE ?"));
            parameters.AddRange(textColumns.Select(_ => AccessDatabase.Parameter("%" + search.Trim() + "%")));
        }
        var orderColumn = table.PrimaryKeyColumns.FirstOrDefault() ?? table.Columns.FirstOrDefault();
        sql += " ORDER BY " + (orderColumn is null ? "1" : AccessDatabase.QuoteIdentifier(orderColumn.Name));

        return _database.Query(sql, parameters);
    }

    public int Insert(DbTableInfo table, IReadOnlyDictionary<string, object?> values)
    {
        var columns = table.Columns
            .Where(c => !c.IsAutoIncrement && !c.IsBinary && values.ContainsKey(c.Name))
            .ToArray();
        if (columns.Length == 0) return 0;

        var sql = $"INSERT INTO {AccessDatabase.QuoteIdentifier(table.Name)} " +
                  $"({string.Join(", ", columns.Select(c => AccessDatabase.QuoteIdentifier(c.Name)))}) " +
                  $"VALUES ({string.Join(", ", columns.Select(_ => "?"))})";
        var parameters = columns.Select(c => AccessDatabase.Parameter(c.DataType, values[c.Name])).ToArray();
        return _database.Execute(sql, parameters);
    }

    public int Update(DbTableInfo table, DataRow originalRow, IReadOnlyDictionary<string, object?> values)
    {
        var columns = table.Columns
            .Where(c => !c.IsAutoIncrement && !c.IsBinary && values.ContainsKey(c.Name) && !c.IsPrimaryKey)
            .ToArray();
        if (columns.Length == 0) return 0;

        var predicates = BuildRowPredicates(table, originalRow, out var whereParameters);
        var sql = $"UPDATE {AccessDatabase.QuoteIdentifier(table.Name)} SET " +
                  string.Join(", ", columns.Select(c => $"{AccessDatabase.QuoteIdentifier(c.Name)} = ?")) +
                  " WHERE " + predicates;
        var parameters = columns.Select(c => AccessDatabase.Parameter(c.DataType, values[c.Name])).Concat(whereParameters).ToArray();
        return _database.Execute(sql, parameters);
    }

    public int Delete(DbTableInfo table, DataRow row)
    {
        var predicates = BuildRowPredicates(table, row, out var parameters);
        return _database.Execute(
            $"DELETE FROM {AccessDatabase.QuoteIdentifier(table.Name)} WHERE {predicates}", parameters);
    }

    public int Count(DbTableInfo table)
    {
        var value = _database.Scalar($"SELECT COUNT(*) FROM {AccessDatabase.QuoteIdentifier(table.Name)}");
        return value is null ? 0 : Convert.ToInt32(value, CultureInfo.InvariantCulture);
    }

    public DataTable RecentRows(DbTableInfo table, int count = 8)
    {
        var order = table.Columns.FirstOrDefault(c => c.Name.Contains("DATE", StringComparison.OrdinalIgnoreCase))
                    ?? table.PrimaryKeyColumns.FirstOrDefault()
                    ?? table.Columns.FirstOrDefault();
        var sql = $"SELECT TOP {Math.Clamp(count, 1, 100)} * FROM {AccessDatabase.QuoteIdentifier(table.Name)}";
        if (order is not null) sql += $" ORDER BY {AccessDatabase.QuoteIdentifier(order.Name)} DESC";
        return _database.Query(sql);
    }

    private static string BuildRowPredicates(DbTableInfo table, DataRow row, out List<OleDbParameter> parameters)
    {
        parameters = new List<OleDbParameter>();
        var keyColumns = table.PrimaryKeyColumns.ToArray();
        var columns = keyColumns.Length > 0 ? keyColumns : table.Columns.Where(c => !c.IsBinary).ToArray();
        if (columns.Length == 0) throw new InvalidOperationException("Cette table ne possède aucune colonne exploitable.");

        var predicates = new List<string>();
        foreach (var column in columns)
        {
            var value = row.Table.Columns.Contains(column.Name) ? row[column.Name] : DBNull.Value;
            if (value is DBNull || value is null)
            {
                predicates.Add($"{AccessDatabase.QuoteIdentifier(column.Name)} IS NULL");
            }
            else
            {
                predicates.Add($"{AccessDatabase.QuoteIdentifier(column.Name)} = ?");
                parameters.Add(AccessDatabase.Parameter(column.DataType, value));
            }
        }
        return string.Join(" AND ", predicates);
    }

    private static bool IsSearchable(DbColumnInfo column)
        => !column.IsBinary && !column.IsBoolean &&
           (column.DataType is OleDbType.Char or OleDbType.VarChar or OleDbType.LongVarChar or OleDbType.WChar
               or OleDbType.VarWChar or OleDbType.LongVarWChar or OleDbType.Guid);
}
