# LTAdmin — gestion scolaire de l'Institut LTA

Application de gestion scolaire (BTS Hôtellerie / Tourisme, Antananarivo) livrée sous la forme
d'une **application web sur le poste de travail** : l'interface est en HTML/CSS/JavaScript et
s'ouvre dans une **fenêtre native** (pywebview) — le même principe qu'Electron, mais avec
Python. Le serveur HTTP, l'API JSON et la base **SQLite** (`LTA_ADM.sqlite3`) tournent en local ;
aucune installation de serveur, de base de données ou de Node.js n'est nécessaire.

```
┌─────────────────────────────────────────────────────────────────────┐
│  Fenêtre native (pywebview)  ─ ou ─  navigateur (python main.py --serve)  │
│  Interface : ltadmin/web/static  (HTML + CSS + JS, sans framework)         │
├─────────────────────────────────────────────────────────────────────┤
│  API JSON  /api/...   (ltadmin/web : routage, sessions, habilitations)      │
├─────────────────────────────────────────────────────────────────────┤
│  Services métier  (ltadmin/services : règles de gestion, validation)        │
│  Dépôts typés     (ltadmin/repositories : SQL paramétré)                    │
├─────────────────────────────────────────────────────────────────────┤
│  SQLite  LTA_ADM.sqlite3  (33 tables, clés étrangères, index, 8 vues R_*)   │
└─────────────────────────────────────────────────────────────────────┘
```

## Fonctionnalités

| Module | Contenu |
| --- | --- |
| Tableau de bord | Année active, effectifs par classe, recouvrement de l'écolage, échéances échues, alertes d'absence, activité récente |
| Étudiants | Fiche complète, recherche, matricule automatique `ETU-AAAA-NNNN`, inscription depuis la fiche |
| Inscriptions | Par classe et année, statuts (INSCRIT / SORTI), sortie motivée, contrôle d'effectif maximal |
| Référentiel | Filières, niveaux, classes, matières, modules de formation, salles |
| Formateurs | Fiches, taux horaire, programmes par classe (matière × formateur × coefficient × volume horaire) |
| Notes et évaluations | Périodes (clôture), évaluations (devoir, interrogation, TP, projet, examen blanc…), grille de saisie, publication, moyennes |
| Bulletins | Génération par classe et période : moyennes pondérées, rangs « compétition », min/max par matière, mentions, impression |
| Examens | Sessions, épreuves, saisie des notes d'examen, résultats finaux **CC 40 % / examen 60 %** (paramétrable), décision, procès-verbal |
| Emploi du temps | Créneaux, planification par classe avec détection des **conflits** salle / formateur / classe, séances (cahier de texte) |
| Absences | Saisie par séance, justification, synthèse par étudiant, seuil d'alerte |
| Écolage | Tarifs par classe, échéanciers, encaissements avec reçu `REC-AAAA-NNNNNN`, remises, statuts DU / PARTIEL / SOLDÉ, situation par classe |
| Paie des formateurs | Heures réalisées × taux horaire, calcul par période, règlement, fiche de paie |
| Statistiques | Effectifs, répartition par sexe, redoublants, résultats, mentions, avancement des saisies, encaissements |
| Rapports | Les 8 états `R_*` (listes, moyennes, bulletins, écolage, EDT, absences) avec filtres et **export CSV** (`;`, UTF-8 BOM, compatible Excel) |
| Administration | Paramètres de gestion, établissement, années scolaires, journal des opérations, sauvegardes / restauration |
| Profils utilisateurs | Comptes, profils, activation, réinitialisation de mot de passe |
| Tables (maintenance) | Édition générique de toutes les tables (profils habilités) |

### Profils et habilitations

