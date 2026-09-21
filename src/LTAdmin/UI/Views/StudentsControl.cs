using LTAdmin.Models;
using LTAdmin.Models.Entities;
using LTAdmin.Services;

namespace LTAdmin.UI.Views;

/// <summary>Écran métier des étudiants : recherche + CRUD via StudentService.</summary>
public sealed class StudentsControl : BusinessView
{
    private readonly TextBox _search = new();
    private readonly DataGridView _grid = new();
    private readonly Label _status = new();

    public StudentsControl(AppComposition app, UserSession session) : base(app, session)
    {
        Controls.Add(BuildHeading("Étudiants", "Dossiers des étudiants — recherche, création, modification."));

        var actions = new Panel { Dock = DockStyle.Top, Height = 48 };
        _search.PlaceholderText = "Nom, prénom ou matricule…";
        _search.Width = 260;
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
        newButton.Click += (_, _) => CreateStudent();
        actions.Controls.Add(newButton);

        var editButton = Theme.Button("Modifier", Color.FromArgb(241, 245, 249), Theme.Text, 95);
        editButton.Location = new Point(512, 1);
        editButton.Click += (_, _) => EditStudent();
        actions.Controls.Add(editButton);

        var deleteButton = Theme.Button("Supprimer", Color.FromArgb(254, 226, 226), Color.FromArgb(185, 28, 28), 100);
        deleteButton.Location = new Point(617, 1);
        deleteButton.Click += (_, _) => DeleteStudent();
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
        _grid.Columns.Add(TextColumn(nameof(Etudiant.Matricule), "Matricule", 130));
        _grid.Columns.Add(TextColumn(nameof(Etudiant.Nom), "Nom", 170));
        _grid.Columns.Add(TextColumn(nameof(Etudiant.Prenom), "Prénom", 170));
        _grid.Columns.Add(TextColumn(nameof(Etudiant.Sexe), "Sexe", 60));
        _grid.Columns.Add(TextColumn(nameof(Etudiant.DateNaissance), "Naissance", 110, "d"));
        _grid.Columns.Add(TextColumn(nameof(Etudiant.Tel), "Téléphone", 130));
        _grid.Columns.Add(TextColumn(nameof(Etudiant.Statut), "Statut", 100));
        _grid.CellDoubleClick += (_, e) => { if (e.RowIndex >= 0) EditStudent(); };
        Controls.Add(_grid);
        Load += (_, _) => RefreshData();
    }

    public override void RefreshData()
    {
        try
        {
            Cursor = Cursors.WaitCursor;
            var students = App.Etudiants.Search(_search.Text);
            _grid.DataSource = students;
            _status.Text = $"{students.Count:N0} étudiant(s). Double-cliquez sur une ligne pour la modifier.";
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

    private void CreateStudent()
    {
        using var editor = new StudentEditForm(App, Session, null);
        if (editor.ShowDialog(FindForm()) == DialogResult.OK) RefreshData();
    }

    private void EditStudent()
    {
        var student = SelectedStudent();
        if (student?.IdEtudiant is null)
        {
            ShowInfo("Sélectionnez d’abord un étudiant.", "Modification");
            return;
        }
        using var editor = new StudentEditForm(App, Session, student);
        if (editor.ShowDialog(FindForm()) == DialogResult.OK) RefreshData();
    }

    private void DeleteStudent()
    {
        var student = SelectedStudent();
        if (student?.IdEtudiant is null)
        {
            ShowInfo("Sélectionnez d’abord un étudiant.", "Suppression");
            return;
        }
        if (!Confirm($"Supprimer le dossier de « {student.NomComplet} » ({student.Matricule}) ?\n\nCette action est irréversible.", "Confirmer la suppression"))
            return;
        var result = App.Etudiants.Delete(student.IdEtudiant.Value, CodeUtr);
        if (result.IsFailure) ShowError(result.FullMessage());
        else RefreshData();
    }

    private Etudiant? SelectedStudent()
        => _grid.CurrentRow?.DataBoundItem as Etudiant;
}
