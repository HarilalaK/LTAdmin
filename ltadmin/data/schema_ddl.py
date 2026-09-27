"""Schéma SQLite renforcé de LTA_ADM : DDL, relations, index et vues.

Le fichier ``LTA_ADM.sqlite3`` issu de la conversion Access → SQLite ne
portait ni clé primaire, ni clé étrangère, ni index : les colonnes ``ID_*``
ne s'auto-incrémentaient donc pas. Ce module décrit le schéma cible
(mêmes 33 tables, mêmes colonnes, mêmes noms) enrichi de :

- clés primaires ``INTEGER PRIMARY KEY AUTOINCREMENT`` (AutoNumber Access)
  ou clés naturelles (``CODE_*``, ``CLE``) ;
- clés étrangères et index uniques tels qu'ils existaient dans le .accdb
  (``analysis/extraction_complete.json`` de l'ancien dépôt) ;
- les 8 requêtes enregistrées Access recréées en vues SQLite (``R_*``).

:func:`migrate_database` convertit un fichier « plat » vers ce schéma en
conservant toutes les données (avec copie de sauvegarde préalable) ;
:func:`create_database` crée une base neuve avec le référentiel initial.
"""

from __future__ import annotations

import datetime as _dt
import os
import shutil
import sqlite3
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from ltadmin.data.schema_catalog import TABLES

SCHEMA_VERSION = 1

# Clés étrangères : table → [(nom, colonnes locales, table référencée)].
# La colonne référencée est toujours la clé primaire de la table cible.
FOREIGN_KEYS: Dict[str, List[Tuple[str, Tuple[str, ...], str]]] = {
    "ABSENCE": [("FK_ABS_INS", ("ID_INSCRIPTION",), "INSCRIPTION"),
                ("FK_ABS_SEA", ("ID_SEANCE",), "SEANCE")],
    "BULLETIN": [("FK_BUL_INS", ("ID_INSCRIPTION",), "INSCRIPTION"),
                 ("FK_BUL_PER", ("ID_PERIODE",), "PERIODE_EVAL")],
    "BULLETIN_LIGNE": [("FK_BLI_BUL", ("ID_BULLETIN",), "BULLETIN"),
                       ("FK_BLI_FORM", ("ID_FORMATEUR",), "FORMATEUR"),
                       ("FK_BLI_MAT", ("CODE_MATIERE",), "MATIERE")],
    "CLASSE": [("FK_CLA_ANNEE", ("ID_ANNEE",), "ANNEE_SCOLAIRE"),
               ("FK_CLA_FIL", ("CODE_FILIERE",), "FILIERE"),
               ("FK_CLA_NIV", ("CODE_NIVEAU",), "NIVEAU"),
               ("FK_CLA_SALLE", ("ID_SALLE",), "SALLE")],
    "ECHEANCIER": [("FK_ECH_INS", ("ID_INSCRIPTION",), "INSCRIPTION"),
                   ("FK_ECH_TAR", ("ID_TARIF",), "TARIF")],
    "EMPLOI_DU_TEMPS": [("FK_EDT_CRE", ("ID_CRENEAU",), "CRENEAU"),
                        ("FK_EDT_PRO", ("ID_PROG",), "PROGRAMME"),
                        ("FK_EDT_SALLE", ("ID_SALLE",), "SALLE")],
    "EPREUVE": [("FK_EPR_CLA", ("ID_CLASSE",), "CLASSE"),
                ("FK_EPR_MAT", ("CODE_MATIERE",), "MATIERE"),
                ("FK_EPR_SALLE", ("ID_SALLE",), "SALLE"),
                ("FK_EPR_SES", ("ID_SESSION",), "SESSION_EXAM")],
    "EVALUATION": [("FK_EVA_PER", ("ID_PERIODE",), "PERIODE_EVAL"),
                   ("FK_EVA_PRO", ("ID_PROG",), "PROGRAMME")],
    "INSCRIPTION": [("FK_INS_CLA", ("ID_CLASSE",), "CLASSE"),
                    ("FK_INS_ETU", ("ID_ETUDIANT",), "ETUDIANT")],
    "MATIERE": [("FK_MAT_MOD", ("CODE_MODULE",), "MODULE_FORMATION")],
    "MODULE_FORMATION": [("FK_MOD_FIL", ("CODE_FILIERE",), "FILIERE")],
    "NOTE": [("FK_NOT_EVA", ("ID_EVALUATION",), "EVALUATION"),
             ("FK_NOT_INS", ("ID_INSCRIPTION",), "INSCRIPTION")],
    "NOTE_EXAMEN": [("FK_NEX_EPR", ("ID_EPREUVE",), "EPREUVE"),
                    ("FK_NEX_INS", ("ID_INSCRIPTION",), "INSCRIPTION")],
    "PAIEMENT": [("FK_PAI_ECH", ("ID_ECHEANCE",), "ECHEANCIER")],
    "PAIE_FORMATEUR": [("FK_PAF_FORM", ("ID_FORMATEUR",), "FORMATEUR")],
    "PERIODE_EVAL": [("FK_PER_ANNEE", ("ID_ANNEE",), "ANNEE_SCOLAIRE")],
    "PROGRAMME": [("FK_PRO_CLA", ("ID_CLASSE",), "CLASSE"),
                  ("FK_PRO_FORM", ("ID_FORMATEUR",), "FORMATEUR"),
                  ("FK_PRO_MAT", ("CODE_MATIERE",), "MATIERE")],
    "RESULTAT_FINAL": [("FK_RES_INS", ("ID_INSCRIPTION",), "INSCRIPTION")],
    "SEANCE": [("FK_SEA_EDT", ("ID_EDT",), "EMPLOI_DU_TEMPS")],
    "SESSION_EXAM": [("FK_SES_ANNEE", ("ID_ANNEE",), "ANNEE_SCOLAIRE")],
    "TARIF": [("FK_TAR_CLA", ("ID_CLASSE",), "CLASSE")],
}