| Profil (valeur en base) | Accès |
| --- | --- |
| Administrateur (`ADMIN`) | Tous les modules |
| Direction | Tout sauf Administration, Profils utilisateurs et Tables |
| Scolarité (`SCOLARITE`) | Scolarité, pédagogie, statistiques, rapports (pas d'écolage ni de paie) |
| Comptabilité (`FINANCE`) | Écolage, paie, statistiques, rapports |
| Enseignant | Tableau de bord, formateurs, notes, bulletins, examens, emploi du temps, absences |

Comptes présents dans la base livrée : `ADMIN` / `admin`, `SCOL` / `scol`, `CAISSE` / `caisse`.
L'identifiant est insensible à la casse. Les mots de passe sont hachés (PBKDF2) à la première
connexion réussie ; changez-les depuis le menu utilisateur.

## Installation et lancement

Pré-requis : **Python 3.11 ou plus récent**. Le cœur de l'application n'utilise que la
bibliothèque standard (`sqlite3`, `http.server`, `json`…).

```bash
pip install -r requirements.txt     # pywebview, uniquement pour la fenêtre native
python main.py                      # ouvre LTAdmin dans une fenêtre
```

Autres modes :

```bash
python main.py --serve                       # serveur local + ouverture du navigateur
python main.py --serve --port 8765           # port fixe (http://127.0.0.1:8765/)
python main.py --serve --host 0.0.0.0        # accessible depuis d'autres postes du réseau
python main.py --db "D:\LTA\LTA_ADM.sqlite3" # base explicite
python main.py --version
```

Si pywebview n'est pas installé, `python main.py` bascule automatiquement en mode navigateur.
Sous Linux, pywebview nécessite les paquets système `python3-gi gir1.2-webkit2-4.1` ; sous
Windows, le runtime WebView2 (fourni avec Edge) ; sous macOS, rien de plus.

Ordre de recherche de la base : `--db` → variable d'environnement `LTADMIN_DB` → dossier de
l'exécutable → dossier courant → dossiers parents. Si aucune base n'existe au premier emplacement
candidat, une base vide (schéma + référentiel initial + comptes) est créée.

## La base de données

`LTA_ADM.sqlite3` est la **source de vérité** du projet et suit le dépôt. Au premier démarrage sur
un fichier « plat » (tables sans clés ni index, tel qu'issu de la conversion Access), l'application
**renforce le schéma** : clés primaires `AUTOINCREMENT`, clés étrangères, contraintes d'unicité,
56 index et les 8 vues `R_*`. **Toutes les données sont conservées** et une copie de l'original est
déposée dans `Sauvegardes/<base>_avant_migration_<horodatage>.sqlite3`. La même opération peut
être lancée ou vérifiée à la main :

```bash
python tools/migrate_schema.py --verifier     # état du schéma (code 3 si migration nécessaire)
python tools/migrate_schema.py                # migration avec sauvegarde préalable
```

La copie de l'original livré est conservée dans le dépôt :
`Sauvegardes/LTA_ADM_avant_migration_20260927_062438.sqlite3`.

Sauvegardes applicatives : *Administration › Sauvegardes* (création horodatée, restauration avec
copie de sécurité, purge) ; les fichiers sont écrits dans le dossier `Sauvegardes/` à côté de la
base. Journal technique : `logs/ltadmin-AAAAMMJJ.log`.

## Tests

```bash
python -m unittest discover -s tests -t . -v
```

126 tests, sans dépendance externe : règles métier et dépôts sur une base SQLite temporaire,
API web appelée en mémoire (authentification, habilitations, scénario complet étudiant →
bulletin → écolage → examen), conformité statique front/back (chaque URL `/api/...` du JavaScript
correspond à une route serveur, chaque module du menu à une vue).

Intégration continue : le fichier `docs/github-workflow-tests.yml` est un workflow GitHub Actions
prêt à l'emploi (Python 3.11 et 3.12) ; copiez-le dans `.github/workflows/tests.yml` pour
l'activer (l'ajout de workflows nécessite les droits correspondants sur le dépôt).

## Empaquetage (exécutable Windows)

```powershell
pip install -r requirements.txt -r requirements-build.txt
pyinstaller --noconfirm --windowed --name LTAdmin --add-data "ltadmin/web/static;ltadmin/web/static" main.py
```

Placez `LTA_ADM.sqlite3` à côté de `LTAdmin.exe` (dossier `dist/LTAdmin/`).

## Organisation du dépôt

```
main.py                  point d'entrée (fenêtre native ou --serve)
ltadmin/bootstrap.py     localisation / création / migration de la base, démarrage du serveur
ltadmin/web/             API JSON (routage, sessions, sérialisation) + interface statique
ltadmin/services/        règles de gestion, validation, authentification, habilitations, journal
ltadmin/repositories/    accès SQL typé par domaine
ltadmin/data/            schéma SQLite (DDL, migration), connexion, données initiales
ltadmin/models/          entités, DTO, modèles de session
tests/                   suite unittest (métier, API, conformité)
tools/migrate_schema.py  migration / vérification du schéma en ligne de commande
docs/ARCHITECTURE.md     architecture détaillée et conventions
```
