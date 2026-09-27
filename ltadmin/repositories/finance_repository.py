"""Dépôt des finances : tarifs, échéanciers, paiements, paie des formateurs."""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal
from typing import List, Optional

from ltadmin.data import row_mapper as rm
from ltadmin.data.schema import SavedQueries, Tables
from ltadmin.models.dto import EcheanceDetail
from ltadmin.models.entities import Echeancier, PaieFormateur, Paiement, Tarif
from ltadmin.repositories.base import RepositoryBase, p, q


class FinanceRepository(RepositoryBase):

    # ----- TARIF -----

    def get_tarif(self, id_tarif: int) -> Optional[Tarif]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.TARIF)} WHERE {q('ID_TARIF')} = ?",
            FinanceRepository.map_tarif, [p(id_tarif)])

    def list_tarifs_by_classe(self, id_classe: int) -> List[Tarif]:
        return self.query_list(
            f"SELECT * FROM {q(Tables.TARIF)} WHERE {q('ID_CLASSE')} = ? "
            f"ORDER BY {q('TYPE_FRAIS')}",
            FinanceRepository.map_tarif, [p(id_classe)])

    def insert_tarif(self, tarif: Tarif) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.TARIF)} ({q('ID_CLASSE')}, {q('TYPE_FRAIS')}, "
            f"{q('MONTANT')}, {q('NB_TRANCHES')}, {q('OBLIGATOIRE')}, {q('OBSERVATION')}) "
            f"VALUES (?, ?, ?, ?, ?, ?)",
            [p(tarif.id_classe), p(tarif.type_frais), p(tarif.montant), p(tarif.nb_tranches),
             p(True if tarif.obligatoire is None else tarif.obligatoire),
             p(tarif.observation)])

    def update_tarif(self, tarif: Tarif) -> int:
        return self.execute(
            f"UPDATE {q(Tables.TARIF)} SET {q('ID_CLASSE')} = ?, {q('TYPE_FRAIS')} = ?, "
            f"{q('MONTANT')} = ?, {q('NB_TRANCHES')} = ?, {q('OBLIGATOIRE')} = ?, "
            f"{q('OBSERVATION')} = ? WHERE {q('ID_TARIF')} = ?",
            [p(tarif.id_classe), p(tarif.type_frais), p(tarif.montant), p(tarif.nb_tranches),
             p(True if tarif.obligatoire is None else tarif.obligatoire),
             p(tarif.observation), p(tarif.id_tarif)])

    def delete_tarif(self, id_tarif: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.TARIF)} WHERE {q('ID_TARIF')} = ?", [p(id_tarif)])

    # ----- ECHEANCIER -----

    def get_echeance(self, id_echeance: int) -> Optional[Echeancier]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.ECHEANCIER)} WHERE {q('ID_ECHEANCE')} = ?",
            FinanceRepository.map_echeance, [p(id_echeance)])

    def list_echeances_by_inscription(self, id_inscription: int) -> List[EcheanceDetail]:
        """Échéances d'une inscription avec type de frais, total payé et dernier paiement."""
        return self.query_list(
            f"SELECT ECH.*, T.{q('TYPE_FRAIS')} AS TYPE_FRAIS_LIB, PE.{q('TOTAL_PAYE')}, "
            f"PE.{q('DERNIER_PAIEMENT')} "
            f"FROM (({q(Tables.ECHEANCIER)} AS ECH "
            f"LEFT JOIN {q(SavedQueries.PAIEMENT_ECHEANCE)} AS PE ON ECH.{q('ID_ECHEANCE')} = "
            f"PE.{q('ID_ECHEANCE')}) "
            f"LEFT JOIN {q(Tables.TARIF)} AS T ON ECH.{q('ID_TARIF')} = T.{q('ID_TARIF')}) "
            f"WHERE ECH.{q('ID_INSCRIPTION')} = ? "
            f"ORDER BY ECH.{q('DATE_ECHEANCE')}, ECH.{q('NUM_TRANCHE')}",
            FinanceRepository.map_echeance_detail, [p(id_inscription)])

    def count_by_inscription_tarif(self, id_inscription: int, id_tarif: int) -> int:
        return self.scalar_int(
            f"SELECT COUNT(*) FROM {q(Tables.ECHEANCIER)} WHERE {q('ID_INSCRIPTION')} = ? "
            f"AND {q('ID_TARIF')} = ?",
            [p(id_inscription), p(id_tarif)])

    def max_num_tranche(self, id_inscription: int, id_tarif: int) -> int:
        return self.scalar_int(
            f"SELECT MAX({q('NUM_TRANCHE')}) FROM {q(Tables.ECHEANCIER)} "
            f"WHERE {q('ID_INSCRIPTION')} = ? AND {q('ID_TARIF')} = ?",
            [p(id_inscription), p(id_tarif)])

    def insert_echeance(self, echeance: Echeancier) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.ECHEANCIER)} ({q('ID_INSCRIPTION')}, {q('ID_TARIF')}, "
            f"{q('NUM_TRANCHE')}, {q('LIBELLE')}, {q('MONTANT_DU')}, {q('DATE_ECHEANCE')}, "
            f"{q('STATUT')}, {q('REMISE')}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [p(echeance.id_inscription), p(echeance.id_tarif), p(echeance.num_tranche),
             p(echeance.libelle), p(echeance.montant_du), p(echeance.date_echeance),
             p(echeance.statut), p(echeance.remise)])

    def update_statut(self, id_echeance: int, statut: str) -> int:
        return self.execute(
            f"UPDATE {q(Tables.ECHEANCIER)} SET {q('STATUT')} = ? WHERE {q('ID_ECHEANCE')} = ?",
            [p(statut), p(id_echeance)])

    def update_remise(self, id_echeance: int, remise: Optional[Decimal]) -> int:
        return self.execute(
            f"UPDATE {q(Tables.ECHEANCIER)} SET {q('REMISE')} = ? WHERE {q('ID_ECHEANCE')} = ?",
            [p(remise), p(id_echeance)])

    def delete_echeance(self, id_echeance: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.ECHEANCIER)} WHERE {q('ID_ECHEANCE')} = ?", [p(id_echeance)])

    # ----- PAIEMENT -----

    def get_paiement(self, id_paiement: int) -> Optional[Paiement]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.PAIEMENT)} WHERE {q('ID_PAIEMENT')} = ?",
            FinanceRepository.map_paiement, [p(id_paiement)])

    def list_paiements_by_echeance(self, id_echeance: int) -> List[Paiement]:
        return self.query_list(
            f"SELECT * FROM {q(Tables.PAIEMENT)} WHERE {q('ID_ECHEANCE')} = ? "
            f"ORDER BY {q('DATE_PAIEMENT')}, {q('ID_PAIEMENT')}",
            FinanceRepository.map_paiement, [p(id_echeance)])

    def total_paye_by_echeance(self, id_echeance: int) -> Decimal:
        value = self.scalar_decimal(
            f"SELECT SUM({q('MONTANT')}) FROM {q(Tables.PAIEMENT)} "
            f"WHERE {q('ID_ECHEANCE')} = ?",
            [p(id_echeance)])
        return value or Decimal("0")

    def recu_existe(self, num_recu: str) -> bool:
        return self.exists(
            f"SELECT COUNT(*) FROM {q(Tables.PAIEMENT)} WHERE {q('NUM_RECU')} = ?",
            [p(num_recu)])

    def list_recus(self, prefixe: str) -> List[str]:
        table = self.query_table(
            f"SELECT {q('NUM_RECU')} FROM {q(Tables.PAIEMENT)} WHERE {q('NUM_RECU')} LIKE ?",
            [p(prefixe + "%")])
        result = []
        for row in table:
            value = rm.get_string(row, "NUM_RECU")
            if value and value.strip():
                result.append(value)
        return result

    def insert_paiement(self, paiement: Paiement) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.PAIEMENT)} ({q('ID_ECHEANCE')}, {q('NUM_RECU')}, "
            f"{q('DATE_PAIEMENT')}, {q('MONTANT')}, {q('MODE_PAIE')}, {q('REF_EXTERNE')}, "
            f"{q('CODE_UTR')}, {q('OBSERVATION')}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [p(paiement.id_echeance), p(paiement.num_recu),
             p(paiement.date_paiement or _dt.datetime.now()), p(paiement.montant),
             p(paiement.mode_paie), p(paiement.ref_externe), p(paiement.code_utr),
             p(paiement.observation)])

    def delete_paiement(self, id_paiement: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.PAIEMENT)} WHERE {q('ID_PAIEMENT')} = ?", [p(id_paiement)])

    def count_paiements(self) -> int:
        return self.scalar_int(f"SELECT COUNT(*) FROM {q(Tables.PAIEMENT)}")

    # ----- PAIE_FORMATEUR -----

    def get_paie(self, id_paie: int) -> Optional[PaieFormateur]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.PAIE_FORMATEUR)} WHERE {q('ID_PAIE')} = ?",
            FinanceRepository.map_paie, [p(id_paie)])

    def get_paie_by_formateur_periode(self, id_formateur: int, periode: str) -> Optional[PaieFormateur]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.PAIE_FORMATEUR)} WHERE {q('ID_FORMATEUR')} = ? "
            f"AND {q('PERIODE')} = ?",
            FinanceRepository.map_paie, [p(id_formateur), p(periode)])

    def list_paies_by_formateur(self, id_formateur: int) -> List[PaieFormateur]:
        return self.query_list(
            f"SELECT * FROM {q(Tables.PAIE_FORMATEUR)} WHERE {q('ID_FORMATEUR')} = ? "
            f"ORDER BY {q('PERIODE')} DESC",
            FinanceRepository.map_paie, [p(id_formateur)])

    def list_paies_by_periode(self, periode: str) -> List[PaieFormateur]:
        return self.query_list(
            f"SELECT * FROM {q(Tables.PAIE_FORMATEUR)} WHERE {q('PERIODE')} = ? "
            f"ORDER BY {q('ID_FORMATEUR')}",
            FinanceRepository.map_paie, [p(periode)])

    def insert_paie(self, paie: PaieFormateur) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.PAIE_FORMATEUR)} ({q('ID_FORMATEUR')}, {q('PERIODE')}, "
            f"{q('NB_HEURES')}, {q('TAUX')}, {q('MONTANT')}, {q('PAYE')}, {q('DATE_PAIE')}, "
            f"{q('OBSERVATION')}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [p(paie.id_formateur), p(paie.periode), p(paie.nb_heures), p(paie.taux),
             p(paie.montant), p(False if paie.paye is None else paie.paye), p(paie.date_paie),
             p(paie.observation)])

    def update_paie(self, paie: PaieFormateur) -> int:
        return self.execute(
            f"UPDATE {q(Tables.PAIE_FORMATEUR)} SET {q('NB_HEURES')} = ?, {q('TAUX')} = ?, "
            f"{q('MONTANT')} = ?, {q('PAYE')} = ?, {q('DATE_PAIE')} = ?, {q('OBSERVATION')} = ? "
            f"WHERE {q('ID_PAIE')} = ?",
            [p(paie.nb_heures), p(paie.taux), p(paie.montant),
             p(False if paie.paye is None else paie.paye), p(paie.date_paie),
             p(paie.observation), p(paie.id_paie)])

    def set_paie_payee(self, id_paie: int, paye: bool, date_paie) -> int:
        return self.execute(
            f"UPDATE {q(Tables.PAIE_FORMATEUR)} SET {q('PAYE')} = ?, {q('DATE_PAIE')} = ? "
            f"WHERE {q('ID_PAIE')} = ?",
            [p(paye), p(date_paie), p(id_paie)])

    def delete_paie(self, id_paie: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.PAIE_FORMATEUR)} WHERE {q('ID_PAIE')} = ?", [p(id_paie)])

    # ----- Mappers -----

    @staticmethod
    def map_tarif(row: dict) -> Tarif:
        return Tarif(
            id_tarif=rm.get_int(row, "ID_TARIF"),
            id_classe=rm.get_int(row, "ID_CLASSE"),
            type_frais=rm.get_string(row, "TYPE_FRAIS"),
            montant=rm.get_decimal(row, "MONTANT"),
            nb_tranches=rm.get_int(row, "NB_TRANCHES"),
            obligatoire=rm.get_bool(row, "OBLIGATOIRE"),
            observation=rm.get_string(row, "OBSERVATION"),
        )

    @staticmethod
    def map_echeance(row: dict) -> Echeancier:
        return Echeancier(
            id_echeance=rm.get_int(row, "ID_ECHEANCE"),
            id_inscription=rm.get_int(row, "ID_INSCRIPTION"),
            id_tarif=rm.get_int(row, "ID_TARIF"),
            num_tranche=rm.get_int(row, "NUM_TRANCHE"),
            libelle=rm.get_string(row, "LIBELLE"),
            montant_du=rm.get_decimal(row, "MONTANT_DU"),
            date_echeance=rm.get_datetime(row, "DATE_ECHEANCE"),
            statut=rm.get_string(row, "STATUT"),
            remise=rm.get_decimal(row, "REMISE"),
        )

    @staticmethod
    def map_echeance_detail(row: dict) -> EcheanceDetail:
        return EcheanceDetail(
            id_echeance=rm.get_int(row, "ID_ECHEANCE"),
            id_inscription=rm.get_int(row, "ID_INSCRIPTION"),
            id_tarif=rm.get_int(row, "ID_TARIF"),
            type_frais=rm.get_string(row, "TYPE_FRAIS_LIB"),
            num_tranche=rm.get_int(row, "NUM_TRANCHE"),
            libelle=rm.get_string(row, "LIBELLE"),
            montant_du=rm.get_decimal(row, "MONTANT_DU"),
            date_echeance=rm.get_datetime(row, "DATE_ECHEANCE"),
            statut=rm.get_string(row, "STATUT"),
            remise=rm.get_decimal(row, "REMISE"),
            total_paye=rm.get_decimal_or(row, "TOTAL_PAYE", Decimal("0")),
            dernier_paiement=rm.get_datetime(row, "DERNIER_PAIEMENT"),
        )

    @staticmethod
    def map_paiement(row: dict) -> Paiement:
        return Paiement(
            id_paiement=rm.get_int(row, "ID_PAIEMENT"),
            id_echeance=rm.get_int(row, "ID_ECHEANCE"),
            num_recu=rm.get_string(row, "NUM_RECU"),
            date_paiement=rm.get_datetime(row, "DATE_PAIEMENT"),
            montant=rm.get_decimal(row, "MONTANT"),
            mode_paie=rm.get_string(row, "MODE_PAIE"),
            ref_externe=rm.get_string(row, "REF_EXTERNE"),
            code_utr=rm.get_string(row, "CODE_UTR"),
            observation=rm.get_string(row, "OBSERVATION"),
        )

    @staticmethod
    def map_paie(row: dict) -> PaieFormateur:
        return PaieFormateur(
            id_paie=rm.get_int(row, "ID_PAIE"),
            id_formateur=rm.get_int(row, "ID_FORMATEUR"),
            periode=rm.get_string(row, "PERIODE"),
            nb_heures=rm.get_double(row, "NB_HEURES"),
            taux=rm.get_decimal(row, "TAUX"),
            montant=rm.get_decimal(row, "MONTANT"),
            paye=rm.get_bool(row, "PAYE"),
            date_paie=rm.get_datetime(row, "DATE_PAIE"),
            observation=rm.get_string(row, "OBSERVATION"),
        )
