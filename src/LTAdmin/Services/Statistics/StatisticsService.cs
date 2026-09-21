using System.Data;
using LTAdmin.Data;
using LTAdmin.Models.Entities;
using LTAdmin.Repositories;
using LTAdmin.Services.Business;
using LTAdmin.Services.Common;
using LTAdmin.Services.Logging;
using LTAdmin.Services.Referentiel;

namespace LTAdmin.Services.Statistics;

/// <summary>
/// Statistiques de pilotage : effectifs, résultats, assiduité, finances,
/// planning. Tous les indicateurs sont calculés depuis les tables et les
/// requêtes existantes, sans modifier la base ni simuler de données.
/// </summary>
public sealed class StatisticsService : ServiceBase
{
    private readonly AdminRepository _admin;
    private readonly ReferentielRepository _referentiel;
    private readonly StudentRepository _etudiants;
    private readonly EnrollmentRepository _inscriptions;
    private readonly StaffRepository _personnel;
    private readonly EvaluationRepository _evaluations;
    private readonly BulletinRepository _bulletins;

    public StatisticsService(AccessDatabase database, AppLogger logger, JournalService journal, ParametreService parametres)
        : base(database, logger, journal, parametres)
    {
        _admin = new AdminRepository(database);
        _referentiel = new ReferentielRepository(database);
        _etudiants = new StudentRepository(database);
        _inscriptions = new EnrollmentRepository(database);
        _personnel = new StaffRepository(database);
        _evaluations = new EvaluationRepository(database);
        _bulletins = new BulletinRepository(database);
    }

    public AnneeScolaire? GetAnneeActive()
    {
        try { return _admin.GetAnneeActive(); }
        catch (Exception ex)
        {
            Logger.Error("Année scolaire active", ex);
            return null;
        }
    }

    /// <summary>Tableau de bord : indicateurs globaux de l'année active.</summary>
    public DashboardStat GetDashboard()
    {
        var stat = new DashboardStat();
        try
        {
            var annee = _admin.GetAnneeActive();
            stat.AnneeLibelle = annee?.Libelle;
            stat.NbEtudiants = _etudiants.Count();
            stat.NbFormateurs = _personnel.CountFormateurs();
            if (annee?.IdAnnee is null)
            {
                stat.NbInscriptions = ScalarInt("inscriptions totales",
                    $"SELECT COUNT(*) FROM {Q(Tables.Inscription)}");
                var recouvrement = GetRecouvrement(null);
                stat.TotalDu = recouvrement.NetDu;
                stat.TotalPaye = recouvrement.TotalPaye;
            }
            else
            {
                stat.NbInscriptions = _inscriptions.CountByAnnee(annee.IdAnnee.Value);
                stat.NbClasses = _referentiel.ListClasses(annee.IdAnnee.Value).Count;
                var recouvrement = GetRecouvrement(annee.IdAnnee.Value);
                stat.TotalDu = recouvrement.NetDu;
                stat.TotalPaye = recouvrement.TotalPaye;
            }
            stat.NbEcheancesEchues = ListEcheancesEchues().Count;
            stat.NbAlertesAbsence = ListEtudiantsAuDessusSeuil(null).Count;
        }
        catch (Exception ex) { Logger.Error("Indicateurs du tableau de bord", ex); }
        return stat;
    }

    // ----- Effectifs et scolarité -----

    public List<EffectifClasseStat> GetEffectifs(int idAnnee)
    {
        var result = new List<EffectifClasseStat>();
        try
        {
            foreach (var classe in _referentiel.ListClassesDetail(idAnnee))
            {
                var inscrits = classe.IdClasse.HasValue ? _inscriptions.CountByClasse(classe.IdClasse.Value) : 0;
                result.Add(new EffectifClasseStat
                {
                    IdClasse = classe.IdClasse,
                    Classe = classe.Libelle,
                    Filiere = classe.Filiere,
                    Niveau = classe.Niveau,
                    Inscrits = inscrits,
                    EffectifMax = classe.EffectifMax,
                    TauxRemplissage = classe.EffectifMax is > 0
                        ? Math.Round(inscrits * 100d / classe.EffectifMax.Value, 1) : null
                });
            }
        }
        catch (Exception ex) { Logger.Error("Effectifs par classe", ex); }
        return result;
    }