# Index : table → [(nom, colonnes, unique)]. Les index de clé étrangère sont
# créés automatiquement à partir de FOREIGN_KEYS.
INDEXES: Dict[str, List[Tuple[str, Tuple[str, ...], bool]]] = {
    "BULLETIN": [("IX_BUL_UNI", ("ID_INSCRIPTION", "ID_PERIODE"), True)],
    "EMPLOI_DU_TEMPS": [("IX_EDT_SLOT", ("JOUR", "ID_CRENEAU", "ID_SALLE"), False)],
    "ETUDIANT": [("IX_ETU_MAT", ("MATRICULE",), True)],
    "INSCRIPTION": [("IX_INS_UNI", ("ID_ETUDIANT", "ID_CLASSE"), True)],
    "NOTE": [("IX_NOTE_UNI", ("ID_EVALUATION", "ID_INSCRIPTION"), True)],
    "NOTE_EXAMEN": [("IX_NEX_UNI", ("ID_EPREUVE", "ID_INSCRIPTION"), True)],
    "PAIEMENT": [("IX_PAI_RECU", ("NUM_RECU",), True)],
    "PROGRAMME": [("IX_PROG_UNI", ("ID_CLASSE", "CODE_MATIERE"), True)],
    "JOURNAL": [("IX_LOG_DATE", ("DATE_LOG",), False)],
}

