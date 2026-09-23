"""Conformance statique de la couche UI (sans tkinter).

Vérifie par analyse AST que :
- chaque entrée du menu (MENU_ORDER) a une vue enregistrée dans main.py ;
- les vues enregistrées existent et acceptent (parent, services, session) ;
- les imports ltadmin.ui.* des fichiers UI résolvent vers des noms réels ;
- les méthodes appelées sur les widgets (DataTable, Toolbar, FormField,
  EntityDialog) existent réellement (ou sont des méthodes tk héritées) ;
- la session n'expose que login/display_name/role dans l'UI ;
- l'éditeur générique couvre bien tous les types de colonnes ;
- chaque nom utilisé comme base d'attribut (``tk.BOTH``, ``Result.fail``) est
  bien lié dans le scope courant (import manquant = écran qui plante).
"""

from __future__ import annotations

import ast
import builtins
import glob
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

UI_FILES = sorted(
    glob.glob(os.path.join(ROOT, "ltadmin", "ui", "**", "*.py"), recursive=True))
ALL_FILES = UI_FILES + [os.path.join(ROOT, "main.py")]

# Tout le code livré : les noms indéfinis ne se limitent pas à l'UI.
SOURCE_FILES = sorted(
    glob.glob(os.path.join(ROOT, "ltadmin", "**", "*.py"), recursive=True)
    + glob.glob(os.path.join(ROOT, "tests", "**", "*.py"), recursive=True)
    + [os.path.join(ROOT, "main.py")])

BUILTINS = frozenset(dir(builtins))
_FUNCS = (ast.FunctionDef, ast.AsyncFunctionDef)

WIDGET_CLASSES = {"DataTable", "Toolbar", "FormField", "EntityDialog"}

# Méthodes héritées de tkinter (Frame/Toplevel/Widget/Misc) autorisées.
TK_ALLOWLIST = {
    "pack", "grid", "place", "pack_forget", "grid_forget", "place_forget",
    "destroy", "bind", "unbind", "bind_all", "configure", "config", "cget",
    "keys", "update", "update_idletasks", "after", "after_cancel", "after_idle",
    "focus_set", "focus_force", "focus_get", "lift", "lower", "tkraise",
    "wait_window", "wait_variable", "wait_visibility", "bell",
    "clipboard_append", "clipboard_clear", "clipboard_get",
    "event_generate", "event_add", "event_delete", "event_info",
    "grab_set", "grab_release", "grab_set_global", "grab_current", "grab_status",
    "mainloop", "quit", "nametowidget", "tk_setPalette",
    "selection_own", "selection_own_get", "selection_clear", "selection_get",
    "selection_handle", "title", "geometry", "geometrymanager",
    "minsize", "maxsize", "resizable", "overrideredirect", "deiconify",
    "iconify", "withdraw", "state", "attributes", "protocol",
    "winfo_exists", "winfo_children", "winfo_toplevel", "winfo_width",
    "winfo_height", "winfo_rootx", "winfo_rooty", "winfo_x", "winfo_y",
    "winfo_reqwidth", "winfo_reqheight", "winfo_viewable", "winfo_ismapped",
    "winfo_id", "winfo_fpixels", "winfo_pixels", "winfo_parent",
    "winfo_manager", "winfo_name", "winfo_screenwidth", "winfo_screenheight",
    "winfo_colormapfull", "winfo_containing", "winfo_depth",
    "winfo_screendepth", "winfo_screenvisual", "winfo_visual", "winfo_visualid",
    "winfo_ismapped", "winfo_pointerx", "winfo_pointery",
}


def _parse(path: str) -> ast.Module:
    with open(path, encoding="utf-8") as handle:
        return ast.parse(handle.read())


def _module_path(module: str) -> str:
    return os.path.join(ROOT, *module.split("."))


def _add_args(names: set, args: ast.arguments) -> None:
    """Ajoute les paramètres d'une fonction (ou lambda) aux noms liés."""
    for arg in args.posonlyargs + args.args + args.kwonlyargs:
        names.add(arg.arg)
    for extra in (args.vararg, args.kwarg):
        if extra is not None:
            names.add(extra.arg)


