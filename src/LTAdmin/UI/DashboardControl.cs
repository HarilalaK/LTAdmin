using LTAdmin.Services;

namespace LTAdmin.UI;

public sealed class DashboardControl : UserControl, IRefreshableView
{
    private readonly AppComposition _app;
    private readonly FlowLayoutPanel _cards;
    private readonly Label _updated = new();
    private readonly Label _subtitle = new();
    private readonly Panel _recentHost;
    private readonly Action<string> _openTable;
    private readonly Action<string> _openModule;

    public DashboardControl(AppComposition app, Action<string> openTable, Action<string> openModule)
    {
        _app = app;
        _openTable = openTable;
        _openModule = openModule;
        Dock = DockStyle.Fill;
        BackColor = Theme.Background;
        Padding = new Padding(30, 24, 30, 24);

        var heading = new Panel { Dock = DockStyle.Top, Height = 74 };
        heading.Controls.Add(new Label { Text = "Tableau de bord", AutoSize = true, Font = Theme.Heading, ForeColor = Theme.Text, Location = new Point(0, 0) });
        _subtitle.Text = "Pilotez votre gestion scolaire depuis un seul espace.";
        _subtitle.AutoSize = true;
        _subtitle.ForeColor = Theme.MutedText;
        _subtitle.Location = new Point(2, 39);
        heading.Controls.Add(_subtitle);
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
            var stats = _app.Statistiques.GetDashboard();
            _subtitle.Text = string.IsNullOrWhiteSpace(stats.AnneeLibelle)
                ? "Aucune année scolaire active : déclarez-la dans Administration → Années scolaires."
                : $"Année scolaire active : {stats.AnneeLibelle} · {stats.NbClasses} classe(s)";
            _cards.Controls.Clear();
            AddCard("Étudiants", stats.NbEtudiants.ToString("N0"), "Dossiers enregistrés", Theme.Primary, () => _openModule("Étudiants"));
            AddCard("Inscriptions", stats.NbInscriptions.ToString("N0"), "Inscrits de l’année", Theme.Success, () => _openModule("Inscriptions"));
            AddCard("Recouvrement", stats.TauxRecouvrement.ToString("N1") + " %",
                $"{stats.TotalPaye:N0} / {stats.TotalDu:N0} {_app.Parametres.Devise}",
                Color.FromArgb(124, 58, 237), () => _openModule("Caisse / paiements"));
            var alertes = stats.NbEcheancesEchues + stats.NbAlertesAbsence;
            AddCard("Alertes", alertes.ToString("N0"),
                $"{stats.NbEcheancesEchues} échéance(s) échue(s) · {stats.NbAlertesAbsence} seuil(s) d’absence",
                Theme.Warning, null);
            _updated.Text = "Actualisé à " + DateTime.Now.ToString("HH:mm");
            LayoutRecent();
        }
        catch (Exception ex)
        {
            _recentHost.Controls.Clear();
            _recentHost.Controls.Add(new Label { Text = "Impossible de charger le tableau de bord : " + ex.Message, AutoSize = true, ForeColor = Color.FromArgb(185, 28, 28), Location = new Point(20, 20) });
        }
    }

    private void AddCard(string title, string value, string caption, Color accent, Action? onClick)
    {
        var card = Theme.Card();
        card.Width = 225;
        card.Height = 98;
        card.Margin = new Padding(0, 0, 14, 0);
        card.Cursor = onClick is null ? Cursors.Default : Cursors.Hand;
        card.Controls.Add(new Panel { BackColor = accent, Width = 4, Height = 58, Location = new Point(0, 20) });
        card.Controls.Add(new Label { Text = title, AutoSize = true, ForeColor = Theme.MutedText, Font = Theme.Small, Location = new Point(20, 15) });
        card.Controls.Add(new Label { Text = value, AutoSize = true, ForeColor = Theme.Text, Font = new Font("Segoe UI", 18, FontStyle.Bold), Location = new Point(20, 33) });
        var captionLabel = new Label { Text = caption, AutoSize = false, Width = 190, Height = 26, ForeColor = Theme.MutedText, Font = new Font("Segoe UI", 8f), Location = new Point(20, 62) };
        card.Controls.Add(captionLabel);
        if (onClick is not null) card.Click += (_, _) => onClick();
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
            ("Étudiants", "Dossiers et identité", (Action)(() => _openModule("Étudiants"))),
            ("Inscriptions", "Année scolaire et classe", (Action)(() => _openModule("Inscriptions"))),
            ("Saisie des notes", "Résultats du contrôle continu", (Action)(() => _openModule("Saisie des notes"))),
            ("Caisse / paiements", "Écolage et reçus", (Action)(() => _openModule("Caisse / paiements"))),
            ("Absences", "Suivi des présences", (Action)(() => _openTable("ABSENCE")))
        };
        var left = 20;
        foreach (var shortcut in shortcuts)
        {
            var button = new Button
            {
                Text = shortcut.Item1 + Environment.NewLine + shortcut.Item2,
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
            button.Click += (_, _) => shortcut.Item3();
            _recentHost.Controls.Add(button);
            left += 184;
            if (left + 170 > _recentHost.Width) break;
        }
    }
}
