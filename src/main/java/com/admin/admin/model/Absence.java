package com.admin.admin.model;

import java.util.Date;

public class Absence {
    private int idAbsence;
    private int idEleve;
    private Date dateAbsence;
    private int idCreneau;
    private boolean justifiee;
    private String motif;
    private String justificatif;

    public Absence(int idAbsence, int idEleve, Date dateAbsence, int idCreneau, boolean justifiee, String motif, String justificatif) {
        this.idAbsence = idAbsence;
        this.idEleve = idEleve;
        this.dateAbsence = dateAbsence;
        this.idCreneau = idCreneau;
        this.justifiee = justifiee;
        this.motif = motif;
        this.justificatif = justificatif;
    }

    // Getters et Setters
    public int getIdAbsence() { return idAbsence; }
    public void setIdAbsence(int idAbsence) { this.idAbsence = idAbsence; }
    public int getIdEleve() { return idEleve; }
    public void setIdEleve(int idEleve) { this.idEleve = idEleve; }
    public Date getDateAbsence() { return dateAbsence; }
    public void setDateAbsence(Date dateAbsence) { this.dateAbsence = dateAbsence; }
    public int getIdCreneau() { return idCreneau; }
    public void setIdCreneau(int idCreneau) { this.idCreneau = idCreneau; }
    public boolean isJustifiee() { return justifiee; }
    public void setJustifiee(boolean justifiee) { this.justifiee = justifiee; }
    public String getMotif() { return motif; }
    public void setMotif(String motif) { this.motif = motif; }
    public String getJustificatif() { return justificatif; }
    public void setJustificatif(String justificatif) { this.justificatif = justificatif; }
}
