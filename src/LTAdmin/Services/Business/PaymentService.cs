using LTAdmin.Core;
using LTAdmin.Data;
using LTAdmin.Models.Dto;
using LTAdmin.Models.Entities;
using LTAdmin.Repositories;
using LTAdmin.Services.Common;
using LTAdmin.Services.Logging;
using LTAdmin.Services.Referentiel;
using LTAdmin.Services.Validation;

namespace LTAdmin.Services.Business;

/// <summary>
/// Écolage : tarifs, échéanciers, caisse (encaissements) et situations.
/// Réimplémentations C# de GENERER_ECHEANCIER (idempotent : seules les
/// tranches manquantes sont créées), MAJ_STATUT_ECHEANCE (DU / PARTIEL /
/// SOLDE) et NOUVEAU_RECU (reçu unique REC-AAAA-######).
/// </summary>
public sealed class PaymentService : ServiceBase
{
    private readonly FinanceRepository _finances;
    private readonly EnrollmentRepository _inscriptions;

    public const string StatutDu = "DU";
    public const string StatutPartiel = "PARTIEL";
    public const string StatutSolde = "SOLDE";

    public PaymentService(AccessDatabase database, AppLogger logger, JournalService journal, ParametreService parametres)
        : base(database, logger, journal, parametres)
    {
        _finances = new FinanceRepository(database);
        _inscriptions = new EnrollmentRepository(database);
    }

    public List<Tarif> ListTarifs(int idClasse)
    {
        try { return _finances.ListTarifsByClasse(idClasse); }
        catch (Exception ex)
        {
            Logger.Error("Liste des tarifs", ex);
            return new List<Tarif>();
        }
    }

    public Result<int> CreateTarif(Tarif tarif, string codeUtr)
    {
        var validation = PaymentValidator.ValidateTarif(tarif);
        if (!validation.IsValid) return Invalid<int>(validation);
        try
        {
            var id = _finances.InsertTarif(tarif);
            Journal.LogCreation(codeUtr, Tables.Tarif, id, tarif.TypeFrais);
            return Result<int>.Ok(id, "Tarif créé.");
        }
        catch (Exception ex) { return Failure<int>("Création d’un tarif", ex); }
    }

    public Result UpdateTarif(Tarif tarif, string codeUtr)
    {
        if (!tarif.IdTarif.HasValue)
            return Result.Fail("Tarif introuvable.", ErrorCodes.NotFound);
        var validation = PaymentValidator.ValidateTarif(tarif);
        if (!validation.IsValid) return Invalid(validation);
        try
        {
            var updated = _finances.UpdateTarif(tarif);
            if (updated == 0)
                return Result.Fail("Tarif introuvable.", ErrorCodes.NotFound);
            Journal.LogModification(codeUtr, Tables.Tarif, tarif.IdTarif, tarif.TypeFrais);
            return Result.Ok("Tarif enregistré.");
        }
        catch (Exception ex) { return Failure("Modification d’un tarif", ex); }
    }

    public Result DeleteTarif(int idTarif, string codeUtr)
    {
        try
        {
            var existing = _finances.GetTarif(idTarif);
            if (existing is null)
                return Result.Fail("Tarif introuvable.", ErrorCodes.NotFound);
            _finances.DeleteTarif(idTarif);
            Journal.LogSuppression(codeUtr, Tables.Tarif, idTarif, existing.TypeFrais);
            return Result.Ok("Tarif supprimé.");
        }
        catch (Exception ex)
        {
            if (OleDbExceptionHelper.IsForeignKeyViolation(ex))
                return Result.Fail("Suppression impossible : des échéances utilisent déjà ce tarif.",
                    ErrorCodes.ForeignKeyViolation);
            return Failure("Suppression d’un tarif", ex);
        }
    }

    public List<EcheanceDetail> ListEcheances(int idInscription)
    {
        try { return _finances.ListEcheancesByInscription(idInscription); }
        catch (Exception ex)
        {
            Logger.Error("Échéances d’une inscription", ex);
            return new List<EcheanceDetail>();
        }
    }

    public List<Paiement> ListPaiements(int idEcheance)
    {
        try { return _finances.ListPaiementsByEcheance(idEcheance); }
        catch (Exception ex)
        {
            Logger.Error("Paiements d’une échéance", ex);
            return new List<Paiement>();
        }
    }

