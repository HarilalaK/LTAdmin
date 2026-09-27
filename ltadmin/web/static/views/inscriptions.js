/* Vue : inscriptions par classe (liste, nouvelle inscription, sortie, modification). */
"use strict";

App.register("inscriptions", {
  async render(container, { segments, params }) {
    if (segments[0]) { await renderDetailInscription(container, Number(segments[0])); return; }
    const classes = App.classesActives();
    const selectClasse = selectInput(classeOptions(classes), params.classe || (classes[0] && classes[0].id_classe), { placeholder: "— Choisir une classe —" });
    const statutFiltre = selectInput([{ value: "", label: "Tous" }, { value: "INSCRIT", label: "Inscrits" }, { value: "SORTI", label: "Sortis" }], params.statut || "");
    const zone = el("div");
    const compteur = el("div", { class: "compteur" });

    const charger = async () => {
      const id = selectClasse.value;
      clear(zone);
      if (!id) { zone.appendChild(el("div", { class: "info" }, "Choisissez une classe pour afficher ses inscrits.")); return; }
      zone.appendChild(loading());
      let rows = await API.value("/api/inscriptions" + API.qs({ classe: id }));
      if (statutFiltre.value) rows = rows.filter((r) => r.statut === statutFiltre.value);
      const classe = App.classe(id);
      compteur.textContent = rows.length + " inscription(s)" + (classe && classe.effectif_max ? " — capacité " + classe.effectif_max : "");
      clear(zone);
      zone.appendChild(dataTable([
        { key: "num_inscription", label: "N°", cls: "mono nowrap" },
        { key: "matricule", label: "Matricule", cls: "mono nowrap" },
        { key: "nom", label: "Nom" },
        { key: "prenom", label: "Prénom(s)" },
        { label: "Date", render: (r) => fmt.date(r.date_inscription), cls: "nowrap" },
        { label: "Redoublant", render: (r) => fmt.bool(r.redoublant) },
        { label: "Statut", render: (r) => fmt.statut(r.statut) },
        { label: "Sortie", render: (r) => r.date_sortie ? fmt.date(r.date_sortie) + (r.motif_sortie ? " — " + r.motif_sortie : "") : "" },
        { label: "", cls: "actions", render: (r) => actionButtons([
          { label: "Détail", onClick: () => App.navigate("inscriptions", {}, [r.id_inscription]) },
          r.statut !== "SORTI" && { label: "Sortie", cls: "danger", onClick: () => enregistrerSortie(r).then((ok) => ok && charger()) },
        ]) },
      ], rows, { onRow: (r) => App.navigate("inscriptions", {}, [r.id_inscription]), empty: "Aucune inscription dans cette classe." }));
    };
    selectClasse.addEventListener("change", charger);
    statutFiltre.addEventListener("change", charger);

    append(container, [
      pageHeader("Inscriptions", "Affectation des étudiants aux classes de l’année.", [
        button("+ Nouvelle inscription", () => nouvelleInscription(selectClasse.value).then((ok) => ok && charger()), "primaire"),
      ]),
      el("div", { class: "filtres" }, filterField("Classe", selectClasse, "large"), filterField("Statut", statutFiltre)),
      compteur, zone,
    ]);
    await charger();
  },
});

async function nouvelleInscription(idClasse) {
  // Étape 1 : choisir l'étudiant (recherche), étape 2 : formulaire d'inscription.
  return new Promise((resolve) => {
    const recherche = el("input", { type: "search", placeholder: "Nom, prénom ou matricule…" });
    const resultats = el("div", { class: "mt" });
    let handle, suite = null;
    const fermer = (action) => { suite = action; handle.close(); };
    const chercher = debounce(async () => {
      const q = recherche.value.trim();
      clear(resultats);
      if (q.length < 2) { resultats.appendChild(el("div", { class: "muted small" }, "Saisissez au moins 2 caractères.")); return; }
      const rows = await API.value("/api/etudiants" + API.qs({ q, max: 30 }));
      clear(resultats);
      resultats.appendChild(dataTable([
        { key: "matricule", label: "Matricule", cls: "mono" }, { key: "nom", label: "Nom" }, { key: "prenom", label: "Prénom(s)" },
        { label: "Né(e) le", render: (r) => fmt.date(r.date_naissance) },
        { label: "", cls: "actions", render: (r) => button("Choisir", () => fermer(() => inscrireEtudiant(r, { id_classe: idClasse || undefined })), "petit primaire") },
      ], rows, { empty: "Aucun étudiant ne correspond." }));
    }, 250);
    recherche.addEventListener("input", chercher);
    handle = modal.open({
      title: "Nouvelle inscription — choisir l’étudiant",
      body: el("div", null,
        el("div", { class: "champ" }, el("label", null, "Rechercher un étudiant existant"), recherche),
        resultats,
        el("div", { class: "mt small muted" }, "L’étudiant n’existe pas encore ? ",
          button("Créer un nouveau dossier", () => fermer(async () => {
            const id = await editerEtudiant(null);
            if (!id) return null;
            const { etudiant } = await API.value("/api/etudiants/" + id);
            return inscrireEtudiant(etudiant, { id_classe: idClasse || undefined });
          }), "lien"))),
      onClose: async () => resolve(suite ? await suite() : null),
    });
    resultats.appendChild(el("div", { class: "muted small" }, "Saisissez au moins 2 caractères."));
  });
}

