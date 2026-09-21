namespace LTAdmin.Data;

/// <summary>
/// Noms exacts des 33 tables et des 8 requêtes enregistrées de LTA_ADM.accdb.
/// Centralisés ici pour éviter toute faute de frappe dans le SQL des dépôts.
/// </summary>
public static class Tables
{
    public const string Utilisateur = "UTILISATEUR";
    public const string Parametre = "PARAMETRE";
    public const string Etablissement = "ETABLISSEMENT";
    public const string AnneeScolaire = "ANNEE_SCOLAIRE";
    public const string Journal = "JOURNAL";

    public const string Filiere = "FILIERE";
    public const string Niveau = "NIVEAU";
    public const string Salle = "SALLE";
    public const string Classe = "CLASSE";
    public const string ModuleFormation = "MODULE_FORMATION";
    public const string Matiere = "MATIERE";

    public const string Formateur = "FORMATEUR";
    public const string Programme = "PROGRAMME";

    public const string Etudiant = "ETUDIANT";
    public const string Inscription = "INSCRIPTION";

    public const string PeriodeEval = "PERIODE_EVAL";
    public const string Evaluation = "EVALUATION";
    public const string Note = "NOTE";

    public const string SessionExam = "SESSION_EXAM";
    public const string Epreuve = "EPREUVE";
    public const string NoteExamen = "NOTE_EXAMEN";

    public const string Creneau = "CRENEAU";
    public const string EmploiDuTemps = "EMPLOI_DU_TEMPS";
    public const string Seance = "SEANCE";
    public const string Absence = "ABSENCE";

    public const string Bulletin = "BULLETIN";
    public const string BulletinLigne = "BULLETIN_LIGNE";
    public const string GrilleMention = "GRILLE_MENTION";
    public const string ResultatFinal = "RESULTAT_FINAL";

    public const string Tarif = "TARIF";
    public const string Echeancier = "ECHEANCIER";
    public const string Paiement = "PAIEMENT";
    public const string PaieFormateur = "PAIE_FORMATEUR";
}

/// <summary>Les 8 requêtes Access livrées avec la base.</summary>
public static class SavedQueries
{
    public const string ListeEtudiant = "R_LISTE_ETUDIANT";
    public const string MoyenneMatiere = "R_MOYENNE_MATIERE";
    public const string MoyennePeriode = "R_MOYENNE_PERIODE";
    public const string BulletinDetail = "R_BULLETIN_DETAIL";
    public const string PaiementEcheance = "R_PAIEMENT_ECHEANCE";
    public const string SituationEcolage = "R_SITUATION_ECOLAGE";
    public const string EdtClasse = "R_EDT_CLASSE";
    public const string AbsenceEtudiant = "R_ABSENCE_ETUDIANT";
}

/// <summary>
/// Clés de la table PARAMETRE : les règles de gestion centralisées.
/// Les valeurs sont stockées en texte dans Access et typées côté services.
/// </summary>
public static class ParametreKeys
{
    public const string BaremeDefaut = "BAREME_DEFAUT";
    public const string MoyAdmission = "MOY_ADMISSION";
    public const string NoteEliminatoire = "NOTE_ELIMINATOIRE";
    public const string PoidsCc = "POIDS_CC";
    public const string PoidsExamen = "POIDS_EXAMEN";
    public const string SeuilAbsence = "SEUIL_ABSENCE";
    public const string Devise = "DEVISE";
}

/// <summary>Profils d'habilitation connus (table UTILISATEUR.PROFIL).</summary>
public static class Profils
{
    public const string Admin = "ADMIN";
    public const string Administrateur = "Administrateur";
    public const string Direction = "Direction";
    public const string Scolarite = "SCOLARITE";
    public const string ScolariteLibelle = "Scolarité";
    public const string Finance = "FINANCE";
    public const string Comptabilite = "Comptabilité";
    public const string Enseignant = "Enseignant";
}
