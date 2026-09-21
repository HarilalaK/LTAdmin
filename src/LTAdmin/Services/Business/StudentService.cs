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
/// Gestion des dossiers étudiants : recherche, création (matricule auto),
/// modification, suppression. Équivalent applicatif de NOUVEAU_MATRICULE().
/// </summary>
public sealed class StudentService : ServiceBase
{
    private readonly StudentRepository _etudiants;

    public StudentService(AccessDatabase database, AppLogger logger, JournalService journal, ParametreService parametres)
        : base(database, logger, journal, parametres)
    {
        _etudiants = new StudentRepository(database);
    }

    public List<Etudiant> Search(string? recherche, int maxRows = 500)
    {
        try { return _etudiants.Search(recherche, maxRows); }
        catch (Exception ex)
        {
            Logger.Error("Recherche d’étudiants", ex);
            return new List<Etudiant>();
        }
    }

    public Etudiant? Get(int idEtudiant)
    {
        try { return _etudiants.GetById(idEtudiant); }
        catch (Exception ex)
        {
            Logger.Error("Lecture d’un étudiant", ex);
            return null;
        }
    }

    public int Count()
    {
        try { return _etudiants.Count(); }
        catch (Exception ex)
        {
            Logger.Error("Comptage des étudiants", ex);
            return 0;
        }
    }

    public Result<int> Create(Etudiant etudiant, string codeUtr)
    {
        var validation = StudentValidator.Validate(etudiant);
        if (!validation.IsValid) return Invalid<int>(validation);

        try
        {
            if (string.IsNullOrWhiteSpace(etudiant.Matricule))
                etudiant.Matricule = GenererMatricule();
            etudiant.DateCreation = DateTime.Now;
            if (string.IsNullOrWhiteSpace(etudiant.Statut))
                etudiant.Statut = "ACTIF";

            var id = _etudiants.Insert(etudiant);
            Journal.LogCreation(codeUtr, Tables.Etudiant, id,
                $"{etudiant.Matricule} — {etudiant.NomComplet}".Trim());
            return Result<int>.Ok(id, $"Étudiant {etudiant.Matricule} créé.");
        }
        catch (Exception ex)
        {
            if (OleDbExceptionHelper.IsUniqueViolation(ex))
                return Result<int>.Fail("Ce matricule est déjà utilisé par un autre étudiant.", ErrorCodes.UniqueViolation);
            return Failure<int>("Création d’un étudiant", ex);
        }
    }

    public Result Update(Etudiant etudiant, string codeUtr)
    {
        if (!etudiant.IdEtudiant.HasValue)
            return Result.Fail("Étudiant introuvable.", ErrorCodes.NotFound);
        var validation = StudentValidator.Validate(etudiant);
        if (!validation.IsValid) return Invalid(validation);

        try
        {
            var updated = _etudiants.Update(etudiant);
            if (updated == 0)
                return Result.Fail("Étudiant introuvable : il a peut-être été supprimé.", ErrorCodes.NotFound);
            Journal.LogModification(codeUtr, Tables.Etudiant, etudiant.IdEtudiant,
                $"{etudiant.Matricule} — {etudiant.NomComplet}".Trim());
            return Result.Ok("Dossier étudiant enregistré.");
        }
        catch (Exception ex)
        {
            if (OleDbExceptionHelper.IsUniqueViolation(ex))
                return Result.Fail("Ce matricule est déjà utilisé par un autre étudiant.", ErrorCodes.UniqueViolation);
            return Failure("Modification d’un étudiant", ex);
        }
    }

    public Result Delete(int idEtudiant, string codeUtr)
    {
        try
        {
            var existing = _etudiants.GetById(idEtudiant);
            if (existing is null)
                return Result.Fail("Étudiant introuvable.", ErrorCodes.NotFound);
            _etudiants.Delete(idEtudiant);
            Journal.LogSuppression(codeUtr, Tables.Etudiant, idEtudiant,
                $"{existing.Matricule} — {existing.NomComplet}".Trim());
            return Result.Ok("Étudiant supprimé.");
        }
        catch (Exception ex)
        {
            if (OleDbExceptionHelper.IsForeignKeyViolation(ex))
                return Result.Fail("Suppression impossible : cet étudiant possède des inscriptions ou des données liées.",
                    ErrorCodes.ForeignKeyViolation);
            return Failure("Suppression d’un étudiant", ex);
        }
    }

    /// <summary>
    /// Génère un matricule unique ETU-AAAA-#### (année courante + séquence).
    /// Réessaie en cas de collision (index unique IX_ETU_MAT).
    /// </summary>
    public string GenererMatricule()
    {
        var prefixe = $"ETU-{DateTime.Today.Year}-";
        var existants = new HashSet<string>(_etudiants.ListMatricules(prefixe), StringComparer.OrdinalIgnoreCase);
        var sequence = 0;
        foreach (var matricule in existants)
        {
            var suffixe = matricule.Substring(prefixe.Length);
            if (int.TryParse(suffixe, out var numero) && numero > sequence)
                sequence = numero;
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
