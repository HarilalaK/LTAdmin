/* Vue : bulletins (génération, consultation, appréciation, impression). */
"use strict";

App.register("bulletins", {
  async render(container, { params, segments }) {
    if (segments[0]) { await renderBulletin(container, Number(segments[0])); return; }
    const classes = App.classesActives();
    const selectClasse = selectInput(classeOptions(classes), params.classe || (classes[0] && classes[0].id_classe), { placeholder: "— Classe —" });
    const selectPeriode = selectInput(periodeOptions(), params.periode || (App.ref.periodes[0] && App.ref.periodes[0].id_periode), { placeholder: "— Période —" });
    const zone = el("div");
    const charger = async () => {
      clear(zone);
      if (!selectClasse.value || !selectPeriode.value) { zone.appendChild(el("div", { class: "info" }, "Choisissez une classe et une période.")); return; }
      zone.appendChild(loading());
      const rows = await API.value("/api/bulletins" + API.qs({ classe: selectClasse.value, periode: selectPeriode.value }));
      clear(zone);
      const moyennes = rows.map((r) => r.moyenne).filter((m) => m !== null && m !== undefined);
      const moyClasse = moyennes.length ? moyennes.reduce((a, b) => a + b, 0) / moyennes.length : null;
      const admis = rows.filter((r) => r.decision === "ADMIS").length;
      zone.appendChild(el("div", { class: "flex wrap mb" },
        el("span", { class: "badge bleu" }, rows.length + " bulletin(s)"),
        el("span", { class: "badge" }, "Moyenne de classe : " + (moyClasse === null ? "—" : fmt.note(moyClasse))),
        el("span", { class: "badge vert" }, admis + " admis"), el("span", { class: "badge rouge" }, (rows.length - admis) + " non admis")));
      zone.appendChild(dataTable([
        { label: "Rang", render: (r) => r.rang ? r.rang + (r.rang === 1 ? "er" : "e") + " / " + r.effectif : "", width: "90px" },
        { key: "matricule", label: "Matricule", cls: "mono nowrap" }, { key: "nom", label: "Nom" }, { key: "prenom", label: "Prénom(s)" },
        { label: "Moyenne", num: true, render: (r) => el("b", null, fmt.note(r.moyenne)) },
        { label: "Mention", render: (r) => mentionPour(r.moyenne) },
        { label: "Décision", render: (r) => fmt.statut(r.decision) },
        { label: "", cls: "actions", render: (r) => actionButtons([
          { label: "Consulter", onClick: () => App.navigate("bulletins", {}, [r.id_bulletin]) },
          { label: "Imprimer", onClick: () => imprimerBulletin(r.id_bulletin) },
        ]) },
      ], rows, { empty: "Aucun bulletin généré pour cette classe et cette période.", onRow: (r) => App.navigate("bulletins", {}, [r.id_bulletin]) }));
      if (rows.length) zone.appendChild(el("div", { class: "mt" }, button("Imprimer tous les bulletins de la classe", () => imprimerTous(rows.map((r) => r.id_bulletin)), "")));
    };
    selectClasse.addEventListener("change", charger);
    selectPeriode.addEventListener("change", charger);
    append(container, [
      pageHeader("Bulletins", "Moyennes pondérées par les coefficients, rangs (classement « compétition ») et mentions.", [
        button("Générer / régénérer les bulletins", async () => {
          if (!selectClasse.value || !selectPeriode.value) { toast.warn("Choisissez une classe et une période."); return; }
          const classe = App.classe(selectClasse.value);
          if (!await modal.confirm({ title: "Générer les bulletins", message: `Calculer les bulletins de « ${classe ? classe.libelle : ""} » pour la période choisie ? Les bulletins existants sont recalculés (les appréciations saisies sont conservées).`, ok: "Générer" })) return;
          try { const r = await API.post("/api/bulletins/generer", { id_classe: Number(selectClasse.value), id_periode: Number(selectPeriode.value) }); toast.success(r.message); charger(); } catch (ex) { reportError(ex); }
        }, "primaire"),
      ]),
      el("div", { class: "filtres" }, filterField("Classe", selectClasse, "large"), filterField("Période", selectPeriode)),
      zone,
    ]);
    await charger();
  },
});

function mentionPour(moyenne) {
  if (moyenne === null || moyenne === undefined) return "";
  const grille = App.ref.mentions || [];
  const max = Math.max(...grille.map((g) => g.sup || 0), 20);
  const m = grille.find((g) => moyenne >= g.inf && (moyenne < g.sup || (moyenne === g.sup && g.sup >= max)));
  return m ? el("span", { class: "badge " + (m.admis ? "vert" : "rouge") }, m.mention) : "";
}

