package com.admin.admin.model;

public class Salle {
    private int idSalle;
    private String nomSalle;
    private String typeSalle;
    private int capacite;
    private String equipements;
    private String batiment;

    public Salle(int idSalle, String nomSalle, String typeSalle, int capacite, String equipements, String batiment) {
        this.idSalle = idSalle;
        this.nomSalle = nomSalle;
        this.typeSalle = typeSalle;
        this.capacite = capacite;
        this.equipements = equipements;
        this.batiment = batiment;
    }

    // Getters et Setters
    public int getIdSalle() { return idSalle; }
    public void setIdSalle(int idSalle) { this.idSalle = idSalle; }
    public String getNomSalle() { return nomSalle; }
    public void setNomSalle(String nomSalle) { this.nomSalle = nomSalle; }
    public String getTypeSalle() { return typeSalle; }
    public void setTypeSalle(String typeSalle) { this.typeSalle = typeSalle; }
    public int getCapacite() { return capacite; }
    public void setCapacite(int capacite) { this.capacite = capacite; }
    public String getEquipements() { return equipements; }
    public void setEquipements(String equipements) { this.equipements = equipements; }
    public String getBatiment() { return batiment; }
    public void setBatiment(String batiment) { this.batiment = batiment; }
}
