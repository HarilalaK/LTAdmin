"""Helpers partagés par les bulletins et les résultats finaux.

Lecture de la grille des mentions, appréciations par défaut et rangs
« competition » (1, 2, 2, 4 ; non classés = 0).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ltadmin.models.entities import GrilleMention


def trouver(grille: List[GrilleMention], moyenne: Optional[float]) -> Optional[GrilleMention]:
    """Trouve la mention pour une moyenne : intervalles [INF, SUP[, sauf la
    borne supérieure maximale (20) qui est incluse. La grille doit être triée
    par INF décroissant (ordre du dépôt)."""
    if moyenne is None:
        return None
    value = moyenne
    fallback: Optional[GrilleMention] = None
    for ligne in grille:
        inf = ligne.inf if ligne.inf is not None else 0.0
        sup = ligne.sup if ligne.sup is not None else 20.0
        if fallback is None:
            fallback = ligne
        if value >= inf and (value < sup or sup >= 20.0):
            return ligne
    return fallback


def appreciation_pour(mention: Optional[str], admis: Optional[bool]) -> str:
    """Appréciation par défaut selon la mention (modifiable ensuite à la main)."""
    if not mention or not mention.strip():
        if admis is False:
            return "Résultats insuffisants. Doit fournir davantage d’efforts."
        return "Résultats en cours d’évaluation."
    text = mention.strip().lower()
    if "très bien" in text or "tres bien" in text:
        return "Excellent travail. Félicitations !"
    if "bien" in text:
        return "Bon travail. Continuez ainsi."
    if "assez bien" in text:
        return "Travail assez bien. Peut encore progresser."
    if "passable" in text:
        return "Travail passable. Des efforts restent nécessaires."
    return "Résultats insuffisants. Doit fournir davantage d’efforts."


def rangs_competition(valeurs: List[Tuple[int, Optional[float]]]) -> Dict[int, int]:
    """Classement « competition » (1, 2, 2, 4) sur des valeurs décroissantes.

    Les valeurs nulles ne sont pas classées (rang 0).
    """
    rangs: Dict[int, int] = {}
    classees = sorted(
        (item for item in valeurs if item[1] is not None),
        key=lambda item: item[1], reverse=True)
    rang = 0
    position = 0
    precedent: Optional[float] = None
    for identifiant, valeur in classees:
        position += 1
        if precedent is None or abs(valeur - precedent) > 0.0001:
            rang = position
        rangs[identifiant] = rang
        precedent = valeur
    for identifiant, valeur in valeurs:
        if valeur is None:
            rangs[identifiant] = 0
    return rangs
