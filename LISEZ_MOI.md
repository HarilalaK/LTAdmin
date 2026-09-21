# Base Access — Gestion scolarité LTA (BTS Hôtellerie & Tourisme)

## Installation (2 min)
1. Access → **Nouvelle base de données vide** → `GESTION_LTA.accdb` (ou `.mdb` si tu veux rester en 2003).
2. `ALT+F11` → **Fichier > Importer un fichier…** → `GESTION_LTA.bas`.
3. Menu **Outils > Références…** → cocher *Microsoft Office xx.x Access database engine Object Library* (DAO).
4. Curseur dans `CREER_BASE_LTA` → **F5**.
5. `CTRL+G` (fenêtre Exécution) pour voir d'éventuelles erreurs.

Relancer la procédure = remise à zéro (`RAZ = True` en haut du module).

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

**1ère / 2ème éval dynamiques** : tout est dans `PERIODE_EVAL`. Tu ajoutes une ligne (3ème éval, rattrapage, examen blanc…) et tout le calcul suit, rien à recoder. Chaque `EVALUATION` a son `BAREME` et son `POIDS` → devoir sur 40 coef 2 mélangé avec une interro sur 10, ça marche.

## Requêtes livrées
`R_LISTE_ETUDIANT`, `R_MOYENNE_MATIERE`, `R_MOYENNE_PERIODE`, `R_BULLETIN_DETAIL`,
`R_PAIEMENT_ECHEANCE`, `R_SITUATION_ECOLAGE`, `R_EDT_CLASSE`, `R_ABSENCE_ETUDIANT`.

## Procédures métier
| Appel | Effet |
|---|---|
| `GENERER_BULLETIN(idClasse, idPeriode)` | bulletins + lignes matières + rang + mention + appréciation |
| `GENERER_RESULTAT_FINAL(idClasse, idSession)` | moyenne CC × POIDS_CC + examen × POIDS_EXAMEN, mention, décision, rang |
| `GENERER_ECHEANCIER(idInscription)` | découpe les TARIF en tranches mensuelles |
| `MAJ_STATUT_ECHEANCE(idInscription)` | DU / PARTIEL / SOLDE |
| `CALCUL_PAIE_FORMATEUR(idFormateur, début, fin)` | heures faites × taux horaire |
| `NOUVEAU_MATRICULE()` / `NOUVEAU_RECU()` | à mettre en *Valeur par défaut* des champs |
| `EDT_CONFLIT(jour, idCreneau, idSalle, idProg)` | bloque double réservation salle/formateur |

Les règles de calcul (moyenne d'admission, note éliminatoire, poids CC/examen, seuil d'absence, devise) sont dans la table `PARAMETRE` — modifiables sans toucher au code.

## Données déjà chargées
Année 2025-2026, filières HOT et TOU, niveaux BTS1/BTS2, 4 classes, 5 salles, 17 matières (cuisine, service, hébergement, hygiène, géo touristique, billetterie, guidage, bureautique…), 4 créneaux, grille de mentions, 3 utilisateurs (`ADMIN/admin`).

## Ordre de saisie conseillé
FORMATEUR → PROGRAMME (coef par matière et par classe) → ETUDIANT → INSCRIPTION → TARIF → `GENERER_ECHEANCIER` → EMPLOI_DU_TEMPS → EVALUATION → NOTE → `GENERER_BULLETIN`.

## Reste à faire côté interface
Formulaires (saisie notes en grille par classe/matière), états Bulletin et Reçu de paiement, menu général. Dis-moi lesquels tu veux, je te génère le code des formulaires/états de la même façon.
