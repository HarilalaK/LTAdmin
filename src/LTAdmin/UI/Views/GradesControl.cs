using System.Data;
using System.Globalization;
using LTAdmin.Models;
using LTAdmin.Models.Dto;
using LTAdmin.Models.Entities;
using LTAdmin.Services;

namespace LTAdmin.UI.Views;

/// <summary>Saisie des notes de contrôle continu : évaluation puis grille par inscrit.</summary>
public sealed class GradesControl : BusinessView
{
    private readonly ComboBox _classes = new();
    private readonly ComboBox _periodes = new();
    private readonly DataGridView _evaluations = new();
    private readonly DataGridView _notes = new();
    private readonly Label _status = new();
    private readonly Button _saveButton;

    public GradesControl(AppComposition app, UserSession session) : base(app, session)
    {
        Controls.Add(BuildHeading("Saisie des notes", "Choisissez une évaluation, saisissez les notes, puis enregistrez."));

        var filters = new Panel { Dock = DockStyle.Top, Height = 44 };
        filters.Controls.Add(new Label { Text = "Classe :", AutoSize = true, ForeColor = Theme.Text, Location = new Point(0, 8) });
        _classes.DropDownStyle = ComboBoxStyle.DropDownList;
        _classes.Width = 250;
        _classes.Location = new Point(58, 4);
        _classes.Font = Theme.Body;
        _classes.SelectedIndexChanged += (_, _) => RefreshEvaluations();
        filters.Controls.Add(_classes);
        filters.Controls.Add(new Label { Text = "Période :", AutoSize = true, ForeColor = Theme.Text, Location = new Point(320, 8) });
        _periodes.DropDownStyle = ComboBoxStyle.DropDownList;
        _periodes.Width = 230;
        _periodes.Location = new Point(388, 4);
        _periodes.Font = Theme.Body;
        _periodes.SelectedIndexChanged += (_, _) => RefreshEvaluations();
        filters.Controls.Add(_periodes);
        _saveButton = Theme.Button("Enregistrer", Theme.Success, Color.White, 130);
        _saveButton.Location = new Point(640, 3);
        _saveButton.Click += (_, _) => SaveNotes();
        filters.Controls.Add(_saveButton);
        Controls.Add(filters);

        var bottom = new Panel { Dock = DockStyle.Bottom, Height = 29 };
        _status.AutoSize = true;
        _status.ForeColor = Theme.MutedText;
        _status.Font = Theme.Small;
        _status.Location = new Point(0, 5);
        bottom.Controls.Add(_status);
        Controls.Add(bottom);

        var split = new SplitContainer { Dock = DockStyle.Fill, Orientation = Orientation.Horizontal, SplitterDistance = 200 };
        Controls.Add(split);

        Theme.StyleGrid(_evaluations);
        _evaluations.Dock = DockStyle.Fill;
        _evaluations.AutoGenerateColumns = false;
        _evaluations.Columns.Add(TextColumn(nameof(EvaluationDetail.DateEval), "Date", 100, "d"));
        _evaluations.Columns.Add(TextColumn(nameof(EvaluationDetail.Matiere), "Matière", 200));
        _evaluations.Columns.Add(TextColumn(nameof(EvaluationDetail.Intitule), "Intitulé", 220));
        _evaluations.Columns.Add(TextColumn(nameof(EvaluationDetail.Bareme), "Barème", 80));
        _evaluations.Columns.Add(TextColumn(nameof(EvaluationDetail.Poids), "Poids", 80));
        _evaluations.Columns.Add(CheckColumn(nameof(EvaluationDetail.Publiee), "Publiée", 80));
        _evaluations.SelectionChanged += (_, _) => RefreshNotes();
        split.Panel1.Controls.Add(_evaluations);

        Theme.StyleGrid(_notes);
        _notes.Dock = DockStyle.Fill;
        _notes.ReadOnly = false;
        split.Panel2.Controls.Add(_notes);

        Load += (_, _) => LoadFilters();
    }

    private void LoadFilters()
    {
        try
        {
            var classes = App.Referentiel.ListClassesDetail(null);
            _classes.DisplayMember = nameof(ClasseDetail.Libelle);
            _classes.DataSource = classes;
            var periodes = App.Evaluations.ListPeriodes(null);
            _periodes.DisplayMember = nameof(PeriodeEval.Libelle);
            _periodes.DataSource = periodes;
            RefreshEvaluations();
        }
        catch (Exception ex) { _status.Text = "Erreur : " + ex.Message; }
    }

    public override void RefreshData() => RefreshEvaluations();

