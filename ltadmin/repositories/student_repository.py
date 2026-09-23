"""Dépôt des dossiers étudiants (table ETUDIANT)."""

from __future__ import annotations

from typing import List, Optional

from ltadmin.data import row_mapper as rm
from ltadmin.data.schema import Tables
from ltadmin.models.entities import Etudiant
from ltadmin.repositories.base import RepositoryBase, p, q


class StudentRepository(RepositoryBase):

    def get_by_id(self, id_etudiant: int) -> Optional[Etudiant]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.ETUDIANT)} WHERE {q('ID_ETUDIANT')} = ?",
            StudentRepository.map_etudiant, [p(id_etudiant)])

    def get_by_matricule(self, matricule: str) -> Optional[Etudiant]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.ETUDIANT)} WHERE {q('MATRICULE')} = ?",
            StudentRepository.map_etudiant, [p(matricule)])

    def search(self, recherche: Optional[str], max_rows: int = 500) -> List[Etudiant]:
        max_rows = max(1, min(max_rows, 5000))
        if not recherche or not recherche.strip():
            return self.query_list(
                f"SELECT TOP {max_rows} * FROM {q(Tables.ETUDIANT)} "
                f"ORDER BY {q('NOM')}, {q('PRENOM')}",
                StudentRepository.map_etudiant)
        motif = "%" + recherche.strip() + "%"
        return self.query_list(
            f"SELECT TOP {max_rows} * FROM {q(Tables.ETUDIANT)} "
            f"WHERE {q('NOM')} LIKE ? OR {q('PRENOM')} LIKE ? OR {q('MATRICULE')} LIKE ? "
            f"ORDER BY {q('NOM')}, {q('PRENOM')}",
            StudentRepository.map_etudiant, [p(motif), p(motif), p(motif)])

    def count(self) -> int:
        return self.scalar_int(f"SELECT COUNT(*) FROM {q(Tables.ETUDIANT)}")

    def matricule_existe(self, matricule: str) -> bool:
        return self.exists(
            f"SELECT COUNT(*) FROM {q(Tables.ETUDIANT)} WHERE {q('MATRICULE')} = ?",
            [p(matricule)])

    def list_matricules(self, prefixe: str) -> List[str]:
        table = self.query_table(
            f"SELECT {q('MATRICULE')} FROM {q(Tables.ETUDIANT)} WHERE {q('MATRICULE')} LIKE ?",
            [p(prefixe + "%")])
        result = []
        for row in table:
            value = rm.get_string(row, "MATRICULE")
            if value and value.strip():
                result.append(value)
        return result

    def insert(self, etudiant: Etudiant) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.ETUDIANT)} ({q('MATRICULE')}, {q('NOM')}, {q('PRENOM')}, "
            f"{q('SEXE')}, {q('DATE_NAISSANCE')}, {q('LIEU_NAISSANCE')}, {q('CIN')}, "
            f"{q('NATIONALITE')}, {q('ADRESSE')}, {q('TEL')}, {q('EMAIL')}, {q('NOM_TUTEUR')}, "
            f"{q('TEL_TUTEUR')}, {q('PROFESSION_TUTEUR')}, {q('SERIE_BACC')}, {q('ANNEE_BACC')}, "
            f"{q('ETAB_ORIGINE')}, {q('PHOTO')}, {q('DATE_CREATION')}, {q('STATUT')}) "
            f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [p(etudiant.matricule), p(etudiant.nom), p(etudiant.prenom), p(etudiant.sexe),
             p(etudiant.date_naissance), p(etudiant.lieu_naissance), p(etudiant.cin),
             p(etudiant.nationalite), p(etudiant.adresse), p(etudiant.tel), p(etudiant.email),
             p(etudiant.nom_tuteur), p(etudiant.tel_tuteur), p(etudiant.profession_tuteur),
             p(etudiant.serie_bacc), p(etudiant.annee_bacc), p(etudiant.etab_origine),
             p(etudiant.photo), p(etudiant.date_creation), p(etudiant.statut)])

    def update(self, etudiant: Etudiant) -> int:
        return self.execute(
            f"UPDATE {q(Tables.ETUDIANT)} SET {q('MATRICULE')} = ?, {q('NOM')} = ?, "
            f"{q('PRENOM')} = ?, {q('SEXE')} = ?, {q('DATE_NAISSANCE')} = ?, "
            f"{q('LIEU_NAISSANCE')} = ?, {q('CIN')} = ?, {q('NATIONALITE')} = ?, "
            f"{q('ADRESSE')} = ?, {q('TEL')} = ?, {q('EMAIL')} = ?, {q('NOM_TUTEUR')} = ?, "
            f"{q('TEL_TUTEUR')} = ?, {q('PROFESSION_TUTEUR')} = ?, {q('SERIE_BACC')} = ?, "
            f"{q('ANNEE_BACC')} = ?, {q('ETAB_ORIGINE')} = ?, {q('PHOTO')} = ?, {q('STATUT')} = ? "
            f"WHERE {q('ID_ETUDIANT')} = ?",
            [p(etudiant.matricule), p(etudiant.nom), p(etudiant.prenom), p(etudiant.sexe),
             p(etudiant.date_naissance), p(etudiant.lieu_naissance), p(etudiant.cin),
             p(etudiant.nationalite), p(etudiant.adresse), p(etudiant.tel), p(etudiant.email),
             p(etudiant.nom_tuteur), p(etudiant.tel_tuteur), p(etudiant.profession_tuteur),
             p(etudiant.serie_bacc), p(etudiant.annee_bacc), p(etudiant.etab_origine),
             p(etudiant.photo), p(etudiant.statut), p(etudiant.id_etudiant)])

    def delete(self, id_etudiant: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.ETUDIANT)} WHERE {q('ID_ETUDIANT')} = ?", [p(id_etudiant)])

    @staticmethod
    def map_etudiant(row: dict) -> Etudiant:
        return Etudiant(
            id_etudiant=rm.get_int(row, "ID_ETUDIANT"),
            matricule=rm.get_string(row, "MATRICULE"),
            nom=rm.get_string(row, "NOM"),
            prenom=rm.get_string(row, "PRENOM"),
            sexe=rm.get_string(row, "SEXE"),
            date_naissance=rm.get_datetime(row, "DATE_NAISSANCE"),
            lieu_naissance=rm.get_string(row, "LIEU_NAISSANCE"),
            cin=rm.get_string(row, "CIN"),
            nationalite=rm.get_string(row, "NATIONALITE"),
            adresse=rm.get_string(row, "ADRESSE"),
            tel=rm.get_string(row, "TEL"),
            email=rm.get_string(row, "EMAIL"),
            nom_tuteur=rm.get_string(row, "NOM_TUTEUR"),
            tel_tuteur=rm.get_string(row, "TEL_TUTEUR"),
            profession_tuteur=rm.get_string(row, "PROFESSION_TUTEUR"),
            serie_bacc=rm.get_string(row, "SERIE_BACC"),
            annee_bacc=rm.get_int(row, "ANNEE_BACC"),
            etab_origine=rm.get_string(row, "ETAB_ORIGINE"),
            photo=rm.get_string(row, "PHOTO"),
            date_creation=rm.get_datetime(row, "DATE_CREATION"),
            statut=rm.get_string(row, "STATUT"),
        )
