using System.Data;
using LTAdmin.Data;
using LTAdmin.Models;
using LTAdmin.Services;

namespace LTAdmin.UI;

public sealed class TableManagerControl : UserControl
{
    private readonly AccessDatabase _database;
    private readonly DatabaseRepository _repository;
    private readonly DbTableInfo _table;
    private readonly DataGridView _grid = new();
    private readonly TextBox _search = new();
    private readonly Label _status = new();
    private readonly Label _count = new();
    private DataTable? _data;

    public TableManagerControl(AccessDatabase database, DbTableInfo table)
    {
        _database = database;
        _repository = new DatabaseRepository(database);
        _table = table;
        Dock = DockStyle.Fill;
        BackColor = Theme.Background;
        Padding = new Padding(30, 24, 30, 24);

        var heading = new Panel { Dock = DockStyle.Top, Height = 70 };
        heading.Controls.Add(new Label { Text = DatabaseCatalog.DisplayName(table.Name), AutoSize = true, Font = Theme.Heading, ForeColor = Theme.Text, Location = new Point(0, 0) });
        heading.Controls.Add(new Label { Text = $"Table {table.Name} · gestion complète des enregistrements", AutoSize = true, ForeColor = Theme.MutedText, Location = new Point(2, 39) });
        Controls.Add(heading);

        var actions = new Panel { Dock = DockStyle.Top, Height = 48 };
        _search.PlaceholderText = "Rechercher dans les champs texte…";
        _search.Width = 260;
        _search.Height = 32;
        _search.Location = new Point(0, 2);
        _search.BorderStyle = BorderStyle.FixedSingle;
        _search.KeyDown += (_, e) => { if (e.KeyCode == Keys.Enter) { e.SuppressKeyPress = true; RefreshData(); } };
        actions.Controls.Add(_search);

        var searchButton = Theme.Button("Rechercher", Theme.Primary, Color.White, 108);
        searchButton.Location = new Point(270, 1);
        searchButton.Click += (_, _) => RefreshData();
        actions.Controls.Add(searchButton);

        var newButton = Theme.Button("＋ Nouveau", Theme.Success, Color.White, 112);
        newButton.Location = new Point(390, 1);
        newButton.Click += (_, _) => CreateRecord();
        actions.Controls.Add(newButton);

        var editButton = Theme.Button("Modifier", Color.FromArgb(241, 245, 249), Theme.Text, 95);
        editButton.Location = new Point(512, 1);
        editButton.Click += (_, _) => EditRecord();
        actions.Controls.Add(editButton);

        var deleteButton = Theme.Button("Supprimer", Color.FromArgb(254, 226, 226), Color.FromArgb(185, 28, 28), 100);
        deleteButton.Location = new Point(617, 1);
        deleteButton.Click += (_, _) => DeleteRecord();
        actions.Controls.Add(deleteButton);

        var exportButton = Theme.Button("Exporter CSV", Color.FromArgb(241, 245, 249), Theme.Text, 110);
        exportButton.Location = new Point(727, 1);
        exportButton.Click += (_, _) => Export();
        actions.Controls.Add(exportButton);

        var refreshButton = Theme.Button("↻", Color.FromArgb(241, 245, 249), Theme.Text, 42);
        refreshButton.Location = new Point(847, 1);
        refreshButton.Click += (_, _) => RefreshData();
        actions.Controls.Add(refreshButton);
        Controls.Add(actions);

        var bottom = new Panel { Dock = DockStyle.Bottom, Height = 29 };
        _status.AutoSize = true;
        _status.ForeColor = Theme.MutedText;
        _status.Font = Theme.Small;
        _status.Location = new Point(0, 5);
        bottom.Controls.Add(_status);
        _count.AutoSize = true;
        _count.ForeColor = Theme.MutedText;
        _count.Font = Theme.Small;
        _count.Anchor = AnchorStyles.Top | AnchorStyles.Right;
        bottom.Controls.Add(_count);
        bottom.Resize += (_, _) => _count.Location = new Point(bottom.Width - _count.Width, 5);
        Controls.Add(bottom);

        Theme.StyleGrid(_grid);
        _grid.Dock = DockStyle.Fill;
        _grid.CellDoubleClick += (_, e) => { if (e.RowIndex >= 0) EditRecord(); };
        _grid.CellFormatting += (_, e) =>
        {
            if (e.Value is byte[] bytes) { e.Value = $"<{bytes.Length} octets>"; e.FormattingApplied = true; }
        };
        _grid.KeyDown += GridKeyDown;
        _grid.DataBindingComplete += (_, _) => FormatGrid();
        Controls.Add(_grid);
        Load += (_, _) => RefreshData();
    }

