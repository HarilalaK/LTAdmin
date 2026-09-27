"""Validation : contrôles élémentaires et validateurs par entité.

Les longueurs correspondent aux limites TEXT d'Access (schéma LTA_ADM.accdb).
Les services refusent toute écriture invalide avant de toucher la base.
"""

from __future__ import annotations

import datetime as _dt
import re
from decimal import Decimal
from typing import List, Optional

from ltadmin.models.entities import (
    Absence,
    Classe,
    EmploiDuTemps,
    Epreuve,
    Etudiant,
    Evaluation,
    Formateur,
    Inscription,
    PeriodeEval,
    Programme,
    Seance,
    SessionExam,
    Tarif,
)

_HEURE_RE = re.compile(r"^([01]?\d|2[0-3]):[0-5]\d$")


class ValidationResult:

    def __init__(self) -> None:
        self.errors: List[str] = []

    @property
    def is_valid(self) -> bool:
        return not self.errors

    @staticmethod
    def success() -> "ValidationResult":
        return ValidationResult()

    def add_error(self, message: str) -> None:
        if message and message.strip():
            self.errors.append(message)

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.add_error(message)

    def to_message(self) -> str:
        return "\n".join(self.errors)


class Guard:
    """Contrôles élémentaires réutilisables."""

    @staticmethod
    def required(result: ValidationResult, value: Optional[str], field: str) -> None:
        result.require(bool(value and value.strip()), f"{field} : valeur obligatoire.")

    @staticmethod
    def required_id(result: ValidationResult, value: Optional[int], field: str) -> None:
        result.require(value is not None and value > 0, f"{field} : valeur obligatoire.")

    @staticmethod
    def required_code(result: ValidationResult, value: Optional[str], field: str) -> None:
        result.require(bool(value and value.strip()), f"{field} : valeur obligatoire.")

    @staticmethod
    def max_length(result: ValidationResult, value: Optional[str], max_len: int,
                   field: str) -> None:
        if value and len(value) > max_len:
            result.add_error(
                f"{field} : {max_len} caractères maximum (actuellement {len(value)}).")

    @staticmethod
    def positive(result: ValidationResult, value, field: str, allow_zero: bool = False) -> None:
        if value is None:
            return
        if isinstance(value, Decimal):
            ok = value >= 0 if allow_zero else value > 0
        else:
            ok = value >= 0 if allow_zero else value > 0
        result.require(ok, f"{field} : montant "
                           f"{'positif ou nul' if allow_zero else 'strictement positif'} attendu.")

    @staticmethod
    def range(result: ValidationResult, value: Optional[float], minimum: float,
              maximum: float, field: str) -> None:
        if value is None:
            return
        result.require(minimum <= value <= maximum,
                       f"{field} : valeur entre {minimum} et {maximum} attendue.")

    @staticmethod
    def in_set(result: ValidationResult, value: Optional[str], field: str,
               allowed) -> None:
        if not value or not value.strip():
            return
        lowered = {a.lower() for a in allowed}
        result.require(value.strip().lower() in lowered,
                       f"{field} : valeur attendue parmi {', '.join(allowed)}.")

    @staticmethod
    def email(result: ValidationResult, value: Optional[str], field: str) -> None:
        if not value or not value.strip():
            return
        text = value.strip()
        at = text.find("@")
        result.require(0 < at < len(text) - 1 and " " not in text,
                       f"{field} : adresse e-mail invalide.")

    @staticmethod
    def past_or_today(result: ValidationResult, value: Optional[_dt.datetime], field: str) -> None:
        if value is None:
            return
        result.require(value.date() <= _dt.date.today(), f"{field} : date future interdite.")

    @staticmethod
    def date_order(result: ValidationResult, debut, fin, field_debut: str, field_fin: str) -> None:
        if debut is None or fin is None:
            return
        result.require(fin >= debut,
                       f"{field_fin} : doit être postérieure ou égale à {field_debut}.")

    @staticmethod
    def heure_texte(result: ValidationResult, value: Optional[str], field: str) -> None:
        if not value or not value.strip():
            return
        result.require(_HEURE_RE.match(value.strip()) is not None,
                       f"{field} : heure au format HH:mm attendue (ex. 07:30).")


