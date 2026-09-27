# Architecture technique — LTAdmin 2.0

> Application « web sur le poste de travail » : interface HTML/CSS/JavaScript servie par un
> serveur HTTP Python local et affichée dans une fenêtre native (pywebview) ou un navigateur.
> Base de données **SQLite** `LTA_ADM.sqlite3` (source de vérité, versionnée dans le dépôt).

## 1. Principes

| Règle | Mise en œuvre |
| --- | --- |
| Les données ne sont jamais perdues | La migration de schéma recopie chaque table après une sauvegarde du fichier ; aucune suppression globale dans le code ; suppressions unitaires refusées lorsque des lignes liées existent (clés étrangères `RESTRICT` + messages traduits) |
| Aucune écriture sans action explicite | Les lectures (tableau de bord, états, statistiques) n'écrivent jamais ; toute écriture naît d'un clic → appel API → service → dépôt, et alimente le `JOURNAL` |
| Requêtes paramétrées partout | Paramètres positionnels `?` ; identifiants protégés par `[crochets]` (compatibles SQLite) |
| Règles métier dans les services, pas dans l'interface | Les vues JavaScript affichent des résultats (`{ok, message, code, errors, value}`) ; les validations et calculs vivent dans `ltadmin/services` |
| Habilitations vérifiées deux fois | Côté HTTP (module de la route ↔ profil de la session) **et** côté service (`ensure_allowed`) ; l'interface ne fait que masquer |
| Bibliothèque standard uniquement | `sqlite3`, `http.server`, `json`, `hashlib`… ; pywebview est optionnel (fenêtre native) |

## 2. Vue d'ensemble

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Fenêtre pywebview (main.py)   ou   navigateur (main.py --serve)           │
│   ltadmin/web/static : index.html · styles.css · core.js · app.js · views/│
└───────────────────────────────┬──────────────────────────────────────────┘
                                │ HTTP 1.1 (localhost), JSON, cookie de session
┌───────────────────────────────▼──────────────────────────────────────────┐
│ ltadmin/web : server.py (ThreadingHTTPServer) · routing.py (Router,       │
│   Request/Response, HttpError) · sessions.py · serialization.py           │
│   api_scolarite.py · api_pedagogie.py · api_finance.py · api_admin.py     │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │ AppServices (ltadmin/services/app_composition.py)
┌───────────────────────────────▼──────────────────────────────────────────┐
│ ltadmin/services : auth · business (10 services) · referentiel ·          │
│   statistics · reports · validation · logging · infrastructure · admin    │
└───────────────────────────────┬──────────────────────────────────────────┘
┌───────────────────────────────▼──────────────────────────────────────────┐
│ ltadmin/repositories : dépôts typés par agrégat (SQL paramétré)           │
│ ltadmin/data : Database (sqlite3, verrou, transactions) · schema_ddl ·    │
│   database_repository (maintenance générique) · seed_data · error_helper  │
└───────────────────────────────┬──────────────────────────────────────────┘
                                ▼
                        LTA_ADM.sqlite3  (user_version = 1)
