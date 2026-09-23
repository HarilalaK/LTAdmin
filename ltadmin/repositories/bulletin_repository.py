"""Dépôt des bulletins, lignes, mentions et résultats finaux."""

from __future__ import annotations

from typing import List, Optional

from ltadmin.data import row_mapper as rm
from ltadmin.data.schema import Tables
from ltadmin.models.dto import BulletinResume
from ltadmin.models.entities import Bulletin, BulletinLigne, GrilleMention, ResultatFinal
from ltadmin.repositories.base import RepositoryBase, p, q


class BulletinRepository(RepositoryBase):

    # ----- BULLETIN -----

    def get_by_inscription_periode(self, id_inscription: int, id_periode: int) -> Optional[Bulletin]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.BULLETIN)} WHERE {q('ID_INSCRIPTION')} = ? "
            f"AND {q('ID_PERIODE')} = ?",
            BulletinRepository.map_bulletin, [p(id_inscription), p(id_periode)])

    def list_by_classe_periode(self, id_classe: int, id_periode: int) -> List[Bulletin]:
        return self.query_list(
            f"SELECT B.* FROM {q(Tables.BULLETIN)} AS B "
            f"INNER JOIN {q(Tables.INSCRIPTION)} AS I ON B.{q('ID_INSCRIPTION')} = "
            f"I.{q('ID_INSCRIPTION')} "
            f"WHERE I.{q('ID_CLASSE')} = ? AND B.{q('ID_PERIODE')} = ? ORDER BY B.{q('RANG')}",
            BulletinRepository.map_bulletin, [p(id_classe), p(id_periode)])

    def list_resumes(self, id_classe: Optional[int] = None,
                     id_periode: Optional[int] = None) -> List[BulletinResume]:
        conditions = []
        parameters = []
        if id_classe is not None:
            conditions.append(f"I.{q('ID_CLASSE')} = ?")
            parameters.append(p(id_classe))
        if id_periode is not None:
            conditions.append(f"B.{q('ID_PERIODE')} = ?")
            parameters.append(p(id_periode))
        sql = BulletinRepository.bulletin_resume_sql()
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += f" ORDER BY C.{q('LIBELLE')}, B.{q('RANG')}"
        return self.query_list(sql, BulletinRepository.map_bulletin_resume, parameters)

    @staticmethod
    def bulletin_resume_sql() -> str:
        return (
            f"SELECT B.*, E.{q('MATRICULE')}, E.{q('NOM')}, E.{q('PRENOM')}, "
            f"C.{q('LIBELLE')} AS CLASSE_LIB, PE.{q('LIBELLE')} AS PERIODE_LIB "
            f"FROM (((({q(Tables.BULLETIN)} AS B "
            f"INNER JOIN {q(Tables.INSCRIPTION)} AS I ON B.{q('ID_INSCRIPTION')} = "
            f"I.{q('ID_INSCRIPTION')}) "
            f"INNER JOIN {q(Tables.ETUDIANT)} AS E ON I.{q('ID_ETUDIANT')} = E.{q('ID_ETUDIANT')}) "
            f"INNER JOIN {q(Tables.CLASSE)} AS C ON I.{q('ID_CLASSE')} = C.{q('ID_CLASSE')}) "
            f"INNER JOIN {q(Tables.PERIODE_EVAL)} AS PE ON B.{q('ID_PERIODE')} = "
            f"PE.{q('ID_PERIODE')})"
        )

    def list_moyennes_by_inscription(self, id_inscription: int) -> List[float]:
        table = self.query_table(
            f"SELECT {q('MOYENNE')} FROM {q(Tables.BULLETIN)} "
            f"WHERE {q('ID_INSCRIPTION')} = ? AND {q('MOYENNE')} IS NOT NULL",
            [p(id_inscription)])
        result = []
        for row in table:
            value = rm.get_double(row, "MOYENNE")
            if value is not None:
                result.append(value)
        return result

    def insert_bulletin(self, bulletin: Bulletin) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.BULLETIN)} ({q('ID_INSCRIPTION')}, {q('ID_PERIODE')}, "
            f"{q('MOYENNE')}, {q('TOTAL_POINTS')}, {q('TOTAL_COEF')}, {q('RANG')}, "
            f"{q('EFFECTIF')}, {q('MOY_CLASSE')}, {q('NB_ABSENCE')}, {q('APPRECIATION')}, "
            f"{q('DECISION')}, {q('DATE_EDITION')}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [p(bulletin.id_inscription), p(bulletin.id_periode), p(bulletin.moyenne),
             p(bulletin.total_points), p(bulletin.total_coef), p(bulletin.rang),
             p(bulletin.effectif), p(bulletin.moy_classe), p(bulletin.nb_absence),
             p(bulletin.appreciation), p(bulletin.decision), p(bulletin.date_edition)])

    def update_rang(self, bulletin: Bulletin) -> int:
        return self.execute(
            f"UPDATE {q(Tables.BULLETIN)} SET {q('RANG')} = ?, {q('EFFECTIF')} = ?, "
            f"{q('MOY_CLASSE')} = ? WHERE {q('ID_BULLETIN')} = ?",
            [p(bulletin.rang), p(bulletin.effectif), p(bulletin.moy_classe),
             p(bulletin.id_bulletin)])

    def update_appreciation(self, bulletin: Bulletin) -> int:
        """Modifie l'appréciation générale d'un bulletin (sans recalcul)."""
        return self.execute(
            f"UPDATE {q(Tables.BULLETIN)} SET {q('APPRECIATION')} = ? "
            f"WHERE {q('ID_BULLETIN')} = ?",
            [p(bulletin.appreciation), p(bulletin.id_bulletin)])

    def list_ids_by_classe_periode(self, id_classe: int, id_periode: int) -> List[int]:
        """Identifiants des bulletins existants pour régénération ciblée."""
        table = self.query_table(
            f"SELECT B.{q('ID_BULLETIN')} FROM {q(Tables.BULLETIN)} AS B "
            f"INNER JOIN {q(Tables.INSCRIPTION)} AS I ON B.{q('ID_INSCRIPTION')} = "
            f"I.{q('ID_INSCRIPTION')} "
            f"WHERE I.{q('ID_CLASSE')} = ? AND B.{q('ID_PERIODE')} = ?",
            [p(id_classe), p(id_periode)])
        result = []
        for row in table:
            value = rm.get_int(row, "ID_BULLETIN")
            if value is not None:
                result.append(value)
        return result

    def delete_bulletin(self, id_bulletin: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.BULLETIN)} WHERE {q('ID_BULLETIN')} = ?", [p(id_bulletin)])

    # ----- BULLETIN_LIGNE -----

    def list_lignes(self, id_bulletin: int) -> List[BulletinLigne]:
        return self.query_list(
            f"SELECT * FROM {q(Tables.BULLETIN_LIGNE)} WHERE {q('ID_BULLETIN')} = ?",
            BulletinRepository.map_ligne, [p(id_bulletin)])

    def insert_ligne(self, ligne: BulletinLigne) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.BULLETIN_LIGNE)} ({q('ID_BULLETIN')}, {q('CODE_MATIERE')}, "
            f"{q('MOYENNE_MAT')}, {q('COEFFICIENT')}, {q('POINTS')}, {q('RANG_MAT')}, "
            f"{q('MOY_MIN')}, {q('MOY_MAX')}, {q('APPRECIATION')}, {q('ID_FORMATEUR')}) "
            f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [p(ligne.id_bulletin), p(ligne.code_matiere), p(ligne.moyenne_mat),
             p(ligne.coefficient), p(ligne.points), p(ligne.rang_mat), p(ligne.moy_min),
             p(ligne.moy_max), p(ligne.appreciation), p(ligne.id_formateur)])

    def update_ligne_stats(self, ligne: BulletinLigne) -> int:
        return self.execute(
            f"UPDATE {q(Tables.BULLETIN_LIGNE)} SET {q('RANG_MAT')} = ?, {q('MOY_MIN')} = ?, "
            f"{q('MOY_MAX')} = ? WHERE {q('ID_LIGNE')} = ?",
            [p(ligne.rang_mat), p(ligne.moy_min), p(ligne.moy_max), p(ligne.id_ligne)])

    def delete_lignes_by_bulletin(self, id_bulletin: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.BULLETIN_LIGNE)} WHERE {q('ID_BULLETIN')} = ?",
            [p(id_bulletin)])

    # ----- GRILLE_MENTION -----

    def list_mentions(self) -> List[GrilleMention]:
        return self.query_list(
            f"SELECT * FROM {q(Tables.GRILLE_MENTION)} ORDER BY {q('INF')} DESC",
            BulletinRepository.map_mention)

    # ----- RESULTAT_FINAL -----

    def get_by_inscription(self, id_inscription: int) -> Optional[ResultatFinal]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.RESULTAT_FINAL)} WHERE {q('ID_INSCRIPTION')} = ?",
            BulletinRepository.map_resultat, [p(id_inscription)])

    def list_by_classe(self, id_classe: int) -> List[ResultatFinal]:
        return self.query_list(
            f"SELECT R.* FROM {q(Tables.RESULTAT_FINAL)} AS R "
            f"INNER JOIN {q(Tables.INSCRIPTION)} AS I ON R.{q('ID_INSCRIPTION')} = "
            f"I.{q('ID_INSCRIPTION')} "
            f"WHERE I.{q('ID_CLASSE')} = ? ORDER BY R.{q('RANG')}",
            BulletinRepository.map_resultat, [p(id_classe)])

    def insert_resultat(self, resultat: ResultatFinal) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.RESULTAT_FINAL)} ({q('ID_INSCRIPTION')}, {q('MOY_CC')}, "
            f"{q('MOY_EXAM')}, {q('MOYENNE_GEN')}, {q('RANG')}, {q('MENTION')}, "
            f"{q('DECISION')}, {q('CREDIT_VALIDE')}, {q('DATE_DELIB')}, {q('OBSERVATION')}) "
            f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [p(resultat.id_inscription), p(resultat.moy_cc), p(resultat.moy_exam),
             p(resultat.moyenne_gen), p(resultat.rang), p(resultat.mention),
             p(resultat.decision), p(resultat.credit_valide), p(resultat.date_delib),
             p(resultat.observation)])

    def update_resultat_rang(self, resultat: ResultatFinal) -> int:
        return self.execute(
            f"UPDATE {q(Tables.RESULTAT_FINAL)} SET {q('RANG')} = ? WHERE {q('ID_RESULTAT')} = ?",
            [p(resultat.rang), p(resultat.id_resultat)])

    def delete_by_inscription(self, id_inscription: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.RESULTAT_FINAL)} WHERE {q('ID_INSCRIPTION')} = ?",
            [p(id_inscription)])

    # ----- Mappers -----

    @staticmethod
    def map_bulletin(row: dict) -> Bulletin:
        return Bulletin(
            id_bulletin=rm.get_int(row, "ID_BULLETIN"),
            id_inscription=rm.get_int(row, "ID_INSCRIPTION"),
            id_periode=rm.get_int(row, "ID_PERIODE"),
            moyenne=rm.get_double(row, "MOYENNE"),
            total_points=rm.get_double(row, "TOTAL_POINTS"),
            total_coef=rm.get_double(row, "TOTAL_COEF"),
            rang=rm.get_int(row, "RANG"),
            effectif=rm.get_int(row, "EFFECTIF"),
            moy_classe=rm.get_double(row, "MOY_CLASSE"),
            nb_absence=rm.get_double(row, "NB_ABSENCE"),
            appreciation=rm.get_string(row, "APPRECIATION"),
            decision=rm.get_string(row, "DECISION"),
            date_edition=rm.get_datetime(row, "DATE_EDITION"),
        )

    @staticmethod
    def map_bulletin_resume(row: dict) -> BulletinResume:
        return BulletinResume(
            id_bulletin=rm.get_int(row, "ID_BULLETIN"),
            id_inscription=rm.get_int(row, "ID_INSCRIPTION"),
            matricule=rm.get_string(row, "MATRICULE"),
            nom=rm.get_string(row, "NOM"),
            prenom=rm.get_string(row, "PRENOM"),
            classe=rm.get_string(row, "CLASSE_LIB"),
            id_periode=rm.get_int(row, "ID_PERIODE"),
            periode=rm.get_string(row, "PERIODE_LIB"),
            moyenne=rm.get_double(row, "MOYENNE"),
            rang=rm.get_int(row, "RANG"),
            effectif=rm.get_int(row, "EFFECTIF"),
            decision=rm.get_string(row, "DECISION"),
        )

    @staticmethod
    def map_ligne(row: dict) -> BulletinLigne:
        return BulletinLigne(
            id_ligne=rm.get_int(row, "ID_LIGNE"),
            id_bulletin=rm.get_int(row, "ID_BULLETIN"),
            code_matiere=rm.get_string(row, "CODE_MATIERE"),
            moyenne_mat=rm.get_double(row, "MOYENNE_MAT"),
            coefficient=rm.get_double(row, "COEFFICIENT"),
            points=rm.get_double(row, "POINTS"),
            rang_mat=rm.get_int(row, "RANG_MAT"),
            moy_min=rm.get_double(row, "MOY_MIN"),
            moy_max=rm.get_double(row, "MOY_MAX"),
            appreciation=rm.get_string(row, "APPRECIATION"),
            id_formateur=rm.get_int(row, "ID_FORMATEUR"),
        )

    @staticmethod
    def map_mention(row: dict) -> GrilleMention:
        return GrilleMention(
            id_mention=rm.get_int(row, "ID_MENTION"),
            inf=rm.get_double(row, "INF"),
            sup=rm.get_double(row, "SUP"),
            mention=rm.get_string(row, "MENTION"),
            admis=rm.get_bool(row, "ADMIS"),
        )

    @staticmethod
    def map_resultat(row: dict) -> ResultatFinal:
        return ResultatFinal(
            id_resultat=rm.get_int(row, "ID_RESULTAT"),
            id_inscription=rm.get_int(row, "ID_INSCRIPTION"),
            moy_cc=rm.get_double(row, "MOY_CC"),
            moy_exam=rm.get_double(row, "MOY_EXAM"),
            moyenne_gen=rm.get_double(row, "MOYENNE_GEN"),
            rang=rm.get_int(row, "RANG"),
            mention=rm.get_string(row, "MENTION"),
            decision=rm.get_string(row, "DECISION"),
            credit_valide=rm.get_int(row, "CREDIT_VALIDE"),
            date_delib=rm.get_datetime(row, "DATE_DELIB"),
            observation=rm.get_string(row, "OBSERVATION"),
        )
