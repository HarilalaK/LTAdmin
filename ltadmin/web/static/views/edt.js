/* Vue : emploi du temps (grille hebdomadaire), créneaux horaires, séances (cahier de texte). */
"use strict";

const JOURS_EDT = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"];
const STATUTS_SEANCE = ["FAITE", "PLANIFIEE", "REPORTEE", "ANNULEE"];

App.register("edt", {
  async render(container, { params }) {
    const onglets = [{ key: "grille", label: "Emploi du temps" }, { key: "seances", label: "Séances (cahier de texte)" }, { key: "creneaux", label: "Créneaux horaires" }];
    let actif = onglets.some((o) => o.key === params.onglet) ? params.onglet : "grille";
    const barre = el("div"), corps = el("div");
    const afficher = () => {
      clear(barre); barre.appendChild(tabs(onglets, actif, (k) => { actif = k; history.replaceState(null, "", "#/edt?onglet=" + k); afficher(); }));
      clear(corps);
      corps.appendChild(actif === "grille" ? sectionGrilleEdt(params) : actif === "seances" ? sectionSeances(params) : sectionCreneaux());
    };
    append(container, [pageHeader("Emploi du temps", "Planification hebdomadaire par classe, avec contrôle des conflits de salle, de formateur et de classe."), barre, corps]);
    afficher();
  },
});

function sectionCreneaux() {
  return crudSection({
    title: "Créneaux horaires", singular: "créneau", url: "/api/creneaux", idKey: "id_creneau", label: (r) => r.libelle,
    description: "Plages horaires communes à toutes les classes (ex. C1 : 07:30 – 09:30).",
    load: async () => API.value("/api/creneaux"),
    columns: [{ key: "libelle", label: "Libellé" }, { key: "heure_debut", label: "Début" }, { key: "heure_fin", label: "Fin" }, { key: "ordre_cre", label: "Ordre", num: true }],
    fields: () => [
      { name: "libelle", label: "Libellé", required: true, span: 6 }, { name: "ordre_cre", label: "Ordre", type: "number", span: 6, step: "1" },
      { name: "heure_debut", label: "Heure de début", required: true, span: 6, placeholder: "07:30" }, { name: "heure_fin", label: "Heure de fin", required: true, span: 6, placeholder: "09:30" },
    ],
    afterSave: () => App.invalidateRef(),
  });
}

function sectionGrilleEdt(params) {
  const classes = App.classesActives();
  const selectClasse = selectInput(classeOptions(classes), params.classe || (classes[0] && classes[0].id_classe), { placeholder: "— Classe —" });
  const zone = el("div");
  const charger = async () => {
    clear(zone);
    if (!selectClasse.value) { zone.appendChild(el("div", { class: "info" }, "Choisissez une classe.")); return; }
    zone.appendChild(loading());
    const slots = await API.value("/api/edt" + API.qs({ classe: selectClasse.value }));
    const creneaux = [...App.ref.creneaux].sort((a, b) => (a.ordre_cre || 0) - (b.ordre_cre || 0));
    clear(zone);
    if (!creneaux.length) { zone.appendChild(el("div", { class: "avert" }, "Définissez d’abord des créneaux horaires (onglet Créneaux).")); return; }
    const grille = el("div", { class: "edt-grille" });
    grille.appendChild(el("div", { class: "cellule entete" }, "Créneau"));
    JOURS_EDT.forEach((j) => grille.appendChild(el("div", { class: "cellule entete" }, j)));
    creneaux.forEach((c) => {
      grille.appendChild(el("div", { class: "cellule creneau" }, c.libelle, el("div", { class: "small muted" }, (c.heure_debut || "") + " – " + (c.heure_fin || ""))));
      JOURS_EDT.forEach((j) => {
        const cellule = el("div", { class: "cellule" });
        slots.filter((s) => s.id_creneau === c.id_creneau && String(s.jour || "").toLowerCase() === j.toLowerCase()).forEach((s) => {
          cellule.appendChild(el("div", { class: "cours", style: s.actif === false ? { opacity: .5 } : null, onClick: () => detailSlot(s).then((changed) => changed && charger()) },
            el("div", { class: "matiere" }, s.matiere), el("div", { class: "detail" }, s.formateur || "—"), el("div", { class: "detail" }, s.salle || "Salle non définie")));
        });
        cellule.appendChild(button("+", () => editerSlot(null, selectClasse.value, { jour: j, id_creneau: c.id_creneau }).then((ok) => ok && charger()), "petit lien", { title: "Planifier un cours" }));
        grille.appendChild(cellule);
      });
    });
    zone.appendChild(grille);
    zone.appendChild(el("div", { class: "mt" }, button("Imprimer l’emploi du temps", () => imprimerEdt(App.classe(selectClasse.value), slots, creneaux))));
  };
  selectClasse.addEventListener("change", charger);
  charger();
  return el("div", null,
    el("div", { class: "filtres" }, filterField("Classe", selectClasse, "large"), el("div", { class: "grow" }),
      button("+ Planifier un cours", () => { if (!selectClasse.value) { toast.warn("Choisissez une classe."); return; } editerSlot(null, selectClasse.value).then((ok) => ok && charger()); }, "primaire")),
    zone);
}

