/* LTAdmin — noyau de l'interface : appels API, mise en forme, composants. */
"use strict";

// ---------------------------------------------------------------------------
// Appels API
// ---------------------------------------------------------------------------

class ApiError extends Error {
  constructor(payload, status) {
    super((payload && payload.message) || "Erreur inattendue.");
    this.payload = payload || {};
    this.status = status;
    this.code = this.payload.code || null;
    this.errors = this.payload.errors || [];
  }
  get fullMessage() {
    return this.errors.length ? this.message + "\n• " + this.errors.join("\n• ") : this.message;
  }
}

const API = {
  onUnauthorized: null,
  async request(method, url, body) {
    const options = { method, headers: { "Accept": "application/json" }, credentials: "same-origin" };
    if (body !== undefined) {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
    let response;
    try {
      response = await fetch(url, options);
    } catch (ex) {
      throw new ApiError({ message: "Le serveur local ne répond pas. Relancez l’application.", code: "RESEAU" }, 0);
    }
    const type = response.headers.get("Content-Type") || "";
    if (!type.includes("json")) {
      if (!response.ok) throw new ApiError({ message: `Erreur HTTP ${response.status}.` }, response.status);
      return response;
    }
    const payload = await response.json();
    if (response.status === 401 && API.onUnauthorized && !url.startsWith("/api/auth/")) {
      API.onUnauthorized();
    }
    if (!response.ok || payload.ok === false) throw new ApiError(payload, response.status);
    return payload;
  },
  get(url) { return this.request("GET", url); },
  post(url, body) { return this.request("POST", url, body === undefined ? {} : body); },
  put(url, body) { return this.request("PUT", url, body === undefined ? {} : body); },
  del(url) { return this.request("DELETE", url); },
  /** Valeur d'une réponse GET. */
  async value(url) { return (await this.get(url)).value; },
  qs(params) {
    const parts = [];
    Object.entries(params || {}).forEach(([k, v]) => {
      if (v === undefined || v === null || v === "") return;
      parts.push(encodeURIComponent(k) + "=" + encodeURIComponent(v));
    });
    return parts.length ? "?" + parts.join("&") : "";
  },
};

// ---------------------------------------------------------------------------
// Mise en forme (français)
// ---------------------------------------------------------------------------

const fmt = {
  date(value) {
    if (!value) return "";
    const s = String(value);
    const m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
    return m ? `${m[3]}/${m[2]}/${m[1]}` : s;
  },
  datetime(value) {
    if (!value) return "";
    const s = String(value);
    const m = s.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
    return m ? `${m[3]}/${m[2]}/${m[1]} ${m[4]}:${m[5]}` : fmt.date(s);
  },
  /** Date HTML (AAAA-MM-JJ) depuis une valeur API. */
  isoDate(value) {
    if (!value) return "";
    const m = String(value).match(/^(\d{4}-\d{2}-\d{2})/);
    return m ? m[1] : "";
  },
  today() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  },
  number(value, decimals = 2) {
    if (value === null || value === undefined || value === "") return "";
    const n = Number(value);
    if (Number.isNaN(n)) return String(value);
    return n.toLocaleString("fr-FR", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  },
  int(value) { return fmt.number(value, 0); },
  money(value, devise) {
    if (value === null || value === undefined || value === "") return "";
    const n = Number(value);
    if (Number.isNaN(n)) return String(value);
    const txt = n.toLocaleString("fr-FR", { minimumFractionDigits: 0, maximumFractionDigits: 2 });
    return devise === undefined ? `${txt} ${App.devise()}` : (devise ? `${txt} ${devise}` : txt);
  },
  note(value) {
    if (value === null || value === undefined || value === "") return "";
    return fmt.number(value, 2);
  },
  bool(value) { return value ? "Oui" : "Non"; },
  hours(value) { return value === null || value === undefined ? "" : fmt.number(value, 1) + " h"; },
  statut(value) {
    const s = String(value || "").toUpperCase();
    const classes = { SOLDE: "vert", PARTIEL: "ambre", DU: "rouge", INSCRIT: "vert", SORTI: "rouge", ADMIS: "vert", AJOURNE: "rouge", REDOUBLE: "ambre", ACTIVE: "vert", FAITE: "vert", ANNULEE: "rouge", REPORTEE: "ambre", PLANIFIEE: "bleu" };
    return el("span", { class: "badge " + (classes[s] || "") }, value || "—");
  },
  oui(value) { return el("span", { class: "badge " + (value ? "vert" : "") }, value ? "Oui" : "Non"); },
  escape(text) {
    return String(text === null || text === undefined ? "" : text)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  },
};

// ---------------------------------------------------------------------------
// Construction du DOM
// ---------------------------------------------------------------------------

function el(tag, attrs, ...children) {
  const node = document.createElement(tag);
  if (attrs) {
    Object.entries(attrs).forEach(([key, value]) => {
      if (value === null || value === undefined || value === false) return;
      if (key === "class") node.className = value;
      else if (key === "style" && typeof value === "object") Object.assign(node.style, value);
      else if (key.startsWith("on") && typeof value === "function") node.addEventListener(key.slice(2).toLowerCase(), value);
      else if (key === "html") node.innerHTML = value;
      else if (key === "value") node.value = value;
      else if (key === "checked") node.checked = !!value;
      else if (key === "disabled") node.disabled = !!value;
      else node.setAttribute(key, value === true ? "" : value);
    });
  }
  append(node, children);
  return node;
}

function append(node, children) {
  children.flat(Infinity).forEach((child) => {
    if (child === null || child === undefined || child === false) return;
    node.appendChild(child instanceof Node ? child : document.createTextNode(String(child)));
  });
  return node;
}

function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); return node; }

