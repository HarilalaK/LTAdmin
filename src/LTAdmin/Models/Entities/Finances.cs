namespace LTAdmin.Models.Entities;

// Bloc Écolage & paie : TARIF, ECHEANCIER, PAIEMENT, PAIE_FORMATEUR.
// Les montants Access (CURRENCY) sont mappés en decimal.

/// <summary>Tarif de frais pour une classe, découpé en tranches.</summary>
public sealed class Tarif
{
    public int? IdTarif { get; set; }
    public int? IdClasse { get; set; }
    public string? TypeFrais { get; set; }
    public decimal? Montant { get; set; }
    public int? NbTranches { get; set; }
    public bool? Obligatoire { get; set; }
    public string? Observation { get; set; }
}

/// <summary>Tranche d'échéancier d'une inscription. STATUT : DU / PARTIEL / SOLDE.</summary>
public sealed class Echeancier
{
    public int? IdEcheance { get; set; }
    public int? IdInscription { get; set; }
    public int? IdTarif { get; set; }
    public int? NumTranche { get; set; }
    public string? Libelle { get; set; }
    public decimal? MontantDu { get; set; }
    public DateTime? DateEcheance { get; set; }
    public string? Statut { get; set; }
    public decimal? Remise { get; set; }
}

/// <summary>Encaissement sur une échéance. NUM_RECU unique (IX_PAI_RECU).</summary>
public sealed class Paiement
{
    public int? IdPaiement { get; set; }
    public int? IdEcheance { get; set; }
    public string? NumRecu { get; set; }
    public DateTime? DatePaiement { get; set; }
    public decimal? Montant { get; set; }
    public string? ModePaie { get; set; }
    public string? RefExterne { get; set; }
    public string? CodeUtr { get; set; }
    public string? Observation { get; set; }
}

/// <summary>Paie d'un formateur : heures réalisées × taux horaire.</summary>
public sealed class PaieFormateur
{
    public int? IdPaie { get; set; }
    public int? IdFormateur { get; set; }
    public string? Periode { get; set; }
    public double? NbHeures { get; set; }
    public decimal? Taux { get; set; }
    public decimal? Montant { get; set; }
    public bool? Paye { get; set; }
    public DateTime? DatePaie { get; set; }
    public string? Observation { get; set; }
}
