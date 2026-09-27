"""Dépôt des inscriptions (table INSCRIPTION)."""

from __future__ import annotations

from typing import List, Optional

from ltadmin.data import row_mapper as rm
from ltadmin.data.schema import Tables
from ltadmin.models.dto import InscriptionDetail
from ltadmin.models.entities import Inscription
from ltadmin.repositories.base import RepositoryBase, p, q


class EnrollmentRepository(RepositoryBase):

    def get_by_id(self, id_inscription: int) -> Optional[Inscription]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.INSCRIPTION)} WHERE {q('ID_INSCRIPTION')} = ?",
            EnrollmentRepository.map_inscription, [p(id_inscription)])

    def get_by_etudiant_classe(self, id_etudiant: int, id_classe: int) -> Optional[Inscription]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.INSCRIPTION)} WHERE {q('ID_ETUDIANT')} = ? "
            f"AND {q('ID_CLASSE')} = ?",
            EnrollmentRepository.map_inscription, [p(id_etudiant), p(id_classe)])

    def get_detail(self, id_inscription: int) -> Optional[InscriptionDetail]:
        return self.query_single(
            EnrollmentRepository.detail_sql() + f" WHERE I.{q('ID_INSCRIPTION')} = ?",
            EnrollmentRepository.map_detail, [p(id_inscription)])

    def list_by_classe(self, id_classe: int) -> List[InscriptionDetail]:
        return self.query_list(
            EnrollmentRepository.detail_sql()
            + f" WHERE I.{q('ID_CLASSE')} = ? ORDER BY E.{q('NOM')}, E.{q('PRENOM')}",
            EnrollmentRepository.map_detail, [p(id_classe)])

    def list_by_etudiant(self, id_etudiant: int) -> List[InscriptionDetail]:
        return self.query_list(
            EnrollmentRepository.detail_sql() + f" WHERE I.{q('ID_ETUDIANT')} = ? "
            f"ORDER BY C.{q('LIBELLE')}",
            EnrollmentRepository.map_detail, [p(id_etudiant)])

    def list_by_annee(self, id_annee: int) -> List[InscriptionDetail]:
        return self.query_list(
            EnrollmentRepository.detail_sql()
            + f" WHERE C.{q('ID_ANNEE')} = ? ORDER BY C.{q('LIBELLE')}, E.{q('NOM')}, E.{q('PRENOM')}",
            EnrollmentRepository.map_detail, [p(id_annee)])

    @staticmethod
    def detail_sql() -> str:
        return (
            f"SELECT I.*, E.{q('MATRICULE')}, E.{q('NOM')}, E.{q('PRENOM')}, "
            f"C.{q('LIBELLE')} AS CLASSE_LIB "
            f"FROM (({q(Tables.INSCRIPTION)} AS I "
            f"INNER JOIN {q(Tables.ETUDIANT)} AS E ON I.{q('ID_ETUDIANT')} = E.{q('ID_ETUDIANT')}) "
            f"INNER JOIN {q(Tables.CLASSE)} AS C ON I.{q('ID_CLASSE')} = C.{q('ID_CLASSE')})"
        )

    def count_by_classe(self, id_classe: int) -> int:
        return self.scalar_int(
            f"SELECT COUNT(*) FROM {q(Tables.INSCRIPTION)} WHERE {q('ID_CLASSE')} = ?",
            [p(id_classe)])

    def count_by_annee(self, id_annee: int) -> int:
        return self.scalar_int(
            f"SELECT COUNT(*) FROM {q(Tables.INSCRIPTION)} AS I "
            f"INNER JOIN {q(Tables.CLASSE)} AS C ON I.{q('ID_CLASSE')} = C.{q('ID_CLASSE')} "
            f"WHERE C.{q('ID_ANNEE')} = ?",
            [p(id_annee)])

    def list_numeros(self, prefixe: str) -> List[str]:
        table = self.query_table(
            f"SELECT {q('NUM_INSCRIPTION')} FROM {q(Tables.INSCRIPTION)} "
            f"WHERE {q('NUM_INSCRIPTION')} LIKE ?",
            [p(prefixe + "%")])
        result = []
        for row in table:
            value = rm.get_string(row, "NUM_INSCRIPTION")
            if value and value.strip():
                result.append(value)
        return result

    def insert(self, inscription: Inscription) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.INSCRIPTION)} ({q('ID_ETUDIANT')}, {q('ID_CLASSE')}, "
            f"{q('NUM_INSCRIPTION')}, {q('DATE_INSCRIPTION')}, {q('REDOUBLANT')}, {q('STATUT')}, "
            f"{q('DATE_SORTIE')}, {q('MOTIF_SORTIE')}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [p(inscription.id_etudiant), p(inscription.id_classe), p(inscription.num_inscription),
             p(inscription.date_inscription),
             p(False if inscription.redoublant is None else inscription.redoublant),
             p(inscription.statut), p(inscription.date_sortie), p(inscription.motif_sortie)])

    def update(self, inscription: Inscription) -> int:
        return self.execute(
            f"UPDATE {q(Tables.INSCRIPTION)} SET {q('ID_ETUDIANT')} = ?, {q('ID_CLASSE')} = ?, "
            f"{q('NUM_INSCRIPTION')} = ?, {q('DATE_INSCRIPTION')} = ?, {q('REDOUBLANT')} = ?, "
            f"{q('STATUT')} = ?, {q('DATE_SORTIE')} = ?, {q('MOTIF_SORTIE')} = ? "
            f"WHERE {q('ID_INSCRIPTION')} = ?",
            [p(inscription.id_etudiant), p(inscription.id_classe), p(inscription.num_inscription),
             p(inscription.date_inscription),
             p(False if inscription.redoublant is None else inscription.redoublant),
             p(inscription.statut), p(inscription.date_sortie), p(inscription.motif_sortie),
             p(inscription.id_inscription)])

    def delete(self, id_inscription: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.INSCRIPTION)} WHERE {q('ID_INSCRIPTION')} = ?",
            [p(id_inscription)])

    @staticmethod
    def map_inscription(row: dict) -> Inscription:
        return Inscription(
            id_inscription=rm.get_int(row, "ID_INSCRIPTION"),
            id_etudiant=rm.get_int(row, "ID_ETUDIANT"),
            id_classe=rm.get_int(row, "ID_CLASSE"),
            num_inscription=rm.get_string(row, "NUM_INSCRIPTION"),
            date_inscription=rm.get_datetime(row, "DATE_INSCRIPTION"),
            redoublant=rm.get_bool(row, "REDOUBLANT"),
            statut=rm.get_string(row, "STATUT"),
            date_sortie=rm.get_datetime(row, "DATE_SORTIE"),
            motif_sortie=rm.get_string(row, "MOTIF_SORTIE"),
        )

    @staticmethod
    def map_detail(row: dict) -> InscriptionDetail:
        return InscriptionDetail(
            id_inscription=rm.get_int(row, "ID_INSCRIPTION"),
            id_etudiant=rm.get_int(row, "ID_ETUDIANT"),
            id_classe=rm.get_int(row, "ID_CLASSE"),
            matricule=rm.get_string(row, "MATRICULE"),
            nom=rm.get_string(row, "NOM"),
            prenom=rm.get_string(row, "PRENOM"),
            classe=rm.get_string(row, "CLASSE_LIB"),
            num_inscription=rm.get_string(row, "NUM_INSCRIPTION"),
            date_inscription=rm.get_datetime(row, "DATE_INSCRIPTION"),
            redoublant=rm.get_bool(row, "REDOUBLANT"),
            statut=rm.get_string(row, "STATUT"),
            date_sortie=rm.get_datetime(row, "DATE_SORTIE"),
            motif_sortie=rm.get_string(row, "MOTIF_SORTIE"),
        )
