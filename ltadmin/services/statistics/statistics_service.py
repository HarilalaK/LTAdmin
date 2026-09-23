"""Statistiques : tableau de bord et indicateurs de pilotage.

Toutes les requêtes sont paramétrées et compatibles Access (identifiants
[crochets], jointures parenthésées). Le tableau de bord se limite à des
compteurs rapides ; les écrans dédiés affichent le détail par indicateur.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

from ltadmin.data.access_database import AccessDatabase
from ltadmin.data.schema import Tables, quote_identifier as q
from ltadmin.services.logging.app_logger import AppLogger
from ltadmin.services.referentiel.parametre_service import ParametreService


@dataclass
class DashboardData:
    """Compteurs affichés sur l'écran d'accueil."""

    annee_libelle: str = ""
    nb_classes: int = 0
    nb_etudiants: int = 0
    nb_formateurs: int = 0
    total_encaisse: Decimal = Decimal("0")
    nb_echeances_echues: int = 0
    montant_echeances_echues: Decimal = Decimal("0")
    alertes_absences: List[tuple] = field(default_factory=list)
    seuil_absence: float = 0.0
    devise: str = "MGA"


@dataclass
class ClasseEffectifRow:
    classe: str = ""
    filiere: str = ""
    effectif_max: Optional[int] = None
    nb_inscrits: int = 0

    @property
    def remplissage(self) -> Optional[float]:
        if not self.effectif_max:
            return None
        return self.nb_inscrits * 100.0 / self.effectif_max


@dataclass
class RepartitionRow:
    libelle: str = ""
    valeur: int = 0


@dataclass
class AvancementRow:
    id_evaluation: Optional[int] = None
    classe: str = ""
    matiere: str = ""
    periode: str = ""
    intitule: str = ""
    nb_inscrits: int = 0
    nb_notes: int = 0

    @property
    def pourcentage(self) -> float:
        return self.nb_notes * 100.0 / self.nb_inscrits if self.nb_inscrits else 0.0


@dataclass
class EncaissementModeRow:
    mode_paie: str = ""
    nb_paiements: int = 0
    total: Decimal = Decimal("0")


@dataclass
class EcheanceEchueRow:
    matricule: str = ""
    nom: str = ""
    prenom: str = ""
    classe: str = ""
    libelle: str = ""
    date_echeance: Optional[_dt.datetime] = None
    reste: Decimal = Decimal("0")


class StatisticsService:

    def __init__(self, database: AccessDatabase, logger: AppLogger,
                 parametres: ParametreService):
        self._database = database
        self._logger = logger
        self._parametres = parametres

    # ----- Tableau de bord -----

    def dashboard(self, id_annee: Optional[int] = None) -> DashboardData:
        data = DashboardData()
        try:
            annee_id = id_annee
            if annee_id is None:
                row = self._database.query(
                    f"SELECT {q('ID_ANNEE')}, {q('LIBELLE')} FROM {q(Tables.ANNEE_SCOLAIRE)} "
                    f"WHERE {q('ACTIVE')} = ?",
                    [True])
                if row:
                    annee_id = row[0].get("ID_ANNEE")
                    data.annee_libelle = row[0].get("LIBELLE") or ""
            if annee_id is None:
                return data

            classes = self._database.query(
                f"SELECT COUNT(*) AS N FROM {q(Tables.CLASSE)} WHERE {q('ID_ANNEE')} = ?",
                [annee_id])
            data.nb_classes = int(classes[0]["N"]) if classes else 0

            # Effectif : un étudiant compté une seule fois même s'il est inscrit
            # dans deux classes (dédoublonnage comme le HashSet du portage C#).
            etudiants = self._database.query(
                f"SELECT COUNT(*) AS N FROM (SELECT DISTINCT I.{q('ID_ETUDIANT')} "
                f"FROM ({q(Tables.INSCRIPTION)} AS I "
                f"INNER JOIN {q(Tables.CLASSE)} AS C ON I.{q('ID_CLASSE')} = C.{q('ID_CLASSE')}) "
                f"WHERE C.{q('ID_ANNEE')} = ?)",
                [annee_id])
            data.nb_etudiants = int(etudiants[0]["N"]) if etudiants else 0

            data.nb_formateurs = int(self._database.scalar(
                f"SELECT COUNT(*) FROM {q(Tables.FORMATEUR)}") or 0)

            # Recouvrement net de l'année : chaque paiement compté une seule fois.
            encaisse = self._database.query(
                f"SELECT SUM(P.{q('MONTANT')}) AS TOT FROM "
                f"((({q(Tables.PAIEMENT)} AS P "
                f"INNER JOIN {q(Tables.ECHEANCIER)} AS ECH ON P.{q('ID_ECHEANCE')} = "
                f"ECH.{q('ID_ECHEANCE')}) "
                f"INNER JOIN {q(Tables.INSCRIPTION)} AS I ON ECH.{q('ID_INSCRIPTION')} = "
                f"I.{q('ID_INSCRIPTION')}) "
                f"INNER JOIN {q(Tables.CLASSE)} AS C ON I.{q('ID_CLASSE')} = C.{q('ID_CLASSE')}) "
                f"WHERE C.{q('ID_ANNEE')} = ?",
                [annee_id])
            if encaisse and encaisse[0].get("TOT") is not None:
                data.total_encaisse = Decimal(str(encaisse[0]["TOT"]))

            # Échéances échues non soldées de l'année active.
            echues = self._database.query(
                f"SELECT COUNT(*) AS N, SUM(ECH.{q('MONTANT_DU')} - IIf(ECH.{q('REMISE')} "
                f"IS NULL, 0, ECH.{q('REMISE')}) - "
                f"IIf(PE.TOTAL_PAYE IS NULL, 0, PE.TOTAL_PAYE)) AS RESTE "
                f"FROM (((({q(Tables.ECHEANCIER)} AS ECH "
                f"INNER JOIN {q(Tables.INSCRIPTION)} AS I ON ECH.{q('ID_INSCRIPTION')} = "
                f"I.{q('ID_INSCRIPTION')}) "
                f"INNER JOIN {q(Tables.CLASSE)} AS C ON I.{q('ID_CLASSE')} = C.{q('ID_CLASSE')}) "
                f"LEFT JOIN (SELECT {q('ID_ECHEANCE')}, SUM({q('MONTANT')}) AS TOTAL_PAYE "
                f"FROM {q(Tables.PAIEMENT)} GROUP BY {q('ID_ECHEANCE')}) AS PE ON "
                f"ECH.{q('ID_ECHEANCE')} = PE.{q('ID_ECHEANCE')})) "
                f"WHERE C.{q('ID_ANNEE')} = ? AND ECH.{q('STATUT')} <> ? "
                f"AND ECH.{q('DATE_ECHEANCE')} < ?",
                [annee_id, "SOLDE", _dt.datetime.now()])
            if echues:
                data.nb_echeances_echues = int(echues[0].get("N") or 0)
                if echues[0].get("RESTE") is not None:
                    data.montant_echeances_echues = Decimal(str(echues[0]["RESTE"]))

            data.seuil_absence = self._parametres.seuil_absence
            data.devise = self._parametres.devise
            if data.seuil_absence > 0:
                data.alertes_absences = self.alertes_absences(annee_id)
        except Exception as ex:
            self._logger.error("Calcul du tableau de bord", ex)
        return data

    # ----- Effectifs et remplissage -----

    def effectifs_par_classe(self, id_annee: Optional[int] = None) -> List[ClasseEffectifRow]:
        try:
            sql = (f"SELECT C.{q('LIBELLE')} AS CLASSE, F.{q('FILIERE')} AS FILIERE, "
                   f"C.{q('EFFECTIF_MAX')}, COUNT(I.{q('ID_INSCRIPTION')}) AS NB "
                   f"FROM (({q(Tables.CLASSE)} AS C "
                   f"LEFT JOIN {q(Tables.INSCRIPTION)} AS I ON C.{q('ID_CLASSE')} = "
                   f"I.{q('ID_CLASSE')}) "
                   f"LEFT JOIN {q(Tables.FILIERE)} AS F ON C.{q('CODE_FILIERE')} = "
                   f"F.{q('CODE_FILIERE')}) ")
            parameters = []
            if id_annee is not None:
                sql += f"WHERE C.{q('ID_ANNEE')} = ? "
                parameters.append(id_annee)
            sql += f"GROUP BY C.{q('LIBELLE')}, F.{q('FILIERE')}, C.{q('EFFECTIF_MAX')} "
            sql += f"ORDER BY C.{q('LIBELLE')}"
            rows = self._database.query(sql, parameters)
            return [ClasseEffectifRow(
                classe=row.get("CLASSE") or "",
                filiere=row.get("FILIERE") or "",
                effectif_max=row.get("EFFECTIF_MAX"),
                nb_inscrits=int(row.get("NB") or 0)) for row in rows]
        except Exception as ex:
            self._logger.error("Statistiques d’effectifs", ex)
            return []

    def repartition_sexe(self, id_annee: Optional[int] = None) -> List[RepartitionRow]:
        return self._repartition(
            f"SELECT E.{q('SEXE')} AS L, COUNT(*) AS N",
            group_column=f"E.{q('SEXE')}",
            from_clause=f"{q(Tables.ETUDIANT)} AS E "
                        f"INNER JOIN {q(Tables.INSCRIPTION)} AS I ON E.{q('ID_ETUDIANT')} = "
                        f"I.{q('ID_ETUDIANT')} INNER JOIN {q(Tables.CLASSE)} AS C ON "
                        f"I.{q('ID_CLASSE')} = C.{q('ID_CLASSE')}",
            id_annee=id_annee)

    def repartition_redoublants(self, id_annee: Optional[int] = None) -> List[RepartitionRow]:
        return self._repartition(
            f"SELECT I.{q('REDOUBLANT')} AS L, COUNT(*) AS N",
            group_column=f"I.{q('REDOUBLANT')}",
            from_clause=f"{q(Tables.INSCRIPTION)} AS I "
                        f"INNER JOIN {q(Tables.CLASSE)} AS C ON I.{q('ID_CLASSE')} = "
                        f"C.{q('ID_CLASSE')}",
            id_annee=id_annee)

    def repartition_resultats(self, id_annee: Optional[int] = None) -> List[RepartitionRow]:
        return self._repartition(
            f"SELECT R.{q('DECISION')} AS L, COUNT(*) AS N",
            group_column=f"R.{q('DECISION')}",
            from_clause=f"{q(Tables.RESULTAT_FINAL)} AS R "
                        f"INNER JOIN {q(Tables.INSCRIPTION)} AS I ON R.{q('ID_INSCRIPTION')} = "
                        f"I.{q('ID_INSCRIPTION')} INNER JOIN {q(Tables.CLASSE)} AS C ON "
                        f"I.{q('ID_CLASSE')} = C.{q('ID_CLASSE')}",
            id_annee=id_annee)

    def repartition_mentions(self, id_annee: Optional[int] = None) -> List[RepartitionRow]:
        return self._repartition(
            f"SELECT R.{q('MENTION')} AS L, COUNT(*) AS N",
            group_column=f"R.{q('MENTION')}",
            from_clause=f"{q(Tables.RESULTAT_FINAL)} AS R "
                        f"INNER JOIN {q(Tables.INSCRIPTION)} AS I ON R.{q('ID_INSCRIPTION')} = "
                         f"I.{q('ID_INSCRIPTION')} INNER JOIN {q(Tables.CLASSE)} AS C ON "
                         f"I.{q('ID_CLASSE')} = C.{q('ID_CLASSE')}",
            id_annee=id_annee)

    def _repartition(self, select_clause: str, group_column: str, from_clause: str,
                     id_annee: Optional[int] = None) -> List[RepartitionRow]:
        try:
            sql = f"{select_clause} FROM {from_clause} "
            parameters = []
            if id_annee is not None:
                sql += f"WHERE C.{q('ID_ANNEE')} = ? "
                parameters.append(id_annee)
            sql += f"GROUP BY {group_column} ORDER BY {group_column}"
            rows = self._database.query(sql, parameters)
            return [RepartitionRow(libelle=str(row.get("L") if row.get("L") is not None
                                               else "Non renseigné"),
                                   valeur=int(row.get("N") or 0)) for row in rows]
        except Exception as ex:
            self._logger.error("Statistique de répartition", ex)
            return []

    # ----- Avancement des saisies de notes -----

    def avancement_saisie(self, id_classe: Optional[int] = None,
                          id_periode: Optional[int] = None) -> List[AvancementRow]:
        """Notes saisies / inscrits pour chaque évaluation d'une période."""
        try:
            sql = (
                f"SELECT EV.{q('ID_EVALUATION')}, C.{q('LIBELLE')} AS CLASSE, "
                f"M.{q('MATIERE')} AS MATIERE, PE.{q('LIBELLE')} AS PERIODE, "
                f"EV.{q('INTITULE')}, "
                f"(SELECT COUNT(*) FROM {q(Tables.INSCRIPTION)} AS I2 "
                f"WHERE I2.{q('ID_CLASSE')} = C.{q('ID_CLASSE')}) AS NB_INSCRITS, "
                f"(SELECT COUNT(*) FROM {q(Tables.NOTE)} AS N2 "
                f"WHERE N2.{q('ID_EVALUATION')} = EV.{q('ID_EVALUATION')}) AS NB_NOTES "
                f"FROM (((({q(Tables.EVALUATION)} AS EV "
                f"INNER JOIN {q(Tables.PROGRAMME)} AS P ON EV.{q('ID_PROG')} = P.{q('ID_PROG')}) "
                f"INNER JOIN {q(Tables.CLASSE)} AS C ON P.{q('ID_CLASSE')} = C.{q('ID_CLASSE')}) "
                f"INNER JOIN {q(Tables.MATIERE)} AS M ON P.{q('CODE_MATIERE')} = "
                f"M.{q('CODE_MATIERE')}) "
                f"INNER JOIN {q(Tables.PERIODE_EVAL)} AS PE ON EV.{q('ID_PERIODE')} = "
                f"PE.{q('ID_PERIODE')}) ")
            conditions, parameters = [], []
            if id_classe is not None:
                conditions.append(f"C.{q('ID_CLASSE')} = ?")
                parameters.append(id_classe)
            if id_periode is not None:
                conditions.append(f"EV.{q('ID_PERIODE')} = ?")
                parameters.append(id_periode)
            if conditions:
                sql += "WHERE " + " AND ".join(conditions) + " "
            sql += f"ORDER BY C.{q('LIBELLE')}, PE.{q('LIBELLE')}, M.{q('MATIERE')}"
            rows = self._database.query(sql, parameters)
            return [AvancementRow(
                id_evaluation=row.get("ID_EVALUATION"),
                classe=row.get("CLASSE") or "",
                matiere=row.get("MATIERE") or "",
                periode=row.get("PERIODE") or "",
                intitule=row.get("INTITULE") or "",
                nb_inscrits=int(row.get("NB_INSCRITS") or 0),
                nb_notes=int(row.get("NB_NOTES") or 0)) for row in rows]
        except Exception as ex:
            self._logger.error("Statistique d’avancement des saisies", ex)
            return []

    # ----- Absentéisme -----

    def alertes_absences(self, id_annee: Optional[int] = None) -> List[tuple]:
        """Étudiants au-dessus du seuil d'heures d'absence (matricule, nom, total)."""
        seuil = self._parametres.seuil_absence
        if seuil <= 0:
            return []
        try:
            # Identifiants pré-quotés (évite les guillemets imbriqués dans les
            # expressions f-string, non supportés par Python < 3.12).
            c_matricule = q("MATRICULE")
            c_nom = q("NOM")
            c_prenom = q("PRENOM")
            c_heures = q("NB_HEURES")
            c_inscription = q("ID_INSCRIPTION")
            c_etudiant = q("ID_ETUDIANT")
            c_classe = q("ID_CLASSE")
            c_annee = q("ID_ANNEE")
            t_absence = q(Tables.ABSENCE)
            t_inscription = q(Tables.INSCRIPTION)
            t_etudiant = q(Tables.ETUDIANT)
            t_classe = q(Tables.CLASSE)
            sql = (
                f"SELECT E.{c_matricule}, E.{c_nom}, E.{c_prenom}, "
                f"SUM(A.{c_heures}) AS TOTAL "
                f"FROM (((({t_absence} AS A "
                f"INNER JOIN {t_inscription} AS I ON A.{c_inscription} = I.{c_inscription}) "
                f"INNER JOIN {t_etudiant} AS E ON I.{c_etudiant} = E.{c_etudiant}) "
                f"INNER JOIN {t_classe} AS C ON I.{c_classe} = C.{c_classe}) "
            )
            parameters = []
            if id_annee is not None:
                sql += f"WHERE C.{c_annee} = ? "
                parameters.append(id_annee)
            sql += (f") GROUP BY E.{c_matricule}, E.{c_nom}, E.{c_prenom} "
                    f"HAVING SUM(A.{c_heures}) >= ? "
                    f"ORDER BY SUM(A.{c_heures}) DESC")
            parameters.append(seuil)
            rows = self._database.query(sql, parameters)
            return [(row.get("MATRICULE") or "",
                     f"{row.get('NOM') or ''} {row.get('PRENOM') or ''}".strip(),
                     float(row.get("TOTAL") or 0.0)) for row in rows]
        except Exception as ex:
            self._logger.error("Statistique d’absentéisme", ex)
            return []

    def total_absences(self, id_annee: Optional[int] = None) -> float:
        try:
            c_heures = q("NB_HEURES")
            c_inscription = q("ID_INSCRIPTION")
            c_classe = q("ID_CLASSE")
            c_annee = q("ID_ANNEE")
            sql = f"SELECT SUM(A.{c_heures}) AS TOT FROM {q(Tables.ABSENCE)} AS A "
            parameters = []
            if id_annee is not None:
                sql += (f"INNER JOIN {q(Tables.INSCRIPTION)} AS I ON A.{c_inscription} = "
                        f"I.{c_inscription} INNER JOIN {q(Tables.CLASSE)} AS C ON "
                        f"I.{c_classe} = C.{c_classe} "
                        f"WHERE C.{c_annee} = ?")
                parameters.append(id_annee)
            rows = self._database.query(sql, parameters)
            return float(rows[0]["TOT"]) if rows and rows[0].get("TOT") is not None else 0.0
        except Exception as ex:
            self._logger.error("Total des absences", ex)
            return 0.0

    # ----- Encaissements -----

    def encaissements_par_mode(self, debut=None, fin=None) -> List[EncaissementModeRow]:
        try:
            sql = f"SELECT {q('MODE_PAIE')}, COUNT(*) AS N, SUM({q('MONTANT')}) AS TOT " \
                  f"FROM {q(Tables.PAIEMENT)}"
            conditions, parameters = [], []
            if debut is not None:
                conditions.append(f"{q('DATE_PAIEMENT')} >= ?")
                parameters.append(debut)
            if fin is not None:
                conditions.append(f"{q('DATE_PAIEMENT')} < ?")
                parameters.append(_dt.datetime.combine(fin.date(), _dt.time())
                                  + _dt.timedelta(days=1))
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            sql += f" GROUP BY {q('MODE_PAIE')} ORDER BY {q('MODE_PAIE')}"
            rows = self._database.query(sql, parameters)
            return [EncaissementModeRow(
                mode_paie=row.get("MODE_PAIE") or "Non précisé",
                nb_paiements=int(row.get("N") or 0),
                total=Decimal(str(row.get("TOT") or 0))) for row in rows]
        except Exception as ex:
            self._logger.error("Statistique des encaissements", ex)
            return []

    # ----- Échéances échues -----

    def echeances_echues(self, id_annee: Optional[int] = None) -> List[EcheanceEchueRow]:
        """Échéances non soldées dont la date est dépassée (relances)."""
        try:
            c_matricule = q("MATRICULE")
            c_nom = q("NOM")
            c_prenom = q("PRENOM")
            c_libelle = q("LIBELLE")
            c_date_ech = q("DATE_ECHEANCE")
            c_statut = q("STATUT")
            c_montant_du = q("MONTANT_DU")
            c_remise = q("REMISE")
            c_echeance = q("ID_ECHEANCE")
            c_inscription = q("ID_INSCRIPTION")
            c_etudiant = q("ID_ETUDIANT")
            c_classe = q("ID_CLASSE")
            c_annee = q("ID_ANNEE")
            c_montant = q("MONTANT")
            t_echeancier = q(Tables.ECHEANCIER)
            t_inscription = q(Tables.INSCRIPTION)
            t_etudiant = q(Tables.ETUDIANT)
            t_classe = q(Tables.CLASSE)
            t_paiement = q(Tables.PAIEMENT)
            sous_total = (f"(SELECT {c_echeance}, SUM({c_montant}) AS TOTAL_PAYE "
                          f"FROM {t_paiement} GROUP BY {c_echeance}) AS PE")
            net_du = (f"(ECH.{c_montant_du} - IIf(ECH.{c_remise} IS NULL, 0, ECH.{c_remise}) "
                      f"- IIf(PE.TOTAL_PAYE IS NULL, 0, PE.TOTAL_PAYE))")
            sql = (
                f"SELECT E.{c_matricule}, E.{c_nom}, E.{c_prenom}, "
                f"C.{c_libelle} AS CLASSE, ECH.{c_libelle} AS LIB, "
                f"ECH.{c_date_ech}, {net_du} AS RESTE "
                f"FROM (((({t_echeancier} AS ECH "
                f"INNER JOIN {t_inscription} AS I ON ECH.{c_inscription} = I.{c_inscription}) "
                f"INNER JOIN {t_etudiant} AS E ON I.{c_etudiant} = E.{c_etudiant}) "
                f"INNER JOIN {t_classe} AS C ON I.{c_classe} = C.{c_classe}) "
                f"LEFT JOIN {sous_total} ON ECH.{c_echeance} = PE.{c_echeance}) "
            )
            conditions = [f"ECH.{c_statut} <> ?", f"ECH.{c_date_ech} < ?"]
            parameters = ["SOLDE", _dt.datetime.now()]
            if id_annee is not None:
                conditions.append(f"C.{c_annee} = ?")
                parameters.append(id_annee)
            sql += "WHERE " + " AND ".join(conditions) + " "
            sql += f"ORDER BY ECH.{c_date_ech}, E.{c_nom}"
            rows = self._database.query(sql, parameters)
            return [EcheanceEchueRow(
                matricule=row.get("MATRICULE") or "",
                nom=row.get("NOM") or "",
                prenom=row.get("PRENOM") or "",
                classe=row.get("CLASSE") or "",
                libelle=row.get("LIB") or "",
                date_echeance=row.get("DATE_ECHEANCE"),
                reste=Decimal(str(row.get("RESTE") or 0))) for row in rows]
        except Exception as ex:
            self._logger.error("Statistique des échéances échues", ex)
            return []
