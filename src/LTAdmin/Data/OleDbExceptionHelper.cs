using System.Data.OleDb;
using LTAdmin.Core;

namespace LTAdmin.Data;

/// <summary>
/// Erreur de base de données interprétée : code stable + message en français.
/// </summary>
public sealed record DatabaseError(string Code, string Message, int NativeError);

/// <summary>
/// Traduit les erreurs du moteur ACE (numéros natifs + mots-clés FR/EN, car les
/// messages dépendent de la langue d'Office) en erreurs métier compréhensibles.
/// Référence des codes : erreurs du moteur Jet/ACE (3022 doublon, 3201/3200
/// intégrité référentielle, 3314/3058 null interdit, 3163 champ trop petit...).
/// </summary>
public static class OleDbExceptionHelper
{
    public static DatabaseError Interpret(Exception exception)
    {
        var oleDb = FindOleDbException(exception);
        if (oleDb is null)
            return new DatabaseError(ErrorCodes.Technical, exception.Message, 0);

        foreach (OleDbError error in oleDb.Errors)
        {
            var mapped = MapNativeError(error.NativeError, error.Message);
            if (mapped is not null) return mapped;
        }

        var keywords = MapByKeywords(oleDb.Message);
        if (keywords is not null) return keywords;

        return new DatabaseError(ErrorCodes.Technical, "Opération sur la base de données impossible : " + oleDb.Message, 0);
    }

    public static bool IsUniqueViolation(Exception exception)
        => Interpret(exception).Code == ErrorCodes.UniqueViolation;

    public static bool IsForeignKeyViolation(Exception exception)
        => Interpret(exception).Code == ErrorCodes.ForeignKeyViolation;

    private static OleDbException? FindOleDbException(Exception exception)
    {
        var current = exception;
        while (current is not null)
        {
            if (current is OleDbException oleDb) return oleDb;
            current = current.InnerException;
        }
        return null;
    }

    private static DatabaseError? MapNativeError(int nativeError, string message)
    {
        return nativeError switch
        {
            // Violation d'index unique / clé primaire (doublon).
            3022 => new DatabaseError(ErrorCodes.UniqueViolation,
                "Doublon interdit : un enregistrement avec les mêmes valeurs existe déjà.", nativeError),
            // Un enregistrement lié est requis (clé étrangère à l'ajout/modification).
            3201 => new DatabaseError(ErrorCodes.ForeignKeyViolation,
                "Enregistrement lié introuvable : vérifiez les liens (classe, étudiant, matière…).", nativeError),
            // Suppression/modification refusée car des enregistrements liés existent.
            3200 or 3202 => new DatabaseError(ErrorCodes.ForeignKeyViolation,
                "Suppression impossible : cet enregistrement est utilisé par d’autres données.", nativeError),
            // Un champ requis contient Null.
            3314 or 3058 => new DatabaseError(ErrorCodes.RequiredField,
                "Une valeur obligatoire est manquante.", nativeError),
            // Champ trop petit pour la valeur (texte trop long).
            3163 => new DatabaseError(ErrorCodes.DataTooLong,
                "Texte trop long pour l’un des champs.", nativeError),
            // Dépassement numérique.
            3349 or 6 => new DatabaseError(ErrorCodes.NumericOverflow,
                "Valeur numérique hors limites pour l’un des champs.", nativeError),
            // Aucun enregistrement courant.
            3021 => new DatabaseError(ErrorCodes.NotFound,
                "Enregistrement introuvable : il a peut-être été supprimé.", nativeError),
            // Données modifiées entre-temps / verrous.
            3197 or 3260 or 3261 or 3262 => new DatabaseError(ErrorCodes.Locked,
                "Données verrouillées ou modifiées par un autre utilisateur. Réessayez.", nativeError),
            // Fichier verrouillé / accès exclusif / réseau.
            3043 or 3050 or 3051 => new DatabaseError(ErrorCodes.Locked,
                "La base de données est verrouillée ou inaccessible (fichier ouvert en exclusif, droits insuffisants).", nativeError),
            _ => null
        };
    }

    private static DatabaseError? MapByKeywords(string message)
    {
        var text = message ?? string.Empty;
        if (ContainsAny(text, "doublon", "duplicate", "doubles", "unique", "clé primaire", "primary key"))
            return new DatabaseError(ErrorCodes.UniqueViolation,
                "Doublon interdit : un enregistrement avec les mêmes valeurs existe déjà.", 0);
        if (ContainsAny(text, "related record", "enregistrement lié", "référentielle", "referential", "intégrité", "integrity"))
            return new DatabaseError(ErrorCodes.ForeignKeyViolation,
                "Opération refusée par une règle de liaison entre les tables.", 0);
        if (ContainsAny(text, "trop long", "too small", "too long"))
            return new DatabaseError(ErrorCodes.DataTooLong, "Texte trop long pour l’un des champs.", 0);
        if (ContainsAny(text, "Null"))
            return new DatabaseError(ErrorCodes.RequiredField, "Une valeur obligatoire est manquante.", 0);
        if (ContainsAny(text, "verrou", "lock", "exclusif", "exclusive", "en cours d’utilisation", "already in use"))
            return new DatabaseError(ErrorCodes.Locked, "La base de données est verrouillée. Réessayez dans un instant.", 0);
        return null;
    }

    private static bool ContainsAny(string text, params string[] keywords)
    {
        foreach (var keyword in keywords)
            if (text.Contains(keyword, StringComparison.OrdinalIgnoreCase)) return true;
        return false;
    }
}
