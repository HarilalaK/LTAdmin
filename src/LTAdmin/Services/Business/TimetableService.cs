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
/// Emplois du temps et séances (cahier de texte).
/// Réimplémentation C# d'EDT_CONFLIT : refus de la double réservation de la
/// salle et du formateur sur (jour, créneau) parmi les slots actifs.
/// </summary>
public sealed class TimetableService : ServiceBase
{
    private readonly PlanningRepository _planning;
    private readonly StaffRepository _personnel;
    private readonly ReferentielRepository _referentiel;

    public TimetableService(AccessDatabase database, AppLogger logger, JournalService journal, ParametreService parametres)
        : base(database, logger, journal, parametres)
    {
        _planning = new PlanningRepository(database);
        _personnel = new StaffRepository(database);
        _referentiel = new ReferentielRepository(database);
    }

    public List<Creneau> ListCreneaux()
    {
        try { return _planning.ListCreneaux(); }
        catch (Exception ex)
        {
            Logger.Error("Liste des créneaux", ex);
            return new List<Creneau>();
        }
    }

    public List<EdtSlotDetail> GetGrilleClasse(int idClasse, bool actifsSeulement = true)
    {
        try { return _planning.ListSlotsByClasse(idClasse, actifsSeulement); }
        catch (Exception ex)
        {
            Logger.Error("Grille d’emploi du temps", ex);
            return new List<EdtSlotDetail>();
        }
    }

    /// <summary>
    /// Détecte un conflit salle / formateur pour un slot (équivalent EDT_CONFLIT).
    /// Retourne la description du conflit, ou null si le slot est libre.
    /// </summary>
    public string? DetecterConflit(string jour, int idCreneau, int? idSalle, int idProg, int? excludeIdEdt = null)
    {
        try
        {
            var programme = _personnel.GetProgramme(idProg);
            if (programme is null) return "Programme (classe × matière) introuvable.";
            var concurrents = _planning.ListSlotsConcurrents(jour, idCreneau, excludeIdEdt);
            foreach (var slot in concurrents)
            {
                if (idSalle.HasValue && slot.IdSalle.HasValue && slot.IdSalle.Value == idSalle.Value)
                    return $"La salle « {slot.Salle ?? idSalle.ToString()} » est déjà occupée {jour} " +
                           $"sur ce créneau par « {slot.Classe} — {slot.Matiere} ».";
                if (programme.IdFormateur.HasValue && slot.IdFormateur.HasValue
                    && slot.IdFormateur.Value == programme.IdFormateur.Value)
                    return $"Le formateur « {slot.Formateur} » est déjà en cours {jour} " +
                           $"sur ce créneau (« {slot.Classe} — {slot.Matiere} »).";
            }
            return null;
        }
        catch (Exception ex)
        {
            Logger.Error("Détection de conflit d’emploi du temps", ex);
            return "Conflit potentiel (vérification technique impossible) : " + ex.Message;
        }
    }

    public Result<int> CreateSlot(EmploiDuTemps slot, string codeUtr)
    {
        var validation = PlanningValidator.ValidateSlot(slot);
        if (!validation.IsValid) return Invalid<int>(validation);
        try
        {
            var programme = _personnel.GetProgramme(slot.IdProg!.Value);
            if (programme is null)
                return Result<int>.Fail("Programme (classe × matière) introuvable.", ErrorCodes.NotFound);
            var creneau = _planning.GetCreneau(slot.IdCreneau!.Value);
            if (creneau is null)
                return Result<int>.Fail("Créneau introuvable.", ErrorCodes.NotFound);
            if (slot.IdSalle.HasValue)
            {
                var salle = _referentiel.GetSalle(slot.IdSalle.Value);
                if (salle is null)
                    return Result<int>.Fail("Salle introuvable.", ErrorCodes.NotFound);
                if (salle.Disponible == false)
                    return Result<int>.Fail($"La salle « {salle.NomSalle} » est marquée indisponible.", ErrorCodes.BusinessRule);
            }
            var conflit = DetecterConflit(slot.Jour!, slot.IdCreneau.Value, slot.IdSalle, slot.IdProg.Value);
            if (conflit is not null)
                return Result<int>.Fail(conflit, ErrorCodes.BusinessRule);

            var id = _planning.InsertSlot(slot);
            Journal.LogCreation(codeUtr, Tables.EmploiDuTemps, id, $"{slot.Jour} — prog {slot.IdProg}");
            return Result<int>.Ok(id, "Créneau d’emploi du temps créé.");
        }
        catch (Exception ex) { return Failure<int>("Création d’un créneau", ex); }
    }