async function enregistrerSortie(inscription) {
  return modal.form({
    title: "Sortie de " + inscription.nom + " " + inscription.prenom, size: "etroite",
    fields: [
      { name: "date_sortie", label: "Date de sortie", type: "date", required: true, span: 12 },
      { name: "motif_sortie", label: "Motif", type: "select", required: true, span: 12, options: ["Abandon", "Transfert", "Exclusion", "Raison familiale", "Raison de santé", "Autre"] },
    ],
    values: { date_sortie: fmt.today() }, submitLabel: "Enregistrer la sortie",
    onSubmit: async (v) => { const r = await API.post(`/api/inscriptions/${inscription.id_inscription}/sortie`, v); toast.success(r.message); },
  });
}

async function modifierInscription(i) {
  return modal.form({
    title: "Modifier l’inscription " + i.num_inscription, size: "etroite",
    fields: [
      { name: "id_classe", label: "Classe", type: "select", required: true, span: 12, options: classeOptions(App.ref.classes) },
      { name: "date_inscription", label: "Date d’inscription", type: "date", required: true, span: 12 },
      { name: "redoublant", label: "Redoublant", type: "check", span: 6 },
      { name: "statut", label: "Statut", type: "select", span: 6, options: ["INSCRIT", "SORTI"], required: true },
    ],
    values: i,
    onSubmit: async (v) => { const r = await API.put("/api/inscriptions/" + i.id_inscription, v); toast.success(r.message); },
  });
}

async function renderDetailInscription(container, id) {
  const i = await API.value("/api/inscriptions/" + id);
  const refresh = () => App.refresh();
  const sections = [];
  const infos = el("dl", { class: "kv" },
    ligneKv("N° d’inscription", i.num_inscription), ligneKv("Étudiant", i.nom + " " + i.prenom + " (" + i.matricule + ")"),
    ligneKv("Classe", i.classe), ligneKv("Date", fmt.date(i.date_inscription)), ligneKv("Redoublant", fmt.bool(i.redoublant)),
    ligneKv("Statut", fmt.statut(i.statut)), ligneKv("Sortie", i.date_sortie ? fmt.date(i.date_sortie) + " — " + (i.motif_sortie || "") : "—"));
  sections.push(card("Inscription", infos));

  if (App.can("Absences")) {
    const abs = await API.value("/api/absences" + API.qs({ inscription: id }));
    sections.push(card("Absences (" + fmt.hours(abs.total_heures) + ")", dataTable([
      { label: "Saisie le", render: (r) => fmt.datetime(r.date_saisie), cls: "nowrap" },
      { key: "nature", label: "Nature" }, { label: "Heures", num: true, render: (r) => fmt.number(r.nb_heures, 1) },
      { label: "Justifiée", render: (r) => fmt.oui(r.justifiee) }, { key: "motif", label: "Motif" },
    ], abs.absences, { empty: "Aucune absence." })));
  }
  if (App.can("Écolage")) {
    const eco = await API.value(`/api/inscriptions/${id}/echeances`);
    sections.push(card("Écolage", el("div", null,
      el("div", { class: "flex wrap mb" },
        el("span", { class: "badge bleu" }, "Dû : " + fmt.money(eco.total_du)),
        el("span", { class: "badge vert" }, "Payé : " + fmt.money(eco.total_paye)),
        el("span", { class: "badge " + (Number(eco.reste) > 0 ? "rouge" : "vert") }, "Reste : " + fmt.money(eco.reste))),
      dataTable([
        { key: "libelle", label: "Échéance" }, { label: "Échéance le", render: (r) => fmt.date(r.date_echeance), cls: "nowrap" },
        { label: "Net dû", num: true, render: (r) => fmt.money(r.net_du, "") }, { label: "Payé", num: true, render: (r) => fmt.money(r.total_paye, "") },
        { label: "Reste", num: true, render: (r) => fmt.money(r.reste, "") }, { label: "Statut", render: (r) => fmt.statut(r.statut) },
      ], eco.echeances, { empty: "Aucun échéancier généré." })),
      [button("Ouvrir l’écolage", () => App.navigate("ecolage", { inscription: id }, ["etudiant"]), "petit")]));
  }

  append(container, [
    pageHeader("Inscription " + i.num_inscription, i.nom + " " + i.prenom + " — " + i.classe, [
      button("← Liste", () => App.navigate("inscriptions", { classe: i.id_classe })),
      App.can("Étudiants") && button("Dossier étudiant", () => App.navigate("etudiants", {}, [i.id_etudiant])),
      button("Modifier", () => modifierInscription(i).then((ok) => ok && refresh())),
      i.statut !== "SORTI" && button("Enregistrer une sortie", () => enregistrerSortie(i).then((ok) => ok && refresh()), "danger"),
      button("Supprimer", async () => {
        if (!await modal.confirm({ title: "Supprimer l’inscription", message: "Supprimer cette inscription ? Impossible si des notes, absences ou paiements y sont rattachés.", ok: "Supprimer", danger: true })) return;
        try { const r = await API.del("/api/inscriptions/" + id); toast.success(r.message); App.navigate("inscriptions", { classe: i.id_classe }); } catch (ex) { reportError(ex); }
      }, "danger"),
    ]),
    el("div", { class: "stack" }, sections),
  ]);
}
