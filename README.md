# LTAdmin — gestion scolaire Windows

Application desktop Windows WinForms (.NET 8) branchée directement sur la base Access existante `LTA_ADM.accdb`.

## Ce qui est livré

- architecture en couches documentée (`docs/ARCHITECTURE.md`) : modèles, dépôts typés, services métier,
  statistiques, rapports, validation, authentification, journalisation, écrans ;
- connexion par la table `UTILISATEUR` (`CODE_UTR`, `MOT_PASSE`, `PROFIL`, `ACTIF`) avec habilitations
  par groupe (ADMIN, SCOLARITE, FINANCE) et journal des connexions ;
- tableau de bord avec indicateurs réels : année active, inscrits, recouvrement, échéances échues, alertes d’absence ;
- écrans métier adossés aux services : étudiants, inscriptions, saisie des notes, caisse/paiements
  (échéanciers, encaissements, reçus, remises) ;
- écran **États** pour les 8 requêtes Access livrées (listes, moyennes, bulletins, écolage, EDT, absences),
  avec filtres classe/période et export CSV ;
- procédures métier réimplémentées en C# : bulletins, résultats finaux, échéanciers, statuts, paie,
  conflits d’emploi du temps, matricules et reçus uniques ;
- maintenance générique de **toutes les tables Access** (réservée aux profils habilités) et édition
  dynamique depuis les métadonnées ;
- sauvegardes horodatées dans `Sauvegardes\` (inventaire, restauration explicite, purge) ;
- gestion des erreurs de contraintes (doublons, liaisons, verrous) et détection automatique d’ACE 16 puis ACE 12 ;
- aucune migration : l’application travaille sur les tables et les règles déjà présentes dans `LTA_ADM.accdb`,
  sans fausses données.

La liste métier reprend la base décrite dans `LISEZ_MOI.md` : étudiants, inscriptions, formateurs, programmes, évaluations, notes, emplois du temps, absences, examens, bulletins, écolage et journal.

## Pré-requis Windows

1. Windows 10/11 64 bits (ou Windows 10/11 32 bits avec un build x86 adapté).
2. .NET 8 SDK pour compiler.
3. **Microsoft Access Database Engine 2016 Redistributable** dans la même architecture que LTAdmin (ACE 16 ou ACE 12). Il est généralement déjà installé avec Microsoft Access.
4. Droits d’écriture dans le dossier contenant la base pour créer les sauvegardes.

> Si le fournisseur ACE est en 32 bits, publier l’application en x86 depuis Visual Studio. Avec Office/ACE 64 bits, publier en x64. Le projet reste AnyCPU par défaut pour faciliter le développement.

## Compiler et lancer

Depuis PowerShell à la racine du dépôt :

```powershell
dotnet restore .\LTAdmin.sln
dotnet build .\LTAdmin.sln -c Release
dotnet run --project .\src\LTAdmin\LTAdmin.csproj
```

`LTA_ADM.accdb` est copié automatiquement dans le dossier de sortie. Pour choisir un autre fichier sans modifier le projet :

```powershell
$env:LTADMIN_DB = 'D:\Donnees\LTA_ADM.accdb'
dotnet run --project .\src\LTAdmin\LTAdmin.csproj
```

Ou démarrer `LTAdmin.exe D:\Donnees\LTA_ADM.accdb`.

## Publier une version autonome

```powershell
dotnet publish .\src\LTAdmin\LTAdmin.csproj -c Release -r win-x64 --self-contained true -o .\publish\win-x64
```

Distribuer le contenu de `publish\win-x64` avec `LTA_ADM.accdb`. Le moteur ACE reste un prérequis Windows séparé.

## Compte initial de la base fournie

La base de démonstration contient le compte indiqué par la documentation existante :

- identifiant : `ADMIN`
- mot de passe : `admin`

Changez ce mot de passe dans le menu **Administration → Utilisateurs** avant une utilisation réelle.

## Organisation technique

L’architecture complète est documentée dans [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) :
couches (`Core`, `Data`, `Models`, `Repositories`, `Services`, `UI`), catalogue des services,
règles de compatibilité Access et marche à suivre pour ajouter un module.

- `Core/Result.cs` : résultats d’opérations (`Result`/`Result<T>`) et codes d’erreur stables ;
- `Data/` : connexion ACE (`AccessDatabase`, transactions, `@@IDENTITY`), traduction des erreurs
  de contraintes (`OleDbExceptionHelper`), lecture défensive (`DataRowMapper`), constantes du schéma ;
- `Models/Entities/` : les 33 entités mappées 1:1 sur la base ; `Models/Dto/` : lignes jointes ;
- `Repositories/` : 9 dépôts typés (requêtes paramétrées, jointures, `Map*`) ;
- `Services/Business/` : `StudentService`, `EnrollmentService`, `EvaluationService`, `GradeService`,
  `ReportCardService`, `ExamService`, `TimetableService`, `AttendanceService`, `PaymentService`,
  `PayrollService` (+ `StatisticsService`, `ReportService`, `BackupService`, authentification,
  paramètres, validation, journalisation) assemblés par `AppComposition` ;
- `UI/` : shell (`LoginForm`, `MainForm`, `DashboardControl`, `ReportsForm`), vues métier
  (`Views/` : étudiants, inscriptions, caisse, saisie des notes) et maintenance générique
  des tables (`TableManagerControl`, `RecordEditorForm`) réservée aux profils habilités.

Le fonctionnement hors Windows n’est pas attendu : `System.Data.OleDb` s’appuie sur le fournisseur ACE installé sur la machine Windows.
