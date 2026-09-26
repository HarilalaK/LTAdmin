# LTAdmin — démarrage rapide (BTS Hôtellerie & Tourisme)

Application **desktop Python (tkinter)** branchée sur `LTA_ADM.accdb`, la base Access
existante. Aucune migration, aucune recréation de table. Le détail complet est dans
`README.md`.

## Installation (2 min)

```powershell
pip install -r requirements.txt        # pyodbc
python main.py                         # la base est cherchée automatiquement
python main.py D:\chemin\LTA_ADM.accdb # chemin explicite
```

Pré-requis : Python 3.11+ avec tkinter, et le **Microsoft Access Database Engine**
(ACE 16 ou 12) de la même architecture 32/64 bits que Python.

Ordre de recherche de la base : argument CLI → variable `LTADMIN_DB` → dossier de
l'exécutable → dossier courant → 5 dossiers parents.

Comptes livrés : `ADMIN`/`admin`, `SCOL`/`scol`, `CAISSE`/`caisse`. **Changez ces mots de
passe à la première connexion** (ils sont stockés en clair dans la base fournie).

Tests, sans Access ni tkinter : `python -m unittest discover -s tests -t .`

## Les 33 tables

| Bloc | Tables |
|---|---|
| Admin | UTILISATEUR, PARAMETRE, ETABLISSEMENT, ANNEE_SCOLAIRE, JOURNAL |
| Référentiel | FILIERE, NIVEAU, SALLE, CLASSE, MODULE_FORMATION, MATIERE |
| Personnel | FORMATEUR, PROGRAMME *(classe × matière × formateur × coefficient)* |
| Étudiants | ETUDIANT, INSCRIPTION *(1 ligne par année → historique + redoublement)* |
| Évaluations | PERIODE_EVAL, EVALUATION, NOTE |
| Examens | SESSION_EXAM, EPREUVE, NOTE_EXAMEN |
| EDT | CRENEAU, EMPLOI_DU_TEMPS, SEANCE *(cahier de texte)*, ABSENCE |
| Bulletins | BULLETIN, BULLETIN_LIGNE, GRILLE_MENTION, RESULTAT_FINAL |
| Écolage | TARIF, ECHEANCIER, PAIEMENT, PAIE_FORMATEUR |

Détail des colonnes, clés et index : `analysis/schema_tables.txt`.

**1ère / 2ème éval dynamiques** : tout est dans `PERIODE_EVAL`. Une ligne ajoutée
(3ème éval, rattrapage, examen blanc…) suffit, le calcul suit sans rien recoder. Chaque
`EVALUATION` porte son `BAREME` et son `POIDS` → un devoir sur 40 coef 2 mélangé à une
interro sur 10 fonctionne.

## Les 8 états (écran États)

`R_LISTE_ETUDIANT`, `R_MOYENNE_MATIERE`, `R_MOYENNE_PERIODE`, `R_BULLETIN_DETAIL`,
`R_PAIEMENT_ECHEANCE`, `R_SITUATION_ECOLAGE`, `R_EDT_CLASSE`, `R_ABSENCE_ETUDIANT`.

Filtres par classe / période, export CSV (`;`, UTF-8 BOM). Texte des requêtes :
`analysis/requetes_access.sql`.

## Opérations métier

| Écran | Effet |
|---|---|
| Bulletins → Générer | bulletins + lignes matières + rang (competition, min/max par matière) + mention + appréciation |
| Examens → Générer résultats | moyenne CC × `POIDS_CC` + examen × `POIDS_EXAMEN`, mention, décision, rang |
| Écolage → Générer échéancier | découpe le `TARIF` en tranches mensuelles |
| Écolage → Statut | DU / PARTIEL / SOLDE par échéance |
| Paie → Calcul | heures faites × taux horaire |
| Étudiants / Écolage | matricule `ETU-AAAA-####` et numéro de reçu uniques |
| EDT → Contrôle | refuse les doubles réservations de salle ou de formateur |

Les règles de calcul (moyenne d'admission, note éliminatoire, poids CC/examen, seuil
d'absence, devise) sont dans la table `PARAMETRE` — modifiables sans toucher au code.

## Données déjà présentes dans `LTA_ADM.accdb`

Référentiel uniquement : année 2025-2026, filières HOT et TOU, niveaux BTS1/BTS2,
4 classes, 5 salles, 4 créneaux, 17 matières (cuisine, service, hébergement, hygiène,
géo touristique, billetterie, guidage, bureautique…), 3 périodes d'évaluation,
grille de mentions, 7 paramètres, 3 utilisateurs.

**Les tables métier sont vides** (étudiants, inscriptions, notes, évaluations, créneaux
d'emploi du temps, écolage…). Détail ligne à ligne : `analysis/donnees_initiales.txt`.

## Ordre de saisie

Formateurs → Programmes (coef par matière et par classe) → Étudiants → Inscriptions →
Tarifs → échéancier → Emploi du temps → Évaluations → Notes → Bulletins.
