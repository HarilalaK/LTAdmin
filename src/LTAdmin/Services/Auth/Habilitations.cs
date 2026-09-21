using LTAdmin.Data;

namespace LTAdmin.Services.Auth;

/// <summary>
/// Modules visibles dans le menu (libellés métier, jamais de noms de tables)
/// et habilitations par profil.
/// </summary>
public static class Modules
{
    public const string TableauDeBord = "Tableau de bord";
    public const string Etudiants = "Étudiants";
    public const string Inscriptions = "Inscriptions";
    public const string Referentiel = "Référentiel";
    public const string Formateurs = "Formateurs";
    public const string Notes = "Notes et évaluations";
    public const string Bulletins = "Bulletins";
    public const string Examens = "Examens";
    public const string EmploiDuTemps = "Emploi du temps";
    public const string Absences = "Absences";
    public const string Ecolage = "Écolage";
    public const string Paie = "Paie des formateurs";
    public const string Statistiques = "Statistiques";
    public const string Rapports = "Rapports";
    public const string Administration = "Administration";
    public const string Utilisateurs = "Profils utilisateurs";
}

public static class Habilitations
{
    public static readonly string[] MenuOrder =
    {
        Modules.TableauDeBord,
        Modules.Etudiants,
        Modules.Inscriptions,
        Modules.Referentiel,
        Modules.Formateurs,
        Modules.Notes,
        Modules.Bulletins,
        Modules.Examens,
        Modules.EmploiDuTemps,
        Modules.Absences,
        Modules.Ecolage,
        Modules.Paie,
        Modules.Statistiques,
        Modules.Rapports,
        Modules.Administration
    };

    public static string NormalizeProfil(string? profil)
    {
        var p = (profil ?? "").Trim();
        if (p.Equals(Profils.Admin, StringComparison.OrdinalIgnoreCase)
            || p.Equals(Profils.Administrateur, StringComparison.OrdinalIgnoreCase)
            || p.Equals("Administrateur", StringComparison.OrdinalIgnoreCase))
            return Profils.Administrateur;
        if (p.Equals(Profils.Direction, StringComparison.OrdinalIgnoreCase)
            || p.Equals("DIRECTION", StringComparison.OrdinalIgnoreCase))
            return Profils.Direction;
        if (p.Equals(Profils.Scolarite, StringComparison.OrdinalIgnoreCase)
            || p.Equals(Profils.ScolariteLibelle, StringComparison.OrdinalIgnoreCase)
            || p.Equals("SCOLARITE", StringComparison.OrdinalIgnoreCase))
            return Profils.ScolariteLibelle;
        if (p.Equals(Profils.Finance, StringComparison.OrdinalIgnoreCase)
            || p.Equals(Profils.Comptabilite, StringComparison.OrdinalIgnoreCase)
            || p.Equals("COMPTABILITE", StringComparison.OrdinalIgnoreCase)
            || p.Equals("CAISSE", StringComparison.OrdinalIgnoreCase))
            return Profils.Comptabilite;
        if (p.Equals(Profils.Enseignant, StringComparison.OrdinalIgnoreCase)
            || p.Equals("ENSEIGNANT", StringComparison.OrdinalIgnoreCase)
            || p.Equals("FORMATEUR", StringComparison.OrdinalIgnoreCase))
            return Profils.Enseignant;
        return string.IsNullOrWhiteSpace(p) ? "Utilisateur" : p;
    }

    public static bool CanAccess(string? profil, string module)
    {
        if (string.Equals(module, Modules.TableauDeBord, StringComparison.OrdinalIgnoreCase))
            return true;

        var role = NormalizeProfil(profil);
        if (role == Profils.Administrateur)
            return true;

        return role switch
        {
            var r when r == Profils.Direction => module is
                Modules.Etudiants or Modules.Inscriptions or Modules.Referentiel
                or Modules.Formateurs or Modules.Notes or Modules.Bulletins
                or Modules.Examens or Modules.EmploiDuTemps or Modules.Absences
                or Modules.Ecolage or Modules.Paie or Modules.Statistiques
                or Modules.Rapports,
            var r when r == Profils.ScolariteLibelle => module is
                Modules.Etudiants or Modules.Inscriptions or Modules.Referentiel
                or Modules.Formateurs or Modules.Notes or Modules.Bulletins
                or Modules.Examens or Modules.EmploiDuTemps or Modules.Absences
                or Modules.Statistiques or Modules.Rapports,
            var r when r == Profils.Comptabilite => module is
                Modules.Ecolage or Modules.Paie or Modules.Statistiques or Modules.Rapports,
            var r when r == Profils.Enseignant => module is
                Modules.Notes or Modules.Bulletins or Modules.Examens
                or Modules.EmploiDuTemps or Modules.Absences or Modules.Formateurs,
            _ => false
        };
    }

    public static IReadOnlyList<string> ProfilsConnus { get; } = new[]
    {
        Profils.Administrateur,
        Profils.Direction,
        Profils.ScolariteLibelle,
        Profils.Comptabilite,
        Profils.Enseignant
    };
}
