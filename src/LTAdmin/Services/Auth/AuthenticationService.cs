using LTAdmin.Core;
using LTAdmin.Data;
using LTAdmin.Models;
using LTAdmin.Repositories;
using LTAdmin.Services.Logging;

namespace LTAdmin.Services.Auth;

/// <summary>
/// Authentification sur la table UTILISATEUR (CODE_UTR unique, comparaison
/// insensible à la casse comme le fait Access, compte ACTIF requis).
/// Note historique : les mots de passe sont stockés en clair dans la base
/// fournie ; le service centralise la vérification pour permettre un
/// durcissement ultérieur (hachage) sans toucher les écrans.
/// </summary>
public sealed class AuthenticationService
{
    private readonly AdminRepository _admin;
    private readonly JournalService _journal;
    private readonly AppLogger _logger;

    public AuthenticationService(AccessDatabase database, JournalService journal, AppLogger logger)
    {
        _admin = new AdminRepository(database);
        _journal = journal;
        _logger = logger;
    }

    /// <summary>
    /// Vérifie un couple identifiant / mot de passe avec une requête paramétrée.
    /// </summary>
    public Result<UserSession> Authenticate(string login, string password)
    {
        var code = (login ?? string.Empty).Trim();
        if (string.IsNullOrWhiteSpace(code) || string.IsNullOrEmpty(password))
            return Result<UserSession>.Fail("Saisissez votre identifiant et votre mot de passe.", ErrorCodes.Authentication);

        try
        {
            var user = _admin.GetUtilisateur(code);
            if (user is null || string.IsNullOrWhiteSpace(user.CodeUtr))
            {
                _journal.LogConnexion(code, false);
                return Result<UserSession>.Fail("Identifiant ou mot de passe incorrect.", ErrorCodes.Authentication);
            }
            if (user.Actif == false)
            {
                _journal.LogConnexion(user.CodeUtr!, false);
                return Result<UserSession>.Fail("Ce compte est désactivé. Contactez l’administrateur.", ErrorCodes.Authentication);
            }
            if (!string.Equals(user.MotPasse ?? string.Empty, password, StringComparison.Ordinal))
            {
                _journal.LogConnexion(user.CodeUtr!, false);
                return Result<UserSession>.Fail("Identifiant ou mot de passe incorrect.", ErrorCodes.Authentication);
            }

            var displayName = string.IsNullOrWhiteSpace(user.NomUtr) ? user.CodeUtr! : user.NomUtr!;
            var role = string.IsNullOrWhiteSpace(user.Profil) ? "Utilisateur" : user.Profil!;
            _journal.LogConnexion(user.CodeUtr!, true);
            return Result<UserSession>.Ok(new UserSession(user.CodeUtr!, displayName, role));
        }
        catch (Exception ex)
        {
            var error = OleDbExceptionHelper.Interpret(ex);
            _logger.Error("Authentification", ex);
            return Result<UserSession>.Fail("Connexion impossible : " + error.Message, ErrorCodes.Technical);
        }
    }

    /// <summary>Change le mot de passe d'un compte après vérification de l'ancien.</summary>
    public Result ChangePassword(string codeUtr, string ancienMotPasse, string nouveauMotPasse)
    {
        if (string.IsNullOrWhiteSpace(nouveauMotPasse) || nouveauMotPasse.Length < 4)
            return Result.Fail("Le nouveau mot de passe doit contenir au moins 4 caractères.", ErrorCodes.Validation);
        if (nouveauMotPasse.Length > 120)
            return Result.Fail("Le nouveau mot de passe doit contenir 120 caractères maximum.", ErrorCodes.Validation);

        try
        {
            var user = _admin.GetUtilisateur(codeUtr.Trim());
            if (user is null)
                return Result.Fail("Compte introuvable.", ErrorCodes.NotFound);
            if (!string.Equals(user.MotPasse ?? string.Empty, ancienMotPasse, StringComparison.Ordinal))
                return Result.Fail("L’ancien mot de passe est incorrect.", ErrorCodes.Authentication);

            _admin.UpdateMotPasse(user.CodeUtr!, nouveauMotPasse);
            _journal.LogOperation(codeUtr, "MOT_DE_PASSE", Tables.Utilisateur, null, "Changement de mot de passe.");
            return Result.Ok("Mot de passe modifié.");
        }
        catch (Exception ex)
        {
            var error = OleDbExceptionHelper.Interpret(ex);
            _logger.Error("Changement de mot de passe", ex);
            return Result.Fail(error.Message, error.Code);
        }
    }
}

/// <summary>
/// Habilitations par groupe fonctionnel. Les profils connus sont ADMIN,
/// SCOLARITE et FINANCE ; tout autre profil n'accède qu'au tableau de bord
/// et aux états.
/// </summary>
public static class Habilitations
{
    public const string Scolarite = "SCOLARITÉ";
    public const string Pedagogie = "PÉDAGOGIE";
    public const string Planning = "PLANNING";
    public const string Examens = "EXAMENS";
    public const string Bulletins = "BULLETINS";
    public const string Finances = "FINANCES";
    public const string Referentiel = "RÉFÉRENTIEL";
    public const string Administration = "ADMINISTRATION";
    public const string Accueil = "ACCUEIL";

    public static bool CanAccess(string? profil, string groupe)
    {
        if (string.Equals(groupe, Accueil, StringComparison.OrdinalIgnoreCase))
            return true;
        if (string.Equals(profil, Profils.Admin, StringComparison.OrdinalIgnoreCase))
            return true;
        if (string.Equals(profil, Profils.Scolarite, StringComparison.OrdinalIgnoreCase))
            return !string.Equals(groupe, Finances, StringComparison.OrdinalIgnoreCase)
                && !string.Equals(groupe, Administration, StringComparison.OrdinalIgnoreCase);
        if (string.Equals(profil, Profils.Finance, StringComparison.OrdinalIgnoreCase))
            return string.Equals(groupe, Finances, StringComparison.OrdinalIgnoreCase);
        return false;
    }
}
