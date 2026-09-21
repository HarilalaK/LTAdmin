using LTAdmin.Models;
using LTAdmin.Services;
using LTAdmin.Services.Auth;
using LTAdmin.UI.Views;

namespace LTAdmin.UI;

public sealed class MainForm : Form
{
    private readonly AppComposition _app;
    private readonly UserSession _session;
    private readonly Panel _content = new();
    private readonly Panel _navHost = new();
    private readonly Label _pageTitle = new();
    private readonly Label _pageDescription = new();
    private readonly Label _userName = new();
    private readonly Label _userRole = new();
    private readonly Label _yearLabel = new();
    private readonly Dictionary<string, Button> _navButtons = new();
    private string _currentModule = Modules.TableauDeBord;

    public bool LogoutRequested { get; private set; }

    public MainForm(AppComposition app, UserSession session)
    {
        _app = app;
        _session = session;
        Text = "LTAdmin — Gestion scolaire";
        StartPosition = FormStartPosition.CenterScreen;
        WindowState = FormWindowState.Maximized;
        MinimumSize = new Size(960, 640);
        BackColor = Theme.Background;
        Font = Theme.Body;
        AutoScaleMode = AutoScaleMode.Dpi;

        var root = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 2,
            RowCount = 2,
            Padding = new Padding(0),
            Margin = new Padding(0)
        };
        root.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 268));
        root.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        root.RowStyles.Add(new RowStyle(SizeType.Absolute, 78));
        root.RowStyles.Add(new RowStyle(SizeType.Percent, 100));

        var sidebar = BuildSidebar();
        var topbar = BuildTopbar();

        _content.Dock = DockStyle.Fill;
        _content.BackColor = Theme.Background;
        _content.Padding = new Padding(8);
        _content.MinimumSize = new Size(400, 300);

        root.Controls.Add(sidebar, 0, 0);
        root.SetRowSpan(sidebar, 2);
        root.Controls.Add(topbar, 1, 0);
        root.Controls.Add(_content, 1, 1);
        Controls.Add(root);

        Shown += (_, _) =>
        {
            RefreshYear();
            OpenModule(Modules.TableauDeBord);
        };
        Resize += (_, _) =>
        {
            if (Width < 1100)
                root.ColumnStyles[0].Width = 220;
            else
                root.ColumnStyles[0].Width = 268;
        };
    }

    private Panel BuildSidebar()
    {
        var sidebar = new Panel
        {
            Dock = DockStyle.Fill,
            BackColor = Theme.Sidebar,
            Padding = new Padding(12, 16, 12, 12)
        };

        var brand = new Panel { Dock = DockStyle.Top, Height = 72 };
        brand.Controls.Add(new Label
        {
            Text = "LTA",
            AutoSize = true,
            Font = new Font("Segoe UI", 22, FontStyle.Bold),
            ForeColor = Color.White,
            Location = new Point(8, 2)
        });
        brand.Controls.Add(new Label
        {
            Text = "ADMINISTRATION",
            AutoSize = true,
            Font = new Font("Segoe UI", 8.5f, FontStyle.Bold),
            ForeColor = Color.FromArgb(147, 197, 253),
            Location = new Point(10, 40)
        });
        var userPanel = new Panel { Dock = DockStyle.Bottom, Height = 118, Padding = new Padding(8) };
        userPanel.Paint += (_, e) =>
        {
            using var pen = new Pen(Color.FromArgb(51, 71, 99));
            e.Graphics.DrawLine(pen, 0, 0, userPanel.Width, 0);
        };
        _userName.Text = _session.DisplayName;
        _userName.AutoSize = false;
        _userName.Width = 220;
        _userName.Height = 22;
        _userName.ForeColor = Color.White;
        _userName.Font = Theme.BodyBold;
        _userName.Location = new Point(6, 10);
        _userRole.Text = _session.Role + " · connecté";
        _userRole.AutoSize = false;
        _userRole.Width = 220;
        _userRole.Height = 20;
        _userRole.ForeColor = Color.FromArgb(186, 198, 214);
        _userRole.Font = Theme.Small;
        _userRole.Location = new Point(6, 32);
        var logout = Theme.Button("Se déconnecter", Color.FromArgb(51, 65, 85), Color.White, 220);
        logout.Location = new Point(6, 62);
        logout.Height = 36;
        logout.Click += (_, _) => ConfirmLogout();
        userPanel.Controls.Add(_userName);
        userPanel.Controls.Add(_userRole);
        userPanel.Controls.Add(logout);
        sidebar.Controls.Add(userPanel);

        _navHost.Dock = DockStyle.Fill;
        _navHost.AutoScroll = true;
        _navHost.BackColor = Theme.Sidebar;
        _navHost.Padding = new Padding(0, 4, 4, 8);
        sidebar.Controls.Add(_navHost);

        BuildNavigation();
        return sidebar;
    }

    private Panel BuildTopbar()
    {
        var topbar = new Panel
        {
            Dock = DockStyle.Fill,
            BackColor = Theme.Surface,
            Padding = new Padding(20, 10, 20, 10)
        };
        topbar.Paint += (_, e) =>
        {
            using var pen = new Pen(Theme.Border);
            e.Graphics.DrawLine(pen, 0, topbar.Height - 1, topbar.Width, topbar.Height - 1);
        };

        _pageTitle.Text = Modules.TableauDeBord;
        _pageTitle.AutoSize = true;
        _pageTitle.Font = Theme.SubHeading;
        _pageTitle.ForeColor = Theme.Text;
        _pageTitle.Location = new Point(20, 12);
        _pageDescription.Text = "Vue d’ensemble";
        _pageDescription.AutoSize = true;
        _pageDescription.Font = Theme.Small;
        _pageDescription.ForeColor = Theme.MutedText;
        _pageDescription.Location = new Point(21, 38);
        topbar.Controls.Add(_pageTitle);
        topbar.Controls.Add(_pageDescription);

        _yearLabel.AutoSize = true;
        _yearLabel.Font = Theme.BodyBold;
        _yearLabel.ForeColor = Theme.Primary;
        _yearLabel.Anchor = AnchorStyles.Top | AnchorStyles.Right;
        topbar.Controls.Add(_yearLabel);

        var refresh = Theme.Button("Actualiser", Theme.Primary, Color.White, 110);
        refresh.Anchor = AnchorStyles.Top | AnchorStyles.Right;
        refresh.Click += (_, _) => RefreshCurrent();
        topbar.Controls.Add(refresh);

        topbar.Resize += (_, _) =>
        {
            refresh.Location = new Point(Math.Max(280, topbar.Width - 130), 20);
            _yearLabel.Location = new Point(Math.Max(280, refresh.Left - _yearLabel.Width - 16), 26);
        };
        return topbar;
    }

    private void BuildNavigation()
    {
        _navHost.Controls.Clear();
        _navButtons.Clear();
        int y = 4;
        foreach (var module in Habilitations.MenuOrder)
        {
            if (!Habilitations.CanAccess(_session.Role, module))
                continue;

            var button = new Button
            {
                Text = "  " + module,
                Width = Math.Max(180, _navHost.ClientSize.Width - 8),
                Height = 38,
                Location = new Point(0, y),
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right,
                FlatStyle = FlatStyle.Flat,
                BackColor = Theme.Sidebar,
                ForeColor = Color.FromArgb(241, 245, 249),
                Font = Theme.BodyBold,
                TextAlign = ContentAlignment.MiddleLeft,
                Padding = new Padding(8, 0, 4, 0),
                Cursor = Cursors.Hand,
                Tag = module
            };
            button.FlatAppearance.BorderSize = 0;
            button.FlatAppearance.MouseOverBackColor = Color.FromArgb(36, 58, 92);
            button.Click += (_, _) => OpenModule(module);
            _navHost.Controls.Add(button);
            _navButtons[module] = button;
            y += 42;
        }

        if (Habilitations.CanAccess(_session.Role, Modules.Administration))
        {
            var users = new Button
            {
                Text = "  " + Modules.Utilisateurs,
                Width = Math.Max(180, _navHost.ClientSize.Width - 8),
                Height = 38,
                Location = new Point(0, y + 8),
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right,
                FlatStyle = FlatStyle.Flat,
                BackColor = Theme.Sidebar,
                ForeColor = Color.FromArgb(191, 219, 254),
                Font = Theme.BodyBold,
                TextAlign = ContentAlignment.MiddleLeft,
                Cursor = Cursors.Hand
            };
            users.FlatAppearance.BorderSize = 0;
            users.Click += (_, _) => OpenModule(Modules.Utilisateurs);
            _navHost.Controls.Add(users);
            _navButtons[Modules.Utilisateurs] = users;
        }
    }

    public void OpenModule(string module)
    {
        if (!Habilitations.CanAccess(_session.Role, module) && module != Modules.Utilisateurs)
            return;
        if (module == Modules.Utilisateurs && !Habilitations.CanAccess(_session.Role, Modules.Administration))
            return;

        _currentModule = module;
        Highlight(module);
        _pageTitle.Text = module;
        _pageDescription.Text = Description(module);
        SetContent(CreateView(module));
        if (_content.Controls.Count > 0 && _content.Controls[0] is IRefreshableView refreshable)
            refreshable.RefreshData();
    }

    private Control CreateView(string module) => module switch
    {
        Modules.TableauDeBord => new DashboardControl(_app, _ => { }, OpenModule),
        Modules.Etudiants => new StudentsControl(_app, _session),
        Modules.Inscriptions => new EnrollmentsControl(_app, _session),
        Modules.Notes => new GradesControl(_app, _session),
        Modules.Ecolage => new PaymentsControl(_app, _session),
        Modules.Rapports => new PlaceholderView(Modules.Rapports,
            "États et exports. Utilisez le catalogue des rapports lorsque les données sont disponibles."),
        Modules.Utilisateurs => new UsersControl(_app, _session),
        Modules.Administration => new UsersControl(_app, _session),
        _ => new PlaceholderView(module, "Module « " + module + " ».")
    };

    private static string Description(string module) => module switch
    {
        Modules.TableauDeBord => "Synthèse de l’établissement",
        Modules.Etudiants => "Dossiers des étudiants",
        Modules.Inscriptions => "Inscriptions de l’année",
        Modules.Referentiel => "Filières, classes, matières",
        Modules.Formateurs => "Personnel enseignant",
        Modules.Notes => "Notes et évaluations",
        Modules.Bulletins => "Bulletins de notes",
        Modules.Examens => "Sessions et épreuves",
        Modules.EmploiDuTemps => "Planning des classes",
        Modules.Absences => "Absences et retards",
        Modules.Ecolage => "Paiements et tarifs",
        Modules.Paie => "Rémunération des formateurs",
        Modules.Statistiques => "Indicateurs",
        Modules.Rapports => "États imprimables",
        Modules.Administration => "Paramétrage et comptes",
        Modules.Utilisateurs => "Comptes et profils",
        _ => ""
    };

    private void Highlight(string module)
    {
        foreach (var kv in _navButtons)
        {
            kv.Value.BackColor = kv.Key == module ? Color.FromArgb(30, 105, 217) : Theme.Sidebar;
            kv.Value.ForeColor = Color.White;
        }
    }

    private void SetContent(Control control)
    {
        control.Dock = DockStyle.Fill;
        control.Visible = true;
        _content.SuspendLayout();
        foreach (var child in _content.Controls.Cast<Control>().ToList())
        {
            _content.Controls.Remove(child);
            child.Dispose();
        }
        _content.Controls.Add(control);
        control.BringToFront();
        _content.ResumeLayout(true);
    }

    private void RefreshCurrent()
    {
        RefreshYear();
        if (_content.Controls.Count > 0 && _content.Controls[0] is IRefreshableView refreshable)
            refreshable.RefreshData();
    }

    private void RefreshYear()
    {
        try
        {
            var annee = _app.Admin.GetAnneeActive();
            _yearLabel.Text = annee?.Libelle is { Length: > 0 } lib
                ? "Année scolaire : " + lib
                : "Année scolaire : non définie";
        }
        catch
        {
            _yearLabel.Text = "Année scolaire : —";
        }
        _yearLabel.BringToFront();
    }

    private void ConfirmLogout()
    {
        if (MessageBox.Show(this, "Voulez-vous vous déconnecter ?", "Déconnexion",
                MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes)
            return;
        LogoutRequested = true;
        Close();
    }
}
