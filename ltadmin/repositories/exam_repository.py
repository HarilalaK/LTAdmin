"""Dépôt des examens : sessions, épreuves, notes d'examen."""

from __future__ import annotations

import datetime as _dt
from typing import List, Optional

from ltadmin.data import row_mapper as rm
from ltadmin.data.schema import Tables
from ltadmin.models.dto import EpreuveDetail, NoteSaisieRow
from ltadmin.models.entities import Epreuve, NoteExamen, SessionExam
from ltadmin.repositories.base import RepositoryBase, p, q
from ltadmin.repositories.evaluation_repository import EvaluationRepository


class ExamRepository(RepositoryBase):

    # ----- SESSION_EXAM -----

    def get_session(self, id_session: int) -> Optional[SessionExam]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.SESSION_EXAM)} WHERE {q('ID_SESSION')} = ?",
            ExamRepository.map_session, [p(id_session)])

    def list_sessions(self, id_annee: Optional[int] = None) -> List[SessionExam]:
        if id_annee is not None:
            return self.query_list(
                f"SELECT * FROM {q(Tables.SESSION_EXAM)} WHERE {q('ID_ANNEE')} = ? "
                f"ORDER BY {q('DATE_DEBUT')}, {q('LIBELLE')}",
                ExamRepository.map_session, [p(id_annee)])
        return self.query_list(
            f"SELECT * FROM {q(Tables.SESSION_EXAM)} ORDER BY {q('ID_ANNEE')} DESC, "
            f"{q('DATE_DEBUT')}",
            ExamRepository.map_session)

    def insert_session(self, session: SessionExam) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.SESSION_EXAM)} ({q('ID_ANNEE')}, {q('LIBELLE')}, "
            f"{q('NATURE')}, {q('DATE_DEBUT')}, {q('DATE_FIN')}, {q('CLOTUREE')}) "
            f"VALUES (?, ?, ?, ?, ?, ?)",
            [p(session.id_annee), p(session.libelle), p(session.nature),
             p(session.date_debut), p(session.date_fin),
             p(False if session.cloturee is None else session.cloturee)])

    def update_session(self, session: SessionExam) -> int:
        return self.execute(
            f"UPDATE {q(Tables.SESSION_EXAM)} SET {q('ID_ANNEE')} = ?, {q('LIBELLE')} = ?, "
            f"{q('NATURE')} = ?, {q('DATE_DEBUT')} = ?, {q('DATE_FIN')} = ?, {q('CLOTUREE')} = ? "
            f"WHERE {q('ID_SESSION')} = ?",
            [p(session.id_annee), p(session.libelle), p(session.nature),
             p(session.date_debut), p(session.date_fin),
             p(False if session.cloturee is None else session.cloturee), p(session.id_session)])

    def set_session_cloturee(self, id_session: int, cloturee: bool) -> int:
        return self.execute(
            f"UPDATE {q(Tables.SESSION_EXAM)} SET {q('CLOTUREE')} = ? WHERE {q('ID_SESSION')} = ?",
            [p(cloturee), p(id_session)])

    def delete_session(self, id_session: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.SESSION_EXAM)} WHERE {q('ID_SESSION')} = ?", [p(id_session)])

    # ----- EPREUVE -----

    def get_epreuve(self, id_epreuve: int) -> Optional[Epreuve]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.EPREUVE)} WHERE {q('ID_EPREUVE')} = ?",
            ExamRepository.map_epreuve, [p(id_epreuve)])

    def get_epreuve_detail(self, id_epreuve: int) -> Optional[EpreuveDetail]:
        return self.query_single(
            ExamRepository.epreuve_detail_sql() + f" WHERE EP.{q('ID_EPREUVE')} = ?",
            ExamRepository.map_epreuve_detail, [p(id_epreuve)])

    def list_epreuves(self, id_session: Optional[int] = None,
                      id_classe: Optional[int] = None) -> List[EpreuveDetail]:
        conditions = []
        parameters = []
        if id_session is not None:
            conditions.append(f"EP.{q('ID_SESSION')} = ?")
            parameters.append(p(id_session))
        if id_classe is not None:
            conditions.append(f"EP.{q('ID_CLASSE')} = ?")
            parameters.append(p(id_classe))
        sql = ExamRepository.epreuve_detail_sql()
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += f" ORDER BY EP.{q('DATE_EPREUVE')}, EP.{q('ID_EPREUVE')}"
        return self.query_list(sql, ExamRepository.map_epreuve_detail, parameters)

    @staticmethod
    def epreuve_detail_sql() -> str:
        return (
            f"SELECT EP.*, SE.{q('LIBELLE')} AS SESSION_LIB, C.{q('LIBELLE')} AS CLASSE_LIB, "
            f"M.{q('MATIERE')} AS MATIERE_LIB, S.{q('NOM_SALLE')} AS SALLE_LIB "
            f"FROM (((({q(Tables.EPREUVE)} AS EP "
            f"INNER JOIN {q(Tables.SESSION_EXAM)} AS SE ON EP.{q('ID_SESSION')} = SE.{q('ID_SESSION')}) "
            f"INNER JOIN {q(Tables.CLASSE)} AS C ON EP.{q('ID_CLASSE')} = C.{q('ID_CLASSE')}) "
            f"INNER JOIN {q(Tables.MATIERE)} AS M ON EP.{q('CODE_MATIERE')} = M.{q('CODE_MATIERE')}) "
            f"LEFT JOIN {q(Tables.SALLE)} AS S ON EP.{q('ID_SALLE')} = S.{q('ID_SALLE')})"
        )

    def insert_epreuve(self, epreuve: Epreuve) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.EPREUVE)} ({q('ID_SESSION')}, {q('ID_CLASSE')}, "
            f"{q('CODE_MATIERE')}, {q('DATE_EPREUVE')}, {q('HEURE_DEBUT')}, {q('DUREE_MN')}, "
            f"{q('COEFFICIENT')}, {q('BAREME')}, {q('ID_SALLE')}, {q('SURVEILLANT')}) "
            f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [p(epreuve.id_session), p(epreuve.id_classe), p(epreuve.code_matiere),
             p(epreuve.date_epreuve), p(epreuve.heure_debut), p(epreuve.duree_mn),
             p(epreuve.coefficient), p(epreuve.bareme), p(epreuve.id_salle),
             p(epreuve.surveillant)])

    def update_epreuve(self, epreuve: Epreuve) -> int:
        return self.execute(
            f"UPDATE {q(Tables.EPREUVE)} SET {q('ID_SESSION')} = ?, {q('ID_CLASSE')} = ?, "
            f"{q('CODE_MATIERE')} = ?, {q('DATE_EPREUVE')} = ?, {q('HEURE_DEBUT')} = ?, "
            f"{q('DUREE_MN')} = ?, {q('COEFFICIENT')} = ?, {q('BAREME')} = ?, {q('ID_SALLE')} = ?, "
            f"{q('SURVEILLANT')} = ? WHERE {q('ID_EPREUVE')} = ?",
            [p(epreuve.id_session), p(epreuve.id_classe), p(epreuve.code_matiere),
             p(epreuve.date_epreuve), p(epreuve.heure_debut), p(epreuve.duree_mn),
             p(epreuve.coefficient), p(epreuve.bareme), p(epreuve.id_salle),
             p(epreuve.surveillant), p(epreuve.id_epreuve)])

    def delete_epreuve(self, id_epreuve: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.EPREUVE)} WHERE {q('ID_EPREUVE')} = ?", [p(id_epreuve)])

    # ----- NOTE_EXAMEN -----

    def get_note_examen(self, id_epreuve: int, id_inscription: int) -> Optional[NoteExamen]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.NOTE_EXAMEN)} WHERE {q('ID_EPREUVE')} = ? "
            f"AND {q('ID_INSCRIPTION')} = ?",
            ExamRepository.map_note_examen, [p(id_epreuve), p(id_inscription)])

    def list_grille_saisie(self, id_epreuve: int, id_classe: int) -> List[NoteSaisieRow]:
        return self.query_list(
            f"SELECT N.{q('ID_NOTE_EX')} AS ID_NOTE, I.{q('ID_INSCRIPTION')}, "
            f"E.{q('MATRICULE')}, E.{q('NOM')}, E.{q('PRENOM')}, N.{q('VALEUR_NOTE')}, "
            f"N.{q('ABSENT')} "
            f"FROM (({q(Tables.INSCRIPTION)} AS I "
            f"INNER JOIN {q(Tables.ETUDIANT)} AS E ON I.{q('ID_ETUDIANT')} = E.{q('ID_ETUDIANT')}) "
            f"LEFT JOIN {q(Tables.NOTE_EXAMEN)} AS N ON N.{q('ID_INSCRIPTION')} = "
            f"I.{q('ID_INSCRIPTION')} AND N.{q('ID_EPREUVE')} = ?) "
            f"WHERE I.{q('ID_CLASSE')} = ? ORDER BY E.{q('NOM')}, E.{q('PRENOM')}",
            EvaluationRepository.map_note_saisie_row, [p(id_epreuve), p(id_classe)])

    def count_notes_by_epreuve(self, id_epreuve: int) -> int:
        return self.scalar_int(
            f"SELECT COUNT(*) FROM {q(Tables.NOTE_EXAMEN)} WHERE {q('ID_EPREUVE')} = ?",
            [p(id_epreuve)])

    def insert_note_examen(self, note: NoteExamen) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.NOTE_EXAMEN)} ({q('ID_EPREUVE')}, {q('ID_INSCRIPTION')}, "
            f"{q('VALEUR_NOTE')}, {q('ABSENT')}, {q('COPIE_NUM')}, {q('DATE_SAISIE')}, "
            f"{q('CODE_UTR')}) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [p(note.id_epreuve), p(note.id_inscription), p(note.valeur_note),
             p(False if note.absent is None else note.absent), p(note.copie_num),
             p(note.date_saisie or _dt.datetime.now()), p(note.code_utr)])

    def update_note_examen(self, note: NoteExamen) -> int:
        return self.execute(
            f"UPDATE {q(Tables.NOTE_EXAMEN)} SET {q('VALEUR_NOTE')} = ?, {q('ABSENT')} = ?, "
            f"{q('COPIE_NUM')} = ?, {q('DATE_SAISIE')} = ?, {q('CODE_UTR')} = ? "
            f"WHERE {q('ID_NOTE_EX')} = ?",
            [p(note.valeur_note), p(False if note.absent is None else note.absent),
             p(note.copie_num), p(note.date_saisie or _dt.datetime.now()),
             p(note.code_utr), p(note.id_note_ex)])

    def delete_note_examen(self, id_note_ex: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.NOTE_EXAMEN)} WHERE {q('ID_NOTE_EX')} = ?", [p(id_note_ex)])

    def list_notes_ponderes(self, id_classe: int, id_session: int) -> List[dict]:
        """Notes d'examen pondérables d'une classe pour une session."""
        return self.query_table(
            f"SELECT N.{q('ID_INSCRIPTION')}, N.{q('VALEUR_NOTE')}, N.{q('ABSENT')}, "
            f"EP.{q('BAREME')}, EP.{q('COEFFICIENT')}, EP.{q('CODE_MATIERE')} "
            f"FROM {q(Tables.NOTE_EXAMEN)} AS N "
            f"INNER JOIN {q(Tables.EPREUVE)} AS EP ON N.{q('ID_EPREUVE')} = EP.{q('ID_EPREUVE')} "
            f"WHERE EP.{q('ID_CLASSE')} = ? AND EP.{q('ID_SESSION')} = ?",
            [p(id_classe), p(id_session)])

    # ----- Mappers -----

    @staticmethod
    def map_session(row: dict) -> SessionExam:
        return SessionExam(
            id_session=rm.get_int(row, "ID_SESSION"),
            id_annee=rm.get_int(row, "ID_ANNEE"),
            libelle=rm.get_string(row, "LIBELLE"),
            nature=rm.get_string(row, "NATURE"),
            date_debut=rm.get_datetime(row, "DATE_DEBUT"),
            date_fin=rm.get_datetime(row, "DATE_FIN"),
            cloturee=rm.get_bool(row, "CLOTUREE"),
        )

    @staticmethod
    def map_epreuve(row: dict) -> Epreuve:
        return Epreuve(
            id_epreuve=rm.get_int(row, "ID_EPREUVE"),
            id_session=rm.get_int(row, "ID_SESSION"),
            id_classe=rm.get_int(row, "ID_CLASSE"),
            code_matiere=rm.get_string(row, "CODE_MATIERE"),
            date_epreuve=rm.get_datetime(row, "DATE_EPREUVE"),
            heure_debut=rm.get_string(row, "HEURE_DEBUT"),
            duree_mn=rm.get_int(row, "DUREE_MN"),
            coefficient=rm.get_double(row, "COEFFICIENT"),
            bareme=rm.get_double(row, "BAREME"),
            id_salle=rm.get_int(row, "ID_SALLE"),
            surveillant=rm.get_string(row, "SURVEILLANT"),
        )

    @staticmethod
    def map_epreuve_detail(row: dict) -> EpreuveDetail:
        return EpreuveDetail(
            id_epreuve=rm.get_int(row, "ID_EPREUVE"),
            id_session=rm.get_int(row, "ID_SESSION"),
            session=rm.get_string(row, "SESSION_LIB"),
            id_classe=rm.get_int(row, "ID_CLASSE"),
            classe=rm.get_string(row, "CLASSE_LIB"),
            code_matiere=rm.get_string(row, "CODE_MATIERE"),
            matiere=rm.get_string(row, "MATIERE_LIB"),
            date_epreuve=rm.get_datetime(row, "DATE_EPREUVE"),
            heure_debut=rm.get_string(row, "HEURE_DEBUT"),
            duree_mn=rm.get_int(row, "DUREE_MN"),
            coefficient=rm.get_double(row, "COEFFICIENT"),
            bareme=rm.get_double(row, "BAREME"),
            id_salle=rm.get_int(row, "ID_SALLE"),
            salle=rm.get_string(row, "SALLE_LIB"),
            surveillant=rm.get_string(row, "SURVEILLANT"),
        )

    @staticmethod
    def map_note_examen(row: dict) -> NoteExamen:
        return NoteExamen(
            id_note_ex=rm.get_int(row, "ID_NOTE_EX"),
            id_epreuve=rm.get_int(row, "ID_EPREUVE"),
            id_inscription=rm.get_int(row, "ID_INSCRIPTION"),
            valeur_note=rm.get_double(row, "VALEUR_NOTE"),
            absent=rm.get_bool(row, "ABSENT"),
            copie_num=rm.get_string(row, "COPIE_NUM"),
            date_saisie=rm.get_datetime(row, "DATE_SAISIE"),
            code_utr=rm.get_string(row, "CODE_UTR"),
        )
