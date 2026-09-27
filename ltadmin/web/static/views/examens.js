/* Vue : sessions d'examen, épreuves, notes d'examen et résultats finaux. */
"use strict";

App.register("examens", {
  async render(container, { params, segments }) {
    if (segments[0] === "saisie" && segments[1]) { await renderSaisieExamen(container, Number(segments[1])); return; }
    const onglets = [{ key: "epreuves", label: "Épreuves et notes" }, { key: "resultats", label: "Résultats finaux" }, { key: "sessions", label: "Sessions" }];
    let actif = onglets.some((o) => o.key === params.onglet) ? params.onglet : "epreuves";
    const barre = el("div"), corps = el("div");
    const afficher = () => {
      clear(barre); barre.appendChild(tabs(onglets, actif, (k) => { actif = k; history.replaceState(null, "", "#/examens?onglet=" + k); afficher(); }));
      clear(corps);
      corps.appendChild(actif === "epreuves" ? sectionEpreuves(params) : actif === "resultats" ? sectionResultats(params) : sectionSessions());
    };
    const cc = App.param("POIDS_CC", 40), ex = App.param("POIDS_EXAMEN", 60), adm = App.param("MOY_ADMISSION", 10);
    append(container, [pageHeader("Examens", `Résultat final = ${cc} % contrôle continu + ${ex} % examen · admission à partir de ${adm}/20 (paramètres).`), barre, corps]);
    afficher();
  },
});

function sessionOptions() {
  return App.ref.sessions.map((s) => ({ value: s.id_session, label: s.libelle + (s.cloturee ? " (clôturée)" : "") }));
}

function sectionSessions() {
  return crudSection({
    title: "Sessions d’examen", singular: "session", url: "/api/sessions", idKey: "id_session", label: (r) => r.libelle,
    description: "Une session regroupe les épreuves d’une période d’examen (ex. Session de juin).",
    load: async () => API.value("/api/sessions"),
    columns: [
      { key: "libelle", label: "Libellé" }, { key: "nature", label: "Nature" },
      { label: "Du", render: (r) => fmt.date(r.date_debut) }, { label: "Au", render: (r) => fmt.date(r.date_fin) },
      { label: "État", render: (r) => button(r.cloturee ? "Clôturée — rouvrir" : "Ouverte — clôturer", async () => {
        try { const x = await API.post(`/api/sessions/${r.id_session}/cloture`, { cloturee: !r.cloturee }); toast.success(x.message); App.invalidateRef(); await App.loadRef(true); App.refresh(); } catch (ex) { reportError(ex); }
      }, "petit " + (r.cloturee ? "danger" : "")) },
    ],
    fields: () => [
      { name: "id_annee", label: "Année scolaire", type: "select", required: true, span: 12, options: App.ref.annees.map((a) => ({ value: a.id_annee, label: a.libelle })) },
      { name: "libelle", label: "Libellé", required: true, span: 8, placeholder: "Session de juin 2026" },
      { name: "nature", label: "Nature", type: "select", span: 4, options: ["Normale", "Rattrapage", "Blanc"] },
      { name: "date_debut", label: "Début", type: "date", span: 6 }, { name: "date_fin", label: "Fin", type: "date", span: 6 },
    ],
    defaults: () => ({ id_annee: App.session.annee_active ? App.session.annee_active.id_annee : null, nature: "Normale" }),
    afterSave: () => App.invalidateRef(),
  });
}

