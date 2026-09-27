"""LTAdmin — gestion scolaire de l'institut LTA (BTS Hôtellerie & Tourisme).

Application « web sur desktop » : interface HTML/JS servie par un serveur
local Python et affichée dans une fenêtre native (pywebview), base SQLite
``LTA_ADM.sqlite3``. Architecture en couches strictement descendantes :
web (API) → services → repositories → data → SQLite.
"""

__version__ = "2.0.0"