async function renderBulletin(container, id) {
  const d = await API.value("/api/bulletins/" + id);
  const b = d.bulletin || {}, r = d.resume;
  const appreciation = el("textarea", { rows: 3 }, b.appreciation || "");
  append(container, [
    pageHeader("Bulletin — " + r.nom + " " + r.prenom, `${r.classe} · ${r.periode}`, [
      button("← Liste", () => App.navigate("bulletins", { periode: r.id_periode })),
      button("Imprimer", () => printDocument(documentBulletin(d)), "primaire"),
    ]),
    el("div", { class: "grille c2" },
      card("Synthèse", el("dl", { class: "kv" },
        ligneKv("Moyenne générale", el("b", null, fmt.note(b.moyenne) + " / 20")), ligneKv("Total points / coef.", fmt.number(b.total_points, 2) + " / " + fmt.number(b.total_coef, 1)),
        ligneKv("Rang", (b.rang || "—") + " / " + (b.effectif || "—")), ligneKv("Moyenne de la classe", fmt.note(b.moy_classe)),
        ligneKv("Mention", mentionPour(b.moyenne)), ligneKv("Décision", fmt.statut(b.decision)),
        ligneKv("Heures d’absence", fmt.hours(d.absences_heures)), ligneKv("Édité le", fmt.datetime(b.date_edition)))),
      card("Appréciation générale", el("div", null, appreciation, el("div", { class: "mt" }, button("Enregistrer l’appréciation", async () => {
        try { const x = await API.put("/api/bulletins/" + id, { appreciation: appreciation.value.trim() || null }); toast.success(x.message); } catch (ex) { reportError(ex); }
      }, "primaire"))))),
    el("div", { class: "mt" }, card("Détail par matière", dataTable([
      { key: "matiere", label: "Matière" }, { key: "formateur", label: "Formateur" },
      { label: "Moyenne", num: true, render: (l) => fmt.note(l.moyenne_mat) }, { label: "Coef.", num: true, render: (l) => fmt.number(l.coefficient, 1) },
      { label: "Points", num: true, render: (l) => fmt.number(l.points, 2) }, { label: "Rang", num: true, key: "rang_mat" },
      { label: "Min / max classe", render: (l) => fmt.note(l.moy_min) + " / " + fmt.note(l.moy_max) }, { key: "appreciation", label: "Appréciation" },
    ], d.lignes, { empty: "Aucune matière notée." }))),
  ]);
}

function documentBulletin(d) {
  const b = d.bulletin || {}, r = d.resume, e = d.etudiant || {}, etab = d.etablissement || {};
  const mention = mentionPour(b.moyenne);
  return el("div", { class: "document" },
    enteteDocument(etab),
    el("h2", { class: "titre-doc" }, "Bulletin de notes — " + r.periode),
    el("table", null, el("tbody", null,
      el("tr", null, el("td", null, el("b", null, "Étudiant : "), r.nom + " " + r.prenom), el("td", null, el("b", null, "Matricule : "), r.matricule)),
      el("tr", null, el("td", null, el("b", null, "Classe : "), r.classe), el("td", null, el("b", null, "Année scolaire : "), d.annee ? d.annee.libelle : "")),
      el("tr", null, el("td", null, el("b", null, "Né(e) le : "), fmt.date(e.date_naissance) + (e.lieu_naissance ? " à " + e.lieu_naissance : "")), el("td", null, el("b", null, "Effectif : "), b.effectif || "")))),
    el("table", null,
      el("thead", null, el("tr", null, ["Matière", "Formateur", "Moyenne /20", "Coef.", "Points", "Rang", "Min", "Max", "Appréciation"].map((h) => el("th", null, h)))),
      el("tbody", null, d.lignes.map((l) => el("tr", null,
        el("td", null, l.matiere), el("td", null, l.formateur || ""), el("td", { class: "num" }, fmt.note(l.moyenne_mat)), el("td", { class: "num" }, fmt.number(l.coefficient, 1)),
        el("td", { class: "num" }, fmt.number(l.points, 2)), el("td", { class: "num" }, l.rang_mat || ""), el("td", { class: "num" }, fmt.note(l.moy_min)), el("td", { class: "num" }, fmt.note(l.moy_max)), el("td", null, l.appreciation || "")))),
      el("tfoot", null, el("tr", null, el("th", { colspan: 2 }, "Totaux"), el("th", { class: "num" }, fmt.note(b.moyenne)), el("th", { class: "num" }, fmt.number(b.total_coef, 1)), el("th", { class: "num" }, fmt.number(b.total_points, 2)), el("th", { colspan: 4 }, "")))),
    el("table", null, el("tbody", null,
      el("tr", null, el("td", null, el("b", null, "Moyenne générale : "), fmt.note(b.moyenne) + " / 20"), el("td", null, el("b", null, "Rang : "), (b.rang || "—") + " / " + (b.effectif || "—")), el("td", null, el("b", null, "Moyenne de classe : "), fmt.note(b.moy_classe))),
      el("tr", null, el("td", null, el("b", null, "Mention : "), el("span", { class: "mention" }, mention ? mention.textContent : "")), el("td", null, el("b", null, "Décision : "), b.decision || ""), el("td", null, el("b", null, "Absences : "), fmt.hours(d.absences_heures))))),
    el("p", null, el("b", null, "Appréciation générale : "), b.appreciation || "…"),
    el("div", { class: "signature" }, el("div", null, "Le responsable de classe", el("div", { class: "trait" }, "")), el("div", null, (etab.directeur ? "Le directeur, " + etab.directeur : "Le directeur"), el("div", { class: "trait" }, ""))),
    el("p", { class: "small", style: { marginTop: "18px", color: "#555" } }, "Édité le " + fmt.datetime(new Date().toISOString()) + " par LTAdmin."));
}

function enteteDocument(etab) {
  return el("div", { class: "entete-doc" },
    el("div", null, el("div", { class: "etab" }, etab.nom_etab || "Établissement"), el("div", { class: "coord" }, [etab.adresse, etab.tel ? "Tél. " + etab.tel : null, etab.email].filter(Boolean).join(" · "))),
    el("div", { class: "right" }, el("div", { class: "etab" }, etab.sigle || ""), el("div", { class: "coord" }, etab.site_web || "")));
}

async function imprimerBulletin(id) {
  try { printDocument(documentBulletin(await API.value("/api/bulletins/" + id))); } catch (ex) { reportError(ex); }
}

async function imprimerTous(ids) {
  try {
    const wrapper = el("div");
    for (const id of ids) {
      const doc = documentBulletin(await API.value("/api/bulletins/" + id));
      doc.style.pageBreakAfter = "always";
      wrapper.appendChild(doc);
    }
    printDocument(wrapper);
  } catch (ex) { reportError(ex); }
}
