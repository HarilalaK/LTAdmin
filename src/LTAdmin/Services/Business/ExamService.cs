using System.Data;
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
/// Examens : sessions, épreuves, notes d'examen et résultats finaux.
/// Réimplémentation C# de GENERER_RESULTAT_FINAL(idClasse, idSession) :
/// moyenne = CC × POIDS_CC/100 + examen × POIDS_EXAMEN/100, mention via
/// GRILLE_MENTION, décision via MOY_ADMISSION, rang. Idempotent par
/// inscription (le schéma ne porte pas de colonne session sur RESULTAT_FINAL).
/// </summary>
public sealed class ExamService : ServiceBase
{
    private readonly ExamRepository _examens;
    private readonly BulletinRepository _bulletins;
    private readonly EnrollmentRepository _inscriptions;
    private readonly ReferentielRepository _referentiel;

    public ExamService(AccessDatabase database, AppLogger logger, JournalService journal, ParametreService parametres)
        : base(database, logger, journal, parametres)
    {
        _examens = new ExamRepository(database);
        _bulletins = new BulletinRepository(database);
        _inscriptions = new EnrollmentRepository(database);
        _referentiel = new ReferentielRepository(database);
    }

    public List<SessionExam> ListSessions(int? idAnnee = null)
    {
        try { return _examens.ListSessions(idAnnee); }
        catch (Exception ex)
        {
            Logger.Error("Liste des sessions d’examen", ex);
            return new List<SessionExam>();
        }
    }

    public Result<int> CreateSession(SessionExam session, string codeUtr)
    {
        var validation = ExamValidator.ValidateSession(session);
        if (!validation.IsValid) return Invalid<int>(validation);
        try
        {
            var id = _examens.InsertSession(session);
            Journal.LogCreation(codeUtr, Tables.SessionExam, id, session.Libelle);
            return Result<int>.Ok(id, "Session d’examen créée.");
        }
        catch (Exception ex) { return Failure<int>("Création d’une session", ex); }
    }

    public Result SetSessionCloturee(int idSession, bool cloturee, string codeUtr)
    {
        try
        {
            var session = _examens.GetSession(idSession);
            if (session is null)
                return Result.Fail("Session introuvable.", ErrorCodes.NotFound);
            _examens.SetSessionCloturee(idSession, cloturee);
            Journal.LogOperation(codeUtr, cloturee ? "CLOTURE_SESSION" : "REOUVERTURE_SESSION",
                Tables.SessionExam, idSession, session.Libelle);
            return Result.Ok(cloturee ? "Session clôturée." : "Session rouverte.");
        }
        catch (Exception ex) { return Failure("Clôture d’une session", ex); }
    }

    public List<EpreuveDetail> ListEpreuves(int? idSession = null, int? idClasse = null)
    {
        try { return _examens.ListEpreuves(idSession, idClasse); }
        catch (Exception ex)
        {
            Logger.Error("Liste des épreuves", ex);
            return new List<EpreuveDetail>();
        }
    }

    public Result<int> CreateEpreuve(Epreuve epreuve, string codeUtr)
    {
        if (!epreuve.Bareme.HasValue || epreuve.Bareme.Value <= 0)
            epreuve.Bareme = Parametres.BaremeDefaut;
        if (!epreuve.Coefficient.HasValue || epreuve.Coefficient.Value <= 0)
            epreuve.Coefficient = 1d;
        var validation = ExamValidator.ValidateEpreuve(epreuve);
        if (!validation.IsValid) return Invalid<int>(validation);
        try
        {
            var session = _examens.GetSession(epreuve.IdSession!.Value);
            if (session is null)
                return Result<int>.Fail("Session introuvable.", ErrorCodes.NotFound);
            if (session.Cloturee == true)
                return Result<int>.Fail("Session clôturée : rouvrez-la pour ajouter une épreuve.", ErrorCodes.BusinessRule);
            var id = _examens.InsertEpreuve(epreuve);
            Journal.LogCreation(codeUtr, Tables.Epreuve, id, epreuve.CodeMatiere);
            return Result<int>.Ok(id, "Épreuve créée.");
        }
        catch (Exception ex) { return Failure<int>("Création d’une épreuve", ex); }
    }

    public Result UpdateEpreuve(Epreuve epreuve, string codeUtr)
    {
        if (!epreuve.IdEpreuve.HasValue)
            return Result.Fail("Épreuve introuvable.", ErrorCodes.NotFound);
        var validation = ExamValidator.ValidateEpreuve(epreuve);
        if (!validation.IsValid) return Invalid(validation);
        try
        {
            var updated = _examens.UpdateEpreuve(epreuve);
            if (updated == 0)
                return Result.Fail("Épreuve introuvable.", ErrorCodes.NotFound);
            Journal.LogModification(codeUtr, Tables.Epreuve, epreuve.IdEpreuve, epreuve.CodeMatiere);
            return Result.Ok("Épreuve enregistrée.");
        }
        catch (Exception ex) { return Failure("Modification d’une épreuve", ex); }
    }

