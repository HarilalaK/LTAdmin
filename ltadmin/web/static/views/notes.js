/* Vue : périodes d'évaluation, évaluations (contrôle continu) et saisie des notes. */
"use strict";

const NATURES_EVALUATION = ["Devoir", "Interrogation", "TP", "Exposé", "Projet", "Examen blanc", "Autre"];

App.register("notes", {
  async render(container, { params, segments }) {
    if (segments[0] === "saisie" && segments[1]) { await renderSaisieNotes(container, Number(segments[1])); return; }
    const onglets = [{ key: "evaluations", label: "Évaluations et notes" }, { key: "periodes", label: "Périodes" }, { key: "moyennes", label: "Moyennes" }];
    let actif = onglets.some((o) => o.key === params.onglet) ? params.onglet : "evaluations";
    const barre = el("div"), corps = el("div");
    const afficher = () => {
      clear(barre); barre.appendChild(tabs(onglets, actif, (k) => { actif = k; history.replaceState(null, "", "#/notes?onglet=" + k); afficher(); }));
      clear(corps);
      corps.appendChild(actif === "evaluations" ? sectionEvaluations(params) : actif === "periodes" ? sectionPeriodes() : sectionMoyennes(params));
    };
    append(container, [pageHeader("Notes et évaluations", "Contrôle continu : périodes, évaluations par matière et saisie des notes."), barre, corps]);
    afficher();
  },
});

function periodeOptions() {
  return App.ref.periodes.map((p) => ({ value: p.id_periode, label: p.libelle + (p.cloturee ? " (clôturée)" : "") }));
}

function sectionPeriodes() {
  return crudSection({
    title: "Périodes d’évaluation", singular: "période", url: "/api/periodes", idKey: "id_periode", label: (r) => r.libelle,
    description: "Trimestres ou semestres de l’année. Une période clôturée n’accepte plus de saisie.",
    load: async () => API.value("/api/periodes"),
    columns: [
      { key: "code_periode", label: "Code", cls: "mono" }, { key: "libelle", label: "Libellé" }, { key: "ordre_per", label: "Ordre", num: true },
      { label: "Pondération", num: true, render: (r) => fmt.number(r.ponderation, 2) },
      { label: "Du", render: (r) => fmt.date(r.date_debut) }, { label: "Au", render: (r) => fmt.date(r.date_fin) },
      { label: "Clôturée", render: (r) => button(r.cloturee ? "Clôturée — rouvrir" : "Ouverte — clôturer", async () => {
        try { const x = await API.post(`/api/periodes/${r.id_periode}/cloture`, { cloturee: !r.cloturee }); toast.success(x.message); App.invalidateRef(); await App.loadRef(true); App.refresh(); } catch (ex) { reportError(ex); }
      }, "petit " + (r.cloturee ? "danger" : "")) },
    ],
    deletable: () => false,
    fields: (r, creation) => [
      { name: "id_annee", label: "Année scolaire", type: "select", required: true, span: 6, options: App.ref.annees.map((a) => ({ value: a.id_annee, label: a.libelle })) },
      { name: "code_periode", label: "Code", required: true, span: 3, upper: true, maxlength: 10, placeholder: "T1" },
      { name: "ordre_per", label: "Ordre", type: "number", required: true, span: 3, step: "1", min: 1 },
      { name: "libelle", label: "Libellé", required: true, span: 12, placeholder: "1er trimestre" },
      { name: "date_debut", label: "Début", type: "date", span: 4 }, { name: "date_fin", label: "Fin", type: "date", span: 4 },
      { name: "ponderation", label: "Pondération", type: "number", span: 4, step: "0.1", min: 0, help: "Poids de la période dans la moyenne annuelle." },
    ],
    defaults: () => ({ id_annee: App.session.annee_active ? App.session.annee_active.id_annee : null, ponderation: 1 }),
  });
}

