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
/// Gestion des périodes d'évaluation et des évaluations (devoirs, interros).
/// Règles : barème et poids strictement positifs, période clôturée figée.
/// </summary>
public sealed class EvaluationService : ServiceBase
{
    private readonly EvaluationRepository _evaluations;
    private readonly StaffRepository _personnel;

    public EvaluationService(AccessDatabase database, AppLogger logger, JournalService journal, ParametreService parametres)
        : base(database, logger, journal, parametres)
    {
        _evaluations = new EvaluationRepository(database);
        _personnel = new StaffRepository(database);
    }

    public List<PeriodeEval> ListPeriodes(int? idAnnee = null)
    {
        try { return _evaluations.ListPeriodes(idAnnee); }
        catch (Exception ex)
        {
            Logger.Error("Liste des périodes d’évaluation", ex);
            return new List<PeriodeEval>();
        }
    }

    public PeriodeEval? GetPeriode(int idPeriode)
    {
        try { return _evaluations.GetPeriode(idPeriode); }
        catch (Exception ex)
        {
            Logger.Error("Lecture d’une période", ex);
            return null;
        }
    }

    public Result<int> CreatePeriode(PeriodeEval periode, string codeUtr)
    {
        var validation = EvaluationValidator.ValidatePeriode(periode);
        if (!validation.IsValid) return Invalid<int>(validation);
        try
        {
            var id = _evaluations.InsertPeriode(periode);
            Journal.LogCreation(codeUtr, Tables.PeriodeEval, id, periode.Libelle);
            return Result<int>.Ok(id, "Période d’évaluation créée.");
        }
        catch (Exception ex) { return Failure<int>("Création d’une période", ex); }
    }

    public Result UpdatePeriode(PeriodeEval periode, string codeUtr)
    {
        if (!periode.IdPeriode.HasValue)
            return Result.Fail("Période introuvable.", ErrorCodes.NotFound);
        var validation = EvaluationValidator.ValidatePeriode(periode);
        if (!validation.IsValid) return Invalid(validation);
        try
        {
            var updated = _evaluations.UpdatePeriode(periode);
            if (updated == 0)
                return Result.Fail("Période introuvable.", ErrorCodes.NotFound);
            Journal.LogModification(codeUtr, Tables.PeriodeEval, periode.IdPeriode, periode.Libelle);
            return Result.Ok("Période enregistrée.");
        }
        catch (Exception ex) { return Failure("Modification d’une période", ex); }
    }

    /// <summary>Clôture (ou rouvre) une période : les notes figées ne sont plus modifiables.</summary>
    public Result SetPeriodeCloturee(int idPeriode, bool cloturee, string codeUtr)
    {
        try
        {
            var periode = _evaluations.GetPeriode(idPeriode);
            if (periode is null)
                return Result.Fail("Période introuvable.", ErrorCodes.NotFound);
            _evaluations.SetPeriodeCloturee(idPeriode, cloturee);
            Journal.LogOperation(codeUtr, cloturee ? "CLOTURE_PERIODE" : "REOUVERTURE_PERIODE",
                Tables.PeriodeEval, idPeriode, periode.Libelle);
            return Result.Ok(cloturee ? "Période clôturée : les notes sont figées." : "Période rouverte.");
        }
        catch (Exception ex) { return Failure("Clôture d’une période", ex); }
    }

    public List<EvaluationDetail> ListEvaluations(int? idPeriode = null, int? idClasse = null, int? idProg = null)
    {
        try { return _evaluations.ListEvaluations(idPeriode, idClasse, idProg); }
        catch (Exception ex)
        {
            Logger.Error("Liste des évaluations", ex);
            return new List<EvaluationDetail>();
        }
    }

    public EvaluationDetail? GetEvaluationDetail(int idEvaluation)
    {
        try { return _evaluations.GetEvaluationDetail(idEvaluation); }
        catch (Exception ex)
        {
            Logger.Error("Lecture d’une évaluation", ex);
            return null;
        }
    }

