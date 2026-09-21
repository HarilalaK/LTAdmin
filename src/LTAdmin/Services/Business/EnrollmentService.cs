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
/// Gestion des inscriptions : une ligne par étudiant et par classe
/// (historique + redoublements), contrôle de l'effectif maximum.
/// </summary>
public sealed class EnrollmentService : ServiceBase
{
    private readonly EnrollmentRepository _inscriptions;
    private readonly StudentRepository _etudiants;
    private readonly ReferentielRepository _referentiel;

    public EnrollmentService(AccessDatabase database, AppLogger logger, JournalService journal, ParametreService parametres)
        : base(database, logger, journal, parametres)
    {
        _inscriptions = new EnrollmentRepository(database);
        _etudiants = new StudentRepository(database);
        _referentiel = new ReferentielRepository(database);
    }

    public List<InscriptionDetail> ListByClasse(int idClasse)
    {
        try { return _inscriptions.ListByClasse(idClasse); }
        catch (Exception ex)
        {
            Logger.Error("Liste des inscrits d’une classe", ex);
            return new List<InscriptionDetail>();
        }
    }

    public List<InscriptionDetail> ListByEtudiant(int idEtudiant)
    {
        try { return _inscriptions.ListByEtudiant(idEtudiant); }
        catch (Exception ex)
        {
            Logger.Error("Historique des inscriptions d’un étudiant", ex);
            return new List<InscriptionDetail>();
        }
    }

    public InscriptionDetail? GetDetail(int idInscription)
    {
        try { return _inscriptions.GetDetail(idInscription); }
        catch (Exception ex)
        {
            Logger.Error("Lecture d’une inscription", ex);
            return null;
        }
    }

    public Inscription? Get(int idInscription)
    {
        try { return _inscriptions.GetById(idInscription); }
        catch (Exception ex)
        {
            Logger.Error("Lecture d’une inscription", ex);
            return null;
        }
    }

    /// <summary>Inscrit un étudiant dans une classe (contrôles : doublon, effectif max).</summary>
    public Result<int> Inscrire(Inscription inscription, string codeUtr)
    {
        var validation = EnrollmentValidator.Validate(inscription);
        if (!validation.IsValid) return Invalid<int>(validation);

        try
        {
            var etudiant = _etudiants.GetById(inscription.IdEtudiant!.Value);
            if (etudiant is null)
                return Result<int>.Fail("Étudiant introuvable.", ErrorCodes.NotFound);
            var classe = _referentiel.GetClasse(inscription.IdClasse!.Value);
            if (classe is null)
                return Result<int>.Fail("Classe introuvable.", ErrorCodes.NotFound);

            var doublon = _inscriptions.GetByEtudiantClasse(inscription.IdEtudiant.Value, inscription.IdClasse.Value);
            if (doublon is not null)
                return Result<int>.Fail($"« {etudiant.NomComplet} » est déjà inscrit dans la classe « {classe.Libelle} ».",
                    ErrorCodes.UniqueViolation);

            if (classe.EffectifMax.HasValue && classe.EffectifMax.Value > 0)
            {
                var effectif = _inscriptions.CountByClasse(classe.IdClasse!.Value);
                if (effectif >= classe.EffectifMax.Value)
                    return Result<int>.Fail(
                        $"Effectif maximum atteint pour « {classe.Libelle} » ({effectif}/{classe.EffectifMax}).",
                        ErrorCodes.BusinessRule);
            }

            if (string.IsNullOrWhiteSpace(inscription.NumInscription))
                inscription.NumInscription = GenererNumero();
            if (!inscription.DateInscription.HasValue)
                inscription.DateInscription = DateTime.Today;
            if (string.IsNullOrWhiteSpace(inscription.Statut))
                inscription.Statut = "INSCRIT";

            var id = _inscriptions.Insert(inscription);
            Journal.LogCreation(codeUtr, Tables.Inscription, id,
                $"{inscription.NumInscription} — {etudiant.NomComplet} → {classe.Libelle}");
            return Result<int>.Ok(id, $"Inscription {inscription.NumInscription} enregistrée.");
        }
        catch (Exception ex)
        {
            if (OleDbExceptionHelper.IsUniqueViolation(ex))
                return Result<int>.Fail("Cette inscription existe déjà (doublon étudiant × classe).",
                    ErrorCodes.UniqueViolation);
            return Failure<int>("Inscription d’un étudiant", ex);
        }
    }