function button(label, onClick, cls = "", attrs = {}) {
  return el("button", Object.assign({ type: "button", class: cls, onClick }, attrs), label);
}

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

const toast = {
  show(message, kind = "info", duration = 3800) {
    const zone = document.getElementById("notifications");
    const node = el("div", { class: "notif " + kind }, message);
    zone.appendChild(node);
    setTimeout(() => node.remove(), duration);
  },
  success(m) { this.show(m, "succes"); },
  error(m) { this.show(m, "erreur", 6500); },
  warn(m) { this.show(m, "avert", 5000); },
  info(m) { this.show(m, "info"); },
};

/** Affiche l'erreur d'une promesse API (message métier) et la journalise en console. */
function reportError(ex) {
  if (ex instanceof ApiError) {
    if (ex.status === 401) return;
    toast.error(ex.fullMessage);
  } else {
    console.error(ex);
    toast.error("Erreur inattendue : " + (ex && ex.message ? ex.message : ex));
  }
}

// ---------------------------------------------------------------------------
// Modales
// ---------------------------------------------------------------------------

const modal = {
  open({ title, body, actions = [], size = "", onClose }) {
    const zone = document.getElementById("modales");
    const voile = el("div", { class: "voile" });
    const close = () => { voile.remove(); if (onClose) onClose(); };
    const boite = el("div", { class: "modale " + size },
      el("div", { class: "modale-entete" }, el("h2", null, title),
        el("button", { type: "button", class: "fermer", title: "Fermer", onClick: close }, "×")),
      el("div", { class: "modale-corps" }, body),
      actions.length ? el("div", { class: "modale-pied" }, actions) : null);
    voile.appendChild(boite);
    voile.addEventListener("mousedown", (e) => { if (e.target === voile) close(); });
    const escape = (e) => { if (e.key === "Escape") { close(); document.removeEventListener("keydown", escape); } };
    document.addEventListener("keydown", escape);
    zone.appendChild(voile);
    const first = boite.querySelector("input:not([readonly]), select, textarea");
    if (first) setTimeout(() => first.focus(), 30);
    return { close, element: boite };
  },
  confirm({ title = "Confirmation", message, ok = "Confirmer", danger = false }) {
    return new Promise((resolve) => {
      let handle;
      const done = (v) => { resolve(v); handle.close(); };
      handle = modal.open({
        title, size: "etroite",
        body: el("p", null, message),
        actions: [button("Annuler", () => done(false)), button(ok, () => done(true), danger ? "danger" : "primaire")],
        onClose: () => resolve(false),
      });
    });
  },
  /**
   * Formulaire modal. `fields` : voir buildForm. `onSubmit(values)` retourne une
   * promesse ; en cas d'ApiError, les erreurs s'affichent dans la modale.
   */
  form({ title, fields, values = {}, onSubmit, submitLabel = "Enregistrer", size = "", extra = null }) {
    return new Promise((resolve) => {
      const form = buildForm(fields, values);
      const errorBox = el("div", { class: "erreurs hidden" });
      let handle;
      const submit = async () => {
        const data = form.read();
        const missing = form.validateRequired();
        if (missing.length) {
          showErrors(errorBox, "Champs obligatoires manquants : " + missing.join(", "));
          return;
        }
        try {
          bouton.disabled = true;
          const result = await onSubmit(data);
          resolve(result === undefined ? true : result);
          handle.close();
        } catch (ex) {
          if (ex instanceof ApiError) showErrors(errorBox, ex.message, ex.errors);
          else { console.error(ex); showErrors(errorBox, "Erreur inattendue : " + ex.message); }
        } finally {
          bouton.disabled = false;
        }
      };
      const bouton = button(submitLabel, submit, "primaire");
      form.element.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && e.target.tagName !== "TEXTAREA") { e.preventDefault(); submit(); }
      });
      handle = modal.open({
        title, size,
        body: el("div", null, errorBox, extra, form.element),
        actions: [button("Annuler", () => { resolve(null); handle.close(); }), bouton],
        onClose: () => resolve(null),
      });
    });
  },
};

