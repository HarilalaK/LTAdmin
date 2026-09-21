using LTAdmin.Models;
using LTAdmin.Services;
using LTAdmin.Services.Infrastructure;
using LTAdmin.UI;

namespace LTAdmin;

internal static class Program
{
    [STAThread]
    private static void Main(string[] args)
    {
        ApplicationConfiguration.Initialize();
        Application.SetUnhandledExceptionMode(UnhandledExceptionMode.CatchException);
        Application.ThreadException += (_, e) => ShowFatalError(e.Exception);
        AppDomain.CurrentDomain.UnhandledException += (_, e) =>
            ShowFatalError(e.ExceptionObject as Exception ?? new Exception(Convert.ToString(e.ExceptionObject)));

        var databasePath = DatabaseLocator.Find(args.FirstOrDefault());
        if (databasePath is null)
        {
            using var picker = new OpenFileDialog
            {
                Title = "Sélectionner la base Access LTA",
                Filter = "Base de données Access (*.accdb;*.mdb)|*.accdb;*.mdb|Tous les fichiers (*.*)|*.*",
                CheckFileExists = true
            };
            if (picker.ShowDialog() != DialogResult.OK) return;
            databasePath = picker.FileName;
        }

        try
        {
            using var app = new AppComposition(databasePath);
            app.Database.Open();
            app.Logger.Info("Démarrage de LTAdmin sur " + databasePath);
            while (true)
            {
                UserSession? session;
                using (var login = new LoginForm(app))
                {
                    if (login.ShowDialog() != DialogResult.OK || login.Session is null)
                        return;
                    session = login.Session;
                }

                using var main = new MainForm(app, session);
                Application.Run(main);
                if (!main.LogoutRequested)
                    return;
            }
        }
        catch (Exception ex)
        {
            ShowFatalError(ex, databasePath);
        }
    }

    private static void ShowFatalError(Exception exception, string? databasePath = null)
    {
        var path = string.IsNullOrWhiteSpace(databasePath) ? "" : $"\n\nFichier : {databasePath}";
        MessageBox.Show(
            "LTAdmin ne peut pas démarrer.\n\n" + exception.Message + path +
            "\n\nVérifiez que Microsoft Access Database Engine (ACE) est installé avec la même architecture que LTAdmin.",
            "LTAdmin — Erreur de démarrage", MessageBoxButtons.OK, MessageBoxIcon.Error);
    }
}
