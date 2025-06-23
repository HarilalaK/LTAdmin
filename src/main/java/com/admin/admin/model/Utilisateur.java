package com.admin.admin.model;

public class Utilisateur {
    private int idUtilisateur;
    private String identifiant;
    private String motDePasse;
    private String email;
    private String role;
    private boolean actif;

    public Utilisateur(int idUtilisateur, String identifiant, String motDePasse, String email, String role, boolean actif) {
        this.idUtilisateur = idUtilisateur;
        this.identifiant = identifiant;
        this.motDePasse = motDePasse;
        this.email = email;
        this.role = role;
        this.actif = actif;
    }

    // Getters et Setters
    public int getIdUtilisateur() { return idUtilisateur; }
    public void setIdUtilisateur(int idUtilisateur) { this.idUtilisateur = idUtilisateur; }
    public String getIdentifiant() { return identifiant; }
    public void setIdentifiant(String identifiant) { this.identifiant = identifiant; }
    public String getMotDePasse() { return motDePasse; }
    public void setMotDePasse(String motDePasse) { this.motDePasse = motDePasse; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }
    public boolean isActif() { return actif; }
    public void setActif(boolean actif) { this.actif = actif; }
}