    private void RefreshEvaluations()
    {
        try
        {
            Cursor = Cursors.WaitCursor;
            var idClasse = (_classes.SelectedItem as ClasseDetail)?.IdClasse;
            var idPeriode = (_periodes.SelectedItem as PeriodeEval)?.IdPeriode;
            var rows = App.Evaluations.ListEvaluations(idPeriode, idClasse);
            _evaluations.DataSource = rows;
            _status.Text = $"{rows.Count:N0} évaluation(s).";
            _status.ForeColor = Theme.MutedText;
            RefreshNotes();
        }
        catch (Exception ex)
        {
            _status.Text = "Erreur : " + ex.Message;
            _status.ForeColor = Color.FromArgb(185, 28, 28);
        }
        finally { Cursor = Cursors.Default; }
    }

    private void RefreshNotes()
    {
        try
        {
            var evaluation = _evaluations.CurrentRow?.DataBoundItem as EvaluationDetail;
            if (evaluation?.IdEvaluation is null)
            {
                _notes.DataSource = null;
                _saveButton.Enabled = false;
                return;
            }
            var table = new DataTable();
            table.Columns.Add("ID_INSCRIPTION", typeof(int));
            table.Columns.Add("Matricule", typeof(string));
            table.Columns.Add("Nom", typeof(string));
            table.Columns.Add("Prénom", typeof(string));
            table.Columns.Add("Note", typeof(string));
            table.Columns.Add("Absent", typeof(bool));
            table.Columns.Add("Observation", typeof(string));
            foreach (var row in App.Notes.GetGrilleSaisie(evaluation.IdEvaluation.Value))
            {
                table.Rows.Add(
                    row.IdInscription ?? 0,
                    row.Matricule ?? "",
                    row.Nom ?? "",
                    row.Prenom ?? "",
                    row.ValeurNote?.ToString("N2", CultureInfo.CurrentCulture) ?? "",
                    row.Absent,
                    row.Observation ?? "");
            }
            _notes.DataSource = table;
            foreach (DataGridViewColumn column in _notes.Columns)
            {
                column.SortMode = DataGridViewColumnSortMode.NotSortable;
                column.ReadOnly = column.Name is not ("Note" or "Absent" or "Observation");
            }
            _notes.Columns["ID_INSCRIPTION"]!.Visible = false;

            var cloturee = evaluation.PeriodeCloturee == true;
            _saveButton.Enabled = !cloturee;
            _status.Text = cloturee
                ? $"Période « {evaluation.Periode} » clôturée : notes figées (barème {evaluation.Bareme})."
                : $"{table.Rows.Count:N0} inscrit(s) — barème {evaluation.Bareme}, note entre 0 et {evaluation.Bareme} (ou absent).";
            _status.ForeColor = cloturee ? Color.FromArgb(185, 28, 28) : Theme.MutedText;
        }
        catch (Exception ex)
        {
            _notes.DataSource = null;
            _status.Text = "Erreur : " + ex.Message;
        }
    }

    private void SaveNotes()
    {
        var evaluation = _evaluations.CurrentRow?.DataBoundItem as EvaluationDetail;
        if (evaluation?.IdEvaluation is null) return;
        if (_notes.DataSource is not DataTable table) return;
        _notes.EndEdit();

        var saved = 0;
        var errors = new List<string>();
        foreach (DataRow row in table.Rows)
        {
            var idInscription = Convert.ToInt32(row["ID_INSCRIPTION"], CultureInfo.InvariantCulture);
            var absent = row["Absent"] is bool b && b;
            double? valeur = null;
            var text = Convert.ToString(row["Note"])?.Trim() ?? "";
            if (!absent && !string.IsNullOrEmpty(text))
            {
                if (!double.TryParse(text, NumberStyles.Float, CultureInfo.CurrentCulture, out var parsed)
                    && !double.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out parsed))
                {
                    errors.Add($"{row["Nom"]} {row["Prénom"]} : note « {text} » illisible.");
                    continue;
                }
                valeur = parsed;
            }
            if (!absent && valeur is null) continue; // Ligne vide : rien à enregistrer.
            var observation = Convert.ToString(row["Observation"])?.Trim();
            var result = App.Notes.UpsertNote(evaluation.IdEvaluation.Value, idInscription, valeur, absent,
                string.IsNullOrEmpty(observation) ? null : observation, CodeUtr);
            if (result.IsFailure) errors.Add($"{row["Nom"]} {row["Prénom"]} : {result.Message}");
            else saved++;
        }

        if (errors.Count == 0) ShowInfo($"{saved} note(s) enregistrée(s).", "Saisie des notes");
        else ShowError($"{saved} note(s) enregistrée(s).\n\n" + string.Join("\n", errors.Take(15)), "Saisie terminée avec des erreurs");
        RefreshNotes();
    }
}
