package com.admin.admin.model;

import java.util.Date;

public class Eleve {
    private int idEleve;
    private int idUtilisateur;
    private int idClasse;
    private String nom;
    private String prenom;
    private Date dateNaissance;
    private String typeFormation;
    private String adresse;
    private String telephone;
    private String email;
    private String photo;

    public Eleve(int idEleve, int idUtilisateur, int idClasse, String nom, String prenom, Date dateNaissance,
                 String typeFormation, String adresse, String telephone, String email, String photo) {
        this.idEleve = idEleve;
        this.idUtilisateur = idUtilisateur;
        this.idClasse = idClasse;
        this.nom = nom;
        this.prenom = prenom;
        this.dateNaissance = dateNaissance;
        this.typeFormation = typeFormation;
        this.adresse = adresse;
        this.telephone = telephone;
        this.email = email;
        this.photo = photo;
    }

    // Getters et Setters
    public int getIdEleve() { return idEleve; }
    public void setIdEleve(int idEleve) { this.idEleve = idEleve; }
    public int getIdUtilisateur() { return idUtilisateur; }
    public void setIdUtilisateur(int idUtilisateur) { this.idUtilisateur = idUtilisateur; }
    public int getIdClasse() { return idClasse; }
    public void setIdClasse(int idClasse) { this.idClasse = idClasse; }
    public String getNom() { return nom; }
    public void setNom(String nom) { this.nom = nom; }
    public String getPrenom() { return prenom; }
    public void setPrenom(String prenom) { this.prenom = prenom; }
    public Date getDateNaissance() { return dateNaissance; }
    public void setDateNaissance(Date dateNaissance) { this.dateNaissance = dateNaissance; }
    public String getTypeFormation() { return typeFormation; }
    public void setTypeFormation(String typeFormation) { this.typeFormation = typeFormation; }
    public String getAdresse() { return adresse; }
    public void setAdresse(String adresse) { this.adresse = adresse; }
    public String getTelephone() { return telephone; }
    public void setTelephone(String telephone) { this.telephone = telephone; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public String getPhoto() { return photo; }
    public void setPhoto(String photo) { this.photo = photo; }
}
