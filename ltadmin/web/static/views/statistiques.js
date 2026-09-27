/* Vue : statistiques (effectifs, répartitions, avancement de saisie, absences, encaissements). */
"use strict";

App.register("statistiques", {
  async render(container, { params }) {
    const classes = App.classesActives();
    const selectClasse = selectInput(classeOptions(classes), params.classe || "", { placeholder: "Toutes les classes" });
    const selectPeriode = selectInput(periodeOptions(), params.periode || "", { placeholder: "Toutes les périodes" });
    const debut = el("input", { type: "date", value: params.debut || (App.session.annee_active ? fmt.isoDate(App.session.annee_active.date_debut) : "") });
    const fin = el("input", { type: "date", value: params.fin || fmt.today() });
    const zone = el("div");
    const charger = async () => {
      clear(zone); zone.appendChild(loading());
      const s = await API.value("/api/statistiques" + API.qs({ classe: selectClasse.value, periode: selectPeriode.value, debut: debut.value, fin: fin.value }));
      clear(zone);
      const totalEnc = s.encaissements.reduce((a, r) => a + Number(r.total || 0), 0);
      zone.appendChild(el("div", { class: "grille c4 mb" },
        indicateur("Inscrits", s.effectifs.reduce((a, r) => a + (r.nb_inscrits || 0), 0), s.effectifs.length + " classe(s)"),
        indicateur("Heures d’absence", fmt.number(s.total_absences, 1), "année active"),
        indicateur("Encaissements", fmt.money(totalEnc), "sur la période choisie", "succes"),
        indicateur("Échéances échues", s.echeances_echues.length, fmt.money(s.echeances_echues.reduce((a, r) => a + Number(r.reste || 0), 0)) + " à recouvrer", s.echeances_echues.length ? "alerte" : "")));
      zone.appendChild(el("div", { class: "grille c2" },
        card("Effectifs par classe", barres(s.effectifs.map((r) => ({ libelle: r.classe, valeur: r.nb_inscrits, detail: r.effectif_max ? r.nb_inscrits + " / " + r.effectif_max : String(r.nb_inscrits) })))),
        card("Répartition par sexe", barres(s.sexe.map((r) => ({ libelle: libelleSexe(r.libelle), valeur: r.valeur })), true)),
        card("Redoublants", barres(s.redoublants.map((r) => ({ libelle: r.libelle, valeur: r.valeur })), true)),
        card("Résultats finaux (décisions)", barres(s.resultats.map((r) => ({ libelle: r.libelle, valeur: r.valeur })), true)),
        card("Mentions (résultats finaux)", barres(s.mentions.map((r) => ({ libelle: r.libelle, valeur: r.valeur })), true)),
        card("Encaissements par mode de paiement", barres(s.encaissements.map((r) => ({ libelle: r.mode_paie || "—", valeur: Number(r.total || 0), detail: fmt.money(r.total, "") + " (" + r.nb_paiements + ")" })))),
      ));
      zone.appendChild(el("div", { class: "mt" }, card("Avancement de la saisie des notes", dataTable([
        { key: "classe", label: "Classe" }, { key: "matiere", label: "Matière" }, { key: "periode", label: "Période" }, { key: "intitule", label: "Évaluation" },
        { label: "Notes / inscrits", num: true, render: (r) => r.nb_notes + " / " + r.nb_inscrits },
        { label: "Avancement", render: (r) => { const pct = r.nb_inscrits ? Math.round(100 * r.nb_notes / r.nb_inscrits) : 0; return el("div", { class: "barres" }, el("div", { class: "ligne", style: { gridTemplateColumns: "1fr 50px" } }, el("div", { class: "piste" }, el("div", { class: "rempli " + (pct >= 100 ? "vert" : pct > 0 ? "ambre" : "rouge"), style: { width: pct + "%" } })), el("span", null, pct + " %"))); } },
      ], s.avancement, { empty: "Aucune évaluation pour ces critères." }))));
      zone.appendChild(el("div", { class: "mt" }, card("Échéances échues non soldées", dataTable([
        { key: "matricule", label: "Matricule", cls: "mono" }, { label: "Étudiant", render: (r) => r.nom + " " + r.prenom }, { key: "classe", label: "Classe" }, { key: "libelle", label: "Échéance" },
        { label: "Date", render: (r) => fmt.date(r.date_echeance) }, { label: "Reste", num: true, render: (r) => fmt.money(r.reste, "") },
      ], s.echeances_echues, { empty: "Aucune échéance en retard." }))));
    };
    [selectClasse, selectPeriode, debut, fin].forEach((i) => i.addEventListener("change", charger));
    append(container, [
      pageHeader("Statistiques", "Indicateurs de pilotage de l’année active."),
      el("div", { class: "filtres" }, filterField("Classe (avancement)", selectClasse, "large"), filterField("Période (avancement)", selectPeriode), filterField("Encaissements du", debut), filterField("au", fin)),
      zone,
    ]);
    await charger();
  },
});

function barres(items, pourcentages = false) {
  if (!items.length) return el("div", { class: "vide" }, "Aucune donnée.");
  const max = Math.max(1, ...items.map((i) => Number(i.valeur) || 0));
  const total = items.reduce((s, i) => s + (Number(i.valeur) || 0), 0) || 1;
  const couleurs = ["", "ambre", "vert", "rouge"];
  return el("div", { class: "barres" }, items.map((i, idx) => el("div", { class: "ligne" },
    el("span", { title: i.libelle }, i.libelle),
    el("div", { class: "piste" }, el("div", { class: "rempli " + (pourcentages ? couleurs[idx % couleurs.length] : ""), style: { width: Math.round(100 * (Number(i.valeur) || 0) / max) + "%" } })),
    el("span", { class: "right small" }, i.detail || (pourcentages ? i.valeur + " (" + Math.round(100 * i.valeur / total) + " %)" : String(i.valeur))))));
}