def _own_nodes(nodes) -> list:
    """Noeuds du scope courant : on ne descend pas dans les scopes imbriqués
    (le corps d'une fonction ne voit pas les noms de celui d'une autre), mais
    on garde décorateurs, valeurs par défaut et bases de classes, évalués
    dans le scope englobant."""
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
    """Noms liés par ce scope : imports, affectations, defs, arguments…"""
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
        elif isinstance(node, ast.Name) \
                and isinstance(node.ctx, (ast.Store, ast.Del)):
            names.add(node.id)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            names.update(node.names)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
    return names


def _undefined_names(source: str, label: str = "<source>") -> list:
    """Noms utilisés comme base d'attribut mais liés nulle part dans le scope.

    Repère exactement le défaut « NameError: name 'tk' is not defined » qui
    n'apparaît qu'à l'ouverture d'un écran : un nom global manquant est
    invisible à l'import, donc à tous les autres contrôles statiques.
    """
    tree = ast.parse(source)
    # ``from x import *`` rend l'analyse statique impossible : fichier ignoré.
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) \
                and any(alias.name == "*" for alias in node.names):
            return []
    problems = set()

    def visit(nodes, visible) -> None:
        scope = visible | _bindings(nodes)
        for node in _own_nodes(nodes):
            if (isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Name)
                    and node.value.id not in scope):
                problems.add(label + ":" + str(node.lineno) + " nom non défini '"
                             + node.value.id + "'")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                   ast.ClassDef)):
                visit(node.body, scope)
            elif isinstance(node, ast.Lambda):
                inner = set(scope)
                _add_args(inner, node.args)
                visit([node.body], inner)

    visit(tree.body, BUILTINS)
    return sorted(problems)


def _top_level_names(tree: ast.Module) -> set:
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _class_infos(tree: ast.Module) -> dict:
    """classe -> (méthodes, attributs self.* et de classe)."""
    infos = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        methods, attrs = set(), set()
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.add(item.name)
                for sub in ast.walk(item):
                    if isinstance(sub, ast.Assign):
                        for target in sub.targets:
                            if (isinstance(target, ast.Attribute)
                                    and isinstance(target.value, ast.Name)
                                    and target.value.id == "self"):
                                attrs.add(target.attr)
                    elif isinstance(sub, ast.AnnAssign):
                        target = sub.target
                        if (isinstance(target, ast.Attribute)
                                and isinstance(target.value, ast.Name)
                                and target.value.id == "self"):
                            attrs.add(target.attr)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        attrs.add(target.id)
        infos[node.name] = (methods, attrs)
    return infos


def _widget_classes() -> dict:
    classes = {}
    for path in (os.path.join(ROOT, "ltadmin", "ui", "widgets.py"),
                 os.path.join(ROOT, "ltadmin", "ui", "dialogs.py")):
        classes.update(_class_infos(_parse(path)))
    return {name: info for name, info in classes.items()
            if name in WIDGET_CLASSES}


