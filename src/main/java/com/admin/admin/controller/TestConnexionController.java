package com.admin.admin.controller;

import com.admin.admin.dao.Database;
import javafx.fxml.FXML;
import javafx.scene.control.Label;

import java.sql.Connection;

public class TestConnexionController {

    @FXML
    private Label labelResultat;

    @FXML
    public void testerConnexion() {
        try (Connection conn = Database.connect()) {
            if (conn != null) {
                labelResultat.setText("✅ Connexion réussie !");
            } else {
                labelResultat.setText("❌ Connexion échouée !");
            }
        } catch (Exception e) {
            labelResultat.setText("❌ Erreur : " + e.getMessage());
        }
    }
}