    public void RefreshData()
    {
        try
        {
            Cursor = Cursors.WaitCursor;
            _data = _repository.LoadTable(_table, _search.Text);
            _grid.DataSource = _data;
            _status.Text = _data.Rows.Count >= 1000
                ? "Affichage limité aux 1 000 premiers enregistrements. Utilisez la recherche pour affiner."
                : "Double-cliquez sur une ligne pour la modifier.";
            _count.Text = $"{_data.Rows.Count:N0} ligne(s) affichée(s)";
            _count.Location = new Point(Math.Max(0, Width - _count.Width), 5);
        }
        catch (Exception ex)
        {
            _grid.DataSource = null;
            _status.Text = "Erreur : " + ex.Message;
            _status.ForeColor = Color.FromArgb(185, 28, 28);
        }
        finally { Cursor = Cursors.Default; }
    }

    private void CreateRecord()
    {
        using var editor = new RecordEditorForm(_database, _table, null);
        if (editor.ShowDialog(FindForm()) == DialogResult.OK) RefreshData();
    }

    private void EditRecord()
    {
        var row = SelectedRow();
        if (row is null)
        {
            MessageBox.Show(FindForm(), "Sélectionnez d’abord une ligne.", "Modification", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }
        using var editor = new RecordEditorForm(_database, _table, row);
        if (editor.ShowDialog(FindForm()) == DialogResult.OK) RefreshData();
    }

    private void DeleteRecord()
    {
        var row = SelectedRow();
        if (row is null)
        {
            MessageBox.Show(FindForm(), "Sélectionnez d’abord une ligne.", "Suppression", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }
        var key = _table.PrimaryKeyColumns.FirstOrDefault();
        var identity = key is not null && row.Table.Columns.Contains(key.Name) ? Convert.ToString(row[key.Name]) : "la ligne sélectionnée";
        if (MessageBox.Show(FindForm(), $"Supprimer {identity} de la table {DatabaseCatalog.DisplayName(_table.Name)} ?\n\nCette action est irréversible.", "Confirmer la suppression", MessageBoxButtons.YesNo, MessageBoxIcon.Warning) != DialogResult.Yes)
            return;
        try
        {
            _repository.Delete(_table, row);
            RefreshData();
        }
        catch (Exception ex)
        {
            MessageBox.Show(FindForm(), "Suppression impossible. La ligne est peut-être utilisée par d’autres données.\n\n" + ex.Message, "Erreur", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private void Export()
    {
        if (_data is null) return;
        using var dialog = new SaveFileDialog
        {
            Filter = "Fichier CSV (*.csv)|*.csv|Tous les fichiers (*.*)|*.*",
            FileName = _table.Name.ToLowerInvariant() + ".csv",
            Title = "Exporter les données"
        };
        if (dialog.ShowDialog(FindForm()) != DialogResult.OK) return;
        try
        {
            CsvExporter.Export(_data, dialog.FileName);
            MessageBox.Show(FindForm(), "Export CSV terminé.", "Exportation", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
        catch (Exception ex) { MessageBox.Show(FindForm(), ex.Message, "Exportation impossible", MessageBoxButtons.OK, MessageBoxIcon.Error); }
    }

    private DataRow? SelectedRow()
        => _grid.CurrentRow?.DataBoundItem is DataRowView view ? view.Row : null;

    private void GridKeyDown(object? sender, KeyEventArgs e)
    {
        if (e.KeyCode == Keys.Delete) { e.SuppressKeyPress = true; DeleteRecord(); }
        else if (e.KeyCode == Keys.Enter) { e.SuppressKeyPress = true; EditRecord(); }
        else if (e.KeyCode == Keys.F5) { e.SuppressKeyPress = true; RefreshData(); }
    }

    private void FormatGrid()
    {
        foreach (DataGridViewColumn column in _grid.Columns)
        {
            column.HeaderText = column.Name.Replace('_', ' ');
            column.SortMode = DataGridViewColumnSortMode.NotSortable;
            if (_table.Columns.FirstOrDefault(c => string.Equals(c.Name, column.Name, StringComparison.OrdinalIgnoreCase))?.IsBinary == true)
                column.DefaultCellStyle.NullValue = "<fichier>";
        }
    }
}
