using System.Data;
using LTAdmin.Data;
using LTAdmin.Models;

namespace LTAdmin.UI;

public sealed class DashboardControl : UserControl
{
    private readonly AccessDatabase _database;
    private readonly DatabaseRepository _repository;
    private readonly FlowLayoutPanel _cards;
    private readonly Label _updated = new();
    private readonly Panel _recentHost;
    private readonly Action<string> _openTable;

    public DashboardControl(AccessDatabase database, Action<string> openTable)
    {
        _database = database;
        _repository = new DatabaseRepository(database);
        _openTable = openTable;
        Dock = DockStyle.Fill;
        BackColor = Theme.Background;
        Padding = new Padding(30, 24, 30, 24);

        var heading = new Panel { Dock = DockStyle.Top, Height = 74 };
        heading.Controls.Add(new Label { Text = "Tableau de bord", AutoSize = true, Font = Theme.Heading, ForeColor = Theme.Text, Location = new Point(0, 0) });
        heading.Controls.Add(new Label { Text = "Pilotez votre gestion scolaire depuis un seul espace.", AutoSize = true, ForeColor = Theme.MutedText, Location = new Point(2, 39) });
        _updated.Text = "";
        _updated.AutoSize = true;
        _updated.Anchor = AnchorStyles.Top | AnchorStyles.Right;
        _updated.ForeColor = Theme.MutedText;
        _updated.Font = Theme.Small;
        heading.Controls.Add(_updated);
        heading.Resize += (_, _) => _updated.Location = new Point(heading.Width - _updated.Width, 12);
        Controls.Add(heading);

        _cards = new FlowLayoutPanel
        {
            Dock = DockStyle.Top,
            Height = 122,
            WrapContents = false,
            AutoScroll = true,
            Padding = new Padding(0, 0, 0, 8),
            BackColor = Theme.Background
        };
        Controls.Add(_cards);

        _recentHost = Theme.Card();
        _recentHost.Dock = DockStyle.Fill;
        _recentHost.Margin = new Padding(0, 16, 0, 0);
        Controls.Add(_recentHost);
        Resize += (_, _) => LayoutRecent();
        Load += (_, _) => RefreshData();
    }

    public void RefreshData()
    {
        try
        {
            var tables = _repository.GetTables();
            _cards.Controls.Clear();
            AddCard("Étudiants", FindCount(tables, "ETUDIANT"), "Dossiers enregistrés", Theme.Primary, "ETUDIANT");
            AddCard("Formateurs", FindCount(tables, "FORMATEUR"), "Personnel enseignant", Theme.Success, "FORMATEUR");
            AddCard("Paiements", FindCount(tables, "PAIEMENT"), "Opérations d’écolage", Color.FromArgb(124, 58, 237), "PAIEMENT");
            AddCard("Tables actives", tables.Count, "Modules disponibles", Theme.Warning, null);
            _updated.Text = "Actualisé à " + DateTime.Now.ToString("HH:mm");
            LayoutRecent();
        }
        catch (Exception ex)
        {
            _recentHost.Controls.Clear();
            _recentHost.Controls.Add(new Label { Text = "Impossible de charger le tableau de bord : " + ex.Message, AutoSize = true, ForeColor = Color.FromArgb(185, 28, 28), Location = new Point(20, 20) });
        }
    }

    private void AddCard(string title, int count, string caption, Color accent, string? tableName)
    {
        var card = Theme.Card();
        card.Width = 205;
        card.Height = 98;
        card.Margin = new Padding(0, 0, 14, 0);
        card.Cursor = tableName is null ? Cursors.Default : Cursors.Hand;
        card.Controls.Add(new Panel { BackColor = accent, Width = 4, Height = 58, Location = new Point(0, 20) });
        card.Controls.Add(new Label { Text = title, AutoSize = true, ForeColor = Theme.MutedText, Font = Theme.Small, Location = new Point(20, 17) });
        card.Controls.Add(new Label { Text = count.ToString("N0"), AutoSize = true, ForeColor = Theme.Text, Font = new Font("Segoe UI", 18, FontStyle.Bold), Location = new Point(20, 35) });
        card.Controls.Add(new Label { Text = caption, AutoSize = true, ForeColor = Theme.MutedText, Font = new Font("Segoe UI", 8f), Location = new Point(86, 48) });
        if (tableName is not null) card.Click += (_, _) => _openTable(tableName);
        _cards.Controls.Add(card);
    }

    private void LayoutRecent()
    {
        if (_recentHost.Width < 100 || _recentHost.Height < 90) return;
        _recentHost.Controls.Clear();
        var title = new Label { Text = "Accès rapide", AutoSize = true, Font = Theme.SubHeading, ForeColor = Theme.Text, Location = new Point(20, 18) };
        _recentHost.Controls.Add(title);
        var sub = new Label { Text = "Ouvrez directement les écrans les plus utilisés.", AutoSize = true, ForeColor = Theme.MutedText, Font = Theme.Small, Location = new Point(20, 44) };
        _recentHost.Controls.Add(sub);

        var shortcuts = new[]
        {
            ("Étudiants", "ETUDIANT", "Dossiers et identité"),
            ("Inscriptions", "INSCRIPTION", "Année scolaire et classe"),
            ("Notes", "NOTE", "Saisie des résultats"),
            ("Paiements", "PAIEMENT", "Écolage et reçus"),
            ("Absences", "ABSENCE", "Suivi des présences")
        };
        var left = 20;
        foreach (var shortcut in shortcuts)
        {
            var button = new Button
            {
                Text = shortcut.Item1 + Environment.NewLine + shortcut.Item3,
                Width = 170,
                Height = 56,
                Location = new Point(left, 78),
                FlatStyle = FlatStyle.Flat,
                BackColor = Color.FromArgb(248, 250, 252),
                ForeColor = Theme.Text,
                Font = Theme.Small,
                TextAlign = ContentAlignment.MiddleLeft,
                Padding = new Padding(12, 0, 4, 0),
                Cursor = Cursors.Hand
            };
            button.FlatAppearance.BorderColor = Theme.Border;
            button.Click += (_, _) => _openTable(shortcut.Item2);
            _recentHost.Controls.Add(button);
            left += 184;
            if (left + 170 > _recentHost.Width) break;
        }
    }

    private int FindCount(IReadOnlyList<DbTableInfo> tables, string name)
    {
        var table = tables.FirstOrDefault(t => string.Equals(t.Name, name, StringComparison.OrdinalIgnoreCase));
        return table is null ? 0 : _repository.Count(table);
    }
}