```

Dépendances strictement descendantes : `static → web → services → repositories → data`.
`ltadmin/core` (`Result`, `ResultValue`) et `ltadmin/models` sont partagés par toutes les couches.

## 3. Démarrage (`main.py` → `ltadmin/bootstrap.py`)

1. `DatabaseLocator.locate(--db)` : `--db` → `LTADMIN_DB` → dossier de l'exécutable → dossier
   courant → parents. Fichier absent ⇒ `schema_ddl.create_database` (schéma + `SEED_ROWS`).
2. `prepare_database` : si `schema_ddl.needs_migration` (user_version 0, pas de clés), copie de
   sécurité `Sauvegardes/<base>_avant_migration_<horodatage>.sqlite3` puis `migrate_database`
   (tables recréées, données recopiées table par table, `PRAGMA integrity_check`, vues `R_*`).
3. `AppServices(database).open()` puis `WebApplication(services)` et `LtadminHttpServer` sur
   `127.0.0.1:<port libre>` (ou `--host/--port`).
4. Fenêtre pywebview (1360 × 860) pointant sur l'URL locale ; à la fermeture, arrêt du serveur et
   fermeture de la base. Sans pywebview ou avec `--serve` : ouverture du navigateur, arrêt par Ctrl+C.

## 4. Couche web

### Routage et sécurité

* `Router.add(method, "/api/x/{id}", handler, module)` ; les segments `{param}` sont capturés et
  décodés (`%20`…). Chemin connu / mauvaise méthode ⇒ 405, inconnu ⇒ 404.
* `module` : `PUBLIC` (sans session : connexion, déconnexion, session, santé), `None` (toute
  session ouverte : référentiels en lecture, tableau de bord…), ou un libellé de
  `habilitations.Modules` (contrôlé par `habilitations.can_access(profil, module)` ⇒ 401 sans
  session, 403 si le profil n'y a pas droit).
* Sessions en mémoire (`SessionStore`) : jeton aléatoire (`secrets.token_urlsafe`), cookie
  `ltadmin_session` **HttpOnly, SameSite=Lax** (+ `Secure` derrière HTTPS), expiration par
  inactivité, révocation immédiate à la désactivation ou suppression d'un compte.
* Les handlers retournent soit un `Result` métier (statut HTTP dérivé du code : `VALIDATION` 400,
  `AUTHENTIFICATION` 401, `HABILITATION` 403, `INTROUVABLE` 404, `DOUBLON`/`LIAISON`/`GESTION` 409,
  `VERROUILLE` 423, sinon 409/500), soit une `Response` (CSV, en-têtes), soit une valeur brute
  enveloppée en `{ok: true, value}`. Toute réponse JSON a la forme
  `{ok, message, code, errors, value}`.
* Les mots de passe ne sont jamais renvoyés (`UTILISATEUR` masqué dans la maintenance générique,
  table non modifiable par cette voie ; les comptes passent par `/api/utilisateurs`).
* Serveur : `ThreadingHTTPServer`, threads démons, `X-Content-Type-Options: nosniff`, statiques
  en `Cache-Control: no-cache`, repli SPA (`GET` non-API inconnu ⇒ `index.html`), protection
  contre la traversée de répertoires.

### Sérialisation (`serialization.py`)

`to_jsonable` convertit `Decimal`, `date/datetime`, dataclasses, tuples, ensembles.
`parse_entity(cls, data, base=None)` reconstruit une entité à partir d'un JSON en respectant les
annotations (`Optional[Decimal]`, `datetime`, `bool`…), accepte `12/05/2004` et `2004-05-12`,
`"1 500 000,50"`, `"oui"/"non"`, ignore les clés inconnues et signale le champ fautif.

### Routes (138)

| Domaine | Routes principales |
| --- | --- |
| Authentification | `POST /api/auth/connexion`, `POST /api/auth/deconnexion`, `GET /api/auth/session`, `POST /api/auth/mot-de-passe`, `GET /api/sante` |
| Pilotage | `GET /api/tableau-de-bord`, `GET /api/statistiques` |
| Référentiel | `GET /api/ref/tout` (cache côté client) ; `GET/POST /api/ref/{filieres,niveaux,salles,classes,modules,matieres}` + `DELETE …/{id}` ; `GET /api/ref/annees` |
| Scolarité | `/api/etudiants[/{id}[/inscriptions]]`, `/api/inscriptions[/{id}[/sortie]]`, `/api/formateurs[/{id}]`, `/api/programmes[/{id}]` |
| Pédagogie | `/api/periodes[/{id}/cloture]`, `/api/evaluations[/{id}[/notes[/{inscription}]|/publication]]`, `DELETE /api/notes/{id}`, `GET /api/moyennes`, `/api/bulletins[/{id}|/generer]`, `GET /api/mentions`, `/api/sessions[/{id}[/cloture]]`, `/api/epreuves[/{id}[/notes]]`, `/api/resultats[/generer]` |
| Emploi du temps | `/api/creneaux[/{id}]`, `/api/edt[/{id}]`, `/api/seances[/{id}]`, `/api/absences[/{id}|/synthese]` |
| Écolage | `/api/tarifs[/{id}]`, `GET /api/inscriptions/{id}/echeances`, `POST /api/echeanciers/{generer,supprimer}`, `/api/echeances/{id}[/paiements|/encaisser|/remise]`, `/api/paiements/{id}`, `GET /api/ecolage/situation` |
| Paie | `GET /api/paie`, `GET /api/paie/heures`, `POST /api/paie/calculer`, `POST /api/paie/{id}/payer`, `PUT/DELETE /api/paie/{id}` |
| Rapports | `GET /api/rapports`, `GET /api/rapports/{key}`, `GET /api/rapports/{key}/csv` |
| Administration | `/api/admin/{info,parametres[/{cle}],etablissement,annees[/{id}/activer],journal,sauvegardes[/restaurer|/purger]}` |
| Comptes / maintenance | `/api/utilisateurs[/{code}[/actif]]`, `GET /api/profils`, `/api/tables[/{name}[/supprimer]]` |

## 5. Interface (`ltadmin/web/static`)

* **Sans framework ni build** : `core.js` (client API, formatage, formulaires, tableaux, modales,
  notifications, impression), `app.js` (session, cache du référentiel, menu par habilitations,
  routeur `#/vue/param?onglet=`), et **17 vues** dans `views/` (`App.register("cle", fn)`), une par
  module du menu (`App.MODULES`, même ordre que `habilitations.MENU_ORDER`).
