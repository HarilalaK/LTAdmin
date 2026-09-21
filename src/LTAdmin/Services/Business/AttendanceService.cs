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
/// Appel et absences : saisie depuis une séance, cumuls par étudiant,
/// alerte au-delà du SEUIL_ABSENCE (exclusion d'examen).
/// </summary>
public sealed class AttendanceService : ServiceBase
{
    private readonly PlanningRepository _planning;
    private readonly EnrollmentRepository _inscriptions;

    public AttendanceService(AccessDatabase database, AppLogger logger, JournalService journal, ParametreService parametres)
        : base(database, logger, journal, parametres)
    {
        _planning = new PlanningRepository(database);
        _inscriptions = new EnrollmentRepository(database);
    }

    public List<Absence> ListBySeance(int idSeance)
    {
        try { return _planning.ListAbsencesBySeance(idSeance); }
        catch (Exception ex)
        {
            Logger.Error("Absences d’une séance", ex);
            return new List<Absence>();
        }
    }

    public List<Absence> ListByInscription(int idInscription)
    {
        try { return _planning.ListAbsencesByInscription(idInscription); }
        catch (Exception ex)
        {
            Logger.Error("Absences d’un inscrit", ex);
            return new List<Absence>();
        }
    }

    /// <summary>Enregistre une absence (ou un retard) pour un inscrit à une séance.</summary>
    public Result<int> MarquerAbsence(Absence absence, string codeUtr)
    {
        var validation = PlanningValidator.ValidateAbsence(absence);
        if (!validation.IsValid) return Invalid<int>(validation);
        try
        {
            var seance = _planning.GetSeance(absence.IdSeance!.Value);
            if (seance is null)
                return Result<int>.Fail("Séance introuvable.", ErrorCodes.NotFound);
            var inscription = _inscriptions.GetById(absence.IdInscription!.Value);
            if (inscription is null)
                return Result<int>.Fail("Inscription introuvable.", ErrorCodes.NotFound);

            var id = _planning.InsertAbsence(absence);
            Journal.LogCreation(codeUtr, Tables.Absence, id,
                $"Séance {absence.IdSeance} / inscrit {absence.IdInscription} : {absence.NbHeures} h");

            var total = _planning.SumHeuresAbsence(absence.IdInscription.Value);
            var seuil = Parametres.SeuilAbsence;
            if (total >= seuil)
                return Result<int>.Ok(id,
                    $"Absence enregistrée. Attention : {total:N1} h cumulées (seuil d’exclusion : {seuil:N0} h).");
            return Result<int>.Ok(id, "Absence enregistrée.");
        }
        catch (Exception ex) { return Failure<int>("Saisie d’une absence", ex); }
    }

    public Result Justifier(int idAbsence, bool justifiee, string? motif, string codeUtr)
    {
        try
        {
            var absence = _planning.GetAbsence(idAbsence);
            if (absence is null)
                return Result.Fail("Absence introuvable.", ErrorCodes.NotFound);
            absence.Justifiee = justifiee;
            if (!string.IsNullOrWhiteSpace(motif))
            {
                if (motif.Length > 300)
                    return Result.Fail("Motif : 300 caractères maximum.", ErrorCodes.Validation);
                absence.Motif = motif;
            }
            _planning.UpdateAbsence(absence);
            Journal.LogModification(codeUtr, Tables.Absence, idAbsence,
                justifiee ? "Absence justifiée." : "Justification retirée.");
            return Result.Ok(justifiee ? "Absence justifiée." : "Justification retirée.");
        }
        catch (Exception ex) { return Failure("Justification d’une absence", ex); }
    }

    public Result Delete(int idAbsence, string codeUtr)
    {
        try
        {
            var existing = _planning.GetAbsence(idAbsence);
            if (existing is null)
                return Result.Fail("Absence introuvable.", ErrorCodes.NotFound);
            _planning.DeleteAbsence(idAbsence);
            Journal.LogSuppression(codeUtr, Tables.Absence, idAbsence);
            return Result.Ok("Absence supprimée.");
        }
        catch (Exception ex) { return Failure("Suppression d’une absence", ex); }
    }

    /// <summary>Cumul des heures d'absence d'un inscrit (toutes séances).</summary>
    public double TotalHeures(int idInscription)
    {
        try { return _planning.SumHeuresAbsence(idInscription); }
        catch (Exception ex)
        {
            Logger.Error("Cumul des absences", ex);
            return 0d;
        }
    }
}