    public Result<int> CreateEvaluation(Evaluation evaluation, string codeUtr)
    {
        if (!evaluation.Bareme.HasValue || evaluation.Bareme.Value <= 0)
            evaluation.Bareme = Parametres.BaremeDefaut;
        if (!evaluation.Poids.HasValue || evaluation.Poids.Value <= 0)
            evaluation.Poids = 1d;
        var validation = EvaluationValidator.ValidateEvaluation(evaluation);
        if (!validation.IsValid) return Invalid<int>(validation);

        try
        {
            var periode = _evaluations.GetPeriode(evaluation.IdPeriode!.Value);
            if (periode is null)
                return Result<int>.Fail("Période introuvable.", ErrorCodes.NotFound);
            if (periode.Cloturee == true)
                return Result<int>.Fail("Période clôturée : rouvrez-la pour ajouter une évaluation.", ErrorCodes.BusinessRule);
            var programme = _personnel.GetProgramme(evaluation.IdProg!.Value);
            if (programme is null)
                return Result<int>.Fail("Programme (classe × matière) introuvable.", ErrorCodes.NotFound);

            var id = _evaluations.InsertEvaluation(evaluation);
            Journal.LogCreation(codeUtr, Tables.Evaluation, id, evaluation.Intitule);
            return Result<int>.Ok(id, "Évaluation créée.");
        }
        catch (Exception ex) { return Failure<int>("Création d’une évaluation", ex); }
    }

    public Result UpdateEvaluation(Evaluation evaluation, string codeUtr)
    {
        if (!evaluation.IdEvaluation.HasValue)
            return Result.Fail("Évaluation introuvable.", ErrorCodes.NotFound);
        var validation = EvaluationValidator.ValidateEvaluation(evaluation);
        if (!validation.IsValid) return Invalid(validation);

        try
        {
            var periode = _evaluations.GetPeriode(evaluation.IdPeriode!.Value);
            if (periode?.Cloturee == true)
                return Result.Fail("Période clôturée : rouvrez-la pour modifier cette évaluation.", ErrorCodes.BusinessRule);
            var updated = _evaluations.UpdateEvaluation(evaluation);
            if (updated == 0)
                return Result.Fail("Évaluation introuvable.", ErrorCodes.NotFound);
            Journal.LogModification(codeUtr, Tables.Evaluation, evaluation.IdEvaluation, evaluation.Intitule);
            return Result.Ok("Évaluation enregistrée.");
        }
        catch (Exception ex) { return Failure("Modification d’une évaluation", ex); }
    }

    public Result SetPubliee(int idEvaluation, bool publiee, string codeUtr)
    {
        try
        {
            var existing = _evaluations.GetEvaluation(idEvaluation);
            if (existing is null)
                return Result.Fail("Évaluation introuvable.", ErrorCodes.NotFound);
            _evaluations.SetEvaluationPubliee(idEvaluation, publiee);
            Journal.LogOperation(codeUtr, publiee ? "PUBLICATION_NOTES" : "DEPUBLICATION_NOTES",
                Tables.Evaluation, idEvaluation, existing.Intitule);
            return Result.Ok(publiee ? "Notes publiées." : "Publication retirée.");
        }
        catch (Exception ex) { return Failure("Publication d’une évaluation", ex); }
    }

    public Result DeleteEvaluation(int idEvaluation, string codeUtr)
    {
        try
        {
            var existing = _evaluations.GetEvaluation(idEvaluation);
            if (existing is null)
                return Result.Fail("Évaluation introuvable.", ErrorCodes.NotFound);
            _evaluations.DeleteEvaluation(idEvaluation);
            Journal.LogSuppression(codeUtr, Tables.Evaluation, idEvaluation, existing.Intitule);
            return Result.Ok("Évaluation supprimée.");
        }
        catch (Exception ex)
        {
            if (OleDbExceptionHelper.IsForeignKeyViolation(ex))
                return Result.Fail("Suppression impossible : des notes sont déjà saisies pour cette évaluation.",
                    ErrorCodes.ForeignKeyViolation);
            return Failure("Suppression d’une évaluation", ex);
        }
    }
}
