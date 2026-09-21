using System.Globalization;
using LTAdmin.Models.Entities;

namespace LTAdmin.Services.Validation;

/// <summary>
/// Résultat d'une validation métier : la liste des anomalies en français.
/// Les services refusent toute écriture invalide avant de toucher la base.
/// </summary>
public sealed class ValidationResult
{
    public List<string> Errors { get; } = new();

    public bool IsValid => Errors.Count == 0;

    public static ValidationResult Success() => new();

    public void AddError(string message)
    {
        if (!string.IsNullOrWhiteSpace(message)) Errors.Add(message);
    }

    public void Require(bool condition, string message)
    {
        if (!condition) AddError(message);
    }

    public string ToMessage() => string.Join(Environment.NewLine, Errors);
}

/// <summary>
/// Contrôles élémentaires réutilisables (longueurs = limites TEXT d'Access).
/// </summary>
public static class Guard
{
    public static void Required(ValidationResult result, string? value, string field)
        => result.Require(!string.IsNullOrWhiteSpace(value), $"{field} : valeur obligatoire.");

    public static void RequiredId(ValidationResult result, int? value, string field)
        => result.Require(value.HasValue && value.Value > 0, $"{field} : valeur obligatoire.");

    public static void RequiredCode(ValidationResult result, string? value, string field)
        => result.Require(!string.IsNullOrWhiteSpace(value), $"{field} : valeur obligatoire.");

    public static void MaxLength(ValidationResult result, string? value, int max, string field)
    {
        if (!string.IsNullOrEmpty(value) && value.Length > max)
            result.AddError($"{field} : {max} caractères maximum (actuellement {value.Length}).");
    }

    public static void Positive(ValidationResult result, double? value, string field, bool allowZero = false)
    {
        if (!value.HasValue) return;
        result.Require(allowZero ? value.Value >= 0 : value.Value > 0,
            $"{field} : montant {(allowZero ? "positif ou nul" : "strictement positif")} attendu.");
    }

    public static void Positive(ValidationResult result, decimal? value, string field, bool allowZero = false)
    {
        if (!value.HasValue) return;
        result.Require(allowZero ? value.Value >= 0 : value.Value > 0,
            $"{field} : montant {(allowZero ? "positif ou nul" : "strictement positif")} attendu.");
    }

    public static void Range(ValidationResult result, double? value, double min, double max, string field)
    {
        if (!value.HasValue) return;
        result.Require(value.Value >= min && value.Value <= max,
            $"{field} : valeur entre {min} et {max} attendue.");
    }

    public static void InSet(ValidationResult result, string? value, string field, params string[] allowed)
    {
        if (string.IsNullOrWhiteSpace(value)) return;
        result.Require(allowed.Any(a => string.Equals(a, value.Trim(), StringComparison.OrdinalIgnoreCase)),
            $"{field} : valeur attendue parmi {string.Join(", ", allowed)}.");
    }

    public static void Email(ValidationResult result, string? value, string field)
    {
        if (string.IsNullOrWhiteSpace(value)) return;
        var text = value.Trim();
        var at = text.IndexOf('@');
        result.Require(at > 0 && at < text.Length - 1 && text.IndexOf(' ', StringComparison.Ordinal) < 0,
            $"{field} : adresse e-mail invalide.");
    }

    public static void PastOrToday(ValidationResult result, DateTime? value, string field)
    {
        if (!value.HasValue) return;
        result.Require(value.Value.Date <= DateTime.Today, $"{field} : date future interdite.");
    }

    public static void DateOrder(ValidationResult result, DateTime? debut, DateTime? fin, string fieldDebut, string fieldFin)
    {
        if (!debut.HasValue || !fin.HasValue) return;
        result.Require(fin.Value >= debut.Value, $"{fieldFin} : doit être postérieure ou égale à {fieldDebut}.");
    }

    public static void HeureTexte(ValidationResult result, string? value, string field)
    {
        if (string.IsNullOrWhiteSpace(value)) return;
        result.Require(TimeSpan.TryParseExact(value.Trim(), new[] { "h\\:mm", "hh\\:mm" },
                CultureInfo.InvariantCulture, TimeSpanStyles.None, out _),
            $"{field} : heure au format HH:mm attendue (ex. 07:30).");
    }
}