class StudentValidator:

    @staticmethod
    def validate(etudiant: Etudiant) -> ValidationResult:
        result = ValidationResult()
        g = Guard
        g.required(result, etudiant.nom, "Nom")
        g.required(result, etudiant.prenom, "Prénom")
        g.max_length(result, etudiant.matricule, 40, "Matricule")
        g.max_length(result, etudiant.nom, 120, "Nom")
        g.max_length(result, etudiant.prenom, 160, "Prénom")
        g.in_set(result, etudiant.sexe, "Sexe", ("M", "F"))
        g.past_or_today(result, etudiant.date_naissance, "Date de naissance")
        if etudiant.date_naissance is not None:
            result.require(
                etudiant.date_naissance.date() >= _dt.date.today() - _dt.timedelta(days=36500),
                "Date de naissance : date invraisemblable (plus de 100 ans).")
        g.max_length(result, etudiant.lieu_naissance, 120, "Lieu de naissance")
        g.max_length(result, etudiant.cin, 40, "CIN")
        g.max_length(result, etudiant.nationalite, 80, "Nationalité")
        g.max_length(result, etudiant.adresse, 300, "Adresse")
        g.max_length(result, etudiant.tel, 80, "Téléphone")
        g.max_length(result, etudiant.email, 160, "E-mail")
        g.email(result, etudiant.email, "E-mail")
        g.max_length(result, etudiant.nom_tuteur, 160, "Nom du tuteur")
        g.max_length(result, etudiant.tel_tuteur, 80, "Téléphone du tuteur")
        g.max_length(result, etudiant.profession_tuteur, 120, "Profession du tuteur")
        g.max_length(result, etudiant.serie_bacc, 40, "Série du bac")
        g.max_length(result, etudiant.etab_origine, 200, "Établissement d’origine")
        g.max_length(result, etudiant.photo, 510, "Photo (chemin)")
        g.max_length(result, etudiant.statut, 40, "Statut")
        if etudiant.annee_bacc is not None:
            result.require(1950 <= etudiant.annee_bacc <= _dt.date.today().year + 1,
                           "Année du bac : année invalide.")
        return result


class EnrollmentValidator:

    @staticmethod
    def validate(inscription: Inscription) -> ValidationResult:
        result = ValidationResult()
        g = Guard
        g.required_id(result, inscription.id_etudiant, "Étudiant")
        g.required_id(result, inscription.id_classe, "Classe")
        g.max_length(result, inscription.num_inscription, 40, "N° d’inscription")
        g.max_length(result, inscription.statut, 40, "Statut")
        g.max_length(result, inscription.motif_sortie, 300, "Motif de sortie")
        g.date_order(result, inscription.date_inscription, inscription.date_sortie,
                     "date d’inscription", "date de sortie")
        return result


class StaffValidator:

    @staticmethod
    def validate_formateur(formateur: Formateur) -> ValidationResult:
        result = ValidationResult()
        g = Guard
        g.required(result, formateur.nom, "Nom")
        g.required(result, formateur.prenom, "Prénom")
        g.max_length(result, formateur.matricule, 40, "Matricule")
        g.max_length(result, formateur.nom, 120, "Nom")
        g.max_length(result, formateur.prenom, 120, "Prénom")
        g.in_set(result, formateur.sexe, "Sexe", ("M", "F"))
        g.past_or_today(result, formateur.date_naissance, "Date de naissance")
        g.max_length(result, formateur.cin, 40, "CIN")
        g.max_length(result, formateur.adresse, 300, "Adresse")
        g.max_length(result, formateur.tel, 80, "Téléphone")
        g.max_length(result, formateur.email, 160, "E-mail")
        g.email(result, formateur.email, "E-mail")
        g.max_length(result, formateur.specialite, 160, "Spécialité")
        g.max_length(result, formateur.diplome, 160, "Diplôme")
        g.max_length(result, formateur.contrat, 40, "Contrat")
        g.positive(result, formateur.taux_horaire, "Taux horaire", allow_zero=True)
        g.max_length(result, formateur.photo, 510, "Photo (chemin)")
        return result

    @staticmethod
    def validate_programme(programme: Programme) -> ValidationResult:
        result = ValidationResult()
        g = Guard
        g.required_id(result, programme.id_classe, "Classe")
        g.required_code(result, programme.code_matiere, "Matière")
        g.max_length(result, programme.code_matiere, 20, "Matière")
        g.positive(result, programme.coefficient, "Coefficient")
        if programme.vol_horaire is not None:
            result.require(programme.vol_horaire >= 0,
                           "Volume horaire : valeur positive ou nulle attendue.")
        g.positive(result, programme.note_elimin, "Note éliminatoire", allow_zero=True)
        g.max_length(result, programme.observation, 300, "Observation")
        return result


