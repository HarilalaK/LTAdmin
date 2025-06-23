package com.admin.admin.model;

public class Filiere {
    private int idFiliere;
    private String nomFiliere;
    private String typeFormation;
    private String sousSpecialite;
    private String description;
    private String couleurTheme;

    public Filiere(int idFiliere, String nomFiliere, String typeFormation, String sousSpecialite, String description, String couleurTheme) {
        this.idFiliere = idFiliere;
        this.nomFiliere = nomFiliere;
        this.typeFormation = typeFormation;
        this.sousSpecialite = sousSpecialite;
        this.description = description;
        this.couleurTheme = couleurTheme;
    }

    // Getters et Setters
    public int getIdFiliere() { return idFiliere; }
    public void setIdFiliere(int idFiliere) { this.idFiliere = idFiliere; }
    public String getNomFiliere() { return nomFiliere; }
    public void setNomFiliere(String nomFiliere) { this.nomFiliere = nomFiliere; }
    public String getTypeFormation() { return typeFormation; }
    public void setTypeFormation(String typeFormation) { this.typeFormation = typeFormation; }
    public String getSousSpecialite() { return sousSpecialite; }
    public void setSousSpecialite(String sousSpecialite) { this.sousSpecialite = sousSpecialite; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    public String getCouleurTheme() { return couleurTheme; }
    public void setCouleurTheme(String couleurTheme) { this.couleurTheme = couleurTheme; }
}
