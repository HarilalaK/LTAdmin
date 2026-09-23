"""Sauvegardes de la base Access : création, liste, restauration, purge.

Une sauvegarde copie le fichier .accdb fermé (jamais pendant une transaction)
vers le sous-dossier « Sauvegardes ». La restauration conserve d'abord une
copie de sécurité « LTA_ADM_avant_restauration_*.accdb ».
"""

from __future__ import annotations

import datetime as _dt
import os
import shutil
from typing import List, Optional

from ltadmin.core.result import Result
from ltadmin.data.access_database import AccessDatabase
from ltadmin.models.dto import BackupInfo
from ltadmin.services.logging.app_logger import AppLogger

BACKUP_FOLDER_NAME = "Sauvegardes"
SAFETY_PREFIX = "LTA_ADM_avant_restauration_"


class BackupService:

    def __init__(self, database: AccessDatabase, logger: AppLogger):
        self._database = database
        self._logger = logger

    @property
    def backup_directory(self) -> str:
        return os.path.join(
            os.path.dirname(self._database.database_path) or os.getcwd(),
            BACKUP_FOLDER_NAME)

    def create_backup(self) -> Result:
        """Crée une sauvegarde datée et retourne son chemin dans le message."""
        try:
            path = self._database.create_backup()
            return Result.ok(f"Sauvegarde créée : {os.path.basename(path)}")
        except Exception as ex:
            self._logger.error("Création de sauvegarde", ex)
            return Result.fail(
                "Sauvegarde impossible : " + str(ex), "TECHNIQUE")

    def list_backups(self, include_safety_copies: bool = False) -> List[BackupInfo]:
        """Sauvegardes disponibles, de la plus récente à la plus ancienne."""
        result: List[BackupInfo] = []
        try:
            if not os.path.isdir(self.backup_directory):
                return result
            for file_name in os.listdir(self.backup_directory):
                if not file_name.lower().endswith(".accdb"):
                    continue
                if not include_safety_copies and file_name.startswith(SAFETY_PREFIX):
                    continue
                full_path = os.path.join(self.backup_directory, file_name)
                try:
                    stat = os.stat(full_path)
                except OSError:
                    continue
                result.append(BackupInfo(
                    file_path=full_path,
                    file_name=file_name,
                    created_at=_dt.datetime.fromtimestamp(stat.st_mtime),
                    size_bytes=stat.st_size))
            result.sort(key=lambda info: info.created_at or _dt.datetime.min,
                        reverse=True)
        except Exception as ex:
            self._logger.error("Liste des sauvegardes", ex)
        return result

    def restore_backup(self, backup_path: str) -> Result:
        """Restaure une sauvegarde (copie de sécurité préalable de la base)."""
        if not backup_path or not os.path.isfile(backup_path):
            return Result.fail("Fichier de sauvegarde introuvable.", "INTROUVABLE")
        if os.path.abspath(backup_path) == os.path.abspath(self._database.database_path):
            return Result.fail("Choisissez une sauvegarde, pas la base active.", "VALIDATION")
        try:
            os.makedirs(self.backup_directory, exist_ok=True)
            safety_path = os.path.join(
                self.backup_directory,
                f"{SAFETY_PREFIX}{_dt.datetime.now():%Y%m%d_%H%M%S}.accdb")
            was_open = self._database.is_open
            if self._database.in_transaction:
                return Result.fail(
                    "Restauration impossible pendant une transaction.", "GESTION")
            if was_open:
                self._database.close()
            try:
                shutil.copyfile(self._database.database_path, safety_path)
                shutil.copyfile(backup_path, self._database.database_path)
            finally:
                if was_open:
                    self._database.open()
            return Result.ok(
                f"Base restaurée depuis {os.path.basename(backup_path)} "
                f"(copie de sécurité : {os.path.basename(safety_path)}).")
        except Exception as ex:
            self._logger.error("Restauration de sauvegarde", ex)
            return Result.fail("Restauration impossible : " + str(ex), "TECHNIQUE")

    def purge_backups(self, keep_count: int = 10, include_safety_copies: bool = False) -> Result:
        """Supprime les plus anciennes sauvegardes au-delà de keep_count (≥ 1)."""
        keep_count = max(1, keep_count)
        try:
            backups = self.list_backups(include_safety_copies)
            if len(backups) <= keep_count:
                return Result.ok(
                    f"Aucune purge nécessaire ({len(backups)} sauvegarde(s) conservée(s)).")
            removed = 0
            for info in backups[keep_count:]:
                try:
                    os.remove(info.file_path)
                    removed += 1
                except OSError:
                    continue
            return Result.ok(f"{removed} sauvegarde(s) ancienne(s) supprimée(s).")
        except Exception as ex:
            self._logger.error("Purge des sauvegardes", ex)
            return Result.fail("Purge impossible : " + str(ex), "TECHNIQUE")

    @staticmethod
    def format_size(size_bytes: int) -> str:
        if size_bytes >= 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} Mo"
        if size_bytes >= 1024:
            return f"{size_bytes / 1024:.1f} Ko"
        return f"{size_bytes} o"

    @staticmethod
    def describe(info: BackupInfo) -> str:
        created = info.created_at.strftime("%d/%m/%Y %H:%M:%S") if info.created_at else "?"
        return f"{info.file_name} — {created} — {BackupService.format_size(info.size_bytes)}"