/// <summary>Validateurs par entité, alignés sur le schéma LTA_ADM.accdb.</summary>
public static class StudentValidator
{
    public static ValidationResult Validate(Etudiant etudiant)
    {
        var result = new ValidationResult();
        Guard.Required(result, etudiant.Nom, "Nom");
        Guard.Required(result, etudiant.Prenom, "Prénom");
        Guard.MaxLength(result, etudiant.Matricule, 40, "Matricule");
        Guard.MaxLength(result, etudiant.Nom, 120, "Nom");
        Guard.MaxLength(result, etudiant.Prenom, 160, "Prénom");
        Guard.InSet(result, etudiant.Sexe, "Sexe", "M", "F");
        Guard.PastOrToday(result, etudiant.DateNaissance, "Date de naissance");
        if (etudiant.DateNaissance.HasValue)
            result.Require(etudiant.DateNaissance.Value.Date >= DateTime.Today.AddYears(-100),
                "Date de naissance : date invraisemblable (plus de 100 ans).");
        Guard.MaxLength(result, etudiant.LieuNaissance, 120, "Lieu de naissance");
        Guard.MaxLength(result, etudiant.Cin, 40, "CIN");
        Guard.MaxLength(result, etudiant.Nationalite, 80, "Nationalité");
        Guard.MaxLength(result, etudiant.Adresse, 300, "Adresse");
        Guard.MaxLength(result, etudiant.Tel, 80, "Téléphone");
        Guard.MaxLength(result, etudiant.Email, 160, "E-mail");
        Guard.Email(result, etudiant.Email, "E-mail");
        Guard.MaxLength(result, etudiant.NomTuteur, 160, "Nom du tuteur");
        Guard.MaxLength(result, etudiant.TelTuteur, 80, "Téléphone du tuteur");
        Guard.MaxLength(result, etudiant.ProfessionTuteur, 120, "Profession du tuteur");
        Guard.MaxLength(result, etudiant.SerieBacc, 40, "Série du bac");
        Guard.MaxLength(result, etudiant.EtabOrigine, 200, "Établissement d’origine");
        Guard.MaxLength(result, etudiant.Photo, 510, "Photo (chemin)");
        Guard.MaxLength(result, etudiant.Statut, 40, "Statut");
        if (etudiant.AnneeBacc.HasValue)
            result.Require(etudiant.AnneeBacc.Value >= 1950 && etudiant.AnneeBacc.Value <= DateTime.Today.Year + 1,
                "Année du bac : année invalide.");
        return result;
    }
}

public static class EnrollmentValidator
{
    public static ValidationResult Validate(Inscription inscription)
    {
        var result = new ValidationResult();
        Guard.RequiredId(result, inscription.IdEtudiant, "Étudiant");
        Guard.RequiredId(result, inscription.IdClasse, "Classe");
        Guard.MaxLength(result, inscription.NumInscription, 40, "N° d’inscription");
        Guard.MaxLength(result, inscription.Statut, 40, "Statut");
        Guard.MaxLength(result, inscription.MotifSortie, 300, "Motif de sortie");
        Guard.DateOrder(result, inscription.DateInscription, inscription.DateSortie, "date d’inscription", "date de sortie");
        return result;
    }
}

public static class StaffValidator
{
    public static ValidationResult ValidateFormateur(Formateur formateur)
    {
        var result = new ValidationResult();
        Guard.Required(result, formateur.Nom, "Nom");
        Guard.Required(result, formateur.Prenom, "Prénom");
        Guard.MaxLength(result, formateur.Matricule, 40, "Matricule");
        Guard.MaxLength(result, formateur.Nom, 120, "Nom");
        Guard.MaxLength(result, formateur.Prenom, 120, "Prénom");
        Guard.InSet(result, formateur.Sexe, "Sexe", "M", "F");
        Guard.PastOrToday(result, formateur.DateNaissance, "Date de naissance");
        Guard.MaxLength(result, formateur.Cin, 40, "CIN");
        Guard.MaxLength(result, formateur.Adresse, 300, "Adresse");
        Guard.MaxLength(result, formateur.Tel, 80, "Téléphone");
        Guard.MaxLength(result, formateur.Email, 160, "E-mail");
        Guard.Email(result, formateur.Email, "E-mail");
        Guard.MaxLength(result, formateur.Specialite, 160, "Spécialité");
        Guard.MaxLength(result, formateur.Diplome, 160, "Diplôme");
        Guard.MaxLength(result, formateur.Contrat, 40, "Contrat");
        Guard.Positive(result, formateur.TauxHoraire, "Taux horaire", allowZero: true);
        Guard.MaxLength(result, formateur.Photo, 510, "Photo (chemin)");
        return result;
    }