function sectionEvaluations(params) {
  const classes = App.classesActives();
  const selectClasse = selectInput(classeOptions(classes), params.classe || (classes[0] && classes[0].id_classe), { placeholder: "— Classe —" });
  const selectPeriode = selectInput(periodeOptions(), params.periode || "", { placeholder: "Toutes les périodes" });
  const zone = el("div");
  const charger = async () => {
    clear(zone);
    if (!selectClasse.value) { zone.appendChild(el("div", { class: "info" }, "Choisissez une classe.")); return; }
    zone.appendChild(loading());
    const rows = await API.value("/api/evaluations" + API.qs({ classe: selectClasse.value, periode: selectPeriode.value }));
    clear(zone);
    zone.appendChild(el("div", { class: "compteur" }, rows.length + " évaluation(s)"));
    zone.appendChild(dataTable([
      { key: "periode", label: "Période" }, { key: "matiere", label: "Matière" }, { key: "intitule", label: "Intitulé" }, { key: "nature", label: "Nature" },
      { label: "Date", render: (r) => fmt.date(r.date_eval), cls: "nowrap" }, { label: "Barème", num: true, render: (r) => fmt.number(r.bareme, 0) },
      { label: "Poids", num: true, render: (r) => fmt.number(r.poids, 1) },
      { label: "État", render: (r) => el("span", null, r.publiee ? el("span", { class: "badge vert" }, "Publiée") : el("span", { class: "badge" }, "Brouillon"), r.periode_cloturee ? el("span", { class: "badge rouge", style: { marginLeft: "4px" } }, "Période clôturée") : null) },
      { label: "", cls: "actions", render: (r) => actionButtons([
        { label: "Saisir les notes", cls: "primaire", onClick: () => App.navigate("notes", {}, ["saisie", r.id_evaluation]) },
        { label: "Modifier", onClick: () => editerEvaluation(r, selectClasse.value).then((ok) => ok && charger()) },
        { label: r.publiee ? "Dépublier" : "Publier", onClick: async () => { try { const x = await API.post(`/api/evaluations/${r.id_evaluation}/publication`, { publiee: !r.publiee }); toast.success(x.message); charger(); } catch (ex) { reportError(ex); } } },
        { label: "Supprimer", cls: "danger", onClick: async () => {
          if (!await modal.confirm({ title: "Supprimer l’évaluation", message: `Supprimer « ${r.intitule} » et toutes ses notes ?`, ok: "Supprimer", danger: true })) return;
          try { const x = await API.del("/api/evaluations/" + r.id_evaluation); toast.success(x.message); charger(); } catch (ex) { reportError(ex); }
        } },
      ]) },
    ], rows, { empty: "Aucune évaluation pour ces critères.", onRow: (r) => App.navigate("notes", {}, ["saisie", r.id_evaluation]) }));
  };
  selectClasse.addEventListener("change", charger);
  selectPeriode.addEventListener("change", charger);
  charger();
  return el("div", null,
    el("div", { class: "filtres" }, filterField("Classe", selectClasse, "large"), filterField("Période", selectPeriode), el("div", { class: "grow" }),
      button("+ Nouvelle évaluation", () => { if (!selectClasse.value) { toast.warn("Choisissez une classe."); return; } editerEvaluation(null, selectClasse.value, selectPeriode.value).then((ok) => ok && charger()); }, "primaire")),
    zone);
}

async function editerEvaluation(e, idClasse, idPeriode) {
  const creation = !e;
  const programmes = await API.value("/api/programmes" + API.qs({ classe: idClasse }));
  if (!programmes.length) { toast.warn("Aucune matière au programme de cette classe : complétez d’abord le programme (menu Formateurs)."); return null; }
  return modal.form({
    title: creation ? "Nouvelle évaluation" : "Modifier l’évaluation",
    fields: [
      { name: "id_periode", label: "Période", type: "select", required: true, span: 6, options: periodeOptions() },
      { name: "id_prog", label: "Matière (programme)", type: "select", required: true, span: 6, options: programmes.map((p) => ({ value: p.id_prog, label: p.matiere + " — " + p.formateur })) },
      { name: "intitule", label: "Intitulé", required: true, span: 8, placeholder: "Devoir n°1" },
      { name: "nature", label: "Nature", type: "select", span: 4, options: NATURES_EVALUATION },
      { name: "date_eval", label: "Date", type: "date", span: 4 },
      { name: "bareme", label: "Barème", type: "number", required: true, span: 4, min: 1, step: "1", help: "Les notes sont ramenées sur 20." },
      { name: "poids", label: "Poids", type: "number", required: true, span: 4, min: 0.1, step: "0.5" },
      { name: "publiee", label: "Publiée (notes communiquées aux étudiants)", type: "check", span: 12 },
    ],
    values: e || { id_periode: idPeriode || (App.ref.periodes[0] && App.ref.periodes[0].id_periode), bareme: Number(App.param("BAREME_DEFAUT", 20)), poids: 1, date_eval: fmt.today(), nature: "Devoir" },
    onSubmit: async (v) => {
      const r = await API.post("/api/evaluations", creation ? v : Object.assign({}, v, { id_evaluation: e.id_evaluation }));
      toast.success(r.message);
    },
  });
}

