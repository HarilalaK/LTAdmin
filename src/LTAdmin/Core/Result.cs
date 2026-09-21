namespace LTAdmin.Core;

/// <summary>
/// Codes d'erreur stables utilisés par les services. Ils permettent aux écrans
/// d'afficher des messages adaptés sans analyser le texte des exceptions.
/// </summary>
public static class ErrorCodes
{
    public const string Validation = "VALIDATION";
    public const string BusinessRule = "GESTION";
    public const string NotFound = "INTROUVABLE";
    public const string UniqueViolation = "DOUBLON";
    public const string ForeignKeyViolation = "LIAISON";
    public const string RequiredField = "REQUIS";
    public const string DataTooLong = "TROP_LONG";
    public const string NumericOverflow = "DEPASSEMENT";
    public const string Locked = "VERROUILLE";
    public const string Authentication = "AUTHENTIFICATION";
    public const string Authorization = "HABILITATION";
    public const string Technical = "TECHNIQUE";
}

/// <summary>
/// Résultat d'une opération de service, sans valeur de retour.
/// Un échec contient toujours un message en français affichable à l'utilisateur.
/// </summary>
public class Result
{
    public bool IsSuccess { get; protected init; }
    public bool IsFailure => !IsSuccess;
    public string Message { get; protected init; } = string.Empty;
    public string? Code { get; protected init; }
    public IReadOnlyList<string> Errors { get; protected init; } = Array.Empty<string>();

    public static Result Ok(string message = "")
        => new() { IsSuccess = true, Message = message };

    public static Result Fail(string message, string? code = null, IEnumerable<string>? errors = null)
        => new()
        {
            IsSuccess = false,
            Message = message,
            Code = code ?? ErrorCodes.BusinessRule,
            Errors = errors is null ? Array.Empty<string>() : errors.ToArray()
        };

    public string FullMessage()
    {
        if (Errors.Count == 0) return Message;
        if (string.IsNullOrWhiteSpace(Message)) return string.Join(Environment.NewLine, Errors);
        return Message + Environment.NewLine + string.Join(Environment.NewLine, Errors);
    }
}

/// <summary>
/// Résultat d'une opération de service avec valeur de retour.
/// </summary>
/// <typeparam name="T">Type de la valeur produite en cas de succès.</typeparam>
public sealed class Result<T> : Result
{
    public T? Value { get; private init; }

    public static Result<T> Ok(T value, string message = "")
        => new() { IsSuccess = true, Value = value, Message = message };

    public static new Result<T> Fail(string message, string? code = null, IEnumerable<string>? errors = null)
        => new()
        {
            IsSuccess = false,
            Value = default,
            Message = message,
            Code = code ?? ErrorCodes.BusinessRule,
            Errors = errors is null ? Array.Empty<string>() : errors.ToArray()
        };
}
