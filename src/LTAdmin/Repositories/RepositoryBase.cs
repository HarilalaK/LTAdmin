using System.Data;
using System.Data.OleDb;
using LTAdmin.Data;

namespace LTAdmin.Repositories;

/// <summary>
/// Base des dépôts typés. Chaque dépôt expose des requêtes paramétrées
/// (jamais de concaténation de valeurs) et mappe les lignes en entités.
/// Aucune règle métier ici : uniquement l'accès aux données.
/// </summary>
public abstract class RepositoryBase
{
    protected RepositoryBase(AccessDatabase database)
    {
        Db = database;
    }

    protected AccessDatabase Db { get; }

    protected static string Q(string identifier) => AccessDatabase.QuoteIdentifier(identifier);

    protected static OleDbParameter P(object? value) => AccessDatabase.Parameter(value);

    protected List<T> QueryList<T>(string sql, Func<DataRow, T> map, params OleDbParameter[] parameters)
    {
        var table = Db.Query(sql, parameters);
        var result = new List<T>(table.Rows.Count);
        foreach (DataRow row in table.Rows)
            result.Add(map(row));
        return result;
    }

    protected T? QuerySingle<T>(string sql, Func<DataRow, T> map, params OleDbParameter[] parameters)
        where T : class
    {
        var table = Db.Query(sql, parameters);
        if (table.Rows.Count == 0) return null;
        return map(table.Rows[0]);
    }

    protected DataTable QueryTable(string sql, params OleDbParameter[] parameters)
        => Db.Query(sql, parameters);

    protected int InsertAndGetId(string sql, params OleDbParameter[] parameters)
        => Db.InsertAndGetId(sql, parameters);

    protected int Execute(string sql, params OleDbParameter[] parameters)
        => Db.Execute(sql, parameters);

    protected int ScalarInt(string sql, params OleDbParameter[] parameters)
    {
        var value = Db.Scalar(sql, parameters);
        if (value is null) return 0;
        try { return Convert.ToInt32(value, System.Globalization.CultureInfo.InvariantCulture); }
        catch { return 0; }
    }

    protected decimal? ScalarDecimal(string sql, params OleDbParameter[] parameters)
    {
        var value = Db.Scalar(sql, parameters);
        if (value is null) return null;
        try { return Convert.ToDecimal(value, System.Globalization.CultureInfo.InvariantCulture); }
        catch { return null; }
    }

    protected double? ScalarDouble(string sql, params OleDbParameter[] parameters)
    {
        var value = Db.Scalar(sql, parameters);
        if (value is null) return null;
        try { return Convert.ToDouble(value, System.Globalization.CultureInfo.InvariantCulture); }
        catch { return null; }
    }

    protected string? ScalarString(string sql, params OleDbParameter[] parameters)
    {
        var value = Db.Scalar(sql, parameters);
        if (value is null) return null;
        return Convert.ToString(value, System.Globalization.CultureInfo.InvariantCulture);
    }

    protected bool Exists(string sql, params OleDbParameter[] parameters)
        => ScalarInt(sql, parameters) > 0;
}
