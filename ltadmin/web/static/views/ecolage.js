/* Vue : écolage (tarifs, échéanciers, encaissements, reçus, remises, situation par classe). */
"use strict";

const MODES_PAIEMENT = ["Espèces", "Mobile money", "Virement", "Chèque", "Autre"];

App.register("ecolage", {
  async render(container, { params, segments }) {
    const onglets = [{ key: "situation", label: "Situation par classe" }, { key: "etudiant", label: "Dossier étudiant" }, { key: "tarifs", label: "Tarifs" }];
    let actif = segments[0] && onglets.some((o) => o.key === segments[0]) ? segments[0] : (onglets.some((o) => o.key === params.onglet) ? params.onglet : "situation");
    const barre = el("div"), corps = el("div");
    const afficher = () => {
      clear(barre); barre.appendChild(tabs(onglets, actif, (k) => { actif = k; history.replaceState(null, "", "#/ecolage/" + k); afficher(); }));
      clear(corps);
      corps.appendChild(actif === "situation" ? sectionSituation(params) : actif === "etudiant" ? sectionDossierEcolage(params) : sectionTarifs(params));
    };
    append(container, [pageHeader("Écolage", "Frais de scolarité : tarifs par classe, échéanciers, encaissements et reçus (" + App.devise() + ")."), barre, corps]);
    afficher();
  },
});

function sectionTarifs(params) {
  const classes = App.classesActives();
  const selectClasse = selectInput(classeOptions(classes), params.classe || (classes[0] && classes[0].id_classe), { placeholder: "— Classe —" });
  const zone = el("div");
  const charger = async () => {
    clear(zone);
    if (!selectClasse.value) { zone.appendChild(el("div", { class: "info" }, "Choisissez une classe.")); return; }
    zone.appendChild(loading());
    const rows = await API.value("/api/tarifs" + API.qs({ classe: selectClasse.value }));
    clear(zone);
    zone.appendChild(dataTable([
      { key: "type_frais", label: "Type de frais" }, { label: "Montant", num: true, render: (r) => fmt.money(r.montant, "") },
      { label: "Tranches", num: true, key: "nb_tranches" }, { label: "Par tranche", num: true, render: (r) => fmt.money(r.montant / (r.nb_tranches || 1), "") },
      { label: "Obligatoire", render: (r) => fmt.oui(r.obligatoire) }, { key: "observation", label: "Observation" },
      { label: "", cls: "actions", render: (r) => actionButtons([
        { label: "Modifier", onClick: () => editerTarif(r, selectClasse.value).then((ok) => ok && charger()) },
        { label: "Supprimer", cls: "danger", onClick: async () => {
          if (!await modal.confirm({ title: "Supprimer le tarif", message: `Supprimer le tarif « ${r.type_frais} » ? Refusé si des échéanciers l’utilisent.`, ok: "Supprimer", danger: true })) return;
          try { const x = await API.del("/api/tarifs/" + r.id_tarif); toast.success(x.message); charger(); } catch (ex) { reportError(ex); }
        } },
      ]) },
    ], rows, { empty: "Aucun tarif défini pour cette classe.", foot: ["Total", fmt.money(rows.reduce((s, r) => s + Number(r.montant || 0), 0), ""), "", "", "", "", ""] }));
  };
  selectClasse.addEventListener("change", charger);
  charger();
  return el("div", null,
    el("div", { class: "filtres" }, filterField("Classe", selectClasse, "large"), el("div", { class: "grow" }),
      button("+ Nouveau tarif", () => { if (!selectClasse.value) { toast.warn("Choisissez une classe."); return; } editerTarif(null, selectClasse.value).then((ok) => ok && charger()); }, "primaire")),
    zone);
}

async function editerTarif(t, idClasse) {
  const creation = !t;
  return modal.form({
    title: creation ? "Nouveau tarif" : "Modifier le tarif",
    fields: [
      { name: "id_classe", label: "Classe", type: "select", required: true, span: 12, options: classeOptions(App.ref.classes), disabled: !creation },
      { name: "type_frais", label: "Type de frais", type: "select", required: true, span: 6, options: ["ECOLAGE", "INSCRIPTION", "TENUE", "EXAMEN", "ASSURANCE", "AUTRE"] },
      { name: "montant", label: "Montant total (" + App.devise() + ")", type: "money", required: true, span: 6, min: 1 },
      { name: "nb_tranches", label: "Nombre de tranches", type: "number", required: true, span: 6, min: 1, max: 24, step: "1", help: "Les échéances sont espacées d’un mois." },
      { name: "obligatoire", label: "Obligatoire", type: "check", span: 6 },
      { name: "observation", label: "Observation", type: "textarea", span: 12, rows: 2 },
    ],
    values: t || { id_classe: Number(idClasse), type_frais: "ECOLAGE", nb_tranches: 3, obligatoire: true },
    onSubmit: async (v) => { const r = await API.post("/api/tarifs", creation ? v : Object.assign({}, v, { id_tarif: t.id_tarif, id_classe: t.id_classe })); toast.success(r.message); },
  });
}

