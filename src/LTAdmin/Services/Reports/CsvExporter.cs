using System.Data;
using System.Text;

namespace LTAdmin.Services.Reports;

/// <summary>Export CSV (séparateur « ; », UTF-8 avec BOM pour Excel).</summary>
public static class CsvExporter
{
    public static void Export(DataTable table, string filePath)
    {
        using var writer = new StreamWriter(filePath, false, new UTF8Encoding(encoderShouldEmitUTF8Identifier: true));
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
