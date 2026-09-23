"""Export CSV : séparateur « ; », encodage UTF-8 avec BOM (ouverture directe
dans Excel), dates au format yyyy-MM-dd HH:mm:ss."""

from __future__ import annotations

import csv
import datetime as _dt
import io
import os
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

CSV_SEPARATOR = ";"
ENCODING = "utf-8-sig"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class CsvExporter:

    @staticmethod
    def write(path: str, columns: Sequence[str], rows: Sequence[Dict[str, Any]]) -> str:
        """Écrit les lignes dans un fichier CSV et retourne un résumé."""
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        with open(path, "w", encoding=ENCODING, newline="") as handle:
            writer = csv.writer(handle, delimiter=CSV_SEPARATOR,
                                quoting=csv.QUOTE_MINIMAL)
            writer.writerow(list(columns))
            for row in rows:
                writer.writerow([CsvExporter._cell(row.get(column))
                                 for column in columns])
        return f"{len(rows)} ligne(s) exportée(s) vers {os.path.basename(path)}"

    @staticmethod
    def to_text(columns: Sequence[str], rows: Sequence[Dict[str, Any]]) -> str:
        """Même contenu, en mémoire (aperçu avant export)."""
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=CSV_SEPARATOR, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(list(columns))
        for row in rows:
            writer.writerow([CsvExporter._cell(row.get(column)) for column in columns])
        return buffer.getvalue()

    @staticmethod
    def _cell(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, _dt.datetime):
            return value.strftime(DATE_FORMAT)
        if isinstance(value, _dt.date):
            return value.strftime("%Y-%m-%d")
        if isinstance(value, Decimal):
            return str(value).replace(".", ",")
        if isinstance(value, bool):
            return "Oui" if value else "Non"
        if isinstance(value, float):
            return f"{value:g}".replace(".", ",")
        return str(value)

    @staticmethod
    def default_file_name(title: str,
                          created_at: Optional[_dt.datetime] = None) -> str:
        """Nom de fichier proposé par défaut : etat_titre_AAAAMMJJ_HHMM.csv."""
        slug = "".join(ch if ch.isalnum() else "_" for ch in title.lower()).strip("_")
        while "__" in slug:
            slug = slug.replace("__", "_")
        moment = created_at or _dt.datetime.now()
        return f"etat_{slug}_{moment:%Y%m%d_%H%M}.csv"