    public Result Update(Inscription inscription, string codeUtr)
    {
        if (!inscription.IdInscription.HasValue)
            return Result.Fail("Inscription introuvable.", ErrorCodes.NotFound);
        var validation = EnrollmentValidator.Validate(inscription);
        if (!validation.IsValid) return Invalid(validation);

        try
        {
            var updated = _inscriptions.Update(inscription);
            if (updated == 0)
                return Result.Fail("Inscription introuvable : elle a peut-être été supprimée.", ErrorCodes.NotFound);
            Journal.LogModification(codeUtr, Tables.Inscription, inscription.IdInscription,
                inscription.NumInscription);
            return Result.Ok("Inscription enregistrée.");
        }
        catch (Exception ex)
        {
            if (OleDbExceptionHelper.IsUniqueViolation(ex))
                return Result.Fail("Cette inscription existe déjà (doublon étudiant × classe).",
                    ErrorCodes.UniqueViolation);
            return Failure("Modification d’une inscription", ex);
        }
    }

    /// <summary>Enregistre une sortie (date + motif) sans supprimer l'historique.</summary>
    public Result EnregistrerSortie(int idInscription, DateTime dateSortie, string? motif, string codeUtr)
    {
        try
        {
            var inscription = _inscriptions.GetById(idInscription);
            if (inscription is null)
                return Result.Fail("Inscription introuvable.", ErrorCodes.NotFound);
            inscription.DateSortie = dateSortie;
            inscription.MotifSortie = motif;
            inscription.Statut = "SORTI";
            var validation = EnrollmentValidator.Validate(inscription);
            if (!validation.IsValid) return Invalid(validation);
            _inscriptions.Update(inscription);
            Journal.LogModification(codeUtr, Tables.Inscription, idInscription, "Sortie enregistrée.");
            return Result.Ok("Sortie enregistrée.");
        }
        catch (Exception ex) { return Failure("Enregistrement d’une sortie", ex); }
    }

    public Result Delete(int idInscription, string codeUtr)
    {
        try
        {
            var existing = _inscriptions.GetById(idInscription);
            if (existing is null)
                return Result.Fail("Inscription introuvable.", ErrorCodes.NotFound);
            _inscriptions.Delete(idInscription);
            Journal.LogSuppression(codeUtr, Tables.Inscription, idInscription, existing.NumInscription);
            return Result.Ok("Inscription supprimée.");
        }
        catch (Exception ex)
        {
            if (OleDbExceptionHelper.IsForeignKeyViolation(ex))
                return Result.Fail("Suppression impossible : cette inscription possède des notes, absences, bulletins ou paiements.",
                    ErrorCodes.ForeignKeyViolation);
            return Failure("Suppression d’une inscription", ex);
        }
    }

    /// <summary>Génère un numéro d'inscription unique INS-AAAA-####.</summary>
    public string GenererNumero()
    {
        var prefixe = $"INS-{DateTime.Today.Year}-";
        var existants = new HashSet<string>(_inscriptions.ListNumeros(prefixe), StringComparer.OrdinalIgnoreCase);
        var sequence = 0;
        foreach (var numero in existants)
        {
            var suffixe = numero.Substring(prefixe.Length);
            if (int.TryParse(suffixe, out var value) && value > sequence)
                sequence = value;
        }
        string candidat;
        do
        {
            sequence++;
            candidat = prefixe + sequence.ToString("D4");
        } while (existants.Contains(candidat));
        return candidat;
    }
}
