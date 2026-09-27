/* Vue : référentiel (filières, niveaux, salles, classes, modules, matières). */
"use strict";

/**
 * Onglet CRUD générique : `spec` = {title, singular, url, idKey, columns, fields(values),
 * load() → lignes, deletable(row), afterSave()}.
 */
function crudSection(spec) {
  const zone = el("div");
  const charger = async () => {
    clear(zone); zone.appendChild(loading());
    let rows;
    try { rows = await spec.load(); } catch (ex) { clear(zone); reportError(ex); return; }
    clear(zone);
    const columns = spec.columns.concat([{ label: "", cls: "actions", render: (r) => actionButtons([
      { label: "Modifier", onClick: () => editer(r) },
      (spec.deletable ? spec.deletable(r) : true) && { label: "Supprimer", cls: "danger", onClick: () => supprimer(r) },
    ]) }]);
    zone.appendChild(el("div", { class: "compteur" }, rows.length + " élément(s)"));
    zone.appendChild(dataTable(columns, rows, { empty: "Aucun élément.", onRow: (r) => editer(r) }));
  };
  const editer = async (row) => {
    const creation = !row;
    const ok = await modal.form({
      title: creation ? "Nouveau — " + spec.singular : "Modifier — " + spec.singular,
      fields: spec.fields(row || {}, creation), values: row || (typeof spec.defaults === "function" ? spec.defaults() : spec.defaults) || {}, size: spec.size || "",
      onSubmit: async (v) => {
        const body = creation ? v : Object.assign({}, v, { [spec.idKey]: row[spec.idKey] });
        const r = await API.post(spec.url, body);
        toast.success(r.message);
      },
    });
    if (ok) { App.invalidateRef(); await App.loadRef(true); if (spec.afterSave) spec.afterSave(); charger(); }
  };
  const supprimer = async (row) => {
    if (!await modal.confirm({ title: "Supprimer", message: `Supprimer « ${spec.label(row)} » ? L’opération est refusée si l’élément est utilisé ailleurs.`, ok: "Supprimer", danger: true })) return;
    try {
      const r = await API.del(spec.url + "/" + encodeURIComponent(row[spec.idKey]));
      toast.success(r.message);
      App.invalidateRef(); await App.loadRef(true); charger();
    } catch (ex) { reportError(ex); }
  };
  const section = el("div", null,
    el("div", { class: "flex between mb" }, el("div", null, el("h2", null, spec.title), spec.description ? el("div", { class: "muted small" }, spec.description) : null),
      button("+ Ajouter", () => editer(null), "primaire")),
    zone);
  charger();
  return section;
}

App.register("referentiel", {
  async render(container, { params }) {
    const onglets = [
      { key: "classes", label: "Classes" }, { key: "filieres", label: "Filières" }, { key: "niveaux", label: "Niveaux" },
      { key: "salles", label: "Salles" }, { key: "modules", label: "Modules" }, { key: "matieres", label: "Matières" },
    ];
    let actif = params.onglet && onglets.some((o) => o.key === params.onglet) ? params.onglet : "classes";
    const corps = el("div");
    const barre = el("div");
    const afficher = () => {
      clear(barre); barre.appendChild(tabs(onglets, actif, (k) => { actif = k; history.replaceState(null, "", "#/referentiel?onglet=" + k); afficher(); }));
      clear(corps); corps.appendChild(SECTIONS_REFERENTIEL[actif]());
    };
    append(container, [pageHeader("Référentiel", "Structure pédagogique : classes, filières, niveaux, salles, modules et matières."), barre, corps]);
    afficher();
  },
});

