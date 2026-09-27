/* Vue : dossiers étudiants (recherche, fiche, création, modification, suppression). */
"use strict";

const ETUDIANT_FIELDS = () => [
  { section: "Identité" },
  { name: "matricule", label: "Matricule", type: "readonly", span: 3 },
  { name: "nom", label: "Nom", required: true, span: 5, upper: true },
  { name: "prenom", label: "Prénom(s)", required: true, span: 4 },
  { name: "sexe", label: "Sexe", type: "select", required: true, span: 3, options: [{ value: "M", label: "Masculin" }, { value: "F", label: "Féminin" }] },
  { name: "date_naissance", label: "Date de naissance", type: "date", span: 3 },
  { name: "lieu_naissance", label: "Lieu de naissance", span: 3 },
  { name: "nationalite", label: "Nationalité", span: 3 },
  { name: "cin", label: "CIN", span: 4, help: "12 chiffres, sans espaces." },
  { name: "tel", label: "Téléphone", span: 4 },
  { name: "email", label: "E-mail", span: 4 },
  { name: "adresse", label: "Adresse", span: 12 },
  { section: "Tuteur" },
  { name: "nom_tuteur", label: "Nom du tuteur", span: 4 },
  { name: "tel_tuteur", label: "Téléphone du tuteur", span: 4 },
  { name: "profession_tuteur", label: "Profession", span: 4 },
  { section: "Parcours" },
  { name: "serie_bacc", label: "Série du bac", span: 3 },
  { name: "annee_bacc", label: "Année du bac", type: "number", span: 3, min: 1950, max: 2100, step: "1" },
  { name: "etab_origine", label: "Établissement d’origine", span: 6 },
];

App.register("etudiants", {
  async render(container, { segments, params }) {
    if (segments[0]) { await renderFicheEtudiant(container, Number(segments[0])); return; }
    const state = { q: params.q || "" };
    const zone = el("div");
    const recherche = el("input", { type: "search", placeholder: "Nom, prénom, matricule, CIN…", value: state.q });
    const compteur = el("div", { class: "compteur" });

    const charger = async () => {
      clear(zone); zone.appendChild(loading());
      const rows = await API.value("/api/etudiants" + API.qs({ q: recherche.value.trim() }));
      compteur.textContent = rows.length + " étudiant(s)" + (rows.length >= 500 ? " — affinez la recherche (500 premiers affichés)" : "");
      clear(zone);
      zone.appendChild(dataTable([
        { key: "matricule", label: "Matricule", cls: "mono nowrap" },
        { key: "nom", label: "Nom" },
        { key: "prenom", label: "Prénom(s)" },
        { label: "Sexe", render: (r) => r.sexe || "" },
        { label: "Né(e) le", render: (r) => fmt.date(r.date_naissance), cls: "nowrap" },
        { key: "tel", label: "Téléphone" },
        { key: "cin", label: "CIN" },
        { label: "", cls: "actions", render: (r) => actionButtons([
          { label: "Fiche", onClick: () => App.navigate("etudiants", {}, [r.id_etudiant]) },
          { label: "Modifier", onClick: () => editerEtudiant(r).then((ok) => ok && charger()) },
          App.can("Inscriptions") && { label: "Inscrire", cls: "primaire", onClick: () => inscrireEtudiant(r).then((ok) => ok && charger()) },
        ]) },
      ], rows, { onRow: (r) => App.navigate("etudiants", {}, [r.id_etudiant]), empty: "Aucun étudiant trouvé." }));
    };
    recherche.addEventListener("input", debounce(charger, 250));

    append(container, [
      pageHeader("Étudiants", "Dossiers des étudiants, indépendants des inscriptions annuelles.", [
        button("+ Nouvel étudiant", () => editerEtudiant(null).then((id) => id && App.navigate("etudiants", {}, [id])), "primaire"),
      ]),
      el("div", { class: "filtres" }, filterField("Recherche", recherche, "large")),
      compteur, zone,
    ]);
    await charger();
  },
});

async function editerEtudiant(etudiant) {
  const creation = !etudiant;
  return modal.form({
    title: creation ? "Nouvel étudiant" : "Modifier l’étudiant " + etudiant.matricule,
    fields: ETUDIANT_FIELDS(), values: etudiant || { nationalite: "Malagasy" }, size: "large",
    onSubmit: async (v) => {
      const r = creation ? await API.post("/api/etudiants", v) : await API.put("/api/etudiants/" + etudiant.id_etudiant, v);
      toast.success(r.message);
      return creation ? r.value : true;
    },
  });
}