function showErrors(box, message, errors = []) {
  clear(box);
  box.classList.remove("hidden");
  box.appendChild(document.createTextNode(message));
  if (errors && errors.length) box.appendChild(el("ul", null, errors.map((e) => el("li", null, e))));
}

// ---------------------------------------------------------------------------
// Formulaires
// ---------------------------------------------------------------------------

/**
 * fields : [{name, label, type: text|number|date|select|check|textarea|money|password|readonly,
 *            options: [{value, label}] | fn, required, span (3|4|6|8|12), help, placeholder,
 *            step, min, max, section: "Titre"}]
 */
function buildForm(fields, values = {}) {
  const inputs = {};
  const element = el("div", { class: "formulaire" });
  fields.forEach((f) => {
    if (f.section) { element.appendChild(el("div", { class: "separateur" }, f.section)); return; }
    const span = f.span ? "l" + f.span : "";
    let input;
    const current = values[f.name];
    switch (f.type) {
      case "select": {
        input = el("select", { name: f.name, disabled: f.disabled });
        const options = typeof f.options === "function" ? f.options() : (f.options || []);
        if (!f.required || f.placeholder !== undefined) input.appendChild(el("option", { value: "" }, f.placeholder || "—"));
        options.forEach((o) => {
          const opt = typeof o === "object" ? o : { value: o, label: o };
          input.appendChild(el("option", { value: opt.value }, opt.label));
        });
        input.value = current === null || current === undefined ? "" : String(current);
        if (input.value === "" && f.required && options.length && f.placeholder === undefined) input.value = String(typeof options[0] === "object" ? options[0].value : options[0]);
        break;
      }
      case "check":
        input = el("input", { type: "checkbox", name: f.name, checked: !!current, disabled: f.disabled });
        break;
      case "textarea":
        input = el("textarea", { name: f.name, placeholder: f.placeholder, rows: f.rows || 3 }, current === null || current === undefined ? "" : String(current));
        break;
      case "date":
        input = el("input", { type: "date", name: f.name, value: fmt.isoDate(current), disabled: f.disabled });
        break;
      case "number":
      case "money":
        input = el("input", { type: "number", name: f.name, step: f.step || (f.type === "money" ? "1" : "any"), min: f.min, max: f.max,
          value: current === null || current === undefined ? "" : current, placeholder: f.placeholder, disabled: f.disabled });
        break;
      case "password":
        input = el("input", { type: "password", name: f.name, value: "", placeholder: f.placeholder, autocomplete: "new-password" });
        break;
      case "readonly":
        input = el("input", { type: "text", name: f.name, value: current === null || current === undefined ? "" : current, readonly: true, tabindex: "-1" });
        break;
      default:
        input = el("input", { type: "text", name: f.name, value: current === null || current === undefined ? "" : current,
          placeholder: f.placeholder, maxlength: f.maxlength, disabled: f.disabled, style: f.upper ? { textTransform: "uppercase" } : null });
    }
    inputs[f.name] = { input, field: f };
    const label = el("label", { for: f.name }, f.label, f.required ? el("span", { class: "req" }, " *") : null);
    const champ = el("div", { class: "champ " + span + (f.type === "check" ? " case" : "") });
    if (f.type === "check") { champ.appendChild(input); champ.appendChild(label); }
    else { champ.appendChild(label); champ.appendChild(input); if (f.help) champ.appendChild(el("div", { class: "aide" }, f.help)); }
    element.appendChild(champ);
  });
  return {
    element, inputs,
    read() {
      const out = {};
      Object.entries(inputs).forEach(([name, { input, field }]) => {
        if (field.type === "check") out[name] = input.checked;
        else if (field.type === "readonly") return;
        else if (field.type === "number" || field.type === "money") out[name] = input.value === "" ? null : Number(input.value);
        else if (field.type === "password") { if (input.value !== "") out[name] = input.value; }
        else out[name] = field.upper ? input.value.trim().toUpperCase() : (typeof input.value === "string" ? input.value.trim() : input.value);
        if (out[name] === "") out[name] = null;
      });
      return out;
    },
    validateRequired() {
      const missing = [];
      Object.values(inputs).forEach(({ input, field }) => {
        input.classList.remove("invalide");
        if (!field.required || field.type === "check") return;
        const v = input.value;
        if (v === "" || v === null) { input.classList.add("invalide"); missing.push(field.label); }
      });
      return missing;
    },
    set(name, value) {
      const entry = inputs[name];
      if (!entry) return;
      if (entry.field.type === "check") entry.input.checked = !!value;
      else if (entry.field.type === "date") entry.input.value = fmt.isoDate(value);
      else entry.input.value = value === null || value === undefined ? "" : value;
    },
    get(name) { const e = inputs[name]; return e ? (e.field.type === "check" ? e.input.checked : e.input.value) : undefined; },
  };
}