    public List<RepartitionStat> GetRepartitionSexe(int idAnnee)
    {
        var result = new List<RepartitionStat>();
        try
        {
            var table = Db.Query(
                $"SELECT E.{Q("SEXE")} AS SEXE, COUNT(*) AS NB " +
                $"FROM (({Q(Tables.Inscription)} AS I " +
                $"INNER JOIN {Q(Tables.Etudiant)} AS E ON I.{Q("ID_ETUDIANT")} = E.{Q("ID_ETUDIANT")}) " +
                $"INNER JOIN {Q(Tables.Classe)} AS C ON I.{Q("ID_CLASSE")} = C.{Q("ID_CLASSE")}) " +
                $"WHERE C.{Q("ID_ANNEE")} = ? GROUP BY E.{Q("SEXE")}",
                new[] { AccessDatabase.Parameter(idAnnee) });
            foreach (DataRow row in table.Rows)
            {
                var sexe = DataRowMapper.GetString(row, "SEXE");
                result.Add(new RepartitionStat
                {
                    Libelle = string.Equals(sexe, "M", StringComparison.OrdinalIgnoreCase) ? "Garçons"
                        : string.Equals(sexe, "F", StringComparison.OrdinalIgnoreCase) ? "Filles" : "Non renseigné",
                    Nombre = DataRowMapper.GetInt32(row, "NB", 0)
                });
            }
        }
        catch (Exception ex) { Logger.Error("Répartition par sexe", ex); }
        return result;
    }

    public int CountRedoublants(int idAnnee)
        => ScalarInt("redoublants",
            $"SELECT COUNT(*) FROM {Q(Tables.Inscription)} AS I " +
            $"INNER JOIN {Q(Tables.Classe)} AS C ON I.{Q("ID_CLASSE")} = C.{Q("ID_CLASSE")} " +
            $"WHERE C.{Q("ID_ANNEE")} = ? AND I.{Q("REDOUBLANT")} = ?",
            idAnnee, true);

    public int CountSorties(int idAnnee)
        => ScalarInt("sorties",
            $"SELECT COUNT(*) FROM {Q(Tables.Inscription)} AS I " +
            $"INNER JOIN {Q(Tables.Classe)} AS C ON I.{Q("ID_CLASSE")} = C.{Q("ID_CLASSE")} " +
            $"WHERE C.{Q("ID_ANNEE")} = ? AND I.{Q("DATE_SORTIE")} IS NOT NULL",
            idAnnee);

    // ----- Résultats pédagogiques -----

    public List<AvancementSaisieStat> GetAvancementSaisie(int? idClasse = null, int? idPeriode = null)
    {
        var result = new List<AvancementSaisieStat>();
        try
        {
            foreach (var evaluation in _evaluations.ListEvaluations(idPeriode, idClasse))
            {
                var attendues = evaluation.IdClasse.HasValue
                    ? _inscriptions.CountByClasse(evaluation.IdClasse.Value) : 0;
                var saisies = evaluation.IdEvaluation.HasValue
                    ? _evaluations.CountNotesByEvaluation(evaluation.IdEvaluation.Value) : 0;
                result.Add(new AvancementSaisieStat
                {
                    IdEvaluation = evaluation.IdEvaluation,
                    Intitule = evaluation.Intitule,
                    Matiere = evaluation.Matiere,
                    Classe = evaluation.Classe,
                    Attendues = attendues,
                    Saisies = saisies
                });
            }
        }
        catch (Exception ex) { Logger.Error("Avancement de la saisie", ex); }
        return result;
    }

    public ClasseResultatStat GetResultatsClasse(int idClasse, int idPeriode)
    {
        var stat = new ClasseResultatStat();
        try
        {
            var bulletins = _bulletins.ListByClassePeriode(idClasse, idPeriode);
            stat.Effectif = bulletins.Count;
            var moyennes = bulletins
                .Where(b => b.Moyenne.HasValue)
                .Select(b => b.Moyenne!.Value)
                .ToList();
            stat.AvecMoyenne = moyennes.Count;
            if (moyennes.Count > 0)
            {
                stat.Moyenne = Math.Round(moyennes.Average(), 2);
                stat.Min = moyennes.Min();
                stat.Max = moyennes.Max();
            }
        }
        catch (Exception ex) { Logger.Error("Résultats d’une classe", ex); }
        return stat;
    }