function sectionEpreuves(params) {
  const classes = App.classesActives();
  const selectSession = selectInput(sessionOptions(), params.session || (App.ref.sessions[0] && App.ref.sessions[0].id_session), { placeholder: "— Session —" });
  const selectClasse = selectInput(classeOptions(classes), params.classe || "", { placeholder: "Toutes les classes" });
  const zone = el("div");
  const charger = async () => {
    clear(zone);
    if (!selectSession.value) { zone.appendChild(el("div", { class: "info" }, App.ref.sessions.length ? "Choisissez une session." : "Créez d’abord une session d’examen (onglet Sessions).")); return; }
    zone.appendChild(loading());
    const rows = await API.value("/api/epreuves" + API.qs({ session: selectSession.value, classe: selectClasse.value }));
    clear(zone);
    zone.appendChild(dataTable([
      { key: "classe", label: "Classe" }, { key: "matiere", label: "Matière" },
      { label: "Date", render: (r) => fmt.date(r.date_epreuve), cls: "nowrap" }, { key: "heure_debut", label: "Heure" }, { label: "Durée", render: (r) => r.duree_mn ? r.duree_mn + " min" : "" },
      { label: "Coef.", num: true, render: (r) => fmt.number(r.coefficient, 1) }, { label: "Barème", num: true, render: (r) => fmt.number(r.bareme, 0) },
      { key: "salle", label: "Salle" }, { key: "surveillant", label: "Surveillant" },
      { label: "", cls: "actions", render: (r) => actionButtons([
        { label: "Saisir les notes", cls: "primaire", onClick: () => App.navigate("examens", {}, ["saisie", r.id_epreuve]) },
        { label: "Modifier", onClick: () => editerEpreuve(r, selectSession.value).then((ok) => ok && charger()) },
        { label: "Supprimer", cls: "danger", onClick: async () => {
          if (!await modal.confirm({ title: "Supprimer l’épreuve", message: `Supprimer l’épreuve « ${r.matiere} — ${r.classe} » et ses notes ?`, ok: "Supprimer", danger: true })) return;
          try { const x = await API.del("/api/epreuves/" + r.id_epreuve); toast.success(x.message); charger(); } catch (ex) { reportError(ex); }
        } },
      ]) },
    ], rows, { empty: "Aucune épreuve planifiée.", onRow: (r) => App.navigate("examens", {}, ["saisie", r.id_epreuve]) }));
  };
  selectSession.addEventListener("change", charger);
  selectClasse.addEventListener("change", charger);
  charger();
  return el("div", null,
    el("div", { class: "filtres" }, filterField("Session", selectSession, "large"), filterField("Classe", selectClasse, "large"), el("div", { class: "grow" }),
      button("+ Nouvelle épreuve", () => { if (!selectSession.value) { toast.warn("Choisissez une session."); return; } editerEpreuve(null, selectSession.value, selectClasse.value).then((ok) => ok && charger()); }, "primaire")),
    zone);
}

async function editerEpreuve(e, idSession, idClasse) {
  const creation = !e;
  return modal.form({
    title: creation ? "Nouvelle épreuve" : "Modifier l’épreuve",
    fields: [
      { name: "id_session", label: "Session", type: "select", required: true, span: 6, options: sessionOptions() },
      { name: "id_classe", label: "Classe", type: "select", required: true, span: 6, options: classeOptions(App.ref.classes) },
      { name: "code_matiere", label: "Matière", type: "select", required: true, span: 12, options: App.ref.matieres.map((m) => ({ value: m.code_matiere, label: m.libelle + " (" + m.code_matiere + ")" })) },
      { name: "date_epreuve", label: "Date", type: "date", span: 4 }, { name: "heure_debut", label: "Heure de début", span: 4, placeholder: "08:00" },
      { name: "duree_mn", label: "Durée (minutes)", type: "number", span: 4, min: 15, step: "15" },
      { name: "coefficient", label: "Coefficient", type: "number", required: true, span: 4, min: 0.5, step: "0.5" },
      { name: "bareme", label: "Barème", type: "number", required: true, span: 4, min: 1, step: "1" },
      { name: "id_salle", label: "Salle", type: "select", span: 4, options: App.ref.salles.map((s) => ({ value: s.id_salle, label: s.nom_salle })) },
      { name: "surveillant", label: "Surveillant", span: 12 },
    ],
    values: e || { id_session: Number(idSession), id_classe: idClasse ? Number(idClasse) : undefined, coefficient: 1, bareme: Number(App.param("BAREME_DEFAUT", 20)), duree_mn: 120 },
    onSubmit: async (v) => { const r = await API.post("/api/epreuves", creation ? v : Object.assign({}, v, { id_epreuve: e.id_epreuve })); toast.success(r.message); },
  });
}

