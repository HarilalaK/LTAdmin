package com.admin.admin.model;

import java.util.Date;

public class Materiel {
    private int idMateriel;
    private String nom;
    private String type;
    private int idSalle;
    private String numeroSerie;
    private Date dateAcquisition;
    private String etat;
    private Date dateDerniereMaintenance;

    public Materiel(int idMateriel, String nom, String type, int idSalle, String numeroSerie, Date dateAcquisition, String etat, Date dateDerniereMaintenance) {
        this.idMateriel = idMateriel;
        this.nom = nom;
        this.type = type;
        this.idSalle = idSalle;
        this.numeroSerie = numeroSerie;
        this.dateAcquisition = dateAcquisition;
        this.etat = etat;
        this.dateDerniereMaintenance = dateDerniereMaintenance;
    }

    // Getters et Setters
    public int getIdMateriel() { return idMateriel; }
    public void setIdMateriel(int idMateriel) { this.idMateriel = idMateriel; }
    public String getNom() { return nom; }
    public void setNom(String nom) { this.nom = nom; }
    public String getType() { return type; }
    public void setType(String type) { this.type = type; }
    public int getIdSalle() { return idSalle; }
    public void setIdSalle(int idSalle) { this.idSalle = idSalle; }
    public String getNumeroSerie() { return numeroSerie; }
    public void setNumeroSerie(String numeroSerie) { this.numeroSerie = numeroSerie; }
    public Date getDateAcquisition() { return dateAcquisition; }
    public void setDateAcquisition(Date dateAcquisition) { this.dateAcquisition = dateAcquisition; }
    public String getEtat() { return etat; }
    public void setEtat(String etat) { this.etat = etat; }
    public Date getDateDerniereMaintenance() { return dateDerniereMaintenance; }
    public void setDateDerniereMaintenance(Date dateDerniereMaintenance) { this.dateDerniereMaintenance = dateDerniereMaintenance; }
}
