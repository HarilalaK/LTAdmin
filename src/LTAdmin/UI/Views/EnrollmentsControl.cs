using LTAdmin.Models;
using LTAdmin.Models.Dto;
using LTAdmin.Services;

namespace LTAdmin.UI.Views;

/// <summary>Écran métier des inscriptions : filtre par classe, inscription, échéancier.</summary>
public sealed class EnrollmentsControl : BusinessView
{
    private readonly ComboBox _classes = new();
    private readonly DataGridView _grid = new();
    private readonly Label _status = new();

    public EnrollmentsControl(AppComposition app, UserSession session) : base(app, session)
    {
        Controls.Add(BuildHeading("Inscriptions", "Inscriptions par classe — historique et redoublements."));

        var actions = new Panel { Dock = DockStyle.Top, Height = 48 };
        _classes.DropDownStyle = ComboBoxStyle.DropDownList;
        _classes.Width = 250;
        _classes.Location = new Point(0, 2);
        _classes.Font = Theme.Body;
        _classes.SelectedIndexChanged += (_, _) => RefreshData();
        actions.Controls.Add(_classes);

        var newButton = Theme.Button("＋ Inscrire", Theme.Success, Color.White, 112);
        newButton.Location = new Point(260, 1);
        newButton.Click += (_, _) => CreateEnrollment();
        actions.Controls.Add(newButton);

        var editButton = Theme.Button("Modifier", Color.FromArgb(241, 245, 249), Theme.Text, 95);
        editButton.Location = new Point(382, 1);
        editButton.Click += (_, _) => EditEnrollment();
        actions.Controls.Add(editButton);

        var scheduleButton = Theme.Button("Échéancier", Color.FromArgb(241, 245, 249), Theme.Text, 105);
        scheduleButton.Location = new Point(487, 1);
        scheduleButton.Click += (_, _) => GenerateSchedule();
        actions.Controls.Add(scheduleButton);

        var deleteButton = Theme.Button("Supprimer", Color.FromArgb(254, 226, 226), Color.FromArgb(185, 28, 28), 100);
        deleteButton.Location = new Point(602, 1);
        deleteButton.Click += (_, _) => DeleteEnrollment();
        actions.Controls.Add(deleteButton);
        Controls.Add(actions);

        var bottom = new Panel { Dock = DockStyle.Bottom, Height = 29 };
        _status.AutoSize = true;
        _status.ForeColor = Theme.MutedText;
        _status.Font = Theme.Small;
        _status.Location = new Point(0, 5);
        bottom.Controls.Add(_status);
        Controls.Add(bottom);

        Theme.StyleGrid(_grid);
        _grid.Dock = DockStyle.Fill;
        _grid.AutoGenerateColumns = false;
        _grid.Columns.Add(TextColumn(nameof(InscriptionDetail.NumInscription), "N°", 130));
        _grid.Columns.Add(TextColumn(nameof(InscriptionDetail.Matricule), "Matricule", 120));
        _grid.Columns.Add(TextColumn(nameof(InscriptionDetail.Nom), "Nom", 150));
        _grid.Columns.Add(TextColumn(nameof(InscriptionDetail.Prenom), "Prénom", 150));
        _grid.Columns.Add(TextColumn(nameof(InscriptionDetail.Classe), "Classe", 150));
        _grid.Columns.Add(TextColumn(nameof(InscriptionDetail.DateInscription), "Inscrit le", 105, "d"));
        _grid.Columns.Add(CheckColumn(nameof(InscriptionDetail.Redoublant), "Red.", 55));
        _grid.Columns.Add(TextColumn(nameof(InscriptionDetail.Statut), "Statut", 100));
        _grid.CellDoubleClick += (_, e) => { if (e.RowIndex >= 0) EditEnrollment(); };
        Controls.Add(_grid);
        Load += (_, _) => LoadClasses();
    }