    /// <summary>
    /// Génère les tranches manquantes de l'échéancier d'une inscription :
    /// pour chaque tarif de la classe, découpe MONTANT en NB_TRANCHES tranches
    /// mensuelles à partir de la date d'inscription (la dernière tranche
    /// absorbe les arrondis). STATUT initial = DU.
    /// </summary>
    public Result<int> GenererEcheancier(int idInscription, string codeUtr)
    {
        try
        {
            var inscription = _inscriptions.GetById(idInscription);
            if (inscription is null)
                return Result<int>.Fail("Inscription introuvable.", ErrorCodes.NotFound);
            var tarifs = _finances.ListTarifsByClasse(inscription.IdClasse!.Value);
            if (tarifs.Count == 0)
                return Result<int>.Fail("Aucun tarif défini pour cette classe : créez d’abord les tarifs.",
                    ErrorCodes.BusinessRule);

            var baseDate = (inscription.DateInscription ?? DateTime.Today).Date;
            var created = 0;
            using var tx = Db.BeginTransaction();
            foreach (var tarif in tarifs)
            {
                var montant = tarif.Montant ?? 0m;
                if (montant <= 0) continue;
                var nbTranches = tarif.NbTranches is > 0 ? tarif.NbTranches.Value : 1;
                var existantes = _finances.CountByInscriptionTarif(idInscription, tarif.IdTarif!.Value);
                if (existantes >= nbTranches) continue;

                var part = Math.Round(montant / nbTranches, 2);
                var dejaCree = part * existantes;
                for (var tranche = existantes + 1; tranche <= nbTranches; tranche++)
                {
                    var montantTranche = tranche == nbTranches
                        ? montant - dejaCree - part * (tranche - existantes - 1)
                        : part;
                    if (montantTranche <= 0)
                        montantTranche = part; // Tranches existantes saisies à la main : on conserve la part théorique.
                    var libelle = $"{tarif.TypeFrais} — tranche {tranche}/{nbTranches}";
                    if (libelle.Length > 80) libelle = libelle.Substring(0, 80);
                    _finances.InsertEcheance(new Echeancier
                    {
                        IdInscription = idInscription,
                        IdTarif = tarif.IdTarif,
                        NumTranche = tranche,
                        Libelle = libelle,
                        MontantDu = montantTranche,
                        DateEcheance = baseDate.AddMonths(tranche - 1),
                        Statut = StatutDu,
                        Remise = 0m
                    });
                    created++;
                }
            }
            tx.Complete();

            Journal.LogOperation(codeUtr, "GENERATION_ECHEANCIER", Tables.Echeancier, null,
                $"Inscription {idInscription} : {created} tranche(s) créée(s).");
            return created == 0
                ? Result<int>.Ok(0, "Échéancier déjà complet : aucune tranche à créer.")
                : Result<int>.Ok(created, $"{created} tranche(s) d’échéancier créée(s).");
        }
        catch (Exception ex) { return Failure<int>("Génération de l’échéancier", ex); }
    }

    /// <summary>Recalcule le statut d'une échéance (DU / PARTIEL / SOLDE).</summary>
    public string MajStatutEcheance(int idEcheance)
    {
        var echeance = _finances.GetEcheance(idEcheance);
        if (echeance is null) return string.Empty;
        var netDu = (echeance.MontantDu ?? 0m) - (echeance.Remise ?? 0m);
        var paye = _finances.TotalPayeByEcheance(idEcheance);
        var statut = paye <= 0.005m ? StatutDu : paye >= netDu - 0.005m ? StatutSolde : StatutPartiel;
        _finances.UpdateStatut(idEcheance, statut);
        return statut;
    }

    public void MajStatutsInscription(int idInscription)
    {
        foreach (var echeance in _finances.ListEcheancesByInscription(idInscription))
        {
            if (echeance.IdEcheance.HasValue)
                MajStatutEcheance(echeance.IdEcheance.Value);
        }
    }