    public List<MentionStat> GetRepartitionMentions(int idClasse, int idPeriode)
    {
        var result = new List<MentionStat>();
        try
        {
            var grille = _bulletins.ListMentions();
            var groupes = new Dictionary<string, MentionStat>(StringComparer.OrdinalIgnoreCase);
            foreach (var bulletin in _bulletins.ListByClassePeriode(idClasse, idPeriode))
            {
                var mention = MentionHelper.Trouver(grille, bulletin.Moyenne);
                var libelle = mention?.Mention ?? "Sans mention";
                if (!groupes.TryGetValue(libelle, out var stat))
                {
                    stat = new MentionStat { Mention = libelle, Admis = mention?.Admis ?? true };
                    groupes[libelle] = stat;
                }
                stat.Nombre++;
            }
            result.AddRange(groupes.Values.OrderByDescending(g => g.Nombre));
        }
        catch (Exception ex) { Logger.Error("Répartition des mentions", ex); }
        return result;
    }

    // ----- Assiduité -----

    public List<AbsenteismeClasseStat> GetAbsenteismeParClasse(int? idAnnee = null)
    {
        var result = new List<AbsenteismeClasseStat>();
        try
        {
            var sql = $"SELECT C.{Q("LIBELLE")} AS CLASSE, A.{Q("NB_HEURES")} AS HEURES, " +
                      $"A.{Q("JUSTIFIEE")} AS JUSTIFIEE, I.{Q("ID_INSCRIPTION")} AS ID_INSCRIPTION " +
                      $"FROM (({Q(Tables.Absence)} AS A " +
                      $"INNER JOIN {Q(Tables.Inscription)} AS I ON A.{Q("ID_INSCRIPTION")} = I.{Q("ID_INSCRIPTION")}) " +
                      $"INNER JOIN {Q(Tables.Classe)} AS C ON I.{Q("ID_CLASSE")} = C.{Q("ID_CLASSE")})";
            DataTable table = idAnnee.HasValue
                ? Db.Query(sql + $" WHERE C.{Q("ID_ANNEE")} = ?", new[] { AccessDatabase.Parameter(idAnnee.Value) })
                : Db.Query(sql);
            var groupes = new Dictionary<string, (double Heures, double Justifiees, HashSet<int> Inscrits)>(StringComparer.OrdinalIgnoreCase);
            foreach (DataRow row in table.Rows)
            {
                var classe = DataRowMapper.GetString(row, "CLASSE") ?? "—";
                if (!groupes.TryGetValue(classe, out var cumul))
                {
                    cumul = (0d, 0d, new HashSet<int>());
                    groupes[classe] = cumul;
                }
                var heures = DataRowMapper.GetDouble(row, "HEURES") ?? 0d;
                cumul.Heures += heures;
                if (DataRowMapper.GetBoolean(row, "JUSTIFIEE", false)) cumul.Justifiees += heures;
                var id = DataRowMapper.GetInt32(row, "ID_INSCRIPTION");
                if (id.HasValue) cumul.Inscrits.Add(id.Value);
                groupes[classe] = cumul;
            }
            foreach (var entree in groupes.OrderBy(g => g.Key))
            {
                result.Add(new AbsenteismeClasseStat
                {
                    Classe = entree.Key,
                    HeuresAbsence = Math.Round(entree.Value.Heures, 1),
                    HeuresJustifiees = Math.Round(entree.Value.Justifiees, 1),
                    NbConcernes = entree.Value.Inscrits.Count
                });
            }
        }
        catch (Exception ex) { Logger.Error("Absentéisme par classe", ex); }
        return result;
    }

