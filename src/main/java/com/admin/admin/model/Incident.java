package com.admin.admin.model;

import java.util.Date;

public class Incident {
    private int idIncident;
    private int idMateriel;
    private int idRapporteur;
    private Date dateIncident;
    private String description;
    private String gravite;
    private String statut;
    private String solution;

    public Incident(int idIncident, int idMateriel, int idRapporteur, Date dateIncident, String description, String gravite, String statut, String solution) {
        this.idIncident = idIncident;
        this.idMateriel = idMateriel;
        this.idRapporteur = idRapporteur;
        this.dateIncident = dateIncident;
        this.description = description;
        this.gravite = gravite;
        this.statut = statut;
        this.solution = solution;
    }

    // Getters et Setters
    public int getIdIncident() { return idIncident; }
    public void setIdIncident(int idIncident) { this.idIncident = idIncident; }
    public int getIdMateriel() { return idMateriel; }
    public void setIdMateriel(int idMateriel) { this.idMateriel = idMateriel; }
    public int getIdRapporteur() { return idRapporteur; }
    public void setIdRapporteur(int idRapporteur) { this.idRapporteur = idRapporteur; }
    public Date getDateIncident() { return dateIncident; }
    public void setDateIncident(Date dateIncident) { this.dateIncident = dateIncident; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    public String getGravite() { return gravite; }
    public void setGravite(String gravite) { this.gravite = gravite; }
    public String getStatut() { return statut; }
    public void setStatut(String statut) { this.statut = statut; }
    public String getSolution() { return solution; }
    public void setSolution(String solution) { this.solution = solution; }
}
