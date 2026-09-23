"""Dépôt du personnel : formateurs et programmes (affectations)."""

from __future__ import annotations

from typing import List, Optional

from ltadmin.data import row_mapper as rm
from ltadmin.data.schema import Tables
from ltadmin.models.dto import ProgrammeDetail
from ltadmin.models.entities import Formateur, Programme
from ltadmin.repositories.base import RepositoryBase, p, q


class StaffRepository(RepositoryBase):

    # ----- FORMATEUR -----

    def get_formateur(self, id_formateur: int) -> Optional[Formateur]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.FORMATEUR)} WHERE {q('ID_FORMATEUR')} = ?",
            StaffRepository.map_formateur, [p(id_formateur)])

    def search_formateurs(self, recherche: Optional[str], actifs_seulement: bool = False,
                          max_rows: int = 500) -> List[Formateur]:
        max_rows = max(1, min(max_rows, 5000))
        conditions = []
        parameters = []
        if actifs_seulement:
            conditions.append(f"{q('ACTIF')} = ?")
            parameters.append(p(True))
        if recherche and recherche.strip():
            motif = "%" + recherche.strip() + "%"
            conditions.append(f"({q('NOM')} LIKE ? OR {q('PRENOM')} LIKE ? OR {q('MATRICULE')} LIKE ?)")
            parameters.extend([p(motif), p(motif), p(motif)])
        sql = f"SELECT TOP {max_rows} * FROM {q(Tables.FORMATEUR)}"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += f" ORDER BY {q('NOM')}, {q('PRENOM')}"
        return self.query_list(sql, StaffRepository.map_formateur, parameters)

    def count_formateurs(self) -> int:
        return self.scalar_int(f"SELECT COUNT(*) FROM {q(Tables.FORMATEUR)}")

    def list_matricules(self, prefixe: str) -> List[str]:
        table = self.query_table(
            f"SELECT {q('MATRICULE')} FROM {q(Tables.FORMATEUR)} WHERE {q('MATRICULE')} LIKE ?",
            [p(prefixe + "%")])
        result = []
        for row in table:
            value = rm.get_string(row, "MATRICULE")
            if value and value.strip():
                result.append(value)
        return result

    def insert_formateur(self, formateur: Formateur) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.FORMATEUR)} ({q('MATRICULE')}, {q('NOM')}, {q('PRENOM')}, "
            f"{q('SEXE')}, {q('DATE_NAISSANCE')}, {q('CIN')}, {q('ADRESSE')}, {q('TEL')}, "
            f"{q('EMAIL')}, {q('SPECIALITE')}, {q('DIPLOME')}, {q('CONTRAT')}, "
            f"{q('TAUX_HORAIRE')}, {q('DATE_EMBAUCHE')}, {q('PHOTO')}, {q('ACTIF')}) "
            f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [p(formateur.matricule), p(formateur.nom), p(formateur.prenom), p(formateur.sexe),
             p(formateur.date_naissance), p(formateur.cin), p(formateur.adresse),
             p(formateur.tel), p(formateur.email), p(formateur.specialite),
             p(formateur.diplome), p(formateur.contrat), p(formateur.taux_horaire),
             p(formateur.date_embauche), p(formateur.photo),
             p(True if formateur.actif is None else formateur.actif)])

    def update_formateur(self, formateur: Formateur) -> int:
        return self.execute(
            f"UPDATE {q(Tables.FORMATEUR)} SET {q('MATRICULE')} = ?, {q('NOM')} = ?, "
            f"{q('PRENOM')} = ?, {q('SEXE')} = ?, {q('DATE_NAISSANCE')} = ?, {q('CIN')} = ?, "
            f"{q('ADRESSE')} = ?, {q('TEL')} = ?, {q('EMAIL')} = ?, {q('SPECIALITE')} = ?, "
            f"{q('DIPLOME')} = ?, {q('CONTRAT')} = ?, {q('TAUX_HORAIRE')} = ?, "
            f"{q('DATE_EMBAUCHE')} = ?, {q('PHOTO')} = ?, {q('ACTIF')} = ? "
            f"WHERE {q('ID_FORMATEUR')} = ?",
            [p(formateur.matricule), p(formateur.nom), p(formateur.prenom), p(formateur.sexe),
             p(formateur.date_naissance), p(formateur.cin), p(formateur.adresse),
             p(formateur.tel), p(formateur.email), p(formateur.specialite),
             p(formateur.diplome), p(formateur.contrat), p(formateur.taux_horaire),
             p(formateur.date_embauche), p(formateur.photo),
             p(True if formateur.actif is None else formateur.actif),
             p(formateur.id_formateur)])

    def delete_formateur(self, id_formateur: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.FORMATEUR)} WHERE {q('ID_FORMATEUR')} = ?",
            [p(id_formateur)])

    # ----- PROGRAMME -----

    def get_programme(self, id_prog: int) -> Optional[Programme]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.PROGRAMME)} WHERE {q('ID_PROG')} = ?",
            StaffRepository.map_programme, [p(id_prog)])

    def get_programme_by_classe_matiere(self, id_classe: int, code_matiere: str) -> Optional[Programme]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.PROGRAMME)} WHERE {q('ID_CLASSE')} = ? "
            f"AND {q('CODE_MATIERE')} = ?",
            StaffRepository.map_programme, [p(id_classe), p(code_matiere)])

    def list_by_classe(self, id_classe: int) -> List[ProgrammeDetail]:
        return self.query_list(
            StaffRepository.programme_detail_sql()
            + f" WHERE P.{q('ID_CLASSE')} = ? ORDER BY M.{q('ORDRE_MAT')}, M.{q('CODE_MATIERE')}",
            StaffRepository.map_programme_detail, [p(id_classe)])

    def list_by_formateur(self, id_formateur: int) -> List[ProgrammeDetail]:
        return self.query_list(
            StaffRepository.programme_detail_sql()
            + f" WHERE P.{q('ID_FORMATEUR')} = ? ORDER BY C.{q('LIBELLE')}, M.{q('CODE_MATIERE')}",
            StaffRepository.map_programme_detail, [p(id_formateur)])

    def get_programme_detail(self, id_prog: int) -> Optional[ProgrammeDetail]:
        return self.query_single(
            StaffRepository.programme_detail_sql() + f" WHERE P.{q('ID_PROG')} = ?",
            StaffRepository.map_programme_detail, [p(id_prog)])

    @staticmethod
    def programme_detail_sql() -> str:
        return (
            f"SELECT P.*, C.{q('LIBELLE')} AS CLASSE_LIB, M.{q('MATIERE')} AS MATIERE_LIB, "
            f"M.{q('ORDRE_MAT')} AS ORDRE_MAT, F.{q('NOM')} AS FORM_NOM, F.{q('PRENOM')} AS FORM_PRENOM "
            f"FROM ((({q(Tables.PROGRAMME)} AS P "
            f"INNER JOIN {q(Tables.CLASSE)} AS C ON P.{q('ID_CLASSE')} = C.{q('ID_CLASSE')}) "
            f"INNER JOIN {q(Tables.MATIERE)} AS M ON P.{q('CODE_MATIERE')} = M.{q('CODE_MATIERE')}) "
            f"LEFT JOIN {q(Tables.FORMATEUR)} AS F ON P.{q('ID_FORMATEUR')} = F.{q('ID_FORMATEUR')})"
        )

    def insert_programme(self, programme: Programme) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.PROGRAMME)} ({q('ID_CLASSE')}, {q('CODE_MATIERE')}, "
            f"{q('ID_FORMATEUR')}, {q('COEFFICIENT')}, {q('VOL_HORAIRE')}, {q('NOTE_ELIMIN')}, "
            f"{q('OBSERVATION')}) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [p(programme.id_classe), p(programme.code_matiere), p(programme.id_formateur),
             p(programme.coefficient), p(programme.vol_horaire), p(programme.note_elimin),
             p(programme.observation)])

    def update_programme(self, programme: Programme) -> int:
        return self.execute(
            f"UPDATE {q(Tables.PROGRAMME)} SET {q('ID_CLASSE')} = ?, {q('CODE_MATIERE')} = ?, "
            f"{q('ID_FORMATEUR')} = ?, {q('COEFFICIENT')} = ?, {q('VOL_HORAIRE')} = ?, "
            f"{q('NOTE_ELIMIN')} = ?, {q('OBSERVATION')} = ? WHERE {q('ID_PROG')} = ?",
            [p(programme.id_classe), p(programme.code_matiere), p(programme.id_formateur),
             p(programme.coefficient), p(programme.vol_horaire), p(programme.note_elimin),
             p(programme.observation), p(programme.id_prog)])

    def delete_programme(self, id_prog: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.PROGRAMME)} WHERE {q('ID_PROG')} = ?", [p(id_prog)])

    # ----- Mappers -----

    @staticmethod
    def map_formateur(row: dict) -> Formateur:
        return Formateur(
            id_formateur=rm.get_int(row, "ID_FORMATEUR"),
            matricule=rm.get_string(row, "MATRICULE"),
            nom=rm.get_string(row, "NOM"),
            prenom=rm.get_string(row, "PRENOM"),
            sexe=rm.get_string(row, "SEXE"),
            date_naissance=rm.get_datetime(row, "DATE_NAISSANCE"),
            cin=rm.get_string(row, "CIN"),
            adresse=rm.get_string(row, "ADRESSE"),
            tel=rm.get_string(row, "TEL"),
            email=rm.get_string(row, "EMAIL"),
            specialite=rm.get_string(row, "SPECIALITE"),
            diplome=rm.get_string(row, "DIPLOME"),
            contrat=rm.get_string(row, "CONTRAT"),
            taux_horaire=rm.get_decimal(row, "TAUX_HORAIRE"),
            date_embauche=rm.get_datetime(row, "DATE_EMBAUCHE"),
            photo=rm.get_string(row, "PHOTO"),
            actif=rm.get_bool(row, "ACTIF"),
        )

    @staticmethod
    def map_programme(row: dict) -> Programme:
        return Programme(
            id_prog=rm.get_int(row, "ID_PROG"),
            id_classe=rm.get_int(row, "ID_CLASSE"),
            code_matiere=rm.get_string(row, "CODE_MATIERE"),
            id_formateur=rm.get_int(row, "ID_FORMATEUR"),
            coefficient=rm.get_double(row, "COEFFICIENT"),
            vol_horaire=rm.get_int(row, "VOL_HORAIRE"),
            note_elimin=rm.get_double(row, "NOTE_ELIMIN"),
            observation=rm.get_string(row, "OBSERVATION"),
        )

    @staticmethod
    def map_programme_detail(row: dict) -> ProgrammeDetail:
        nom = rm.get_string(row, "FORM_NOM")
        prenom = rm.get_string(row, "FORM_PRENOM")
        return ProgrammeDetail(
            id_prog=rm.get_int(row, "ID_PROG"),
            id_classe=rm.get_int(row, "ID_CLASSE"),
            classe=rm.get_string(row, "CLASSE_LIB"),
            code_matiere=rm.get_string(row, "CODE_MATIERE"),
            matiere=rm.get_string(row, "MATIERE_LIB"),
            id_formateur=rm.get_int(row, "ID_FORMATEUR"),
            formateur=None if not (nom or "").strip() and not (prenom or "").strip()
            else f"{nom or ''} {prenom or ''}".strip(),
            coefficient=rm.get_double(row, "COEFFICIENT"),
            vol_horaire=rm.get_int(row, "VOL_HORAIRE"),
            note_elimin=rm.get_double(row, "NOTE_ELIMIN"),
        )
