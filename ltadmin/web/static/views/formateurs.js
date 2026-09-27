/* Vue : formateurs et programmes (affectation matière × classe × formateur). */
"use strict";

const FORMATEUR_FIELDS = () => [
  { section: "Identité" },
  { name: "matricule", label: "Matricule", type: "readonly", span: 3 },
  { name: "nom", label: "Nom", required: true, span: 5, upper: true },
  { name: "prenom", label: "Prénom(s)", required: true, span: 4 },
  { name: "sexe", label: "Sexe", type: "select", span: 3, options: [{ value: "M", label: "Masculin" }, { value: "F", label: "Féminin" }] },
  { name: "date_naissance", label: "Date de naissance", type: "date", span: 3 },
  { name: "cin", label: "CIN", span: 3 },
  { name: "tel", label: "Téléphone", span: 3 },
  { name: "email", label: "E-mail", span: 6 },
  { name: "adresse", label: "Adresse", span: 6 },
  { section: "Profil professionnel" },
  { name: "specialite", label: "Spécialité", span: 4 },
  { name: "diplome", label: "Diplôme", span: 4 },
  { name: "contrat", label: "Contrat", type: "select", span: 4, options: ["Permanent", "Vacataire", "Stagiaire"] },
  { name: "taux_horaire", label: "Taux horaire (" + App.devise() + ")", type: "money", span: 4, min: 0 },
  { name: "date_embauche", label: "Date d’embauche", type: "date", span: 4 },
  { name: "actif", label: "Actif", type: "check", span: 4 },
];

App.register("formateurs", {
  async render(container, { params, segments }) {
    if (segments[0]) { await renderFicheFormateur(container, Number(segments[0])); return; }
    const onglets = [{ key: "formateurs", label: "Formateurs" }, { key: "programmes", label: "Programmes par classe" }];
    let actif = params.onglet === "programmes" ? "programmes" : "formateurs";
    const barre = el("div"), corps = el("div");
    const afficher = () => {
      clear(barre); barre.appendChild(tabs(onglets, actif, (k) => { actif = k; history.replaceState(null, "", "#/formateurs?onglet=" + k); afficher(); }));
      clear(corps); corps.appendChild(actif === "formateurs" ? sectionFormateurs() : sectionProgrammes(params));
    };
    append(container, [pageHeader("Formateurs", "Corps enseignant et programmes (matières enseignées par classe)."), barre, corps]);
    afficher();
  },
});

function sectionFormateurs() {
  const zone = el("div");
  const recherche = el("input", { type: "search", placeholder: "Nom, prénom, matricule, spécialité…" });
  const actifs = el("input", { type: "checkbox", checked: true });
  const charger = async () => {
    clear(zone); zone.appendChild(loading());
    const rows = await API.value("/api/formateurs" + API.qs({ q: recherche.value.trim(), actifs: actifs.checked ? 1 : "" }));
    clear(zone);
    zone.appendChild(el("div", { class: "compteur" }, rows.length + " formateur(s)"));
    zone.appendChild(dataTable([
      { key: "matricule", label: "Matricule", cls: "mono nowrap" }, { key: "nom", label: "Nom" }, { key: "prenom", label: "Prénom(s)" },
      { key: "specialite", label: "Spécialité" }, { key: "contrat", label: "Contrat" }, { key: "tel", label: "Téléphone" },
      { label: "Taux horaire", num: true, render: (r) => fmt.money(r.taux_horaire, "") }, { label: "Actif", render: (r) => fmt.oui(r.actif) },
      { label: "", cls: "actions", render: (r) => actionButtons([
        { label: "Fiche", onClick: () => App.navigate("formateurs", {}, [r.id_formateur]) },
        { label: "Modifier", onClick: () => editerFormateur(r).then((ok) => ok && charger()) },
      ]) },
    ], rows, { onRow: (r) => App.navigate("formateurs", {}, [r.id_formateur]), empty: "Aucun formateur." }));
  };
  recherche.addEventListener("input", debounce(charger, 250));
  actifs.addEventListener("change", charger);
  charger();
  return el("div", null,
    el("div", { class: "filtres" }, filterField("Recherche", recherche, "large"),
      el("div", { class: "champ case" }, actifs, el("label", null, "Actifs seulement")),
      el("div", { class: "grow" }), button("+ Nouveau formateur", () => editerFormateur(null).then((ok) => ok && charger()), "primaire")),
    zone);
}