    /// <summary>Encaisse un paiement sur une échéance (reçu unique, statut recalculé).</summary>
    public Result<PaiementCree> Encaisser(int idEcheance, decimal montant, string? modePaie,
        string? refExterne, string? observation, string codeUtr, DateTime? datePaiement = null)
    {
        try
        {
            var echeance = _finances.GetEcheance(idEcheance);
            if (echeance is null)
                return Result<PaiementCree>.Fail("Échéance introuvable.", ErrorCodes.NotFound);
            var netDu = (echeance.MontantDu ?? 0m) - (echeance.Remise ?? 0m);
            var paye = _finances.TotalPayeByEcheance(idEcheance);
            var reste = netDu - paye;

            var validation = PaymentValidator.ValidateEncaissement(montant, modePaie, reste);
            if (!string.IsNullOrEmpty(refExterne) && refExterne.Length > 80)
                validation.AddError("Référence externe : 80 caractères maximum.");
            if (!string.IsNullOrEmpty(observation) && observation.Length > 300)
                validation.AddError("Observation : 300 caractères maximum.");
            if (!validation.IsValid) return Invalid<PaiementCree>(validation);

            using var tx = Db.BeginTransaction();
            var numRecu = GenererNumeroRecu();
            var idPaiement = _finances.InsertPaiement(new Paiement
            {
                IdEcheance = idEcheance,
                NumRecu = numRecu,
                DatePaiement = datePaiement ?? DateTime.Now,
                Montant = montant,
                ModePaie = modePaie!.Trim(),
                RefExterne = string.IsNullOrWhiteSpace(refExterne) ? null : refExterne.Trim(),
                CodeUtr = codeUtr,
                Observation = string.IsNullOrWhiteSpace(observation) ? null : observation.Trim()
            });
            var statut = MajStatutEcheance(idEcheance);
            tx.Complete();

            Journal.LogCreation(codeUtr, Tables.Paiement, idPaiement,
                $"{numRecu} : {montant:N0} {Parametres.Devise} ({modePaie})");
            return Result<PaiementCree>.Ok(
                new PaiementCree { IdPaiement = idPaiement, NumRecu = numRecu, NouveauStatut = statut },
                $"Paiement enregistré — reçu {numRecu} ({statut}).");
        }
        catch (Exception ex)
        {
            if (OleDbExceptionHelper.IsUniqueViolation(ex))
                return Result<PaiementCree>.Fail("Numéro de reçu déjà utilisé : réessayez l’encaissement.",
                    ErrorCodes.UniqueViolation);
            return Failure<PaiementCree>("Encaissement d’un paiement", ex);
        }
    }

    /// <summary>Annule explicitement un paiement (suppression + recalcul du statut).</summary>
    public Result AnnulerPaiement(int idPaiement, string codeUtr)
    {
        try
        {
            var paiement = _finances.GetPaiement(idPaiement);
            if (paiement is null)
                return Result.Fail("Paiement introuvable.", ErrorCodes.NotFound);
            using var tx = Db.BeginTransaction();
            _finances.DeletePaiement(idPaiement);
            if (paiement.IdEcheance.HasValue)
                MajStatutEcheance(paiement.IdEcheance.Value);
            tx.Complete();
            Journal.LogSuppression(codeUtr, Tables.Paiement, idPaiement,
                $"Annulation du reçu {paiement.NumRecu} ({paiement.Montant:N0}).");
            return Result.Ok($"Paiement {paiement.NumRecu} annulé.");
        }
        catch (Exception ex) { return Failure("Annulation d’un paiement", ex); }
    }

    public Result AppliquerRemise(int idEcheance, decimal? remise, string codeUtr)
    {
        try
        {
            var echeance = _finances.GetEcheance(idEcheance);
            if (echeance is null)
                return Result.Fail("Échéance introuvable.", ErrorCodes.NotFound);
            var validation = PaymentValidator.ValidateRemise(remise, echeance.MontantDu ?? 0m);
            if (!validation.IsValid) return Invalid(validation);
            _finances.UpdateRemise(idEcheance, remise ?? 0m);
            var statut = MajStatutEcheance(idEcheance);
            Journal.LogModification(codeUtr, Tables.Echeancier, idEcheance, $"Remise : {remise:N0} ({statut}).");
            return Result.Ok($"Remise enregistrée ({statut}).");
        }
        catch (Exception ex) { return Failure("Application d’une remise", ex); }
    }

    public SituationEcolageRow GetSituation(int idInscription)
    {
        var situation = new SituationEcolageRow { IdInscription = idInscription };
        try
        {
            foreach (var echeance in _finances.ListEcheancesByInscription(idInscription))
            {
                situation.TotalDu += echeance.NetDu;
                situation.TotalPaye += echeance.TotalPaye;
            }
        }
        catch (Exception ex) { Logger.Error("Situation d’écolage", ex); }
        return situation;
    }

    /// <summary>Génère un numéro de reçu unique REC-AAAA-###### (équivalent NOUVEAU_RECU).</summary>
    public string GenererNumeroRecu()
    {
        var prefixe = $"REC-{DateTime.Today.Year}-";
        var existants = new HashSet<string>(_finances.ListRecus(prefixe), StringComparer.OrdinalIgnoreCase);
        var sequence = 0;
        foreach (var recu in existants)
        {
            var suffixe = recu.Substring(prefixe.Length);
            if (int.TryParse(suffixe, out var numero) && numero > sequence)
                sequence = numero;
        }
        string candidat;
        do
        {
            sequence++;
            candidat = prefixe + sequence.ToString("D6");
        } while (existants.Contains(candidat));
        return candidat;
    }
}
