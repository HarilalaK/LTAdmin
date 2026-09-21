"""Vérifie les affirmations chiffrées et nominatives d'ANALYSE_BASE_LTA.md contre LTA_ADM.accdb."""
import sys, re, json; sys.path.insert(0, '/home/user/.venv-acc')
from extract_lib import DB, full_catalog, schema, table_by_id, ID_BY_NAME

ok, ko = [], []
def check(cond, label):
    (ok if cond else ko).append(label)

# --- relations réelles ---
rel = table_by_id(ID_BY_NAME['MSysRelationships']).parse()
rels = {}
for i in range(len(rel['szRelationship'])):
    rels[rel['szRelationship'][i]] = (rel['szObject'][i], rel['szColumn'][i],
                                     rel['szReferencedObject'][i], rel['szReferencedColumn'][i], rel['grbit'][i])
user_rels = {k: v for k, v in rels.items() if not k.startswith('MSysNavPane')}

# --- index uniques réels ---
cat = full_catalog()
user_tables = sorted(r['Name'] for r in cat if r['Type'] == 1 and r['Flags'] == 0 and r['Id'] > 0 and not r['Name'].startswith('MSys'))
sch = {t: schema(t) for t in user_tables}
uniq = {}
for t, s in sch.items():
    for i in s['indexes']:
        if i['unique'] and not i['is_pk']:
            uniq[i['name']] = (t, tuple(i['columns']))

report = open('ANALYSE_BASE_LTA.md', encoding='utf-8').read()

# 1) chaque FK citée dans le rapport existe vraiment
cited_fk = set(re.findall(r'\bFK_[A-Z_]+\b', report))
for fk in sorted(cited_fk):
    check(fk in user_rels, f"FK citée existe dans MSysRelationships : {fk}")

# 2) chaque index unique cité existe et porte les bonnes colonnes
attendus = {'IX_ETU_MAT': ('ETUDIANT', ('MATRICULE',)),
            'IX_INS_UNI': ('INSCRIPTION', ('ID_ETUDIANT', 'ID_CLASSE')),
            'IX_PROG_UNI': ('PROGRAMME', ('ID_CLASSE', 'CODE_MATIERE')),
            'IX_NOTE_UNI': ('NOTE', ('ID_EVALUATION', 'ID_INSCRIPTION')),
            'IX_NEX_UNI': ('NOTE_EXAMEN', ('ID_EPREUVE', 'ID_INSCRIPTION')),
            'IX_BUL_UNI': ('BULLETIN', ('ID_INSCRIPTION', 'ID_PERIODE')),
            'IX_PAI_RECU': ('PAIEMENT', ('NUM_RECU',))}
check(set(attendus) == set(uniq), f"exactement 7 index uniques métier (réel={len(uniq)})")
for n, v in attendus.items():
    check(uniq.get(n) == v, f"index unique {n} -> {v} (réel={uniq.get(n)})")
check(set(attendus) == set(re.findall(r'\bIX_[A-Z_]+UNI\b|\bIX_ETU_MAT\b|\bIX_PAI_RECU\b', report)) ,
      "les 7 index uniques sont tous cités dans le rapport")

# 3) comptages annoncés
tot_cols = sum(len(s['columns']) for s in sch.values())
check(len(user_tables) == 33, f"33 tables métier (réel={len(user_tables)})")
check(tot_cols == 267, f"267 colonnes (réel={tot_cols})")
check(len(user_rels) == 40, f"40 relations utilisateur (réel={len(user_rels)})")
check(all(v[4] == 0 for v in user_rels.values()), "les 40 relations ont grbit=0 (aucune cascade)")
auto = [(t, c['name']) for t, s in sch.items() for c in s['columns'] if c['autonumber']]
check(len(auto) == 26, f"26 colonnes AutoNumber (réel={len(auto)})")
req = [1 for s in sch.values() for c in s['columns'] if c['required']]
check(len(req) == 0, f"0 colonne NOT NULL (réel={len(req)})")
big = [1 for s in sch.values() for c in s['columns'] if c['type_code'] == 10 and c['length'] > 255]
check(len(big) == 18, f"18 colonnes TEXT > 255 (réel={len(big)})")
check(len(DB.extra_props) and not any(DB.extra_props.values()), "aucune propriété Access stockée sur les tables")

# 4) requêtes
queries = [r['Name'] for r in cat if r['Type'] == 5]
check(len(queries) == 8, f"8 requêtes enregistrées (réel={len(queries)})")
for qn in queries:
    check(f"`{qn}`" in report, f"requête citée dans le rapport : {qn}")

# 5) VBA vide
stor = table_by_id(ID_BY_NAME['MSysAccessStorage']).parse()
vba_streams = [stor['Name'][i] for i in range(len(stor['Name']))
               if stor['ParentId'][i] == 18 and stor['Type'][i] == 2]
modules = [n for n in vba_streams if n not in ('_VBA_PROJECT', 'dir')]
check(modules == [], f"0 module VBA (flux du projet VBA = {vba_streams})")

# 6) données initiales citées
data = json.load(open('analysis/extraction_complete.json'))['data']
counts = {t: len(v) for t, v in data.items()}
attendu_data = {'ANNEE_SCOLAIRE': 1, 'CLASSE': 4, 'CRENEAU': 4, 'ETABLISSEMENT': 1, 'FILIERE': 2,
                'GRILLE_MENTION': 5, 'MATIERE': 17, 'MODULE_FORMATION': 4, 'NIVEAU': 2,
                'PARAMETRE': 7, 'PERIODE_EVAL': 3, 'SALLE': 5, 'UTILISATEUR': 3}
check(counts == attendu_data, f"13 tables peuplées avec les comptages annoncés (réel={counts})")
param = {r['CLE']: r['VALEUR'] for r in data['PARAMETRE']}
attendu_param = {'BAREME_DEFAUT': '20', 'MOY_ADMISSION': '10', 'NOTE_ELIMINATOIRE': '5',
                 'POIDS_CC': '40', 'POIDS_EXAMEN': '60', 'SEUIL_ABSENCE': '30', 'DEVISE': 'MGA'}
check(param == attendu_param, f"7 paramètres annoncés corrects (réel={param})")
users = {(r['CODE_UTR'], r['MOT_PASSE'], r['PROFIL']) for r in data['UTILISATEUR']}
check(users == {('ADMIN', 'admin', 'ADMIN'), ('SCOL', 'scol', 'SCOLARITE'), ('CAISSE', 'caisse', 'FINANCE')},
      f"3 comptes annoncés corrects (réel={users})")
vides = [t for t in user_tables if t not in counts]
check(len(vides) == 20, f"20 tables vides (réel={len(vides)})")

# 7) les 10 relations mises en avant par la demande
dix = ['FK_INS_ETU', 'FK_INS_CLA', 'FK_CLA_FIL', 'FK_PRO_MAT', 'FK_PRO_FORM', 'FK_NOT_EVA', 'FK_NOT_INS',
       'FK_BUL_INS', 'FK_ECH_INS', 'FK_PAI_ECH', 'FK_EDT_PRO', 'FK_SEA_EDT', 'FK_ABS_SEA', 'FK_ABS_INS']
for fk in dix:
    check(fk in user_rels, f"relation de la demande présente : {fk}")

print(f"VÉRIFICATIONS RÉUSSIES : {len(ok)}")
for l in ok: print("  OK  ", l)
print(f"\nÉCHECS : {len(ko)}")
for l in ko: print("  KO  ", l)
sys.exit(1 if ko else 0)
