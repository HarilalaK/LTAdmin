using LTAdmin.Models;
using LTAdmin.Models.Dto;
using LTAdmin.Models.Entities;
using LTAdmin.Services;

namespace LTAdmin.UI.Views;

/// <summary>Caisse : situations d'écolage, échéances, encaissements et reçus.</summary>
public sealed class PaymentsControl : BusinessView
{
    private readonly ComboBox _classes = new();
    private readonly DataGridView _inscrits = new();
    private readonly DataGridView _echeances = new();
    private readonly DataGridView _paiements = new();
    private readonly Label _status = new();

    public PaymentsControl(AppComposition app, UserSession session) : base(app, session)
    {
        Controls.Add(BuildHeading("Caisse / paiements", "Écolage : échéanciers, encaissements, reçus et situations."));

        var actions = new Panel { Dock = DockStyle.Top, Height = 48 };
        _classes.DropDownStyle = ComboBoxStyle.DropDownList;
        _classes.Width = 250;
        _classes.Location = new Point(0, 2);
        _classes.Font = Theme.Body;
        _classes.SelectedIndexChanged += (_, _) => RefreshData();
        actions.Controls.Add(_classes);

        var scheduleButton = Theme.Button("Échéancier", Color.FromArgb(241, 245, 249), Theme.Text, 105);
        scheduleButton.Location = new Point(260, 1);
        scheduleButton.Click += (_, _) => GenerateSchedule();
        actions.Controls.Add(scheduleButton);

        var payButton = Theme.Button("Encaisser", Theme.Success, Color.White, 105);
        payButton.Location = new Point(375, 1);
        payButton.Click += (_, _) => Encaisser();
        actions.Controls.Add(payButton);

        var remiseButton = Theme.Button("Remise", Color.FromArgb(241, 245, 249), Theme.Text, 95);
        remiseButton.Location = new Point(490, 1);
        remiseButton.Click += (_, _) => AppliquerRemise();
        actions.Controls.Add(remiseButton);

        var cancelButton = Theme.Button("Annuler paiement", Color.FromArgb(254, 226, 226), Color.FromArgb(185, 28, 28), 140);
        cancelButton.Location = new Point(595, 1);
        cancelButton.Click += (_, _) => AnnulerPaiement();
        actions.Controls.Add(cancelButton);
        Controls.Add(actions);

        var bottom = new Panel { Dock = DockStyle.Bottom, Height = 29 };
        _status.AutoSize = true;
        _status.ForeColor = Theme.MutedText;
        _status.Font = Theme.Small;
        _status.Location = new Point(0, 5);
        bottom.Controls.Add(_status);
        Controls.Add(bottom);

        var split = new SplitContainer { Dock = DockStyle.Fill, Orientation = Orientation.Horizontal, SplitterDistance = 220 };
        Controls.Add(split);

        Theme.StyleGrid(_inscrits);
        _inscrits.Dock = DockStyle.Fill;
        _inscrits.AutoGenerateColumns = false;
        _inscrits.Columns.Add(TextColumn("Matricule", "Matricule", 110));
        _inscrits.Columns.Add(TextColumn("Nom", "Nom", 140));
        _inscrits.Columns.Add(TextColumn("Prenom", "Prénom", 140));
        _inscrits.Columns.Add(TextColumn("TotalDu", "Dû", 110, "N0"));
        _inscrits.Columns.Add(TextColumn("TotalPaye", "Payé", 110, "N0"));
        _inscrits.Columns.Add(TextColumn("Reste", "Reste", 110, "N0"));
        _inscrits.SelectionChanged += (_, _) => RefreshDetails();
        split.Panel1.Controls.Add(_inscrits);

        var lower = new SplitContainer { Dock = DockStyle.Fill, Orientation = Orientation.Vertical, SplitterDistance = 480 };
        split.Panel2.Controls.Add(lower);

        Theme.StyleGrid(_echeances);
        _echeances.Dock = DockStyle.Fill;
        _echeances.AutoGenerateColumns = false;
        _echeances.Columns.Add(TextColumn(nameof(EcheanceDetail.NumTranche), "N°", 45));
        _echeances.Columns.Add(TextColumn(nameof(EcheanceDetail.Libelle), "Tranche", 170));
        _echeances.Columns.Add(TextColumn(nameof(EcheanceDetail.MontantDu), "Dû", 100, "N0"));
        _echeances.Columns.Add(TextColumn(nameof(EcheanceDetail.TotalPaye), "Payé", 100, "N0"));
        _echeances.Columns.Add(TextColumn(nameof(EcheanceDetail.Reste), "Reste", 100, "N0"));
        _echeances.Columns.Add(TextColumn(nameof(EcheanceDetail.DateEcheance), "Échéance", 100, "d"));
        _echeances.Columns.Add(TextColumn(nameof(EcheanceDetail.Statut), "Statut", 90));
        _echeances.SelectionChanged += (_, _) => RefreshPaiements();
        lower.Panel1.Controls.Add(_echeances);

        Theme.StyleGrid(_paiements);
        _paiements.Dock = DockStyle.Fill;
        _paiements.AutoGenerateColumns = false;
        _paiements.Columns.Add(TextColumn("DatePaiement", "Date", 110, "g"));
        _paiements.Columns.Add(TextColumn("Montant", "Montant", 100, "N0"));
        _paiements.Columns.Add(TextColumn("ModePaie", "Mode", 110));
        _paiements.Columns.Add(TextColumn("NumRecu", "Reçu", 130));
        _paiements.Columns.Add(TextColumn("CodeUtr", "Caisse", 90));
        lower.Panel2.Controls.Add(_paiements);

        Load += (_, _) => LoadClasses();
    }

