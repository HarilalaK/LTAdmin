package com.admin.admin.model;

import java.util.Date;

public class Note {
    private int idNote;
    private int idEleve;
    private int idMatiere;
    private double valeur;
    private double coefficient;
    private String typeNote;
    private Date dateNote;
    private String commentaire;

    public Note(int idNote, int idEleve, int idMatiere, double valeur, double coefficient, String typeNote, Date dateNote, String commentaire) {
        this.idNote = idNote;
        this.idEleve = idEleve;
        this.idMatiere = idMatiere;
        this.valeur = valeur;
        this.coefficient = coefficient;
        this.typeNote = typeNote;
        this.dateNote = dateNote;
        this.commentaire = commentaire;
    }

    // Getters et Setters
    public int getIdNote() { return idNote; }
    public void setIdNote(int idNote) { this.idNote = idNote; }
    public int getIdEleve() { return idEleve; }
    public void setIdEleve(int idEleve) { this.idEleve = idEleve; }
    public int getIdMatiere() { return idMatiere; }
    public void setIdMatiere(int idMatiere) { this.idMatiere = idMatiere; }
    public double getValeur() { return valeur; }
    public void setValeur(double valeur) { this.valeur = valeur; }
    public double getCoefficient() { return coefficient; }
    public void setCoefficient(double coefficient) { this.coefficient = coefficient; }
    public String getTypeNote() { return typeNote; }
    public void setTypeNote(String typeNote) { this.typeNote = typeNote; }
    public Date getDateNote() { return dateNote; }
    public void setDateNote(Date dateNote) { this.dateNote = dateNote; }
    public String getCommentaire() { return commentaire; }
    public void setCommentaire(String commentaire) { this.commentaire = commentaire; }
}
