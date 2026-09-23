# LTAdmin — gestion scolaire desktop en Python

Application **desktop Python (tkinter)** branchée directement sur la base Access existante
`LTA_ADM.accdb` — **aucune migration, aucune recréation de table**. Portage complet de
l'application WinForms .NET 8 d'origine (conservée dans `src/LTAdmin/` comme référence).

## Ce qui est livré

- architecture en couches (`ltadmin/`) : modèles, dépôts typés, services métier,
  statistiques, rapports, validation, authentification, habilitations, journalisation, écrans ;
- connexion par la table `UTILISATEUR` (`CODE_UTR`, `MOT_PASSE`, `PROFIL`, `ACTIF`) avec habilitations
  par groupe (ADMIN, Direction, Scolarité, Compta, Enseignant) et journal des connexions ;
- tableau de bord avec indicateurs réels : année active, inscrits, recouvrement, échéances échues, alertes d'absence ;
- écrans métier adossés aux services : étudiants, inscriptions, évaluations/notes, bulletins,
  examens/résultats, caisse (échéanciers, encaissements, reçus, remises), EDT/séances/absences,
  formateurs/programmes/paie ;
- écran **États** pour les 8 requêtes Access livrées (listes, moyennes, bulletins, écolage, EDT, absences),
  avec filtres classe/période et export CSV (`;`, UTF-8 BOM) ;
- procédures métier réimplémentées : bulletins (rangs « competition », min/max/rang par matière),
  résultats finaux pondérés CC 40 % / examen 60 %, échéanciers, statuts DU/PARTIEL/SOLDE,
  paie = heures × taux, conflits d'emploi du temps (salle/formateur), matricules et reçus uniques ;
- maintenance générique de **toutes les tables Access** (réservée aux profils habilités) et édition
  dynamique depuis les métadonnées ;
- sauvegardes horodatées (inventaire, restauration explicite avec copie de sécurité, purge) ;
- gestion des erreurs de contraintes (doublons, liaisons, verrous) via les codes
  `VALIDATION`, `GESTION`, `INTROUVABLE`, `DOUBLON`, `LIAISON`, `VERROUILLE`… ;
- **suite de tests d'intégration** (81 tests) exécutable sans Access grâce à un moteur SQLite
  injectable qui reproduit les règles SQL utilisées (paramètres positionnels `?`, identifiants
  `[crochets]`, `TOP n`, `@@IDENTITY`, `Nz`→`IIf`/`IFNULL`, `UCASE`…).

## Pré-requis

1. **Python 3.11+** (3.12+ recommandé) avec **tkinter** (inclus dans l'installateur Windows
   officiel — cocher *tcl/tk and IDLE*).
2. `pip install pyodbc`
3. **Microsoft Access Database Engine Redistributable** (ACE 16 ou ACE 12), même architecture
   (32/64 bits) que Python — généralement déjà installé avec Microsoft Access.
4. Droits d'écriture dans le dossier contenant la base (sauvegardes, journal).

## Lancer l'application

```powershell
pip install pyodbc
python main.py                                # la base est cherchée automatiquement
python main.py D:\chemin\LTA_ADM.accdb        # chemin explicite (argument positionnel)
```

Ordre de recherche de la base : argument CLI → variable d'environnement `LTADMIN_DB` → dossier
de l'exécutable → dossier courant → remontée jusqu'à 5 niveaux parents.

Comptes livrés avec les données initiales : `ADMIN`/`admin` (Administrateur),
`SCOL`/`scol` (Scolarité), `CAISSE`/`caisse` (Comptabilité). La connexion est insensible à la casse
(sémantique Access).

## Lancer les tests (sans Access ni tkinter)

```powershell
python -m unittest discover -s tests -t . -v
```

Les tests reconstruisent en SQLite les 33 tables + les 8 requêtes depuis
`analysis/extraction_complete.json` (données initiales réelles), injectent ce moteur dans
l'application et valident : infrastructure/habilitations, étudiants/inscriptions,
évaluations/notes/bulletins, examens/résultats, écolage/paie/EDT, statistiques/états/CSV,
administration/sauvegardes/maintenance des tables.

## Règles Access respectées

- SQL 100 % paramétré positionnel (`?`), jamais de concaténation de valeurs ;
- identifiants entre crochets `[TABLE].[CHAMP]` ;
- jointures parenthésées à la Jet `FROM ((A INNER JOIN B) INNER JOIN C)` ;
- `SELECT TOP n` pour les listes tronquées ;
- `SELECT @@IDENTITY` sur le même curseur après insertion (autonumbers) ;
- pas de `Nz()` côté Python : équivalents `IIf(...)` dans les requêtes recréées, `COALESCE`-like
  géré par le code.

## Structure du dépôt

```
main.py                 point d'entrée (localisation base, login, fenêtre principale)
ltadmin/
  core/                 résultats typés, erreurs, journalisation
  data/                 moteur pyodbc + AccessDatabase (transactions, @@IDENTITY)
  models/               entités (dataclasses) et DTO
  repositories/         dépôts typés (étudiants, notes, écolage, EDT, paie…)
  services/             services métier, auth, habilitations, stats, rapports, sauvegardes
  ui/                   thème, widgets, dialogues, vues (16 écrans + éditeur générique)
tests/                  moteur SQLite de test + 7 suites (91 tests)
analysis/               requêtes Access, schéma, extraction complète des données
docs/ARCHITECTURE.md    architecture (écrite pour la version C#, les couches sont identiques)
src/LTAdmin/            code C# .NET 8 d'origine (référence du portage)
LTA_ADM.accdb           base de données — source de vérité, inchangée
```

## Habilitations par profil

| Profil | Accès |
|---|---|
| Administrateur | tout, y compris Administration et Tables |
| Direction | tout sauf Administration / Tables |
| Scolarité | tout sauf Écolage / Paie / Administration / Tables |
| Comptabilité | Écolage, Paie, Statistiques, Rapports |
| Enseignant | Notes, Bulletins, Examens, EDT, Absences, Formateurs |

Profil inconnu → tableau de bord + états. Le menu n'affiche que les modules autorisés.

## Sauvegardes

Sauvegardes horodatées dans le sous-dossier `Sauvegardes\` à côté de la base :
`LTA_ADM_AAAAMMJJ_HHMMSS.accdb`.
La restauration copie d'abord la base courante en `LTA_ADM_avant_restauration_*.accdb`,
puis écrase ; la purge exige un nombre conservé ≥ 1.
