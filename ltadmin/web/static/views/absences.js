/* Vue : absences (appel par séance, synthèse par étudiant, alertes). */
"use strict";

const NATURES_ABSENCE = ["Absence", "Retard", "Exclusion"];

App.register("absences", {
  async render(container, { params }) {
    const onglets = [{ key: "appel", label: "Appel par séance" }, { key: "synthese", label: "Synthèse par étudiant" }];
    let actif = params.seance ? "appel" : (params.onglet === "synthese" ? "synthese" : "appel");
    const barre = el("div"), corps = el("div");
    const afficher = () => {
      clear(barre); barre.appendChild(tabs(onglets, actif, (k) => { actif = k; history.replaceState(null, "", "#/absences?onglet=" + k); afficher(); }));
      clear(corps); corps.appendChild(actif === "appel" ? sectionAppel(params) : sectionSyntheseAbsences(params));
    };
    append(container, [pageHeader("Absences", "Saisie des absences par séance et suivi du seuil d’alerte (" + fmt.number(App.param("SEUIL_ABSENCE", 30), 0) + " h)."), barre, corps]);
    afficher();
  },
});

function sectionAppel(params) {
  const classes = App.classesActives();
  const selectClasse = selectInput(classeOptions(classes), params.classe || (classes[0] && classes[0].id_classe), { placeholder: "— Classe —" });
  const debut = el("input", { type: "date", value: params.debut || fmt.isoDate(new Date(Date.now() - 14 * 86400000).toISOString()) });
  const fin = el("input", { type: "date", value: params.fin || fmt.today() });
  const listeSeances = el("div");
  const feuille = el("div");
  let seanceActive = params.seance ? Number(params.seance) : null;

  const chargerFeuille = async () => {
    clear(feuille);
    if (!seanceActive) { feuille.appendChild(el("div", { class: "info" }, "Choisissez une séance dans la liste pour faire l’appel.")); return; }
    feuille.appendChild(loading());
    const { seance, slot, absences } = await API.value("/api/seances/" + seanceActive);
    const inscrits = slot ? await API.value("/api/inscriptions" + API.qs({ classe: slot.id_classe })) : [];
    clear(feuille);
    const parInscription = {};
    absences.forEach((a) => { parInscription[a.id_inscription] = a; });
    const lignes = inscrits.filter((i) => i.statut !== "SORTI").map((i) => ({ inscription: i, absence: parInscription[i.id_inscription] || null }));
    feuille.appendChild(el("div", { class: "carte-entete", style: { borderBottom: "none", padding: "0 0 10px" } },
      el("h2", null, `Appel — ${slot ? slot.matiere : ""} · ${fmt.date(seance.date_seance)}`),
      el("span", { class: "muted small" }, slot ? `${slot.classe} · ${slot.jour} ${slot.creneau} · ${slot.formateur}` : ""),
      el("div", { class: "actions" }, el("span", { class: "badge rouge" }, absences.length + " absence(s)"))));
    feuille.appendChild(dataTable([
      { key: "matricule", label: "Matricule", cls: "mono nowrap", render: (r) => r.inscription.matricule },
      { label: "Étudiant", render: (r) => r.inscription.nom + " " + r.inscription.prenom },
      { label: "Absence", render: (r) => r.absence ? el("span", { class: "badge " + (r.absence.justifiee ? "ambre" : "rouge") }, `${r.absence.nature || "Absence"} · ${fmt.number(r.absence.nb_heures, 1)} h${r.absence.justifiee ? " · justifiée" : ""}`) : el("span", { class: "badge vert" }, "Présent") },
      { label: "Motif", render: (r) => r.absence ? r.absence.motif || "" : "" },
      { label: "", cls: "actions", render: (r) => actionButtons([
        !r.absence && { label: "Marquer absent", cls: "danger", onClick: () => editerAbsence(null, seance, r.inscription).then((ok) => ok && chargerFeuille()) },
        r.absence && { label: "Modifier", onClick: () => editerAbsence(r.absence, seance, r.inscription).then((ok) => ok && chargerFeuille()) },
        r.absence && { label: "Présent", onClick: async () => { try { const x = await API.del("/api/absences/" + r.absence.id_absence); toast.success(x.message); chargerFeuille(); } catch (ex) { reportError(ex); } } },
      ]) },
    ], lignes, { empty: "Aucun inscrit actif dans cette classe." }));
  };

  const chargerSeances = async () => {
    clear(listeSeances); listeSeances.appendChild(loading());
    const rows = selectClasse.value ? await API.value("/api/seances" + API.qs({ classe: selectClasse.value, debut: debut.value, fin: fin.value })) : [];
    clear(listeSeances);
    listeSeances.appendChild(dataTable([
      { label: "Date", render: (r) => fmt.date(r.date_seance), cls: "nowrap" }, { key: "matiere", label: "Matière" }, { label: "Créneau", render: (r) => r.creneau },
      { label: "Heures", num: true, render: (r) => fmt.number(r.nb_heures, 1) },
    ], rows, { empty: "Aucune séance : enregistrez d’abord les séances réalisées (Emploi du temps).", onRow: (r, tr) => { seanceActive = r.id_seance; listeSeances.querySelectorAll("tr.selectionne").forEach((x) => x.classList.remove("selectionne")); tr.classList.add("selectionne"); chargerFeuille(); }, rowClass: (r) => r.id_seance === seanceActive ? "selectionne" : "" }));
  };
  [selectClasse, debut, fin].forEach((i) => i.addEventListener("change", () => { seanceActive = null; chargerSeances(); chargerFeuille(); }));
  chargerSeances(); chargerFeuille();
  return el("div", null,
    el("div", { class: "filtres" }, filterField("Classe", selectClasse, "large"), filterField("Séances du", debut), filterField("au", fin)),
    el("div", { class: "grille", style: { gridTemplateColumns: "minmax(280px, 1fr) 2fr" } }, card("Séances", listeSeances), card(null, feuille)));
}

