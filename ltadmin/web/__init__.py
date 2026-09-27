"""Couche web : serveur HTTP local, API JSON et interface HTML/JS.

L'interface (``static/``) est une application web classique ; elle est
affichée dans une fenêtre native par pywebview (``main.py``) ou dans un
navigateur (``main.py --serve``). Toute la logique métier reste dans
:mod:`ltadmin.services` : l'API ne fait que traduire HTTP ⇄ services.
"""
