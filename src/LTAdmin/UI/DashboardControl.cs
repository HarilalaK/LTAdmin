using LTAdmin.Services;
using LTAdmin.Services.Auth;

namespace LTAdmin.UI;

public sealed class DashboardControl : UserControl, IRefreshableView
{
    private readonly AppComposition _app;
    private readonly Action<string> _openModule;
    private readonly Label _welcome = new();
    private readonly Label _year = new();
    private readonly FlowLayoutPanel _shortcuts = new();

    public DashboardControl(AppComposition app, Action<string> openTable, Action<string> openModule)
    {
        _ = openTable;
        _app = app;
        _openModule = openModule;
        Dock = DockStyle.Fill;
        BackColor = Theme.Background;
        Padding = new Padding(24);
        AutoScroll = true;

        var heading = new Panel { Dock = DockStyle.Top, Height = 90, MinimumSize = new Size(300, 80) };
        heading.Controls.Add(new Label
        {
            Text = "Tableau de bord",
            AutoSize = true,
            Font = Theme.Heading,
            ForeColor = Theme.Text,
            Location = new Point(0, 4)
        });
        _welcome.AutoSize = true;
        _welcome.ForeColor = Theme.MutedText;
        _welcome.Location = new Point(2, 46);
        _welcome.MaximumSize = new Size(900, 0);
        heading.Controls.Add(_welcome);

        var info = Theme.Card();
        info.Dock = DockStyle.Top;
        info.Height = 88;
        info.Padding = new Padding(20);
        _year.AutoSize = true;
        _year.Font = Theme.SubHeading;
        _year.ForeColor = Theme.Text;
        info.Controls.Add(_year);

        _shortcuts.Dock = DockStyle.Fill;
        _shortcuts.WrapContents = true;
        _shortcuts.AutoScroll = true;
        _shortcuts.Padding = new Padding(0, 16, 0, 0);

        Controls.Add(_shortcuts);
        Controls.Add(info);
        Controls.Add(heading);

        Load += (_, _) => RefreshData();
    }

    public void RefreshData()
    {
        _welcome.Text = "Espace de travail prêt. Choisissez un module dans le menu de gauche.";
        try
        {
            var annee = _app.Admin.GetAnneeActive();
            _year.Text = annee?.Libelle is { Length: > 0 } lib
                ? "Année scolaire active : " + lib
                : "Aucune année scolaire n’est marquée comme active.";
        }
        catch (Exception ex)
        {
            _year.Text = "Année scolaire indisponible : " + ex.Message;
        }

        _shortcuts.Controls.Clear();
        var titles = new[]
        {
            Modules.Etudiants, Modules.Inscriptions, Modules.Notes,
            Modules.Ecolage, Modules.Absences, Modules.Rapports
        };
        foreach (var title in titles)
        {
            var card = Theme.Card();
            card.Width = 220;
            card.Height = 92;
            card.Margin = new Padding(0, 0, 14, 14);
            card.Cursor = Cursors.Hand;
            var label = new Label
            {
                Text = title,
                AutoSize = false,
                Dock = DockStyle.Fill,
                TextAlign = ContentAlignment.MiddleCenter,
                Font = Theme.BodyBold,
                ForeColor = Theme.Text
            };
            card.Controls.Add(label);
            var module = title;
            card.Click += (_, _) => _openModule(module);
            label.Click += (_, _) => _openModule(module);
            _shortcuts.Controls.Add(card);
        }
    }
}