    private sealed class LigneSituation
    {
        public int? IdInscription { get; set; }
        public string? Matricule { get; set; }
        public string? Nom { get; set; }
        public string? Prenom { get; set; }
        public decimal TotalDu { get; set; }
        public decimal TotalPaye { get; set; }
        public decimal Reste => TotalDu - TotalPaye;
    }

    private void LoadClasses()
    {
        try
        {
            var classes = App.Referentiel.ListClassesDetail(null);
            _classes.DisplayMember = nameof(ClasseDetail.Libelle);
            _classes.DataSource = classes;
            if (classes.Count > 0) RefreshData();
            else _status.Text = "Aucune classe : créez d’abord les classes du référentiel.";
        }
        catch (Exception ex) { _status.Text = "Erreur : " + ex.Message; }
    }

    public override void RefreshData()
    {
        try
        {
            Cursor = Cursors.WaitCursor;
            if (_classes.SelectedItem is not ClasseDetail classe || classe.IdClasse is null)
            {
                _inscrits.DataSource = null;
                return;
            }
            var lignes = new List<LigneSituation>();
            foreach (var inscrit in App.Inscriptions.ListByClasse(classe.IdClasse.Value))
            {
                var situation = App.Ecolage.GetSituation(inscrit.IdInscription!.Value);
                lignes.Add(new LigneSituation
                {
                    IdInscription = inscrit.IdInscription,
                    Matricule = inscrit.Matricule,
                    Nom = inscrit.Nom,
                    Prenom = inscrit.Prenom,
                    TotalDu = situation.TotalDu,
                    TotalPaye = situation.TotalPaye
                });
            }
            _inscrits.DataSource = lignes;
            _status.Text = $"{lignes.Count:N0} inscrit(s) — montants en {App.Parametres.Devise}.";
            _status.ForeColor = Theme.MutedText;
            RefreshDetails();
        }
        catch (Exception ex)
        {
            _status.Text = "Erreur : " + ex.Message;
            _status.ForeColor = Color.FromArgb(185, 28, 28);
        }
        finally { Cursor = Cursors.Default; }
    }

    private void RefreshDetails()
    {
        try
        {
            var ligne = _inscrits.CurrentRow?.DataBoundItem as LigneSituation;
            _echeances.DataSource = ligne?.IdInscription is null
                ? null
                : App.Ecolage.ListEcheances(ligne.IdInscription.Value);
            RefreshPaiements();
        }
        catch { _echeances.DataSource = null; }
    }

    private void RefreshPaiements()
    {
        try
        {
            var echeance = _echeances.CurrentRow?.DataBoundItem as EcheanceDetail;
            _paiements.DataSource = echeance?.IdEcheance is null
                ? null
                : App.Ecolage.ListPaiements(echeance.IdEcheance.Value);
        }
        catch { _paiements.DataSource = null; }
    }

    private void GenerateSchedule()
    {
        var ligne = _inscrits.CurrentRow?.DataBoundItem as LigneSituation;
        if (ligne?.IdInscription is null)
        {
            ShowInfo("Sélectionnez d’abord un inscrit.", "Échéancier");
            return;
        }
        if (!Confirm($"Générer les tranches manquantes pour « {ligne.Nom} {ligne.Prenom} » ?\n\nLes tranches existantes sont conservées.", "Générer l’échéancier"))
            return;
        var result = App.Ecolage.GenererEcheancier(ligne.IdInscription.Value, CodeUtr);
        if (result.IsFailure) ShowError(result.FullMessage());
        else
        {
            ShowInfo(result.Message, "Échéancier");
            RefreshData();
        }
    }

    private void Encaisser()
    {
        var echeance = _echeances.CurrentRow?.DataBoundItem as EcheanceDetail;
        if (echeance?.IdEcheance is null)
        {
            ShowInfo("Sélectionnez d’abord une échéance.", "Encaissement");
            return;
        }
        using var dialog = new PaymentDialog(App, Session, echeance);
        if (dialog.ShowDialog(FindForm()) == DialogResult.OK) RefreshData();
    }

    private void AppliquerRemise()
    {
        var echeance = _echeances.CurrentRow?.DataBoundItem as EcheanceDetail;
        if (echeance?.IdEcheance is null)
        {
            ShowInfo("Sélectionnez d’abord une échéance.", "Remise");
            return;
        }
        var saisie = DialogPrompt.Show(FindForm(), "Remise", $"Remise sur « {echeance.Libelle} » (montant dû : {echeance.MontantDu:N0}) :",
            (echeance.Remise ?? 0m).ToString("N0"));
        if (saisie is null) return;
        if (!decimal.TryParse(saisie, out var remise))
        {
            ShowError("Montant invalide.");
            return;
        }
        var result = App.Ecolage.AppliquerRemise(echeance.IdEcheance.Value, remise, CodeUtr);
        if (result.IsFailure) ShowError(result.FullMessage());
        else RefreshData();
    }

    private void AnnulerPaiement()
    {
        var paiement = _paiements.CurrentRow?.DataBoundItem as Paiement;
        if (paiement?.IdPaiement is null)
        {
            ShowInfo("Sélectionnez d’abord un paiement dans la liste de droite.", "Annulation");
            return;
        }
        if (!Confirm($"Annuler le paiement {paiement.NumRecu} ({paiement.Montant:N0} {App.Parametres.Devise}) ?\n\nLe statut de l’échéance sera recalculé.", "Annuler le paiement"))
            return;
        var result = App.Ecolage.AnnulerPaiement(paiement.IdPaiement.Value, CodeUtr);
        if (result.IsFailure) ShowError(result.FullMessage());
        else
        {
            ShowInfo(result.Message, "Annulation");
            RefreshData();
        }
    }
}
