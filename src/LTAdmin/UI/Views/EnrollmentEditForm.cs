using LTAdmin.Models;
using LTAdmin.Models.Dto;
using LTAdmin.Models.Entities;
using LTAdmin.Services;

namespace LTAdmin.UI.Views;

/// <summary>Fiche d'inscription : nouvelle inscription (recherche étudiant) ou modification.</summary>
public sealed class EnrollmentEditForm : Form
{
    private readonly AppComposition _app;
    private readonly UserSession _session;
    private readonly Inscription _inscription;
    private readonly bool _isNew;

    private readonly TextBox _studentSearch = new();
    private readonly ListBox _studentResults = new();
    private readonly Label _studentFixed = new();
    private readonly ComboBox _classes = new();
    private readonly Label _classeFixed = new();
    private readonly TextBox _numero = new();
    private readonly DateTimePicker _dateInscription = new();
    private readonly CheckBox _redoublant = new();
    private readonly TextBox _statut = new();
    private readonly DateTimePicker _dateSortie = new();
    private readonly TextBox _motifSortie = new();

    public EnrollmentEditForm(AppComposition app, UserSession session, Inscription? inscription, int? defaultClasseId)
    {
        _app = app;
        _session = session;
        _isNew = inscription?.IdInscription is null;
        _inscription = inscription ?? new Inscription { IdClasse = defaultClasseId };

        Text = _isNew ? "Nouvelle inscription" : "Modifier l’inscription";
        StartPosition = FormStartPosition.CenterParent;
        MinimumSize = new Size(600, 560);
        Size = new Size(640, 680);
        BackColor = Theme.Background;
        Font = Theme.Body;

        var title = new Panel { Dock = DockStyle.Top, Height = 70, Padding = new Padding(24, 16, 24, 8), BackColor = Theme.Surface };
        title.Controls.Add(new Label { Text = Text, AutoSize = true, Font = Theme.SubHeading, ForeColor = Theme.Text, Location = new Point(24, 14) });
        title.Controls.Add(new Label
        {
            Text = _isNew ? "Recherchez l’étudiant, choisissez la classe, puis validez." : "L’étudiant et la classe ne sont plus modifiables.",
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
        fields.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 160));
        fields.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        Controls.Add(fields);

        if (_isNew)
        {
            var searchPanel = new Panel { Dock = DockStyle.Fill, Height = 150 };
            _studentSearch.PlaceholderText = "Nom, prénom ou matricule…";
            _studentSearch.BorderStyle = BorderStyle.FixedSingle;
            _studentSearch.Width = 230;
            _studentSearch.Location = new Point(0, 0);
            _studentSearch.KeyDown += (_, e) => { if (e.KeyCode == Keys.Enter) { e.SuppressKeyPress = true; SearchStudents(); } };
            searchPanel.Controls.Add(_studentSearch);
            var searchButton = Theme.Button("Rechercher", Theme.Primary, Color.White, 105);
            searchButton.Location = new Point(238, 0);
            searchButton.Height = 28;
            searchButton.Click += (_, _) => SearchStudents();
            searchPanel.Controls.Add(searchButton);
            _studentResults.FormattingEnabled = true;
            _studentResults.Location = new Point(0, 34);
            _studentResults.Width = 343;
            _studentResults.Height = 110;
            _studentResults.BorderStyle = BorderStyle.FixedSingle;
            _studentResults.Format += (_, e) =>
            {
                e.Value = e.ListItem is Etudiant etudiant
                    ? $"{etudiant.Matricule} — {etudiant.NomComplet}" : "";
            };
            searchPanel.Controls.Add(_studentResults);
            AddRow(fields, "Étudiant *", searchPanel);

            _classes.DropDownStyle = ComboBoxStyle.DropDownList;
            AddRow(fields, "Classe *", _classes);
        }
        else
        {
            _studentFixed.AutoSize = false;
            _studentFixed.Height = 28;
            _studentFixed.Dock = DockStyle.Fill;
            _studentFixed.Font = Theme.BodyBold;
            _studentFixed.ForeColor = Theme.Text;
            AddRow(fields, "Étudiant", _studentFixed);
            _classeFixed.AutoSize = false;
            _classeFixed.Height = 28;
            _classeFixed.Dock = DockStyle.Fill;
            _classeFixed.Font = Theme.BodyBold;
            _classeFixed.ForeColor = Theme.Text;
            AddRow(fields, "Classe", _classeFixed);
        }

        _numero.PlaceholderText = "Auto (INS-AAAA-####)";
        AddRow(fields, "N° d’inscription", _numero, _inscription.NumInscription);
        _dateInscription.Format = DateTimePickerFormat.Short;
        _dateInscription.Value = _inscription.DateInscription ?? DateTime.Today;
        AddRow(fields, "Date d’inscription", _dateInscription);
        _redoublant.Text = "Redoublant";
        _redoublant.Checked = _inscription.Redoublant == true;
        AddRow(fields, "Parcours", _redoublant);
        AddRow(fields, "Statut", _statut, _inscription.Statut ?? (_isNew ? "INSCRIT" : ""));
        _dateSortie.Format = DateTimePickerFormat.Short;
        _dateSortie.ShowCheckBox = true;
        _dateSortie.Checked = _inscription.DateSortie.HasValue;
        _dateSortie.Value = _inscription.DateSortie ?? DateTime.Today;
        AddRow(fields, "Date de sortie", _dateSortie);
        _motifSortie.Multiline = true;
        _motifSortie.Height = 52;
        AddRow(fields, "Motif de sortie", _motifSortie, _inscription.MotifSortie);

        var footer = new Panel { Dock = DockStyle.Bottom, Height = 64, Padding = new Padding(24, 12, 24, 12) };
        var cancel = Theme.Button("Annuler", Color.FromArgb(241, 245, 249), Theme.Text, 110);
        cancel.Anchor = AnchorStyles.Right;
        cancel.Click += (_, _) => DialogResult = DialogResult.Cancel;
        footer.Controls.Add(cancel);
        var save = Theme.Button("Enregistrer", Theme.Primary, Color.White, 130);
        save.Anchor = AnchorStyles.Right;
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

        Load += (_, _) => Initialize();
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

    private void Initialize()
    {
        if (_isNew)
        {
            var classes = _app.Referentiel.ListClassesDetail(null);
            _classes.DisplayMember = nameof(ClasseDetail.Libelle);
            _classes.DataSource = classes;
            if (_inscription.IdClasse.HasValue)
            {
                var index = classes.FindIndex(c => c.IdClasse == _inscription.IdClasse);
                if (index >= 0) _classes.SelectedIndex = index;
            }
        }
        else
        {
            var detail = _inscription.IdInscription.HasValue
                ? _app.Inscriptions.GetDetail(_inscription.IdInscription.Value) : null;
            _studentFixed.Text = detail is null
                ? $"Étudiant #{_inscription.IdEtudiant}"
                : $"{detail.Matricule} — {detail.NomComplet}";
            _classeFixed.Text = detail?.Classe ?? $"Classe #{_inscription.IdClasse}";
        }
    }

    private void SearchStudents()
    {
        try
        {
            Cursor = Cursors.WaitCursor;
            _studentResults.DataSource = _app.Etudiants.Search(_studentSearch.Text, 100);
        }
        finally { Cursor = Cursors.Default; }
    }

    private void Save()
    {
        if (_isNew)
        {
            if (_studentResults.SelectedItem is not Etudiant etudiant || etudiant.IdEtudiant is null)
            {
                MessageBox.Show(this, "Recherchez puis sélectionnez l’étudiant à inscrire.", "Vérifiez la saisie",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }
            if (_classes.SelectedItem is not ClasseDetail classe || classe.IdClasse is null)
            {
                MessageBox.Show(this, "Choisissez la classe d’inscription.", "Vérifiez la saisie",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }
            _inscription.IdEtudiant = etudiant.IdEtudiant;
            _inscription.IdClasse = classe.IdClasse;
        }

        _inscription.NumInscription = string.IsNullOrWhiteSpace(_numero.Text) ? null : _numero.Text.Trim();
        _inscription.DateInscription = _dateInscription.Value.Date;
        _inscription.Redoublant = _redoublant.Checked;
        _inscription.Statut = string.IsNullOrWhiteSpace(_statut.Text) ? null : _statut.Text.Trim();
        _inscription.DateSortie = _dateSortie.Checked ? _dateSortie.Value.Date : null;
        _inscription.MotifSortie = string.IsNullOrWhiteSpace(_motifSortie.Text) ? null : _motifSortie.Text.Trim();

        var result = _isNew
            ? _app.Inscriptions.Inscrire(_inscription, _session.Login).ToResult()
            : _app.Inscriptions.Update(_inscription, _session.Login);
        if (result.IsFailure)
        {
            MessageBox.Show(this, result.FullMessage(), "Vérifiez la saisie", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }
        MessageBox.Show(this, result.Message, "Inscription", MessageBoxButtons.OK, MessageBoxIcon.Information);
        DialogResult = DialogResult.OK;
        Close();
    }
}
