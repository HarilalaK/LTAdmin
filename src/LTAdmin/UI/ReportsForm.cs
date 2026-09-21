using System.Data;
using LTAdmin.Data;
using LTAdmin.Services;

namespace LTAdmin.UI;

/// <summary>Read-only viewer for the saved Access reports already delivered with the database.</summary>
public sealed class ReportsForm : Form
{
    private readonly DatabaseRepository _repository;
    private readonly ComboBox _queries = new();
    private readonly DataGridView _grid = new();
    private readonly Label _status = new();
    private DataTable? _data;

    public ReportsForm(AccessDatabase database)
    {
        _repository = new DatabaseRepository(database);
        Text = "LTAdmin — États et requêtes";
        StartPosition = FormStartPosition.CenterParent;
        WindowState = FormWindowState.Maximized;
        MinimumSize = new Size(900, 580);
        BackColor = Theme.Background;
        Padding = new Padding(28, 22, 28, 22);

        var heading = new Panel { Dock = DockStyle.Top, Height = 72 };
        heading.Controls.Add(new Label { Text = "États et requêtes", AutoSize = true, Font = Theme.Heading, ForeColor = Theme.Text, Location = new Point(0, 0) });
        heading.Controls.Add(new Label { Text = "Consultez les requêtes déjà livrées avec LTA_ADM.accdb et exportez leurs résultats.", AutoSize = true, ForeColor = Theme.MutedText, Location = new Point(2, 39) });
        Controls.Add(heading);

        var toolbar = new Panel { Dock = DockStyle.Top, Height = 50 };
        _queries.DropDownStyle = ComboBoxStyle.DropDownList;
        _queries.Width = 300;
        _queries.Height = 32;
        _queries.Location = new Point(0, 2);
        _queries.Font = Theme.Body;
        toolbar.Controls.Add(_queries);
        var run = Theme.Button("Exécuter", Theme.Primary, Color.White, 105);
        run.Location = new Point(312, 1);
        run.Click += (_, _) => RunQuery();
        toolbar.Controls.Add(run);
        var export = Theme.Button("Exporter CSV", Color.FromArgb(241, 245, 249), Theme.Text, 115);
        export.Location = new Point(427, 1);
        export.Click += (_, _) => Export();
        toolbar.Controls.Add(export);
        Controls.Add(toolbar);

        Theme.StyleGrid(_grid);
        _grid.Dock = DockStyle.Fill;
        Controls.Add(_grid);
        var footer = new Panel { Dock = DockStyle.Bottom, Height = 28 };
        _status.AutoSize = true;
        _status.Font = Theme.Small;
        _status.ForeColor = Theme.MutedText;
        _status.Location = new Point(0, 4);
        footer.Controls.Add(_status);
        Controls.Add(footer);
        Load += (_, _) => LoadQueries();
    }

    private void LoadQueries()
    {
        try
        {
            _queries.DataSource = _repository.GetSavedQueries().ToList();
            if (_queries.Items.Count > 0) RunQuery();
            else _status.Text = "Aucune requête enregistrée trouvée.";
        }
        catch (Exception ex) { _status.Text = ex.Message; }
    }

    private void RunQuery()
    {
        if (_queries.SelectedItem is not string queryName) return;
        try
        {
            Cursor = Cursors.WaitCursor;
            _data = _repository.LoadSavedQuery(queryName);
            _grid.DataSource = _data;
            foreach (DataGridViewColumn column in _grid.Columns) column.HeaderText = column.Name.Replace('_', ' ');
            _status.Text = $"{queryName} · {_data.Rows.Count:N0} ligne(s)";
        }
        catch (Exception ex)
        {
            _grid.DataSource = null;
            _status.Text = $"{queryName} : cette requête nécessite peut-être des paramètres Access. {ex.Message}";
        }
        finally { Cursor = Cursors.Default; }
    }

    private void Export()
    {
        if (_data is null) return;
        using var dialog = new SaveFileDialog { Filter = "Fichier CSV (*.csv)|*.csv|Tous les fichiers (*.*)|*.*", FileName = (_queries.SelectedItem?.ToString() ?? "rapport") + ".csv" };
        if (dialog.ShowDialog(this) != DialogResult.OK) return;
        try
        {
            CsvExporter.Export(_data, dialog.FileName);
            MessageBox.Show(this, "Export CSV terminé.", "Exportation", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
        catch (Exception ex) { MessageBox.Show(this, ex.Message, "Exportation impossible", MessageBoxButtons.OK, MessageBoxIcon.Error); }
    }
}
