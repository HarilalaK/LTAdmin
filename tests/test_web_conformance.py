"""Conformité statique de l'application web (sans navigateur ni serveur).

Vérifie par analyse de code que :
- chaque nom utilisé comme base d'attribut dans le code Python livré est bien
  lié dans son scope (un import manquant = écran qui plante à l'usage) ;
- chaque module du menu (``App.MODULES``) a une vue enregistrée, chaque vue
  est chargée par ``index.html`` et correspond à un module d'habilitation ;
- chaque URL ``/api/...`` écrite dans le JavaScript correspond à une route
  réellement enregistrée côté serveur (et réciproquement pour les modules) ;
- les routes protégées référencent des modules d'habilitation connus ;
- les fichiers JavaScript sont syntaxiquement valides (si ``node`` est présent).
"""

from __future__ import annotations

import ast
import builtins
import glob
import os
import re
import shutil
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ltadmin.services.auth import habilitations  # noqa: E402
from ltadmin.services.auth.habilitations import Modules  # noqa: E402
from ltadmin.web.routing import PUBLIC, Router  # noqa: E402
from ltadmin.web import api_admin, api_finance, api_pedagogie, api_scolarite  # noqa: E402

STATIC_DIR = os.path.join(ROOT, "ltadmin", "web", "static")
VIEW_FILES = sorted(glob.glob(os.path.join(STATIC_DIR, "views", "*.js")))
JS_FILES = sorted(glob.glob(os.path.join(STATIC_DIR, "*.js"))) + VIEW_FILES
SOURCE_FILES = sorted(
    glob.glob(os.path.join(ROOT, "ltadmin", "**", "*.py"), recursive=True)
    + glob.glob(os.path.join(ROOT, "tests", "*.py"))
    + glob.glob(os.path.join(ROOT, "tools", "*.py"))
    + [os.path.join(ROOT, "main.py")])

BUILTINS = frozenset(dir(builtins))
_FUNCS = (ast.FunctionDef, ast.AsyncFunctionDef)


# ---------------------------------------------------------------------------
# Analyse AST : noms non liés
# ---------------------------------------------------------------------------


def _add_args(names: set, args: ast.arguments) -> None:
    for arg in args.posonlyargs + args.args + args.kwonlyargs:
        names.add(arg.arg)
    for extra in (args.vararg, args.kwarg):
        if extra is not None:
            names.add(extra.arg)


def _own_nodes(nodes) -> list:
    """Noeuds du scope courant (sans descendre dans les fonctions/classes)."""
    result, stack = [], list(nodes)
    while stack:
        node = stack.pop()
        result.append(node)
        if isinstance(node, _FUNCS):
            stack.extend(node.decorator_list)
            stack.extend(d for d in node.args.defaults if d is not None)
            stack.extend(d for d in node.args.kw_defaults if d is not None)
            continue
        if isinstance(node, ast.ClassDef):
            stack.extend(node.decorator_list)
            stack.extend(node.bases)
            stack.extend(key.value for key in node.keywords)
            continue
        if isinstance(node, ast.Lambda):
            stack.extend(d for d in node.args.defaults if d is not None)
            stack.extend(d for d in node.args.kw_defaults if d is not None)
            continue
        stack.extend(ast.iter_child_nodes(node))
    return result


def _bindings(nodes) -> set:
    names = set()
    for node in _own_nodes(nodes):
        if isinstance(node, _FUNCS):
            names.add(node.name)
            _add_args(names, node.args)
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Lambda):
            _add_args(names, node.args)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            names.add(node.id)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            names.update(node.names)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
    return names


