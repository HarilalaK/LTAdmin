package com.admin.admin.dao;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.net.URL;
import java.nio.file.Paths;
import java.nio.file.Path;

public class Database {
    public static Connection connect() {
        try {
            // Récupère la ressource depuis le classpath
            URL resource = Database.class.getResource("/com/admin/admin/DB/lta_scolaire.db");

            if (resource == null) {
                System.err.println("Base de données introuvable !");
                return null;
            }

            Path path = Paths.get(resource.toURI());
            String url = "jdbc:sqlite:" + path.toString();

            Connection conn = DriverManager.getConnection(url);
            System.out.println("Connexion à SQLite réussie !");
            return conn;
        } catch (Exception e) {
            System.err.println("Erreur de connexion : " + e.getMessage());
            return null;
        }
    }
}
