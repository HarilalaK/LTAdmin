package com.admin.admin.model;

public class Niveau {
    private int idNiveau;
    private String nomNiveau;
    private int ordreAffichage;

    public Niveau(int idNiveau, String nomNiveau, int ordreAffichage) {
        this.idNiveau = idNiveau;
        this.nomNiveau = nomNiveau;
        this.ordreAffichage = ordreAffichage;
    }

    // Getters et Setters
    public int getIdNiveau() { return idNiveau; }
    public void setIdNiveau(int idNiveau) { this.idNiveau = idNiveau; }
    public String getNomNiveau() { return nomNiveau; }
    public void setNomNiveau(String nomNiveau) { this.nomNiveau = nomNiveau; }
    public int getOrdreAffichage() { return ordreAffichage; }
    public void setOrdreAffichage(int ordreAffichage) { this.ordreAffichage = ordreAffichage; }
}
