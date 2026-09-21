# Architecture technique — LTAdmin

> Application Windows Desktop **C# WinForms .NET 8**, adossée à la base existante
> **`LTA_ADM.accdb` (source de vérité)**. Analyse du schéma : `ANALYSE_BASE_LTA.md`.

## 1. Principes intangibles

| Règle | Mise en œuvre |
|---|---|
| Ne pas supprimer / réinitialiser la base | Aucun `DROP`, aucun `DELETE` global, aucune recréation de table dans le code |
| Ne pas modifier les données sans action explicite | Chaque écriture naît d'un clic utilisateur → service → dépôt ; les lectures (dashboard, états, stats) n'écrivent jamais |
| Requêtes paramétrées partout | Paramètres positionnels OleDb (`?`) via `AccessDatabase.Parameter()` ; les identifiants sont protégés par `[crochets]` |
| Compatibilité Microsoft Access | SQL dialecte ACE : `TOP`, `SELECT @@IDENTITY`, jointures parenthésées, `IIf()` (jamais `Nz()` en SQL ad-hoc), booléens et dates en paramètres |
| Erreurs de contraintes gérées | `OleDbExceptionHelper` traduit les codes natifs ACE (3022, 3200/3201, 3314, 3163…) en messages français + codes stables |
| Aucune logique métier dans les Forms | Les écrans appellent les services et affichent les `Result` ; toute règle vit dans `Services/` |
| Aucune donnée simulée | Chaque écran affiche des données lues depuis la base ; en cas d'échec technique, message d'erreur explicite |

## 2. Vue d'ensemble

```
┌────────────────────────────────────────────────────────────┐
│ UI (WinForms) — Forms + UserControls                       │
│  Shell (Login, Main, Dashboard) · Vues métier · Maintenance│
└──────────────────────────┬─────────────────────────────────┘
                           │ AppComposition (racine de composition)
┌──────────────────────────▼─────────────────────────────────┐
│ Services                                                   │
│  Métier (10) · Statistiques · Rapports · Auth · Paramètres │
│  Validation · Journalisation · Sauvegarde                  │
└──────────────────────────┬─────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────┐
│ Repositories (dépôts typés, un par agrégat)                │
└──────────────────────────┬─────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────┐
│ Data — AccessDatabase (ACE/OleDb) · Models (33 entités)    │
└──────────────────────────┬─────────────────────────────────┘
                           │
                    LTA_ADM.accdb (inchangeable par défaut)
```

Dépendances strictement descendantes : `UI → Services → Repositories → Data → .accdb`.
`Core` (types partagés) est référencé par toutes les couches.

## 3. Arborescence

```
src/LTAdmin/
├── Program.cs                  # Démarrage : base → composition → login → shell
├── GlobalUsings.cs             # System.Drawing + System.Windows.Forms
├── Core/
│   └── Result.cs               # Result / Result<T> + ErrorCodes stables
├── Data/
│   ├── AccessDatabase.cs       # Connexion ACE, SQL paramétré, transactions, @@IDENTITY, backup fichier
│   ├── AccessTransaction.cs    # Portée de transaction (Complete / rollback auto)
│   ├── DatabaseRepository.cs   # Accès générique (maintenance des tables, états bruts)
│   ├── DataRowMapper.cs        # Lecture défensive des DataRow (DBNull, colonnes absentes)
│   ├── OleDbExceptionHelper.cs # Traduction des erreurs ACE → messages français + codes
│   └── Schema.cs               # Tables, SavedQueries, ParametreKeys, Profils (constantes)
├── Models/
│   ├── DbModels.cs             # Métadonnées génériques + session + catalogue de navigation
│   ├── Entities/               # 33 entités 1:1 avec le schéma (9 fichiers par bloc)
│   └── Dto/BusinessDto.cs      # Lignes jointes pour listes et grilles
├── Repositories/               # 9 dépôts + RepositoryBase (CRUD typé paramétré, jointures)
├── Services/
│   ├── AppComposition.cs       # Assemble base, dépôts, services pour les écrans
│   ├── Auth/                   # AuthenticationService (+ Habilitations par groupe)
│   ├── Business/               # 10 services de gestion (+ MentionHelper)
│   ├── Common/ServiceBase.cs   # Base : Db, Logger, Journal, Parametres, gestion d'erreurs
│   ├── Infrastructure/         # DatabaseLocator, BackupService
│   ├── Logging/                # AppLogger (fichier) + JournalService (table JOURNAL)
│   ├── Referentiel/            # ParametreService (règles de gestion typées + cache)
│   ├── Reports/                # ReportService (8 requêtes + filtres + repli Nz) + CsvExporter
│   ├── Statistics/             # StatisticsService + StatisticsModels (pilotage)
│   └── Validation/             # ValidationResult + Guard + validateurs par entité
└── UI/
    ├── LoginForm, MainForm, DashboardControl, ReportsForm, TableManagerControl, RecordEditorForm, Theme
    ├── IRefreshableView.cs     # Contrat « Actualiser » des vues
    └── Views/                  # Écrans métier : BusinessView (+ DialogPrompt),
                                # Students, Enrollments, Payments (+ PaymentDialog), Grades
```