# Les 8 requêtes enregistrées Access, en dialecte SQLite.
VIEWS: Dict[str, str] = {
    "R_PAIEMENT_ECHEANCE": """
        SELECT ID_ECHEANCE, SUM(MONTANT) AS TOTAL_PAYE,
               MAX(DATE_PAIEMENT) AS DERNIER_PAIEMENT
        FROM PAIEMENT GROUP BY ID_ECHEANCE""",
    "R_MOYENNE_MATIERE": """
        SELECT I.ID_INSCRIPTION, EV.ID_PERIODE, P.ID_CLASSE, P.CODE_MATIERE,
               P.COEFFICIENT, P.ID_FORMATEUR,
               SUM(N.VALEUR_NOTE / EV.BAREME * 20 * EV.POIDS) / SUM(EV.POIDS)
                   AS MOYENNE_MAT
        FROM NOTE AS N
        INNER JOIN EVALUATION AS EV ON N.ID_EVALUATION = EV.ID_EVALUATION
        INNER JOIN PROGRAMME AS P ON EV.ID_PROG = P.ID_PROG
        INNER JOIN INSCRIPTION AS I ON N.ID_INSCRIPTION = I.ID_INSCRIPTION
        WHERE IFNULL(N.ABSENT, 0) = 0 AND N.VALEUR_NOTE IS NOT NULL
        GROUP BY I.ID_INSCRIPTION, EV.ID_PERIODE, P.ID_CLASSE, P.CODE_MATIERE,
                 P.COEFFICIENT, P.ID_FORMATEUR""",
    "R_MOYENNE_PERIODE": """
        SELECT ID_INSCRIPTION, ID_PERIODE, ID_CLASSE,
               SUM(MOYENNE_MAT * COEFFICIENT) AS TOTAL_POINTS,
               SUM(COEFFICIENT) AS TOTAL_COEF,
               SUM(MOYENNE_MAT * COEFFICIENT) / SUM(COEFFICIENT) AS MOYENNE
        FROM R_MOYENNE_MATIERE
        GROUP BY ID_INSCRIPTION, ID_PERIODE, ID_CLASSE""",
    "R_LISTE_ETUDIANT": """
        SELECT I.ID_INSCRIPTION, E.MATRICULE, E.NOM, E.PRENOM, E.SEXE,
               E.DATE_NAISSANCE, E.TEL, C.LIBELLE AS CLASSE, F.FILIERE,
               N.NIVEAU, A.LIBELLE AS ANNEE, I.STATUT
        FROM INSCRIPTION AS I
        INNER JOIN ETUDIANT AS E ON I.ID_ETUDIANT = E.ID_ETUDIANT
        INNER JOIN CLASSE AS C ON I.ID_CLASSE = C.ID_CLASSE
        INNER JOIN FILIERE AS F ON C.CODE_FILIERE = F.CODE_FILIERE
        INNER JOIN NIVEAU AS N ON C.CODE_NIVEAU = N.CODE_NIVEAU
        INNER JOIN ANNEE_SCOLAIRE AS A ON C.ID_ANNEE = A.ID_ANNEE""",
    "R_BULLETIN_DETAIL": """
        SELECT E.MATRICULE, E.NOM, E.PRENOM, C.LIBELLE AS CLASSE,
               PE.LIBELLE AS PERIODE, M.MATIERE, BL.MOYENNE_MAT,
               BL.COEFFICIENT, BL.POINTS, BL.RANG_MAT, B.MOYENNE, B.RANG,
               B.EFFECTIF, B.DECISION
        FROM BULLETIN AS B
        INNER JOIN BULLETIN_LIGNE AS BL ON B.ID_BULLETIN = BL.ID_BULLETIN
        INNER JOIN MATIERE AS M ON BL.CODE_MATIERE = M.CODE_MATIERE
        INNER JOIN INSCRIPTION AS I ON B.ID_INSCRIPTION = I.ID_INSCRIPTION
        INNER JOIN ETUDIANT AS E ON I.ID_ETUDIANT = E.ID_ETUDIANT
        INNER JOIN CLASSE AS C ON I.ID_CLASSE = C.ID_CLASSE
        INNER JOIN PERIODE_EVAL AS PE ON B.ID_PERIODE = PE.ID_PERIODE""",
    "R_SITUATION_ECOLAGE": """
        SELECT E.MATRICULE, E.NOM, E.PRENOM, C.LIBELLE AS CLASSE,
               I.ID_INSCRIPTION,
               SUM(ECH.MONTANT_DU - IFNULL(ECH.REMISE, 0)) AS TOTAL_DU,
               SUM(IFNULL(PE.TOTAL_PAYE, 0)) AS TOTAL_PAYE,
               SUM(ECH.MONTANT_DU - IFNULL(ECH.REMISE, 0))
                   - SUM(IFNULL(PE.TOTAL_PAYE, 0)) AS RESTE
        FROM ECHEANCIER AS ECH
        LEFT JOIN R_PAIEMENT_ECHEANCE AS PE ON ECH.ID_ECHEANCE = PE.ID_ECHEANCE
        INNER JOIN INSCRIPTION AS I ON ECH.ID_INSCRIPTION = I.ID_INSCRIPTION
        INNER JOIN ETUDIANT AS E ON I.ID_ETUDIANT = E.ID_ETUDIANT
        INNER JOIN CLASSE AS C ON I.ID_CLASSE = C.ID_CLASSE
        GROUP BY E.MATRICULE, E.NOM, E.PRENOM, C.LIBELLE, I.ID_INSCRIPTION""",
    "R_EDT_CLASSE": """
        SELECT C.LIBELLE AS CLASSE, EDT.JOUR, CR.ORDRE_CRE, CR.HEURE_DEBUT,
               CR.HEURE_FIN, M.MATIERE,
               (IFNULL(F.NOM, '') || ' ' || IFNULL(F.PRENOM, '')) AS FORMATEUR,
               S.NOM_SALLE
        FROM EMPLOI_DU_TEMPS AS EDT
        INNER JOIN CRENEAU AS CR ON EDT.ID_CRENEAU = CR.ID_CRENEAU
        INNER JOIN PROGRAMME AS P ON EDT.ID_PROG = P.ID_PROG
        INNER JOIN CLASSE AS C ON P.ID_CLASSE = C.ID_CLASSE
        INNER JOIN MATIERE AS M ON P.CODE_MATIERE = M.CODE_MATIERE
        LEFT JOIN FORMATEUR AS F ON P.ID_FORMATEUR = F.ID_FORMATEUR
        LEFT JOIN SALLE AS S ON EDT.ID_SALLE = S.ID_SALLE
        WHERE IFNULL(EDT.ACTIF, 0) <> 0""",
    "R_ABSENCE_ETUDIANT": """
        SELECT I.ID_INSCRIPTION, E.MATRICULE, E.NOM, E.PRENOM,
               C.LIBELLE AS CLASSE, SUM(A.NB_HEURES) AS TOTAL_HEURES,
               SUM(CASE WHEN IFNULL(A.JUSTIFIEE, 0) <> 0
                        THEN A.NB_HEURES ELSE 0 END) AS HEURES_JUSTIFIEES
        FROM ABSENCE AS A
        INNER JOIN INSCRIPTION AS I ON A.ID_INSCRIPTION = I.ID_INSCRIPTION
        INNER JOIN ETUDIANT AS E ON I.ID_ETUDIANT = E.ID_ETUDIANT
        INNER JOIN CLASSE AS C ON I.ID_CLASSE = C.ID_CLASSE
        GROUP BY I.ID_INSCRIPTION, E.MATRICULE, E.NOM, E.PRENOM, C.LIBELLE""",
}

