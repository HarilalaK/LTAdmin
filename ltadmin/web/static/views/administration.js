/* Vue : administration (paramètres, établissement, années scolaires, journal, sauvegardes, à propos). */
"use strict";

const LIBELLES_PARAMETRES = {
  BAREME_DEFAUT: "Barème par défaut des évaluations", MOY_ADMISSION: "Moyenne d’admission (/20)", NOTE_ELIMINATOIRE: "Note éliminatoire par défaut (/20)",
  POIDS_CC: "Poids du contrôle continu (%)", POIDS_EXAMEN: "Poids de l’examen (%)", SEUIL_ABSENCE: "Seuil d’alerte d’absence (heures)", DEVISE: "Devise",
};

App.register("administration", {
  async render(container, { params }) {
    const onglets = [{ key: "parametres", label: "Paramètres" }, { key: "etablissement", label: "Établissement" }, { key: "annees", label: "Années scolaires" }, { key: "journal", label: "Journal" }, { key: "sauvegardes", label: "Sauvegardes" }, { key: "apropos", label: "À propos" }];
    let actif = onglets.some((o) => o.key === params.onglet) ? params.onglet : "parametres";
    const barre = el("div"), corps = el("div");
    const afficher = () => {
      clear(barre); barre.appendChild(tabs(onglets, actif, (k) => { actif = k; history.replaceState(null, "", "#/administration?onglet=" + k); afficher(); }));
      clear(corps); corps.appendChild(SECTIONS_ADMIN[actif]());
    };
    append(container, [pageHeader("Administration", "Règles de gestion, identité de l’établissement, années, journal d’audit et sauvegardes."), barre, corps]);
    afficher();
  },
});