    public Result DeleteEpreuve(int idEpreuve, string codeUtr)
    {
        try
        {
            var existing = _examens.GetEpreuve(idEpreuve);
            if (existing is null)
                return Result.Fail("Épreuve introuvable.", ErrorCodes.NotFound);
            _examens.DeleteEpreuve(idEpreuve);
            Journal.LogSuppression(codeUtr, Tables.Epreuve, idEpreuve, existing.CodeMatiere);
            return Result.Ok("Épreuve supprimée.");
        }
        catch (Exception ex)
        {
            if (OleDbExceptionHelper.IsForeignKeyViolation(ex))
                return Result.Fail("Suppression impossible : des notes d’examen sont déjà saisies.", ErrorCodes.ForeignKeyViolation);
            return Failure("Suppression d’une épreuve", ex);
        }
    }

    public List<NoteSaisieRow> GetGrilleSaisie(int idEpreuve)
    {
        try
        {
            var epreuve = _examens.GetEpreuveDetail(idEpreuve);
            if (epreuve?.IdClasse is null) return new List<NoteSaisieRow>();
            return _examens.ListGrilleSaisie(idEpreuve, epreuve.IdClasse.Value);
        }
        catch (Exception ex)
        {
            Logger.Error("Grille de saisie des notes d’examen", ex);
            return new List<NoteSaisieRow>();
        }
    }

    public Result UpsertNoteExamen(int idEpreuve, int idInscription, double? valeur, bool absent, string? copieNum, string codeUtr)
    {
        try
        {
            var epreuve = _examens.GetEpreuveDetail(idEpreuve);
            if (epreuve is null)
                return Result.Fail("Épreuve introuvable.", ErrorCodes.NotFound);
            var bareme = epreuve.Bareme ?? Parametres.BaremeDefaut;
            var validation = GradeValidator.ValidateNote(valeur, absent, bareme);
            if (!validation.IsValid) return Invalid(validation);
            if (!string.IsNullOrEmpty(copieNum) && copieNum.Length > 40)
                return Result.Fail("N° de copie : 40 caractères maximum.", ErrorCodes.Validation);

            var inscription = _inscriptions.GetById(idInscription);
            if (inscription is null)
                return Result.Fail("Inscription introuvable.", ErrorCodes.NotFound);
            if (inscription.IdClasse != epreuve.IdClasse)
                return Result.Fail("Cet étudiant n’est pas inscrit dans la classe de cette épreuve.", ErrorCodes.BusinessRule);

            var existing = _examens.GetNoteExamen(idEpreuve, idInscription);
            if (existing is null)
            {
                var id = _examens.InsertNoteExamen(new NoteExamen
                {
                    IdEpreuve = idEpreuve,
                    IdInscription = idInscription,
                    ValeurNote = absent ? null : valeur,
                    Absent = absent,
                    CopieNum = copieNum,
                    DateSaisie = DateTime.Now,
                    CodeUtr = codeUtr
                });
                Journal.LogCreation(codeUtr, Tables.NoteExamen, id, $"Épreuve {idEpreuve} / inscrit {idInscription}");
            }
            else
            {
                existing.ValeurNote = absent ? null : valeur;
                existing.Absent = absent;
                existing.CopieNum = copieNum;
                existing.DateSaisie = DateTime.Now;
                existing.CodeUtr = codeUtr;
                _examens.UpdateNoteExamen(existing);
                Journal.LogModification(codeUtr, Tables.NoteExamen, existing.IdNoteEx, $"Épreuve {idEpreuve} / inscrit {idInscription}");
            }
            return Result.Ok("Note d’examen enregistrée.");
        }
        catch (Exception ex) { return Failure("Saisie d’une note d’examen", ex); }
    }

    public List<ResultatFinal> ListResultats(int idClasse)
    {
        try { return _bulletins.ListByClasse(idClasse); }
        catch (Exception ex)
        {
            Logger.Error("Liste des résultats finaux", ex);
            return new List<ResultatFinal>();
        }
    }

