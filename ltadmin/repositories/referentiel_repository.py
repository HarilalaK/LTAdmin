"""Dépôt du référentiel : filières, niveaux, salles, classes, modules, matières."""

from __future__ import annotations

from typing import List, Optional

from ltadmin.data import row_mapper as rm
from ltadmin.data.schema import Tables
from ltadmin.models.dto import ClasseDetail
from ltadmin.models.entities import Classe, Filiere, Matiere, ModuleFormation, Niveau, Salle
from ltadmin.repositories.base import RepositoryBase, p, q


class ReferentielRepository(RepositoryBase):

    # ----- FILIERE -----

    def list_filieres(self, actives_seulement: bool = False) -> List[Filiere]:
        if actives_seulement:
            return self.query_list(
                f"SELECT * FROM {q(Tables.FILIERE)} WHERE {q('ACTIVE')} = ? "
                f"ORDER BY {q('CODE_FILIERE')}",
                ReferentielRepository.map_filiere, [p(True)])
        return self.query_list(
            f"SELECT * FROM {q(Tables.FILIERE)} ORDER BY {q('CODE_FILIERE')}",
            ReferentielRepository.map_filiere)

    def get_filiere(self, code: str) -> Optional[Filiere]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.FILIERE)} WHERE {q('CODE_FILIERE')} = ?",
            ReferentielRepository.map_filiere, [p(code)])

    def insert_filiere(self, filiere: Filiere) -> None:
        self.execute(
            f"INSERT INTO {q(Tables.FILIERE)} ({q('CODE_FILIERE')}, {q('FILIERE')}, "
            f"{q('DIPLOME')}, {q('DUREE_ANS')}, {q('ACTIVE')}) VALUES (?, ?, ?, ?, ?)",
            [p(filiere.code_filiere), p(filiere.libelle), p(filiere.diplome),
             p(filiere.duree_ans), p(True if filiere.active is None else filiere.active)])

    def update_filiere(self, filiere: Filiere) -> int:
        return self.execute(
            f"UPDATE {q(Tables.FILIERE)} SET {q('FILIERE')} = ?, {q('DIPLOME')} = ?, "
            f"{q('DUREE_ANS')} = ?, {q('ACTIVE')} = ? WHERE {q('CODE_FILIERE')} = ?",
            [p(filiere.libelle), p(filiere.diplome), p(filiere.duree_ans),
             p(True if filiere.active is None else filiere.active), p(filiere.code_filiere)])

    def delete_filiere(self, code: str) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.FILIERE)} WHERE {q('CODE_FILIERE')} = ?", [p(code)])

    # ----- NIVEAU -----

    def list_niveaux(self) -> List[Niveau]:
        return self.query_list(
            f"SELECT * FROM {q(Tables.NIVEAU)} ORDER BY {q('ORDRE_NIV')}, {q('CODE_NIVEAU')}",
            ReferentielRepository.map_niveau)

    def get_niveau(self, code: str) -> Optional[Niveau]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.NIVEAU)} WHERE {q('CODE_NIVEAU')} = ?",
            ReferentielRepository.map_niveau, [p(code)])

    def insert_niveau(self, niveau: Niveau) -> None:
        self.execute(
            f"INSERT INTO {q(Tables.NIVEAU)} ({q('CODE_NIVEAU')}, {q('NIVEAU')}, {q('ORDRE_NIV')}) "
            f"VALUES (?, ?, ?)",
            [p(niveau.code_niveau), p(niveau.libelle), p(niveau.ordre_niv)])

    def update_niveau(self, niveau: Niveau) -> int:
        return self.execute(
            f"UPDATE {q(Tables.NIVEAU)} SET {q('NIVEAU')} = ?, {q('ORDRE_NIV')} = ? "
            f"WHERE {q('CODE_NIVEAU')} = ?",
            [p(niveau.libelle), p(niveau.ordre_niv), p(niveau.code_niveau)])

    def delete_niveau(self, code: str) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.NIVEAU)} WHERE {q('CODE_NIVEAU')} = ?", [p(code)])

    # ----- SALLE -----

    def list_salles(self, disponibles_seulement: bool = False) -> List[Salle]:
        if disponibles_seulement:
            return self.query_list(
                f"SELECT * FROM {q(Tables.SALLE)} WHERE {q('DISPONIBLE')} = ? "
                f"ORDER BY {q('NOM_SALLE')}",
                ReferentielRepository.map_salle, [p(True)])
        return self.query_list(
            f"SELECT * FROM {q(Tables.SALLE)} ORDER BY {q('NOM_SALLE')}",
            ReferentielRepository.map_salle)

    def get_salle(self, id_salle: int) -> Optional[Salle]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.SALLE)} WHERE {q('ID_SALLE')} = ?",
            ReferentielRepository.map_salle, [p(id_salle)])

    def insert_salle(self, salle: Salle) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.SALLE)} ({q('NOM_SALLE')}, {q('CAPACITE')}, "
            f"{q('NATURE_SALLE')}, {q('DISPONIBLE')}) VALUES (?, ?, ?, ?)",
            [p(salle.nom_salle), p(salle.capacite), p(salle.nature_salle),
             p(True if salle.disponible is None else salle.disponible)])

    def update_salle(self, salle: Salle) -> int:
        return self.execute(
            f"UPDATE {q(Tables.SALLE)} SET {q('NOM_SALLE')} = ?, {q('CAPACITE')} = ?, "
            f"{q('NATURE_SALLE')} = ?, {q('DISPONIBLE')} = ? WHERE {q('ID_SALLE')} = ?",
            [p(salle.nom_salle), p(salle.capacite), p(salle.nature_salle),
             p(True if salle.disponible is None else salle.disponible), p(salle.id_salle)])

    def delete_salle(self, id_salle: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.SALLE)} WHERE {q('ID_SALLE')} = ?", [p(id_salle)])

    # ----- CLASSE -----

    def list_classes(self, id_annee: Optional[int] = None) -> List[Classe]:
        if id_annee is not None:
            return self.query_list(
                f"SELECT * FROM {q(Tables.CLASSE)} WHERE {q('ID_ANNEE')} = ? "
                f"ORDER BY {q('LIBELLE')}",
                ReferentielRepository.map_classe, [p(id_annee)])
        return self.query_list(
            f"SELECT * FROM {q(Tables.CLASSE)} ORDER BY {q('LIBELLE')}",
            ReferentielRepository.map_classe)

    def get_classe(self, id_classe: int) -> Optional[Classe]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.CLASSE)} WHERE {q('ID_CLASSE')} = ?",
            ReferentielRepository.map_classe, [p(id_classe)])

    def get_classe_detail(self, id_classe: int) -> Optional[ClasseDetail]:
        return self.query_single(
            ReferentielRepository.classe_detail_sql() + f" WHERE C.{q('ID_CLASSE')} = ?",
            ReferentielRepository.map_classe_detail, [p(id_classe)])

    def list_classes_detail(self, id_annee: Optional[int] = None) -> List[ClasseDetail]:
        if id_annee is not None:
            return self.query_list(
                ReferentielRepository.classe_detail_sql()
                + f" WHERE C.{q('ID_ANNEE')} = ? ORDER BY C.{q('LIBELLE')}",
                ReferentielRepository.map_classe_detail, [p(id_annee)])
        return self.query_list(
            ReferentielRepository.classe_detail_sql() + f" ORDER BY C.{q('LIBELLE')}",
            ReferentielRepository.map_classe_detail)

    @staticmethod
    def classe_detail_sql() -> str:
        return (
            f"SELECT C.*, A.{q('LIBELLE')} AS ANNEE_LIB, F.{q('FILIERE')} AS FILIERE_LIB, "
            f"N.{q('NIVEAU')} AS NIVEAU_LIB, S.{q('NOM_SALLE')} AS SALLE_LIB "
            f"FROM (((({q(Tables.CLASSE)} AS C "
            f"LEFT JOIN {q(Tables.ANNEE_SCOLAIRE)} AS A ON C.{q('ID_ANNEE')} = A.{q('ID_ANNEE')}) "
            f"LEFT JOIN {q(Tables.FILIERE)} AS F ON C.{q('CODE_FILIERE')} = F.{q('CODE_FILIERE')}) "
            f"LEFT JOIN {q(Tables.NIVEAU)} AS N ON C.{q('CODE_NIVEAU')} = N.{q('CODE_NIVEAU')}) "
            f"LEFT JOIN {q(Tables.SALLE)} AS S ON C.{q('ID_SALLE')} = S.{q('ID_SALLE')})"
        )

    def insert_classe(self, classe: Classe) -> int:
        return self.insert_and_get_id(
            f"INSERT INTO {q(Tables.CLASSE)} ({q('LIBELLE')}, {q('ID_ANNEE')}, "
            f"{q('CODE_FILIERE')}, {q('CODE_NIVEAU')}, {q('ID_SALLE')}, {q('EFFECTIF_MAX')}, "
            f"{q('ID_RESPONSABLE')}) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [p(classe.libelle), p(classe.id_annee), p(classe.code_filiere),
             p(classe.code_niveau), p(classe.id_salle), p(classe.effectif_max),
             p(classe.id_responsable)])

    def update_classe(self, classe: Classe) -> int:
        return self.execute(
            f"UPDATE {q(Tables.CLASSE)} SET {q('LIBELLE')} = ?, {q('ID_ANNEE')} = ?, "
            f"{q('CODE_FILIERE')} = ?, {q('CODE_NIVEAU')} = ?, {q('ID_SALLE')} = ?, "
            f"{q('EFFECTIF_MAX')} = ?, {q('ID_RESPONSABLE')} = ? WHERE {q('ID_CLASSE')} = ?",
            [p(classe.libelle), p(classe.id_annee), p(classe.code_filiere),
             p(classe.code_niveau), p(classe.id_salle), p(classe.effectif_max),
             p(classe.id_responsable), p(classe.id_classe)])

    def delete_classe(self, id_classe: int) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.CLASSE)} WHERE {q('ID_CLASSE')} = ?", [p(id_classe)])

    def count_inscrits(self, id_classe: int) -> int:
        return self.scalar_int(
            f"SELECT COUNT(*) FROM {q(Tables.INSCRIPTION)} WHERE {q('ID_CLASSE')} = ?",
            [p(id_classe)])

    # ----- MODULE_FORMATION -----

    def list_modules(self, code_filiere: Optional[str] = None) -> List[ModuleFormation]:
        if not code_filiere or not code_filiere.strip():
            return self.query_list(
                f"SELECT * FROM {q(Tables.MODULE_FORMATION)} ORDER BY {q('CODE_MODULE')}",
                ReferentielRepository.map_module)
        return self.query_list(
            f"SELECT * FROM {q(Tables.MODULE_FORMATION)} WHERE {q('CODE_FILIERE')} = ? "
            f"ORDER BY {q('CODE_MODULE')}",
            ReferentielRepository.map_module, [p(code_filiere)])

    def get_module(self, code: str) -> Optional[ModuleFormation]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.MODULE_FORMATION)} WHERE {q('CODE_MODULE')} = ?",
            ReferentielRepository.map_module, [p(code)])

    def insert_module(self, module: ModuleFormation) -> None:
        self.execute(
            f"INSERT INTO {q(Tables.MODULE_FORMATION)} ({q('CODE_MODULE')}, {q('MODULE_LIB')}, "
            f"{q('CODE_FILIERE')}) VALUES (?, ?, ?)",
            [p(module.code_module), p(module.module_lib), p(module.code_filiere)])

    def update_module(self, module: ModuleFormation) -> int:
        return self.execute(
            f"UPDATE {q(Tables.MODULE_FORMATION)} SET {q('MODULE_LIB')} = ?, "
            f"{q('CODE_FILIERE')} = ? WHERE {q('CODE_MODULE')} = ?",
            [p(module.module_lib), p(module.code_filiere), p(module.code_module)])

    def delete_module(self, code: str) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.MODULE_FORMATION)} WHERE {q('CODE_MODULE')} = ?", [p(code)])

    # ----- MATIERE -----

    def list_matieres(self, code_module: Optional[str] = None) -> List[Matiere]:
        if not code_module or not code_module.strip():
            return self.query_list(
                f"SELECT * FROM {q(Tables.MATIERE)} ORDER BY {q('ORDRE_MAT')}, {q('CODE_MATIERE')}",
                ReferentielRepository.map_matiere)
        return self.query_list(
            f"SELECT * FROM {q(Tables.MATIERE)} WHERE {q('CODE_MODULE')} = ? "
            f"ORDER BY {q('ORDRE_MAT')}, {q('CODE_MATIERE')}",
            ReferentielRepository.map_matiere, [p(code_module)])

    def get_matiere(self, code: str) -> Optional[Matiere]:
        return self.query_single(
            f"SELECT * FROM {q(Tables.MATIERE)} WHERE {q('CODE_MATIERE')} = ?",
            ReferentielRepository.map_matiere, [p(code)])

    def insert_matiere(self, matiere: Matiere) -> None:
        self.execute(
            f"INSERT INTO {q(Tables.MATIERE)} ({q('CODE_MATIERE')}, {q('MATIERE')}, "
            f"{q('CODE_MODULE')}, {q('NATURE')}, {q('ORDRE_MAT')}) VALUES (?, ?, ?, ?, ?)",
            [p(matiere.code_matiere), p(matiere.libelle), p(matiere.code_module),
             p(matiere.nature), p(matiere.ordre_mat)])

    def update_matiere(self, matiere: Matiere) -> int:
        return self.execute(
            f"UPDATE {q(Tables.MATIERE)} SET {q('MATIERE')} = ?, {q('CODE_MODULE')} = ?, "
            f"{q('NATURE')} = ?, {q('ORDRE_MAT')} = ? WHERE {q('CODE_MATIERE')} = ?",
            [p(matiere.libelle), p(matiere.code_module), p(matiere.nature),
             p(matiere.ordre_mat), p(matiere.code_matiere)])

    def delete_matiere(self, code: str) -> int:
        return self.execute(
            f"DELETE FROM {q(Tables.MATIERE)} WHERE {q('CODE_MATIERE')} = ?", [p(code)])

    # ----- Mappers -----

    @staticmethod
    def map_filiere(row: dict) -> Filiere:
        return Filiere(
            code_filiere=rm.get_string(row, "CODE_FILIERE"),
            libelle=rm.get_string(row, "FILIERE"),
            diplome=rm.get_string(row, "DIPLOME"),
            duree_ans=rm.get_int(row, "DUREE_ANS"),
            active=rm.get_bool(row, "ACTIVE"),
        )

    @staticmethod
    def map_niveau(row: dict) -> Niveau:
        return Niveau(
            code_niveau=rm.get_string(row, "CODE_NIVEAU"),
            libelle=rm.get_string(row, "NIVEAU"),
            ordre_niv=rm.get_int(row, "ORDRE_NIV"),
        )

    @staticmethod
    def map_salle(row: dict) -> Salle:
        return Salle(
            id_salle=rm.get_int(row, "ID_SALLE"),
            nom_salle=rm.get_string(row, "NOM_SALLE"),
            capacite=rm.get_int(row, "CAPACITE"),
            nature_salle=rm.get_string(row, "NATURE_SALLE"),
            disponible=rm.get_bool(row, "DISPONIBLE"),
        )

    @staticmethod
    def map_classe(row: dict) -> Classe:
        return Classe(
            id_classe=rm.get_int(row, "ID_CLASSE"),
            libelle=rm.get_string(row, "LIBELLE"),
            id_annee=rm.get_int(row, "ID_ANNEE"),
            code_filiere=rm.get_string(row, "CODE_FILIERE"),
            code_niveau=rm.get_string(row, "CODE_NIVEAU"),
            id_salle=rm.get_int(row, "ID_SALLE"),
            effectif_max=rm.get_int(row, "EFFECTIF_MAX"),
            id_responsable=rm.get_int(row, "ID_RESPONSABLE"),
        )

    @staticmethod
    def map_classe_detail(row: dict) -> ClasseDetail:
        return ClasseDetail(
            id_classe=rm.get_int(row, "ID_CLASSE"),
            libelle=rm.get_string(row, "LIBELLE"),
            id_annee=rm.get_int(row, "ID_ANNEE"),
            annee=rm.get_string(row, "ANNEE_LIB"),
            code_filiere=rm.get_string(row, "CODE_FILIERE"),
            filiere=rm.get_string(row, "FILIERE_LIB"),
            code_niveau=rm.get_string(row, "CODE_NIVEAU"),
            niveau=rm.get_string(row, "NIVEAU_LIB"),
            id_salle=rm.get_int(row, "ID_SALLE"),
            salle=rm.get_string(row, "SALLE_LIB"),
            effectif_max=rm.get_int(row, "EFFECTIF_MAX"),
        )

    @staticmethod
    def map_module(row: dict) -> ModuleFormation:
        return ModuleFormation(
            code_module=rm.get_string(row, "CODE_MODULE"),
            module_lib=rm.get_string(row, "MODULE_LIB"),
            code_filiere=rm.get_string(row, "CODE_FILIERE"),
        )

    @staticmethod
    def map_matiere(row: dict) -> Matiere:
        return Matiere(
            code_matiere=rm.get_string(row, "CODE_MATIERE"),
            libelle=rm.get_string(row, "MATIERE"),
            code_module=rm.get_string(row, "CODE_MODULE"),
            nature=rm.get_string(row, "NATURE"),
            ordre_mat=rm.get_int(row, "ORDRE_MAT"),
        )