function sectionSituation(params) {
  const classes = App.classesActives();
  const selectClasse = selectInput(classeOptions(classes), params.classe || (classes[0] && classes[0].id_classe), { placeholder: "— Classe —" });
  const zone = el("div");
  const charger = async () => {
    clear(zone);
    if (!selectClasse.value) { zone.appendChild(el("div", { class: "info" }, "Choisissez une classe.")); return; }
    zone.appendChild(loading());
    const rows = await API.value("/api/ecolage/situation" + API.qs({ classe: selectClasse.value }));
    clear(zone);
    const tot = (k) => rows.reduce((s, r) => s + Number(r[k] || 0), 0);
    zone.appendChild(el("div", { class: "grille c4 mb" },
      indicateur("Total dû", fmt.money(tot("total_du")), rows.length + " inscrit(s)"), indicateur("Encaissé", fmt.money(tot("total_paye")), "", "succes"),
      indicateur("Reste à encaisser", fmt.money(tot("reste")), ""), indicateur("Échu non payé", fmt.money(tot("montant_echu")), rows.filter((r) => r.nb_echues).length + " dossier(s) en retard", tot("montant_echu") > 0 ? "alerte" : "")));
    zone.appendChild(dataTable([
      { key: "matricule", label: "Matricule", cls: "mono nowrap" }, { key: "nom", label: "Nom" }, { key: "prenom", label: "Prénom(s)" },
      { label: "Dû", num: true, render: (r) => fmt.money(r.total_du, "") }, { label: "Payé", num: true, render: (r) => fmt.money(r.total_paye, "") },
      { label: "Reste", num: true, render: (r) => el("b", null, fmt.money(r.reste, "")) }, { label: "Échu", num: true, render: (r) => r.nb_echues ? el("span", { class: "badge rouge" }, fmt.money(r.montant_echu, "")) : "" },
      { label: "Statut", render: (r) => fmt.statut(r.statut) },
      { label: "", cls: "actions", render: (r) => button("Dossier", () => App.navigate("ecolage", { inscription: r.id_inscription }, ["etudiant"]), "petit primaire") },
    ], rows, { empty: "Aucun inscrit dans cette classe.", onRow: (r) => App.navigate("ecolage", { inscription: r.id_inscription }, ["etudiant"]) }));
  };
  selectClasse.addEventListener("change", charger);
  charger();
  return el("div", null, el("div", { class: "filtres" }, filterField("Classe", selectClasse, "large")), zone);
}