async function editerSlot(s, idClasse, defaults = {}) {
  const creation = !s;
  const programmes = await API.value("/api/programmes" + API.qs({ classe: idClasse }));
  if (!programmes.length) { toast.warn("Aucune matière au programme de cette classe : complétez le programme (menu Formateurs)."); return null; }
  return modal.form({
    title: creation ? "Planifier un cours" : "Modifier le cours",
    fields: [
      { name: "id_prog", label: "Matière — formateur", type: "select", required: true, span: 12, options: programmes.map((p) => ({ value: p.id_prog, label: p.matiere + " — " + p.formateur })) },
      { name: "jour", label: "Jour", type: "select", required: true, span: 4, options: JOURS_EDT },
      { name: "id_creneau", label: "Créneau", type: "select", required: true, span: 4, options: App.ref.creneaux.map((c) => ({ value: c.id_creneau, label: c.libelle + " (" + c.heure_debut + "–" + c.heure_fin + ")" })) },
      { name: "id_salle", label: "Salle", type: "select", span: 4, options: App.ref.salles.filter((x) => x.disponible !== false).map((x) => ({ value: x.id_salle, label: x.nom_salle })) },
      { name: "date_debut", label: "Valable du", type: "date", span: 4 }, { name: "date_fin", label: "au", type: "date", span: 4 },
      { name: "actif", label: "Actif", type: "check", span: 4 },
    ],
    values: s || Object.assign({ actif: true, date_debut: fmt.today() }, defaults),
    onSubmit: async (v) => { const r = await API.post("/api/edt", creation ? v : Object.assign({}, v, { id_edt: s.id_edt })); toast.success(r.message); },
  });
}

async function detailSlot(s) {
  return new Promise(async (resolve) => {
    let handle, suite = null;  // suite : action différée après fermeture
    const { seances } = await API.value("/api/edt/" + s.id_edt);
    const fermer = (action) => { suite = action; handle.close(); };
    const corps = el("div", null,
      el("dl", { class: "kv mb" }, ligneKv("Classe", s.classe), ligneKv("Matière", s.matiere), ligneKv("Formateur", s.formateur), ligneKv("Créneau", `${s.jour} · ${s.creneau} (${s.heure_debut}–${s.heure_fin})`), ligneKv("Salle", s.salle), ligneKv("Validité", (s.date_debut ? "du " + fmt.date(s.date_debut) : "") + (s.date_fin ? " au " + fmt.date(s.date_fin) : "")), ligneKv("Actif", fmt.oui(s.actif))),
      el("h3", { class: "mb" }, "Séances réalisées (" + seances.length + ")"),
      dataTable([{ label: "Date", render: (r) => fmt.date(r.date_seance) }, { key: "contenu", label: "Contenu" }, { label: "Heures", num: true, render: (r) => fmt.number(r.nb_heures, 1) }, { label: "Statut", render: (r) => fmt.statut(r.statut) }], seances.slice(0, 15), { empty: "Aucune séance enregistrée." }));
    handle = modal.open({
      title: "Cours — " + s.matiere, body: corps, size: "",
      actions: [
        button("Supprimer", async () => {
          if (!await modal.confirm({ title: "Supprimer le cours", message: "Retirer ce cours de l’emploi du temps ? Refusé si des séances y sont rattachées (désactivez-le plutôt).", ok: "Supprimer", danger: true })) return;
          try { const r = await API.del("/api/edt/" + s.id_edt); toast.success(r.message); fermer(async () => true); } catch (ex) { reportError(ex); }
        }, "danger"),
        button("Modifier", () => fermer(async () => !!(await editerSlot(s, s.id_classe)))),
        button("+ Séance", () => fermer(async () => !!(await editerSeance(null, s))), "primaire"),
        button("Fermer", () => fermer(null)),
      ],
      onClose: async () => resolve(suite ? await suite() : false),
    });
  });
}

