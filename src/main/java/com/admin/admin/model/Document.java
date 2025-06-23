package com.admin.admin.model;

import java.util.Date;

public class Document {
    private int idDocument;
    private String type;
    private String cheminFichier;
    private int idEleve;
    private int idProfesseur;
    private int idMateriel;
    private Date dateDepot;
    private int auteur;

    public Document(int idDocument, String type, String cheminFichier, int idEleve, int idProfesseur, int idMateriel, Date dateDepot, int auteur) {
        this.idDocument = idDocument;
        this.type = type;
        this.cheminFichier = cheminFichier;
        this.idEleve = idEleve;
        this.idProfesseur = idProfesseur;
        this.idMateriel = idMateriel;
        this.dateDepot = dateDepot;
        this.auteur = auteur;
    }

    // Getters et Setters
    public int getIdDocument() { return idDocument; }
    public void setIdDocument(int idDocument) { this.idDocument = idDocument; }
    public String getType() { return type; }
    public void setType(String type) { this.type = type; }
    public String getCheminFichier() { return cheminFichier; }
    public void setCheminFichier(String cheminFichier) { this.cheminFichier = cheminFichier; }
    public int getIdEleve() { return idEleve; }
    public void setIdEleve(int idEleve) { this.idEleve = idEleve; }
    public int getIdProfesseur() { return idProfesseur; }
    public void setIdProfesseur(int idProfesseur) { this.idProfesseur = idProfesseur; }
    public int getIdMateriel() { return idMateriel; }
    public void setIdMateriel(int idMateriel) { this.idMateriel = idMateriel; }
    public Date getDateDepot() { return dateDepot; }
    public void setDateDepot(Date dateDepot) { this.dateDepot = dateDepot; }
    public int getAuteur() { return auteur; }
    public void setAuteur(int auteur) { this.auteur = auteur; }
}
