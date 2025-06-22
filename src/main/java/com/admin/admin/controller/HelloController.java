package com.admin.admin.controller;

import javafx.fxml.FXML;
import javafx.scene.control.Label;

public class HelloController {
    @FXML
    private Label welcomeText;
    private int value = 1; // valeur initiale

    @FXML
    protected void onHelloButtonClick() {
        value *= 2;
        welcomeText.setText("Valeur : " + value);
    }
}