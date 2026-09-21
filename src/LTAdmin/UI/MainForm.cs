using LTAdmin.Data;
using LTAdmin.Models;

namespace LTAdmin.UI;

public sealed class MainForm : Form
{
    private readonly AccessDatabase _database;
    private readonly DatabaseRepository _repository;
    private readonly UserSession _session;
    private readonly Panel _content = new();
    private readonly Label _pageTitle = new();
    private readonly Label _pageDescription = new();
    private readonly Label _databaseLabel = new();
    private readonly FlowLayoutPanel _navigation = new();
    private IReadOnlyList<DbTableInfo> _tables = Array.Empty<DbTableInfo>();
    private DashboardControl? _dashboard;

    public MainForm(AccessDatabase database, UserSession session)
    {
        _database = database;
        _repository = new DatabaseRepository(database);
        _session = session;
        Text = "LTAdmin — Gestion scolaire";
        StartPosition = FormStartPosition.CenterScreen;
        WindowState = FormWindowState.Maximized;
        MinimumSize = new Size(1100, 700);
        BackColor = Theme.Background;
        Font = Theme.Body;

        BuildSidebar();
        BuildWorkspace();
        LoadTables();
        Shown += (_, _) => ShowDashboard();
    }

    private void BuildSidebar()
    {
        var sidebar = new Panel { Dock = DockStyle.Left, Width = 248, BackColor = Theme.Sidebar, Padding = new Padding(14, 16, 14, 12) };
        var brand = new Panel { Dock = DockStyle.Top, Height = 75 };
        brand.Controls.Add(new Label { Text = "LTA", AutoSize = true, Font = new Font("Segoe UI", 25, FontStyle.Bold), ForeColor = Color.White, Location = new Point(10, 0) });
        brand.Controls.Add(new Label { Text = "ADMINISTRATION", AutoSize = true, Font = new Font("Segoe UI", 8.5f, FontStyle.Bold), ForeColor = Color.FromArgb(147, 197, 253), Location = new Point(13, 39) });
        brand.Controls.Add(new Label { Text = "Gestion scolaire", AutoSize = true, Font = Theme.Small, ForeColor = Theme.SidebarMuted, Location = new Point(76, 23) });
        sidebar.Controls.Add(brand);

        _navigation.Dock = DockStyle.Fill;
        _navigation.FlowDirection = FlowDirection.TopDown;
        _navigation.WrapContents = false;
        _navigation.AutoScroll = true;
        _navigation.Padding = new Padding(0, 4, 0, 8);
        _navigation.BackColor = Theme.Sidebar;
        sidebar.Controls.Add(_navigation);

        var userPanel = new Panel { Dock = DockStyle.Bottom, Height = 66, Padding = new Padding(8, 8, 5, 4) };
        userPanel.Paint += (_, e) =>
        {
            using var pen = new Pen(Color.FromArgb(45, 63, 88));
            e.Graphics.DrawLine(pen, 0, 0, userPanel.Width, 0);
        };
        userPanel.Controls.Add(new Label { Text = _session.DisplayName, AutoSize = true, ForeColor = Color.White, Font = Theme.BodyBold, Location = new Point(8, 10) });
        userPanel.Controls.Add(new Label { Text = _session.Role + " · connecté", AutoSize = true, ForeColor = Theme.SidebarMuted, Font = Theme.Small, Location = new Point(8, 32) });
        sidebar.Controls.Add(userPanel);
        Controls.Add(sidebar);
    }

