using LTAdmin.Core;
using LTAdmin.Data;
using LTAdmin.Models.Entities;
using LTAdmin.Repositories;
using LTAdmin.Services.Common;
using LTAdmin.Services.Logging;
using LTAdmin.Services.Referentiel;
using LTAdmin.Services.Validation;

namespace LTAdmin.Services.Business;

/// <summary>
/// Paie des formateurs : heures réalisées (séances) × taux horaire.
/// Réimplémentation C# de CALCUL_PAIE_FORMATEUR : les heures sont sommées
/// depuis SEANCE via EMPLOI_DU_TEMPS → PROGRAMME. Une paie marquée PAYE
/// ne peut plus être recalculée ni supprimée.
/// </summary>
public sealed class PayrollService : ServiceBase
{
    private readonly FinanceRepository _finances;
    private readonly StaffRepository _personnel;
    private readonly PlanningRepository _planning;

    public PayrollService(AccessDatabase database, AppLogger logger, JournalService journal, ParametreService parametres)
        : base(database, logger, journal, parametres)
    {
        _finances = new FinanceRepository(database);
        _personnel = new StaffRepository(database);
        _planning = new PlanningRepository(database);
    }

    public List<PaieFormateur> ListByFormateur(int idFormateur)
    {
        try { return _finances.ListPaiesByFormateur(idFormateur); }
        catch (Exception ex)
        {
            Logger.Error("Paies d’un formateur", ex);
            return new List<PaieFormateur>();
        }
    }

    /// <summary>Calcule (ou recalcule si non payée) la paie d'un formateur sur une période.</summary>
    public Result<int> CalculerPaie(int idFormateur, DateTime debut, DateTime fin, string codeUtr, string? observation = null)
    {
        var validation = PayrollValidator.ValidateCalcul(idFormateur, debut, fin);
        if (!validation.IsValid) return Invalid<int>(validation);
        try
        {
            var formateur = _personnel.GetFormateur(idFormateur);
            if (formateur is null)
                return Result<int>.Fail("Formateur introuvable.", ErrorCodes.NotFound);
            if (!formateur.TauxHoraire.HasValue || formateur.TauxHoraire.Value <= 0)
                return Result<int>.Fail(
                    $"Taux horaire non renseigné pour « {formateur.NomComplet} » : complétez sa fiche avant le calcul.",
                    ErrorCodes.BusinessRule);

            var periode = LibellePeriode(debut, fin);
            var existante = _finances.GetPaieByFormateurPeriode(idFormateur, periode);
            if (existante?.Paye == true)
                return Result<int>.Fail($"La paie « {periode} » est déjà marquée payée : calcul figé.",
                    ErrorCodes.BusinessRule);

            var heures = _planning.SumHeuresFormateur(idFormateur, debut, fin);
            var taux = formateur.TauxHoraire.Value;
            var montant = Math.Round((decimal)heures * taux, 2);

            if (existante is null)
            {
                var id = _finances.InsertPaie(new PaieFormateur
                {
                    IdFormateur = idFormateur,
                    Periode = periode,
                    NbHeures = heures,
                    Taux = taux,
                    Montant = montant,
                    Paye = false,
                    Observation = observation
                });
                Journal.LogCreation(codeUtr, Tables.PaieFormateur, id,
                    $"{formateur.NomComplet} — {periode} : {heures:N1} h × {taux:N0} = {montant:N0} {Parametres.Devise}");
                return Result<int>.Ok(id, $"Paie calculée : {montant:N0} {Parametres.Devise} ({heures:N1} h).");
            }

            existante.NbHeures = heures;
            existante.Taux = taux;
            existante.Montant = montant;
            existante.Observation = observation;
            _finances.UpdatePaie(existante);
            Journal.LogModification(codeUtr, Tables.PaieFormateur, existante.IdPaie,
                $"{formateur.NomComplet} — {periode} : {heures:N1} h × {taux:N0} = {montant:N0} {Parametres.Devise}");
            return Result<int>.Ok(existante.IdPaie ?? 0, $"Paie recalculée : {montant:N0} {Parametres.Devise} ({heures:N1} h).");
        }
        catch (Exception ex) { return Failure<int>("Calcul de la paie", ex); }
    }

    public Result MarquerPayee(int idPaie, bool payee, string codeUtr, DateTime? datePaie = null)
    {
        try
        {
            var paie = _finances.GetPaie(idPaie);
            if (paie is null)
                return Result.Fail("Paie introuvable.", ErrorCodes.NotFound);
            _finances.SetPaiePayee(idPaie, payee, payee ? (datePaie ?? DateTime.Today) : null);
            Journal.LogOperation(codeUtr, payee ? "PAIE_PAYEE" : "PAIE_IMPAYEE",
                Tables.PaieFormateur, idPaie, paie.Periode);
            return Result.Ok(payee ? "Paie marquée payée." : "Marquage « payée » retiré.");
        }
        catch (Exception ex) { return Failure("Marquage d’une paie", ex); }
    }

    public Result Delete(int idPaie, string codeUtr)
    {
        try
        {
            var paie = _finances.GetPaie(idPaie);
            if (paie is null)
                return Result.Fail("Paie introuvable.", ErrorCodes.NotFound);
            if (paie.Paye == true)
                return Result.Fail("Paie déjà payée : suppression interdite.", ErrorCodes.BusinessRule);
            _finances.DeletePaie(idPaie);
            Journal.LogSuppression(codeUtr, Tables.PaieFormateur, idPaie, paie.Periode);
            return Result.Ok("Paie supprimée.");
        }
        catch (Exception ex) { return Failure("Suppression d’une paie", ex); }
    }

    private static string LibellePeriode(DateTime debut, DateTime fin)
    {
        if (debut.Year == fin.Year && debut.Month == fin.Month)
            return debut.ToString("MM/yyyy");
        return $"{debut:dd/MM/yyyy} - {fin:dd/MM/yyyy}";
    }
}