    public static ValidationResult ValidateProgramme(Programme programme)
    {
        var result = new ValidationResult();
        Guard.RequiredId(result, programme.IdClasse, "Classe");
        Guard.RequiredCode(result, programme.CodeMatiere, "Matière");
        Guard.MaxLength(result, programme.CodeMatiere, 20, "Matière");
        Guard.Positive(result, programme.Coefficient, "Coefficient");
        if (programme.VolHoraire.HasValue)
            result.Require(programme.VolHoraire.Value >= 0, "Volume horaire : valeur positive ou nulle attendue.");
        Guard.Positive(result, programme.NoteElimin, "Note éliminatoire", allowZero: true);
        Guard.MaxLength(result, programme.Observation, 300, "Observation");
        return result;
    }
}

public static class EvaluationValidator
{
    public static ValidationResult ValidatePeriode(PeriodeEval periode)
    {
        var result = new ValidationResult();
        Guard.RequiredId(result, periode.IdAnnee, "Année scolaire");
        Guard.MaxLength(result, periode.CodePeriode, 20, "Code période");
        Guard.MaxLength(result, periode.Libelle, 100, "Libellé");
        Guard.Positive(result, periode.Ponderation, "Pondération", allowZero: true);
        Guard.DateOrder(result, periode.DateDebut, periode.DateFin, "date de début", "date de fin");
        return result;
    }

    public static ValidationResult ValidateEvaluation(Evaluation evaluation)
    {
        var result = new ValidationResult();
        Guard.RequiredId(result, evaluation.IdPeriode, "Période");
        Guard.RequiredId(result, evaluation.IdProg, "Programme (classe × matière)");
        Guard.MaxLength(result, evaluation.Intitule, 200, "Intitulé");
        Guard.MaxLength(result, evaluation.Nature, 50, "Nature");
        Guard.Positive(result, evaluation.Bareme, "Barème");
        Guard.Positive(result, evaluation.Poids, "Poids");
        return result;
    }
}

public static class GradeValidator
{
    public static ValidationResult ValidateNote(double? valeur, bool absent, double bareme)
    {
        var result = new ValidationResult();
        if (absent) return result;
        result.Require(valeur.HasValue, "Note : valeur obligatoire (ou cocher « absent »).");
        Guard.Range(result, valeur, 0, bareme, "Note");
        return result;
    }
}

public static class ExamValidator
{
    public static ValidationResult ValidateSession(SessionExam session)
    {
        var result = new ValidationResult();
        Guard.RequiredId(result, session.IdAnnee, "Année scolaire");
        Guard.Required(result, session.Libelle, "Libellé");
        Guard.MaxLength(result, session.Libelle, 120, "Libellé");
        Guard.MaxLength(result, session.Nature, 50, "Nature");
        Guard.DateOrder(result, session.DateDebut, session.DateFin, "date de début", "date de fin");
        return result;
    }

    public static ValidationResult ValidateEpreuve(Epreuve epreuve)
    {
        var result = new ValidationResult();
        Guard.RequiredId(result, epreuve.IdSession, "Session");
        Guard.RequiredId(result, epreuve.IdClasse, "Classe");
        Guard.RequiredCode(result, epreuve.CodeMatiere, "Matière");
        Guard.HeureTexte(result, epreuve.HeureDebut, "Heure de début");
        if (epreuve.DureeMn.HasValue)
            result.Require(epreuve.DureeMn.Value > 0, "Durée : valeur strictement positive attendue (minutes).");
        Guard.Positive(result, epreuve.Coefficient, "Coefficient");
        Guard.Positive(result, epreuve.Bareme, "Barème");
        Guard.MaxLength(result, epreuve.Surveillant, 160, "Surveillant");
        return result;
    }
}

public static class PlanningValidator
{
    public static readonly string[] JoursAutorises =
        { "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche" };

    public static ValidationResult ValidateCreneau(Creneau creneau)
    {
        var result = new ValidationResult();
        Guard.MaxLength(result, creneau.Libelle, 60, "Libellé");
        Guard.HeureTexte(result, creneau.HeureDebut, "Heure de début");
        Guard.HeureTexte(result, creneau.HeureFin, "Heure de fin");
        return result;
    }

