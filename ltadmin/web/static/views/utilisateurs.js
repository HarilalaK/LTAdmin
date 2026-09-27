/* Vue : comptes utilisateurs et profils d'habilitation. */
"use strict";

App.register("utilisateurs", {
  async render(container) {
    const profils = await API.value("/api/profils");
    const zone = el("div");
    const charger = async () => {
      clear(zone); zone.appendChild(loading());
      const rows = await API.value("/api/utilisateurs");
      clear(zone);
      zone.appendChild(dataTable([
        { key: "code_utr", label: "Identifiant", cls: "mono" }, { key: "nom_utr", label: "Nom" },
        { label: "Profil", render: (r) => el("span", null, r.profil_normalise, r.profil !== r.profil_normalise ? el("span", { class: "muted small" }, " (" + r.profil + ")") : null) },
        { label: "Actif", render: (r) => fmt.oui(r.actif) },
        { label: "", cls: "actions", render: (r) => actionButtons([
          { label: "Modifier", onClick: () => editerUtilisateur(r, profils).then((ok) => ok && charger()) },
          r.code_utr !== App.session.login && { label: r.actif ? "Désactiver" : "Activer", cls: r.actif ? "danger" : "", onClick: async () => { try { const x = await API.post(`/api/utilisateurs/${encodeURIComponent(r.code_utr)}/actif`, { actif: !r.actif }); toast.success(x.message); charger(); } catch (ex) { reportError(ex); } } },
          r.code_utr !== App.session.login && { label: "Supprimer", cls: "danger", onClick: async () => {
            if (!await modal.confirm({ title: "Supprimer le compte", message: `Supprimer le compte « ${r.code_utr} » ? Son historique dans le journal est conservé.`, ok: "Supprimer", danger: true })) return;
            try { const x = await API.del("/api/utilisateurs/" + encodeURIComponent(r.code_utr)); toast.success(x.message); charger(); } catch (ex) { reportError(ex); }
          } },
        ]) },
      ], rows, { empty: "Aucun compte." }));
    };
    charger();
    append(container, [
      pageHeader("Profils utilisateurs", "Comptes de connexion et droits d’accès par profil.", [button("+ Nouveau compte", () => editerUtilisateur(null, profils).then((ok) => ok && charger()), "primaire")]),
      el("div", { class: "grille", style: { gridTemplateColumns: "1fr 380px" } },
        zone,
        card("Droits par profil", el("div", { class: "stack" }, profils.map((p) => el("div", null, el("b", null, p.libelle), el("div", { class: "small muted" }, p.modules.join(" · "))))))),
    ]);
  },
});

async function editerUtilisateur(u, profils) {
  const creation = !u;
  return modal.form({
    title: creation ? "Nouveau compte" : "Modifier le compte " + u.code_utr, size: "etroite",
    fields: [
      { name: "code_utr", label: "Identifiant", required: true, span: 12, upper: true, maxlength: 20, disabled: !creation, help: "Lettres et chiffres, sans espaces." },
      { name: "nom_utr", label: "Nom affiché", required: true, span: 12 },
      { name: "profil", label: "Profil", type: "select", required: true, span: 12, options: profils.map((p) => p.libelle) },
      { name: "mot_de_passe", label: creation ? "Mot de passe" : "Nouveau mot de passe (laisser vide pour conserver)", type: "password", span: 12, required: creation, help: "4 caractères minimum." },
      { name: "actif", label: "Compte actif", type: "check", span: 12 },
    ],
    values: u ? Object.assign({}, u, { profil: u.profil_normalise }) : { actif: true, profil: "Scolarité" },
    onSubmit: async (v) => { const r = await API.post("/api/utilisateurs", Object.assign({}, v, { code_utr: creation ? v.code_utr : u.code_utr })); toast.success(r.message); },
  });
}
