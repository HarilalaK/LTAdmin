using LTAdmin.Models;
using LTAdmin.Models.Entities;
using LTAdmin.Services;
using LTAdmin.Services.Auth;

namespace LTAdmin.UI.Views;

/// <summary>Gestion des profils utilisateurs (table UTILISATEUR, libellés métier).</summary>
public sealed class UsersControl : UserControl, IRefreshableView
{
    private readonly AppComposition _app;
    private readonly UserSession _session;
    private readonly DataGridView _grid = new();
    private readonly Label _status = new();

    public UsersControl(AppComposition app, UserSession session)
    {
        _app = app;
        _session = session;
        Dock = DockStyle.Fill;
        BackColor = Theme.Background;
        Padding = new Padding(20);

        var toolbar = new FlowLayoutPanel
        {
            Dock = DockStyle.Top,
            Height = 48,
            FlowDirection = FlowDirection.LeftToRight,
            WrapContents = false,
            AutoSize = false,
            Padding = new Padding(0, 4, 0, 8)
        };

        var add = Theme.Button("Nouveau compte", Theme.Primary, Color.White, 150);
        add.Click += (_, _) => Edit(null);
        var edit = Theme.Button("Modifier", Color.FromArgb(241, 245, 249), Theme.Text, 110);
        edit.Click += (_, _) => Edit(Current());
        var pwd = Theme.Button("Mot de passe", Color.FromArgb(241, 245, 249), Theme.Text, 130);
        pwd.Click += (_, _) => ResetPassword();
        toolbar.Controls.Add(add);
        toolbar.Controls.Add(edit);
        toolbar.Controls.Add(pwd);

        _status.AutoSize = true;
        _status.ForeColor = Theme.MutedText;
        _status.Padding = new Padding(12, 8, 0, 0);
        toolbar.Controls.Add(_status);

        Theme.StyleGrid(_grid);
        _grid.Dock = DockStyle.Fill;
        _grid.DoubleClick += (_, _) => Edit(Current());

        Controls.Add(_grid);
        Controls.Add(toolbar);
        Load += (_, _) => RefreshData();
    }

    public void RefreshData()
    {
        try
        {
            var rows = _app.Admin.ListUtilisateurs()
                .Select(u => new
                {
                    Identifiant = u.CodeUtr,
                    Nom = u.NomUtr,
                    Profil = Habilitations.NormalizeProfil(u.Profil),
                    Actif = u.Actif == true ? "Oui" : "Non"
                })
                .ToList();
            _grid.DataSource = rows;
            _status.Text = rows.Count + " compte(s)";
            _status.ForeColor = Theme.MutedText;
        }
        catch (Exception ex)
        {
            _status.Text = "Impossible de charger les comptes : " + ex.Message;
            _status.ForeColor = Color.FromArgb(185, 28, 28);
        }
    }

    private Utilisateur? Current()
    {
        if (_grid.CurrentRow?.Cells["Identifiant"]?.Value is not string code)
            return null;
        return _app.Admin.GetUtilisateur(code);
    }