# Ordre de création respectant les dépendances (parents avant enfants).
TABLE_ORDER: Tuple[str, ...] = (
    "UTILISATEUR", "PARAMETRE", "ETABLISSEMENT", "ANNEE_SCOLAIRE", "JOURNAL",
    "GRILLE_MENTION", "FILIERE", "NIVEAU", "SALLE", "CLASSE",
    "MODULE_FORMATION", "MATIERE", "FORMATEUR", "PROGRAMME",
    "ETUDIANT", "INSCRIPTION", "PERIODE_EVAL", "EVALUATION", "NOTE",
    "SESSION_EXAM", "EPREUVE", "NOTE_EXAMEN", "CRENEAU", "EMPLOI_DU_TEMPS",
    "SEANCE", "ABSENCE", "BULLETIN", "BULLETIN_LIGNE", "RESULTAT_FINAL",
    "TARIF", "ECHEANCIER", "PAIEMENT", "PAIE_FORMATEUR",
)

# Type déclaré SQLite par « kind » du catalogue. Les noms restent parlants
# (PRAGMA table_info les restitue) tout en respectant les affinités SQLite.
_DECLARED_TYPES = {
    "TEXT": "VARCHAR({size})",
    "MEMO": "TEXT",
    "LONG": "INTEGER",
    "DOUBLE": "REAL",
    "CURRENCY": "REAL",
    "DATETIME": "DATETIME",
    "BOOLEAN": "BOOLEAN",
}


def q(identifier: str) -> str:
    return "[" + identifier.replace("]", "]]") + "]"


def primary_key_of(table: str) -> List[str]:
    return list(TABLES[table]["pk"])


def table_ddl(table: str) -> str:
    """CREATE TABLE complet (colonnes, clé primaire, clés étrangères)."""
    catalog = TABLES[table]
    pk = list(catalog["pk"])
    parts: List[str] = []
    for name, kind, size, _nullable, autonumber in catalog["columns"]:
        if autonumber and pk == [name]:
            parts.append(f"{q(name)} INTEGER PRIMARY KEY AUTOINCREMENT")
            continue
        declared = _DECLARED_TYPES.get(kind, "TEXT").format(size=size or 255)
        parts.append(f"{q(name)} {declared}")
    autonumber_pk = any(autonumber and pk == [name]
                        for name, _k, _s, _n, autonumber in catalog["columns"])
    if pk and not autonumber_pk:
        parts.append("PRIMARY KEY (" + ", ".join(q(c) for c in pk) + ")")
    for fk_name, columns, ref_table in FOREIGN_KEYS.get(table, []):
        ref_pk = primary_key_of(ref_table)
        parts.append(
            f"CONSTRAINT {q(fk_name)} FOREIGN KEY ("
            + ", ".join(q(c) for c in columns) + f") REFERENCES {q(ref_table)} ("
            + ", ".join(q(c) for c in ref_pk) + ")")
    return f"CREATE TABLE {q(table)} (\n  " + ",\n  ".join(parts) + "\n)"