    public Result UpdateSlot(EmploiDuTemps slot, string codeUtr)
    {
        if (!slot.IdEdt.HasValue)
            return Result.Fail("Créneau introuvable.", ErrorCodes.NotFound);
        var validation = PlanningValidator.ValidateSlot(slot);
        if (!validation.IsValid) return Invalid(validation);
        try
        {
            var conflit = DetecterConflit(slot.Jour!, slot.IdCreneau!.Value, slot.IdSalle, slot.IdProg!.Value, slot.IdEdt);
            if (conflit is not null)
                return Result.Fail(conflit, ErrorCodes.BusinessRule);
            var updated = _planning.UpdateSlot(slot);
            if (updated == 0)
                return Result.Fail("Créneau introuvable.", ErrorCodes.NotFound);
            Journal.LogModification(codeUtr, Tables.EmploiDuTemps, slot.IdEdt, slot.Jour);
            return Result.Ok("Créneau enregistré.");
        }
        catch (Exception ex) { return Failure("Modification d’un créneau", ex); }
    }

    public Result SetSlotActif(int idEdt, bool actif, string codeUtr)
    {
        try
        {
            _planning.SetSlotActif(idEdt, actif);
            Journal.LogOperation(codeUtr, actif ? "ACTIVATION_EDT" : "DESACTIVATION_EDT",
                Tables.EmploiDuTemps, idEdt);
            return Result.Ok(actif ? "Créneau activé." : "Créneau désactivé.");
        }
        catch (Exception ex) { return Failure("Activation d’un créneau", ex); }
    }

    public Result DeleteSlot(int idEdt, string codeUtr)
    {
        try
        {
            var existing = _planning.GetSlot(idEdt);
            if (existing is null)
                return Result.Fail("Créneau introuvable.", ErrorCodes.NotFound);
            _planning.DeleteSlot(idEdt);
            Journal.LogSuppression(codeUtr, Tables.EmploiDuTemps, idEdt, existing.Jour);
            return Result.Ok("Créneau supprimé.");
        }
        catch (Exception ex)
        {
            if (OleDbExceptionHelper.IsForeignKeyViolation(ex))
                return Result.Fail("Suppression impossible : des séances sont rattachées à ce créneau.",
                    ErrorCodes.ForeignKeyViolation);
            return Failure("Suppression d’un créneau", ex);
        }
    }

    public List<SeanceDetail> ListSeances(DateTime? debut, DateTime? fin, int? idClasse = null)
    {
        try { return _planning.ListSeances(debut, fin, idClasse); }
        catch (Exception ex)
        {
            Logger.Error("Liste des séances", ex);
            return new List<SeanceDetail>();
        }
    }

    public Result<int> CreateSeance(Seance seance, string codeUtr)
    {
        var validation = PlanningValidator.ValidateSeance(seance);
        if (!validation.IsValid) return Invalid<int>(validation);
        try
        {
            var slot = _planning.GetSlot(seance.IdEdt!.Value);
            if (slot is null)
                return Result<int>.Fail("Créneau d’emploi du temps introuvable.", ErrorCodes.NotFound);
            var id = _planning.InsertSeance(seance);
            Journal.LogCreation(codeUtr, Tables.Seance, id,
                seance.DateSeance?.ToString("dd/MM/yyyy"));
            return Result<int>.Ok(id, "Séance enregistrée au cahier de texte.");
        }
        catch (Exception ex) { return Failure<int>("Création d’une séance", ex); }
    }

    public Result UpdateSeance(Seance seance, string codeUtr)
    {
        if (!seance.IdSeance.HasValue)
            return Result.Fail("Séance introuvable.", ErrorCodes.NotFound);
        var validation = PlanningValidator.ValidateSeance(seance);
        if (!validation.IsValid) return Invalid(validation);
        try
        {
            var updated = _planning.UpdateSeance(seance);
            if (updated == 0)
                return Result.Fail("Séance introuvable.", ErrorCodes.NotFound);
            Journal.LogModification(codeUtr, Tables.Seance, seance.IdSeance);
            return Result.Ok("Séance enregistrée.");
        }
        catch (Exception ex) { return Failure("Modification d’une séance", ex); }
    }
}