    public List<EtudiantSeuilStat> ListEtudiantsAuDessusSeuil(int? idAnnee)
    {
        var result = new List<EtudiantSeuilStat>();
        try
        {
            var seuil = Parametres.SeuilAbsence;
            var sql = $"SELECT E.{Q("MATRICULE")} AS MATRICULE, E.{Q("NOM")} AS NOM, E.{Q("PRENOM")} AS PRENOM, " +
                      $"C.{Q("LIBELLE")} AS CLASSE, A.{Q("NB_HEURES")} AS HEURES, I.{Q("ID_INSCRIPTION")} AS ID_INSCRIPTION " +
                      $"FROM ((({Q(Tables.Absence)} AS A " +
                      $"INNER JOIN {Q(Tables.Inscription)} AS I ON A.{Q("ID_INSCRIPTION")} = I.{Q("ID_INSCRIPTION")}) " +
                      $"INNER JOIN {Q(Tables.Etudiant)} AS E ON I.{Q("ID_ETUDIANT")} = E.{Q("ID_ETUDIANT")}) " +
                      $"INNER JOIN {Q(Tables.Classe)} AS C ON I.{Q("ID_CLASSE")} = C.{Q("ID_CLASSE")})";
            DataTable table = idAnnee.HasValue
                ? Db.Query(sql + $" WHERE C.{Q("ID_ANNEE")} = ?", new[] { AccessDatabase.Parameter(idAnnee.Value) })
                : Db.Query(sql);
            var cumuls = new Dictionary<int, (string? Mat, string? Nom, string? Prenom, string? Classe, double Heures)>();
            foreach (DataRow row in table.Rows)
            {
                var id = DataRowMapper.GetInt32(row, "ID_INSCRIPTION");
                if (!id.HasValue) continue;
                if (!cumuls.TryGetValue(id.Value, out var cumul))
                {
                    cumul = (DataRowMapper.GetString(row, "MATRICULE"), DataRowMapper.GetString(row, "NOM"),
                        DataRowMapper.GetString(row, "PRENOM"), DataRowMapper.GetString(row, "CLASSE"), 0d);
                }
                cumul.Heures += DataRowMapper.GetDouble(row, "HEURES") ?? 0d;
                cumuls[id.Value] = cumul;
            }
            foreach (var entree in cumuls.Values.Where(c => c.Heures >= seuil).OrderByDescending(c => c.Heures))
            {
                result.Add(new EtudiantSeuilStat
                {
                    Matricule = entree.Mat,
                    Nom = entree.Nom,
                    Prenom = entree.Prenom,
                    Classe = entree.Classe,
                    TotalHeures = Math.Round(entree.Heures, 1)
                });
            }
        }
        catch (Exception ex) { Logger.Error("Étudiants au-delà du seuil d’absence", ex); }
        return result;
    }

    // ----- Finances -----

    public RecouvrementStat GetRecouvrement(int? idAnnee)
    {
        var stat = new RecouvrementStat();
        try
        {
            var sql = $"SELECT ECH.{Q("ID_ECHEANCE")} AS ID_ECHEANCE, ECH.{Q("MONTANT_DU")} AS MONTANT_DU, ECH.{Q("REMISE")} AS REMISE, PAI.{Q("MONTANT")} AS PAYE " +
                      $"FROM (({Q(Tables.Echeancier)} AS ECH " +
                      $"INNER JOIN {Q(Tables.Inscription)} AS I ON ECH.{Q("ID_INSCRIPTION")} = I.{Q("ID_INSCRIPTION")}) " +
                      $"INNER JOIN {Q(Tables.Classe)} AS C ON I.{Q("ID_CLASSE")} = C.{Q("ID_CLASSE")}) " +
                      $"LEFT JOIN {Q(Tables.Paiement)} AS PAI ON PAI.{Q("ID_ECHEANCE")} = ECH.{Q("ID_ECHEANCE")}";
            DataTable table = idAnnee.HasValue
                ? Db.Query(sql + $" WHERE C.{Q("ID_ANNEE")} = ?", new[] { AccessDatabase.Parameter(idAnnee.Value) })
                : Db.Query(sql);
            var echeancesVues = new HashSet<int>();
            foreach (DataRow row in table.Rows)
            {
                // Le montant dû est compté une fois par échéance (la jointure des paiements duplique les lignes).
                var id = DataRowMapper.GetInt32(row, "ID_ECHEANCE");
                if (id.HasValue && echeancesVues.Add(id.Value))
                {
                    stat.TotalDuBrut += DataRowMapper.GetDecimal(row, "MONTANT_DU", 0m);
                    stat.TotalRemise += DataRowMapper.GetDecimal(row, "REMISE", 0m);
                }
                stat.TotalPaye += DataRowMapper.GetDecimal(row, "PAYE", 0m);
            }
        }
        catch (Exception ex) { Logger.Error("Recouvrement global", ex); }
        return stat;
    }