/** Champ de filtre autonome (retourne {element, input}). */
function filterField(label, input, cls = "") {
  return el("div", { class: "champ " + cls }, el("label", null, label), input);
}

function selectInput(options, value, attrs = {}) {
  const select = el("select", attrs);
  if (attrs.placeholder !== undefined) select.appendChild(el("option", { value: "" }, attrs.placeholder));
  options.forEach((o) => {
    const opt = typeof o === "object" ? o : { value: o, label: o };
    select.appendChild(el("option", { value: opt.value }, opt.label));
  });
  if (value !== undefined && value !== null) select.value = String(value);
  return select;
}

// ---------------------------------------------------------------------------
// Tableaux
// ---------------------------------------------------------------------------

/**
 * columns : [{key, label, render(row), cls, num, width}] ; options : {empty, onRow, rowClass, foot}
 */
function dataTable(columns, rows, options = {}) {
  const table = el("table", { class: "tableau" });
  table.appendChild(el("thead", null, el("tr", null, columns.map((c) =>
    el("th", { class: (c.num ? "num " : "") + (c.cls || ""), style: c.width ? { width: c.width } : null }, c.label)))));
  const body = el("tbody");
  if (!rows || !rows.length) {
    body.appendChild(el("tr", null, el("td", { colspan: columns.length, class: "vide" }, options.empty || "Aucune donnée.")));
  } else {
    rows.forEach((row, index) => {
      const tr = el("tr", { class: (options.onRow ? "selectionnable " : "") + (options.rowClass ? options.rowClass(row) || "" : "") });
      columns.forEach((c) => {
        let value = c.render ? c.render(row, index) : row[c.key];
        if (value === null || value === undefined) value = "";
        tr.appendChild(el("td", { class: (c.num ? "num " : "") + (c.cls || "") }, value));
      });
      if (options.onRow) tr.addEventListener("click", (e) => { if (e.target.closest("button, a, input, select")) return; options.onRow(row, tr); });
      body.appendChild(tr);
    });
  }
  table.appendChild(body);
  if (options.foot) table.appendChild(el("tfoot", null, el("tr", null, options.foot.map((v, i) => el("td", { class: columns[i] && columns[i].num ? "num" : "" }, v)))));
  return el("div", { class: "tableau-conteneur" }, table);
}

function actionButtons(actions) {
  return actions.filter(Boolean).map((a) => button(a.label, a.onClick, "petit " + (a.cls || ""), { title: a.title }));
}

// ---------------------------------------------------------------------------
// Divers
// ---------------------------------------------------------------------------

function pageHeader(title, description, actions = []) {
  return el("div", { class: "page-titre" },
    el("div", null, el("h1", null, title), description ? el("div", { class: "desc" }, description) : null),
    actions.length ? el("div", { class: "actions" }, actions) : null);
}

function card(title, body, actions = [], cls = "") {
  return el("div", { class: "carte " + cls },
    title !== null ? el("div", { class: "carte-entete" }, el("h2", null, title), actions.length ? el("div", { class: "actions" }, actions) : null) : null,
    el("div", { class: "carte-corps" }, body));
}

function tabs(items, active, onChange) {
  const bar = el("div", { class: "onglets" });
  items.forEach((item) => {
    bar.appendChild(el("button", { type: "button", class: item.key === active ? "actif" : "", onClick: () => onChange(item.key) }, item.label));
  });
  return bar;
}

function loading(text = "Chargement…") { return el("div", { class: "chargement" }, text); }

function debounce(fn, delay = 300) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); };
}

/** Sélecteur de classe (options depuis le référentiel). */
function classeOptions(classes) {
  return (classes || []).map((c) => ({ value: c.id_classe, label: c.libelle + (c.annee ? " — " + c.annee : "") }));
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = el("a", { href: url, download: filename });
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { a.remove(); URL.revokeObjectURL(url); }, 500);
}

/** Impression d'un document HTML dans la zone dédiée. */
function printDocument(node) {
  const zone = document.getElementById("impression");
  clear(zone);
  zone.appendChild(node);
  setTimeout(() => window.print(), 80);
}