async function renderSaisieExamen(container, id) {
  const { epreuve: e, notes } = await API.value("/api/epreuves/" + id);
  const bareme = e.bareme || 20;
  const lignes = notes.map((n) => Object.assign({}, n));
  const table = dataTable([
    { label: "#", render: (r, i) => i + 1, width: "40px" },
    { key: "matricule", label: "Matricule", cls: "mono nowrap" }, { key: "nom", label: "Nom" }, { key: "prenom", label: "Prénom(s)" },
    { label: "N° de copie", render: (r) => { const i = el("input", { type: "text", value: r.observation || "", style: { width: "110px" } }); i.addEventListener("input", () => { r.observation = i.value; r._modifie = true; }); return i; } },
    { label: "Note / " + bareme, num: true, render: (r) => {
      const input = el("input", { type: "number", class: "note", min: 0, max: bareme, step: "0.25", value: r.valeur_note === null ? "" : r.valeur_note, disabled: r.absent });
      input.addEventListener("input", () => { r.valeur_note = input.value === "" ? null : Number(input.value); r._modifie = true; });
      input.addEventListener("keydown", (ev) => { if (ev.key === "Enter") { ev.preventDefault(); const all = [...table.querySelectorAll("input.note")]; const idx = all.indexOf(input); if (all[idx + 1]) all[idx + 1].focus(); } });
      r._input = input; return input;
    } },
    { label: "Absent", render: (r) => { const cb = el("input", { type: "checkbox", checked: r.absent }); cb.addEventListener("change", () => { r.absent = cb.checked; r._modifie = true; if (cb.checked) { r.valeur_note = null; r._input.value = ""; } r._input.disabled = cb.checked; }); return cb; } },
  ], lignes, { empty: "Aucun inscrit dans cette classe." });
  const enregistrer = async () => {
    const modifiees = lignes.filter((l) => l._modifie);
    if (!modifiees.length) { toast.info("Aucune modification."); return; }
    try {
      const r = await API.post(`/api/epreuves/${id}/notes`, { notes: modifiees.map((l) => ({ id_inscription: l.id_inscription, valeur_note: l.valeur_note, absent: l.absent, copie_num: l.observation })) });
      if (r.value.erreurs.length) { toast.warn(r.message); modal.open({ title: "Notes non enregistrées", body: el("ul", null, r.value.erreurs.map((x) => el("li", null, x))) }); } else toast.success(r.message);
      modifiees.forEach((l) => { l._modifie = false; });
    } catch (ex) { reportError(ex); }
  };
  append(container, [
    pageHeader("Notes d’examen — " + e.matiere, `${e.session} · ${e.classe} · ${fmt.date(e.date_epreuve)} ${e.heure_debut || ""} · coef. ${fmt.number(e.coefficient, 1)} · barème ${bareme}`, [
      button("← Épreuves", () => App.navigate("examens", { session: e.id_session, classe: e.id_classe })),
      button("Enregistrer les notes", enregistrer, "primaire"),
    ]),
    el("div", { class: "info mb" }, "Le numéro de copie est facultatif (anonymat). Une note hors barème est refusée."),
    table,
  ]);
}