    public List<RecouvrementClasseStat> GetRecouvrementParClasse(int idAnnee)
    {
        var result = new List<RecouvrementClasseStat>();
        try
        {
            var table = Db.Query(
                $"SELECT C.{Q("LIBELLE")} AS CLASSE, ECH.{Q("ID_ECHEANCE")} AS ID_ECHEANCE, " +
                $"ECH.{Q("MONTANT_DU")} AS MONTANT_DU, ECH.{Q("REMISE")} AS REMISE, PAI.{Q("MONTANT")} AS PAYE " +
                $"FROM ((({Q(Tables.Echeancier)} AS ECH " +
                $"INNER JOIN {Q(Tables.Inscription)} AS I ON ECH.{Q("ID_INSCRIPTION")} = I.{Q("ID_INSCRIPTION")}) " +
                $"INNER JOIN {Q(Tables.Classe)} AS C ON I.{Q("ID_CLASSE")} = C.{Q("ID_CLASSE")}) " +
                $"LEFT JOIN {Q(Tables.Paiement)} AS PAI ON PAI.{Q("ID_ECHEANCE")} = ECH.{Q("ID_ECHEANCE")}) " +
                $"WHERE C.{Q("ID_ANNEE")} = ?",
                new[] { AccessDatabase.Parameter(idAnnee) });
            var groupes = new Dictionary<string, (decimal Du, decimal Paye, HashSet<int> Echeances)>(StringComparer.OrdinalIgnoreCase);
            foreach (DataRow row in table.Rows)
            {
                var classe = DataRowMapper.GetString(row, "CLASSE") ?? "—";
                if (!groupes.TryGetValue(classe, out var cumul))
                {
                    cumul = (0m, 0m, new HashSet<int>());
                    groupes[classe] = cumul;
                }
                var id = DataRowMapper.GetInt32(row, "ID_ECHEANCE");
                if (id.HasValue && cumul.Echeances.Add(id.Value))
                    cumul.Du += DataRowMapper.GetDecimal(row, "MONTANT_DU", 0m) - DataRowMapper.GetDecimal(row, "REMISE", 0m);
                cumul.Paye += DataRowMapper.GetDecimal(row, "PAYE", 0m);
                groupes[classe] = cumul;
            }
            foreach (var entree in groupes.OrderBy(g => g.Key))
            {
                result.Add(new RecouvrementClasseStat
                {
                    Classe = entree.Key,
                    TotalDu = entree.Value.Du,
                    TotalPaye = entree.Value.Paye
                });
            }
        }
        catch (Exception ex) { Logger.Error("Recouvrement par classe", ex); }
        return result;
    }