    private void BuildWorkspace()
    {
        var topbar = new Panel { Dock = DockStyle.Top, Height = 72, BackColor = Theme.Surface, Padding = new Padding(28, 14, 28, 10) };
        _pageTitle.Text = "Tableau de bord";
        _pageTitle.AutoSize = true;
        _pageTitle.Font = Theme.SubHeading;
        _pageTitle.ForeColor = Theme.Text;
        _pageTitle.Location = new Point(28, 14);
        topbar.Controls.Add(_pageTitle);
        _pageDescription.Text = "Vue d’ensemble";
        _pageDescription.AutoSize = true;
        _pageDescription.Font = Theme.Small;
        _pageDescription.ForeColor = Theme.MutedText;
        _pageDescription.Location = new Point(29, 38);
        topbar.Controls.Add(_pageDescription);

        var reports = Theme.Button("États", Color.FromArgb(241, 245, 249), Theme.Text, 92);
        reports.Anchor = AnchorStyles.Top | AnchorStyles.Right;
        reports.Location = new Point(topbar.Width - 370, 18);
        reports.Click += (_, _) => ShowReports();
        topbar.Controls.Add(reports);
        var backup = Theme.Button("Sauvegarder", Color.FromArgb(241, 245, 249), Theme.Text, 112);
        backup.Anchor = AnchorStyles.Top | AnchorStyles.Right;
        backup.Location = new Point(topbar.Width - 268, 18);
        backup.Click += Backup;
        topbar.Controls.Add(backup);
        var reload = Theme.Button("Actualiser", Theme.Primary, Color.White, 100);
        reload.Anchor = AnchorStyles.Top | AnchorStyles.Right;
        reload.Location = new Point(topbar.Width - 140, 18);
        reload.Click += (_, _) => RefreshCurrent();
        topbar.Controls.Add(reload);
        topbar.Resize += (_, _) =>
        {
            reports.Left = topbar.Width - 370;
            backup.Left = topbar.Width - 268;
            reload.Left = topbar.Width - 140;
        };
        Controls.Add(topbar);

        _content.Dock = DockStyle.Fill;
        _content.BackColor = Theme.Background;
        Controls.Add(_content);
    }