def index_ddl(table: str) -> List[str]:
    """CREATE INDEX pour les index déclarés et les clés étrangères."""
    statements: List[str] = []
    for name, columns, unique in INDEXES.get(table, []):
        kind = "UNIQUE INDEX" if unique else "INDEX"
        statements.append(
            f"CREATE {kind} IF NOT EXISTS {q(name)} ON {q(table)} ("
            + ", ".join(q(c) for c in columns) + ")")
    for fk_name, columns, _ref in FOREIGN_KEYS.get(table, []):
        statements.append(
            f"CREATE INDEX IF NOT EXISTS {q(fk_name)} ON {q(table)} ("
            + ", ".join(q(c) for c in columns) + ")")
    return statements


def view_ddl(name: str) -> str:
    return f"CREATE VIEW IF NOT EXISTS {q(name)} AS {VIEWS[name].strip()}"


def full_schema_sql() -> str:
    """Script SQL complet (documentation / création manuelle)."""
    lines = [f"-- LTA_ADM — schéma SQLite v{SCHEMA_VERSION}", "PRAGMA foreign_keys = ON;", ""]
    for table in TABLE_ORDER:
        lines.append(table_ddl(table) + ";")
        lines.extend(s + ";" for s in index_ddl(table))
        lines.append("")
    for view in VIEWS:
        lines.append(view_ddl(view) + ";")
    lines.append(f"PRAGMA user_version = {SCHEMA_VERSION};")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Inspection
# ---------------------------------------------------------------------------


def _table_names(connection: sqlite3.Connection) -> List[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' "
        "AND name NOT LIKE 'sqlite_%'").fetchall()
    return [r[0] for r in rows]


def _has_primary_key(connection: sqlite3.Connection, table: str) -> bool:
    rows = connection.execute(f"PRAGMA table_info({q(table)})").fetchall()
    return any(row[5] for row in rows)


def _existing_columns(connection: sqlite3.Connection, table: str) -> List[str]:
    return [row[1] for row in connection.execute(f"PRAGMA table_info({q(table)})")]


