@echo off

echo. > main.py
echo. > requirements.txt

:: Dossier Base de données
mkdir database
cd database
echo. > __init__.py
echo. > db_manager.py
echo. > init_db.py
cd ..

:: Dossier Modèles (tables SQLite)
mkdir models
cd models
echo. > __init__.py
echo. > eleve.py
echo. > prof.py
echo. > classe.py
echo. > salle.py
echo. > materiel.py
echo. > note.py
echo. > paiement.py
echo. > utilisateur.py
cd ..

:: Dossier Interface (UI)
mkdir ui
cd ui
echo. > __init__.py
echo. > main_app.py

:: Composants réutilisables UI
mkdir components
cd components
echo. > __init__.py
echo. > sidebar.py
echo. > navbar.py
cd ..

:: Pages (fenêtres Tkinter)
mkdir pages
cd pages
echo. > __init__.py
echo. > home_page.py
echo. > eleve_page.py
echo. > prof_page.py
echo. > classe_page.py
echo. > salle_page.py
echo. > materiel_page.py
echo. > note_page.py
echo. > paiement_page.py
echo. > rapport_page.py
cd ..
cd ..

:: Dossier Utilitaires
mkdir utils
cd utils
echo. > __init__.py
echo. > pdf_generator.py
echo. > helpers.py
cd ..

echo ✅ Structure du projet app_etablissement créée avec succès !
pause