    public List<EcheanceRetardStat> ListEcheancesEchues()
    {
        var result = new List<EcheanceRetardStat>();
        try
        {
            var table = Db.Query(
                $"SELECT ECH.{Q("ID_ECHEANCE")} AS ID_ECHEANCE, ECH.{Q("LIBELLE")} AS LIBELLE, " +
                $"ECH.{Q("MONTANT_DU")} AS MONTANT_DU, ECH.{Q("REMISE")} AS REMISE, " +
                $"ECH.{Q("DATE_ECHEANCE")} AS DATE_ECHEANCE, E.{Q("MATRICULE")} AS MATRICULE, " +
                $"E.{Q("NOM")} AS NOM, E.{Q("PRENOM")} AS PRENOM, C.{Q("LIBELLE")} AS CLASSE, " +
                $"(SELECT SUM(PAI.{Q("MONTANT")}) FROM {Q(Tables.Paiement)} AS PAI " +
                $"WHERE PAI.{Q("ID_ECHEANCE")} = ECH.{Q("ID_ECHEANCE")}) AS TOTAL_PAYE " +
                $"FROM ((({Q(Tables.Echeancier)} AS ECH " +
                $"INNER JOIN {Q(Tables.Inscription)} AS I ON ECH.{Q("ID_INSCRIPTION")} = I.{Q("ID_INSCRIPTION")}) " +
                $"INNER JOIN {Q(Tables.Etudiant)} AS E ON I.{Q("ID_ETUDIANT")} = E.{Q("ID_ETUDIANT")}) " +
                $"INNER JOIN {Q(Tables.Classe)} AS C ON I.{Q("ID_CLASSE")} = C.{Q("ID_CLASSE")}) " +
                $"WHERE ECH.{Q("DATE_ECHEANCE")} < ? AND ECH.{Q("STATUT")} <> ? " +
                $"ORDER BY ECH.{Q("DATE_ECHEANCE")}",
                new[] { AccessDatabase.Parameter(DateTime.Today), AccessDatabase.Parameter(PaymentService.StatutSolde) });
            foreach (DataRow row in table.Rows)
            {
                var netDu = DataRowMapper.GetDecimal(row, "MONTANT_DU", 0m) - DataRowMapper.GetDecimal(row, "REMISE", 0m);
                var paye = DataRowMapper.GetDecimal(row, "TOTAL_PAYE", 0m);
                var echeance = DataRowMapper.GetDateTime(row, "DATE_ECHEANCE");
                result.Add(new EcheanceRetardStat
                {
                    IdEcheance = DataRowMapper.GetInt32(row, "ID_ECHEANCE"),
                    Matricule = DataRowMapper.GetString(row, "MATRICULE"),
                    Nom = DataRowMapper.GetString(row, "NOM"),
                    Prenom = DataRowMapper.GetString(row, "PRENOM"),
                    Classe = DataRowMapper.GetString(row, "CLASSE"),
                    Libelle = DataRowMapper.GetString(row, "LIBELLE"),
                    Reste = netDu - paye,
                    DateEcheance = echeance,
                    JoursRetard = echeance.HasValue ? Math.Max(0, (DateTime.Today - echeance.Value.Date).Days) : 0
                });
            }
        }
        catch (Exception ex) { Logger.Error("Échéances échues", ex); }
        return result;
    }

    public List<EncaissementModeStat> GetEncaissementsParMode(DateTime? debut = null, DateTime? fin = null)
    {
        var result = new List<EncaissementModeStat>();
        try
        {
            var sql = $"SELECT {Q("MODE_PAIE")} AS MODE, COUNT(*) AS NB, SUM({Q("MONTANT")}) AS TOTAL " +
                      $"FROM {Q(Tables.Paiement)}";
            var conditions = new List<string>();
            var parameters = new List<System.Data.OleDb.OleDbParameter>();
            if (debut.HasValue) { conditions.Add($"{Q("DATE_PAIEMENT")} >= ?"); parameters.Add(AccessDatabase.Parameter(debut.Value)); }
            if (fin.HasValue) { conditions.Add($"{Q("DATE_PAIEMENT")} < ?"); parameters.Add(AccessDatabase.Parameter(fin.Value.Date.AddDays(1))); }
            if (conditions.Count > 0) sql += " WHERE " + string.Join(" AND ", conditions);
            sql += $" GROUP BY {Q("MODE_PAIE")}";
            var table = Db.Query(sql, parameters);
            foreach (DataRow row in table.Rows)
            {
                result.Add(new EncaissementModeStat
                {
                    Mode = DataRowMapper.GetString(row, "MODE") ?? "Non précisé",
                    Nombre = DataRowMapper.GetInt32(row, "NB", 0),
                    Total = DataRowMapper.GetDecimal(row, "TOTAL", 0m)
                });
            }
        }
        catch (Exception ex) { Logger.Error("Encaissements par mode", ex); }
        return result;
    }

    // ----- Helpers -----

    private static string Q(string identifier) => AccessDatabase.QuoteIdentifier(identifier);

    private int ScalarInt(string operation, string sql, params object?[] values)
    {
        try
        {
            var parameters = values.Select(AccessDatabase.Parameter).ToArray();
            var value = Db.Scalar(sql, parameters);
            if (value is null) return 0;
            return Convert.ToInt32(value, System.Globalization.CultureInfo.InvariantCulture);
        }
        catch (Exception ex)
        {
            Logger.Error("Statistique (" + operation + ")", ex);
            return 0;
        }
    }
}