* Conventions : les vues construisent le DOM avec `el()`/`dataTable()`/`card()`/`tabs()` ;
  les écritures passent par `modal.form({fields, onSubmit})` puis `toast` ; les erreurs API
  (`ApiError`) sont affichées par `reportError` ; un 401 hors `/api/auth/` renvoie à l'écran de
  connexion. Les impressions (bulletins, reçus, PV, EDT, fiches de paie) utilisent la zone
  `#impression` et les styles `@media print`.
* Les composants réutilisables inter-vues sont des fonctions globales (`crudSection`, `ligneKv`,
  `editerEtudiant`, `inscrireEtudiant`, `imprimerRecu`…) ; `index.html` charge les scripts dans
  l'ordre de dépendance.

## 6. Base de données (`ltadmin/data/schema_ddl.py`)

* 33 tables (mêmes noms et colonnes que la base Access d'origine), clés naturelles pour
  `ETABLISSEMENT`, `FILIERE`, `NIVEAU`, `MATIERE`, `MODULE_FORMATION`, `PARAMETRE`, `UTILISATEUR`,
  `INTEGER PRIMARY KEY AUTOINCREMENT` ailleurs ; clés étrangères activées (`PRAGMA foreign_keys=ON`)
  ; unicités métier (`ETUDIANT.MATRICULE`, `INSCRIPTION(ID_ETUDIANT, ID_CLASSE)`,
  `NOTE(ID_EVALUATION, ID_INSCRIPTION)`, `PAIEMENT.NUM_RECU`, `PROGRAMME(ID_CLASSE, CODE_MATIERE)`…) ;
  56 index ; 8 vues `R_*` utilisées par les rapports.
* Dates stockées en texte `YYYY-MM-DD HH:MM:SS`, booléens 0/1, montants `NUMERIC` lus en `Decimal`.
* `Database` : connexion partagée, verrou réentrant, transactions explicites, `last_insert_rowid`.
* `error_helper.interpret` traduit les erreurs SQLite (UNIQUE, FOREIGN KEY, NOT NULL, verrou) en
  messages français et codes stables.
* `tools/migrate_schema.py` : migration / vérification en ligne de commande (mêmes fonctions).

## 7. Règles métier notables

* Matricules `ETU-AAAA-NNNN`, inscriptions `INS-AAAA-NNNN`, formateurs `FOR-AAAA-NNNN`, reçus
  `REC-AAAA-NNNNNN` : séquences par année, uniques.
* Bulletins : moyenne par matière = Σ(note/barème×20 × poids)/Σpoids ; moyenne générale pondérée
  par les coefficients ; rang « compétition » (ex æquo partagent le rang) ; min/max/rang par
  matière ; mention selon `GRILLE_MENTION`.
* Résultats finaux : `POIDS_CC` / `POIDS_EXAMEN` (40/60 par défaut), `MOY_ADMISSION`,
  `NOTE_ELIMINATOIRE` ; décision ADMIS / AJOURNÉ ; rang et mention.
* Écolage : échéancier = tarif réparti en `nb_tranches` ; statut recalculé après chaque paiement
  ou remise (DU → PARTIEL → SOLDÉ) ; encaissement plafonné au reste dû.
* Emploi du temps : refus si salle, formateur ou classe déjà occupés sur le même jour/créneau
  (plages de validité) ; séances rattachées à un créneau ; absences en heures.
* Paie : heures des séances « faites » sur la période × taux horaire du formateur.

## 8. Tests (`tests/`, 126 tests)

| Fichier | Périmètre |
| --- | --- |
| `test_base.py`, `test_*_service.py` | Règles métier et dépôts sur base SQLite temporaire (moteur de test = `schema_ddl.create_database`) |
| `test_web_api.py` | API appelée en mémoire : sérialisation, routeur, sessions, 401/403/404/405/400, scénario complet (étudiant → bulletin → écolage → examen → paie → rapports → administration) |
| `test_web_conformance.py` | Analyse statique : noms non définis (AST), chaque URL `/api/...` du JavaScript ↔ route serveur, menu ↔ vues ↔ `index.html`, routes ↔ modules d'habilitation, syntaxe JS (`node --check` si disponible) |

`python -m unittest discover -s tests -t . -v` — workflow GitHub Actions fourni dans
`docs/github-workflow-tests.yml` (à copier dans `.github/workflows/`).