    private void LoadClasses()
    {
        try
        {
            var classes = new List<ClasseDetail> { new() { Libelle = "Toutes les classes" } };
            classes.AddRange(App.Referentiel.ListClassesDetail(null));
            _classes.DisplayMember = nameof(ClasseDetail.Libelle);
            _classes.DataSource = classes;
        }
        catch (Exception ex) { _status.Text = "Erreur : " + ex.Message; }
    }

    public override void RefreshData()
    {
        try
        {
            Cursor = Cursors.WaitCursor;
            List<InscriptionDetail> rows;
            if (_classes.SelectedItem is ClasseDetail classe && classe.IdClasse.HasValue)
                rows = App.Inscriptions.ListByClasse(classe.IdClasse.Value);
            else
                rows = App.Statistiques.GetAnneeActive()?.IdAnnee is int annee
                    ? LoadByAnnee(annee)
                    : new List<InscriptionDetail>();
            _grid.DataSource = rows;
            _status.Text = $"{rows.Count:N0} inscription(s).";
            _status.ForeColor = Theme.MutedText;
        }
        catch (Exception ex)
        {
            _grid.DataSource = null;
            _status.Text = "Erreur : " + ex.Message;
            _status.ForeColor = Color.FromArgb(185, 28, 28);
        }
        finally { Cursor = Cursors.Default; }
    }

    private List<InscriptionDetail> LoadByAnnee(int idAnnee)
    {
        var rows = new List<InscriptionDetail>();
        foreach (var classe in App.Referentiel.ListClasses(idAnnee))
        {
            if (classe.IdClasse.HasValue)
                rows.AddRange(App.Inscriptions.ListByClasse(classe.IdClasse.Value));
        }
        return rows;
    }

    private void CreateEnrollment()
    {
        using var editor = new EnrollmentEditForm(App, Session, null, SelectedClasseId());
        if (editor.ShowDialog(FindForm()) == DialogResult.OK) RefreshData();
    }

    private void EditEnrollment()
    {
        var row = SelectedRow();
        if (row?.IdInscription is null)
        {
            ShowInfo("Sélectionnez d’abord une inscription.", "Modification");
            return;
        }
        var inscription = App.Inscriptions.Get(row.IdInscription.Value);
        if (inscription is null)
        {
            ShowError("Inscription introuvable.");
            return;
        }
        using var editor = new EnrollmentEditForm(App, Session, inscription, null);
        if (editor.ShowDialog(FindForm()) == DialogResult.OK) RefreshData();
    }

    private void GenerateSchedule()
    {
        var row = SelectedRow();
        if (row?.IdInscription is null)
        {
            ShowInfo("Sélectionnez d’abord une inscription.", "Échéancier");
            return;
        }
        if (!Confirm($"Générer les tranches d’échéancier manquantes pour « {row.NomComplet} » ?\n\nLes tranches existantes sont conservées.",
            "Générer l’échéancier"))
            return;
        var result = App.Ecolage.GenererEcheancier(row.IdInscription.Value, CodeUtr);
        if (result.IsFailure) ShowError(result.FullMessage());
        else ShowInfo(result.Message, "Échéancier");
    }

    private void DeleteEnrollment()
    {
        var row = SelectedRow();
        if (row?.IdInscription is null)
        {
            ShowInfo("Sélectionnez d’abord une inscription.", "Suppression");
            return;
        }
        if (!Confirm($"Supprimer l’inscription {row.NumInscription} de « {row.NomComplet} » ?\n\nCette action est irréversible.", "Confirmer la suppression"))
            return;
        var result = App.Inscriptions.Delete(row.IdInscription.Value, CodeUtr);
        if (result.IsFailure) ShowError(result.FullMessage());
        else RefreshData();
    }

    private InscriptionDetail? SelectedRow()
        => _grid.CurrentRow?.DataBoundItem as InscriptionDetail;

    private int? SelectedClasseId()
        => _classes.SelectedItem is ClasseDetail classe ? classe.IdClasse : null;
}
