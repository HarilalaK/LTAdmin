using LTAdmin.Models;
using LTAdmin.Models.Entities;
using LTAdmin.Services;

namespace LTAdmin.UI.Views;

/// <summary>Fiche étudiant : création et modification via StudentService.</summary>
public sealed class StudentEditForm : Form
{
    private readonly AppComposition _app;
    private readonly UserSession _session;
    private readonly Etudiant _student;
    private readonly bool _isNew;

    private readonly TextBox _matricule = new();
    private readonly TextBox _nom = new();
    private readonly TextBox _prenom = new();
    private readonly ComboBox _sexe = new();
    private readonly DateTimePicker _naissance = new();
    private readonly TextBox _lieu = new();
    private readonly TextBox _cin = new();
    private readonly TextBox _nationalite = new();
    private readonly TextBox _adresse = new();
    private readonly TextBox _tel = new();
    private readonly TextBox _email = new();
    private readonly TextBox _tuteur = new();
    private readonly TextBox _telTuteur = new();
    private readonly TextBox _professionTuteur = new();
    private readonly TextBox _serieBacc = new();
    private readonly TextBox _anneeBacc = new();
    private readonly TextBox _etabOrigine = new();
    private readonly TextBox _statut = new();

    public StudentEditForm(AppComposition app, UserSession session, Etudiant? student)
    {
        _app = app;
        _session = session;
        _isNew = student?.IdEtudiant is null;
        _student = student ?? new Etudiant();

        Text = _isNew ? "Nouvel étudiant" : $"Modifier — {_student.NomComplet}";
        StartPosition = FormStartPosition.CenterParent;
        MinimumSize = new Size(640, 560);
        Size = new Size(700, 720);
        BackColor = Theme.Background;
        Font = Theme.Body;

        var title = new Panel { Dock = DockStyle.Top, Height = 70, Padding = new Padding(24, 16, 24, 8), BackColor = Theme.Surface };
        title.Controls.Add(new Label { Text = Text, AutoSize = true, Font = Theme.SubHeading, ForeColor = Theme.Text, Location = new Point(24, 14) });
        title.Controls.Add(new Label
        {
            Text = _isNew ? "Le matricule est généré automatiquement s’il est laissé vide." : $"Matricule : {_student.Matricule}",
            AutoSize = true, Font = Theme.Small, ForeColor = Theme.MutedText, Location = new Point(24, 40)
        });
        Controls.Add(title);

        var fields = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            AutoScroll = true,
            ColumnCount = 2,
            Padding = new Padding(24, 12, 24, 12)
        };
        fields.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 170));
        fields.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        Controls.Add(fields);

        AddRow(fields, "Matricule", _matricule, _student.Matricule ?? (_isNew ? "" : ""));
        _matricule.PlaceholderText = _isNew ? "Auto (ETU-AAAA-####)" : "";
        AddRow(fields, "Nom *", _nom, _student.Nom);
        AddRow(fields, "Prénom *", _prenom, _student.Prenom);
        _sexe.DropDownStyle = ComboBoxStyle.DropDownList;
        _sexe.Items.AddRange(new object[] { "", "M", "F" });
        _sexe.SelectedItem = _student.Sexe ?? "";
        AddRow(fields, "Sexe", _sexe);
        _naissance.Format = DateTimePickerFormat.Short;
        _naissance.ShowCheckBox = true;
        _naissance.Checked = _student.DateNaissance.HasValue;
        _naissance.Value = _student.DateNaissance ?? DateTime.Today.AddYears(-18);
        AddRow(fields, "Date de naissance", _naissance);
        AddRow(fields, "Lieu de naissance", _lieu, _student.LieuNaissance);
        AddRow(fields, "CIN", _cin, _student.Cin);
        AddRow(fields, "Nationalité", _nationalite, _student.Nationalite);
        _adresse.Multiline = true;
        _adresse.Height = 52;
        AddRow(fields, "Adresse", _adresse, _student.Adresse);
        AddRow(fields, "Téléphone", _tel, _student.Tel);
        AddRow(fields, "E-mail", _email, _student.Email);
        AddRow(fields, "Nom du tuteur", _tuteur, _student.NomTuteur);
        AddRow(fields, "Tél. tuteur", _telTuteur, _student.TelTuteur);
        AddRow(fields, "Profession tuteur", _professionTuteur, _student.ProfessionTuteur);
        AddRow(fields, "Série du bac", _serieBacc, _student.SerieBacc);
        AddRow(fields, "Année du bac", _anneeBacc, _student.AnneeBacc?.ToString());
        AddRow(fields, "Établissement d’origine", _etabOrigine, _student.EtabOrigine);
        AddRow(fields, "Statut", _statut, _student.Statut ?? (_isNew ? "ACTIF" : ""));

        var footer = new Panel { Dock = DockStyle.Bottom, Height = 64, Padding = new Padding(24, 12, 24, 12) };
        var cancel = Theme.Button("Annuler", Color.FromArgb(241, 245, 249), Theme.Text, 110);
        cancel.Anchor = AnchorStyles.Right;
        cancel.Location = new Point(footer.Width - 240, 12);
        cancel.Click += (_, _) => DialogResult = DialogResult.Cancel;
        footer.Controls.Add(cancel);
        var save = Theme.Button("Enregistrer", Theme.Primary, Color.White, 130);
        save.Anchor = AnchorStyles.Right;
        save.Location = new Point(footer.Width - 120, 12);
        save.Click += (_, _) => Save();
        footer.Controls.Add(save);
        footer.Resize += (_, _) =>
        {
            cancel.Left = footer.Width - 250;
            save.Left = footer.Width - 130;
        };
        Controls.Add(footer);
        AcceptButton = save;
        CancelButton = cancel;
    }

    private static void AddRow(TableLayoutPanel panel, string label, Control editor, string? value = null)
    {
        if (editor is TextBox text && value is not null) text.Text = value;
        editor.Dock = DockStyle.Fill;
        editor.Margin = new Padding(0, 5, 0, 5);
        if (editor is TextBox box) box.BorderStyle = BorderStyle.FixedSingle;
        var row = panel.RowCount++;
        panel.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        panel.Controls.Add(new Label
        {
            Text = label, AutoSize = false, Height = 30, TextAlign = ContentAlignment.MiddleLeft,
            ForeColor = Theme.Text, Font = Theme.Body, Dock = DockStyle.Fill, Margin = new Padding(0, 5, 8, 5)
        }, 0, row);
        panel.Controls.Add(editor, 1, row);
    }

    private void Save()
    {
        int? anneeBacc = null;
        if (!string.IsNullOrWhiteSpace(_anneeBacc.Text))
        {
            if (!int.TryParse(_anneeBacc.Text.Trim(), out var parsed))
            {
                MessageBox.Show(this, "Année du bac : nombre invalide.", "Vérifiez la saisie",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }
            anneeBacc = parsed;
        }

        _student.Matricule = string.IsNullOrWhiteSpace(_matricule.Text) ? null : _matricule.Text.Trim();
        _student.Nom = _nom.Text.Trim();
        _student.Prenom = _prenom.Text.Trim();
        _student.Sexe = string.IsNullOrWhiteSpace(_sexe.Text) ? null : _sexe.Text;
        _student.DateNaissance = _naissance.Checked ? _naissance.Value.Date : null;
        _student.LieuNaissance = BlankToNull(_lieu.Text);
        _student.Cin = BlankToNull(_cin.Text);
        _student.Nationalite = BlankToNull(_nationalite.Text);
        _student.Adresse = BlankToNull(_adresse.Text);
        _student.Tel = BlankToNull(_tel.Text);
        _student.Email = BlankToNull(_email.Text);
        _student.NomTuteur = BlankToNull(_tuteur.Text);
        _student.TelTuteur = BlankToNull(_telTuteur.Text);
        _student.ProfessionTuteur = BlankToNull(_professionTuteur.Text);
        _student.SerieBacc = BlankToNull(_serieBacc.Text);
        _student.AnneeBacc = anneeBacc;
        _student.EtabOrigine = BlankToNull(_etabOrigine.Text);
        _student.Statut = BlankToNull(_statut.Text);

        var result = _isNew
            ? _app.Etudiants.Create(_student, _session.Login).ToResult()
            : _app.Etudiants.Update(_student, _session.Login);
        if (result.IsFailure)
        {
            MessageBox.Show(this, result.FullMessage(), "Vérifiez la saisie", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }
        DialogResult = DialogResult.OK;
        Close();
    }

    private static string? BlankToNull(string value)
        => string.IsNullOrWhiteSpace(value) ? null : value.Trim();
}

internal static class ResultExtensions
{
    public static LTAdmin.Core.Result ToResult<T>(this LTAdmin.Core.Result<T> result)
        => result.IsSuccess
            ? LTAdmin.Core.Result.Ok(result.Message)
            : LTAdmin.Core.Result.Fail(result.Message, result.Code, result.Errors);
}
