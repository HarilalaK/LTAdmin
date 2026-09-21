using LTAdmin.Models;
using LTAdmin.Services;

namespace LTAdmin.UI.Views;

/// <summary>
/// Base des écrans métier : accès aux services via la composition, session
/// courante pour la journalisation, helpers d'affichage. Aucune requête SQL
/// ni règle de gestion dans les vues : elles appellent les services et
/// affichent les résultats.
/// </summary>
public abstract class BusinessView : UserControl, IRefreshableView
{
    protected BusinessView(AppComposition app, UserSession session)
    {
        App = app;
        Session = session;
        Dock = DockStyle.Fill;
        BackColor = Theme.Background;
        Padding = new Padding(30, 24, 30, 24);
    }

    protected AppComposition App { get; }
    protected UserSession Session { get; }
    protected string CodeUtr => Session.Login;

    public abstract void RefreshData();

    protected static Panel BuildHeading(string title, string subtitle)
    {
        var heading = new Panel { Dock = DockStyle.Top, Height = 70 };
        heading.Controls.Add(new Label { Text = title, AutoSize = true, Font = Theme.Heading, ForeColor = Theme.Text, Location = new Point(0, 0) });
        heading.Controls.Add(new Label { Text = subtitle, AutoSize = true, ForeColor = Theme.MutedText, Location = new Point(2, 39) });
        return heading;
    }

    protected void ShowError(string message, string title = "Opération impossible")
        => MessageBox.Show(FindForm(), message, title, MessageBoxButtons.OK, MessageBoxIcon.Error);

    protected void ShowInfo(string message, string title = "LTAdmin")
        => MessageBox.Show(FindForm(), message, title, MessageBoxButtons.OK, MessageBoxIcon.Information);

    protected bool Confirm(string message, string title = "Confirmer")
        => MessageBox.Show(FindForm(), message, title, MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes;

    protected static DataGridViewTextBoxColumn TextColumn(string property, string header, int width = 0, string? format = null)
    {
        var column = new DataGridViewTextBoxColumn
        {
            DataPropertyName = property,
            HeaderText = header,
            SortMode = DataGridViewColumnSortMode.NotSortable
        };
        if (width > 0) column.Width = width;
        if (format is not null) column.DefaultCellStyle.Format = format;
        return column;
    }

    protected static DataGridViewCheckBoxColumn CheckColumn(string property, string header, int width = 0)
    {
        var column = new DataGridViewCheckBoxColumn
        {
            DataPropertyName = property,
            HeaderText = header,
            SortMode = DataGridViewColumnSortMode.NotSortable
        };
        if (width > 0) column.Width = width;
        return column;
    }
}

/// <summary>Petite boîte de saisie libre (montants, motifs…).</summary>
public static class DialogPrompt
{
    public static string? Show(IWin32Window? owner, string title, string label, string defaultValue = "")
    {
        using var dialog = new Form
        {
            Text = title,
            StartPosition = FormStartPosition.CenterParent,
            FormBorderStyle = FormBorderStyle.FixedDialog,
            MaximizeBox = false,
            MinimizeBox = false,
            ClientSize = new Size(380, 160),
            BackColor = Theme.Background,
            Font = Theme.Body
        };
        dialog.Controls.Add(new Label { Text = label, AutoSize = true, ForeColor = Theme.Text, Location = new Point(20, 18) });
        var input = new TextBox { Location = new Point(20, 44), Width = 336, BorderStyle = BorderStyle.FixedSingle, Text = defaultValue };
        dialog.Controls.Add(input);
        var ok = Theme.Button("Valider", Theme.Primary, Color.White, 100);
        ok.Location = new Point(256, 100);
        ok.Click += (_, _) => { dialog.DialogResult = DialogResult.OK; dialog.Close(); };
        dialog.Controls.Add(ok);
        var cancel = Theme.Button("Annuler", Color.FromArgb(241, 245, 249), Theme.Text, 100);
        cancel.Location = new Point(146, 100);
        cancel.Click += (_, _) => { dialog.DialogResult = DialogResult.Cancel; dialog.Close(); };
        dialog.Controls.Add(cancel);
        dialog.AcceptButton = ok;
        dialog.CancelButton = cancel;
        return dialog.ShowDialog(owner) == DialogResult.OK ? input.Text : null;
    }
}