class EvaluationValidator:

    @staticmethod
    def validate_periode(periode: PeriodeEval) -> ValidationResult:
        result = ValidationResult()
        g = Guard
        g.required_id(result, periode.id_annee, "Année scolaire")
        g.max_length(result, periode.code_periode, 20, "Code période")
        g.max_length(result, periode.libelle, 100, "Libellé")
        g.positive(result, periode.ponderation, "Pondération", allow_zero=True)
        g.date_order(result, periode.date_debut, periode.date_fin,
                     "date de début", "date de fin")
        return result

    @staticmethod
    def validate_evaluation(evaluation: Evaluation) -> ValidationResult:
        result = ValidationResult()
        g = Guard
        g.required_id(result, evaluation.id_periode, "Période")
        g.required_id(result, evaluation.id_prog, "Programme (classe × matière)")
        g.max_length(result, evaluation.intitule, 200, "Intitulé")
        g.max_length(result, evaluation.nature, 50, "Nature")
        g.positive(result, evaluation.bareme, "Barème")
        g.positive(result, evaluation.poids, "Poids")
        return result


class GradeValidator:

    @staticmethod
    def validate_note(valeur: Optional[float], absent: bool, bareme: float) -> ValidationResult:
        result = ValidationResult()
        if absent:
            return result
        result.require(valeur is not None,
                       "Note : valeur obligatoire (ou cocher « absent »).")
        if valeur is not None:
            Guard.range(result, valeur, 0, bareme, "Note")
        return result


class ExamValidator:

    @staticmethod
    def validate_session(session: SessionExam) -> ValidationResult:
        result = ValidationResult()
        g = Guard
        g.required_id(result, session.id_annee, "Année scolaire")
        g.required(result, session.libelle, "Libellé")
        g.max_length(result, session.libelle, 120, "Libellé")
        g.max_length(result, session.nature, 50, "Nature")
        g.date_order(result, session.date_debut, session.date_fin,
                     "date de début", "date de fin")
        return result

    @staticmethod
    def validate_epreuve(epreuve: Epreuve) -> ValidationResult:
        result = ValidationResult()
        g = Guard
        g.required_id(result, epreuve.id_session, "Session")
        g.required_id(result, epreuve.id_classe, "Classe")
        g.required_code(result, epreuve.code_matiere, "Matière")
        g.heure_texte(result, epreuve.heure_debut, "Heure de début")
        if epreuve.duree_mn is not None:
            result.require(epreuve.duree_mn > 0,
                           "Durée : valeur strictement positive attendue (minutes).")
        g.positive(result, epreuve.coefficient, "Coefficient")
        g.positive(result, epreuve.bareme, "Barème")
        g.max_length(result, epreuve.surveillant, 160, "Surveillant")
        return result


JOURS_AUTORISES = ("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche")