    private void Edit(Utilisateur? existing)
    {
        using var dlg = new UserEditDialog(existing);
        if (dlg.ShowDialog(FindForm()) != DialogResult.OK || dlg.Value is null) return;
        try
        {
            if (existing is null)
                _app.Admin.InsertUtilisateur(dlg.Value);
            else
            {
                _app.Admin.UpdateUtilisateur(dlg.Value);
                if (!string.IsNullOrEmpty(dlg.NewPassword))
                    _app.Admin.UpdateMotPasse(dlg.Value.CodeUtr!, dlg.NewPassword);
            }
            _app.Journal.LogOperation(_session.Login, existing is null ? "CREATION" : "MODIFICATION",
                "UTILISATEUR", null, dlg.Value.CodeUtr);
            RefreshData();
        }
        catch (Exception ex)
        {
            MessageBox.Show(FindForm(), ex.Message, "Comptes utilisateurs", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private void ResetPassword()
    {
        var user = Current();
        if (user is null) return;
        var pwd = DialogPrompt.Show(FindForm(), "Nouveau mot de passe", "Mot de passe (4 caractères minimum)");
        if (string.IsNullOrEmpty(pwd)) return;
        if (pwd.Length < 4)
        {
            MessageBox.Show(FindForm(), "Le mot de passe doit contenir au moins 4 caractères.", "Mot de passe",
                MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }
        _app.Admin.UpdateMotPasse(user.CodeUtr!, pwd);
        MessageBox.Show(FindForm(), "Mot de passe mis à jour.", "Mot de passe", MessageBoxButtons.OK, MessageBoxIcon.Information);
    }
}

internal sealed class UserEditDialog : Form
{
    private readonly TextBox _code = new();
    private readonly TextBox _nom = new();
    private readonly ComboBox _profil = new();
    private readonly CheckBox _actif = new();
    private readonly TextBox _pwd = new();

    public UserEditDialog(Utilisateur? existing)
    {
        Text = existing is null ? "Nouveau compte" : "Modifier le compte";
        StartPosition = FormStartPosition.CenterParent;
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox = false;
        MinimizeBox = false;
        ClientSize = new Size(440, 360);
        BackColor = Theme.Surface;
        Font = Theme.Body;
        Padding = new Padding(24);

        int y = 20;
        void Label(string t)
        {
            Controls.Add(new Label { Text = t, AutoSize = true, Location = new Point(24, y), Font = Theme.BodyBold, ForeColor = Theme.Text });
            y += 22;
        }

        Label("Identifiant");
        _code.SetBounds(24, y, 390, 32);
        _code.Enabled = existing is null;
        _code.Text = existing?.CodeUtr ?? "";
        Controls.Add(_code);
        y += 42;

        Label("Nom affiché");
        _nom.SetBounds(24, y, 390, 32);
        _nom.Text = existing?.NomUtr ?? "";
        Controls.Add(_nom);
        y += 42;

        Label("Profil");
        _profil.SetBounds(24, y, 390, 32);
        _profil.DropDownStyle = ComboBoxStyle.DropDownList;
        _profil.Items.AddRange(Habilitations.ProfilsConnus.Cast<object>().ToArray());
        var norm = Habilitations.NormalizeProfil(existing?.Profil);
        _profil.SelectedItem = Habilitations.ProfilsConnus.Contains(norm) ? norm : Profils.ScolariteLibelle;
        Controls.Add(_profil);
        y += 42;

        _actif.Text = "Compte actif";
        _actif.AutoSize = true;
        _actif.Location = new Point(24, y);
        _actif.Checked = existing?.Actif != false;
        Controls.Add(_actif);
        y += 32;

        Label(existing is null ? "Mot de passe" : "Nouveau mot de passe (optionnel)");
        _pwd.SetBounds(24, y, 390, 32);
        _pwd.UseSystemPasswordChar = true;
        Controls.Add(_pwd);
        y += 48;

        var ok = Theme.Button("Enregistrer", Theme.Primary, Color.White, 130);
        ok.Location = new Point(164, y);
        ok.Click += (_, _) => Save(existing);
        var cancel = Theme.Button("Annuler", Color.FromArgb(241, 245, 249), Theme.Text, 110);
        cancel.Location = new Point(304, y);
        cancel.Click += (_, _) => DialogResult = DialogResult.Cancel;
        Controls.Add(ok);
        Controls.Add(cancel);
        AcceptButton = ok;
        CancelButton = cancel;
    }

    public Utilisateur? Value { get; private set; }
    public string? NewPassword { get; private set; }

    private void Save(Utilisateur? existing)
    {
        if (string.IsNullOrWhiteSpace(_code.Text) || string.IsNullOrWhiteSpace(_nom.Text))
        {
            MessageBox.Show(this, "Identifiant et nom sont obligatoires.", Text, MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }
        if (existing is null && string.IsNullOrWhiteSpace(_pwd.Text))
        {
            MessageBox.Show(this, "Saisissez un mot de passe.", Text, MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }
        Value = new Utilisateur
        {
            CodeUtr = _code.Text.Trim(),
            NomUtr = _nom.Text.Trim(),
            MotPasse = existing is null ? _pwd.Text : existing.MotPasse,
            Profil = _profil.SelectedItem?.ToString(),
            Actif = _actif.Checked
        };
        NewPassword = string.IsNullOrWhiteSpace(_pwd.Text) ? null : _pwd.Text;
        DialogResult = DialogResult.OK;
    }
}
