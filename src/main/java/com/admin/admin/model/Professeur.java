package com.admin.admin.model;

import java.util.Date;

public class Professeur {
    private int idProfesseur;
    private int idUtilisateur;
    private String nom;
    private String prenom;
    private Date dateNaissance;
    private String specialisation;
    private String statut;
    private String telephone;
    private String email;
    private String photo;

    public Professeur(int idProfesseur, int idUtilisateur, String nom, String prenom, Date dateNaissance,
                      String specialisation, String statut, String telephone, String email, String photo) {
        this.idProfesseur = idProfesseur;
        this.idUtilisateur = idUtilisateur;
        this.nom = nom;
        this.prenom = prenom;
        this.dateNaissance = dateNaissance;
        this.specialisation = specialisation;
        this.statut = statut;
        this.telephone = telephone;
        this.email = email;
        this.photo = photo;
    }

    // Getters et Setters
    public int getIdProfesseur() { return idProfesseur; }
    public void setIdProfesseur(int idProfesseur) { this.idProfesseur = idProfesseur; }
    public int getIdUtilisateur() { return idUtilisateur; }
    public void setIdUtilisateur(int idUtilisateur) { this.idUtilisateur = idUtilisateur; }
    public String getNom() { return nom; }
    public void setNom(String nom) { this.nom = nom; }
    public String getPrenom() { return prenom; }
    public void setPrenom(String prenom) { this.prenom = prenom; }
    public Date getDateNaissance() { return dateNaissance; }
    public void setDateNaissance(Date dateNaissance) { this.dateNaissance = dateNaissance; }
    public String getSpecialisation() { return specialisation; }
    public void setSpecialisation(String specialisation) { this.specialisation = specialisation; }
    public String getStatut() { return statut; }
    public void setStatut(String statut) { this.statut = statut; }
    public String getTelephone() { return telephone; }
    public void setTelephone(String telephone) { this.telephone = telephone; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public String getPhoto() { return photo; }
    public void setPhoto(String photo) { this.photo = photo; }
}