def undefined_attribute_bases(source: str, label: str = "<source>") -> list:
    """Noms utilisés comme base d'attribut (``x.y``) mais liés nulle part."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names):
            return []
    problems = set()

    def visit(nodes, visible) -> None:
        scope = visible | _bindings(nodes)
        for node in _own_nodes(nodes):
            if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                    and node.value.id not in scope):
                problems.add(f"{label}:{node.lineno} nom non défini '{node.value.id}'")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                visit(node.body, scope)
            elif isinstance(node, ast.Lambda):
                inner = set(scope)
                _add_args(inner, node.args)
                visit([node.body], inner)

    visit(tree.body, BUILTINS)
    return sorted(problems)


# ---------------------------------------------------------------------------
# Aides front / back
# ---------------------------------------------------------------------------


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _router() -> Router:
    router = Router()
    for module in (api_scolarite, api_pedagogie, api_finance, api_admin):
        module.register(router)
    return router


def _menu_keys() -> dict:
    """{clé de vue: libellé de module} déclaré dans ``App.MODULES`` (app.js)."""
    source = _read(os.path.join(STATIC_DIR, "app.js"))
    block = source[source.index("MODULES: ["):]
    block = block[:block.index("],")]
    pairs = re.findall(r'module:\s*"([^"]+)",\s*key:\s*"([^"]+)"', block)
    return {key: module for module, key in pairs}


def _api_literals() -> list:
    """(fichier, chemin normalisé) pour chaque URL /api/... écrite dans le JS.

    ``${expr}`` (gabarits) devient un segment paramétré ; une chaîne finissant
    par ``/`` (concaténation ``"/api/x/" + id``) est traitée comme un préfixe.
    """
    found = []
    pattern = re.compile(r'["\'`](/api/[^"\'`\s?]*)')
    for path in JS_FILES:
        for match in pattern.finditer(_read(path)):
            literal = match.group(1)
            literal = re.sub(r"\$\{[^}]*\}", "{p}", literal)
            if literal == "/api/auth/":  # test « startsWith » de core.js, pas une URL
                continue
            found.append((os.path.relpath(path, ROOT), literal))
    return found


def _templates_normalized(router: Router) -> list:
    return [re.sub(r"\{\w+\}", "{p}", route.template) for route in router.routes]


def _literal_matches(literal: str, templates: list) -> bool:
    if literal.endswith("/"):  # préfixe : "/api/x/" + id
        prefix = literal
        return any(t.startswith(prefix) and t[len(prefix):].startswith("{p}") for t in templates)
    return literal in templates


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPythonSources(unittest.TestCase):

    def test_no_undefined_attribute_base(self):
        problems = []
        for path in SOURCE_FILES:
            problems.extend(undefined_attribute_bases(_read(path), os.path.relpath(path, ROOT)))
        self.assertEqual(problems, [], "\n".join(problems))

    def test_all_sources_compile(self):
        for path in SOURCE_FILES:
            compile(_read(path), path, "exec")


class TestRoutes(unittest.TestCase):

    def setUp(self):
        self.router = _router()

    def test_routes_reference_known_modules(self):
        known = set(habilitations.MENU_ORDER)
        for route in self.router.routes:
            if route.module in (None, PUBLIC):
                continue
            self.assertIn(route.module, known, f"{route.method} {route.template}")

    def test_no_duplicate_route(self):
        seen = set()
        for route in self.router.routes:
            key = (route.method, re.sub(r"\{\w+\}", "{p}", route.template))
            self.assertNotIn(key, seen, f"route en double : {key}")
            seen.add(key)

    def test_public_routes_are_limited(self):
        public = sorted(r.template for r in self.router.routes if r.module == PUBLIC)
        self.assertEqual(public, ["/api/auth/connexion", "/api/auth/deconnexion",
                                  "/api/auth/session", "/api/sante"])

    def test_every_menu_module_has_an_api_route(self):
        modules_with_routes = {r.module for r in self.router.routes if r.module}
        # Ces modules s'appuient sur des routes partagées (module=None) ou d'autres modules.
        exempt = {Modules.TABLEAU_DE_BORD}
        for module in habilitations.MENU_ORDER:
            if module in exempt:
                continue
            self.assertIn(module, modules_with_routes, module)


class TestFrontend(unittest.TestCase):

    def test_menu_keys_views_and_scripts(self):
        keys = _menu_keys()
        self.assertEqual(len(keys), 17)
        registered = {}
        for path in VIEW_FILES:
            for key in re.findall(r'App\.register\("([^"]+)"', _read(path)):
                registered[key] = os.path.basename(path)
        for key, module in keys.items():
            self.assertIn(key, registered, f"aucune vue enregistrée pour « {key} »")
            self.assertIn(module, habilitations.MENU_ORDER, module)
        self.assertEqual(set(registered) - set(keys), set(), "vue enregistrée hors menu")
        index = _read(os.path.join(STATIC_DIR, "index.html"))
        scripts = re.findall(r'<script src="([^"]+)"', index)
        for path in JS_FILES:
            rel = os.path.relpath(path, STATIC_DIR).replace(os.sep, "/")
            self.assertIn(rel, scripts, f"{rel} non chargé par index.html")
        for script in scripts:
            self.assertTrue(os.path.isfile(os.path.join(STATIC_DIR, script)), script)
        self.assertIn('<link rel="stylesheet" href="styles.css">', index)

    def test_menu_matches_habilitation_order(self):
        keys = _menu_keys()
        self.assertEqual(list(keys.values()), list(habilitations.MENU_ORDER))

    def test_every_js_api_url_matches_a_route(self):
        templates = _templates_normalized(_router())
        missing = [f"{f}: {lit}" for f, lit in _api_literals() if not _literal_matches(lit, templates)]
        self.assertEqual(missing, [], "\n".join(missing))

    def test_every_route_is_used_by_the_frontend_or_documented(self):
        """Toute route non appelée par l'interface doit être listée ici (API utile
        aux tests/outils), pour éviter les routes mortes non assumées."""
        literals = {lit for _, lit in _api_literals()}
        prefixes = {lit for lit in literals if lit.endswith("/")}
        exact = literals - prefixes
        tolerated = {"/api/sante", "/api/notes/{p}", "/api/notes-examen/{p}", "/api/creneaux/{p}",
                     "/api/paie/heures", "/api/etudiants/{p}/inscriptions",
                     "/api/inscriptions/{p}", "/api/seances/{p}", "/api/tarifs/{p}",
                     "/api/absences/{p}", "/api/evaluations/{p}", "/api/epreuves/{p}",
                     "/api/sessions/{p}", "/api/periodes/{p}", "/api/programmes/{p}",
                     "/api/formateurs/{p}", "/api/etudiants/{p}", "/api/edt/{p}",
                     "/api/bulletins/{p}", "/api/rapports/{p}", "/api/rapports/{p}/csv",
                     "/api/paiements/{p}", "/api/tables/{p}", "/api/utilisateurs/{p}",
                     "/api/admin/parametres/{p}", "/api/ref/classes/{p}", "/api/ref/filieres/{p}",
                     "/api/ref/niveaux/{p}", "/api/ref/matieres/{p}", "/api/ref/modules/{p}",
                     "/api/ref/salles/{p}", "/api/ref/annees/{p}", "/api/admin/annees/{p}",
                     "/api/paie/{p}", "/api/admin/journal", "/api/echeances/{p}",
                     "/api/mentions"}
        unused = []
        for template in _templates_normalized(_router()):
            if template in exact or template in tolerated:
                continue
            if any(template.startswith(prefix) and template[len(prefix):].startswith("{p}")
                   for prefix in prefixes):
                continue
            unused.append(template)
        self.assertEqual(sorted(set(unused)), [], "routes sans appel côté interface : "
                         + ", ".join(sorted(set(unused))))

    @unittest.skipUnless(shutil.which("node"), "node absent : syntaxe JS non vérifiée")
    def test_javascript_syntax(self):
        for path in JS_FILES:
            proc = subprocess.run(["node", "--check", path], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
