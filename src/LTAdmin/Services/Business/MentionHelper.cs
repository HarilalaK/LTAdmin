using LTAdmin.Models.Entities;

namespace LTAdmin.Services.Business;

/// <summary>
/// Helpers partagés par les bulletins et les résultats finaux :
/// lecture de la grille des mentions, appréciations par défaut et rangs.
/// </summary>
public static class MentionHelper
{
    /// <summary>
    /// Trouve la mention pour une moyenne selon la grille : intervalles [INF, SUP[,
    /// sauf la borne supérieure maximale (20) qui est incluse. La grille doit être
    /// triée par INF décroissant (ordre du dépôt).
    /// </summary>
    public static GrilleMention? Trouver(List<GrilleMention> grille, double? moyenne)
    {
        if (!moyenne.HasValue) return null;
        var value = moyenne.Value;
        GrilleMention? fallback = null;
        foreach (var ligne in grille)
        {
            var inf = ligne.Inf ?? 0d;
            var sup = ligne.Sup ?? 20d;
            fallback ??= ligne;
            if (value >= inf && (value < sup || sup >= 20d))
                return ligne;
        }
        return fallback;
    }

    /// <summary>Appréciation par défaut selon la mention (modifiable ensuite à la main).</summary>
    public static string AppreciationPour(string? mention, bool? admis)
    {
        if (string.IsNullOrWhiteSpace(mention))
            return admis == false ? "Résultats insuffisants. Doit fournir davantage d’efforts." : "Résultats en cours d’évaluation.";
        var text = mention.Trim().ToLowerInvariant();
        if (text.Contains("très bien") || text.Contains("tres bien")) return "Excellent travail. Félicitations !";
        if (text.Contains("bien")) return "Bon travail. Continuez ainsi.";
        if (text.Contains("assez bien")) return "Travail assez bien. Peut encore progresser.";
        if (text.Contains("passable")) return "Travail passable. Des efforts restent nécessaires.";
        return "Résultats insuffisants. Doit fournir davantage d’efforts.";
    }

    /// <summary>
    /// Classement « competition » (1, 2, 2, 4) sur des valeurs triées par ordre
    /// décroissant. Les valeurs nulles ne sont pas classées (rang 0).
    /// </summary>
    public static Dictionary<int, int> RangsCompetition(List<(int Id, double? Valeur)> valeurs)
    {
        var rangs = new Dictionary<int, int>();
        var classees = valeurs
            .Where(v => v.Valeur.HasValue)
            .OrderByDescending(v => v.Valeur!.Value)
            .ToList();
        var rang = 0;
        var position = 0;
        double? precedent = null;
        foreach (var item in classees)
        {
            position++;
            if (!precedent.HasValue || Math.Abs(item.Valeur!.Value - precedent.Value) > 0.0001)
                rang = position;
            rangs[item.Id] = rang;
            precedent = item.Valeur;
        }
        foreach (var item in valeurs.Where(v => !v.Valeur.HasValue))
            rangs[item.Id] = 0;
        return rangs;
    }
}