def needs_migration(path: str) -> bool:
    """La base est-elle encore au format « plat » de la conversion ?"""
    if not os.path.isfile(path):
        return False
    connection = sqlite3.connect(path)
    try:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version >= SCHEMA_VERSION:
            return False
        existing = {t.upper() for t in _table_names(connection)}
        for table in TABLE_ORDER:
            if table in existing and not _has_primary_key(connection, table):
                return True
        # Tables manquantes ou vues absentes : migration également utile.
        if any(t not in existing for t in TABLE_ORDER):
            return True
        views = {r[0].upper() for r in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'view'")}
        return any(v not in views for v in VIEWS)
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# Création / migration
# ---------------------------------------------------------------------------


def _normalize_bool_text(value):
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("true", "vrai", "yes", "oui", "-1", "1"):
            return 1
        if text in ("false", "faux", "no", "non", "0", ""):
            return 0
    return value


def _copy_rows(connection: sqlite3.Connection, source: str, target: str,
               table: str) -> int:
    """Copie les lignes de ``source`` vers ``target`` (colonnes communes)."""
    catalog = TABLES[table]
    target_columns = [c[0] for c in catalog["columns"]]
    kinds = {c[0]: c[1] for c in catalog["columns"]}
    source_columns = _existing_columns(connection, source)
    by_upper = {c.upper(): c for c in source_columns}
    common = [(by_upper[c.upper()], c) for c in target_columns if c.upper() in by_upper]
    if not common:
        return 0
    select_sql = ("SELECT " + ", ".join(q(src) for src, _ in common)
                  + f" FROM {q(source)}")
    insert_sql = (f"INSERT OR IGNORE INTO {q(target)} ("
                  + ", ".join(q(dst) for _, dst in common) + ") VALUES ("
                  + ", ".join("?" * len(common)) + ")")
    copied = 0
    for row in connection.execute(select_sql).fetchall():
        values = list(row)
        for index, (_src, dst) in enumerate(common):
            if kinds.get(dst) == "BOOLEAN":
                values[index] = _normalize_bool_text(values[index])
            elif kinds.get(dst) == "DATETIME" and isinstance(values[index], str):
                values[index] = values[index].strip() or None
        connection.execute(insert_sql, values)
        copied += 1
    return copied


def apply_schema(connection: sqlite3.Connection) -> Dict[str, int]:
    """Crée ou renforce le schéma sur une connexion ouverte (idempotent).

    Les tables sans clé primaire sont reconstruites à l'identique avec
    reprise des données ; les tables manquantes sont créées ; les vues et
    index sont (re)créés. Retourne le nombre de lignes reprises par table.
    """
    copied: Dict[str, int] = {}
    connection.execute("PRAGMA foreign_keys = OFF")
    existing = {t.upper(): t for t in _table_names(connection)}
    connection.execute("BEGIN")
    try:
        for view in VIEWS:
            connection.execute(f"DROP VIEW IF EXISTS {q(view)}")
        for table in TABLE_ORDER:
            actual = existing.get(table)
            if actual is None:
                connection.execute(table_ddl(table))
                continue
            if _has_primary_key(connection, actual):
                continue
            temporary = f"{table}__ancien"
            connection.execute(f"ALTER TABLE {q(actual)} RENAME TO {q(temporary)}")
            connection.execute(table_ddl(table))
            copied[table] = _copy_rows(connection, temporary, table, table)
            connection.execute(f"DROP TABLE {q(temporary)}")
        for table in TABLE_ORDER:
            for statement in index_ddl(table):
                connection.execute(statement)
        for view in VIEWS:
            connection.execute(view_ddl(view))
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    finally:
        connection.execute("PRAGMA foreign_keys = ON")
    return copied


def backup_before_migration(path: str) -> str:
    folder = os.path.join(os.path.dirname(os.path.abspath(path)), "Sauvegardes")
    os.makedirs(folder, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.splitext(os.path.basename(path))[0]
    destination = os.path.join(folder, f"{base}_avant_migration_{stamp}.sqlite3")
    shutil.copyfile(path, destination)
    return destination


def migrate_database(path: str, backup: bool = True) -> Tuple[Optional[str], Dict[str, int]]:
    """Renforce le schéma du fichier ``path`` en conservant les données.

    Retourne ``(chemin_de_sauvegarde_ou_None, lignes_reprises_par_table)``.
    Ne fait rien si la base est déjà au bon format.
    """
    if not needs_migration(path):
        return None, {}
    backup_path = backup_before_migration(path) if backup else None
    connection = sqlite3.connect(path)
    try:
        copied = apply_schema(connection)
        connection.execute("VACUUM")
    finally:
        connection.close()
    return backup_path, copied


def create_database(path: str, seed_rows: Optional[Dict[str, Iterable[dict]]] = None,
                    overwrite: bool = False) -> str:
    """Crée une base neuve au schéma renforcé, avec des données initiales."""
    if os.path.exists(path):
        if not overwrite:
            raise FileExistsError(path)
        os.remove(path)
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        apply_schema(connection)
        if seed_rows:
            insert_rows(connection, seed_rows)
        connection.commit()
    finally:
        connection.close()
    return path


def insert_rows(connection: sqlite3.Connection,
                rows_by_table: Dict[str, Iterable[dict]]) -> int:
    """Insère des lignes (dictionnaires colonne → valeur) table par table."""
    inserted = 0
    for table in TABLE_ORDER:
        rows = list(rows_by_table.get(table) or [])
        if not rows:
            continue
        columns = [c[0] for c in TABLES[table]["columns"]]
        sql = (f"INSERT OR IGNORE INTO {q(table)} ("
               + ", ".join(q(c) for c in columns) + ") VALUES ("
               + ", ".join("?" * len(columns)) + ")")
        for row in rows:
            values = [row.get(column) for column in columns]
            connection.execute(sql, values)
            inserted += 1
    return inserted


def export_rows(connection: sqlite3.Connection,
                tables: Sequence[str] = TABLE_ORDER) -> Dict[str, List[dict]]:
    """Exporte les lignes des tables demandées (utilisé pour les jeux de données)."""
    result: Dict[str, List[dict]] = {}
    for table in tables:
        columns = [c[0] for c in TABLES[table]["columns"]]
        rows = connection.execute(
            "SELECT " + ", ".join(q(c) for c in columns) + f" FROM {q(table)}").fetchall()
        if rows:
            result[table] = [dict(zip(columns, row)) for row in rows]
    return result