    /// <summary>
    /// Génère les résultats finaux d'une classe pour une session.
    /// MOY_CC = moyenne des bulletins (toutes périodes) ; MOY_EXAM = moyenne
    /// pondérée des notes d'examen normalisées sur 20 ; si l'une des deux
    /// parties est absente, la moyenne générale reprend la partie disponible.
    /// </summary>
    public Result<int> GenererResultatsFinaux(int idClasse, int idSession, string codeUtr, string? observation = null)
    {
        try
        {
            var classe = _referentiel.GetClasse(idClasse);
            if (classe is null)
                return Result<int>.Fail("Classe introuvable.", ErrorCodes.NotFound);
            var session = _examens.GetSession(idSession);
            if (session is null)
                return Result<int>.Fail("Session introuvable.", ErrorCodes.NotFound);
            if (session.Cloturee == true)
                return Result<int>.Fail("Session clôturée : rouvrez-la pour régénérer les résultats.", ErrorCodes.BusinessRule);

            var inscrits = _inscriptions.ListByClasse(idClasse);
            if (inscrits.Count == 0)
                return Result<int>.Fail($"Aucun inscrit dans la classe « {classe.Libelle} ».", ErrorCodes.BusinessRule);

            var grille = _bulletins.ListMentions();
            var poidsCc = Parametres.PoidsCc;
            var poidsExam = Parametres.PoidsExamen;
            var seuil = Parametres.MoyAdmission;
            var moyExamParInscrit = CalculerMoyennesExamen(idClasse, idSession);

            using var tx = Db.BeginTransaction();
            var rangsSource = new List<(int Id, double? Valeur)>();
            foreach (var inscrit in inscrits)
            {
                var idInscription = inscrit.IdInscription!.Value;
                _bulletins.DeleteByInscription(idInscription);

                var moyennesBulletins = _bulletins.ListMoyennesByInscription(idInscription);
                double? moyCc = moyennesBulletins.Count > 0 ? moyennesBulletins.Average() : null;
                moyExamParInscrit.TryGetValue(idInscription, out var moyExam);

                double? moyenneGen = (moyCc, moyExam) switch
                {
                    (not null, not null) => moyCc.Value * poidsCc / 100d + moyExam.Value * poidsExam / 100d,
                    (not null, null) => moyCc,
                    (null, not null) => moyExam,
                    _ => null
                };
                var mention = MentionHelper.Trouver(grille, moyenneGen);
                var resultat = new ResultatFinal
                {
                    IdInscription = idInscription,
                    MoyCc = moyCc,
                    MoyExam = moyExam,
                    MoyenneGen = moyenneGen,
                    Mention = mention?.Mention,
                    Decision = moyenneGen.HasValue
                        ? (moyenneGen.Value >= seuil ? "ADMIS" : "AJOURNÉ")
                        : "EN ATTENTE",
                    DateDelib = DateTime.Now,
                    Observation = observation
                };
                var idResultat = _bulletins.InsertResultat(resultat);
                rangsSource.Add((idResultat, moyenneGen));
            }

            var rangs = MentionHelper.RangsCompetition(rangsSource);
            foreach (var item in rangsSource)
            {
                _bulletins.UpdateResultatRang(new ResultatFinal
                {
                    IdResultat = item.Id,
                    Rang = rangs.TryGetValue(item.Id, out var rang) && rang > 0 ? rang : null
                });
            }

            tx.Complete();
            Journal.LogOperation(codeUtr, "GENERATION_RESULTATS", Tables.ResultatFinal, null,
                $"Classe « {classe.Libelle} » × session « {session.Libelle} » : {inscrits.Count} résultat(s).");
            return Result<int>.Ok(inscrits.Count, $"{inscrits.Count} résultat(s) généré(s) pour « {classe.Libelle} ».");
        }
        catch (Exception ex) { return Failure<int>("Génération des résultats finaux", ex); }
    }

    private Dictionary<int, double?> CalculerMoyennesExamen(int idClasse, int idSession)
    {
        var table = _examens.ListNotesPonderees(idClasse, idSession);
        var cumuls = new Dictionary<int, (double Points, double Coefs)>();
        foreach (DataRow row in table.Rows)
        {
            var idInscription = DataRowMapper.GetInt32(row, "ID_INSCRIPTION");
            var valeur = DataRowMapper.GetDouble(row, "VALEUR_NOTE");
            var absent = DataRowMapper.GetBoolean(row, "ABSENT", false);
            var bareme = DataRowMapper.GetDouble(row, "BAREME");
            var coef = DataRowMapper.GetDouble(row, "COEFFICIENT") ?? 1d;
            if (!idInscription.HasValue || absent || !valeur.HasValue) continue;
            if (!bareme.HasValue || bareme.Value <= 0) continue;
            var normalisee = valeur.Value / bareme.Value * 20d;
            if (cumuls.TryGetValue(idInscription.Value, out var cumul))
                cumuls[idInscription.Value] = (cumul.Points + normalisee * coef, cumul.Coefs + coef);
            else
                cumuls[idInscription.Value] = (normalisee * coef, coef);
        }
        return cumuls.ToDictionary(
            entree => entree.Key,
            entree => entree.Value.Coefs > 0 ? (double?)(entree.Value.Points / entree.Value.Coefs) : null);
    }
}