async function renderSaisieNotes(container, id) {
  const { evaluation: e, notes } = await API.value("/api/evaluations/" + id);
  const bareme = e.bareme || 20;
  const verrou = !!e.periode_cloturee;
  const lignes = notes.map((n) => Object.assign({}, n));
  const stats = el("div", { class: "flex wrap mb" });
  const majStats = () => {
    const valeurs = lignes.filter((l) => !l.absent && l.valeur_note !== null && l.valeur_note !== "" && !Number.isNaN(Number(l.valeur_note))).map((l) => Number(l.valeur_note));
    const moy = valeurs.length ? valeurs.reduce((a, b) => a + b, 0) / valeurs.length : null;
    clear(stats);
    append(stats, [
      el("span", { class: "badge bleu" }, `${valeurs.length} / ${lignes.length} notes saisies`),
      el("span", { class: "badge" }, "Moyenne : " + (moy === null ? "—" : fmt.number(moy, 2) + " / " + bareme)),
      el("span", { class: "badge" }, "Min : " + (valeurs.length ? fmt.number(Math.min(...valeurs), 2) : "—")),
      el("span", { class: "badge" }, "Max : " + (valeurs.length ? fmt.number(Math.max(...valeurs), 2) : "—")),
      el("span", { class: "badge ambre" }, lignes.filter((l) => l.absent).length + " absent(s)"),
    ]);
  };
  majStats();

  const table = dataTable([
    { label: "#", render: (r, i) => i + 1, width: "40px" },
    { key: "matricule", label: "Matricule", cls: "mono nowrap" }, { key: "nom", label: "Nom" }, { key: "prenom", label: "Prénom(s)" },
    { label: "Note / " + bareme, num: true, render: (r) => {
      const input = el("input", { type: "number", class: "note", min: 0, max: bareme, step: "0.25", value: r.valeur_note === null ? "" : r.valeur_note, disabled: verrou || r.absent });
      input.addEventListener("input", () => { r.valeur_note = input.value === "" ? null : Number(input.value); r._modifie = true; input.classList.toggle("invalide", input.value !== "" && (Number(input.value) < 0 || Number(input.value) > bareme)); majStats(); });
      input.addEventListener("keydown", (ev) => { if (ev.key === "Enter") { ev.preventDefault(); const all = [...table.querySelectorAll("input.note")]; const idx = all.indexOf(input); if (all[idx + 1]) all[idx + 1].focus(); } });
      r._input = input;
      return input;
    } },
    { label: "Absent", render: (r) => { const cb = el("input", { type: "checkbox", checked: r.absent, disabled: verrou }); cb.addEventListener("change", () => { r.absent = cb.checked; r._modifie = true; if (cb.checked) { r.valeur_note = null; r._input.value = ""; } r._input.disabled = verrou || cb.checked; majStats(); }); return cb; } },
    { label: "Observation", render: (r) => { const i = el("input", { type: "text", value: r.observation || "", disabled: verrou, placeholder: "" }); i.addEventListener("input", () => { r.observation = i.value; r._modifie = true; }); return i; } },
  ], lignes, { empty: "Aucun inscrit dans cette classe." });

  const enregistrer = async () => {
    const modifiees = lignes.filter((l) => l._modifie);
    if (!modifiees.length) { toast.info("Aucune modification à enregistrer."); return; }
    const invalides = modifiees.filter((l) => !l.absent && l.valeur_note !== null && (l.valeur_note < 0 || l.valeur_note > bareme));
    if (invalides.length) { toast.error("Certaines notes dépassent le barème (" + bareme + ")."); return; }
    try {
      const r = await API.post(`/api/evaluations/${id}/notes`, { notes: modifiees.map((l) => ({ id_inscription: l.id_inscription, valeur_note: l.valeur_note, absent: l.absent, observation: l.observation })) });
      if (r.value.erreurs.length) { toast.warn(r.message); modal.open({ title: "Notes non enregistrées", body: el("ul", null, r.value.erreurs.map((x) => el("li", null, x))) }); } else toast.success(r.message);
      modifiees.forEach((l) => { l._modifie = false; });
    } catch (ex) { reportError(ex); }
  };

  append(container, [
    pageHeader("Saisie des notes — " + e.intitule, `${e.classe} · ${e.matiere} · ${e.periode} · ${e.nature || ""} du ${fmt.date(e.date_eval)} · barème ${bareme}`, [
      button("← Évaluations", () => App.navigate("notes", { classe: e.id_classe, periode: e.id_periode })),
      !verrou && button("Enregistrer les notes", enregistrer, "primaire"),
    ]),
    verrou ? el("div", { class: "avert mb" }, "La période est clôturée : la saisie est verrouillée.") : el("div", { class: "info mb" }, "Saisissez les notes puis cliquez sur « Enregistrer ». Touche Entrée : passer à la ligne suivante. Cochez « Absent » pour une absence à l’évaluation."),
    stats, table,
  ]);
  document.addEventListener("keydown", function raccourci(ev) {
    if (App.current !== "notes") { document.removeEventListener("keydown", raccourci); return; }
    if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "s") { ev.preventDefault(); if (!verrou) enregistrer(); }
  });
}