async function editerAbsence(absence, seance, inscription) {
  const creation = !absence;
  return modal.form({
    title: (creation ? "Absence — " : "Modifier l’absence — ") + inscription.nom + " " + inscription.prenom, size: "etroite",
    fields: [
      { name: "nature", label: "Nature", type: "select", required: true, span: 12, options: NATURES_ABSENCE },
      { name: "nb_heures", label: "Heures", type: "number", required: true, span: 6, min: 0.5, step: "0.5" },
      { name: "justifiee", label: "Justifiée", type: "check", span: 6 },
      { name: "motif", label: "Motif", type: "textarea", span: 12, rows: 2 },
    ],
    values: absence || { nature: "Absence", nb_heures: seance.nb_heures || 2, justifiee: false },
    onSubmit: async (v) => {
      const body = Object.assign({ id_seance: seance.id_seance, id_inscription: inscription.id_inscription }, v, creation ? {} : { id_absence: absence.id_absence });
      const r = await API.post("/api/absences", body); toast.success(r.message);
    },
  });
}

function sectionSyntheseAbsences(params) {
  const classes = App.classesActives();
  const selectClasse = selectInput(classes.map((c) => ({ value: c.libelle, label: c.libelle })), params.classe_lib || "", { placeholder: "Toutes les classes" });
  const zone = el("div");
  const seuil = Number(App.param("SEUIL_ABSENCE", 30));
  const charger = async () => {
    clear(zone); zone.appendChild(loading());
    const rows = await API.value("/api/absences/synthese" + API.qs({ classe: selectClasse.value }));
    rows.sort((a, b) => (b.TOTAL_HEURES || 0) - (a.TOTAL_HEURES || 0));
    clear(zone);
    zone.appendChild(el("div", { class: "compteur" }, rows.length + " étudiant(s) avec absences · " + rows.filter((r) => (r.TOTAL_HEURES || 0) >= seuil).length + " au-dessus du seuil de " + seuil + " h"));
    zone.appendChild(dataTable([
      { key: "MATRICULE", label: "Matricule", cls: "mono nowrap" }, { key: "NOM", label: "Nom" }, { key: "PRENOM", label: "Prénom(s)" }, { key: "CLASSE", label: "Classe" },
      { label: "Total", num: true, render: (r) => fmt.hours(r.TOTAL_HEURES) }, { label: "Justifiées", num: true, render: (r) => fmt.hours(r.HEURES_JUSTIFIEES) },
      { label: "Non justifiées", num: true, render: (r) => fmt.hours((r.TOTAL_HEURES || 0) - (r.HEURES_JUSTIFIEES || 0)) },
      { label: "Alerte", render: (r) => (r.TOTAL_HEURES || 0) >= seuil ? el("span", { class: "badge rouge" }, "Seuil dépassé") : "" },
      { label: "", cls: "actions", render: (r) => actionButtons([App.can("Inscriptions") && { label: "Détail", onClick: () => App.navigate("inscriptions", {}, [r.ID_INSCRIPTION]) }]) },
    ], rows, { empty: "Aucune absence enregistrée.", rowClass: (r) => "" }));
  };
  selectClasse.addEventListener("change", charger);
  charger();
  return el("div", null, el("div", { class: "filtres" }, filterField("Classe", selectClasse, "large")), zone);
}
