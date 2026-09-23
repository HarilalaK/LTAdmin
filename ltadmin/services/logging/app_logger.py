"""Journal technique sur fichier (logs/ltadmin-AAAAMMJJ.log).

Complète le journal applicatif en base (table JOURNAL) : ici les erreurs
techniques et la trace de démarrage, là-bas les opérations métier.
La journalisation ne doit jamais faire échouer l'application.
"""

from __future__ import annotations

import datetime as _dt
import os
import sys
import threading
import traceback
from typing import Optional


class AppLogger:

    def __init__(self, log_directory: Optional[str] = None):
        self._lock = threading.Lock()
        self._log_directory = log_directory or AppLogger.default_log_directory()

    @staticmethod
    def default_log_directory() -> str:
        try:
            base = os.path.dirname(os.path.abspath(sys.argv[0])) or os.getcwd()
            directory = os.path.join(base, "logs")
            os.makedirs(directory, exist_ok=True)
            return directory
        except Exception:
            return os.path.join(os.environ.get("TEMP", "/tmp"), "LTAdmin-logs")

    def info(self, message: str) -> None:
        self._write("INFO", message, None)

    def warning(self, message: str) -> None:
        self._write("AVERT", message, None)

    def error(self, operation: str, exception: BaseException) -> None:
        detail = "".join(traceback.format_exception(
            type(exception), exception, exception.__traceback__))
        self._write("ERREUR", f"{operation} : {exception}", detail)

    def _write(self, level: str, message: str, detail: Optional[str]) -> None:
        try:
            os.makedirs(self._log_directory, exist_ok=True)
            file_name = os.path.join(
                self._log_directory, f"ltadmin-{_dt.datetime.now():%Y%m%d}.log")
            stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            lines = [f"{stamp} [{level}] {message}"]
            if detail and detail.strip():
                lines.append(detail.rstrip())
            with self._lock:
                with open(file_name, "a", encoding="utf-8") as handle:
                    handle.write("\n".join(lines) + "\n")
        except Exception:
            # La journalisation ne doit jamais faire échouer l'application.
            pass