## 4. Couche Data

- **Connexion unique** `AccessDatabase` (ouverte au démarrage), fournisseurs `ACE.OLEDB.16.0` puis `12.0`.
- **Transactions** : `using var tx = Db.BeginTransaction(); …; tx.Complete();` — toute commande créée
  pendant la portée s'y enrôle automatiquement. Pas d'imbrication (limite ACE).
- **AutoNumber** : `InsertAndGetId()` = `INSERT` + `SELECT @@IDENTITY` sur la même connexion.
- **Contraintes** : `OleDbExceptionHelper.Interpret()` mappe les `NativeError` ACE puis, en repli, des
  mots-clés FR/EN (les messages dépendent de la langue d'Office) :
  `3022 doublon`, `3201 liaison manquante`, `3200/3202 suppression refusée (liés)`,
  `3314/3058 valeur requise`, `3163 texte trop long`, `3349 dépassement`, `3021 introuvable`,
  `3197/3260/3261 verrous`, `3043/3050/3051 fichier verrouillé`.
- **Constantes** : `Tables` (33 noms), `SavedQueries` (8 requêtes), `ParametreKeys` (7 clés),
  `Profils` (`ADMIN`, `SCOLARITE`, `FINANCE`).

## 5. Modèles

- **33 entités** (`Models/Entities/`, 9 fichiers par bloc fonctionnel), types C# alignés sur Access :
  `TEXT→string?`, `LONG→int?`, `DOUBLE→double?`, `CURRENCY→decimal`, `DATETIME→DateTime?`,
  `BOOLEAN→bool?`, `MEMO→string?`.
- **DTO** (`Models/Dto/BusinessDto.cs`) : `ClasseDetail`, `InscriptionDetail`, `ProgrammeDetail`,
  `EvaluationDetail`, `NoteSaisieRow`, `EpreuveDetail`, `EdtSlotDetail`, `SeanceDetail`,
  `EcheanceDetail`, `SituationEcolageRow`, `MoyenneMatiereRow`, `MoyennePeriodeRow`,
  `BulletinResume`, `PaiementCree`, `BackupInfo`.

## 6. Dépôts (Repositories)

Un dépôt par agrégat, dérivant de `RepositoryBase` (helpers `QueryList`, `QuerySingle`,
`InsertAndGetId`, `ScalarInt/Decimal/Double/String`, `Exists`). Chaque dépôt expose :

- le CRUD typé de ses tables (requêtes paramétrées, identifiants quotés) ;
- les requêtes de lecture jointes dont les services ont besoin (détails, grilles, cumuls) ;
- des `Map*` publics et défensifs (`DataRowMapper`).

| Dépôt | Tables |
|---|---|
| `AdminRepository` | UTILISATEUR, PARAMETRE, ETABLISSEMENT, ANNEE_SCOLAIRE, JOURNAL |
| `ReferentielRepository` | FILIERE, NIVEAU, SALLE, CLASSE, MODULE_FORMATION, MATIERE |
| `StaffRepository` | FORMATEUR, PROGRAMME |
| `StudentRepository` | ETUDIANT |
| `EnrollmentRepository` | INSCRIPTION |
| `EvaluationRepository` | PERIODE_EVAL, EVALUATION, NOTE (+ R_MOYENNE_*) |
| `ExamRepository` | SESSION_EXAM, EPREUVE, NOTE_EXAMEN |
| `PlanningRepository` | CRENEAU, EMPLOI_DU_TEMPS, SEANCE, ABSENCE |
| `BulletinRepository` | BULLETIN, BULLETIN_LIGNE, GRILLE_MENTION, RESULTAT_FINAL |
| `FinanceRepository` | TARIF, ECHEANCIER, PAIEMENT, PAIE_FORMATEUR |

> `DatabaseRepository` (couche Data) reste le moteur de la **maintenance générique** des tables ;
> les écrans métier utilisent exclusivement les dépôts typés via les services.

## 7. Services

### 7.1 Services métier (10) — `Services/Business/`

| Service exigé | Classe | Responsabilités |
|---|---|---|
| StudentService | `StudentService` | Recherche, CRUD étudiant, matricule auto `ETU-AAAA-####`, unicité `IX_ETU_MAT` |
| EnrollmentService | `EnrollmentService` | Inscription (anti-doublon, effectif max), n° `INS-AAAA-####`, sortie, suppression protégée |
| EvaluationService | `EvaluationService` | Périodes (clôture), évaluations (barème/poids > 0, défauts depuis PARAMETRE), publication |
| GradeService | `GradeService` | Grille de saisie par évaluation, upsert (unicité), note ∈ [0, barème] sauf absent, période non clôturée, classe cohérente, moyennes via `R_MOYENNE_*` |
| ReportCardService | `ReportCardService` | `GENERER_BULLETIN` : moyennes `R_MOYENNE_MATIERE`, points = moy × coef, rangs « competition », mention via grille, appréciation, absences ; régénération idempotente **en transaction** |
| ExamService | `ExamService` | Sessions (clôture), épreuves, notes d'examen, `GENERER_RESULTAT_FINAL` : CC × POIDS_CC + exam × POIDS_EXAMEN, mention, décision vs MOY_ADMISSION, rang ; idempotent **par inscription** (le schéma ne porte pas de session sur RESULTAT_FINAL — voir §9) |
| TimetableService | `TimetableService` | Slots + `EDT_CONFLIT` (salle et formateur sur jour × créneau actifs), jours Lundi–Dimanche, salle disponible, séances (cahier de texte) |
| AttendanceService | `AttendanceService` | Appel depuis une séance, justification, cumul, **alerte SEUIL_ABSENCE** (exclusion d'examen) |
| PaymentService | `PaymentService` | Tarifs, `GENERER_ECHEANCIER` **idempotent** (tranches manquantes, mensualisation depuis l'inscription, dernière tranche = arrondis), `MAJ_STATUT_ECHEANCE` (DU/PARTIEL/SOLDE), `Encaisser` (reçu unique `REC-AAAA-######`, statut recalculé, en transaction), annulation, remises, situations |
| PayrollService | `PayrollService` | `CALCUL_PAIE_FORMATEUR` : Σ SEANCE.NB_HEURES via EDT→PROGRAMME × TAUX_HORAIRE ; paie `PAYE` figée |

`MentionHelper` (partagé bulletins/résultats) : lecture de `GRILLE_MENTION` (intervalles `[INF, SUP[`,
borne 20 incluse), appréciations par défaut, rangs « competition » (1, 2, 2, 4 ; non classés = 0).

### 7.2 Services transverses exigés

| Service exigé | Classe | Responsabilités |
|---|---|---|
| StatisticsService | `Services/Statistics/StatisticsService` | Effectifs + remplissage, sexe, redoublants, sorties, avancement de saisie, résultats/mentions par classe, absentéisme, seuil, recouvrement (global/par classe), échues non soldées, encaissements par mode, `GetDashboard()` |
| ReportService | `Services/Reports/ReportService` | Catalogue des **8 requêtes** (`Title`, description, filtres classe/période), exécution paramétrée, **repli sans `Nz()`** pour `R_SITUATION_ECOLAGE`, export CSV |
| BackupService | `Services/Infrastructure/BackupService` | Sauvegarde horodatée, inventaire, **restauration explicite** (copie de sécurité préalable), purge |

Autres services :

| Classe | Rôle |
|---|---|
| `Auth/AuthenticationService` | Connexion paramétrée sur `UTILISATEUR` (`ACTIF` requis, journalisée), changement de mot de passe ; `Habilitations.CanAccess(profil, groupe)` |
| `Referentiel/ParametreService` | `BaremeDefaut` (20), `MoyAdmission` (10), `NoteEliminatoire` (5), `PoidsCc` (40), `PoidsExamen` (60), `SeuilAbsence` (30), `Devise` (MGA) + cache et `SetValue` journalisée |
| `Logging/JournalService` | Écritures « au mieux » en table `JOURNAL` (jamais bloquantes) : connexions, CRUD, opérations |
| `Logging/AppLogger` | Fichier `logs/ltadmin-AAAAMMJJ.log` (erreurs techniques, démarrage) |
| `Validation/*` | `ValidationResult`, `Guard` (requis, longueurs = limites Access, plages, e-mail, `HH:mm`…), validateurs par entité |
| `AppComposition` | Racine de composition : construit et expose base, dépôts, services aux écrans |

### 7.3 Contrat des services

- Toute opération d'écriture retourne `Result` / `Result<T>` (`IsSuccess`, `Message` français affichable,
  `Code` parmi `ErrorCodes`, `Errors` détaillées) — **jamais d'exception vers l'UI** pour les cas gérés.
- Les lectures retournent des listes typées (ou DTO) ; en cas d'échec technique : liste vide + trace fichier.
- Chaque écriture est **validée avant** tout accès base, puis **journalisée** (`JOURNAL` + code utilisateur).
- Les opérations multi-tables sont **transactionnelles** (bulletins, résultats, encaissement, activation d'année…).

## 8. Compatibilité Access — règles appliquées

1. **Paramètres positionnels** `?` dans l'ordre (OleDb ignore les noms) ; jamais de concaténation de valeurs.
2. **Identifiants quotés** `[TABLE]`/`[COLONNE]` partout (mots réservés, espaces).
3. **Jointures parenthésées** : N jointures = N niveaux (`FROM (((A ⋈ B) ⋈ C) ⋈ D)`), exigence du dialecte ACE.
4. **Pas de `Nz()` via OleDb** (fonction VBA indisponible hors Access) : `IIf(champ IS NULL, …)` ou calculs en C#.
   Les requêtes `R_*` existantes sont réutilisées telles quelles, sauf repli documenté pour `R_SITUATION_ECOLAGE`.
5. **`TOP n`** (jamais `LIMIT`), `SELECT @@IDENTITY` après `INSERT`, `LIKE` avec `%`, `ORDER BY` explicite.
6. **Aucun `UPDATE…JOIN` ni `DELETE…JOIN`** : lectures d'identifiants puis mises à jour ciblées par clé.
7. **Agrégats NULL-sûrs** : `SUM` vide = `NULL` → géré côté C# (`?? 0`) ; regroupements en C# quand le SQL
   devient fragile (mentions, recouvrements, cumuls).
8. **Concurrence** : connexion unique, usage mono-poste ; erreurs de verrous traduites (`VERROUILLE`).

## 9. Écarts et choix documentés (schéma inchangé)

- `RESULTAT_FINAL` ne porte **pas de colonne session** : une seule ligne par inscription ; la génération est
  idempotente par inscription (suppression ciblée + recalcul). Le libellé de session est journalisé.
- `MOY_CC` (résultats) = moyenne des bulletins toutes périodes ; si CC ou examen absent, la moyenne générale
  reprend la partie disponible (documenté dans `ExamService`) ; sinon `NULL`.
- `PONDERATION` (`PERIODE_EVAL`) n'est pas exploitée par les requêtes livrées : non utilisée (comme la base).
- `JOUR` / heures (`CRENEAU`, `EPREUVE`) restent du **texte** : jours validés (Lundi–Dimanche), heures `HH:mm`.
- `PHOTO`/`LOGO` restent des **chemins** (pas de binaires).
- Mots de passe `UTILISATEUR` **en clair** (état historique) : vérification centralisée dans
  `AuthenticationService` pour permettre un hachage ultérieur sans toucher les écrans.
- `FORMATEUR.MATRICULE` n'a pas d'index unique (contrairement à `ETUDIANT`) : génération prudente côté service.
- `ECHEANCIER` n'a pas de contrainte d'unicité : idempotence applicative (tranches manquantes uniquement).
- `ABSENCE` n'a pas d'unicité (séance, inscrit) : plusieurs lignes possibles (volontaire : absences + retards).

## 10. Authentification & habilitations

- `Authenticate(login, motDePasse)` : requête paramétrée `WHERE [CODE_UTR] = ?` (comparaison Access,
  insensible à la casse), compte `ACTIF` requis, toute tentative journalisée (`CONNEXION` / `CONNEXION_REFUSEE`).
- `ChangePassword` : vérification de l'ancien, ≥ 4 caractères, journalisé.
- `Habilitations` : `ADMIN` = tout ; `SCOLARITE` = tout sauf Finances et Administration ;
  `FINANCE` = Finances (+ tableau de bord et états, ouverts à tous les connectés) ;
  profil inconnu = tableau de bord et états uniquement. La navigation désactive les entrées interdites.

## 11. Interface (Forms et UserControls)

- **Shell** : `LoginForm` (via `Auth`), `MainForm` (navigation par groupes, habilitations, sauvegarde via
  `BackupService`, états via `ReportService`), `DashboardControl` (indicateurs réels de `StatisticsService`).
- **Vues métier** (`UI/Views/`, base `BusinessView` : `App`, `Session`, helpers) — données réelles uniquement :
  - `StudentsControl` + `StudentEditForm` : recherche, CRUD étudiant.
  - `EnrollmentsControl` + `EnrollmentEditForm` : filtre par classe, inscription (recherche étudiant),
    modification/sortie, génération d'échéancier, suppression protégée.
  - `PaymentsControl` + `PaymentDialog` : caisse — situations par classe, échéances, encaissement (reçu),
    remises, annulation de paiement.
  - `GradesControl` : classe × période → évaluations → grille de saisie (note/absent/observation), période
    clôturée = saisie verrouillée.
- **Maintenance générique** (`TableManagerControl` + `RecordEditorForm`, pilotés par les métadonnées Access) :
  conservée pour les tables sans vue métier et l'administration — **réservée aux profils habilités**.
- **États** (`ReportsForm`) : catalogue `ReportService`, filtres classe/période contextuels, export CSV.

## 12. Ajouter un module métier (marche à suivre)

1. Entité(s) dans `Models/Entities/` (+ DTO si liste jointe dans `Models/Dto/`).
2. Méthodes dans le dépôt de l'agrégat (SQL paramétré + `Map*`).
3. Validateur dans `Services/Validation/` (longueurs = limites du schéma).
4. Méthodes dans le service métier (`Result`, journalisation, transaction si multi-tables).
5. Vue dans `UI/Views/` (base `BusinessView`, `RefreshData()`), entrée dans `MainForm.BuildModules()`.
6. Documenter ici tout choix non trivial (§9).

## 13. Feuille de route (prochaines vues métier)

Services déjà prêts, vues à construire sur le même patron : programmes/formateurs, emploi du temps
(grille + conflits), appel/absences, épreuves/notes d'examen, génération + aperçu des bulletins,
résultats/délibérations, paie des formateurs, statistiques détaillées, utilisateurs/paramètres/journal,
impression (bulletin, reçu). La maintenance générique couvre ces tables en attendant, sans fausses données.

## 14. Compilation & exécution (Windows)

```powershell
dotnet restore .\LTAdmin.sln
dotnet build .\LTAdmin.sln -c Release
dotnet run --project .\src\LTAdmin\LTAdmin.csproj
```

Prérequis : .NET 8 SDK + **Microsoft Access Database Engine 2016** (même architecture que l'app, x64/x86).
`LTA_ADM.accdb` est copié dans le dossier de sortie ; `LTADMIN_DB` ou un argument permet d'en choisir un autre.
Comptes de la base fournie : `ADMIN/admin`, `SCOL/scol`, `CAISSE/caisse` (à changer avant usage réel).