def _receiver_key(node: ast.AST) -> str:
    """Clé textuelle d'un récepteur : name, self.attr ou conteneur."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _receiver_key(node.value)
        return base + "." + node.attr if base else ""
    if isinstance(node, ast.Subscript):
        return _receiver_key(node.value)
    return ""


def _tracked_widgets(tree: ast.Module) -> dict:
    """id/self.attr/conteneur -> classe widget qui y est affectée."""
    mapping = {}
    for node in ast.walk(tree):
        widget = None
        value = node.value if isinstance(node, ast.Assign) else None
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) \
                and value.func.id in WIDGET_CLASSES:
            widget = value.func.id
        elif isinstance(value, (ast.List, ast.Tuple)):
            for element in value.elts:
                if (isinstance(element, ast.Call)
                        and isinstance(element.func, ast.Name)
                        and element.func.id in WIDGET_CLASSES):
                    widget = element.func.id
                    break
        if widget is None or not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            key = _receiver_key(target)
            if key:
                mapping.setdefault(key, widget)
    return mapping


class TestMenuEtEnregistrements(unittest.TestCase):

    def test_chaque_entree_menu_a_une_vue(self):
        from ltadmin.services.auth.habilitations import MENU_ORDER, Modules
        registered = self._registered_views()
        self.assertEqual(set(registered), set(MENU_ORDER),
                         "Menu et vues enregistrées divergent : "
                         + str(set(MENU_ORDER) ^ set(registered)))

    def test_cle_enregistree_est_un_module_connu(self):
        from ltadmin.services.auth.habilitations import Modules
        valeurs = {value for name, value in vars(Modules).items()
                   if not name.startswith("_")}
        for key in self._registered_views():
            self.assertIn(key, valeurs, "Clé de module inconnue : " + repr(key))

    def test_vues_enregistrees_existent_et_signees(self):
        classes = self._view_classes()
        for key, class_name in self._registered_views().items():
            self.assertIn(class_name, classes,
                          "Vue " + class_name + " (" + key + ") introuvable")
            init = classes[class_name]
            self.assertGreaterEqual(
                init, 4, class_name + ".__init__ doit accepter "
                "(parent, services, session) : " + str(init) + " paramètres")

    def _registered_views(self) -> dict:
        tree = _parse(os.path.join(ROOT, "main.py"))
        registered = {}
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "register_view" and node.args):
                key_node, class_node = node.args[0], node.args[1]
                if isinstance(key_node, ast.Attribute):
                    key = key_node.attr
                elif isinstance(key_node, ast.Constant):
                    key = key_node.value
                else:
                    continue
                registered[key] = class_node.id
        # résout les clés m.ATTR -> libellé Modules
        from ltadmin.services.auth.habilitations import Modules
        resolved = {}
        for key, class_name in registered.items():
            resolved[getattr(Modules, key, key)] = class_name
        return resolved

    def _view_classes(self) -> dict:
        """Classe -> nb de paramètres positionnels de __init__
        (résolu via les classes de base si absent, ex. DashboardView)."""
        declared = {}
        for path in glob.glob(os.path.join(ROOT, "ltadmin", "ui", "views",
                                           "*.py")):
            for node in _parse(path).body:
                if isinstance(node, ast.ClassDef):
                    arity = None
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) \
                                and item.name == "__init__":
                            arity = (len(item.args.posonlyargs)
                                     + len(item.args.args))
                    declared[node.name] = (arity, [
                        base.id for base in node.bases
                        if isinstance(base, ast.Name)])
        resolved = {}

        def _arity(name: str, seen=None) -> int:
            if name in resolved:
                return resolved[name]
            seen = seen or set()
            if name in seen or name not in declared:
                return 0
            seen.add(name)
            arity, bases = declared[name]
            if arity is None:
                arity = max((_arity(base, seen) for base in bases), default=0)
            resolved[name] = arity
            return arity

        for name in declared:
            _arity(name)
        return resolved


class TestImportsUI(unittest.TestCase):

    def test_les_imports_ltadmin_resolvent(self):
        problems = []
        for path in ALL_FILES:
            tree = _parse(path)
            for node in ast.walk(tree):
                if not (isinstance(node, ast.ImportFrom) and node.module
                        and node.module.startswith("ltadmin")):
                    continue
                base = _module_path(node.module)
                if not (os.path.isfile(base + ".py")
                        or os.path.isdir(base)):
                    problems.append(path + " : module " + node.module
                                    + " introuvable")
                    continue
                if os.path.isfile(base + ".py"):
                    names = _top_level_names(_parse(base + ".py"))
                else:  # package : __init__
                    init = os.path.join(base, "__init__.py")
                    names = _top_level_names(_parse(init)) if os.path.isfile(
                        init) else set()
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    submodule = os.path.join(base, alias.name + ".py")
                    if alias.name not in names and not os.path.isfile(
                            submodule):
                        problems.append(
                            path + " : " + alias.name
                            + " introuvable dans " + node.module)
        self.assertEqual(problems, [], "\n".join(problems))


class TestAppelsWidgets(unittest.TestCase):

    def test_methodes_appelees_existent(self):
        widget_classes = _widget_classes()
        problems = []
        for path in ALL_FILES:
            tree = _parse(path)
            tracked = _tracked_widgets(tree)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not (isinstance(func, ast.Attribute)
                        and isinstance(func.value, (ast.Name, ast.Attribute,
                                                    ast.Subscript))):
                    continue
                key = _receiver_key(func.value)
                if key not in tracked:
                    continue
                widget = tracked[key]
                methods, attrs = widget_classes[widget]
                if func.attr not in methods | attrs | TK_ALLOWLIST:
                    problems.append(
                        os.path.basename(path) + ":" + str(node.lineno)
                        + " " + widget + "." + func.attr + "() inexistant")
        self.assertEqual(problems, [], "\n".join(problems))


class TestSessionEtEditeur(unittest.TestCase):

    def test_session_n_expose_que_login_display_name_role(self):
        from ltadmin.models.db_models import UserSession
        champs = set(getattr(UserSession, "__dataclass_fields__",
                             vars(UserSession).get("_fields", {})))
        self.assertEqual(champs, {"login", "display_name", "role"},
                         str(champs))
        for path in ALL_FILES:
            with open(path, encoding="utf-8") as handle:
                source = handle.read()
            for pattern in (r"session\.profil\b", r"session\.code_utr\b"):
                match = re.search(pattern, source)
                self.assertIsNone(
                    match, path + " utilise " + pattern
                    + " (UserSession expose login/role)")

    def test_editeur_generique_couvre_les_types(self):
        path = os.path.join(ROOT, "ltadmin", "ui", "views", "record_editor.py")
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        for kind in ("BOOLEAN", "DATETIME", "MEMO", "LONG", "DOUBLE",
                     "CURRENCY"):
            self.assertIn('"' + kind + '"', source,
                          "record_editor ne gère pas le type " + kind)
        # AUTONUMBER et BINARY passent par les attributs de colonne.
        self.assertIn("column.autonumber", source)
        self.assertIn("column.is_binary", source)
        self.assertNotIn('"BOOL"', source,
                         "record_editor : le type s'appelle BOOLEAN, pas BOOL")
        self.assertNotIn("column.length", source,
                         "record_editor : l'attribut s'appelle column.size")

    def test_login_dialog_run(self):
        tree = _parse(os.path.join(ROOT, "ltadmin", "ui", "login_dialog.py"))
        run = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "LoginDialog":
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "run":
                        run = item
        self.assertIsNotNone(run, "LoginDialog.run absent")
        positional = len(run.args.args) + len(run.args.posonlyargs)
        self.assertEqual(positional, 2,
                         "run(parent, services) attendu, "
                         + str(positional) + " paramètres trouvés")
        # main.py appelle LoginDialog.run(x, y)
        main_tree = _parse(os.path.join(ROOT, "main.py"))
        calls = [node for node in ast.walk(main_tree)
                 if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute)
                 and node.func.attr == "run"
                 and isinstance(node.func.value, ast.Name)
                 and node.func.value.id == "LoginDialog"]
        self.assertTrue(calls, "main.py n'appelle pas LoginDialog.run")
        for call in calls:
            self.assertEqual(len(call.args), 2)


class TestNomsDefinis(unittest.TestCase):
    """Aucun écran ne doit planter sur un nom global manquant."""

    def test_les_noms_utilises_sont_definis(self):
        problems = []
        for path in SOURCE_FILES:
            with open(path, encoding="utf-8") as handle:
                source = handle.read()
            problems.extend(_undefined_names(
                source, os.path.relpath(path, ROOT).replace(os.sep, "/")))
        self.assertEqual(problems, [], "\n".join(problems))

    def test_le_controleur_detecte_un_import_manquant(self):
        """Garde-fou : le contrôleur repère bien le défaut d'origine."""
        # import absent du fichier (cas tkinter dans statistics_view).
        self.assertEqual(
            _undefined_names("def ouvrir(self):\n    return tk.BOTH\n"),
            ["<source>:2 nom non défini 'tk'"])
        # import présent, mais dans une autre fonction : hors de portée.
        self.assertEqual(
            _undefined_names(
                "def premier():\n"
                "    from ltadmin.core.result import Result\n"
                "    return Result.ok()\n"
                "\n"
                "def second():\n"
                "    return Result.fail('x')\n"),
            ["<source>:6 nom non défini 'Result'"])
        # cas corrects : module, fonction, lambda, compréhension, global.
        for correct in (
                "import tkinter as tk\n\n\ndef a():\n    return tk.BOTH\n",
                "def a():\n    import tkinter as tk\n    return tk.BOTH\n",
                "def a():\n    return sorted(c.name for c in [])\n",
                "import tkinter as tk\n\nf = lambda e: tk.X\n",
                "import tkinter as tk\n\n\ndef a():\n"
                "    import tkinter as tk\n    return tk.X\n"):
            self.assertEqual(_undefined_names(correct), [], correct)


if __name__ == "__main__":
    unittest.main()
