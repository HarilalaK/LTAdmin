"""Dépôt des évaluations et des notes de contrôle continu."""

from __future__ import annotations

from typing import List, Optional

from ltadmin.data import row_mapper as rm
from ltadmin.data.schema import SavedQueries, Tables
from ltadmin.models.dto import (
    EvaluationDetail,
    MoyenneMatiereRow,
    MoyennePeriodeRow,
    NoteSaisieRow,
)
from ltadmin.models.entities import Evaluation, Note, PeriodeEval
from ltadmin.repositories.base import RepositoryBase, p, q


class EvaluationRepository(RepositoryBase):

    # ----- PERIODE_EVAL -----

    def get_periode(self, id_periode: int) -> Optional[PeriodeEval]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.PERIODE_EVAL)} WHERE {q('ID_PERIODE')} = ?",
            EvaluationRepository.map_periode, [p(id_periode)])

    def list_periodes(self, id_annee: Optional[int] = None) -> List[PeriodeEval]:
        if id_annee is not None:
            return self.query_list(
                f"SELECT * FROM {q(Tables.PERIODE_EVAL)} WHERE {q('ID_ANNEE')} = ? "
                f"ORDER BY {q('ORDRE_PER')}",
                EvaluationRepository.map_periode, [p(id_annee)])
        return self.query_list(
            f"SELECT * FROM {q(Tables.PERIODE_EVAL)} ORDER BY {q('ID_ANNEE')}, {q('ORDRE_PER')}",
            EvaluationRepository.map_periode)

    def insert_periode(self, periode: PeriodeEval) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.PERIODE_EVAL)} ({q('ID_ANNEE')}, {q('CODE_PERIODE')}, "
            f"{q('LIBELLE')}, {q('ORDRE_PER')}, {q('PONDERATION')}, {q('DATE_DEBUT')}, "
            f"{q('DATE_FIN')}, {q('CLOTUREE')}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [p(periode.id_annee), p(periode.code_periode), p(periode.libelle),
             p(periode.ordre_per), p(periode.ponderation), p(periode.date_debut),
             p(periode.date_fin), p(False if periode.cloturee is None else periode.cloturee)])

    def update_periode(self, periode: PeriodeEval) -> int:
        return self.execute(
            f"UPDATE {q(Tables.PERIODE_EVAL)} SET {q('ID_ANNEE')} = ?, {q('CODE_PERIODE')} = ?, "
            f"{q('LIBELLE')} = ?, {q('ORDRE_PER')} = ?, {q('PONDERATION')} = ?, "
            f"{q('DATE_DEBUT')} = ?, {q('DATE_FIN')} = ?, {q('CLOTUREE')} = ? "
            f"WHERE {q('ID_PERIODE')} = ?",
            [p(periode.id_annee), p(periode.code_periode), p(periode.libelle),
             p(periode.ordre_per), p(periode.ponderation), p(periode.date_debut),
             p(periode.date_fin), p(False if periode.cloturee is None else periode.cloturee),
             p(periode.id_periode)])

    def set_periode_cloturee(self, id_periode: int, cloturee: bool) -> int:
        return self.execute(
            f"UPDATE {q(Tables.PERIODE_EVAL)} SET {q('CLOTUREE')} = ? WHERE {q('ID_PERIODE')} = ?",
            [p(cloturee), p(id_periode)])

    def delete_periode(self, id_periode: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.PERIODE_EVAL)} WHERE {q('ID_PERIODE')} = ?", [p(id_periode)])

    # ----- EVALUATION -----

    def get_evaluation(self, id_evaluation: int) -> Optional[Evaluation]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.EVALUATION)} WHERE {q('ID_EVALUATION')} = ?",
            EvaluationRepository.map_evaluation, [p(id_evaluation)])

    def get_evaluation_detail(self, id_evaluation: int) -> Optional[EvaluationDetail]:
        return self.query_single(
            EvaluationRepository.evaluation_detail_sql() + f" WHERE EV.{q('ID_EVALUATION')} = ?",
            EvaluationRepository.map_evaluation_detail, [p(id_evaluation)])

    def list_evaluations(self, id_periode: Optional[int] = None,
                         id_classe: Optional[int] = None,
                         id_prog: Optional[int] = None) -> List[EvaluationDetail]:
        conditions = []
        parameters = []
        if id_periode is not None:
            conditions.append(f"EV.{q('ID_PERIODE')} = ?")
            parameters.append(p(id_periode))
        if id_classe is not None:
            conditions.append(f"P.{q('ID_CLASSE')} = ?")
            parameters.append(p(id_classe))
        if id_prog is not None:
            conditions.append(f"EV.{q('ID_PROG')} = ?")
            parameters.append(p(id_prog))
        sql = EvaluationRepository.evaluation_detail_sql()
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += f" ORDER BY EV.{q('DATE_EVAL')}, EV.{q('ID_EVALUATION')}"
        return self.query_list(sql, EvaluationRepository.map_evaluation_detail, parameters)

    @staticmethod
    def evaluation_detail_sql() -> str:
        return (
            f"SELECT EV.*, PE.{q('LIBELLE')} AS PERIODE_LIB, PE.{q('CLOTUREE')} AS PERIODE_CLOTUREE, "
            f"P.{q('ID_CLASSE')} AS ID_CLASSE, C.{q('LIBELLE')} AS CLASSE_LIB, "
            f"P.{q('CODE_MATIERE')} AS CODE_MATIERE, M.{q('MATIERE')} AS MATIERE_LIB "
            f"FROM (((({q(Tables.EVALUATION)} AS EV "
            f"INNER JOIN {q(Tables.PERIODE_EVAL)} AS PE ON EV.{q('ID_PERIODE')} = PE.{q('ID_PERIODE')}) "
            f"INNER JOIN {q(Tables.PROGRAMME)} AS P ON EV.{q('ID_PROG')} = P.{q('ID_PROG')}) "
            f"INNER JOIN {q(Tables.CLASSE)} AS C ON P.{q('ID_CLASSE')} = C.{q('ID_CLASSE')}) "
            f"INNER JOIN {q(Tables.MATIERE)} AS M ON P.{q('CODE_MATIERE')} = M.{q('CODE_MATIERE')})"
        )

    def insert_evaluation(self, evaluation: Evaluation) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.EVALUATION)} ({q('ID_PERIODE')}, {q('ID_PROG')}, "
            f"{q('INTITULE')}, {q('NATURE')}, {q('DATE_EVAL')}, {q('BAREME')}, {q('POIDS')}, "
            f"{q('PUBLIEE')}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [p(evaluation.id_periode), p(evaluation.id_prog), p(evaluation.intitule),
             p(evaluation.nature), p(evaluation.date_eval), p(evaluation.bareme),
             p(evaluation.poids), p(False if evaluation.publiee is None else evaluation.publiee)])

    def update_evaluation(self, evaluation: Evaluation) -> int:
        return self.execute(
            f"UPDATE {q(Tables.EVALUATION)} SET {q('ID_PERIODE')} = ?, {q('ID_PROG')} = ?, "
            f"{q('INTITULE')} = ?, {q('NATURE')} = ?, {q('DATE_EVAL')} = ?, {q('BAREME')} = ?, "
            f"{q('POIDS')} = ?, {q('PUBLIEE')} = ? WHERE {q('ID_EVALUATION')} = ?",
            [p(evaluation.id_periode), p(evaluation.id_prog), p(evaluation.intitule),
             p(evaluation.nature), p(evaluation.date_eval), p(evaluation.bareme),
             p(evaluation.poids), p(False if evaluation.publiee is None else evaluation.publiee),
             p(evaluation.id_evaluation)])

    def set_evaluation_publiee(self, id_evaluation: int, publiee: bool) -> int:
        return self.execute(
            f"UPDATE {q(Tables.EVALUATION)} SET {q('PUBLIEE')} = ? WHERE {q('ID_EVALUATION')} = ?",
            [p(publiee), p(id_evaluation)])

    def delete_evaluation(self, id_evaluation: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.EVALUATION)} WHERE {q('ID_EVALUATION')} = ?",
            [p(id_evaluation)])

    # ----- NOTE -----

    def get_note(self, id_evaluation: int, id_inscription: int) -> Optional[Note]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.NOTE)} WHERE {q('ID_EVALUATION')} = ? "
            f"AND {q('ID_INSCRIPTION')} = ?",
            EvaluationRepository.map_note, [p(id_evaluation), p(id_inscription)])

    def list_grille_saisie(self, id_evaluation: int, id_classe: int) -> List[NoteSaisieRow]:
        """Grille de saisie : tous les inscrits de la classe + leur note éventuelle."""
        return self.query_list(
            f"SELECT N.{q('ID_NOTE')}, I.{q('ID_INSCRIPTION')}, E.{q('MATRICULE')}, "
            f"E.{q('NOM')}, E.{q('PRENOM')}, N.{q('VALEUR_NOTE')}, N.{q('ABSENT')}, "
            f"N.{q('OBSERVATION')} "
            f"FROM (({q(Tables.INSCRIPTION)} AS I "
            f"INNER JOIN {q(Tables.ETUDIANT)} AS E ON I.{q('ID_ETUDIANT')} = E.{q('ID_ETUDIANT')}) "
            f"LEFT JOIN {q(Tables.NOTE)} AS N ON N.{q('ID_INSCRIPTION')} = I.{q('ID_INSCRIPTION')} "
            f"AND N.{q('ID_EVALUATION')} = ?) "
            f"WHERE I.{q('ID_CLASSE')} = ? ORDER BY E.{q('NOM')}, E.{q('PRENOM')}",
            EvaluationRepository.map_note_saisie_row, [p(id_evaluation), p(id_classe)])

    def count_notes_by_evaluation(self, id_evaluation: int) -> int:
        return self.scalar_int(
            f"SELECT COUNT(*) FROM {q(Tables.NOTE)} WHERE {q('ID_EVALUATION')} = ?",
            [p(id_evaluation)])

    def insert_note(self, note: Note) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.NOTE)} ({q('ID_EVALUATION')}, {q('ID_INSCRIPTION')}, "
            f"{q('VALEUR_NOTE')}, {q('ABSENT')}, {q('OBSERVATION')}, {q('DATE_SAISIE')}, "
            f"{q('CODE_UTR')}) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [p(note.id_evaluation), p(note.id_inscription), p(note.valeur_note),
             p(False if note.absent is None else note.absent), p(note.observation),
             p(note.date_saisie or __import__("datetime").datetime.now()), p(note.code_utr)])

    def update_note(self, note: Note) -> int:
        return self.execute(
            f"UPDATE {q(Tables.NOTE)} SET {q('VALEUR_NOTE')} = ?, {q('ABSENT')} = ?, "
            f"{q('OBSERVATION')} = ?, {q('DATE_SAISIE')} = ?, {q('CODE_UTR')} = ? "
            f"WHERE {q('ID_NOTE')} = ?",
            [p(note.valeur_note), p(False if note.absent is None else note.absent),
             p(note.observation), p(note.date_saisie or __import__("datetime").datetime.now()),
             p(note.code_utr), p(note.id_note)])

    def delete_note(self, id_note: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.NOTE)} WHERE {q('ID_NOTE')} = ?", [p(id_note)])

    # ----- Moyennes (requêtes enregistrées) -----

    def list_moyennes_matiere(self, id_classe: Optional[int] = None,
                              id_periode: Optional[int] = None,
                              id_inscription: Optional[int] = None) -> List[MoyenneMatiereRow]:
        """Moyennes sur 20 par matière (requête R_MOYENNE_MATIERE)."""
        conditions = []
        parameters = []
        if id_classe is not None:
            conditions.append(f"{q('ID_CLASSE')} = ?")
            parameters.append(p(id_classe))
        if id_periode is not None:
            conditions.append(f"{q('ID_PERIODE')} = ?")
            parameters.append(p(id_periode))
        if id_inscription is not None:
            conditions.append(f"{q('ID_INSCRIPTION')} = ?")
            parameters.append(p(id_inscription))
        sql = f"SELECT * FROM {q(SavedQueries.MOYENNE_MATIERE)}"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        return self.query_list(sql, EvaluationRepository.map_moyenne_matiere, parameters)

    def list_moyennes_periode(self, id_classe: Optional[int] = None,
                              id_periode: Optional[int] = None) -> List[MoyennePeriodeRow]:
        """Moyennes générales pondérées par période (requête R_MOYENNE_PERIODE)."""
        conditions = []
        parameters = []
        if id_classe is not None:
            conditions.append(f"{q('ID_CLASSE')} = ?")
            parameters.append(p(id_classe))
        if id_periode is not None:
            conditions.append(f"{q('ID_PERIODE')} = ?")
            parameters.append(p(id_periode))
        sql = f"SELECT * FROM {q(SavedQueries.MOYENNE_PERIODE)}"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        return self.query_list(sql, EvaluationRepository.map_moyenne_periode, parameters)

    # ----- Mappers -----

    @staticmethod
    def map_periode(row: dict) -> PeriodeEval:
        return PeriodeEval(
            id_periode=rm.get_int(row, "ID_PERIODE"),
            id_annee=rm.get_int(row, "ID_ANNEE"),
            code_periode=rm.get_string(row, "CODE_PERIODE"),
            libelle=rm.get_string(row, "LIBELLE"),
            ordre_per=rm.get_int(row, "ORDRE_PER"),
            ponderation=rm.get_double(row, "PONDERATION"),
            date_debut=rm.get_datetime(row, "DATE_DEBUT"),
            date_fin=rm.get_datetime(row, "DATE_FIN"),
            cloturee=rm.get_bool(row, "CLOTUREE"),
        )

    @staticmethod
    def map_evaluation(row: dict) -> Evaluation:
        return Evaluation(
            id_evaluation=rm.get_int(row, "ID_EVALUATION"),
            id_periode=rm.get_int(row, "ID_PERIODE"),
            id_prog=rm.get_int(row, "ID_PROG"),
            intitule=rm.get_string(row, "INTITULE"),
            nature=rm.get_string(row, "NATURE"),
            date_eval=rm.get_datetime(row, "DATE_EVAL"),
            bareme=rm.get_double(row, "BAREME"),
            poids=rm.get_double(row, "POIDS"),
            publiee=rm.get_bool(row, "PUBLIEE"),
        )

    @staticmethod
    def map_evaluation_detail(row: dict) -> EvaluationDetail:
        return EvaluationDetail(
            id_evaluation=rm.get_int(row, "ID_EVALUATION"),
            id_periode=rm.get_int(row, "ID_PERIODE"),
            periode=rm.get_string(row, "PERIODE_LIB"),
            id_prog=rm.get_int(row, "ID_PROG"),
            id_classe=rm.get_int(row, "ID_CLASSE"),
            classe=rm.get_string(row, "CLASSE_LIB"),
            code_matiere=rm.get_string(row, "CODE_MATIERE"),
            matiere=rm.get_string(row, "MATIERE_LIB"),
            intitule=rm.get_string(row, "INTITULE"),
            nature=rm.get_string(row, "NATURE"),
            date_eval=rm.get_datetime(row, "DATE_EVAL"),
            bareme=rm.get_double(row, "BAREME"),
            poids=rm.get_double(row, "POIDS"),
            publiee=rm.get_bool(row, "PUBLIEE"),
            periode_cloturee=rm.get_bool(row, "PERIODE_CLOTUREE"),
        )

    @staticmethod
    def map_note(row: dict) -> Note:
        return Note(
            id_note=rm.get_int(row, "ID_NOTE"),
            id_evaluation=rm.get_int(row, "ID_EVALUATION"),
            id_inscription=rm.get_int(row, "ID_INSCRIPTION"),
            valeur_note=rm.get_double(row, "VALEUR_NOTE"),
            absent=rm.get_bool(row, "ABSENT"),
            observation=rm.get_string(row, "OBSERVATION"),
            date_saisie=rm.get_datetime(row, "DATE_SAISIE"),
            code_utr=rm.get_string(row, "CODE_UTR"),
        )

    @staticmethod
    def map_note_saisie_row(row: dict) -> NoteSaisieRow:
        return NoteSaisieRow(
            id_note=rm.get_int(row, "ID_NOTE"),
            id_inscription=rm.get_int(row, "ID_INSCRIPTION"),
            matricule=rm.get_string(row, "MATRICULE"),
            nom=rm.get_string(row, "NOM"),
            prenom=rm.get_string(row, "PRENOM"),
            valeur_note=rm.get_double(row, "VALEUR_NOTE"),
            absent=rm.get_bool_or(row, "ABSENT", False),
            observation=rm.get_string(row, "OBSERVATION"),
        )

    @staticmethod
    def map_moyenne_matiere(row: dict) -> MoyenneMatiereRow:
        return MoyenneMatiereRow(
            id_inscription=rm.get_int(row, "ID_INSCRIPTION"),
            id_periode=rm.get_int(row, "ID_PERIODE"),
            id_classe=rm.get_int(row, "ID_CLASSE"),
            code_matiere=rm.get_string(row, "CODE_MATIERE"),
            coefficient=rm.get_double(row, "COEFFICIENT"),
            id_formateur=rm.get_int(row, "ID_FORMATEUR"),
            moyenne_mat=rm.get_double(row, "MOYENNE_MAT"),
        )

    @staticmethod
    def map_moyenne_periode(row: dict) -> MoyennePeriodeRow:
        return MoyennePeriodeRow(
            id_inscription=rm.get_int(row, "ID_INSCRIPTION"),
            id_periode=rm.get_int(row, "ID_PERIODE"),
            id_classe=rm.get_int(row, "ID_CLASSE"),
            total_points=rm.get_double(row, "TOTAL_POINTS"),
            total_coef=rm.get_double(row, "TOTAL_COEF"),
            moyenne=rm.get_double(row, "MOYENNE"),
        )
