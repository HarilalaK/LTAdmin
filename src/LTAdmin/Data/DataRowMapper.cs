using System.Data;
using System.Globalization;

namespace LTAdmin.Data;

/// <summary>
/// Lecture défensive des colonnes d'un DataRow : colonnes absentes et DBNull
/// sont convertis en valeurs par défaut au lieu de lever des exceptions.
/// </summary>
public static class DataRowMapper
{
    public static bool HasColumn(DataRow row, string column)
        => row.Table.Columns.Contains(column);

    public static string? GetString(DataRow row, string column)
    {
        if (!HasColumn(row, column) || row[column] is DBNull) return null;
        return Convert.ToString(row[column], CultureInfo.InvariantCulture);
    }

    public static string GetString(DataRow row, string column, string defaultValue)
        => GetString(row, column) ?? defaultValue;

    public static int? GetInt32(DataRow row, string column)
    {
        if (!HasColumn(row, column) || row[column] is DBNull) return null;
        try { return Convert.ToInt32(row[column], CultureInfo.InvariantCulture); }
        catch { return null; }
    }

    public static int GetInt32(DataRow row, string column, int defaultValue)
        => GetInt32(row, column) ?? defaultValue;

    public static long? GetInt64(DataRow row, string column)
    {
        if (!HasColumn(row, column) || row[column] is DBNull) return null;
        try { return Convert.ToInt64(row[column], CultureInfo.InvariantCulture); }
        catch { return null; }
    }

    public static double? GetDouble(DataRow row, string column)
    {
        if (!HasColumn(row, column) || row[column] is DBNull) return null;
        try { return Convert.ToDouble(row[column], CultureInfo.InvariantCulture); }
        catch { return null; }
    }

    public static double GetDouble(DataRow row, string column, double defaultValue)
        => GetDouble(row, column) ?? defaultValue;

    public static decimal? GetDecimal(DataRow row, string column)
    {
        if (!HasColumn(row, column) || row[column] is DBNull) return null;
        try { return Convert.ToDecimal(row[column], CultureInfo.InvariantCulture); }
        catch { return null; }
    }

    public static decimal GetDecimal(DataRow row, string column, decimal defaultValue)
        => GetDecimal(row, column) ?? defaultValue;

    public static bool? GetBoolean(DataRow row, string column)
    {
        if (!HasColumn(row, column) || row[column] is DBNull) return null;
        var value = row[column];
        if (value is bool boolean) return boolean;
        var text = Convert.ToString(value, CultureInfo.InvariantCulture);
        if (string.Equals(text, "1", StringComparison.OrdinalIgnoreCase)
            || string.Equals(text, "YES", StringComparison.OrdinalIgnoreCase)
            || string.Equals(text, "TRUE", StringComparison.OrdinalIgnoreCase)
            || string.Equals(text, "VRAI", StringComparison.OrdinalIgnoreCase)) return true;
        if (string.Equals(text, "0", StringComparison.OrdinalIgnoreCase)
            || string.Equals(text, "NO", StringComparison.OrdinalIgnoreCase)
            || string.Equals(text, "FALSE", StringComparison.OrdinalIgnoreCase)
            || string.Equals(text, "FAUX", StringComparison.OrdinalIgnoreCase)) return false;
        return null;
    }

    public static bool GetBoolean(DataRow row, string column, bool defaultValue)
        => GetBoolean(row, column) ?? defaultValue;

    public static DateTime? GetDateTime(DataRow row, string column)
    {
        if (!HasColumn(row, column) || row[column] is DBNull) return null;
        try { return Convert.ToDateTime(row[column], CultureInfo.InvariantCulture); }
        catch { return null; }
    }
}
