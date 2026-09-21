using LTAdmin.Data;
using LTAdmin.Models;
using LTAdmin.Services;

namespace LTAdmin.UI;

public sealed class LoginForm : Form
{
    private readonly AuthenticationService _authentication;
    private readonly TextBox _login = new();
    private readonly TextBox _password = new();
    private readonly Label _error = new();
    private readonly Button _submit;

    public LoginForm(AccessDatabase database)
    {
        _authentication = new AuthenticationService(database);

        Text = "LTAdmin — Connexion";
        StartPosition = FormStartPosition.CenterScreen;
        FormBorderStyle = FormBorderStyle.FixedSingle;
        MaximizeBox = false;
        MinimizeBox = false;
        ClientSize = new Size(470, 575);
        BackColor = Theme.Background;
        Font = Theme.Body;

        var header = new Panel
        {
            Dock = DockStyle.Top,
            Height = 218,
            BackColor = Theme.Sidebar
        };

        header.Paint += (_, e) =>
        {
            using var brush = new SolidBrush(Color.FromArgb(30, 105, 217));
            e.Graphics.FillEllipse(brush, 350, -55, 190, 190);

            using var brush2 = new SolidBrush(Color.FromArgb(33, 54, 83));
            e.Graphics.FillEllipse(brush2, -80, 140, 160, 160);
        };

        header.Controls.Add(new Label
        {
            Text = "LTA",
            ForeColor = Color.White,
            Font = new Font("Segoe UI", 32, FontStyle.Bold),
            AutoSize = true,
            Location = new Point(42, 42),
            BackColor = Color.Transparent
        });

        header.Controls.Add(new Label
        {
            Text = "ADMINISTRATION",
            ForeColor = Color.FromArgb(191, 219, 254),
            Font = new Font("Segoe UI", 10, FontStyle.Bold),
            AutoSize = true,
            Location = new Point(47, 92),
            BackColor = Color.Transparent
        });

        header.Controls.Add(new Label
        {
            Text = "Gestion scolaire · BTS Hôtellerie & Tourisme",
            ForeColor = Color.FromArgb(203, 213, 225),
            Font = Theme.Body,
            AutoSize = true,
            Location = new Point(47, 133),
            BackColor = Color.Transparent
        });

        var content = new Panel
        {
            Dock = DockStyle.Fill,
            BackColor = Theme.Background
        };

        content.Controls.Add(new Label
        {
            Text = "Bienvenue",
            AutoSize = true,
            Location = new Point(47, 20),
            Font = Theme.Heading,
            ForeColor = Theme.Text
        });

        content.Controls.Add(new Label
        {
            Text = "Connectez-vous pour accéder à votre espace.",
            AutoSize = true,
            Location = new Point(47, 57),
            ForeColor = Theme.MutedText
        });

        content.Controls.Add(new Label
        {
            Text = "Identifiant",
            AutoSize = true,
            Location = new Point(47, 96),
            Font = Theme.BodyBold,
            ForeColor = Theme.Text
        });

        _login.Location = new Point(47, 118);
        _login.Width = 370;
        _login.Height = 32;
        _login.PlaceholderText = "Ex. ADMIN";
        _login.BorderStyle = BorderStyle.FixedSingle;
        _login.BackColor = Color.White;
        _login.ForeColor = Theme.Text;
        _login.Font = Theme.Body;
        _login.KeyDown += InputKeyDown;
        content.Controls.Add(_login);

        content.Controls.Add(new Label
        {
            Text = "Mot de passe",
            AutoSize = true,
            Location = new Point(47, 163),
            Font = Theme.BodyBold,
            ForeColor = Theme.Text
        });

        _password.Location = new Point(47, 185);
        _password.Width = 370;
        _password.Height = 32;
        _password.PlaceholderText = "Votre mot de passe";
        _password.BorderStyle = BorderStyle.FixedSingle;
        _password.BackColor = Color.White;
        _password.ForeColor = Theme.Text;
        _password.UseSystemPasswordChar = true;
        _password.Font = Theme.Body;
        _password.KeyDown += InputKeyDown;
        content.Controls.Add(_password);

        var showPassword = new CheckBox
        {
            Text = "Afficher le mot de passe",
            AutoSize = true,
            Location = new Point(47, 228),
            ForeColor = Theme.MutedText,
            Font = Theme.Small
        };

        showPassword.CheckedChanged += (_, _) =>
        {
            _password.UseSystemPasswordChar = !showPassword.Checked;
        };

        content.Controls.Add(showPassword);

        _error.AutoSize = false;
        _error.Width = 370;
        _error.Height = 36;
        _error.Location = new Point(47, 256);
        _error.ForeColor = Color.FromArgb(185, 28, 28);
        _error.Font = Theme.Small;
        content.Controls.Add(_error);

        _submit = Theme.Button(
            "Se connecter",
            Theme.Primary,
            Color.White,
            370
        );

        _submit.Location = new Point(47, 300);
        _submit.Height = 42;
        _submit.Click += (_, _) => SignIn();
        content.Controls.Add(_submit);

        var layout = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 1,
            RowCount = 2,
            Margin = new Padding(0),
            Padding = new Padding(0),
            BackColor = Theme.Background
        };

        layout.RowStyles.Add(
            new RowStyle(SizeType.Absolute, 218)
        );

        layout.RowStyles.Add(
            new RowStyle(SizeType.Percent, 100)
        );

        layout.Controls.Add(header, 0, 0);
        layout.Controls.Add(content, 0, 1);

        Controls.Add(layout);

        AcceptButton = _submit;

        Shown += (_, _) =>
        {
            _login.Focus();
        };
    }

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

        if (string.IsNullOrWhiteSpace(_login.Text) ||
            string.IsNullOrEmpty(_password.Text))
        {
            _error.Text =
                "Saisissez votre identifiant et votre mot de passe.";

            return;
        }

        try
        {
            Cursor = Cursors.WaitCursor;

            Session = _authentication.Authenticate(
                _login.Text,
                _password.Text
            );

            if (Session is null)
            {
                _error.Text =
                    "Identifiant ou mot de passe incorrect.";

                _password.SelectAll();
                _password.Focus();

                return;
            }

            DialogResult = DialogResult.OK;
            Close();
        }
        catch (Exception ex)
        {
            _error.Text =
                "Connexion impossible : " + ex.Message;
        }
        finally
        {
            Cursor = Cursors.Default;
        }
    }
}