const SECTIONS_ADMIN = {
  parametres: () => {
    const zone = el("div");
    const charger = async () => {
      clear(zone); zone.appendChild(loading());
      const rows = await API.value("/api/admin/parametres");
      clear(zone);
      zone.appendChild(el("div", { class: "info mb" }, "Ces valeurs pilotent les calculs (barèmes, pondération CC/examen, seuil d’absence). La somme POIDS_CC + POIDS_EXAMEN doit faire 100."));
      zone.appendChild(dataTable([
        { key: "cle", label: "Clé", cls: "mono" }, { label: "Libellé", render: (r) => LIBELLES_PARAMETRES[r.cle] || r.description || "" },
        { label: "Valeur", render: (r) => el("b", null, r.valeur) }, { key: "description", label: "Description" },
        { label: "", cls: "actions", render: (r) => button("Modifier", async () => {
          const ok = await modal.form({ title: "Paramètre " + r.cle, size: "etroite", fields: [{ name: "valeur", label: LIBELLES_PARAMETRES[r.cle] || r.cle, required: true, span: 12, help: r.description }], values: { valeur: r.valeur },
            onSubmit: async (v) => { const x = await API.put("/api/admin/parametres/" + encodeURIComponent(r.cle), { valeur: v.valeur }); toast.success(x.message); } });
          if (ok) { const s = await API.value("/api/auth/session"); App.session = s; charger(); }
        }, "petit") },
      ], rows, { empty: "Aucun paramètre." }));
    };
    charger();
    return zone;
  },

  etablissement: () => {
    const zone = el("div");
    (async () => {
      const e = await API.value("/api/admin/etablissement");
      const form = buildForm([
        { name: "code_etab", label: "Code", type: "readonly", span: 3 }, { name: "sigle", label: "Sigle", span: 3, required: true }, { name: "nom_etab", label: "Nom de l’établissement", span: 6, required: true },
        { name: "adresse", label: "Adresse", span: 12 }, { name: "tel", label: "Téléphone", span: 4 }, { name: "email", label: "E-mail", span: 4 }, { name: "site_web", label: "Site web", span: 4 },
        { name: "directeur", label: "Directeur / directrice", span: 6 }, { name: "logo", label: "Logo (chemin du fichier)", span: 6 },
      ], e);
      const errorBox = el("div", { class: "erreurs hidden" });
      zone.appendChild(card("Identité de l’établissement (en-têtes des bulletins et reçus)", el("div", null, errorBox, form.element, el("div", { class: "mt" }, button("Enregistrer", async () => {
        try { const r = await API.put("/api/admin/etablissement", form.read()); toast.success(r.message); errorBox.classList.add("hidden"); App.session = (await API.value("/api/auth/session")); App.renderMenu(); }
        catch (ex) { if (ex instanceof ApiError) showErrors(errorBox, ex.message, ex.errors); else reportError(ex); }
      }, "primaire")))));
    })();
    return zone;
  },

  annees: () => crudSection({
    title: "Années scolaires", singular: "année scolaire", url: "/api/admin/annees", idKey: "id_annee", label: (r) => r.libelle,
    description: "Une seule année est active : elle filtre les classes, périodes et statistiques.",
    load: async () => API.value("/api/ref/annees"),
    columns: [
      { key: "libelle", label: "Libellé" }, { label: "Début", render: (r) => fmt.date(r.date_debut) }, { label: "Fin", render: (r) => fmt.date(r.date_fin) },
      { label: "Active", render: (r) => r.active ? el("span", { class: "badge vert" }, "Année active") : button("Activer", async () => {
        if (!await modal.confirm({ title: "Activer l’année", message: `Faire de « ${r.libelle} » l’année active ? L’année actuellement active sera désactivée.`, ok: "Activer" })) return;
        try { const x = await API.post(`/api/admin/annees/${r.id_annee}/activer`); toast.success(x.message); App.session = (await API.value("/api/auth/session")); App.invalidateRef(); App.renderMenu(); App.refresh(); } catch (ex) { reportError(ex); }
      }, "petit") },
    ],
    deletable: () => false,
    fields: () => [
      { name: "libelle", label: "Libellé", required: true, span: 12, placeholder: "2026-2027" },
      { name: "date_debut", label: "Début", type: "date", required: true, span: 6 }, { name: "date_fin", label: "Fin", type: "date", required: true, span: 6 },
    ],
    afterSave: () => App.invalidateRef(),
  }),

  journal: () => {
    const depuis = el("input", { type: "date", value: fmt.isoDate(new Date(Date.now() - 7 * 86400000).toISOString()) });
    const utilisateur = el("input", { type: "text", placeholder: "Code utilisateur" });
    const action = selectInput(["CONNEXION", "CONNEXION_ECHEC", "DECONNEXION", "CREATION", "MODIFICATION", "SUPPRESSION", "ENCAISSEMENT", "ANNULATION", "GENERATION", "SAUVEGARDE", "RESTAURATION", "EXPORT"], "", { placeholder: "Toutes les actions" });
    const zone = el("div");
    const charger = async () => {
      clear(zone); zone.appendChild(loading());
      const rows = await API.value("/api/admin/journal" + API.qs({ depuis: depuis.value, utilisateur: utilisateur.value.trim(), action: action.value, max: 1000 }));
      clear(zone);
      zone.appendChild(el("div", { class: "compteur" }, rows.length + " opération(s)" + (rows.length >= 1000 ? " — 1000 premières affichées" : "")));
      zone.appendChild(dataTable([
        { label: "Date", render: (r) => fmt.datetime(r.date_log), cls: "nowrap" }, { key: "code_utr", label: "Utilisateur" }, { key: "action_log", label: "Action" },
        { key: "table_cible", label: "Cible" }, { key: "id_cible", label: "Id", num: true }, { key: "detail", label: "Détail" },
      ], rows, { empty: "Aucune opération sur la période." }));
    };
    [depuis, utilisateur, action].forEach((i) => i.addEventListener("change", charger));
    charger();
    return el("div", null, el("div", { class: "filtres" }, filterField("Depuis le", depuis), filterField("Utilisateur", utilisateur), filterField("Action", action, "large")), zone);
  },

  sauvegardes: () => {
    const zone = el("div");
    const charger = async () => {
      clear(zone); zone.appendChild(loading());
      const d = await API.value("/api/admin/sauvegardes?securite=1");
      clear(zone);
      zone.appendChild(el("div", { class: "info mb" }, "Dossier : ", el("code", null, d.dossier), ". Les fichiers « securite_avant_restauration_* » et « *_avant_migration_* » sont des copies de sécurité automatiques."));
      zone.appendChild(dataTable([
        { key: "file_name", label: "Fichier", cls: "mono" }, { label: "Créée le", render: (r) => fmt.datetime(r.created_at), cls: "nowrap" }, { key: "size_text", label: "Taille", num: true },
        { label: "", cls: "actions", render: (r) => button("Restaurer", async () => {
          if (!await modal.confirm({ title: "Restaurer la base", message: `Remplacer la base actuelle par « ${r.file_name} » ? Une copie de sécurité de la base actuelle est créée avant l’opération. Toutes les modifications postérieures à cette sauvegarde seront perdues.`, ok: "Restaurer", danger: true })) return;
          try { const x = await API.post("/api/admin/sauvegardes/restaurer", { file_path: r.file_path }); toast.success(x.message); App.invalidateRef(); charger(); } catch (ex) { reportError(ex); }
        }, "petit danger") },
      ], d.sauvegardes, { empty: "Aucune sauvegarde." }));
    };
    charger();
    return el("div", null,
      el("div", { class: "flex mb" },
        button("Créer une sauvegarde maintenant", async () => { try { const r = await API.post("/api/admin/sauvegardes"); toast.success(r.message); charger(); } catch (ex) { reportError(ex); } }, "primaire"),
        button("Purger (conserver les 10 plus récentes)", async () => {
          if (!await modal.confirm({ title: "Purger les sauvegardes", message: "Supprimer les sauvegardes les plus anciennes au-delà des 10 plus récentes ?", ok: "Purger", danger: true })) return;
          try { const r = await API.post("/api/admin/sauvegardes/purger", { conserver: 10 }); toast.success(r.message); charger(); } catch (ex) { reportError(ex); }
        })),
      zone);
  },

  apropos: () => {
    const zone = el("div");
    (async () => {
      const i = await API.value("/api/admin/info");
      zone.appendChild(el("div", { class: "grille c2" },
        card("Application", el("dl", { class: "kv" }, ligneKv("Version", "LTAdmin " + i.version), ligneKv("Python", i.python), ligneKv("SQLite", i.sqlite), ligneKv("Système", i.systeme), ligneKv("Démarrée le", fmt.datetime(i.demarrage)), ligneKv("Sessions actives", i.sessions_actives))),
        card("Base de données", el("dl", { class: "kv" }, ligneKv("Fichier", el("code", null, i.base)), ligneKv("Taille", i.taille_base_texte), ligneKv("Tables", i.nb_tables), ligneKv("Sauvegardes", el("code", null, i.dossier_sauvegardes)))),
      ));
      const lignes = Object.entries(i.lignes_par_table).sort((a, b) => a[0].localeCompare(b[0]));
      zone.appendChild(el("div", { class: "mt" }, card("Volumétrie", dataTable([{ label: "Table", render: (r) => el("code", null, r[0]) }, { label: "Lignes", num: true, render: (r) => fmt.int(r[1]) }], lignes))));
    })();
    return zone;
  },
};