function sectionMoyennes(params) {
  const classes = App.classesActives();
  const selectClasse = selectInput(classeOptions(classes), params.classe || (classes[0] && classes[0].id_classe), { placeholder: "— Classe —" });
  const selectPeriode = selectInput(periodeOptions(), params.periode || (App.ref.periodes[0] && App.ref.periodes[0].id_periode), { placeholder: "— Période —" });
  const zone = el("div");
  const charger = async () => {
    clear(zone);
    if (!selectClasse.value || !selectPeriode.value) { zone.appendChild(el("div", { class: "info" }, "Choisissez une classe et une période.")); return; }
    zone.appendChild(loading());
    const [data, inscrits, programmes] = await Promise.all([
      API.value("/api/moyennes" + API.qs({ classe: selectClasse.value, periode: selectPeriode.value })),
      API.value("/api/inscriptions" + API.qs({ classe: selectClasse.value })),
      API.value("/api/programmes" + API.qs({ classe: selectClasse.value })),
    ]);
    clear(zone);
    const parInscription = {};
    inscrits.forEach((i) => { parInscription[i.id_inscription] = { inscription: i, matieres: {}, moyenne: null }; });
    data.matieres.forEach((m) => { if (parInscription[m.id_inscription]) parInscription[m.id_inscription].matieres[m.code_matiere] = m.moyenne_mat; });
    data.periodes.forEach((p) => { if (parInscription[p.id_inscription]) parInscription[p.id_inscription].moyenne = p.moyenne; });
    const rows = Object.values(parInscription).sort((a, b) => (b.moyenne || -1) - (a.moyenne || -1));
    const colonnes = [
      { label: "Rang", render: (r, i) => r.moyenne === null ? "" : i + 1, width: "50px" },
      { label: "Étudiant", render: (r) => r.inscription.nom + " " + r.inscription.prenom },
    ].concat(programmes.map((p) => ({ label: p.code_matiere, num: true, render: (r) => fmt.note(r.matieres[p.code_matiere]), cls: "small" })))
      .concat([{ label: "Moyenne", num: true, render: (r) => r.moyenne === null ? "—" : el("b", null, fmt.note(r.moyenne)) }]);
    zone.appendChild(el("div", { class: "muted small mb" }, "Moyennes sur 20 pondérées par le poids des évaluations (absents exclus) ; en-têtes = codes matières (" + programmes.map((p) => p.code_matiere + " : " + p.matiere).join(", ") + ")."));
    zone.appendChild(dataTable(colonnes, rows, { empty: "Aucun inscrit." }));
  };
  selectClasse.addEventListener("change", charger);
  selectPeriode.addEventListener("change", charger);
  charger();
  return el("div", null, el("div", { class: "filtres" }, filterField("Classe", selectClasse, "large"), filterField("Période", selectPeriode)), zone);
}
