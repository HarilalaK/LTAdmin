using LTAdmin.Data;
using LTAdmin.Repositories;
using LTAdmin.Services.Auth;
using LTAdmin.Services.Business;
using LTAdmin.Services.Infrastructure;
using LTAdmin.Services.Logging;
using LTAdmin.Services.Referentiel;
using LTAdmin.Services.Reports;
using LTAdmin.Services.Statistics;

namespace LTAdmin.Services;

/// <summary>
/// Racine de composition de l'application : construit une fois la connexion
/// Access, les dépôts et les services, puis les expose aux écrans.
/// Les écrans reçoivent cette instance et appellent les services métier ;
/// ils ne construisent ni requêtes SQL ni règles de gestion.
/// </summary>
public sealed class AppComposition : IDisposable
{
    private bool _disposed;

    public AppComposition(string databasePath)
    {
        Database = new AccessDatabase(databasePath);
        Logger = new AppLogger();
        Journal = new JournalService(Database, Logger);
        Parametres = new ParametreService(Database, Journal, Logger);
        Auth = new AuthenticationService(Database, Journal, Logger);

        Admin = new AdminRepository(Database);
        Referentiel = new ReferentielRepository(Database);
        Tables = new DatabaseRepository(Database);

        Etudiants = new StudentService(Database, Logger, Journal, Parametres);
        Inscriptions = new EnrollmentService(Database, Logger, Journal, Parametres);
        Evaluations = new EvaluationService(Database, Logger, Journal, Parametres);
        Notes = new GradeService(Database, Logger, Journal, Parametres);
        Bulletins = new ReportCardService(Database, Logger, Journal, Parametres);
        Examens = new ExamService(Database, Logger, Journal, Parametres);
        EmploisDuTemps = new TimetableService(Database, Logger, Journal, Parametres);
        Absences = new AttendanceService(Database, Logger, Journal, Parametres);
        Ecolage = new PaymentService(Database, Logger, Journal, Parametres);
        Paie = new PayrollService(Database, Logger, Journal, Parametres);

        Statistiques = new StatisticsService(Database, Logger, Journal, Parametres);
        Etats = new ReportService(Database, Logger, Journal, Parametres);
        Sauvegardes = new BackupService(Database, Logger, Journal, Parametres);
    }

    public AccessDatabase Database { get; }
    public AppLogger Logger { get; }
    public JournalService Journal { get; }
    public ParametreService Parametres { get; }
    public AuthenticationService Auth { get; }

    public AdminRepository Admin { get; }
    public ReferentielRepository Referentiel { get; }
    public DatabaseRepository Tables { get; }

    public StudentService Etudiants { get; }
    public EnrollmentService Inscriptions { get; }
    public EvaluationService Evaluations { get; }
    public GradeService Notes { get; }
    public ReportCardService Bulletins { get; }
    public ExamService Examens { get; }
    public TimetableService EmploisDuTemps { get; }
    public AttendanceService Absences { get; }
    public PaymentService Ecolage { get; }
    public PayrollService Paie { get; }

    public StatisticsService Statistiques { get; }
    public ReportService Etats { get; }
    public BackupService Sauvegardes { get; }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        Database.Dispose();
    }
}
