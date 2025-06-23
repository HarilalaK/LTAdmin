package com.admin.admin.model;

import java.sql.Time;

public class EmploiDuTemps {
    private int idCreneau;
    private String jour;
    private Time heureDebut;
    private Time heureFin;
    private int idClasse;
    private int idProfesseur;
    private int idMatiere;
    private int idSalle;
    private String periode;
    private String commentaire;

    public EmploiDuTemps(int idCreneau, String jour, Time heureDebut, Time heureFin, int idClasse, int idProfesseur, int idMatiere, int idSalle, String periode, String commentaire) {
        this.idCreneau = idCreneau;
        this.jour = jour;
        this.heureDebut = heureDebut;
        this.heureFin = heureFin;
        this.idClasse = idClasse;
        this.idProfesseur = idProfesseur;
        this.idMatiere = idMatiere;
        this.idSalle = idSalle;
        this.periode = periode;
        this.commentaire = commentaire;
    }

    // Getters et Setters
    public int getIdCreneau() { return idCreneau; }
    public void setIdCreneau(int idCreneau) { this.idCreneau = idCreneau; }
    public String getJour() { return jour; }
    public void setJour(String jour) { this.jour = jour; }
    public Time getHeureDebut() { return heureDebut; }
    public void setHeureDebut(Time heureDebut) { this.heureDebut = heureDebut; }
    public Time getHeureFin() { return heureFin; }
    public void setHeureFin(Time heureFin) { this.heureFin = heureFin; }
    public int getIdClasse() { return idClasse; }
    public void setIdClasse(int idClasse) { this.idClasse = idClasse; }
    public int getIdProfesseur() { return idProfesseur; }
    public void setIdProfesseur(int idProfesseur) { this.idProfesseur = idProfesseur; }
    public int getIdMatiere() { return idMatiere; }
    public void setIdMatiere(int idMatiere) { this.idMatiere = idMatiere; }
    public int getIdSalle() { return idSalle; }
    public void setIdSalle(int idSalle) { this.idSalle = idSalle; }
    public String getPeriode() { return periode; }
    public void setPeriode(String periode) { this.periode = periode; }
    public String getCommentaire() { return commentaire; }
    public void setCommentaire(String commentaire) { this.commentaire = commentaire; }
}