async function editerFormateur(f) {
  const creation = !f;
  const ok = await modal.form({
    title: creation ? "Nouveau formateur" : "Modifier " + f.nom_complet, fields: FORMATEUR_FIELDS(), size: "large",
    values: f || { actif: true, contrat: "Vacataire" },
    onSubmit: async (v) => {
      const r = creation ? await API.post("/api/formateurs", v) : await API.put("/api/formateurs/" + f.id_formateur, v);
      toast.success(r.message);
    },
  });
  if (ok) App.invalidateRef();
  return ok;
}

async function renderFicheFormateur(container, id) {
  const { formateur: f, programmes, paies } = await API.value("/api/formateurs/" + id);
  const refresh = () => App.refresh();
  const infos = el("dl", { class: "kv" },
    ligneKv("Matricule", f.matricule), ligneKv("Nom complet", f.nom_complet), ligneKv("Sexe", f.sexe === "F" ? "Féminin" : f.sexe === "M" ? "Masculin" : "—"),
    ligneKv("Naissance", fmt.date(f.date_naissance)), ligneKv("CIN", f.cin), ligneKv("Téléphone", f.tel), ligneKv("E-mail", f.email), ligneKv("Adresse", f.adresse),
    ligneKv("Spécialité", f.specialite), ligneKv("Diplôme", f.diplome), ligneKv("Contrat", f.contrat), ligneKv("Taux horaire", fmt.money(f.taux_horaire)),
    ligneKv("Embauche", fmt.date(f.date_embauche)), ligneKv("Actif", fmt.oui(f.actif)));
  const progs = dataTable([
    { key: "classe", label: "Classe" }, { key: "matiere", label: "Matière" }, { label: "Coef.", num: true, render: (r) => fmt.number(r.coefficient, 1) },
    { label: "Vol. horaire", num: true, key: "vol_horaire" },
  ], programmes, { empty: "Aucune matière affectée." });
  const sections = [card("Identité", infos), card("Matières enseignées", progs, [button("Programmes", () => App.navigate("formateurs", { onglet: "programmes" }), "petit")])];
  if (App.can("Paie des formateurs")) {
    sections.push(card("Paies", dataTable([
      { key: "periode", label: "Période" }, { label: "Heures", num: true, render: (r) => fmt.number(r.nb_heures, 1) },
      { label: "Taux", num: true, render: (r) => fmt.money(r.taux, "") }, { label: "Montant", num: true, render: (r) => fmt.money(r.montant, "") },
      { label: "Payée", render: (r) => r.paye ? el("span", { class: "badge vert" }, "Payée le " + fmt.date(r.date_paie)) : el("span", { class: "badge ambre" }, "À payer") },
    ], paies, { empty: "Aucune paie calculée." }), [button("Paie", () => App.navigate("paie", { formateur: id }), "petit")]));
  }
  append(container, [
    pageHeader(f.nom_complet, "Formateur " + f.matricule, [
      button("← Liste", () => App.navigate("formateurs")),
      button("Modifier", () => editerFormateur(f).then((ok) => ok && refresh())),
      button("Supprimer", async () => {
        if (!await modal.confirm({ title: "Supprimer le formateur", message: `Supprimer ${f.nom_complet} ? Refusé s’il est affecté à des programmes ou des paies (désactivez-le plutôt).`, ok: "Supprimer", danger: true })) return;
        try { const r = await API.del("/api/formateurs/" + id); toast.success(r.message); App.invalidateRef(); App.navigate("formateurs"); } catch (ex) { reportError(ex); }
      }, "danger"),
    ]),
    el("div", { class: "grille c2" }, sections),
  ]);
}