function sectionDossierEcolage(params) {
  const classes = App.classesActives();
  const selectClasse = selectInput(classeOptions(classes), params.classe || "", { placeholder: "— Classe —" });
  const selectInscription = selectInput([], "", { placeholder: "— Étudiant —" });
  const zone = el("div");
  const chargerInscrits = async (garder) => {
    clear(selectInscription); selectInscription.appendChild(el("option", { value: "" }, "— Étudiant —"));
    if (!selectClasse.value) return;
    const rows = await API.value("/api/inscriptions" + API.qs({ classe: selectClasse.value }));
    rows.forEach((i) => selectInscription.appendChild(el("option", { value: i.id_inscription }, `${i.nom} ${i.prenom} (${i.matricule})`)));
    if (garder) selectInscription.value = String(garder);
  };
  const charger = async () => {
    clear(zone);
    const id = selectInscription.value;
    if (!id) { zone.appendChild(el("div", { class: "info" }, "Choisissez une classe puis un étudiant, ou ouvrez un dossier depuis la situation de classe.")); return; }
    zone.appendChild(loading());
    const d = await API.value(`/api/inscriptions/${id}/echeances`);
    const tarifs = await API.value("/api/tarifs" + API.qs({ classe: d.inscription.id_classe }));
    clear(zone);
    const i = d.inscription;
    const tarifsUtilises = new Set(d.echeances.map((e) => e.id_tarif));
    const tarifsDisponibles = tarifs.filter((t) => !tarifsUtilises.has(t.id_tarif));
    zone.appendChild(el("div", { class: "grille c4 mb" },
      indicateur("Étudiant", i.nom + " " + i.prenom, i.matricule + " · " + i.classe), indicateur("Total dû", fmt.money(d.total_du), d.echeances.length + " échéance(s)"),
      indicateur("Payé", fmt.money(d.total_paye), "", "succes"), indicateur("Reste", fmt.money(d.reste), "", Number(d.reste) > 0 ? "alerte" : "succes")));
    const aujourdHui = fmt.today();
    zone.appendChild(card("Échéancier", dataTable([
      { key: "libelle", label: "Échéance" }, { label: "Date", render: (r) => { const retard = r.statut !== "SOLDE" && fmt.isoDate(r.date_echeance) < aujourdHui; return el("span", { class: retard ? "badge rouge" : "" }, fmt.date(r.date_echeance)); }, cls: "nowrap" },
      { label: "Montant", num: true, render: (r) => fmt.money(r.montant_du, "") }, { label: "Remise", num: true, render: (r) => Number(r.remise) ? fmt.money(r.remise, "") : "" },
      { label: "Net dû", num: true, render: (r) => fmt.money(r.net_du, "") }, { label: "Payé", num: true, render: (r) => fmt.money(r.total_paye, "") },
      { label: "Reste", num: true, render: (r) => el("b", null, fmt.money(r.reste, "")) }, { label: "Statut", render: (r) => fmt.statut(r.statut) },
      { label: "", cls: "actions", render: (r) => actionButtons([
        Number(r.reste) > 0 && { label: "Encaisser", cls: "primaire", onClick: () => encaisser(r).then((ok) => ok && charger()) },
        { label: "Paiements", onClick: () => listerPaiements(r).then((changed) => changed && charger()) },
        { label: "Remise", onClick: () => accorderRemise(r).then((ok) => ok && charger()) },
      ]) },
    ], d.echeances, { empty: "Aucun échéancier : générez-le à partir d’un tarif de la classe." }),
    [
      tarifsDisponibles.length ? button("+ Générer un échéancier", async () => {
        const ok = await modal.form({
          title: "Générer l’échéancier", size: "etroite",
          fields: [{ name: "id_tarif", label: "Tarif", type: "select", required: true, span: 12, options: tarifsDisponibles.map((t) => ({ value: t.id_tarif, label: `${t.type_frais} — ${fmt.money(t.montant)} en ${t.nb_tranches} tranche(s)` })) }],
          submitLabel: "Générer",
          onSubmit: async (v) => { const r = await API.post("/api/echeanciers/generer", { id_inscription: Number(id), id_tarif: v.id_tarif }); toast.success(r.message); },
        });
        if (ok) charger();
      }, "petit primaire") : null,
      tarifsUtilises.size ? button("Supprimer un échéancier", async () => {
        const utilises = tarifs.filter((t) => tarifsUtilises.has(t.id_tarif));
        const ok = await modal.form({
          title: "Supprimer un échéancier (aucun paiement enregistré)", size: "etroite",
          fields: [{ name: "id_tarif", label: "Tarif", type: "select", required: true, span: 12, options: utilises.map((t) => ({ value: t.id_tarif, label: t.type_frais + " — " + fmt.money(t.montant) })) }],
          submitLabel: "Supprimer",
          onSubmit: async (v) => { const r = await API.post("/api/echeanciers/supprimer", { id_inscription: Number(id), id_tarif: v.id_tarif }); toast.success(r.message); },
        });
        if (ok) charger();
      }, "petit danger") : null,
    ]));
  };
  selectClasse.addEventListener("change", async () => { await chargerInscrits(); charger(); });
  selectInscription.addEventListener("change", charger);
  (async () => {
    if (params.inscription) {
      const i = await API.value("/api/inscriptions/" + params.inscription);
      selectClasse.value = String(i.id_classe);
      await chargerInscrits(params.inscription);
    }
    charger();
  })();
  return el("div", null, el("div", { class: "filtres" }, filterField("Classe", selectClasse, "large"), filterField("Étudiant", selectInscription, "large")), zone);
}

async function encaisser(echeance) {
  const paiement = await modal.form({
    title: "Encaisser — " + echeance.libelle, size: "etroite",
    extra: el("div", { class: "info mb" }, "Reste à payer sur cette échéance : ", el("b", null, fmt.money(echeance.reste))),
    fields: [
      { name: "montant", label: "Montant (" + App.devise() + ")", type: "money", required: true, span: 12, min: 1, max: Number(echeance.reste) },
      { name: "mode_paie", label: "Mode de paiement", type: "select", required: true, span: 12, options: MODES_PAIEMENT },
      { name: "ref_externe", label: "Référence (n° de transaction, chèque…)", span: 12 },
      { name: "observation", label: "Observation", span: 12 },
    ],
    values: { montant: Number(echeance.reste), mode_paie: "Espèces" }, submitLabel: "Encaisser et éditer le reçu",
    onSubmit: async (v) => { const r = await API.post(`/api/echeances/${echeance.id_echeance}/encaisser`, v); toast.success(r.message); return r.value; },
  });
  if (paiement && paiement.id_paiement) {
    if (await modal.confirm({ title: "Reçu " + paiement.num_recu, message: "Paiement enregistré. Imprimer le reçu maintenant ?", ok: "Imprimer" })) imprimerRecu(paiement.id_paiement);
  }
  return !!paiement;
}

