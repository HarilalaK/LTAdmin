# LTAdmin — gestion scolaire Windows

Application desktop Windows WinForms (.NET 8) branchée directement sur la base Access existante `LTA_ADM.accdb`.

## Ce qui est livré

- connexion par la table `UTILISATEUR` (`CODE_UTR`, `MOT_PASSE`, `PROFIL`) ;
- tableau de bord avec indicateurs étudiants, formateurs, paiements et tables disponibles ;
- navigation métier en français : scolarité, référentiel, pédagogie, planning, examens, bulletins, finances et administration ;
- écran générique de gestion pour **toutes les tables Access** : recherche, affichage, ajout, modification, suppression, export CSV ;
- formulaire d’édition généré à partir des métadonnées Access : types numériques, dates, booléens, champs longs, clés primaires et champs AutoNumber ;
- écran **États** pour les requêtes Access livrées (`R_LISTE_ETUDIANT`, moyennes, bulletins, paiements, EDT et absences) avec export CSV ;
- sauvegarde horodatée de la base dans `Sauvegardes\` ;
- gestion des erreurs de contraintes et détection automatique d’ACE 16 puis ACE 12 ;
- aucune migration : l’application travaille sur les tables et les règles métier déjà présentes dans `LTA_ADM.accdb`.

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

- `AccessDatabase.cs` : connexion ACE, métadonnées, clés, sauvegardes et requêtes paramétrées ;
- `DatabaseRepository.cs` : CRUD générique sans concaténer de valeurs utilisateur dans le SQL ;
- `RecordEditorForm.cs` : formulaire dynamique qui s’adapte aux colonnes réelles de l’ACCDB ;
- `MainForm.cs`, `DashboardControl.cs`, `TableManagerControl.cs` : shell et écrans de gestion ;
- `AppServices.cs` : résolution de la base, authentification et export CSV.

Le fonctionnement hors Windows n’est pas attendu : `System.Data.OleDb` s’appuie sur le fournisseur ACE installé sur la machine Windows.
