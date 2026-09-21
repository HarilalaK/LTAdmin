using LTAdmin.Models;
using LTAdmin.Services;
using LTAdmin.Services.Auth;

namespace LTAdmin.UI;

public sealed class LoginForm : Form
{
    private readonly AuthenticationService _authentication;
    private readonly TextBox _login = new();
    private readonly TextBox _password = new();
    private readonly Label _error = new();
    private readonly Button _submit;

    public LoginForm(AppComposition app)
    {
        _authentication = app.Auth;

        Text = "LTAdmin — Connexion";
        StartPosition = FormStartPosition.CenterScreen;
        FormBorderStyle = FormBorderStyle.Sizable;
        MinimumSize = new Size(480, 560);
        Size = new Size(560, 640);
        MaximizeBox = true;
        MinimizeBox = true;
        BackColor = Theme.Background;
        Font = Theme.Body;
        AutoScaleMode = AutoScaleMode.Dpi;

        var root = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 1,
            RowCount = 2,
            Padding = new Padding(0)
        };
        root.RowStyles.Add(new RowStyle(SizeType.Percent, 34));
        root.RowStyles.Add(new RowStyle(SizeType.Percent, 66));

        var header = new Panel { Dock = DockStyle.Fill, BackColor = Theme.Sidebar };
        header.Controls.Add(new Label
        {
            Text = "LTA",
            ForeColor = Color.White,
            Font = new Font("Segoe UI", 32, FontStyle.Bold),
            AutoSize = true,
            Location = new Point(36, 36),
            BackColor = Color.Transparent
        });
        header.Controls.Add(new Label
        {
            Text = "ADMINISTRATION",
            ForeColor = Color.FromArgb(191, 219, 254),
            Font = new Font("Segoe UI", 11, FontStyle.Bold),
            AutoSize = true,
            Location = new Point(40, 88),
            BackColor = Color.Transparent
        });
        header.Controls.Add(new Label
        {
            Text = "Connexion à l’espace de gestion scolaire",
            ForeColor = Color.FromArgb(226, 232, 240),
            Font = Theme.Body,
            AutoSize = true,
            Location = new Point(40, 124),
            BackColor = Color.Transparent
        });

        var content = new Panel { Dock = DockStyle.Fill, BackColor = Theme.Background, Padding = new Padding(36, 20, 36, 24) };

        var form = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 1,
            RowCount = 10,
            AutoScroll = true
        };
        form.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));

        form.Controls.Add(MakeLabel("Bienvenue", Theme.Heading, Theme.Text));
        form.Controls.Add(MakeLabel("Saisissez vos identifiants (table des utilisateurs).", Theme.Body, Theme.MutedText));
        form.Controls.Add(MakeLabel("Identifiant", Theme.BodyBold, Theme.Text));

        _login.Dock = DockStyle.Top;
        _login.Height = 36;
        _login.PlaceholderText = "Ex. ADMIN";
        _login.BorderStyle = BorderStyle.FixedSingle;
        _login.BackColor = Color.White;
        _login.ForeColor = Theme.Text;
        _login.Font = new Font("Segoe UI", 11f);
        _login.Margin = new Padding(0, 4, 0, 12);
        _login.KeyDown += InputKeyDown;
        form.Controls.Add(_login);

        form.Controls.Add(MakeLabel("Mot de passe", Theme.BodyBold, Theme.Text));
        _password.Dock = DockStyle.Top;
        _password.Height = 36;
        _password.PlaceholderText = "Votre mot de passe";
        _password.BorderStyle = BorderStyle.FixedSingle;
        _password.BackColor = Color.White;
        _password.ForeColor = Theme.Text;
        _password.UseSystemPasswordChar = true;
        _password.Font = new Font("Segoe UI", 11f);
        _password.Margin = new Padding(0, 4, 0, 8);
        _password.KeyDown += InputKeyDown;
        form.Controls.Add(_password);

        var showPassword = new CheckBox
        {
            Text = "Afficher le mot de passe",
            AutoSize = true,
            ForeColor = Theme.Text,
            Font = Theme.Body,
            Margin = new Padding(0, 4, 0, 8)
        };
        showPassword.CheckedChanged += (_, _) => _password.UseSystemPasswordChar = !showPassword.Checked;
        form.Controls.Add(showPassword);

        _error.AutoSize = true;
        _error.MaximumSize = new Size(460, 0);
        _error.ForeColor = Color.FromArgb(185, 28, 28);
        _error.Font = Theme.BodyBold;
        _error.Margin = new Padding(0, 4, 0, 8);
        form.Controls.Add(_error);

        _submit = Theme.Button("Se connecter", Theme.Primary, Color.White, 220);
        _submit.Dock = DockStyle.Top;
        _submit.Height = 44;
        _submit.Margin = new Padding(0, 8, 0, 0);
        _submit.Click += (_, _) => SignIn();
        form.Controls.Add(_submit);

        content.Controls.Add(form);
        root.Controls.Add(header, 0, 0);
        root.Controls.Add(content, 0, 1);
        Controls.Add(root);
        AcceptButton = _submit;
        Shown += (_, _) => _login.Focus();
    }

    private static Label MakeLabel(string text, Font font, Color color) => new()
    {
        Text = text,
        AutoSize = true,
        Font = font,
        ForeColor = color,
        Margin = new Padding(0, 2, 0, 4)
    };

    public UserSession? Session { get; private set; }

    private void InputKeyDown(object? sender, KeyEventArgs e)
    {
        if (e.KeyCode == Keys.Enter)
        {
            e.SuppressKeyPress = true;
            SignIn();
        }
    }

    private void SignIn()
    {
        _error.Text = "";
        if (string.IsNullOrWhiteSpace(_login.Text) || string.IsNullOrEmpty(_password.Text))
        {
            _error.Text = "Saisissez votre identifiant et votre mot de passe.";
            return;
        }

        try
        {
            Cursor = Cursors.WaitCursor;
            var result = _authentication.Authenticate(_login.Text, _password.Text);
            if (result.IsFailure || result.Value is null)
            {
                _error.Text = result.FullMessage();
                _password.SelectAll();
                _password.Focus();
                return;
            }

            Session = result.Value;
            DialogResult = DialogResult.OK;
            Close();
        }
        catch (Exception ex)
        {
            _error.Text = "Connexion impossible : " + ex.Message;
        }
        finally
        {
            Cursor = Cursors.Default;
        }
    }
}