package com.admin.admin.model;

import java.util.Date;

public class Message {
    private int idMessage;
    private int expediteur;
    private int destinataire;
    private String sujet;
    private String contenu;
    private Date dateEnvoi;
    private boolean lu;

    public Message(int idMessage, int expediteur, int destinataire, String sujet, String contenu, Date dateEnvoi, boolean lu) {
        this.idMessage = idMessage;
        this.expediteur = expediteur;
        this.destinataire = destinataire;
        this.sujet = sujet;
        this.contenu = contenu;
        this.dateEnvoi = dateEnvoi;
        this.lu = lu;
    }

    // Getters et Setters
    public int getIdMessage() { return idMessage; }
    public void setIdMessage(int idMessage) { this.idMessage = idMessage; }
    public int getExpediteur() { return expediteur; }
    public void setExpediteur(int expediteur) { this.expediteur = expediteur; }
    public int getDestinataire() { return destinataire; }
    public void setDestinataire(int destinataire) { this.destinataire = destinataire; }
    public String getSujet() { return sujet; }
    public void setSujet(String sujet) { this.sujet = sujet; }
    public String getContenu() { return contenu; }
    public void setContenu(String contenu) { this.contenu = contenu; }
    public Date getDateEnvoi() { return dateEnvoi; }
    public void setDateEnvoi(Date dateEnvoi) { this.dateEnvoi = dateEnvoi; }
    public boolean isLu() { return lu; }
    public void setLu(boolean lu) { this.lu = lu; }
}
