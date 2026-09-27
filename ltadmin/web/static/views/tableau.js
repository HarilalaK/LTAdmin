/* Vue : tableau de bord. */
"use strict";

App.register("tableau", {
  async render(container) {
    const d = await API.value("/api/tableau-de-bord");
    const devise = d.devise || App.devise();
    const maxEff = Math.max(1, ...d.effectifs.map((e) => e.nb_inscrits || 0));

    const indicateurs = el("div", { class: "grille c4" },
      indicateur("Classes", d.nb_classes, d.annee_libelle ? "Année " + d.annee_libelle : "Aucune année active"),
      indicateur("Étudiants inscrits", d.nb_etudiants, "Inscriptions actives"),
      indicateur("Formateurs actifs", d.nb_formateurs, ""),
      indicateur("Total encaissé", fmt.money(d.total_encaisse, devise), "Écolage — année en cours", "succes"),
    );

    const alertesEcheances = el("div", { class: "grille c2 mt" },
      indicateur("Échéances échues", d.nb_echeances_echues, fmt.money(d.montant_echeances_echues, devise) + " restant dus",
        d.nb_echeances_echues ? "alerte" : ""),
      indicateur("Alertes d’absence", d.alertes_absences.length, "Seuil : " + fmt.number(d.seuil_absence, 0) + " h",
        d.alertes_absences.length ? "alerte" : ""),
    );

    const effectifs = card("Effectifs par classe", d.effectifs.length
      ? el("div", { class: "barres" }, d.effectifs.map((e) => el("div", { class: "ligne" },
        el("span", { title: e.filiere }, e.classe),
        el("div", { class: "piste" }, el("div", { class: "rempli" + ((e.effectif_max && e.nb_inscrits > e.effectif_max) ? " rouge" : ""), style: { width: Math.round(100 * (e.nb_inscrits || 0) / maxEff) + "%" } })),
        el("span", { class: "right" }, (e.nb_inscrits || 0) + (e.effectif_max ? " / " + e.effectif_max : "")))))
      : el("div", { class: "vide" }, "Aucune classe pour l’année active."),
      App.can("Référentiel") ? [button("Gérer les classes", () => App.navigate("referentiel", { onglet: "classes" }), "petit")] : []);

    const totalSexe = d.repartition_sexe.reduce((s, r) => s + (r.valeur || 0), 0) || 1;
    const sexe = card("Répartition par sexe", d.repartition_sexe.length
      ? el("div", { class: "barres" }, d.repartition_sexe.map((r) => el("div", { class: "ligne" },
        el("span", null, libelleSexe(r.libelle)),
        el("div", { class: "piste" }, el("div", { class: "rempli " + (r.libelle === "F" ? "ambre" : ""), style: { width: Math.round(100 * r.valeur / totalSexe) + "%" } })),
        el("span", { class: "right" }, r.valeur + " (" + Math.round(100 * r.valeur / totalSexe) + " %)"))))
      : el("div", { class: "vide" }, "Aucun inscrit."));

    const absences = card("Étudiants au-dessus du seuil d’absence",
      dataTable([
        { key: "matricule", label: "Matricule" },
        { key: "nom", label: "Étudiant" },
        { label: "Heures", num: true, render: (r) => fmt.hours(r.heures) },
      ], d.alertes_absences, { empty: "Aucune alerte : aucun étudiant ne dépasse " + fmt.number(d.seuil_absence, 0) + " h." }),
      App.can("Absences") ? [button("Voir les absences", () => App.navigate("absences"), "petit")] : []);

    const journal = d.journal_recent === null ? null : card("Activité récente",
      dataTable([
        { label: "Date", render: (r) => fmt.datetime(r.date_log), cls: "nowrap" },
        { key: "code_utr", label: "Utilisateur" },
        { key: "action_log", label: "Action" },
        { key: "table_cible", label: "Cible" },
        { key: "detail", label: "Détail" },
      ], d.journal_recent, { empty: "Aucune opération enregistrée." }));

    append(container, [
      pageHeader("Tableau de bord", "Vue d’ensemble de l’année " + (d.annee_libelle || "—") + " · " + fmt.datetime(new Date().toISOString())),
      indicateurs, alertesEcheances,
      el("div", { class: "grille c2 mt" }, effectifs, sexe),
      el("div", { class: "grille c2 mt" }, absences, journal || el("div")),
    ]);
  },
});

function indicateur(libelle, valeur, detail, cls = "") {
  return el("div", { class: "carte indicateur " + cls },
    el("div", { class: "libelle" }, libelle),
    el("div", { class: "valeur" }, valeur === null || valeur === undefined ? "—" : valeur),
    el("div", { class: "detail" }, detail || " "));
}

function libelleSexe(code) {
  return code === "F" ? "Féminin" : code === "M" ? "Masculin" : (code || "Non renseigné");
}