    public static ValidationResult ValidateSlot(EmploiDuTemps slot)
    {
        var result = new ValidationResult();
        Guard.RequiredId(result, slot.IdProg, "Programme (classe × matière)");
        Guard.RequiredId(result, slot.IdCreneau, "Créneau");
        Guard.Required(result, slot.Jour, "Jour");
        Guard.InSet(result, slot.Jour, "Jour", JoursAutorises);
        Guard.MaxLength(result, slot.Jour, 24, "Jour");
        Guard.DateOrder(result, slot.DateDebut, slot.DateFin, "date de début", "date de fin");
        return result;
    }

    public static ValidationResult ValidateSeance(Seance seance)
    {
        var result = new ValidationResult();
        Guard.RequiredId(result, seance.IdEdt, "Créneau d’emploi du temps");
        result.Require(seance.DateSeance.HasValue, "Date de séance : valeur obligatoire.");
        Guard.Positive(result, seance.NbHeures, "Nombre d’heures", allowZero: true);
        Guard.MaxLength(result, seance.Statut, 40, "Statut");
        return result;
    }

    public static ValidationResult ValidateAbsence(Absence absence)
    {
        var result = new ValidationResult();
        Guard.RequiredId(result, absence.IdSeance, "Séance");
        Guard.RequiredId(result, absence.IdInscription, "Inscription");
        Guard.Positive(result, absence.NbHeures, "Nombre d’heures");
        Guard.MaxLength(result, absence.Nature, 30, "Nature");
        Guard.MaxLength(result, absence.Motif, 300, "Motif");
        return result;
    }
}

public static class PaymentValidator
{
    public static ValidationResult ValidateTarif(Tarif tarif)
    {
        var result = new ValidationResult();
        Guard.RequiredId(result, tarif.IdClasse, "Classe");
        Guard.Required(result, tarif.TypeFrais, "Type de frais");
        Guard.MaxLength(result, tarif.TypeFrais, 60, "Type de frais");
        Guard.Positive(result, tarif.Montant, "Montant");
        if (tarif.NbTranches.HasValue)
            result.Require(tarif.NbTranches.Value >= 1 && tarif.NbTranches.Value <= 24,
                "Nombre de tranches : valeur entre 1 et 24 attendue.");
        Guard.MaxLength(result, tarif.Observation, 300, "Observation");
        return result;
    }

    public static ValidationResult ValidateEncaissement(decimal montant, string? modePaie, decimal reste)
    {
        var result = new ValidationResult();
        result.Require(montant > 0, "Montant : valeur strictement positive attendue.");
        Guard.Required(result, modePaie, "Mode de paiement");
        Guard.MaxLength(result, modePaie, 50, "Mode de paiement");
        result.Require(montant <= reste + 0.01m,
            $"Montant : {montant:N0} supérieur au reste à payer ({reste:N0}).");
        return result;
    }

    public static ValidationResult ValidateRemise(decimal? remise, decimal montantDu)
    {
        var result = new ValidationResult();
        Guard.Positive(result, remise, "Remise", allowZero: true);
        if (remise.HasValue)
            result.Require(remise.Value <= montantDu, "Remise : ne peut pas dépasser le montant dû.");
        return result;
    }
}

public static class PayrollValidator
{
    public static ValidationResult ValidateCalcul(int? idFormateur, DateTime debut, DateTime fin)
    {
        var result = new ValidationResult();
        Guard.RequiredId(result, idFormateur, "Formateur");
        result.Require(fin >= debut, "Date de fin : doit être postérieure ou égale à la date de début.");
        result.Require((fin - debut).TotalDays <= 366, "Période : 12 mois maximum par calcul.");
        return result;
    }
}

public static class ReferentielValidator
{
    public static ValidationResult ValidateClasse(Classe classe)
    {
        var result = new ValidationResult();
        Guard.Required(result, classe.Libelle, "Libellé");
        Guard.MaxLength(result, classe.Libelle, 120, "Libellé");
        Guard.RequiredId(result, classe.IdAnnee, "Année scolaire");
        Guard.MaxLength(result, classe.CodeFiliere, 20, "Filière");
        Guard.MaxLength(result, classe.CodeNiveau, 20, "Niveau");
        if (classe.EffectifMax.HasValue)
            result.Require(classe.EffectifMax.Value > 0, "Effectif maximum : valeur strictement positive attendue.");
        return result;
    }
}
