package com.admin.admin.model;

public class Matiere {
    private int idMatiere;
    private String nomMatiere;
    private int idFiliere;
    private double coefficient;
    private String couleurEdt;
    private boolean estOptionnelle;
    private String description;

    public Matiere(int idMatiere, String nomMatiere, int idFiliere, double coefficient, String couleurEdt, boolean estOptionnelle, String description) {
        this.idMatiere = idMatiere;
        this.nomMatiere = nomMatiere;
        this.idFiliere = idFiliere;
        this.coefficient = coefficient;
        this.couleurEdt = couleurEdt;
        this.estOptionnelle = estOptionnelle;
        this.description = description;
    }

    // Getters et Setters
    public int getIdMatiere() { return idMatiere; }
    public void setIdMatiere(int idMatiere) { this.idMatiere = idMatiere; }
    public String getNomMatiere() { return nomMatiere; }
    public void setNomMatiere(String nomMatiere) { this.nomMatiere = nomMatiere; }
    public int getIdFiliere() { return idFiliere; }
    public void setIdFiliere(int idFiliere) { this.idFiliere = idFiliere; }
    public double getCoefficient() { return coefficient; }
    public void setCoefficient(double coefficient) { this.coefficient = coefficient; }
    public String getCouleurEdt() { return couleurEdt; }
    public void setCouleurEdt(String couleurEdt) { this.couleurEdt = couleurEdt; }
    public boolean isEstOptionnelle() { return estOptionnelle; }
    public void setEstOptionnelle(boolean estOptionnelle) { this.estOptionnelle = estOptionnelle; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
}