function sectionProgrammes(params) {
  const classes = App.classesActives();
  const selectClasse = selectInput(classeOptions(classes), params.classe || (classes[0] && classes[0].id_classe), { placeholder: "— Choisir une classe —" });
  const zone = el("div");
  const charger = async () => {
    const id = selectClasse.value;
    clear(zone);
    if (!id) { zone.appendChild(el("div", { class: "info" }, "Choisissez une classe.")); return; }
    zone.appendChild(loading());
    const rows = await API.value("/api/programmes" + API.qs({ classe: id }));
    clear(zone);
    const totalCoef = rows.reduce((s, r) => s + (r.coefficient || 0), 0);
    const totalVol = rows.reduce((s, r) => s + (r.vol_horaire || 0), 0);
    zone.appendChild(dataTable([
      { key: "code_matiere", label: "Code", cls: "mono" }, { key: "matiere", label: "Matière" }, { key: "formateur", label: "Formateur" },
      { label: "Coefficient", num: true, render: (r) => fmt.number(r.coefficient, 1) }, { label: "Vol. horaire", num: true, key: "vol_horaire" },
      { label: "Note élim.", num: true, render: (r) => fmt.number(r.note_elimin, 1) },
      { label: "", cls: "actions", render: (r) => actionButtons([
        { label: "Modifier", onClick: () => editerProgramme(r, id).then((ok) => ok && charger()) },
        { label: "Retirer", cls: "danger", onClick: async () => {
          if (!await modal.confirm({ title: "Retirer la matière", message: `Retirer « ${r.matiere} » du programme de la classe ? Refusé si des évaluations ou un emploi du temps y sont rattachés.`, ok: "Retirer", danger: true })) return;
          try { const x = await API.del("/api/programmes/" + r.id_prog); toast.success(x.message); charger(); } catch (ex) { reportError(ex); }
        } },
      ]) },
    ], rows, { empty: "Aucune matière au programme de cette classe.", foot: ["", "Total", "", fmt.number(totalCoef, 1), totalVol, "", ""] }));
  };
  selectClasse.addEventListener("change", charger);
  charger();
  return el("div", null,
    el("div", { class: "filtres" }, filterField("Classe", selectClasse, "large"), el("div", { class: "grow" }),
      button("+ Ajouter une matière", () => { if (!selectClasse.value) { toast.warn("Choisissez une classe."); return; } editerProgramme(null, selectClasse.value).then((ok) => ok && charger()); }, "primaire")),
    zone);
}

async function editerProgramme(p, idClasse) {
  const creation = !p;
  return modal.form({
    title: creation ? "Ajouter une matière au programme" : "Modifier — " + p.matiere,
    fields: [
      { name: "id_classe", label: "Classe", type: "select", required: true, span: 12, options: classeOptions(App.ref.classes), disabled: !creation },
      { name: "code_matiere", label: "Matière", type: "select", required: true, span: 12, disabled: !creation,
        options: App.ref.matieres.map((m) => ({ value: m.code_matiere, label: m.libelle + " (" + m.code_matiere + ")" })) },
      { name: "id_formateur", label: "Formateur", type: "select", required: true, span: 12,
        options: App.ref.formateurs.filter((f) => f.actif || (p && f.id_formateur === p.id_formateur)).map((f) => ({ value: f.id_formateur, label: f.nom_complet + (f.specialite ? " — " + f.specialite : "") })) },
      { name: "coefficient", label: "Coefficient", type: "number", required: true, span: 4, min: 0.5, step: "0.5" },
      { name: "vol_horaire", label: "Volume horaire", type: "number", span: 4, min: 0, step: "1" },
      { name: "note_elimin", label: "Note éliminatoire", type: "number", span: 4, min: 0, max: 20, step: "0.5", help: "Par défaut : paramètre NOTE_ELIMINATOIRE." },
    ],
    values: p || { id_classe: Number(idClasse), coefficient: 1, note_elimin: Number(App.param("NOTE_ELIMINATOIRE", 5)) },
    onSubmit: async (v) => {
      const body = creation ? v : Object.assign({}, v, { id_prog: p.id_prog, id_classe: p.id_classe, code_matiere: p.code_matiere });
      const r = await API.post("/api/programmes", body);
      toast.success(r.message);
    },
  });
}