async function listerPaiements(echeance) {
  return new Promise(async (resolve) => {
    let changed = false, handle;
    const zone = el("div");
    const charger = async () => {
      const rows = await API.value(`/api/echeances/${echeance.id_echeance}/paiements`);
      clear(zone);
      zone.appendChild(dataTable([
        { key: "num_recu", label: "Reçu", cls: "mono nowrap" }, { label: "Date", render: (r) => fmt.datetime(r.date_paiement), cls: "nowrap" },
        { label: "Montant", num: true, render: (r) => fmt.money(r.montant, "") }, { key: "mode_paie", label: "Mode" }, { key: "ref_externe", label: "Référence" }, { key: "code_utr", label: "Caissier" },
        { label: "", cls: "actions", render: (r) => actionButtons([
          { label: "Reçu", onClick: () => imprimerRecu(r.id_paiement) },
          { label: "Annuler", cls: "danger", onClick: async () => {
            if (!await modal.confirm({ title: "Annuler le paiement", message: `Annuler le paiement ${r.num_recu} de ${fmt.money(r.montant)} ? Le statut de l’échéance sera recalculé.`, ok: "Annuler le paiement", danger: true })) return;
            try { const x = await API.del("/api/paiements/" + r.id_paiement); toast.success(x.message); changed = true; charger(); } catch (ex) { reportError(ex); }
          } },
        ]) },
      ], rows, { empty: "Aucun paiement sur cette échéance." }));
    };
    await charger();
    handle = modal.open({ title: "Paiements — " + echeance.libelle, body: zone, size: "large", actions: [button("Fermer", () => { handle.close(); resolve(changed); })], onClose: () => resolve(changed) });
  });
}

async function accorderRemise(echeance) {
  return modal.form({
    title: "Remise — " + echeance.libelle, size: "etroite",
    fields: [{ name: "remise", label: "Montant de la remise (" + App.devise() + ")", type: "money", span: 12, min: 0, max: Number(echeance.montant_du), help: "0 pour retirer la remise. Le statut est recalculé." }],
    values: { remise: Number(echeance.remise || 0) },
    onSubmit: async (v) => { const r = await API.post(`/api/echeances/${echeance.id_echeance}/remise`, { remise: v.remise || 0 }); toast.success(r.message); },
  });
}

async function imprimerRecu(idPaiement) {
  try {
    const d = await API.value("/api/paiements/" + idPaiement);
    const p = d.paiement, e = d.echeance || {}, i = d.inscription || {}, etab = d.etablissement || {};
    const recu = (copie) => el("div", { class: "document", style: { pageBreakInside: "avoid", borderBottom: copie ? "none" : "1px dashed #999", marginBottom: "20px", paddingBottom: "20px" } },
      enteteDocument(etab),
      el("h2", { class: "titre-doc" }, "Reçu de paiement n° " + p.num_recu + (copie ? " — copie caisse" : "")),
      el("table", null, el("tbody", null,
        el("tr", null, el("td", null, el("b", null, "Reçu de : "), (i.nom || "") + " " + (i.prenom || "")), el("td", null, el("b", null, "Matricule : "), i.matricule || "")),
        el("tr", null, el("td", null, el("b", null, "Classe : "), i.classe || ""), el("td", null, el("b", null, "Date : "), fmt.datetime(p.date_paiement))),
        el("tr", null, el("td", null, el("b", null, "Objet : "), e.libelle || ""), el("td", null, el("b", null, "Mode : "), (p.mode_paie || "") + (p.ref_externe ? " — réf. " + p.ref_externe : ""))))),
      el("div", { class: "recu-montant" }, "Montant : " + fmt.money(p.montant, d.devise)),
      el("p", null, `Échéance : net dû ${fmt.money(e.net_du, d.devise)} · total payé ${fmt.money(e.total_paye, d.devise)} · reste ${fmt.money(e.reste, d.devise)} · statut ${e.statut || ""}.`),
      p.observation ? el("p", null, el("i", null, p.observation)) : null,
      el("div", { class: "signature" }, el("div", null, "Le payeur", el("div", { class: "trait" }, "")), el("div", null, "Le caissier" + (d.caissier ? " — " + d.caissier.nom_utr : ""), el("div", { class: "trait" }, ""))));
    printDocument(el("div", null, recu(false), recu(true)));
  } catch (ex) { reportError(ex); }
}
