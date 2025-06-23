package com.admin.admin.model;

import java.util.Date;

public class AnneeScolaire {
    private int idAnnee;
    private String libelleAnnee;
    private Date dateDebut;
    private Date dateFin;
    private boolean anneeActive;

    public AnneeScolaire(int idAnnee, String libelleAnnee, Date dateDebut, Date dateFin, boolean anneeActive) {
        this.idAnnee = idAnnee;
        this.libelleAnnee = libelleAnnee;
        this.dateDebut = dateDebut;
        this.dateFin = dateFin;
        this.anneeActive = anneeActive;
    }

    // Getters et Setters
    public int getIdAnnee() { return idAnnee; }
    public void setIdAnnee(int idAnnee) { this.idAnnee = idAnnee; }
    public String getLibelleAnnee() { return libelleAnnee; }
    public void setLibelleAnnee(String libelleAnnee) { this.libelleAnnee = libelleAnnee; }
    public Date getDateDebut() { return dateDebut; }
    public void setDateDebut(Date dateDebut) { this.dateDebut = dateDebut; }
    public Date getDateFin() { return dateFin; }
    public void setDateFin(Date dateFin) { this.dateFin = dateFin; }
    public boolean isAnneeActive() { return anneeActive; }
    public void setAnneeActive(boolean anneeActive) { this.anneeActive = anneeActive; }
}
