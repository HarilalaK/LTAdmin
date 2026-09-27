/* Vue : maintenance générique des tables (réservée à l'administrateur). */
"use strict";

App.register("tables", {
  async render(container) {
    const tables = await API.value("/api/tables");
    const selectTable = selectInput(tables.map((t) => ({ value: t.name, label: `${t.name} (${t.count})` })), tables[0] && tables[0].name, {});
    const recherche = el("input", { type: "search", placeholder: "Recherche dans les colonnes texte…" });
    const zone = el("div");
    let table = null;
    const charger = async () => {
      clear(zone); zone.appendChild(loading());
      const d = await API.value("/api/tables/" + encodeURIComponent(selectTable.value) + API.qs({ q: recherche.value.trim(), max: 500 }));
      table = d;
      clear(zone);
      const pk = d.columns.filter((c) => c.is_primary_key).map((c) => c.name);
      zone.appendChild(el("div", { class: "compteur" }, `${d.rows.length} ligne(s) affichée(s) sur ${d.count} · clé primaire : ${pk.join(", ") || "aucune"}`));
      zone.appendChild(dataTable(d.columns.map((c) => ({ label: c.name + (c.is_primary_key ? " 🔑" : ""), render: (r) => formatValeurBrute(r[c.name]), cls: "small" }))
        .concat([{ label: "", cls: "actions", render: (r) => d.name.toUpperCase() === "UTILISATEUR" ? "" : actionButtons([
          { label: "Modifier", onClick: () => editerLigne(d, r).then((ok) => ok && charger()) },
          { label: "Supprimer", cls: "danger", onClick: async () => {
            if (!await modal.confirm({ title: "Supprimer la ligne", message: "Supprimer cette ligne ? Les contraintes d’intégrité (clés étrangères) peuvent refuser l’opération.", ok: "Supprimer", danger: true })) return;
            try { const x = await API.post(`/api/tables/${encodeURIComponent(d.name)}/supprimer`, { row: r }); toast.success(x.message); charger(); } catch (ex) { reportError(ex); }
          } },
        ]) }]), d.rows, { empty: "Table vide." }));
    };
    selectTable.addEventListener("change", charger);
    recherche.addEventListener("input", debounce(charger, 300));
    append(container, [
      pageHeader("Tables (maintenance)", "Accès direct aux 33 tables. Réservé aux corrections exceptionnelles : privilégiez toujours les écrans métier.", [
        button("+ Insérer une ligne", () => table && editerLigne(table, null).then((ok) => ok && charger()), "primaire"),
      ]),
      el("div", { class: "avert mb" }, "Les modifications ici contournent les règles de gestion (journal, validations métier). Faites une sauvegarde avant toute intervention."),
      el("div", { class: "filtres" }, filterField("Table", selectTable, "large"), filterField("Recherche", recherche, "large")),
      zone,
    ]);
    await charger();
  },
});

function formatValeurBrute(v) {
  if (v === null || v === undefined) return el("span", { class: "muted" }, "NULL");
  const s = String(v);
  return s.length > 60 ? s.slice(0, 57) + "…" : s;
}

async function editerLigne(table, row) {
  const creation = !row;
  const fields = table.columns.filter((c) => !(creation && c.autonumber)).map((c) => ({
    name: c.name, label: c.name + (c.nullable ? "" : " *") + " — " + c.kind + (c.size ? "(" + c.size + ")" : ""), span: 6,
    type: c.autonumber || (c.is_primary_key && !creation) ? "readonly" : (c.kind === "MEMO" ? "textarea" : "text"),
  }));
  return modal.form({
    title: (creation ? "Insérer dans " : "Modifier ") + table.name, fields, values: row || {}, size: "large",
    onSubmit: async (v) => {
      const values = {};
      Object.entries(v).forEach(([k, val]) => { values[k] = val; });
      const r = creation ? await API.post("/api/tables/" + encodeURIComponent(table.name), { values })
        : await API.put("/api/tables/" + encodeURIComponent(table.name), { original: row, values });
      toast.success(r.message);
    },
  });
}
