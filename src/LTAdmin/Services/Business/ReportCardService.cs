using LTAdmin.Core;
using LTAdmin.Data;
using LTAdmin.Models.Dto;
using LTAdmin.Models.Entities;
using LTAdmin.Repositories;
using LTAdmin.Services.Common;
using LTAdmin.Services.Logging;
using LTAdmin.Services.Referentiel;

namespace LTAdmin.Services.Business;

/// <summary>
/// Bulletins : génération, consultation, suppression.
/// Réimplémentation C# de GENERER_BULLETIN(idClasse, idPeriode) :
/// moyennes par matière depuis R_MOYENNE_MATIERE, points = moyenne × coef,
/// moyenne = Σ points / Σ coef, rang, effectif, moyenne de classe,
/// mention via GRILLE_MENTION, appréciation. Régénération idempotente :
/// les bulletins existants (bulletin + lignes) sont d'abord supprimés,
/// en transaction.
/// </summary>
public sealed class ReportCardService : ServiceBase
{
    private readonly BulletinRepository _bulletins;
    private readonly EvaluationRepository _evaluations;
    private readonly EnrollmentRepository _inscriptions;
    private readonly StaffRepository _personnel;
    private readonly ReferentielRepository _referentiel;
    private readonly PlanningRepository _planning;

    public ReportCardService(AccessDatabase database, AppLogger logger, JournalService journal, ParametreService parametres)
        : base(database, logger, journal, parametres)
    {
        _bulletins = new BulletinRepository(database);
        _evaluations = new EvaluationRepository(database);
        _inscriptions = new EnrollmentRepository(database);
        _personnel = new StaffRepository(database);
        _referentiel = new ReferentielRepository(database);
        _planning = new PlanningRepository(database);
    }

    public List<BulletinResume> ListBulletins(int? idClasse = null, int? idPeriode = null)
    {
        try { return _bulletins.ListResumes(idClasse, idPeriode); }
        catch (Exception ex)
        {
            Logger.Error("Liste des bulletins", ex);
            return new List<BulletinResume>();
        }
    }

    public List<BulletinLigne> ListLignes(int idBulletin)
    {
        try { return _bulletins.ListLignes(idBulletin); }
        catch (Exception ex)
        {
            Logger.Error("Détail d’un bulletin", ex);
            return new List<BulletinLigne>();
        }
    }

    /// <summary>Génère (ou régénère) les bulletins d'une classe pour une période.</summary>
    public Result<int> GenererBulletins(int idClasse, int idPeriode, string codeUtr)
    {
        try
        {
            var classe = _referentiel.GetClasse(idClasse);
            if (classe is null)
                return Result<int>.Fail("Classe introuvable.", ErrorCodes.NotFound);
            var periode = _evaluations.GetPeriode(idPeriode);
            if (periode is null)
                return Result<int>.Fail("Période introuvable.", ErrorCodes.NotFound);
            if (periode.Cloturee == true)
                return Result<int>.Fail("Période clôturée : rouvrez-la pour régénérer les bulletins.", ErrorCodes.BusinessRule);

            var inscrits = _inscriptions.ListByClasse(idClasse);
            if (inscrits.Count == 0)
                return Result<int>.Fail($"Aucun inscrit dans la classe « {classe.Libelle} ».", ErrorCodes.BusinessRule);

            var moyennes = _evaluations.ListMoyennesMatiere(idClasse, idPeriode);
            var programmes = _personnel.ListByClasse(idClasse);
            if (programmes.Count == 0)
                return Result<int>.Fail($"Aucune matière programmée pour la classe « {classe.Libelle} ».", ErrorCodes.BusinessRule);
            var grille = _bulletins.ListMentions();

            var moyennesParInscrit = moyennes
                .Where(m => m.IdInscription.HasValue && !string.IsNullOrWhiteSpace(m.CodeMatiere))
                .GroupBy(m => m.IdInscription!.Value)
                .ToDictionary(g => g.Key, g => g.ToDictionary(
                    m => m.CodeMatiere!,
                    m => m,
                    StringComparer.OrdinalIgnoreCase));

            using var tx = Db.BeginTransaction();
            // Idempotence : suppression ciblée des bulletins existants (lignes puis bulletins).
            foreach (var idBulletin in _bulletins.ListIdsByClassePeriode(idClasse, idPeriode))
            {
                _bulletins.DeleteLignesByBulletin(idBulletin);
                _bulletins.DeleteBulletin(idBulletin);
            }

            var bulletinIds = new Dictionary<int, int>();
            var moyennesGenerales = new List<(int Id, double? Valeur)>();
            foreach (var inscrit in inscrits)
            {
                var idInscription = inscrit.IdInscription!.Value;
                moyennesParInscrit.TryGetValue(idInscription, out var moyennesEtudiant);

                double totalPoints = 0;
                double totalCoef = 0;
                var lignes = new List<BulletinLigne>();
                foreach (var programme in programmes)
                {
                    var codeMatiere = programme.CodeMatiere ?? string.Empty;
                    MoyenneMatiereRow? moyenne = null;
                    moyennesEtudiant?.TryGetValue(codeMatiere, out moyenne);
                    var coef = programme.Coefficient ?? 1d;
                    double? points = moyenne?.MoyenneMat.HasValue == true ? moyenne.MoyenneMat!.Value * coef : null;
                    if (points.HasValue)
                    {
                        totalPoints += points.Value;
                        totalCoef += coef;
                    }
                    lignes.Add(new BulletinLigne
                    {
                        CodeMatiere = codeMatiere,
                        MoyenneMat = moyenne?.MoyenneMat,
                        Coefficient = coef,
                        Points = points,
                        IdFormateur = moyenne?.IdFormateur ?? programme.IdFormateur
                    });
                }

                double? moyenneGenerale = totalCoef > 0 ? totalPoints / totalCoef : null;
                var mention = MentionHelper.Trouver(grille, moyenneGenerale);
                var bulletin = new Bulletin
                {
                    IdInscription = idInscription,
                    IdPeriode = idPeriode,
                    Moyenne = moyenneGenerale,
                    TotalPoints = totalPoints,
                    TotalCoef = totalCoef,
                    NbAbsence = _planning.SumHeuresAbsence(idInscription),
                    Appreciation = MentionHelper.AppreciationPour(mention?.Mention, mention?.Admis),
                    Decision = mention?.Admis == false ? "AJOURNÉ" : "ADMIS",
                    DateEdition = DateTime.Now
                };
                var idBulletin = _bulletins.InsertBulletin(bulletin);
                bulletinIds[idInscription] = idBulletin;
                moyennesGenerales.Add((idBulletin, moyenneGenerale));
                foreach (var ligne in lignes)
                {
                    ligne.IdBulletin = idBulletin;
                    _bulletins.InsertLigne(ligne);
                }
            }

            // Rangs, effectif, moyenne de classe.
            var rangs = MentionHelper.RangsCompetition(moyennesGenerales);
            var valeursClassees = moyennesGenerales.Where(m => m.Valeur.HasValue).Select(m => m.Valeur!.Value).ToList();
            double? moyClasse = valeursClassees.Count > 0 ? valeursClassees.Average() : null;
            foreach (var bulletinId in bulletinIds.Values)
            {
                _bulletins.UpdateRang(new Bulletin
                {
                    IdBulletin = bulletinId,
                    Rang = rangs.TryGetValue(bulletinId, out var rang) && rang > 0 ? rang : null,
                    Effectif = inscrits.Count,
                    MoyClasse = moyClasse
                });
            }

            // Min / max / rang par matière.
            CalculerStatsMatieres(bulletinIds.Values.ToList(), programmes);

            tx.Complete();
            Journal.LogOperation(codeUtr, "GENERATION_BULLETINS", Tables.Bulletin, null,
                $"Classe « {classe.Libelle} » × période « {periode.Libelle} » : {inscrits.Count} bulletin(s).");
            return Result<int>.Ok(inscrits.Count, $"{inscrits.Count} bulletin(s) généré(s) pour « {classe.Libelle} ».");
        }
        catch (Exception ex) { return Failure<int>("Génération des bulletins", ex); }
    }