class PlanningValidator:

    @staticmethod
    def validate_creneau(creneau) -> ValidationResult:
        result = ValidationResult()
        g = Guard
        g.max_length(result, creneau.libelle, 60, "Libellé")
        g.heure_texte(result, creneau.heure_debut, "Heure de début")
        g.heure_texte(result, creneau.heure_fin, "Heure de fin")
        return result

    @staticmethod
    def validate_slot(slot: EmploiDuTemps) -> ValidationResult:
        result = ValidationResult()
        g = Guard
        g.required_id(result, slot.id_prog, "Programme (classe × matière)")
        g.required_id(result, slot.id_creneau, "Créneau")
        g.required(result, slot.jour, "Jour")
        g.in_set(result, slot.jour, "Jour", JOURS_AUTORISES)
        g.max_length(result, slot.jour, 24, "Jour")
        g.date_order(result, slot.date_debut, slot.date_fin, "date de début", "date de fin")
        return result

    @staticmethod
    def validate_seance(seance: Seance) -> ValidationResult:
        result = ValidationResult()
        g = Guard
        g.required_id(result, seance.id_edt, "Créneau d’emploi du temps")
        result.require(seance.date_seance is not None,
                       "Date de séance : valeur obligatoire.")
        g.positive(result, seance.nb_heures, "Nombre d’heures", allow_zero=True)
        g.max_length(result, seance.statut, 40, "Statut")
        return result

    @staticmethod
    def validate_absence(absence: Absence) -> ValidationResult:
        result = ValidationResult()
        g = Guard
        g.required_id(result, absence.id_seance, "Séance")
        g.required_id(result, absence.id_inscription, "Inscription")
        g.positive(result, absence.nb_heures, "Nombre d’heures")
        g.max_length(result, absence.nature, 30, "Nature")
        g.max_length(result, absence.motif, 300, "Motif")
        return result


class PaymentValidator:

    @staticmethod
    def validate_tarif(tarif: Tarif) -> ValidationResult:
        result = ValidationResult()
        g = Guard
        g.required_id(result, tarif.id_classe, "Classe")
        g.required(result, tarif.type_frais, "Type de frais")
        g.max_length(result, tarif.type_frais, 60, "Type de frais")
        g.positive(result, tarif.montant, "Montant")
        if tarif.nb_tranches is not None:
            result.require(1 <= tarif.nb_tranches <= 24,
                           "Nombre de tranches : valeur entre 1 et 24 attendue.")
        g.max_length(result, tarif.observation, 300, "Observation")
        return result

    @staticmethod
    def validate_encaissement(montant: Decimal, mode_paie: Optional[str],
                              reste: Decimal) -> ValidationResult:
        result = ValidationResult()
        result.require(montant > 0, "Montant : valeur strictement positive attendue.")
        Guard.required(result, mode_paie, "Mode de paiement")
        Guard.max_length(result, mode_paie, 50, "Mode de paiement")
        result.require(montant <= reste + Decimal("0.01"),
                       f"Montant : {montant:,.0f} supérieur au reste à payer ({reste:,.0f}).")
        return result

    @staticmethod
    def validate_remise(remise: Optional[Decimal], montant_du: Decimal) -> ValidationResult:
        result = ValidationResult()
        Guard.positive(result, remise, "Remise", allow_zero=True)
        if remise is not None:
            result.require(remise <= montant_du,
                           "Remise : ne peut pas dépasser le montant dû.")
        return result


class PayrollValidator:

    @staticmethod
    def validate_calcul(id_formateur: Optional[int], debut, fin) -> ValidationResult:
        result = ValidationResult()
        Guard.required_id(result, id_formateur, "Formateur")
        result.require(fin >= debut,
                       "Date de fin : doit être postérieure ou égale à la date de début.")
        result.require((fin - debut).days <= 366,
                       "Période : 12 mois maximum par calcul.")
        return result


class ReferentielValidator:

    @staticmethod
    def validate_classe(classe: Classe) -> ValidationResult:
        result = ValidationResult()
        g = Guard
        g.required(result, classe.libelle, "Libellé")
        g.max_length(result, classe.libelle, 120, "Libellé")
        g.required_id(result, classe.id_annee, "Année scolaire")
        g.max_length(result, classe.code_filiere, 20, "Filière")
        g.max_length(result, classe.code_niveau, 20, "Niveau")
        if classe.effectif_max is not None:
            result.require(classe.effectif_max > 0,
                           "Effectif maximum : valeur strictement positive attendue.")
        return result