const SECTIONS_REFERENTIEL = {
  classes: () => crudSection({
    title: "Classes", singular: "classe", url: "/api/ref/classes", idKey: "id_classe",
    description: "Une classe = année × filière × niveau. L’effectif maximal est contrôlé à l’inscription.",
    label: (r) => r.libelle,
    load: async () => API.value("/api/ref/classes"),
    columns: [
      { key: "libelle", label: "Libellé" }, { key: "annee", label: "Année" }, { key: "filiere", label: "Filière" },
      { key: "niveau", label: "Niveau" }, { key: "salle", label: "Salle" },
      { label: "Inscrits / max", num: true, render: (r) => (r.nb_inscrits || 0) + " / " + (r.effectif_max || "—") },
    ],
    fields: () => [
      { name: "libelle", label: "Libellé", required: true, span: 12, placeholder: "Ex. BTS1 Hôtellerie" },
      { name: "id_annee", label: "Année scolaire", type: "select", required: true, span: 6, options: App.ref.annees.map((a) => ({ value: a.id_annee, label: a.libelle + (a.active ? " (active)" : "") })) },
      { name: "code_filiere", label: "Filière", type: "select", required: true, span: 6, options: App.ref.filieres.map((f) => ({ value: f.code_filiere, label: f.libelle })) },
      { name: "code_niveau", label: "Niveau", type: "select", required: true, span: 6, options: App.ref.niveaux.map((n) => ({ value: n.code_niveau, label: n.libelle })) },
      { name: "id_salle", label: "Salle principale", type: "select", span: 6, options: App.ref.salles.map((s) => ({ value: s.id_salle, label: s.nom_salle })) },
      { name: "effectif_max", label: "Effectif maximal", type: "number", span: 6, min: 1, step: "1" },
      { name: "id_responsable", label: "Formateur responsable", type: "select", span: 6, options: App.ref.formateurs.map((f) => ({ value: f.id_formateur, label: f.nom_complet })) },
    ],
    defaults: () => ({}),
  }),
  filieres: () => crudSection({
    title: "Filières", singular: "filière", url: "/api/ref/filieres", idKey: "code_filiere", label: (r) => r.libelle,
    load: async () => API.value("/api/ref/filieres"),
    columns: [{ key: "code_filiere", label: "Code", cls: "mono" }, { key: "libelle", label: "Filière" }, { key: "diplome", label: "Diplôme" },
      { label: "Durée (ans)", num: true, key: "duree_ans" }, { label: "Active", render: (r) => fmt.oui(r.active) }],
    fields: (r, creation) => [
      { name: "code_filiere", label: "Code", required: true, span: 4, upper: true, maxlength: 10, disabled: !creation },
      { name: "libelle", label: "Libellé", required: true, span: 8 },
      { name: "diplome", label: "Diplôme", span: 6 }, { name: "duree_ans", label: "Durée (ans)", type: "number", span: 3, min: 1, step: "1" },
      { name: "active", label: "Active", type: "check", span: 3 },
    ],
    defaults: { active: true, duree_ans: 2, diplome: "BTS" },
  }),
  niveaux: () => crudSection({
    title: "Niveaux", singular: "niveau", url: "/api/ref/niveaux", idKey: "code_niveau", label: (r) => r.libelle,
    load: async () => API.value("/api/ref/niveaux"),
    columns: [{ key: "code_niveau", label: "Code", cls: "mono" }, { key: "libelle", label: "Niveau" }, { key: "ordre_niv", label: "Ordre", num: true }],
    fields: (r, creation) => [
      { name: "code_niveau", label: "Code", required: true, span: 4, upper: true, maxlength: 10, disabled: !creation },
      { name: "libelle", label: "Libellé", required: true, span: 5 }, { name: "ordre_niv", label: "Ordre", type: "number", span: 3, step: "1" },
    ],
  }),
  salles: () => crudSection({
    title: "Salles", singular: "salle", url: "/api/ref/salles", idKey: "id_salle", label: (r) => r.nom_salle,
    load: async () => API.value("/api/ref/salles"),
    columns: [{ key: "nom_salle", label: "Salle" }, { key: "nature_salle", label: "Nature" }, { key: "capacite", label: "Capacité", num: true }, { label: "Disponible", render: (r) => fmt.oui(r.disponible) }],
    fields: () => [
      { name: "nom_salle", label: "Nom", required: true, span: 6 },
      { name: "nature_salle", label: "Nature", type: "select", span: 6, options: ["Cours", "Cuisine pédagogique", "Restaurant d’application", "Laboratoire", "Informatique", "Amphithéâtre", "Autre"] },
      { name: "capacite", label: "Capacité", type: "number", span: 6, min: 1, step: "1" }, { name: "disponible", label: "Disponible", type: "check", span: 6 },
    ],
    defaults: { disponible: true },
  }),
  modules: () => crudSection({
    title: "Modules de formation", singular: "module", url: "/api/ref/modules", idKey: "code_module", label: (r) => r.module_lib,
    load: async () => API.value("/api/ref/modules"),
    columns: [{ key: "code_module", label: "Code", cls: "mono" }, { key: "module_lib", label: "Module" },
      { label: "Filière", render: (r) => { const f = App.ref.filieres.find((x) => x.code_filiere === r.code_filiere); return f ? f.libelle : r.code_filiere; } }],
    fields: (r, creation) => [
      { name: "code_module", label: "Code", required: true, span: 4, upper: true, maxlength: 10, disabled: !creation },
      { name: "module_lib", label: "Libellé", required: true, span: 8 },
      { name: "code_filiere", label: "Filière", type: "select", required: true, span: 6, options: App.ref.filieres.map((f) => ({ value: f.code_filiere, label: f.libelle })) },
    ],
  }),
  matieres: () => crudSection({
    title: "Matières", singular: "matière", url: "/api/ref/matieres", idKey: "code_matiere", label: (r) => r.libelle,
    load: async () => API.value("/api/ref/matieres"),
    columns: [{ key: "code_matiere", label: "Code", cls: "mono" }, { key: "libelle", label: "Matière" },
      { label: "Module", render: (r) => { const m = App.ref.modules.find((x) => x.code_module === r.code_module); return m ? m.module_lib : r.code_module; } },
      { key: "nature", label: "Nature" }, { key: "ordre_mat", label: "Ordre", num: true }],
    fields: (r, creation) => [
      { name: "code_matiere", label: "Code", required: true, span: 4, upper: true, maxlength: 10, disabled: !creation },
      { name: "libelle", label: "Libellé", required: true, span: 8 },
      { name: "code_module", label: "Module", type: "select", required: true, span: 6, options: App.ref.modules.map((m) => ({ value: m.code_module, label: m.module_lib })) },
      { name: "nature", label: "Nature", type: "select", span: 3, options: ["Théorique", "Pratique", "Mixte"] },
      { name: "ordre_mat", label: "Ordre", type: "number", span: 3, step: "1" },
    ],
  }),
};
