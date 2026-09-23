"""Dépôt du planning : créneaux, emplois du temps, séances, absences."""

from __future__ import annotations

import datetime as _dt
from typing import List, Optional

from ltadmin.data import row_mapper as rm
from ltadmin.data.schema import Tables
from ltadmin.models.dto import EdtSlotDetail, SeanceDetail
from ltadmin.models.entities import Absence, Creneau, EmploiDuTemps, Seance
from ltadmin.repositories.base import RepositoryBase, p, q


class PlanningRepository(RepositoryBase):

    # ----- CRENEAU -----

    def list_creneaux(self) -> List[Creneau]:
        return self.query_list(
            f"SELECT * FROM {q(Tables.CRENEAU)} ORDER BY {q('ORDRE_CRE')}, {q('ID_CRENEAU')}",
            PlanningRepository.map_creneau)

    def get_creneau(self, id_creneau: int) -> Optional[Creneau]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.CRENEAU)} WHERE {q('ID_CRENEAU')} = ?",
            PlanningRepository.map_creneau, [p(id_creneau)])

    def insert_creneau(self, creneau: Creneau) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.CRENEAU)} ({q('LIBELLE')}, {q('HEURE_DEBUT')}, "
            f"{q('HEURE_FIN')}, {q('ORDRE_CRE')}) VALUES (?, ?, ?, ?)",
            [p(creneau.libelle), p(creneau.heure_debut), p(creneau.heure_fin),
             p(creneau.ordre_cre)])

    def update_creneau(self, creneau: Creneau) -> int:
        return self.execute(
            f"UPDATE {q(Tables.CRENEAU)} SET {q('LIBELLE')} = ?, {q('HEURE_DEBUT')} = ?, "
            f"{q('HEURE_FIN')} = ?, {q('ORDRE_CRE')} = ? WHERE {q('ID_CRENEAU')} = ?",
            [p(creneau.libelle), p(creneau.heure_debut), p(creneau.heure_fin),
             p(creneau.ordre_cre), p(creneau.id_creneau)])

    def delete_creneau(self, id_creneau: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.CRENEAU)} WHERE {q('ID_CRENEAU')} = ?", [p(id_creneau)])

    # ----- EMPLOI_DU_TEMPS -----

    def get_slot(self, id_edt: int) -> Optional[EmploiDuTemps]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.EMPLOI_DU_TEMPS)} WHERE {q('ID_EDT')} = ?",
            PlanningRepository.map_slot, [p(id_edt)])

    def get_slot_detail(self, id_edt: int) -> Optional[EdtSlotDetail]:
        return self.query_single(
            PlanningRepository.slot_detail_sql() + f" WHERE EDT.{q('ID_EDT')} = ?",
            PlanningRepository.map_slot_detail, [p(id_edt)])

    def list_slots_by_classe(self, id_classe: int, actifs_seulement: bool = True) -> List[EdtSlotDetail]:
        sql = PlanningRepository.slot_detail_sql() + f" WHERE P.{q('ID_CLASSE')} = ?"
        if actifs_seulement:
            sql += f" AND EDT.{q('ACTIF')} = ?"
        sql += f" ORDER BY CR.{q('ORDRE_CRE')}"
        if actifs_seulement:
            return self.query_list(sql, PlanningRepository.map_slot_detail, [p(id_classe), p(True)])
        return self.query_list(sql, PlanningRepository.map_slot_detail, [p(id_classe)])

    def list_slots_by_prog(self, id_prog: int) -> List[EdtSlotDetail]:
        return self.query_list(
            PlanningRepository.slot_detail_sql()
            + f" WHERE EDT.{q('ID_PROG')} = ? ORDER BY CR.{q('ORDRE_CRE')}",
            PlanningRepository.map_slot_detail, [p(id_prog)])

    def list_slots_concurrents(self, jour: str, id_creneau: int,
                               exclude_id_edt: Optional[int] = None) -> List[EdtSlotDetail]:
        """Slots actifs concurrents : même jour + même créneau (hors slot exclu).

        Le service évalue ensuite le conflit salle / formateur (EDT_CONFLIT).
        """
        sql = (PlanningRepository.slot_detail_sql()
               + f" WHERE EDT.{q('JOUR')} = ? AND EDT.{q('ID_CRENEAU')} = ? "
                 f"AND EDT.{q('ACTIF')} = ?")
        parameters = [p(jour), p(id_creneau), p(True)]
        if exclude_id_edt is not None:
            sql += f" AND EDT.{q('ID_EDT')} <> ?"
            parameters.append(p(exclude_id_edt))
        return self.query_list(sql, PlanningRepository.map_slot_detail, parameters)

    @staticmethod
    def slot_detail_sql() -> str:
        return (
            f"SELECT EDT.*, P.{q('ID_CLASSE')} AS ID_CLASSE, C.{q('LIBELLE')} AS CLASSE_LIB, "
            f"P.{q('CODE_MATIERE')} AS CODE_MATIERE, M.{q('MATIERE')} AS MATIERE_LIB, "
            f"P.{q('ID_FORMATEUR')} AS ID_FORMATEUR, F.{q('NOM')} AS FORM_NOM, "
            f"F.{q('PRENOM')} AS FORM_PRENOM, CR.{q('LIBELLE')} AS CRENEAU_LIB, "
            f"CR.{q('HEURE_DEBUT')} AS CR_DEBUT, CR.{q('HEURE_FIN')} AS CR_FIN, "
            f"S.{q('NOM_SALLE')} AS SALLE_LIB "
            f"FROM (((((({q(Tables.EMPLOI_DU_TEMPS)} AS EDT "
            f"INNER JOIN {q(Tables.PROGRAMME)} AS P ON EDT.{q('ID_PROG')} = P.{q('ID_PROG')}) "
            f"INNER JOIN {q(Tables.CLASSE)} AS C ON P.{q('ID_CLASSE')} = C.{q('ID_CLASSE')}) "
            f"INNER JOIN {q(Tables.MATIERE)} AS M ON P.{q('CODE_MATIERE')} = M.{q('CODE_MATIERE')}) "
            f"INNER JOIN {q(Tables.CRENEAU)} AS CR ON EDT.{q('ID_CRENEAU')} = CR.{q('ID_CRENEAU')}) "
            f"LEFT JOIN {q(Tables.FORMATEUR)} AS F ON P.{q('ID_FORMATEUR')} = F.{q('ID_FORMATEUR')}) "
            f"LEFT JOIN {q(Tables.SALLE)} AS S ON EDT.{q('ID_SALLE')} = S.{q('ID_SALLE')})"
        )

    def insert_slot(self, slot: EmploiDuTemps) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.EMPLOI_DU_TEMPS)} ({q('ID_PROG')}, {q('ID_CRENEAU')}, "
            f"{q('JOUR')}, {q('ID_SALLE')}, {q('DATE_DEBUT')}, {q('DATE_FIN')}, {q('ACTIF')}) "
            f"VALUES (?, ?, ?, ?, ?, ?, ?)",
            [p(slot.id_prog), p(slot.id_creneau), p(slot.jour), p(slot.id_salle),
             p(slot.date_debut), p(slot.date_fin),
             p(True if slot.actif is None else slot.actif)])

    def update_slot(self, slot: EmploiDuTemps) -> int:
        return self.execute(
            f"UPDATE {q(Tables.EMPLOI_DU_TEMPS)} SET {q('ID_PROG')} = ?, {q('ID_CRENEAU')} = ?, "
            f"{q('JOUR')} = ?, {q('ID_SALLE')} = ?, {q('DATE_DEBUT')} = ?, {q('DATE_FIN')} = ?, "
            f"{q('ACTIF')} = ? WHERE {q('ID_EDT')} = ?",
            [p(slot.id_prog), p(slot.id_creneau), p(slot.jour), p(slot.id_salle),
             p(slot.date_debut), p(slot.date_fin),
             p(True if slot.actif is None else slot.actif), p(slot.id_edt)])

    def set_slot_actif(self, id_edt: int, actif: bool) -> int:
        return self.execute(
            f"UPDATE {q(Tables.EMPLOI_DU_TEMPS)} SET {q('ACTIF')} = ? WHERE {q('ID_EDT')} = ?",
            [p(actif), p(id_edt)])

    def delete_slot(self, id_edt: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.EMPLOI_DU_TEMPS)} WHERE {q('ID_EDT')} = ?", [p(id_edt)])

    # ----- SEANCE -----

    def get_seance(self, id_seance: int) -> Optional[Seance]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.SEANCE)} WHERE {q('ID_SEANCE')} = ?",
            PlanningRepository.map_seance, [p(id_seance)])

    def list_seances_by_edt(self, id_edt: int) -> List[Seance]:
        return self.query_list(
            f"SELECT * FROM {q(Tables.SEANCE)} WHERE {q('ID_EDT')} = ? "
            f"ORDER BY {q('DATE_SEANCE')} DESC",
            PlanningRepository.map_seance, [p(id_edt)])

    def list_seances(self, debut=None, fin=None, id_classe: Optional[int] = None) -> List[SeanceDetail]:
        conditions = []
        parameters = []
        if debut is not None:
            conditions.append(f"SEA.{q('DATE_SEANCE')} >= ?")
            parameters.append(p(debut))
        if fin is not None:
            conditions.append(f"SEA.{q('DATE_SEANCE')} < ?")
            parameters.append(p(_dt.datetime.combine(fin.date(), _dt.time()) + _dt.timedelta(days=1)))
        if id_classe is not None:
            conditions.append(f"P.{q('ID_CLASSE')} = ?")
            parameters.append(p(id_classe))
        sql = PlanningRepository.seance_detail_sql()
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += f" ORDER BY SEA.{q('DATE_SEANCE')} DESC"
        return self.query_list(sql, PlanningRepository.map_seance_detail, parameters)

    @staticmethod
    def seance_detail_sql() -> str:
        return (
            f"SELECT SEA.*, EDT.{q('JOUR')} AS JOUR, CR.{q('LIBELLE')} AS CRENEAU_LIB, "
            f"C.{q('LIBELLE')} AS CLASSE_LIB, M.{q('MATIERE')} AS MATIERE_LIB "
            f"FROM ((((({q(Tables.SEANCE)} AS SEA "
            f"INNER JOIN {q(Tables.EMPLOI_DU_TEMPS)} AS EDT ON SEA.{q('ID_EDT')} = EDT.{q('ID_EDT')}) "
            f"INNER JOIN {q(Tables.PROGRAMME)} AS P ON EDT.{q('ID_PROG')} = P.{q('ID_PROG')}) "
            f"INNER JOIN {q(Tables.CLASSE)} AS C ON P.{q('ID_CLASSE')} = C.{q('ID_CLASSE')}) "
            f"INNER JOIN {q(Tables.MATIERE)} AS M ON P.{q('CODE_MATIERE')} = M.{q('CODE_MATIERE')}) "
            f"INNER JOIN {q(Tables.CRENEAU)} AS CR ON EDT.{q('ID_CRENEAU')} = CR.{q('ID_CRENEAU')})"
        )

    def insert_seance(self, seance: Seance) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.SEANCE)} ({q('ID_EDT')}, {q('DATE_SEANCE')}, {q('CONTENU')}, "
            f"{q('NB_HEURES')}, {q('STATUT')}, {q('ID_FORMATEUR_REMP')}) VALUES (?, ?, ?, ?, ?, ?)",
            [p(seance.id_edt), p(seance.date_seance), p(seance.contenu), p(seance.nb_heures),
             p(seance.statut), p(seance.id_formateur_remp)])

    def update_seance(self, seance: Seance) -> int:
        return self.execute(
            f"UPDATE {q(Tables.SEANCE)} SET {q('ID_EDT')} = ?, {q('DATE_SEANCE')} = ?, "
            f"{q('CONTENU')} = ?, {q('NB_HEURES')} = ?, {q('STATUT')} = ?, "
            f"{q('ID_FORMATEUR_REMP')} = ? WHERE {q('ID_SEANCE')} = ?",
            [p(seance.id_edt), p(seance.date_seance), p(seance.contenu), p(seance.nb_heures),
             p(seance.statut), p(seance.id_formateur_remp), p(seance.id_seance)])

    def delete_seance(self, id_seance: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.SEANCE)} WHERE {q('ID_SEANCE')} = ?", [p(id_seance)])

    def sum_heures_formateur(self, id_formateur: int, debut: _dt.datetime,
                             fin: _dt.datetime) -> float:
        """Heures réalisées par un formateur sur une période (paie)."""
        fin_exclu = _dt.datetime.combine(fin.date(), _dt.time()) + _dt.timedelta(days=1)
        value = self.scalar_double(
            f"SELECT SUM(SEA.{q('NB_HEURES')}) "
            f"FROM (({q(Tables.SEANCE)} AS SEA "
            f"INNER JOIN {q(Tables.EMPLOI_DU_TEMPS)} AS EDT ON SEA.{q('ID_EDT')} = EDT.{q('ID_EDT')}) "
            f"INNER JOIN {q(Tables.PROGRAMME)} AS P ON EDT.{q('ID_PROG')} = P.{q('ID_PROG')}) "
            f"WHERE P.{q('ID_FORMATEUR')} = ? AND SEA.{q('DATE_SEANCE')} >= ? "
            f"AND SEA.{q('DATE_SEANCE')} < ?",
            [p(id_formateur), p(debut), p(fin_exclu)])
        return value or 0.0

    # ----- ABSENCE -----

    def get_absence(self, id_absence: int) -> Optional[Absence]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.ABSENCE)} WHERE {q('ID_ABSENCE')} = ?",
            PlanningRepository.map_absence, [p(id_absence)])

    def list_absences_by_seance(self, id_seance: int) -> List[Absence]:
        return self.query_list(
            f"SELECT * FROM {q(Tables.ABSENCE)} WHERE {q('ID_SEANCE')} = ?",
            PlanningRepository.map_absence, [p(id_seance)])

    def list_absences_by_inscription(self, id_inscription: int) -> List[Absence]:
        return self.query_list(
            f"SELECT * FROM {q(Tables.ABSENCE)} WHERE {q('ID_INSCRIPTION')} = ?",
            PlanningRepository.map_absence, [p(id_inscription)])

    def sum_heures_absence(self, id_inscription: int) -> float:
        value = self.scalar_double(
            f"SELECT SUM({q('NB_HEURES')}) FROM {q(Tables.ABSENCE)} "
            f"WHERE {q('ID_INSCRIPTION')} = ?",
            [p(id_inscription)])
        return value or 0.0

    def insert_absence(self, absence: Absence) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.ABSENCE)} ({q('ID_SEANCE')}, {q('ID_INSCRIPTION')}, "
            f"{q('NATURE')}, {q('NB_HEURES')}, {q('JUSTIFIEE')}, {q('MOTIF')}, {q('DATE_SAISIE')}) "
            f"VALUES (?, ?, ?, ?, ?, ?, ?)",
            [p(absence.id_seance), p(absence.id_inscription), p(absence.nature),
             p(absence.nb_heures), p(False if absence.justifiee is None else absence.justifiee),
             p(absence.motif), p(absence.date_saisie or _dt.datetime.now())])

    def update_absence(self, absence: Absence) -> int:
        return self.execute(
            f"UPDATE {q(Tables.ABSENCE)} SET {q('ID_SEANCE')} = ?, {q('ID_INSCRIPTION')} = ?, "
            f"{q('NATURE')} = ?, {q('NB_HEURES')} = ?, {q('JUSTIFIEE')} = ?, {q('MOTIF')} = ?, "
            f"{q('DATE_SAISIE')} = ? WHERE {q('ID_ABSENCE')} = ?",
            [p(absence.id_seance), p(absence.id_inscription), p(absence.nature),
             p(absence.nb_heures), p(False if absence.justifiee is None else absence.justifiee),
             p(absence.motif), p(absence.date_saisie or _dt.datetime.now()),
             p(absence.id_absence)])

    def delete_absence(self, id_absence: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.ABSENCE)} WHERE {q('ID_ABSENCE')} = ?", [p(id_absence)])

    # ----- Mappers -----

    @staticmethod
    def map_creneau(row: dict) -> Creneau:
        return Creneau(
            id_creneau=rm.get_int(row, "ID_CRENEAU"),
            libelle=rm.get_string(row, "LIBELLE"),
            heure_debut=rm.get_string(row, "HEURE_DEBUT"),
            heure_fin=rm.get_string(row, "HEURE_FIN"),
            ordre_cre=rm.get_int(row, "ORDRE_CRE"),
        )

    @staticmethod
    def map_slot(row: dict) -> EmploiDuTemps:
        return EmploiDuTemps(
            id_edt=rm.get_int(row, "ID_EDT"),
            id_prog=rm.get_int(row, "ID_PROG"),
            id_creneau=rm.get_int(row, "ID_CRENEAU"),
            jour=rm.get_string(row, "JOUR"),
            id_salle=rm.get_int(row, "ID_SALLE"),
            date_debut=rm.get_datetime(row, "DATE_DEBUT"),
            date_fin=rm.get_datetime(row, "DATE_FIN"),
            actif=rm.get_bool(row, "ACTIF"),
        )

    @staticmethod
    def map_slot_detail(row: dict) -> EdtSlotDetail:
        nom = rm.get_string(row, "FORM_NOM")
        prenom = rm.get_string(row, "FORM_PRENOM")
        return EdtSlotDetail(
            id_edt=rm.get_int(row, "ID_EDT"),
            id_prog=rm.get_int(row, "ID_PROG"),
            id_classe=rm.get_int(row, "ID_CLASSE"),
            classe=rm.get_string(row, "CLASSE_LIB"),
            code_matiere=rm.get_string(row, "CODE_MATIERE"),
            matiere=rm.get_string(row, "MATIERE_LIB"),
            id_formateur=rm.get_int(row, "ID_FORMATEUR"),
            formateur=None if not (nom or "").strip() and not (prenom or "").strip()
            else f"{nom or ''} {prenom or ''}".strip(),
            id_creneau=rm.get_int(row, "ID_CRENEAU"),
            creneau=rm.get_string(row, "CRENEAU_LIB"),
            heure_debut=rm.get_string(row, "CR_DEBUT"),
            heure_fin=rm.get_string(row, "CR_FIN"),
            jour=rm.get_string(row, "JOUR"),
            id_salle=rm.get_int(row, "ID_SALLE"),
            salle=rm.get_string(row, "SALLE_LIB"),
            date_debut=rm.get_datetime(row, "DATE_DEBUT"),
            date_fin=rm.get_datetime(row, "DATE_FIN"),
            actif=rm.get_bool(row, "ACTIF"),
        )

    @staticmethod
    def map_seance(row: dict) -> Seance:
        return Seance(
            id_seance=rm.get_int(row, "ID_SEANCE"),
            id_edt=rm.get_int(row, "ID_EDT"),
            date_seance=rm.get_datetime(row, "DATE_SEANCE"),
            contenu=rm.get_string(row, "CONTENU"),
            nb_heures=rm.get_double(row, "NB_HEURES"),
            statut=rm.get_string(row, "STATUT"),
            id_formateur_remp=rm.get_int(row, "ID_FORMATEUR_REMP"),
        )

    @staticmethod
    def map_seance_detail(row: dict) -> SeanceDetail:
        return SeanceDetail(
            id_seance=rm.get_int(row, "ID_SEANCE"),
            id_edt=rm.get_int(row, "ID_EDT"),
            classe=rm.get_string(row, "CLASSE_LIB"),
            matiere=rm.get_string(row, "MATIERE_LIB"),
            jour=rm.get_string(row, "JOUR"),
            creneau=rm.get_string(row, "CRENEAU_LIB"),
            date_seance=rm.get_datetime(row, "DATE_SEANCE"),
            nb_heures=rm.get_double(row, "NB_HEURES"),
            statut=rm.get_string(row, "STATUT"),
        )

    @staticmethod
    def map_absence(row: dict) -> Absence:
        return Absence(
            id_absence=rm.get_int(row, "ID_ABSENCE"),
            id_seance=rm.get_int(row, "ID_SEANCE"),
            id_inscription=rm.get_int(row, "ID_INSCRIPTION"),
            nature=rm.get_string(row, "NATURE"),
            nb_heures=rm.get_double(row, "NB_HEURES"),
            justifiee=rm.get_bool(row, "JUSTIFIEE"),
            motif=rm.get_string(row, "MOTIF"),
            date_saisie=rm.get_datetime(row, "DATE_SAISIE"),
        )