function sectionResultats(params) {
  const classes = App.classesActives();
  const selectClasse = selectInput(classeOptions(classes), params.classe || (classes[0] && classes[0].id_classe), { placeholder: "— Classe —" });
  const selectSession = selectInput(sessionOptions(), params.session || (App.ref.sessions[0] && App.ref.sessions[0].id_session), { placeholder: "— Session —" });
  const zone = el("div");
  const charger = async () => {
    clear(zone);
    if (!selectClasse.value) { zone.appendChild(el("div", { class: "info" }, "Choisissez une classe.")); return; }
    zone.appendChild(loading());
    const rows = await API.value("/api/resultats" + API.qs({ classe: selectClasse.value }));
    clear(zone);
    const admis = rows.filter((r) => r.resultat.decision === "ADMIS").length;
    zone.appendChild(el("div", { class: "flex wrap mb" }, el("span", { class: "badge bleu" }, rows.length + " résultat(s)"), el("span", { class: "badge vert" }, admis + " admis"), el("span", { class: "badge rouge" }, (rows.length - admis) + " ajournés")));
    zone.appendChild(dataTable([
      { label: "Rang", render: (r) => r.resultat.rang || "", width: "60px" },
      { key: "matricule", label: "Matricule", cls: "mono nowrap" }, { key: "nom", label: "Nom" }, { key: "prenom", label: "Prénom(s)" },
      { label: "Moy. CC", num: true, render: (r) => fmt.note(r.resultat.moy_cc) }, { label: "Moy. examen", num: true, render: (r) => fmt.note(r.resultat.moy_exam) },
      { label: "Moyenne générale", num: true, render: (r) => el("b", null, fmt.note(r.resultat.moyenne_gen)) },
      { label: "Mention", render: (r) => r.resultat.mention ? el("span", { class: "badge " + (r.resultat.decision === "ADMIS" ? "vert" : "rouge") }, r.resultat.mention) : "" },
      { label: "Décision", render: (r) => fmt.statut(r.resultat.decision) },
    ], rows, { empty: "Aucun résultat généré pour cette classe." }));
    if (rows.length) zone.appendChild(el("div", { class: "mt" }, button("Imprimer le procès-verbal", () => imprimerPV(rows, App.classe(selectClasse.value)), "")));
  };
  selectClasse.addEventListener("change", charger);
  charger();
  return el("div", null,
    el("div", { class: "filtres" }, filterField("Classe", selectClasse, "large"), filterField("Session (pour la génération)", selectSession, "large"), el("div", { class: "grow" }),
      button("Générer les résultats", async () => {
        if (!selectClasse.value || !selectSession.value) { toast.warn("Choisissez une classe et une session."); return; }
        if (!await modal.confirm({ title: "Générer les résultats finaux", message: "Calculer les moyennes finales (CC + examen), rangs, mentions et décisions pour la classe ? Les résultats existants sont remplacés.", ok: "Générer" })) return;
        try { const r = await API.post("/api/resultats/generer", { id_classe: Number(selectClasse.value), id_session: Number(selectSession.value) }); toast.success(r.message); charger(); } catch (ex) { reportError(ex); }
      }, "primaire")),
    zone);
}

async function imprimerPV(rows, classe) {
  const etab = App.session.etablissement || {};
  printDocument(el("div", { class: "document" },
    enteteDocument(etab),
    el("h2", { class: "titre-doc" }, "Procès-verbal des résultats — " + (classe ? classe.libelle : "")),
    el("p", null, "Année scolaire " + (App.session.annee_active ? App.session.annee_active.libelle : "") + " · pondération : " + App.param("POIDS_CC", 40) + " % CC / " + App.param("POIDS_EXAMEN", 60) + " % examen · seuil d’admission " + App.param("MOY_ADMISSION", 10) + "/20."),
    el("table", null,
      el("thead", null, el("tr", null, ["Rang", "Matricule", "Nom et prénom(s)", "Moy. CC", "Moy. examen", "Moy. générale", "Mention", "Décision"].map((h) => el("th", null, h)))),
      el("tbody", null, rows.map((r) => el("tr", null, el("td", { class: "num" }, r.resultat.rang || ""), el("td", null, r.matricule || ""), el("td", null, (r.nom || "") + " " + (r.prenom || "")),
        el("td", { class: "num" }, fmt.note(r.resultat.moy_cc)), el("td", { class: "num" }, fmt.note(r.resultat.moy_exam)), el("td", { class: "num" }, el("b", null, fmt.note(r.resultat.moyenne_gen))),
        el("td", null, r.resultat.mention || ""), el("td", null, r.resultat.decision || ""))))),
    el("div", { class: "signature" }, el("div", null, "Le président du jury", el("div", { class: "trait" }, "")), el("div", null, etab.directeur ? "Le directeur, " + etab.directeur : "Le directeur", el("div", { class: "trait" }, "")))));
}
