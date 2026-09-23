"""Dépôt du bloc Administration (utilisateurs, paramètres, établissement, années, journal)."""

from __future__ import annotations

import datetime as _dt
from typing import List, Optional

from ltadmin.data import row_mapper as rm
from ltadmin.data.schema import Tables
from ltadmin.models.entities import (
    AnneeScolaire,
    Etablissement,
    JournalEntry,
    Parametre,
    Utilisateur,
)
from ltadmin.repositories.base import RepositoryBase, p, q


class AdminRepository(RepositoryBase):

    # ----- UTILISATEUR -----

    def get_utilisateur(self, code_utr: str) -> Optional[Utilisateur]:
        # Access compare les chaînes sans tenir compte de la casse par défaut ;
        # UCASE rend ce comportement explicite et identique sous SQLite.
        return self.query_single(
            f"SELECT * FROM {q(Tables.UTILISATEUR)} "
            f"WHERE UCASE({q('CODE_UTR')}) = UCASE(?)",
            UtilisateurMapper.map, [p(code_utr)])

    def list_utilisateurs(self) -> List[Utilisateur]:
        return self.query_list(
            f"SELECT * FROM {q(Tables.UTILISATEUR)} ORDER BY {q('CODE_UTR')}",
            UtilisateurMapper.map)

    def insert_utilisateur(self, user: Utilisateur) -> None:
        self.execute(
            f"INSERT INTO {q(Tables.UTILISATEUR)} ({q('CODE_UTR')}, {q('NOM_UTR')}, "
            f"{q('MOT_PASSE')}, {q('PROFIL')}, {q('ACTIF')}) VALUES (?, ?, ?, ?, ?)",
            [p(user.code_utr), p(user.nom_utr), p(user.mot_passe), p(user.profil),
             p(True if user.actif is None else user.actif)])

    def update_utilisateur(self, user: Utilisateur) -> int:
        return self.execute(
            f"UPDATE {q(Tables.UTILISATEUR)} SET {q('NOM_UTR')} = ?, {q('PROFIL')} = ?, "
            f"{q('ACTIF')} = ? WHERE {q('CODE_UTR')} = ?",
            [p(user.nom_utr), p(user.profil), p(True if user.actif is None else user.actif),
             p(user.code_utr)])

    def update_mot_passe(self, code_utr: str, nouveau_mot_passe: str) -> int:
        return self.execute(
            f"UPDATE {q(Tables.UTILISATEUR)} SET {q('MOT_PASSE')} = ? WHERE {q('CODE_UTR')} = ?",
            [p(nouveau_mot_passe), p(code_utr)])

    def set_utilisateur_actif(self, code_utr: str, actif: bool) -> int:
        return self.execute(
            f"UPDATE {q(Tables.UTILISATEUR)} SET {q('ACTIF')} = ? WHERE {q('CODE_UTR')} = ?",
            [p(actif), p(code_utr)])

    def delete_utilisateur(self, code_utr: str) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.UTILISATEUR)} WHERE {q('CODE_UTR')} = ?", [p(code_utr)])

    # ----- PARAMETRE -----

    def list_parametres(self) -> List[Parametre]:
        return self.query_list(
            f"SELECT * FROM {q(Tables.PARAMETRE)} ORDER BY {q('CLE')}",
            AdminRepository.map_parametre)

    def get_valeur(self, cle: str) -> Optional[str]:
        return self.scalar_string(
            f"SELECT {q('VALEUR')} FROM {q(Tables.PARAMETRE)} WHERE {q('CLE')} = ?", [p(cle)])

    def update_valeur(self, cle: str, valeur: str) -> int:
        return self.execute(
            f"UPDATE {q(Tables.PARAMETRE)} SET {q('VALEUR')} = ? WHERE {q('CLE')} = ?",
            [p(valeur), p(cle)])

    # ----- ETABLISSEMENT -----

    def get_etablissement(self) -> Optional[Etablissement]:
        return self.query_single(
            f"SELECT TOP 1 * FROM {q(Tables.ETABLISSEMENT)} ORDER BY {q('CODE_ETAB')}",
            AdminRepository.map_etablissement)

    def update_etablissement(self, etablissement: Etablissement) -> int:
        return self.execute(
            f"UPDATE {q(Tables.ETABLISSEMENT)} SET {q('NOM_ETAB')} = ?, {q('SIGLE')} = ?, "
            f"{q('ADRESSE')} = ?, {q('TEL')} = ?, {q('EMAIL')} = ?, {q('SITE_WEB')} = ?, "
            f"{q('DIRECTEUR')} = ?, {q('LOGO')} = ? WHERE {q('CODE_ETAB')} = ?",
            [p(etablissement.nom_etab), p(etablissement.sigle), p(etablissement.adresse),
             p(etablissement.tel), p(etablissement.email), p(etablissement.site_web),
             p(etablissement.directeur), p(etablissement.logo), p(etablissement.code_etab)])

    # ----- ANNEE_SCOLAIRE -----

    def list_annees(self) -> List[AnneeScolaire]:
        return self.query_list(
            f"SELECT * FROM {q(Tables.ANNEE_SCOLAIRE)} ORDER BY {q('LIBELLE')} DESC",
            AdminRepository.map_annee)

    def get_annee(self, id_annee: int) -> Optional[AnneeScolaire]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.ANNEE_SCOLAIRE)} WHERE {q('ID_ANNEE')} = ?",
            AdminRepository.map_annee, [p(id_annee)])

    def get_annee_active(self) -> Optional[AnneeScolaire]:
        return self.query_single(
            f"SELECT TOP 1 * FROM {q(Tables.ANNEE_SCOLAIRE)} WHERE {q('ACTIVE')} = ? "
            f"ORDER BY {q('ID_ANNEE')} DESC",
            AdminRepository.map_annee, [p(True)])

    def insert_annee(self, annee: AnneeScolaire) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.ANNEE_SCOLAIRE)} ({q('LIBELLE')}, {q('DATE_DEBUT')}, "
            f"{q('DATE_FIN')}, {q('ACTIVE')}) VALUES (?, ?, ?, ?)",
            [p(annee.libelle), p(annee.date_debut), p(annee.date_fin),
             p(False if annee.active is None else annee.active)])

    def update_annee(self, annee: AnneeScolaire) -> int:
        return self.execute(
            f"UPDATE {q(Tables.ANNEE_SCOLAIRE)} SET {q('LIBELLE')} = ?, {q('DATE_DEBUT')} = ?, "
            f"{q('DATE_FIN')} = ?, {q('ACTIVE')} = ? WHERE {q('ID_ANNEE')} = ?",
            [p(annee.libelle), p(annee.date_debut), p(annee.date_fin),
             p(False if annee.active is None else annee.active), p(annee.id_annee)])

    def set_annee_active(self, id_annee: int) -> None:
        """Active une année et désactive les autres, en transaction."""
        with self.db.begin_transaction():
            self.execute(f"UPDATE {q(Tables.ANNEE_SCOLAIRE)} SET {q('ACTIVE')} = ?", [p(False)])
            self.execute(
                f"UPDATE {q(Tables.ANNEE_SCOLAIRE)} SET {q('ACTIVE')} = ? WHERE {q('ID_ANNEE')} = ?",
                [p(True), p(id_annee)])

    # ----- JOURNAL -----

    def insert_journal(self, entry: JournalEntry) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.JOURNAL)} ({q('DATE_LOG')}, {q('CODE_UTR')}, "
            f"{q('ACTION_LOG')}, {q('TABLE_CIBLE')}, {q('ID_CIBLE')}, {q('DETAIL')}) "
            f"VALUES (?, ?, ?, ?, ?, ?)",
            [p(entry.date_log or _dt.datetime.now()), p(entry.code_utr), p(entry.action_log),
             p(entry.table_cible), p(entry.id_cible), p(entry.detail)])

    def list_journal(self, depuis=None, code_utr: Optional[str] = None,
                     action: Optional[str] = None, max_rows: int = 500) -> List[JournalEntry]:
        max_rows = max(1, min(max_rows, 5000))
        sql = f"SELECT TOP {max_rows} * FROM {q(Tables.JOURNAL)}"
        conditions = []
        parameters = []
        if depuis is not None:
            conditions.append(f"{q('DATE_LOG')} >= ?")
            parameters.append(p(depuis))
        if code_utr and code_utr.strip():
            conditions.append(f"{q('CODE_UTR')} = ?")
            parameters.append(p(code_utr.strip()))
        if action and action.strip():
            conditions.append(f"{q('ACTION_LOG')} = ?")
            parameters.append(p(action.strip()))
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += f" ORDER BY {q('ID_LOG')} DESC"
        return self.query_list(sql, AdminRepository.map_journal, parameters)

    def count_journal(self) -> int:
        return self.scalar_int(f"SELECT COUNT(*) FROM {q(Tables.JOURNAL)}")

    # ----- Mappers -----

    @staticmethod
    def map_utilisateur(row: dict) -> Utilisateur:
        return Utilisateur(
            code_utr=rm.get_string(row, "CODE_UTR"),
            nom_utr=rm.get_string(row, "NOM_UTR"),
            mot_passe=rm.get_string(row, "MOT_PASSE"),
            profil=rm.get_string(row, "PROFIL"),
            actif=rm.get_bool(row, "ACTIF"),
        )

    @staticmethod
    def map_parametre(row: dict) -> Parametre:
        return Parametre(
            cle=rm.get_string(row, "CLE"),
            valeur=rm.get_string(row, "VALEUR"),
            description=rm.get_string(row, "DESCRIPTION_P"),
        )

    @staticmethod
    def map_etablissement(row: dict) -> Etablissement:
        return Etablissement(
            code_etab=rm.get_string(row, "CODE_ETAB"),
            nom_etab=rm.get_string(row, "NOM_ETAB"),
            sigle=rm.get_string(row, "SIGLE"),
            adresse=rm.get_string(row, "ADRESSE"),
            tel=rm.get_string(row, "TEL"),
            email=rm.get_string(row, "EMAIL"),
            site_web=rm.get_string(row, "SITE_WEB"),
            directeur=rm.get_string(row, "DIRECTEUR"),
            logo=rm.get_string(row, "LOGO"),
        )

    @staticmethod
    def map_annee(row: dict) -> AnneeScolaire:
        return AnneeScolaire(
            id_annee=rm.get_int(row, "ID_ANNEE"),
            libelle=rm.get_string(row, "LIBELLE"),
            date_debut=rm.get_datetime(row, "DATE_DEBUT"),
            date_fin=rm.get_datetime(row, "DATE_FIN"),
            active=rm.get_bool(row, "ACTIVE"),
        )

    @staticmethod
    def map_journal(row: dict) -> JournalEntry:
        return JournalEntry(
            id_log=rm.get_int(row, "ID_LOG"),
            date_log=rm.get_datetime(row, "DATE_LOG"),
            code_utr=rm.get_string(row, "CODE_UTR"),
            action_log=rm.get_string(row, "ACTION_LOG"),
            table_cible=rm.get_string(row, "TABLE_CIBLE"),
            id_cible=rm.get_int(row, "ID_CIBLE"),
            detail=rm.get_string(row, "DETAIL"),
        )


# Alias pratique (le C# exposait MapUtilisateur en statique public).
class UtilisateurMapper:
    map = AdminRepository.map_utilisateur
