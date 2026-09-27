/* LTAdmin — coque applicative : session, navigation, routage des vues. */
"use strict";

const App = {
  session: null,
  ref: null,          // référentiel mis en cache (classes, matières, ...)
  refLoadedAt: 0,
  views: {},
  current: null,

  // Modules du menu → clé de vue, icône, groupe.
  MODULES: [
    { module: "Tableau de bord", key: "tableau", icon: "◫", group: "Général" },
    { module: "Étudiants", key: "etudiants", icon: "👤", group: "Scolarité" },
    { module: "Inscriptions", key: "inscriptions", icon: "📝", group: "Scolarité" },
    { module: "Référentiel", key: "referentiel", icon: "🗂", group: "Scolarité" },
    { module: "Formateurs", key: "formateurs", icon: "🎓", group: "Scolarité" },
    { module: "Notes et évaluations", key: "notes", icon: "✎", group: "Pédagogie" },
    { module: "Bulletins", key: "bulletins", icon: "📄", group: "Pédagogie" },
    { module: "Examens", key: "examens", icon: "🏛", group: "Pédagogie" },
    { module: "Emploi du temps", key: "edt", icon: "🗓", group: "Pédagogie" },
    { module: "Absences", key: "absences", icon: "⏱", group: "Pédagogie" },
    { module: "Écolage", key: "ecolage", icon: "💰", group: "Finances" },
    { module: "Paie des formateurs", key: "paie", icon: "💼", group: "Finances" },
    { module: "Statistiques", key: "statistiques", icon: "📊", group: "Pilotage" },
    { module: "Rapports", key: "rapports", icon: "📑", group: "Pilotage" },
    { module: "Administration", key: "administration", icon: "⚙", group: "Système" },
    { module: "Profils utilisateurs", key: "utilisateurs", icon: "🔐", group: "Système" },
    { module: "Tables (maintenance)", key: "tables", icon: "🛠", group: "Système" },
  ],

  register(key, view) { this.views[key] = view; },

  devise() { return (this.session && this.session.parametres && this.session.parametres.DEVISE) || "MGA"; },
  param(cle, defaut) {
    const v = this.session && this.session.parametres ? this.session.parametres[cle] : undefined;
    return v === undefined || v === null || v === "" ? defaut : v;
  },
  can(module) { return !!(this.session && this.session.modules.includes(module)); },
  isAdmin() { return this.session && this.session.role === "Administrateur"; },

  // ----- Référentiel partagé -----
  async loadRef(force = false) {
    if (!force && this.ref && Date.now() - this.refLoadedAt < 60000) return this.ref;
    this.ref = await API.value("/api/ref/tout");
    this.refLoadedAt = Date.now();
    return this.ref;
  },
  invalidateRef() { this.refLoadedAt = 0; },
  classe(id) { return (this.ref && this.ref.classes.find((c) => c.id_classe === Number(id))) || null; },
  matiere(code) { return (this.ref && this.ref.matieres.find((m) => m.code_matiere === code)) || null; },
  classesActives() {
    if (!this.ref) return [];
    const annee = this.session && this.session.annee_active ? this.session.annee_active.id_annee : null;
    const actives = this.ref.classes.filter((c) => !annee || c.id_annee === annee);
    return actives.length ? actives : this.ref.classes;
  },

  // ----- Session -----
  async start() {
    API.onUnauthorized = () => this.showLogin("Votre session a expiré : reconnectez-vous.");
    document.getElementById("form-connexion").addEventListener("submit", (e) => { e.preventDefault(); this.login(); });
    try {
      const payload = await API.get("/api/auth/session");
      this.openSession(payload.value);
    } catch (ex) {
      this.showLogin();
    }
  },
  showLogin(message = "") {
    this.session = null;
    document.getElementById("application").classList.add("hidden");
    document.getElementById("connexion").classList.remove("hidden");
    document.getElementById("connexion-erreur").textContent = message;
    const login = document.getElementById("login");
    setTimeout(() => login.focus(), 50);
  },
  async login() {
    const login = document.getElementById("login").value.trim();
    const mot = document.getElementById("mot-de-passe").value;
    const erreur = document.getElementById("connexion-erreur");
    const bouton = document.getElementById("bouton-connexion");
    erreur.textContent = "";
    if (!login || !mot) { erreur.textContent = "Saisissez votre identifiant et votre mot de passe."; return; }
    bouton.disabled = true;
    try {
      const payload = await API.post("/api/auth/connexion", { login, mot_de_passe: mot });
      document.getElementById("mot-de-passe").value = "";
      this.openSession(payload.value);
    } catch (ex) {
      erreur.textContent = ex.message;
    } finally {
      bouton.disabled = false;
    }
  },
  async logout() {
    try { await API.post("/api/auth/deconnexion"); } catch (ex) { /* ignoré */ }
    this.invalidateRef();
    location.hash = "#/tableau";
    this.showLogin("Session fermée.");
  },
  openSession(session) {
    this.session = session;
    document.getElementById("connexion").classList.add("hidden");
    document.getElementById("application").classList.remove("hidden");
    this.renderMenu();
    window.onhashchange = () => this.route();
    if (!location.hash || location.hash === "#/") location.hash = "#/tableau";
    else this.route();
  },

  // ----- Menu -----
  renderMenu() {
    const nav = document.getElementById("navigation");
    clear(nav);
    let group = null;
    this.MODULES.filter((m) => this.session.modules.includes(m.module)).forEach((m) => {
      if (m.group !== group) { group = m.group; nav.appendChild(el("div", { class: "groupe" }, group)); }
      nav.appendChild(el("a", { href: "#/" + m.key, "data-key": m.key },
        el("span", { class: "ico" }, m.icon), m.module));
    });
    const etab = this.session.etablissement || {};
    document.getElementById("menu-titre").textContent = etab.sigle || "LTAdmin";
    document.getElementById("menu-sous").textContent = etab.nom_etab || "Gestion scolaire";
    document.getElementById("menu-utilisateur").textContent = this.session.display_name || this.session.login;
    document.getElementById("menu-role").textContent = this.session.role + " · " + this.session.login;
    document.getElementById("barre-annee").textContent = this.session.annee_active
      ? "Année " + this.session.annee_active.libelle : "Aucune année active";
    document.getElementById("menu-version").textContent = "LTAdmin " + this.session.version + " · " + this.session.database;
  },

  // ----- Routage -----
  parseHash() {
    const hash = location.hash.replace(/^#\/?/, "");
    const [path, query] = hash.split("?");
    const segments = path.split("/").filter(Boolean);
    const params = {};
    (query || "").split("&").filter(Boolean).forEach((p) => {
      const [k, v] = p.split("=");
      params[decodeURIComponent(k)] = v === undefined ? "" : decodeURIComponent(v);
    });
    return { key: segments[0] || "tableau", segments: segments.slice(1), params };
  },
  navigate(key, params = {}, segments = []) {
    location.hash = "#/" + [key, ...segments].join("/") + API.qs(params);
  },
  async route() {
    if (!this.session) return;
    const { key, segments, params } = this.parseHash();
    const def = this.MODULES.find((m) => m.key === key);
    const view = this.views[key];
    if (!def || !view) { this.navigate("tableau"); return; }
    if (!this.session.modules.includes(def.module)) {
      toast.warn("Module « " + def.module + " » non autorisé pour votre profil.");
      this.navigate("tableau");
      return;
    }
    document.querySelectorAll("#navigation a").forEach((a) => a.classList.toggle("actif", a.dataset.key === key));
    document.getElementById("barre-fil").innerHTML = `<b>${fmt.escape(def.module)}</b>`;
    const zone = document.getElementById("vue");
    clear(zone);
    zone.appendChild(loading());
    this.current = key;
    try {
      await this.loadRef();
      const container = el("div");
      await view.render(container, { segments, params, key });
      if (this.current !== key) return;
      clear(zone);
      zone.appendChild(container);
      window.scrollTo(0, 0);
    } catch (ex) {
      clear(zone);
      zone.appendChild(el("div", { class: "erreurs" }, "Impossible d’afficher cet écran : " + (ex.message || ex)));
      reportError(ex);
    }
  },
  refresh() { this.route(); },

  async changePassword() {
    await modal.form({
      title: "Changer mon mot de passe", size: "etroite",
      fields: [
        { name: "ancien", label: "Mot de passe actuel", type: "password", span: 12, required: true },
        { name: "nouveau", label: "Nouveau mot de passe", type: "password", span: 12, required: true, help: "4 caractères minimum." },
        { name: "confirmation", label: "Confirmation", type: "password", span: 12, required: true },
      ],
      onSubmit: async (v) => {
        if (v.nouveau !== v.confirmation) throw new ApiError({ message: "La confirmation ne correspond pas." });
        const r = await API.post("/api/auth/mot-de-passe", { ancien: v.ancien, nouveau: v.nouveau });
        toast.success(r.message);
      },
    });
  },
};

window.addEventListener("DOMContentLoaded", () => App.start());
