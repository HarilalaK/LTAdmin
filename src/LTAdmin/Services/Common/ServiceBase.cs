using LTAdmin.Core;
using LTAdmin.Data;
using LTAdmin.Services.Logging;
using LTAdmin.Services.Referentiel;
using LTAdmin.Services.Validation;

namespace LTAdmin.Services.Common;

/// <summary>
/// Base des services métier : accès aux dépôts via la base, journalisation,
/// paramètres de gestion et traduction uniforme des erreurs ACE.
/// Les écrans ne contiennent aucune règle métier : ils appellent les services
/// et affichent les <see cref="Result"/> retournés.
/// </summary>
public abstract class ServiceBase
{
    protected ServiceBase(AccessDatabase database, AppLogger logger, JournalService journal, ParametreService parametres)
    {
        Db = database;
        Logger = logger;
        Journal = journal;
        Parametres = parametres;
    }

    protected AccessDatabase Db { get; }
    protected AppLogger Logger { get; }
    protected JournalService Journal { get; }
    protected ParametreService Parametres { get; }

    protected Result Failure(string operation, Exception exception)
    {
        var error = OleDbExceptionHelper.Interpret(exception);
        Logger.Error(operation, exception);
        return Result.Fail(error.Message, error.Code);
    }

    protected Result<T> Failure<T>(string operation, Exception exception)
    {
        var error = OleDbExceptionHelper.Interpret(exception);
        Logger.Error(operation, exception);
        return Result<T>.Fail(error.Message, error.Code);
    }

    protected static Result Invalid(ValidationResult validation)
        => Result.Fail("Vérifiez la saisie :", ErrorCodes.Validation, validation.Errors);

    protected static Result<T> Invalid<T>(ValidationResult validation)
        => Result<T>.Fail("Vérifiez la saisie :", ErrorCodes.Validation, validation.Errors);
}