    private void LoadTables()
    {
        try
        {
            _tables = _repository.GetTables();
            BuildNavigation();
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, "Impossible de lire les tables de la base.\n\n" + ex.Message, "Base de données", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private void BuildNavigation()
    {
        _navigation.SuspendLayout();
        _navigation.Controls.Clear();
        string? currentGroup = null;
        foreach (var item in DatabaseCatalog.Items)
        {
            if (!string.Equals(currentGroup, item.Group, StringComparison.Ordinal))
            {
                currentGroup = item.Group;
                var groupLabel = new Label
                {
                    Text = item.Group,
                    Width = 208,
                    Height = 27,
                    Margin = new Padding(8, 11, 0, 0),
                    ForeColor = Theme.SidebarMuted,
                    Font = new Font("Segoe UI", 8f, FontStyle.Bold),
                    TextAlign = ContentAlignment.MiddleLeft
                };
                _navigation.Controls.Add(groupLabel);
            }

            var available = item.TableName is null || FindTable(item.TableName) is not null;
            var button = new Button
            {
                Text = "  " + item.Label,
                Width = 218,
                Height = 35,
                Margin = new Padding(0, 1, 0, 0),
                FlatStyle = FlatStyle.Flat,
                BackColor = Theme.Sidebar,
                ForeColor = available ? Color.FromArgb(226, 232, 240) : Color.FromArgb(71, 85, 105),
                Font = Theme.Body,
                TextAlign = ContentAlignment.MiddleLeft,
                Padding = new Padding(10, 0, 4, 0),
                Cursor = available ? Cursors.Hand : Cursors.Default,
                Enabled = available
            };
            button.FlatAppearance.BorderSize = 0;
            button.FlatAppearance.MouseOverBackColor = Color.FromArgb(31, 50, 79);
            button.Tag = item;
            button.Click += (_, _) => Navigate(item);
            _navigation.Controls.Add(button);
        }

        var all = new Button
        {
            Text = "  Toutes les tables",
            Width = 218,
            Height = 35,
            Margin = new Padding(0, 12, 0, 0),
            FlatStyle = FlatStyle.Flat,
            BackColor = Theme.Sidebar,
            ForeColor = Color.FromArgb(147, 197, 253),
            Font = Theme.BodyBold,
            TextAlign = ContentAlignment.MiddleLeft,
            Padding = new Padding(10, 0, 4, 0),
            Cursor = Cursors.Hand
        };
        all.FlatAppearance.BorderSize = 0;
        all.Click += (_, _) => ShowAllTables();
        _navigation.Controls.Add(all);
        _navigation.ResumeLayout();
    }

    private void Navigate(NavigationItem item)
    {
        if (item.TableName is null) { ShowDashboard(); return; }
        OpenTable(item.TableName, item.Label, item.Description);
    }

    private void ShowDashboard()
    {
        _pageTitle.Text = "Tableau de bord";
        _pageDescription.Text = "Vue d’ensemble de votre établissement";
        _dashboard ??= new DashboardControl(_database, table => OpenTable(table, DatabaseCatalog.DisplayName(table), "Gestion des enregistrements"));
        SetContent(_dashboard);
        _dashboard.RefreshData();
    }

    private void OpenTable(string tableName, string? title = null, string? description = null)
    {
        var table = FindTable(tableName);
        if (table is null)
        {
            MessageBox.Show(this, $"La table {tableName} n’existe pas dans cette base.", "Table indisponible", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }
        _pageTitle.Text = title ?? DatabaseCatalog.DisplayName(table.Name);
        _pageDescription.Text = description ?? $"Table {table.Name}";
        _dashboard = null;
        SetContent(new TableManagerControl(_database, table));
    }

    private void SetContent(Control control)
    {
        _content.SuspendLayout();
        foreach (var child in _content.Controls.Cast<Control>().Where(child => !ReferenceEquals(child, control)).ToList())
        {
            _content.Controls.Remove(child);
            child.Dispose();
        }
        if (!_content.Controls.Contains(control)) _content.Controls.Add(control);
        _content.ResumeLayout(true);
    }

    private void RefreshCurrent()
    {
        if (_content.Controls.OfType<DashboardControl>().FirstOrDefault() is { } dashboard) dashboard.RefreshData();
        else if (_content.Controls.OfType<TableManagerControl>().FirstOrDefault() is { } table) table.RefreshData();
        else LoadTables();
    }

    private void ShowReports()
    {
        using var reports = new ReportsForm(_database);
        reports.ShowDialog(this);
    }

    private void Backup(object? sender, EventArgs e)
    {
        try
        {
            Cursor = Cursors.WaitCursor;
            var file = _database.CreateBackup();
            MessageBox.Show(this, "Sauvegarde créée avec succès :\n\n" + file, "Sauvegarde", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
        catch (Exception ex) { MessageBox.Show(this, ex.Message, "Sauvegarde impossible", MessageBoxButtons.OK, MessageBoxIcon.Error); }
        finally { Cursor = Cursors.Default; }
    }

    private void ShowAllTables()
    {
        using var chooser = new TableChooserForm(_tables);
        if (chooser.ShowDialog(this) == DialogResult.OK && chooser.SelectedTable is not null)
            OpenTable(chooser.SelectedTable.Name, DatabaseCatalog.DisplayName(chooser.SelectedTable.Name), "Gestion complète des enregistrements");
    }

    private DbTableInfo? FindTable(string name)
        => _tables.FirstOrDefault(t => string.Equals(t.Name, name, StringComparison.OrdinalIgnoreCase));
}

internal sealed class TableChooserForm : Form
{
    private readonly ListBox _list = new();
    private readonly IReadOnlyList<DbTableInfo> _tables;

    public TableChooserForm(IReadOnlyList<DbTableInfo> tables)
    {
        _tables = tables;
        Text = "Toutes les tables";
        StartPosition = FormStartPosition.CenterParent;
        ClientSize = new Size(440, 510);
        BackColor = Theme.Background;
        Padding = new Padding(22);
        Controls.Add(new Label { Text = "Choisir une table", AutoSize = true, Font = Theme.SubHeading, ForeColor = Theme.Text, Location = new Point(22, 20) });
        Controls.Add(new Label { Text = "L’accès générique permet d’ajouter, modifier, supprimer et exporter toutes les données.", AutoSize = false, Width = 390, Height = 38, ForeColor = Theme.MutedText, Font = Theme.Small, Location = new Point(22, 50) });
        _list.Location = new Point(22, 102);
        _list.Width = 394;
        _list.Height = 320;
        _list.Font = Theme.Body;
        _list.BorderStyle = BorderStyle.FixedSingle;
        _list.DisplayMember = nameof(DbTableInfo.Name);
        _list.DataSource = _tables.ToList();
        _list.DoubleClick += (_, _) => Open();
        Controls.Add(_list);
        var cancel = Theme.Button("Annuler", Color.FromArgb(241, 245, 249), Theme.Text, 100);
        cancel.Location = new Point(206, 450);
        cancel.Click += (_, _) => DialogResult = DialogResult.Cancel;
        Controls.Add(cancel);
        var open = Theme.Button("Ouvrir", Theme.Primary, Color.White, 100);
        open.Location = new Point(316, 450);
        open.Click += (_, _) => Open();
        Controls.Add(open);
        AcceptButton = open;
        CancelButton = cancel;
    }

    public DbTableInfo? SelectedTable => _list.SelectedItem as DbTableInfo;
    private void Open() { if (SelectedTable is not null) DialogResult = DialogResult.OK; }
}
