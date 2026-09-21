using System.Data;
using System.Data.OleDb;
using System.Globalization;
using LTAdmin.Data;
using LTAdmin.Models;

namespace LTAdmin.UI;

public sealed class RecordEditorForm : Form
{
    private readonly DatabaseRepository _repository;
    private readonly DbTableInfo _table;
    private readonly DataRow? _originalRow;
    private readonly Dictionary<string, Control> _editors = new(StringComparer.OrdinalIgnoreCase);
    private readonly ErrorProvider _errors = new();
    private readonly TableLayoutPanel _fields;

    public RecordEditorForm(AccessDatabase database, DbTableInfo table, DataRow? originalRow)
    {
        _repository = new DatabaseRepository(database);
        _table = table;
        _originalRow = originalRow;
        Text = originalRow is null ? $"Nouveau — {DatabaseCatalog.DisplayName(table.Name)}" : $"Modifier — {DatabaseCatalog.DisplayName(table.Name)}";
        StartPosition = FormStartPosition.CenterParent;
        FormBorderStyle = FormBorderStyle.Sizable;
        MinimumSize = new Size(560, 430);
        Size = new Size(690, Math.Min(860, 250 + Math.Max(1, table.Columns.Count) * 62));
        BackColor = Theme.Background;
        Font = Theme.Body;

        var title = new Panel { Dock = DockStyle.Top, Height = 76, Padding = new Padding(24, 18, 24, 8), BackColor = Theme.Surface };
        title.Controls.Add(new Label { Text = Text, AutoSize = true, Font = Theme.SubHeading, ForeColor = Theme.Text, Location = new Point(24, 18) });
        title.Controls.Add(new Label { Text = "Les champs marqués d’un * sont requis.", AutoSize = true, Font = Theme.Small, ForeColor = Theme.MutedText, Location = new Point(24, 43) });
        Controls.Add(title);

        _fields = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            AutoScroll = true,
            ColumnCount = 2,
            RowCount = 0,
            Padding = new Padding(26, 20, 26, 10),
            BackColor = Theme.Background
        };
        _fields.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 205));
        _fields.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        Controls.Add(_fields);

        var footer = new Panel { Dock = DockStyle.Bottom, Height = 66, Padding = new Padding(24, 14, 24, 14), BackColor = Theme.Surface };
        var cancel = Theme.Button("Annuler", Color.FromArgb(241, 245, 249), Theme.Text, 105);
        cancel.Location = new Point(footer.Width - 230, 14);
        cancel.Anchor = AnchorStyles.Right | AnchorStyles.Top;
        cancel.Click += (_, _) => DialogResult = DialogResult.Cancel;
        footer.Controls.Add(cancel);
        var save = Theme.Button("Enregistrer", Theme.Primary, Color.White, 115);
        save.Location = new Point(footer.Width - 115, 14);
        save.Anchor = AnchorStyles.Right | AnchorStyles.Top;
        save.Click += (_, _) => Save();
        footer.Controls.Add(save);
        Controls.Add(footer);
        AcceptButton = save;
        CancelButton = cancel;

        BuildFields();
    }

    private void BuildFields()
    {
        foreach (var column in _table.Columns)
        {
            var row = _fields.RowCount++;
            _fields.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            var required = !column.IsNullable && !column.IsAutoIncrement;
            var label = new Label
            {
                Text = column.Name + (required ? " *" : ""),
                AutoSize = true,
                Anchor = AnchorStyles.Left,
                Margin = new Padding(0, 9, 12, 8),
                ForeColor = Theme.Text,
                Font = required ? Theme.BodyBold : Theme.Body
            };
            _fields.Controls.Add(label, 0, row);

            var value = _originalRow is null || !_originalRow.Table.Columns.Contains(column.Name)
                ? null
                : _originalRow[column.Name];
            var editor = CreateEditor(column, value);
            editor.Margin = new Padding(0, 3, 0, 7);
            editor.Dock = DockStyle.Top;
            editor.Anchor = AnchorStyles.Left | AnchorStyles.Right;
            _fields.Controls.Add(editor, 1, row);
            _editors[column.Name] = editor;
        }
    }

    private Control CreateEditor(DbColumnInfo column, object? value)
    {
        if (column.IsAutoIncrement || column.IsBinary)
        {
            var readOnly = new Label
            {
                Text = column.IsAutoIncrement ? "Généré automatiquement" : "Fichier binaire — modification non disponible",
                AutoSize = true,
                Height = 29,
                Padding = new Padding(9, 7, 9, 4),
                ForeColor = Theme.MutedText,
                BackColor = Color.FromArgb(241, 245, 249)
            };
            readOnly.Tag = null;
            return readOnly;
        }

        if (column.IsBoolean)
        {
            var check = new CheckBox { Text = "Oui", AutoSize = true, Height = 28, ForeColor = Theme.Text };
            if (value is not null && value is not DBNull) check.Checked = Convert.ToBoolean(value, CultureInfo.InvariantCulture);
            return check;
        }

        if (column.IsDate)
        {
            var date = new DateTimePicker
            {
                Format = DateTimePickerFormat.Custom,
                CustomFormat = "dd/MM/yyyy HH:mm",
                ShowCheckBox = column.IsNullable,
                Height = 29
            };
            if (value is not null && value is not DBNull && DateTime.TryParse(Convert.ToString(value), out var parsed))
            {
                date.Value = parsed;
                date.Checked = true;
            }
            else if (column.IsNullable) date.Checked = false;
            return date;
        }

        var text = new TextBox
        {
            Text = value is null or DBNull ? "" : Convert.ToString(value, CultureInfo.CurrentCulture) ?? "",
            Height = 30,
            BorderStyle = BorderStyle.FixedSingle,
            ForeColor = Theme.Text,
            BackColor = Color.White,
            Multiline = column.IsLongText,
            ScrollBars = column.IsLongText ? ScrollBars.Vertical : ScrollBars.None,
            MaxLength = column.Size > 0 && column.Size < 32767 ? column.Size : 0
        };
        if (column.IsLongText) text.Height = 78;
        if (LooksLikePassword(column.Name)) text.UseSystemPasswordChar = true;
        return text;
    }

    private void Save()
    {
        _errors.Clear();
        try
        {
            var values = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase);
            foreach (var column in _table.Columns)
            {
                if (column.IsAutoIncrement || column.IsBinary) continue;
                var value = ReadValue(column, _editors[column.Name]);
                if (value is null && !column.IsNullable)
                {
                    _errors.SetError(_editors[column.Name], "Ce champ est obligatoire.");
                    _editors[column.Name].Focus();
                    return;
                }
                values[column.Name] = value;
            }

            if (_originalRow is null) _repository.Insert(_table, values);
            else _repository.Update(_table, _originalRow, values);
            DialogResult = DialogResult.OK;
            Close();
        }
        catch (FormatException ex)
        {
            MessageBox.Show(this, ex.Message, "Valeur incorrecte", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
        catch (OleDbException ex)
        {
            MessageBox.Show(this, FriendlyDatabaseError(ex), "Enregistrement impossible", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, ex.Message, "Enregistrement impossible", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private static object? ReadValue(DbColumnInfo column, Control editor)
    {
        if (editor is CheckBox check) return check.Checked;
        if (editor is DateTimePicker date) return date.ShowCheckBox && !date.Checked ? null : date.Value;
        if (editor is not TextBox text) return null;

        var raw = text.Text.Trim();
        if (raw.Length == 0) return column.IsNullable ? null : "";
        var culture = CultureInfo.CurrentCulture;
        return column.DataType switch
        {
            OleDbType.BigInt or OleDbType.UnsignedBigInt => long.TryParse(raw, NumberStyles.Integer, culture, out var big) ? big : throw new FormatException($"{column.Name} doit être un nombre entier."),
            OleDbType.Integer or OleDbType.UnsignedInt => int.TryParse(raw, NumberStyles.Integer, culture, out var integer) ? integer : throw new FormatException($"{column.Name} doit être un nombre entier."),
            OleDbType.SmallInt or OleDbType.UnsignedSmallInt => short.TryParse(raw, NumberStyles.Integer, culture, out var small) ? small : throw new FormatException($"{column.Name} doit être un nombre entier."),
            OleDbType.TinyInt or OleDbType.UnsignedTinyInt => byte.TryParse(raw, NumberStyles.Integer, culture, out var tiny) ? tiny : throw new FormatException($"{column.Name} doit être un nombre entier positif."),
            OleDbType.Decimal or OleDbType.Numeric or OleDbType.Currency or OleDbType.VarNumeric => decimal.TryParse(raw, NumberStyles.Number, culture, out var decimalValue) ? decimalValue : throw new FormatException($"{column.Name} doit être un nombre."),
            OleDbType.Single => float.TryParse(raw, NumberStyles.Float, culture, out var single) ? single : throw new FormatException($"{column.Name} doit être un nombre."),
            OleDbType.Double => double.TryParse(raw, NumberStyles.Float, culture, out var doubleValue) ? doubleValue : throw new FormatException($"{column.Name} doit être un nombre."),
            OleDbType.Guid => Guid.TryParse(raw, out var guid) ? guid : throw new FormatException($"{column.Name} doit être un identifiant valide."),
            OleDbType.Date or OleDbType.DBDate or OleDbType.DBTime or OleDbType.DBTimeStamp => DateTime.TryParse(raw, culture, DateTimeStyles.None, out var parsedDate) ? parsedDate : throw new FormatException($"{column.Name} doit être une date valide."),
            _ => raw
        };
    }

    private static bool LooksLikePassword(string name)
        => name.Contains("PASS", StringComparison.OrdinalIgnoreCase) || name.Contains("MDP", StringComparison.OrdinalIgnoreCase)
           || name.Contains("SECRET", StringComparison.OrdinalIgnoreCase);

    private static string FriendlyDatabaseError(OleDbException ex)
    {
        var message = ex.Message;
        if (message.Contains("duplicate", StringComparison.OrdinalIgnoreCase) || message.Contains("unique", StringComparison.OrdinalIgnoreCase))
            return "Cette valeur existe déjà dans la base. Vérifiez les champs uniques.\n\n" + message;
        if (message.Contains("referential", StringComparison.OrdinalIgnoreCase) || message.Contains("relation", StringComparison.OrdinalIgnoreCase))
            return "Cette opération est liée à d’autres données. Supprimez ou modifiez d’abord les enregistrements dépendants.\n\n" + message;
        return message;
    }
}
