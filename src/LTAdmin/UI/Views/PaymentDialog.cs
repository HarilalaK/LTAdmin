using System.Globalization;
using LTAdmin.Models;
using LTAdmin.Models.Dto;
using LTAdmin.Services;

namespace LTAdmin.UI.Views;

/// <summary>Dialogue d'encaissement : montant, mode, référence, observation.</summary>
public sealed class PaymentDialog : Form
{
    private readonly AppComposition _app;
    private readonly UserSession _session;
    private readonly EcheanceDetail _echeance;

    private readonly TextBox _montant = new();
    private readonly ComboBox _mode = new();
    private readonly TextBox _reference = new();
    private readonly TextBox _observation = new();
    private readonly DateTimePicker _datePaiement = new();

    public PaymentDialog(AppComposition app, UserSession session, EcheanceDetail echeance)
    {
        _app = app;
        _session = session;
        _echeance = echeance;

        Text = "Encaisser un paiement";
        StartPosition = FormStartPosition.CenterParent;
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox = false;
        MinimizeBox = false;
        ClientSize = new Size(440, 430);
        BackColor = Theme.Background;
        Font = Theme.Body;

        var title = new Panel { Dock = DockStyle.Top, Height = 86, BackColor = Theme.Surface, Padding = new Padding(22, 14, 22, 8) };
        title.Controls.Add(new Label { Text = echeance.Libelle ?? "Échéance", AutoSize = true, Font = Theme.SubHeading, ForeColor = Theme.Text, Location = new Point(22, 12) });
        title.Controls.Add(new Label
        {
            Text = $"Dû : {echeance.NetDu:N0} · Payé : {echeance.TotalPaye:N0} · Reste : {echeance.Reste:N0} {app.Parametres.Devise}",
            AutoSize = true, Font = Theme.BodyBold, ForeColor = Theme.Primary, Location = new Point(22, 42)
        });
        title.Controls.Add(new Label
        {
            Text = echeance.DateEcheance.HasValue ? "Échéance au " + echeance.DateEcheance.Value.ToString("dd/MM/yyyy") : "Sans date d’échéance",
            AutoSize = true, Font = Theme.Small, ForeColor = Theme.MutedText, Location = new Point(22, 62)
        });
        Controls.Add(title);

        var fields = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2, Padding = new Padding(22, 10, 22, 6) };
        fields.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 130));
        fields.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        Controls.Add(fields);

        AddRow(fields, "Montant *", _montant, echeance.Reste.ToString("N0", CultureInfo.CurrentCulture));
        _mode.Items.AddRange(new object[] { "Espèces", "Chèque", "Virement", "Mobile Money", "Autre" });
        _mode.Text = "Espèces";
        AddRow(fields, "Mode *", _mode);
        AddRow(fields, "Référence", _reference);
        AddRow(fields, "Observation", _observation);
        _datePaiement.Format = DateTimePickerFormat.Short;
        _datePaiement.Value = DateTime.Today;
        AddRow(fields, "Date", _datePaiement);

        var footer = new Panel { Dock = DockStyle.Bottom, Height = 62, Padding = new Padding(22, 10, 22, 10) };
        var cancel = Theme.Button("Annuler", Color.FromArgb(241, 245, 249), Theme.Text, 100);
        cancel.Location = new Point(212, 12);
        cancel.Click += (_, _) => DialogResult = DialogResult.Cancel;
        footer.Controls.Add(cancel);
        var save = Theme.Button("Encaisser", Theme.Success, Color.White, 120);
        save.Location = new Point(320, 12);
        save.Click += (_, _) => Save();
        footer.Controls.Add(save);
        Controls.Add(footer);
        AcceptButton = save;
        CancelButton = cancel;
    }

    public string? NumeroRecu { get; private set; }

    private static void AddRow(TableLayoutPanel panel, string label, Control editor, string? value = null)
    {
        if (editor is TextBox text && value is not null) text.Text = value;
        editor.Dock = DockStyle.Fill;
        editor.Margin = new Padding(0, 5, 0, 5);
        if (editor is TextBox box) box.BorderStyle = BorderStyle.FixedSingle;
        var row = panel.RowCount++;
        panel.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        panel.Controls.Add(new Label
        {
            Text = label, AutoSize = false, Height = 30, TextAlign = ContentAlignment.MiddleLeft,
            ForeColor = Theme.Text, Font = Theme.Body, Dock = DockStyle.Fill, Margin = new Padding(0, 5, 8, 5)
        }, 0, row);
        panel.Controls.Add(editor, 1, row);
    }

    private void Save()
    {
        if (!decimal.TryParse(_montant.Text, NumberStyles.Number, CultureInfo.CurrentCulture, out var montant))
        {
            MessageBox.Show(this, "Montant invalide.", "Vérifiez la saisie", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }
        var result = _app.Ecolage.Encaisser(
            _echeance.IdEcheance!.Value, montant, _mode.Text,
            string.IsNullOrWhiteSpace(_reference.Text) ? null : _reference.Text.Trim(),
            string.IsNullOrWhiteSpace(_observation.Text) ? null : _observation.Text.Trim(),
            _session.Login, _datePaiement.Value.Date);
        if (result.IsFailure || result.Value is null)
        {
            MessageBox.Show(this, result.FullMessage(), "Vérifiez la saisie", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }
        NumeroRecu = result.Value.NumRecu;
        MessageBox.Show(this, $"Paiement enregistré.\n\nReçu : {result.Value.NumRecu}\nNouveau statut : {result.Value.NouveauStatut}",
            "Encaissement", MessageBoxButtons.OK, MessageBoxIcon.Information);
        DialogResult = DialogResult.OK;
        Close();
    }
}