async function editerSeance(seance, slot) {
  const creation = !seance;
  const duree = slot && slot.heure_debut && slot.heure_fin ? dureeHeures(slot.heure_debut, slot.heure_fin) : 2;
  return modal.form({
    title: creation ? "Nouvelle séance — " + (slot ? slot.matiere : "") : "Modifier la séance",
    fields: [
      { name: "date_seance", label: "Date", type: "date", required: true, span: 4 },
      { name: "nb_heures", label: "Heures", type: "number", required: true, span: 4, min: 0, step: "0.5" },
      { name: "statut", label: "Statut", type: "select", required: true, span: 4, options: STATUTS_SEANCE },
      { name: "contenu", label: "Contenu (cahier de texte)", type: "textarea", span: 12, rows: 4 },
      { name: "id_formateur_remp", label: "Formateur remplaçant", type: "select", span: 12, options: App.ref.formateurs.map((f) => ({ value: f.id_formateur, label: f.nom_complet })) },
    ],
    values: seance || { date_seance: fmt.today(), nb_heures: duree, statut: "FAITE" },
    onSubmit: async (v) => { const r = await API.post("/api/seances", Object.assign(creation ? { id_edt: slot.id_edt } : { id_seance: seance.id_seance, id_edt: seance.id_edt }, v)); toast.success(r.message); },
  });
}

function dureeHeures(debut, fin) {
  const [h1, m1] = String(debut).split(":").map(Number), [h2, m2] = String(fin).split(":").map(Number);
  if ([h1, m1, h2, m2].some((x) => Number.isNaN(x))) return 2;
  return Math.max(0, Math.round(((h2 * 60 + m2) - (h1 * 60 + m1)) / 30) / 2);
}

function sectionSeances(params) {
  const classes = App.classesActives();
  const selectClasse = selectInput(classeOptions(classes), params.classe || "", { placeholder: "Toutes les classes" });
  const debut = el("input", { type: "date", value: params.debut || fmt.isoDate(new Date(Date.now() - 30 * 86400000).toISOString()) });
  const fin = el("input", { type: "date", value: params.fin || fmt.today() });
  const zone = el("div");
  const charger = async () => {
    clear(zone); zone.appendChild(loading());
    const rows = await API.value("/api/seances" + API.qs({ classe: selectClasse.value, debut: debut.value, fin: fin.value }));
    clear(zone);
    const total = rows.reduce((s, r) => s + (r.nb_heures || 0), 0);
    zone.appendChild(el("div", { class: "compteur" }, rows.length + " séance(s) · " + fmt.hours(total)));
    zone.appendChild(dataTable([
      { label: "Date", render: (r) => fmt.date(r.date_seance), cls: "nowrap" }, { key: "classe", label: "Classe" }, { key: "matiere", label: "Matière" },
      { label: "Créneau", render: (r) => (r.jour || "") + " " + (r.creneau || "") }, { label: "Heures", num: true, render: (r) => fmt.number(r.nb_heures, 1) },
      { label: "Statut", render: (r) => fmt.statut(r.statut) },
      { label: "", cls: "actions", render: (r) => actionButtons([
        App.can("Absences") && { label: "Absences", onClick: () => App.navigate("absences", { seance: r.id_seance }) },
        { label: "Modifier", onClick: async () => { const s = await API.value("/api/seances/" + r.id_seance); if (await editerSeance(s.seance, s.slot)) charger(); } },
        { label: "Supprimer", cls: "danger", onClick: async () => {
          if (!await modal.confirm({ title: "Supprimer la séance", message: "Supprimer cette séance ? Refusé si des absences y sont rattachées.", ok: "Supprimer", danger: true })) return;
          try { const x = await API.del("/api/seances/" + r.id_seance); toast.success(x.message); charger(); } catch (ex) { reportError(ex); }
        } },
      ]) },
    ], rows, { empty: "Aucune séance sur la période." }));
  };
  [selectClasse, debut, fin].forEach((i) => i.addEventListener("change", charger));
  charger();
  return el("div", null, el("div", { class: "filtres" }, filterField("Classe", selectClasse, "large"), filterField("Du", debut), filterField("Au", fin)), zone);
}

function imprimerEdt(classe, slots, creneaux) {
  const etab = App.session.etablissement || {};
  printDocument(el("div", { class: "document" },
    enteteDocument(etab),
    el("h2", { class: "titre-doc" }, "Emploi du temps — " + (classe ? classe.libelle : "")),
    el("table", null,
      el("thead", null, el("tr", null, el("th", null, "Créneau"), JOURS_EDT.map((j) => el("th", null, j)))),
      el("tbody", null, creneaux.map((c) => el("tr", null, el("td", null, el("b", null, c.libelle), el("br"), (c.heure_debut || "") + " – " + (c.heure_fin || "")),
        JOURS_EDT.map((j) => el("td", null, slots.filter((s) => s.id_creneau === c.id_creneau && s.actif !== false && String(s.jour || "").toLowerCase() === j.toLowerCase())
          .map((s) => el("div", null, el("b", null, s.matiere), el("br"), s.formateur || "", el("br"), el("i", null, s.salle || ""))))))))),
    el("p", { class: "small" }, "Année " + (App.session.annee_active ? App.session.annee_active.libelle : "") + " · édité le " + fmt.date(new Date().toISOString()))));
}