    /// <summary>Supprime explicitement les bulletins d'une classe pour une période.</summary>
    public Result SupprimerBulletins(int idClasse, int idPeriode, string codeUtr)
    {
        try
        {
            using var tx = Db.BeginTransaction();
            var ids = _bulletins.ListIdsByClassePeriode(idClasse, idPeriode);
            foreach (var id in ids)
            {
                _bulletins.DeleteLignesByBulletin(id);
                _bulletins.DeleteBulletin(id);
            }
            tx.Complete();
            Journal.LogOperation(codeUtr, "SUPPRESSION_BULLETINS", Tables.Bulletin, null,
                $"Classe {idClasse} × période {idPeriode} : {ids.Count} bulletin(s) supprimé(s).");
            return Result.Ok($"{ids.Count} bulletin(s) supprimé(s).");
        }
        catch (Exception ex) { return Failure("Suppression des bulletins", ex); }
    }

    private void CalculerStatsMatieres(List<int> bulletinIds, List<ProgrammeDetail> programmes)
    {
        var lignesParMatiere = new Dictionary<string, List<(int IdLigne, double? Moyenne)>>(StringComparer.OrdinalIgnoreCase);
        foreach (var idBulletin in bulletinIds)
        {
            foreach (var ligne in _bulletins.ListLignes(idBulletin))
            {
                if (string.IsNullOrWhiteSpace(ligne.CodeMatiere) || !ligne.IdLigne.HasValue) continue;
                if (!lignesParMatiere.TryGetValue(ligne.CodeMatiere!, out var liste))
                {
                    liste = new List<(int, double?)>();
                    lignesParMatiere[ligne.CodeMatiere!] = liste;
                }
                liste.Add((ligne.IdLigne.Value, ligne.MoyenneMat));
            }
        }
        foreach (var entree in lignesParMatiere)
        {
            var valeurs = entree.Value.Where(l => l.Moyenne.HasValue).Select(l => l.Moyenne!.Value).ToList();
            double? min = valeurs.Count > 0 ? valeurs.Min() : null;
            double? max = valeurs.Count > 0 ? valeurs.Max() : null;
            var rangs = MentionHelper.RangsCompetition(
                entree.Value.Select(l => (l.IdLigne, l.Moyenne)).ToList());
            foreach (var ligne in entree.Value)
            {
                _bulletins.UpdateLigneStats(new BulletinLigne
                {
                    IdLigne = ligne.IdLigne,
                    RangMat = rangs.TryGetValue(ligne.IdLigne, out var rang) && rang > 0 ? rang : null,
                    MoyMin = min,
                    MoyMax = max
                });
            }
        }
    }
}
