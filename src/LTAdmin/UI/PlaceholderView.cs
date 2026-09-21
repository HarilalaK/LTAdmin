namespace LTAdmin.UI;

/// <summary>Écran métier vide mais utilisable (navigation, titre, message).</summary>
public sealed class PlaceholderView : UserControl, IRefreshableView
{
    private readonly Label _title;
    private readonly Label _body;

    public PlaceholderView(string title, string description)
    {
        Dock = DockStyle.Fill;
        BackColor = Theme.Background;
        Padding = new Padding(28);

        var card = new Panel
        {
            Dock = DockStyle.Fill,
            BackColor = Theme.Surface,
            Padding = new Padding(32),
            MinimumSize = new Size(280, 180)
        };

        _title = new Label
        {
            Text = title,
            AutoSize = true,
            Font = Theme.Heading,
            ForeColor = Theme.Text,
            MaximumSize = new Size(900, 0)
        };
        _body = new Label
        {
            Text = description + Environment.NewLine + Environment.NewLine
                   + "Cet espace est prêt. Les fonctions détaillées seront branchées ici.",
            AutoSize = true,
            Font = Theme.Body,
            ForeColor = Theme.MutedText,
            MaximumSize = new Size(720, 0),
            Location = new Point(0, 56)
        };

        card.Controls.Add(_title);
        card.Controls.Add(_body);
        Controls.Add(card);
    }

    public void RefreshData() { }
}