async function inscrireEtudiant(etudiant, defaults = {}) {
  const classes = App.classesActives();
  if (!classes.length) { toast.warn("Créez d’abord une classe pour l’année active."); return null; }
  return modal.form({
    title: "Inscrire " + etudiant.nom + " " + etudiant.prenom,
    fields: [
      { name: "id_classe", label: "Classe", type: "select", required: true, span: 12, options: classeOptions(classes) },
      { name: "date_inscription", label: "Date d’inscription", type: "date", span: 6, required: true },
      { name: "redoublant", label: "Redoublant", type: "check", span: 6 },
    ],
    values: Object.assign({ date_inscription: fmt.today() }, defaults),
    submitLabel: "Inscrire",
    onSubmit: async (v) => {
      const r = await API.post("/api/inscriptions", Object.assign({ id_etudiant: etudiant.id_etudiant }, v));
      toast.success(r.message);
      return r.value;
    },
  });
}

async function renderFicheEtudiant(container, id) {
  const { etudiant: e, inscriptions } = await API.value("/api/etudiants/" + id);
  const refresh = () => App.refresh();
  const identite = el("dl", { class: "kv" },
    ligneKv("Matricule", e.matricule), ligneKv("Nom complet", e.nom + " " + e.prenom),
    ligneKv("Sexe", e.sexe === "F" ? "Féminin" : e.sexe === "M" ? "Masculin" : "—"),
    ligneKv("Naissance", [fmt.date(e.date_naissance), e.lieu_naissance ? " à " + e.lieu_naissance : ""].join("")),
    ligneKv("Nationalité", e.nationalite), ligneKv("CIN", e.cin), ligneKv("Téléphone", e.tel), ligneKv("E-mail", e.email),
    ligneKv("Adresse", e.adresse), ligneKv("Tuteur", [e.nom_tuteur, e.tel_tuteur, e.profession_tuteur].filter(Boolean).join(" · ")),
    ligneKv("Baccalauréat", [e.serie_bacc, e.annee_bacc].filter(Boolean).join(" — ")), ligneKv("Établissement d’origine", e.etab_origine),
    ligneKv("Dossier créé le", fmt.datetime(e.date_creation)));

  const tableInscriptions = dataTable([
    { key: "num_inscription", label: "N°", cls: "mono nowrap" },
    { key: "classe", label: "Classe" },
    { label: "Date", render: (r) => fmt.date(r.date_inscription) },
    { label: "Redoublant", render: (r) => fmt.bool(r.redoublant) },
    { label: "Statut", render: (r) => fmt.statut(r.statut) },
    { label: "", cls: "actions", render: (r) => actionButtons([
      App.can("Inscriptions") && { label: "Détail", onClick: () => App.navigate("inscriptions", {}, [r.id_inscription]) },
      App.can("Écolage") && { label: "Écolage", onClick: () => App.navigate("ecolage", { inscription: r.id_inscription }, ["etudiant"]) },
    ]) },
  ], inscriptions, { empty: "Aucune inscription." });

  append(container, [
    pageHeader(e.nom + " " + e.prenom, "Matricule " + e.matricule, [
      button("← Liste", () => App.navigate("etudiants")),
      button("Modifier", () => editerEtudiant(e).then((ok) => ok && refresh())),
      App.can("Inscriptions") && button("Inscrire dans une classe", () => inscrireEtudiant(e).then((ok) => ok && refresh()), "primaire"),
      button("Supprimer", async () => {
        if (!await modal.confirm({ title: "Supprimer l’étudiant", message: `Supprimer définitivement le dossier de ${e.nom} ${e.prenom} ? Impossible s’il possède des inscriptions.`, ok: "Supprimer", danger: true })) return;
        try { const r = await API.del("/api/etudiants/" + e.id_etudiant); toast.success(r.message); App.navigate("etudiants"); } catch (ex) { reportError(ex); }
      }, "danger"),
    ]),
    el("div", { class: "grille c2" }, card("Identité", identite), card("Inscriptions", tableInscriptions)),
  ]);
}

function ligneKv(label, value) {
  return [el("dt", null, label), el("dd", null, value === null || value === undefined || value === "" ? "—" : value)];
}
