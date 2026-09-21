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
/// Saisie et suivi des notes de contrôle continu.
/// Règles : note entre 0 et barème (sauf absent), période non clôturée,
/// étudiant inscrit dans la classe de l'évaluation, unicité (évaluation, inscrit).
/// </summary>
public sealed class GradeService : ServiceBase
{
    private readonly EvaluationRepository _evaluations;
    private readonly EnrollmentRepository _inscriptions;

    public GradeService(AccessDatabase database, AppLogger logger, JournalService journal, ParametreService parametres)
        : base(database, logger, journal, parametres)
    {
        _evaluations = new EvaluationRepository(database);
        _inscriptions = new EnrollmentRepository(database);
    }

    public List<NoteSaisieRow> GetGrilleSaisie(int idEvaluation)
    {
        try
        {
            var evaluation = _evaluations.GetEvaluationDetail(idEvaluation);
            if (evaluation?.IdClasse is null) return new List<NoteSaisieRow>();
            return _evaluations.ListGrilleSaisie(idEvaluation, evaluation.IdClasse.Value);
        }
        catch (Exception ex)
        {
            Logger.Error("Chargement de la grille de saisie", ex);
            return new List<NoteSaisieRow>();
        }
    }

    /// <summary>Enregistre (insertion ou mise à jour) la note d'un inscrit.</summary>
    public Result UpsertNote(int idEvaluation, int idInscription, double? valeur, bool absent, string? observation, string codeUtr)
    {
        try
        {
            var evaluation = _evaluations.GetEvaluationDetail(idEvaluation);
            if (evaluation is null)
                return Result.Fail("Évaluation introuvable.", ErrorCodes.NotFound);
            if (evaluation.PeriodeCloturee == true)
                return Result.Fail("Période clôturée : les notes sont figées.", ErrorCodes.BusinessRule);
            if (string.IsNullOrWhiteSpace(observation)) observation = null;
            else if (observation.Length > 300)
                return Result.Fail("Observation : 300 caractères maximum.", ErrorCodes.Validation);

            var bareme = evaluation.Bareme ?? Parametres.BaremeDefaut;
            var validation = GradeValidator.ValidateNote(valeur, absent, bareme);
            if (!validation.IsValid) return Invalid(validation);

            var inscription = _inscriptions.GetById(idInscription);
            if (inscription is null)
                return Result.Fail("Inscription introuvable.", ErrorCodes.NotFound);
            if (inscription.IdClasse != evaluation.IdClasse)
                return Result.Fail("Cet étudiant n’est pas inscrit dans la classe de cette évaluation.", ErrorCodes.BusinessRule);

            var existing = _evaluations.GetNote(idEvaluation, idInscription);
            if (existing is null)
            {
                var id = _evaluations.InsertNote(new Note
                {
                    IdEvaluation = idEvaluation,
                    IdInscription = idInscription,
                    ValeurNote = absent ? null : valeur,
                    Absent = absent,
                    Observation = observation,
                    DateSaisie = DateTime.Now,
                    CodeUtr = codeUtr
                });
                Journal.LogCreation(codeUtr, Tables.Note, id, $"Éval {idEvaluation} / inscrit {idInscription}");
            }
            else
            {
                existing.ValeurNote = absent ? null : valeur;
                existing.Absent = absent;
                existing.Observation = observation;
                existing.DateSaisie = DateTime.Now;
                existing.CodeUtr = codeUtr;
                _evaluations.UpdateNote(existing);
                Journal.LogModification(codeUtr, Tables.Note, existing.IdNote, $"Éval {idEvaluation} / inscrit {idInscription}");
            }
            return Result.Ok("Note enregistrée.");
        }
        catch (Exception ex) { return Failure("Saisie d’une note", ex); }
    }

    public Result DeleteNote(int idNote, string codeUtr)
    {
        try
        {
            _evaluations.DeleteNote(idNote);
            Journal.LogSuppression(codeUtr, Tables.Note, idNote);
            return Result.Ok("Note supprimée.");
        }
        catch (Exception ex) { return Failure("Suppression d’une note", ex); }
    }

    public List<MoyenneMatiereRow> GetMoyennesMatiere(int? idClasse = null, int? idPeriode = null)
    {
        try { return _evaluations.ListMoyennesMatiere(idClasse, idPeriode); }
        catch (Exception ex)
        {
            Logger.Error("Lecture des moyennes par matière", ex);
            return new List<MoyenneMatiereRow>();
        }
    }

    public List<MoyennePeriodeRow> GetMoyennesPeriode(int? idClasse = null, int? idPeriode = null)
    {
        try { return _evaluations.ListMoyennesPeriode(idClasse, idPeriode); }
        catch (Exception ex)
        {
            Logger.Error("Lecture des moyennes par période", ex);
            return new List<MoyennePeriodeRow>();
        }
    }
}
