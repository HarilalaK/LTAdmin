/* Vue : paie des formateurs (heures réalisées × taux horaire). */
"use strict";

App.register("paie", {
  async render(container, { params }) {
    const maintenant = new Date();
    const periodeDefaut = `${maintenant.getFullYear()}-${String(maintenant.getMonth() + 1).padStart(2, "0")}`;
    const periode = el("input", { type: "month", value: params.periode || periodeDefaut });
    const selectFormateur = selectInput(App.ref.formateurs.map((f) => ({ value: f.id_formateur, label: f.nom_complet })), params.formateur || "", { placeholder: "Toutes (par période)" });
    const zone = el("div");
    const charger = async () => {
      clear(zone); zone.appendChild(loading());
      const rows = await API.value("/api/paie" + API.qs(selectFormateur.value ? { formateur: selectFormateur.value } : { periode: periode.value }));
      clear(zone);
      const total = rows.reduce((s, r) => s + Number(r.paie.montant || 0), 0);
      const payees = rows.filter((r) => r.paie.paye).reduce((s, r) => s + Number(r.paie.montant || 0), 0);
      zone.appendChild(el("div", { class: "grille c3 mb" },
        indicateur("Paies", rows.length, selectFormateur.value ? "toutes périodes" : "période " + periode.value),
        indicateur("Montant total", fmt.money(total), ""), indicateur("Déjà payé", fmt.money(payees), fmt.money(total - payees) + " restant", "succes")));
      zone.appendChild(dataTable([
        { key: "periode", label: "Période", render: (r) => r.paie.periode }, { key: "formateur", label: "Formateur" }, { key: "matricule", label: "Matricule", cls: "mono" },
        { label: "Heures", num: true, render: (r) => fmt.number(r.paie.nb_heures, 1) }, { label: "Taux", num: true, render: (r) => fmt.money(r.paie.taux, "") },
        { label: "Montant", num: true, render: (r) => el("b", null, fmt.money(r.paie.montant, "")) },
        { label: "Statut", render: (r) => r.paie.paye ? el("span", { class: "badge vert" }, "Payée le " + fmt.date(r.paie.date_paie)) : el("span", { class: "badge ambre" }, "À payer") },
        { key: "observation", label: "Observation", render: (r) => r.paie.observation },
        { label: "", cls: "actions", render: (r) => actionButtons([
          !r.paie.paye && { label: "Marquer payée", cls: "primaire", onClick: async () => {
            const ok = await modal.form({ title: "Paiement de " + r.formateur, size: "etroite", fields: [{ name: "date_paie", label: "Date de paiement", type: "date", required: true, span: 12 }], values: { date_paie: fmt.today() }, submitLabel: "Confirmer",
              onSubmit: async (v) => { const x = await API.post(`/api/paie/${r.paie.id_paie}/payer`, { paye: true, date_paie: v.date_paie }); toast.success(x.message); } });
            if (ok) charger();
          } },
          r.paie.paye && { label: "Annuler le paiement", onClick: async () => { try { const x = await API.post(`/api/paie/${r.paie.id_paie}/payer`, { paye: false }); toast.success(x.message); charger(); } catch (ex) { reportError(ex); } } },
          { label: "Observation", onClick: async () => {
            const ok = await modal.form({ title: "Observation", size: "etroite", fields: [{ name: "observation", label: "Observation", type: "textarea", span: 12 }], values: { observation: r.paie.observation },
              onSubmit: async (v) => { const x = await API.put(`/api/paie/${r.paie.id_paie}`, { id_formateur: r.paie.id_formateur, observation: v.observation }); toast.success(x.message); } });
            if (ok) charger();
          } },
          { label: "Fiche", onClick: () => imprimerFichePaie(r) },
          !r.paie.paye && { label: "Supprimer", cls: "danger", onClick: async () => {
            if (!await modal.confirm({ title: "Supprimer la paie", message: "Supprimer ce calcul de paie ?", ok: "Supprimer", danger: true })) return;
            try { const x = await API.del("/api/paie/" + r.paie.id_paie); toast.success(x.message); charger(); } catch (ex) { reportError(ex); }
          } },
        ]) },
      ], rows, { empty: "Aucune paie pour ces critères." }));
    };
    periode.addEventListener("change", charger);
    selectFormateur.addEventListener("change", charger);
    append(container, [
      pageHeader("Paie des formateurs", "Calcul mensuel : heures des séances réalisées × taux horaire du formateur.", [
        button("Calculer une paie", () => calculerPaie(periode.value).then((ok) => ok && charger()), "primaire"),
      ]),
      el("div", { class: "filtres" }, filterField("Période", periode), filterField("Formateur", selectFormateur, "large")),
      zone,
    ]);
    await charger();
  },
});

async function calculerPaie(periodeDefaut) {
  const [an, mois] = (periodeDefaut || fmt.today().slice(0, 7)).split("-").map(Number);
  const debut = `${an}-${String(mois).padStart(2, "0")}-01`;
  const finDate = new Date(an, mois, 0);
  const fin = `${an}-${String(mois).padStart(2, "0")}-${String(finDate.getDate()).padStart(2, "0")}`;
  const apercu = el("div", { class: "info mb" }, "Choisissez le formateur et la période : les heures des séances « FAITE » sont totalisées.");
  return modal.form({
    title: "Calculer une paie", extra: apercu,
    fields: [
      { name: "id_formateur", label: "Formateur", type: "select", required: true, span: 12, options: App.ref.formateurs.filter((f) => f.actif !== false).map((f) => ({ value: f.id_formateur, label: f.nom_complet + (f.taux_horaire ? " — " + fmt.money(f.taux_horaire) + "/h" : " — taux horaire non défini") })) },
      { name: "periode", label: "Période (AAAA-MM)", required: true, span: 4, placeholder: "2026-01" },
      { name: "debut", label: "Du", type: "date", required: true, span: 4 }, { name: "fin", label: "Au", type: "date", required: true, span: 4 },
    ],
    values: { periode: periodeDefaut, debut, fin }, submitLabel: "Calculer",
    onSubmit: async (v) => { const r = await API.post("/api/paie/calculer", v); toast.success(r.message); },
  });
}

function imprimerFichePaie(r) {
  const etab = App.session.etablissement || {};
  printDocument(el("div", { class: "document" },
    enteteDocument(etab),
    el("h2", { class: "titre-doc" }, "Fiche de paie formateur — " + r.paie.periode),
    el("table", null, el("tbody", null,
      el("tr", null, el("td", null, el("b", null, "Formateur : "), r.formateur), el("td", null, el("b", null, "Matricule : "), r.matricule || "")),
      el("tr", null, el("td", null, el("b", null, "Heures réalisées : "), fmt.number(r.paie.nb_heures, 1) + " h"), el("td", null, el("b", null, "Taux horaire : "), fmt.money(r.paie.taux))),
      el("tr", null, el("td", null, el("b", null, "Montant : "), el("span", { class: "recu-montant" }, fmt.money(r.paie.montant))), el("td", null, el("b", null, "Statut : "), r.paie.paye ? "Payée le " + fmt.date(r.paie.date_paie) : "À payer")))),
    r.paie.observation ? el("p", null, el("i", null, r.paie.observation)) : null,
    el("div", { class: "signature" }, el("div", null, "Le formateur", el("div", { class: "trait" }, "")), el("div", null, "La comptabilité", el("div", { class: "trait" }, "")))));
}
