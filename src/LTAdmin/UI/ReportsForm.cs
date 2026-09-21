using System.Data;
using LTAdmin.Models.Dto;
using LTAdmin.Models.Entities;
using LTAdmin.Services;
using LTAdmin.Services.Reports;

namespace LTAdmin.UI;

/// <summary>États : les 8 requêtes Access livrées, avec filtres et export CSV.</summary>
public sealed class ReportsForm : Form
{
    private readonly AppComposition _app;
    private readonly ComboBox _reports = new();
    private readonly ComboBox _classes = new();
    private readonly ComboBox _periodes = new();
    private readonly Label _description = new();
    private readonly DataGridView _grid = new();
    private readonly Label _status = new();
    private DataTable? _data;
    private string? _currentName;

    public ReportsForm(AppComposition app)
    {
        _app = app;
        Text = "LTAdmin — États et requêtes";
        StartPosition = FormStartPosition.CenterParent;
        WindowState = FormWindowState.Maximized;
        MinimumSize = new Size(900, 580);
        BackColor = Theme.Background;
        Padding = new Padding(28, 22, 28, 22);

        var heading = new Panel { Dock = DockStyle.Top, Height = 72 };
        heading.Controls.Add(new Label { Text = "États et requêtes", AutoSize = true, Font = Theme.Heading, ForeColor = Theme.Text, Location = new Point(0, 0) });
        heading.Controls.Add(new Label { Text = "Consultez les requêtes livrées avec LTA_ADM.accdb et exportez leurs résultats.", AutoSize = true, ForeColor = Theme.MutedText, Location = new Point(2, 39) });
        Controls.Add(heading);

        var toolbar = new Panel { Dock = DockStyle.Top, Height = 86 };
        _reports.DropDownStyle = ComboBoxStyle.DropDownList;
        _reports.Width = 300;
        _reports.Location = new Point(0, 2);
        _reports.Font = Theme.Body;
        _reports.SelectedIndexChanged += (_, _) => { UpdateFilters(); RunReport(); };
        toolbar.Controls.Add(_reports);
        var run = Theme.Button("Exécuter", Theme.Primary, Color.White, 105);
        run.Location = new Point(312, 1);
        run.Click += (_, _) => RunReport();
        toolbar.Controls.Add(run);
        var export = Theme.Button("Exporter CSV", Color.FromArgb(241, 245, 249), Theme.Text, 115);
        export.Location = new Point(427, 1);
        export.Click += (_, _) => Export();
        toolbar.Controls.Add(export);

        _description.AutoSize = false;
        _description.Width = 560;
        _description.Height = 20;
        _description.Location = new Point(0, 40);
        _description.Font = Theme.Small;
        _description.ForeColor = Theme.MutedText;
        toolbar.Controls.Add(_description);

        _classes.DropDownStyle = ComboBoxStyle.DropDownList;
        _classes.Width = 260;
        _classes.Location = new Point(0, 60 - 22);
        _classes.Visible = false;
        _classes.Font = Theme.Body;
        toolbar.Controls.Add(_classes);
        _periodes.DropDownStyle = ComboBoxStyle.DropDownList;
        _periodes.Width = 240;
        _periodes.Location = new Point(270, 60 - 22);
        _periodes.Visible = false;
        _periodes.Font = Theme.Body;
        toolbar.Controls.Add(_periodes);
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
        Load += (_, _) => LoadReports();
    }

    private void LoadReports()
    {
        try
        {
            var reports = _app.Etats.ListReports().ToList();
            _reports.DisplayMember = nameof(ReportDefinition.Title);
            _reports.ValueMember = nameof(ReportDefinition.Name);
            _reports.DataSource = reports;

            var classes = new List<ClasseDetail> { new() { Libelle = "Toutes les classes" } };
            classes.AddRange(_app.Referentiel.ListClassesDetail(null));
            _classes.DisplayMember = nameof(ClasseDetail.Libelle);
            _classes.DataSource = classes;

            var periodes = new List<PeriodeEval> { new() { Libelle = "Toutes les périodes" } };
            periodes.AddRange(_app.Evaluations.ListPeriodes(null));
            _periodes.DisplayMember = nameof(PeriodeEval.Libelle);
            _periodes.DataSource = periodes;

            if (_reports.Items.Count > 0) { _reports.SelectedIndex = 0; UpdateFilters(); RunReport(); }
            else _status.Text = "Aucun état disponible.";
        }
        catch (Exception ex) { _status.Text = ex.Message; }
    }

    private void UpdateFilters()
    {
        var definition = _reports.SelectedItem as ReportDefinition;
        _description.Text = definition?.Description ?? "";
        _classes.Visible = definition?.FilterByClasse == true;
        _periodes.Visible = definition?.FilterByPeriode == true;
        _classes.Location = new Point(0, 60);
        _periodes.Location = new Point(_classes.Visible ? 270 : 0, 60);
    }

    private ReportFilter BuildFilter()
    {
        var filter = new ReportFilter();
        if (_classes.Visible && _classes.SelectedItem is ClasseDetail classe && classe.IdClasse.HasValue)
        {
            filter.IdClasse = classe.IdClasse;
            filter.ClasseLibelle = classe.Libelle;
        }
        if (_periodes.Visible && _periodes.SelectedItem is PeriodeEval periode && periode.IdPeriode.HasValue)
        {
            filter.IdPeriode = periode.IdPeriode;
            filter.PeriodeLibelle = periode.Libelle;
        }
        return filter;
    }

    private void RunReport()
    {
        if (_reports.SelectedItem is not ReportDefinition definition) return;
        try
        {
            Cursor = Cursors.WaitCursor;
            var result = _app.Etats.GetReportData(definition.Name, BuildFilter());
            if (result.IsFailure || result.Value is null)
            {
                _grid.DataSource = null;
                _status.Text = result.FullMessage();
                return;
            }
            _data = result.Value;
            _currentName = definition.Name;
            _grid.DataSource = _data;
            foreach (DataGridViewColumn column in _grid.Columns) column.HeaderText = column.Name.Replace('_', ' ');
            _status.Text = $"{definition.Title} · {_data.Rows.Count:N0} ligne(s)";
        }
        catch (Exception ex)
        {
            _grid.DataSource = null;
            _status.Text = ex.Message;
        }
        finally { Cursor = Cursors.Default; }
    }

    private void Export()
    {
        if (_data is null || _currentName is null) return;
        using var dialog = new SaveFileDialog { Filter = "Fichier CSV (*.csv)|*.csv|Tous les fichiers (*.*)|*.*", FileName = _currentName + ".csv" };
        if (dialog.ShowDialog(this) != DialogResult.OK) return;
        var result = _app.Etats.ExportCsv(_currentName, BuildFilter(), dialog.FileName);
        MessageBox.Show(this, result.FullMessage(), result.IsSuccess ? "Exportation" : "Exportation impossible",
            MessageBoxButtons.OK, result.IsSuccess ? MessageBoxIcon.Information : MessageBoxIcon.Error);
    }
}
