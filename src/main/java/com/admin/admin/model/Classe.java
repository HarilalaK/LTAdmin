package com.admin.admin.model;

public class Classe {
    private int idClasse;
    private String nomClasse;
    private int idFiliere;
    private int idNiveau;
    private int idAnnee;
    private int capaciteMax;

    public Classe(int idClasse, String nomClasse, int idFiliere, int idNiveau, int idAnnee, int capaciteMax) {
        this.idClasse = idClasse;
        this.nomClasse = nomClasse;
        this.idFiliere = idFiliere;
        this.idNiveau = idNiveau;
        this.idAnnee = idAnnee;
        this.capaciteMax = capaciteMax;
    }

    // Getters et Setters
    public int getIdClasse() { return idClasse; }
    public void setIdClasse(int idClasse) { this.idClasse = idClasse; }
    public String getNomClasse() { return nomClasse; }
    public void setNomClasse(String nomClasse) { this.nomClasse = nomClasse; }
    public int getIdFiliere() { return idFiliere; }
    public void setIdFiliere(int idFiliere) { this.idFiliere = idFiliere; }
    public int getIdNiveau() { return idNiveau; }
    public void setIdNiveau(int idNiveau) { this.idNiveau = idNiveau; }
    public int getIdAnnee() { return idAnnee; }
    public void setIdAnnee(int idAnnee) { this.idAnnee = idAnnee; }
    public int getCapaciteMax() { return capaciteMax; }
    public void setCapaciteMax(int capaciteMax) { this.capaciteMax = capaciteMax; }
}
