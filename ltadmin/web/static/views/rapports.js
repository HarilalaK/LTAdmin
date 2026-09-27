/* Vue : rapports (états R_*), aperçu et export CSV. */
"use strict";

App.register("rapports", {
  async render(container, { params }) {
    const definitions = await API.value("/api/rapports");
    const liste = el("div", { class: "stack" });
    const zone = el("div");
    let actif = definitions.find((d) => d.key === params.rapport) || definitions[0];

    const afficherListe = () => {
      clear(liste);
      definitions.forEach((d) => liste.appendChild(el("div", { class: "carte plate", style: { padding: "10px 12px", cursor: "pointer", borderColor: d.key === actif.key ? "var(--bleu)" : "" }, onClick: () => { actif = d; afficherListe(); afficherRapport(); } },
        el("div", { style: { fontWeight: 600 } }, d.title), el("div", { class: "small muted" }, d.description), el("div", { class: "small" }, el("span", { class: "badge bleu" }, d.filter_label || "Sans filtre")))));
    };

    const afficherRapport = () => {
      clear(zone);
      if (!actif) return;
      const filtres = {};
      const champs = [];
      const classes = App.classesActives();
      if (actif.filter_kind === "classe_libelle") {
        const s = selectInput(classes.map((c) => ({ value: c.libelle, label: c.libelle })), classes[0] && classes[0].libelle, {});
        champs.push(filterField("Classe", s, "large")); filtres.classe = () => s.value;
      } else if (actif.filter_kind === "classe_periode") {
        const s = selectInput(classeOptions(classes), classes[0] && classes[0].id_classe, {});
        const p = selectInput(periodeOptions(), "", { placeholder: "Toutes les périodes" });
        champs.push(filterField("Classe", s, "large"), filterField("Période", p)); filtres.id_classe = () => s.value; filtres.id_periode = () => p.value;
      } else if (actif.filter_kind === "inscription") {
        const s = selectInput(classeOptions(classes), classes[0] && classes[0].id_classe, {});
        const i = selectInput([], "", { placeholder: "— Étudiant —" });
        const chargerInscrits = async () => { clear(i); i.appendChild(el("option", { value: "" }, "— Étudiant —")); if (!s.value) return; (await API.value("/api/inscriptions" + API.qs({ classe: s.value }))).forEach((x) => i.appendChild(el("option", { value: x.id_inscription }, `${x.nom} ${x.prenom} (${x.matricule})`))); };
        s.addEventListener("change", chargerInscrits); chargerInscrits();
        champs.push(filterField("Classe", s, "large"), filterField("Étudiant", i, "large")); filtres.id_inscription = () => i.value;
      } else if (actif.filter_kind === "matricule") {
        const m = el("input", { type: "text", placeholder: "ETU-2026-0001" });
        champs.push(filterField("Matricule", m)); filtres.matricule = () => m.value.trim();
      }
      const resultat = el("div", { class: "mt" });
      const lireFiltres = () => { const out = {}; Object.entries(filtres).forEach(([k, fn]) => { out[k] = fn(); }); return out; };
      const executer = async () => {
        clear(resultat); resultat.appendChild(loading());
        try {
          const d = await API.value("/api/rapports/" + actif.key + API.qs(lireFiltres()));
          clear(resultat);
          resultat.appendChild(el("div", { class: "compteur" }, d.count + " ligne(s)"));
          resultat.appendChild(dataTable(d.columns.map((c) => ({ key: c, label: c.replace(/_/g, " "), render: (r) => formatCellule(r[c], c) })), d.rows, { empty: "Aucune donnée pour ces critères." }));
        } catch (ex) { clear(resultat); reportError(ex); }
      };
      const exporter = async () => {
        try {
          const response = await API.get("/api/rapports/" + actif.key + "/csv" + API.qs(lireFiltres()));
          const blob = await response.blob();
          const dispo = response.headers.get("Content-Disposition") || "";
          const m = dispo.match(/filename="([^"]+)"/);
          downloadBlob(blob, m ? m[1] : actif.key + ".csv");
          toast.success("Export CSV téléchargé (séparateur « ; », encodage UTF-8 compatible Excel).");
        } catch (ex) { reportError(ex); }
      };
      zone.appendChild(el("div", null,
        el("h2", null, actif.title), el("p", { class: "muted" }, actif.description),
        el("div", { class: "filtres" }, champs, el("div", { class: "grow" }), button("Afficher", executer, "primaire"), button("Exporter en CSV", exporter)),
        resultat));
      executer();
    };
    afficherListe();
    afficherRapport();
    append(container, [
      pageHeader("Rapports", "États prédéfinis de la base, consultables à l’écran et exportables au format CSV."),
      el("div", { class: "grille", style: { gridTemplateColumns: "300px 1fr" } }, liste, card(null, zone)),
    ]);
  },
});

function formatCellule(value, column) {
  if (value === null || value === undefined) return "";
  const c = column.toUpperCase();
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}/.test(value)) return c.includes("DATE") && value.length > 10 ? fmt.datetime(value) : fmt.date(value);
  if (typeof value === "number") {
    if (/MONTANT|TOTAL_PAYE|RESTE|DU\b|REMISE|PAYE/.test(c) && !/HEURES|NOTE|MOY/.test(c)) return fmt.money(value, "");
    if (/MOY|NOTE|POINTS/.test(c)) return fmt.number(value, 2);
    if (Number.isInteger(value)) return String(value);
    return fmt.number(value, 2);
  }
  return String(value);
}
