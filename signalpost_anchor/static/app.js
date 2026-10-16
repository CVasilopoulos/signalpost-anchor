(function () {
  "use strict";

  const INDEX = window.SP_INDEX || {};
  const VERSION = typeof window.SP_VERSION === "string" ? window.SP_VERSION : "";
  const REPORT = INDEX.report || {};
  const ROWS = Array.isArray(INDEX.companies) ? INDEX.companies : [];
  const SECTION_ORDER = Array.isArray(INDEX.section_order) && INDEX.section_order.length ? INDEX.section_order : [
    "legal_identity", "annual_accounts", "leadership", "workplaces", "website",
    "company_profiles", "hiring", "public_activity", "contact", "external_identifiers"
  ];
  const CODE_STATE = INDEX.state_codes || {};
  const TITLE = "Signalpost Anchor — Norwegian company research";
  const MAX_COMPARE = 4;
  const PAGE = 100;
  const STORE_KEY = "signalpost-anchor.compare";

  const STATE_LABEL = {
    available: "Available", not_available: "Not available", blocked: "Blocked",
    not_applicable: "Not applicable", ambiguous: "Ambiguous", failed: "Failed"
  };
  const STATE_TONE = {
    available: "ok", not_available: "neutral", blocked: "bad",
    not_applicable: "neutral", ambiguous: "warn", failed: "bad"
  };
  const STATUS_LABEL = {
    active: "Active", deleted: "Deleted", bankrupt: "Bankrupt", forced_dissolution: "Forced dissolution",
    liquidating: "In liquidation", subunit: "Subunit", not_found: "Not found", failed: "Lookup failed"
  };
  const STATUS_TONE = {
    active: "ok", deleted: "bad", bankrupt: "bad", forced_dissolution: "bad",
    liquidating: "warn", subunit: "info", not_found: "bad", failed: "bad"
  };
  const SECTION_TITLE = {
    legal_identity: "Legal identity", annual_accounts: "Annual accounts", leadership: "Leadership and roles",
    workplaces: "Workplaces and addresses", website: "Official website", company_profiles: "Company-owned profiles",
    hiring: "Hiring", public_activity: "Public activity", contact: "Contact", external_identifiers: "External identifiers"
  };
  const TOPIC_TITLE = {
    what_it_does: "What it does", size_and_financials: "Size and financials", leadership: "Leadership",
    footprint: "Public footprint", what_changed: "Recent changes", unknowns: "Not established", hiring: "Hiring"
  };
  const SIGNAL_TEXT = {
    negative_equity: "Negative equity", loss_in_latest_year: "Loss in the latest year",
    revenue_growth_over_25pct: "Revenue up more than 25%", revenue_decline_over_25pct: "Revenue down more than 25%",
    unaudited_accounts: "Accounts not audited", currently_hiring: "Currently hiring"
  };
  const SEVERITY_TONE = { high: "bad", medium: "warn", low: "neutral", info: "info" };
  const COVERAGE_LABEL = {
    official_identity: "Official identity", annual_accounts: "Annual accounts", leadership: "Leadership",
    registered_workplaces: "Registered workplaces", verified_website: "Verified website",
    company_profiles: "Company-owned profiles", hiring_any: "Any hiring signal", job_postings: "Job postings",
    website_news: "Website news", registry_activity: "Registry activity", contact: "Contact details",
    lei: "LEI", wikidata: "Wikidata", public_brand: "Public brand"
  };
  const SOURCE_CLASS = {
    official_registry: "Official registry", official_api: "Official API", company_owned: "Company-owned",
    open_data: "Open data", third_party: "Third party"
  };
  const PLATFORM = {
    linkedin: "LinkedIn", facebook: "Facebook", instagram: "Instagram", youtube: "YouTube", twitter: "X (Twitter)",
    x: "X", tiktok: "TikTok", github: "GitHub", vimeo: "Vimeo", pinterest: "Pinterest", wikidata: "Wikidata", threads: "Threads"
  };
  const ROLE_GROUPS = [
    ["leadership.ceo", "Chief executive (daglig leder)"],
    ["leadership.board_chair", "Board chair"],
    ["leadership.board_member", "Board members"],
    ["leadership.board_deputy_member", "Deputy board members"],
    ["leadership.owner", "Owners"],
    ["leadership.auditor", "Auditor"],
    ["leadership.accountant", "Accountant"],
    ["leadership.business_manager", "Business manager"]
  ];
  const FIN_GROUPS = [
    ["Income statement", [
      ["revenue", "Total operating revenue"], ["sales_revenue", "Sales revenue"],
      ["operating_expenses", "Operating expenses"], ["wage_costs", "Wage costs"],
      ["operating_result", "Operating result"], ["financial_income", "Financial income"],
      ["financial_expenses", "Financial expenses"], ["net_financial_items", "Net financial items"],
      ["profit_before_tax", "Profit before tax"], ["tax_expense", "Tax expense"],
      ["annual_result", "Annual result"], ["total_comprehensive_result", "Total comprehensive result"]
    ]],
    ["Balance sheet", [
      ["total_assets", "Total assets"], ["fixed_assets", "Fixed assets"], ["goodwill", "Goodwill"],
      ["current_assets", "Current assets"], ["inventory", "Inventory"], ["receivables", "Receivables"],
      ["cash_and_bank", "Cash and bank"], ["equity", "Equity"], ["paid_in_equity", "Paid-in equity"],
      ["retained_earnings", "Retained earnings"], ["total_liabilities", "Total liabilities"],
      ["long_term_liabilities", "Long-term liabilities"], ["current_liabilities", "Current liabilities"],
      ["equity_ratio", "Equity ratio (derived)"]
    ]],
    ["Filing", [["audited", "Audited"], ["accounting_rules", "Accounting rules"], ["statement_format", "Statement format"]]]
  ];
  const KNOWN_CLAIM_KEYS = new Set([
    "id", "key", "section", "field", "label", "value", "availability", "relationship", "confidence", "method",
    "evidence_ids", "period", "as_of", "unit", "fiscal_year", "account_scope", "first_observed_at",
    "last_observed_at", "stale", "stale_reason", "carried_forward_from_run", "_historic", "_superseded_at"
  ]);
  const EXTRA_LABEL = {
    url: "Link", date_posted: "Date posted", published: "Published", work_locations: "Work locations",
    employer_name: "Employer", employer_organisation_number: "Employer org. no.", municipality: "Municipality",
    municipality_number: "Municipality number", subunit_organisation_number: "Subunit org. no.",
    holder_organisation_number: "Holder org. no.", holder_type: "Holder type", role_code: "Role code",
    role_group: "Role group", industry: "Industry", employees: "Employees", started: "Started",
    website: "Website", source_system: "Source system", expires: "Expires", application_due: "Application due",
    valid_through: "Valid through", event_type: "Registry event", changed_path: "Changed field"
  };

  const nf = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 2 });
  const reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const byFile = new Map();
  const byId = new Map();
  ROWS.forEach(function (row) {
    row._name = displayName(row);
    row._sortName = norm(row._name);
    row._hay = norm([row.id, row.name, row.brand, row.municipality, row.form, row.form_label, (row.industries || []).join(" "), row.website ? hostOf(row.website) : "", row.ceo, row.chair, inputText(row.input)].filter(Boolean).join(" | "));
    byFile.set(String(row.file), row);
    if (row.id && !byId.has(String(row.id))) byId.set(String(row.id), row);
  });

  const cache = new Map();
  const pending = new Map();
  const state = {
    compare: [],
    list: { q: "", state: "", status: "", web: false, hiring: false, accounts: false, changed: false, sort: "" },
    shown: PAGE,
    listScroll: 0,
    lastView: "",
    token: 0,
    scopes: {}
  };
  const view = { data: null, rowEls: new Map(), details: {}, renderers: {} };

  const main = document.getElementById("main");
  const qInput = document.getElementById("q");
  const tray = document.getElementById("tray");
  const dlg = document.getElementById("verify");
  const live = document.getElementById("live");
  let dlgReturn = null;
  let listRefs = null;

  function isNum(v) { return typeof v === "number" && isFinite(v); }
  function fmtNum(v) { return isNum(v) ? nf.format(v) : "—"; }
  function fmtNok(v) { return isNum(v) ? "NOK " + nf.format(Math.round(v)) : "—"; }
  function fmtNokShort(v) {
    if (!isNum(v)) return "—";
    const a = Math.abs(v);
    const sign = v < 0 ? "−" : "";
    let s;
    if (a >= 1e9) s = (a / 1e9).toFixed(2) + " bn";
    else if (a >= 1e6) s = (a / 1e6).toFixed(1) + " m";
    else if (a >= 1e3) s = (a / 1e3).toFixed(0) + " k";
    else s = String(Math.round(a));
    return sign + "NOK " + s;
  }
  function fmtPct(v) { return isNum(v) ? (v * 100).toFixed(1) + "%" : "—"; }
  function fmtDate(v) { return typeof v === "string" && /^\d{4}-\d{2}-\d{2}/.test(v) ? v.slice(0, 10) : (v ? String(v) : "—"); }
  function fmtTime(v) {
    if (typeof v !== "string" || !v) return "—";
    const m = v.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})(?::\d{2}(?:\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?$/);
    if (!m) return v;
    return m[1] + " " + m[2] + (m[3] === "Z" ? " UTC" : m[3] ? " " + m[3] : "");
  }
  function fmtOrg(v) {
    const s = String(v == null ? "" : v);
    return /^\d{9}$/.test(s) ? s.slice(0, 3) + " " + s.slice(3, 6) + " " + s.slice(6) : s;
  }
  function humanise(v) {
    const s = String(v == null ? "" : v).replace(/[_]+/g, " ").trim();
    return s ? s.charAt(0).toUpperCase() + s.slice(1) : "";
  }
  function methodText(v) {
    return humanise(v)
      .replace(/\bapi\b/gi, "API").replace(/\bhtml\b/gi, "HTML").replace(/\burl\b/gi, "URL")
      .replace(/\brss\b/gi, "RSS").replace(/\bjson ld\b/gi, "JSON-LD").replace(/\bjson\b/gi, "JSON")
      .replace(/\bnav\b/gi, "NAV").replace(/\blei\b/gi, "LEI").replace(/\bsparql\b/gi, "SPARQL");
  }
  function norm(v) {
    let s = String(v == null ? "" : v).toLowerCase().replace(/æ/g, "ae").replace(/ø/g, "o").replace(/å/g, "a");
    if (s.normalize) s = s.normalize("NFKD").replace(/[̀-ͯ]/g, "");
    return s;
  }
  function safeUrl(value) {
    if (typeof value !== "string") return null;
    const s = value.trim();
    if (!/^https?:\/\//i.test(s)) return null;
    try {
      const u = new URL(s);
      return u.protocol === "http:" || u.protocol === "https:" ? u.href : null;
    } catch (e) {
      return null;
    }
  }
  function hostOf(url) {
    const safe = safeUrl(url);
    if (!safe) return String(url || "");
    try { return new URL(safe).hostname.replace(/^www\./, ""); } catch (e) { return safe; }
  }
  function prettyUrl(u) { return String(u).replace(/^https?:\/\//i, "").replace(/\/$/, ""); }
  function inputText(input) {
    if (input == null) return "";
    if (typeof input === "object") {
      if (input.organisation_number != null) return String(input.organisation_number);
      const first = Object.values(input).find(function (v) { return typeof v === "string" || typeof v === "number"; });
      return first == null ? "" : String(first);
    }
    return String(input);
  }
  function displayName(row) {
    if (row.name) return String(row.name);
    const inp = inputText(row.input) || row.id;
    return inp ? "Input " + inp : "Unnamed input";
  }
  function replaceHash(target) {
    try {
      history.replaceState(null, "", target);
      return true;
    } catch (e) {
      return false;
    }
  }
  function announce(text) {
    live.textContent = "";
    window.setTimeout(function () { live.textContent = text; }, 30);
  }

  function append(el, kids) {
    kids.forEach(function (kid) {
      if (Array.isArray(kid)) { append(el, kid); return; }
      if (kid === null || kid === undefined || kid === false) return;
      el.appendChild(kid instanceof Node ? kid : document.createTextNode(String(kid)));
    });
    return el;
  }
  function h(tag, attrs) {
    const el = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        const v = attrs[k];
        if (v === null || v === undefined || v === false) return;
        if (k === "class") el.className = v;
        else if (k.slice(0, 2) === "on" && typeof v === "function") el.addEventListener(k.slice(2).toLowerCase(), v);
        else if (k === "href") {
          const s = String(v);
          if (s.charAt(0) === "#" || safeUrl(s)) el.setAttribute("href", s.charAt(0) === "#" ? s : safeUrl(s));
        } else el.setAttribute(k, v === true ? "" : String(v));
      });
    }
    return append(el, Array.prototype.slice.call(arguments, 2));
  }
  function add(el) {
    return append(el, Array.prototype.slice.call(arguments, 1));
  }
  function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }
  function extLink(url, text, cls) {
    const safe = safeUrl(url);
    const label = text != null ? text : (safe ? prettyUrl(safe) : String(url == null ? "—" : url));
    if (!safe) return h("span", { class: cls || null }, label);
    return h("a", { href: safe, target: "_blank", rel: "noopener noreferrer nofollow", class: cls || null },
      label, h("span", { "aria-hidden": "true" }, " ↗"), h("span", { class: "sr-only" }, " (opens in a new tab)"));
  }
  function badge(text, tone, plain) {
    return h("span", { class: "badge " + (tone || "neutral") + (plain ? " plain" : "") }, text);
  }
  function stateBadge(s, prefix) {
    return badge((prefix || "") + (STATE_LABEL[s] || humanise(s) || "Unknown"), STATE_TONE[s] || "neutral");
  }
  function statusBadge(s) {
    if (!s) return null;
    return badge(STATUS_LABEL[s] || humanise(s), STATUS_TONE[s] || "neutral");
  }
  function signalText(sig) {
    if (SIGNAL_TEXT[sig]) return SIGNAL_TEXT[sig];
    if (String(sig).indexOf("registry_status_") === 0) {
      const st = String(sig).slice(16);
      return "Registry status: " + (STATUS_LABEL[st] || humanise(st)).toLowerCase();
    }
    return humanise(sig);
  }
  function kvList(rows) {
    return h("dl", { class: "kv" }, rows.filter(Boolean).map(function (r) {
      return h("div", null, h("dt", null, r[0]), h("dd", null, r[1] == null || r[1] === "" ? h("span", { class: "dash" }, "—") : r[1]), r[2] || null);
    }));
  }
  function dash(sr) { return h("span", { class: "dash" }, "—", h("span", { class: "sr-only" }, sr || " not found")); }

  function claimDate(c) {
    return c.as_of || c.published || c.date_posted || (c.period && (c.period.to || c.period.from)) || "";
  }
  function claimText(c) {
    const v = c.value;
    if (v === null || v === undefined || v === "") return "—";
    if (typeof v === "boolean") return v ? "Yes" : "No";
    if (typeof v === "number") {
      if (c.unit === "NOK") return fmtNok(v);
      if (c.unit) return fmtNum(v) + " " + c.unit;
      return fmtNum(v);
    }
    if (typeof v === "object") return JSON.stringify(v);
    return String(v);
  }
  function valueNode(c) {
    const v = c.value;
    if (typeof v === "string" && safeUrl(v)) return extLink(v, prettyUrl(v));
    if (typeof v === "string") {
      const m = v.match(/https?:\/\/\S+/);
      if (m && safeUrl(m[0])) {
        const before = v.slice(0, m.index).replace(/[:\s]+$/, "");
        return h("span", null, before ? before + ": " : "", extLink(m[0], prettyUrl(m[0])));
      }
    }
    return h("span", null, claimText(c));
  }
  function periodText(c) {
    const p = c.period;
    if (p && (p.from || p.to)) return (p.from || "…") + " → " + (p.to || "…");
    if (c.as_of) return "as of " + fmtDate(c.as_of);
    return "";
  }

  function prepare(key, env) {
    const claims = Array.isArray(env.claims) ? env.claims.filter(function (c) { return c && typeof c === "object" && c.id; }) : [];
    const evidence = new Map();
    (env.evidence || []).forEach(function (e) { if (e && e.id) evidence.set(e.id, e); });
    const claimById = new Map();
    claims.forEach(function (c) { claimById.set(c.id, c); });
    (env.history || []).forEach(function (entry) {
      if (!entry || typeof entry !== "object") return;
      (entry.evidence || []).forEach(function (e) {
        if (e && e.id && !evidence.has(e.id)) evidence.set(e.id, Object.assign({}, e, { _historic: true }));
      });
      const c = entry.claim;
      if (c && c.id && !claimById.has(c.id)) claimById.set(c.id, Object.assign({}, c, { _historic: true, _superseded_at: entry.superseded_at }));
    });
    const bySection = {};
    const byField = {};
    claims.forEach(function (c) {
      (bySection[c.section] = bySection[c.section] || []).push(c);
      (byField[c.field] = byField[c.field] || []).push(c);
    });
    return { key: key, env: env, claims: claims, evidence: evidence, claimById: claimById, bySection: bySection, byField: byField, row: byFile.get(key) };
  }
  function field(data, name) { return (data.byField[name] || []).filter(function (c) { return !c.stale; }); }
  function fieldAll(data, name) { return data.byField[name] || []; }
  function first(data, name) { return field(data, name)[0] || fieldAll(data, name)[0] || null; }
  function prefixed(data, prefix) { return data.claims.filter(function (c) { return String(c.field || "").indexOf(prefix) === 0; }); }

  window.SP_LOAD = function (key, env) {
    const k = String(key);
    if (!env || typeof env !== "object") return;
    cache.set(k, prepare(k, env));
    const p = pending.get(k);
    if (p) { pending.delete(k); p.resolve(cache.get(k)); }
  };
  function loadCompany(row) {
    const key = String(row.file);
    if (cache.has(key)) return Promise.resolve(cache.get(key));
    if (pending.has(key)) return pending.get(key).promise;
    let resolve, reject;
    const promise = new Promise(function (res, rej) { resolve = res; reject = rej; });
    pending.set(key, { promise: promise, resolve: resolve, reject: reject });
    const s = document.createElement("script");
    s.src = "data/c/" + encodeURIComponent(key) + ".js" + (VERSION ? "?v=" + encodeURIComponent(VERSION) : "");
    s.async = true;
    s.onerror = function () {
      s.remove();
      if (pending.has(key)) { pending.delete(key); reject(new Error("The research file for " + row._name + " could not be loaded.")); }
    };
    s.onload = function () {
      s.remove();
      if (pending.has(key)) { pending.delete(key); reject(new Error("The research file for " + row._name + " is not valid.")); }
    };
    document.head.appendChild(s);
    return promise;
  }

  function loadCompare() {
    try {
      const raw = window.localStorage.getItem(STORE_KEY);
      const list = raw ? JSON.parse(raw) : [];
      return Array.isArray(list) ? list.map(String).filter(function (k) { return byFile.has(k); }).slice(0, MAX_COMPARE) : [];
    } catch (e) {
      return [];
    }
  }
  function saveCompare() {
    try { window.localStorage.setItem(STORE_KEY, JSON.stringify(state.compare)); } catch (e) { return; }
  }
  function compareHref(keys) { return "#/compare/" + (keys || state.compare).map(encodeURIComponent).join(","); }
  function inCompare(key) { return state.compare.indexOf(String(key)) !== -1; }
  function toggleCompare(row) {
    const key = String(row.file);
    if (inCompare(key)) {
      state.compare = state.compare.filter(function (k) { return k !== key; });
      announce(row._name + " removed from compare. " + state.compare.length + " selected.");
    } else {
      if (state.compare.length >= MAX_COMPARE) {
        announce("Compare holds up to " + MAX_COMPARE + " companies. Remove one first.");
        flashTray();
        return false;
      }
      state.compare = state.compare.concat([key]);
      announce(row._name + " added to compare. " + state.compare.length + " of " + MAX_COMPARE + " selected.");
    }
    saveCompare();
    syncCompareUi();
    return true;
  }
  function compareButton(row, small) {
    const btn = h("button", { type: "button", class: "btn" + (small ? " small" : "") });
    function paint() {
      const on = inCompare(row.file);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
      btn.textContent = on ? "✓ In compare" : "+ Compare";
      btn.setAttribute("aria-label", (on ? "Remove " : "Add ") + row._name + (on ? " from compare" : " to compare"));
      const full = !on && state.compare.length >= MAX_COMPARE;
      if (full) btn.setAttribute("aria-disabled", "true"); else btn.removeAttribute("aria-disabled");
      btn.title = full ? "Compare holds up to " + MAX_COMPARE + " companies" : "";
    }
    btn.addEventListener("click", function () { toggleCompare(row); });
    btn._paint = paint;
    btn.classList.add("cmp-toggle");
    paint();
    return btn;
  }
  function syncCompareUi() {
    document.querySelectorAll(".cmp-toggle").forEach(function (b) { if (b._paint) b._paint(); });
    document.getElementById("compare-count").textContent = String(state.compare.length);
    document.getElementById("nav-compare").setAttribute("href", compareHref());
    renderTray();
  }
  function flashTray() {
    tray.classList.add("flash");
    window.setTimeout(function () { tray.classList.remove("flash"); }, 900);
  }
  function renderTray() {
    clear(tray);
    if (!state.compare.length || state.lastView === "compare") { tray.hidden = true; return; }
    tray.hidden = false;
    const items = state.compare.map(function (k) {
      const row = byFile.get(k);
      if (!row) return null;
      return h("span", { class: "tray-item" }, h("span", { title: row._name }, row._name),
        h("button", { type: "button", "aria-label": "Remove " + row._name + " from compare", onclick: function () { toggleCompare(row); } }, "×"));
    });
    add(tray, h("div", { class: "tray-inner" },
      h("span", { class: "tray-label" }, "Compare " + state.compare.length + "/" + MAX_COMPARE),
      h("div", { class: "tray-items", role: "list", "aria-label": "Selected for compare" }, items.map(function (i) { return i ? (i.setAttribute("role", "listitem"), i) : null; })),
      h("a", { class: "btn primary", href: compareHref() }, "Compare now"),
      h("button", { type: "button", class: "btn", onclick: function () { state.compare = []; saveCompare(); syncCompareUi(); announce("Compare cleared."); } }, "Clear")));
  }

  function setNav(kind) {
    const list = document.getElementById("nav-list");
    const cmp = document.getElementById("nav-compare");
    if (kind === "list") list.setAttribute("aria-current", "page"); else list.removeAttribute("aria-current");
    if (kind === "compare") cmp.setAttribute("aria-current", "page"); else cmp.removeAttribute("aria-current");
  }
  function parseHash() {
    const raw = location.hash || "#/";
    if (raw.indexOf("#/") !== 0) return null;
    const qi = raw.indexOf("?");
    const path = qi === -1 ? raw.slice(1) : raw.slice(1, qi);
    const params = new URLSearchParams(qi === -1 ? "" : raw.slice(qi + 1));
    const parts = path.split("/").filter(Boolean).map(function (p) { try { return decodeURIComponent(p); } catch (e) { return p; } });
    if (parts[0] === "c" && parts[1]) return { view: "company", key: parts[1], params: params };
    if (parts[0] === "compare") return { view: "compare", keys: (parts[1] || "").split(",").map(function (s) { return s.trim(); }).filter(Boolean), params: params };
    return { view: "list", params: params };
  }
  function resolveRow(key) { return byFile.get(String(key)) || byId.get(String(key).replace(/\s+/g, "")) || null; }
  function route() {
    const r = parseHash();
    if (!r) return;
    if (dlg.open) closeDialog(true);
    if (state.lastView === "list" && r.view !== "list") state.listScroll = window.scrollY;
    const previous = state.lastView;
    state.lastView = r.view;
    state.token += 1;
    setNav(r.view);
    view.data = null;
    view.rowEls = new Map();
    view.details = {};
    view.renderers = {};
    listRefs = null;
    if (r.view === "company") renderCompany(r.key, r.params);
    else if (r.view === "compare") renderCompare(r.keys);
    else renderList(r.params, previous);
    renderTray();
  }

  function readListParams(params) {
    const L = state.list;
    L.q = params.get("q") || "";
    L.state = params.get("state") || "";
    L.status = params.get("status") || "";
    L.sort = params.get("sort") || "";
    const f = (params.get("f") || "").split(",");
    L.web = f.indexOf("web") !== -1;
    L.hiring = f.indexOf("hiring") !== -1;
    L.accounts = f.indexOf("accounts") !== -1;
    L.changed = f.indexOf("changed") !== -1;
  }
  function listHash() {
    const L = state.list;
    const p = new URLSearchParams();
    if (L.q) p.set("q", L.q);
    if (L.state) p.set("state", L.state);
    if (L.status) p.set("status", L.status);
    const f = ["web", "hiring", "accounts", "changed"].filter(function (k) { return L[k]; });
    if (f.length) p.set("f", f.join(","));
    if (L.sort) p.set("sort", L.sort);
    const s = p.toString();
    return "#/" + (s ? "?" + s : "");
  }
  function writeListHash() {
    const target = listHash();
    if (location.hash !== target) replaceHash(target);
  }
  function queryTerms(q) {
    const raw = String(q || "").trim();
    if (!raw) return [];
    if (/^[\d\s.]+$/.test(raw)) return [raw.replace(/[\s.]+/g, "")];
    return norm(raw).split(/\s+/).filter(Boolean);
  }
  function relevance(row, q, terms) {
    if (!terms.length) return 0;
    const nq = norm(q.trim());
    const digits = q.replace(/[\s.]+/g, "");
    if (/^\d+$/.test(digits) && row.id === digits) return 100;
    const name = row._sortName;
    const brand = norm(row.brand || "");
    if (name === nq || brand === nq) return 90;
    if (name.indexOf(nq) === 0 || brand.indexOf(nq) === 0) return 70;
    if (name.indexOf(nq) !== -1 || brand.indexOf(nq) !== -1) return 50;
    if (terms.every(function (t) { return name.indexOf(t) !== -1; })) return 40;
    return 10;
  }
  function filteredRows() {
    const L = state.list;
    const terms = queryTerms(L.q);
    const rows = ROWS.filter(function (r) {
      if (L.state && r.state !== L.state) return false;
      if (L.status && (r.status || "unknown") !== L.status) return false;
      if (L.web && !(r.website && r.website_state === "available")) return false;
      if (L.hiring && !r.hiring) return false;
      if (L.accounts && !r.accounts) return false;
      if (L.changed && !(r.changes > 0)) return false;
      for (let i = 0; i < terms.length; i += 1) if (r._hay.indexOf(terms[i]) === -1) return false;
      return true;
    });
    const sort = L.sort || (terms.length ? "relevance" : "name");
    const byName = function (a, b) { return a._sortName < b._sortName ? -1 : a._sortName > b._sortName ? 1 : 0; };
    const desc = function (get) {
      return function (a, b) {
        const x = get(a), y = get(b);
        const xn = isNum(x), yn = isNum(y);
        if (xn && yn && x !== y) return y - x;
        if (xn !== yn) return xn ? -1 : 1;
        return byName(a, b);
      };
    };
    if (sort === "relevance") {
      rows.forEach(function (r) { r._score = relevance(r, L.q, terms); });
      rows.sort(function (a, b) { return b._score - a._score || byName(a, b); });
    } else if (sort === "revenue") rows.sort(desc(function (r) { return r.fin ? r.fin.revenue : null; }));
    else if (sort === "employees") rows.sort(desc(function (r) { return r.employees; }));
    else if (sort === "data") rows.sort(desc(function (r) { return r.claims; }));
    else rows.sort(byName);
    return rows;
  }

  function runSummary() {
    const run = REPORT.run || {};
    const v = REPORT.validation || {};
    const states = REPORT.envelope_states || {};
    const cov = REPORT.coverage_share || {};
    const covN = REPORT.coverage_companies || {};
    const ops = REPORT.operations || {};
    const card = h("section", { class: "card run", "aria-labelledby": "run-h" });
    const passed = v.passed === true ? badge("Validation passed", "ok") : v.passed === false ? badge("Validation failed", "bad") : badge("Validation not reported", "neutral");
    add(card, h("div", { class: "run-top" },
      h("h2", { id: "run-h" }, "Research run"),
      h("span", { class: "muted small mono" }, run.run_id || "run id not reported"),
      h("span", { class: "muted small" }, "Completed " + fmtTime(run.completed_at)),
      h("span", { class: "muted small" }, fmtNum(ROWS.length) + " companies"),
      passed));
    const stateText = Object.keys(states).map(function (k) { return (STATE_LABEL[k] || humanise(k)) + " " + states[k]; }).join(" · ");
    const stats = [
      ["Input records", REPORT.input && isNum(REPORT.input.records) ? fmtNum(REPORT.input.records) + (REPORT.input.invalid ? " (" + REPORT.input.invalid + " invalid)" : "") : "—"],
      ["Claims with evidence", isNum(REPORT.claims_total) ? fmtNum(REPORT.claims_total) : fmtNum(ROWS.reduce(function (s, r) { return s + (r.claims || 0); }, 0))],
      ["Envelope states", stateText || "—", true],
      ["Requests", isNum(ops.requests) ? fmtNum(ops.requests) : "—"],
      ["Runtime", isNum(ops.runtime_s) ? fmtNum(ops.runtime_s) + " s" : "—"],
      ["Third-party cost", isNum(ops.third_party_cost_usd) ? "USD " + ops.third_party_cost_usd.toFixed(2) : "—"]
    ];
    const det = h("details", { class: "run-more" });
    if (window.matchMedia && window.matchMedia("(min-width: 720px)").matches) det.open = true;
    add(det, h("summary", null, "Run details and coverage across companies"));
    add(det, h("dl", { class: "stats" }, stats.map(function (s) {
      return h("div", { class: "stat" }, h("dt", null, s[0]), h("dd", { class: s[2] ? "smallval" : null }, s[1]));
    })));
    const keys = Object.keys(cov);
    if (keys.length) {
      add(det, h("h3", { class: "group-title" }, "Coverage: share of companies where each kind of data was found"));
      add(det, h("ul", { class: "coverage" }, keys.map(function (k) {
        const share = isNum(cov[k]) ? Math.max(0, Math.min(1, cov[k])) : 0;
        const bar = h("span");
        bar.style.width = (share * 100).toFixed(1) + "%";
        return h("li", null,
          h("span", null, COVERAGE_LABEL[k] || humanise(k)),
          h("span", { class: "pct" }, Math.round(share * 100) + "%" + (isNum(covN[k]) ? " · " + covN[k] : "")),
          h("span", { class: "bar", "aria-hidden": "true" }, bar));
      })));
    } else add(det, h("p", { class: "muted small" }, "No run report was supplied, so coverage shares are not available."));
    const checks = Object.keys(v).filter(function (k) { return k !== "passed" && typeof v[k] === "boolean"; });
    if (checks.length) {
      add(det, h("p", { class: "small muted" }, "Validation checks: ", checks.map(function (k, i) {
        return [i ? " · " : "", humanise(k) + " ", v[k] ? h("strong", null, "pass") : h("strong", null, "FAIL")];
      })));
    }
    add(card, det);
    return card;
  }

  function optionCounts(get) {
    const counts = {};
    ROWS.forEach(function (r) { const k = get(r) || "unknown"; counts[k] = (counts[k] || 0) + 1; });
    return counts;
  }
  function selectField(id, label, value, options, onchange) {
    const sel = h("select", { id: id, onchange: function () { onchange(sel.value); } }, options.map(function (o) {
      return h("option", { value: o[0], selected: o[0] === value ? true : null }, o[1]);
    }));
    return h("label", { class: "field", for: id }, label, sel);
  }
  function checkField(id, label, checked, onchange) {
    const box = h("input", { type: "checkbox", id: id, checked: checked ? true : null, onchange: function () { onchange(box.checked); } });
    return h("label", { class: "check", for: id }, box, label);
  }
  function renderList(params, previous) {
    readListParams(params);
    document.title = TITLE;
    if (document.activeElement !== qInput) qInput.value = state.list.q;
    clear(main);
    const L = state.list;
    const stateCounts = optionCounts(function (r) { return r.state; });
    const statusCounts = optionCounts(function (r) { return r.status; });
    const anyChanged = ROWS.some(function (r) { return r.changes > 0; });
    const update = function () { state.shown = PAGE; writeListHash(); updateResults(); };
    const controls = h("div", { class: "controls" },
      selectField("f-state", "Research state", L.state, [["", "All states"]].concat(Object.keys(stateCounts).map(function (k) { return [k, (STATE_LABEL[k] || humanise(k)) + " (" + stateCounts[k] + ")"]; })), function (v) { L.state = v; update(); }),
      selectField("f-status", "Registry status", L.status, [["", "Any status"]].concat(Object.keys(statusCounts).map(function (k) { return [k, (STATUS_LABEL[k] || humanise(k)) + " (" + statusCounts[k] + ")"]; })), function (v) { L.status = v; update(); }),
      h("fieldset", { class: "checks" }, h("legend", null, "Only companies with"),
        checkField("f-web", "Verified website", L.web, function (v) { L.web = v; update(); }),
        checkField("f-hiring", "Hiring signals", L.hiring, function (v) { L.hiring = v; update(); }),
        checkField("f-accounts", "Annual accounts", L.accounts, function (v) { L.accounts = v; update(); }),
        anyChanged ? checkField("f-changed", "Changes since last run", L.changed, function (v) { L.changed = v; update(); }) : null),
      selectField("f-sort", "Sort by", L.sort, [["", "Best match / name"], ["name", "Name A–Z"], ["revenue", "Revenue (highest first)"], ["employees", "Employees (most first)"], ["data", "Data found (most claims)"]], function (v) { L.sort = v; update(); }));
    const meta = h("div", { class: "result-meta" });
    const list = h("ol", { class: "results", "aria-label": "Companies" });
    const more = h("div", { class: "more-row" });
    const panel = filterPanel(controls);
    listRefs = { meta: meta, list: list, more: more, panel: panel };
    add(main,
      h("div", { class: "page-head" }, h("h1", { tabindex: "-1" }, "Companies"), h("p", null, "Search, filter and open any company. Every value on a profile links to its source evidence.")),
      runSummary(), panel, meta, list, more);
    updateResults();
    if (previous && previous !== "list") window.scrollTo(0, state.listScroll || 0);
  }
  function activeFilterCount() {
    const L = state.list;
    return [L.state, L.status, L.web, L.hiring, L.accounts, L.changed, L.sort].filter(Boolean).length;
  }
  function filterPanel(controls) {
    const n = activeFilterCount();
    const count = h("span", { class: "count", "aria-label": n + " active" }, String(n));
    count.hidden = !n;
    const det = h("details", { class: "card filters" }, h("summary", null, "Filter and sort", count), controls);
    det._count = count;
    if (n || (window.matchMedia && window.matchMedia("(min-width: 720px)").matches)) det.open = true;
    return det;
  }
  function updateResults() {
    if (!listRefs) return;
    const rows = filteredRows();
    const L = state.list;
    const n = activeFilterCount();
    listRefs.panel._count.textContent = String(n);
    listRefs.panel._count.setAttribute("aria-label", n + " active");
    listRefs.panel._count.hidden = !n;
    clear(listRefs.meta);
    const active = L.q || L.state || L.status || L.web || L.hiring || L.accounts || L.changed;
    add(listRefs.meta, h("span", null, h("strong", null, fmtNum(rows.length)), " of " + fmtNum(ROWS.length) + " companies" + (L.q ? " match “" + L.q + "”" : "")),
      active ? h("button", { type: "button", class: "btn small", onclick: function () {
        state.list = { q: "", state: "", status: "", web: false, hiring: false, accounts: false, changed: false, sort: "" };
        qInput.value = "";
        replaceHash("#/");
        renderList(new URLSearchParams(""), "list");
      } }, "Clear filters") : null);
    clear(listRefs.list);
    clear(listRefs.more);
    if (!rows.length) {
      add(listRefs.list, h("li", { class: "card empty" }, "No companies match. Try fewer words, an organisation number, or clear the filters."));
    }
    const frag = document.createDocumentFragment();
    rows.slice(0, state.shown).forEach(function (r) { frag.appendChild(resultItem(r)); });
    listRefs.list.appendChild(frag);
    if (rows.length > state.shown) {
      add(listRefs.more, h("button", { type: "button", class: "btn", onclick: function () {
        state.shown += PAGE;
        updateResults();
      } }, "Show " + Math.min(PAGE, rows.length - state.shown) + " more (" + fmtNum(rows.length - state.shown) + " not shown)"));
    }
    announce(rows.length + " companies shown.");
  }
  function sectionsStrip(codes) {
    const s = String(codes || "");
    const labels = SECTION_ORDER.map(function (name, i) { return (SECTION_TITLE[name] || name) + ": " + (STATE_LABEL[CODE_STATE[s.charAt(i)]] || "unknown"); });
    const found = s.split("").filter(function (c) { return c === "A"; }).length;
    return h("span", { class: "chip", title: labels.join("\n") },
      h("span", { class: "sections-strip", "aria-hidden": "true" }, s.split("").map(function (c) { return h("span", { class: c }); })),
      " " + found + "/" + SECTION_ORDER.length + " sections found");
  }
  function resultItem(r) {
    const href = "#/c/" + encodeURIComponent(r.file);
    const sub = [
      r.brand && norm(r.brand) !== r._sortName ? "Brand: " + r.brand : null,
      r.id ? "Org. no. " + fmtOrg(r.id) : null,
      r.form ? r.form + (r.form_label ? " – " + r.form_label : "") : null,
      r.municipality || null,
      (r.industries || [])[0] || null
    ].filter(Boolean).join(" · ");
    const fin = r.fin || {};
    const finFacts = r.fin ? [
      ["Revenue" + (fin.year ? " " + fin.year : ""), isNum(fin.revenue) ? fmtNokShort(fin.revenue) : null],
      ["Operating result", isNum(fin.operating_result) ? fmtNokShort(fin.operating_result) : null],
      ["Annual result", isNum(fin.annual_result) ? fmtNokShort(fin.annual_result) : null],
      ["Equity ratio", isNum(fin.equity_ratio) ? fmtPct(fin.equity_ratio) : null]
    ] : [["Annual accounts", h("span", { class: "muted" }, "No company accounts found")]];
    const facts = [
      ["Employees", isNum(r.employees) ? fmtNum(r.employees) : null]
    ].concat(finFacts, [

      ["Website", r.website && r.website_state === "available" ? extLink(r.website, hostOf(r.website)) : (r.website_state ? h("span", { class: "muted" }, STATE_LABEL[r.website_state] || humanise(r.website_state)) : null)]
    ]);
    const chips = [
      h("span", { class: "chip" }, fmtNum(r.claims || 0) + " claims"),
      r.workplaces ? h("span", { class: "chip" }, r.workplaces + " workplaces") : null,
      r.profiles ? h("span", { class: "chip" }, r.profiles + " profiles") : null,
      r.jobs ? h("span", { class: "chip on" }, r.jobs + " job ads") : (r.hiring ? h("span", { class: "chip on" }, "Hiring page") : null),
      r.latest_activity ? h("span", { class: "chip" }, "Latest activity " + r.latest_activity) : null,
      r.changes ? h("span", { class: "chip on" }, r.changes + " changes") : null,
      r.stale ? h("span", { class: "chip" }, r.stale + " stale") : null,
      sectionsStrip(r.sections)
    ];
    return h("li", { class: "card co" },
      h("div", { class: "co-main" },
        h("div", { class: "co-title" }, h("a", { href: href }, r._name), statusBadge(r.status), r.state !== "available" ? stateBadge(r.state, "Research: ") : null,
          (r.signals || []).filter(function (s) { return s !== "currently_hiring" && String(s).indexOf("registry_status_") !== 0; }).map(function (s) { return badge(signalText(s), s.indexOf("registry_status_") === 0 || s === "negative_equity" ? "bad" : "warn", true); })),
        sub ? h("div", { class: "co-sub" }, sub) : null,
        r.note ? h("div", { class: "co-sub" }, r.note) : null,
        r.state === "available" || r.name ? h("dl", { class: "co-facts" }, facts.map(function (f) {
          return h("div", null, h("dt", null, f[0]), h("dd", null, f[1] == null ? dash() : f[1]));
        })) : null,
        h("div", { class: "chips" }, chips)),
      h("div", { class: "co-side" }, compareButton(r, true), h("a", { class: "btn small", href: href, "aria-label": "Open profile of " + r._name }, "Open profile →")));
  }

  function verifyBtn(data, ids, opts) {
    const list = (Array.isArray(ids) ? ids : [ids]).filter(Boolean);
    if (!data || !list.length) return null;
    opts = opts || {};
    return h("button", {
      type: "button", class: "verify",
      "aria-label": "Verify " + (opts.what || "this value") + ": show source evidence",
      onclick: function (e) { openVerify(data, list, Object.assign({}, opts, { returnFocus: e.currentTarget })); }
    }, h("span", { class: "tick", "aria-hidden": "true" }, "✓"), opts.label || "Verify");
  }
  function companyLabel(data) {
    const row = data.row || {};
    return (row._name || data.key) + (row.id ? " · " + fmtOrg(row.id) : "");
  }
  function openVerify(data, ids, opts) {
    opts = opts || {};
    const claims = ids.map(function (id) { return data.claimById.get(id); }).filter(Boolean);
    const firstClaim = claims[0];
    const title = opts.title || (firstClaim ? firstClaim.label || humanise(firstClaim.field) : "Evidence");
    clear(dlg);
    const closeBtn = h("button", { type: "button", class: "btn dlg-close", "aria-label": "Close evidence", onclick: function () { closeDialog(); } }, "×");
    const body = h("div", { class: "dlg-body" });
    if (opts.note) add(body, h("p", { class: "reason" }, opts.note));
    if (!claims.length) add(body, h("p", { class: "reason warn" }, "The cited claim is not present in this research file."));
    claims.forEach(function (c) { add(body, claimBlock(data, c, claims.length > 1)); });
    add(dlg, h("div", { class: "dlg-head" }, h("div", null, h("h2", { id: "verify-title" }, title), h("div", { class: "sub" }, companyLabel(data))), closeBtn), body);
    dlgReturn = opts.returnFocus || document.activeElement;
    if (typeof dlg.showModal === "function") {
      if (!dlg.open) dlg.showModal();
    } else dlg.setAttribute("open", "");
    dlg.scrollTop = 0;
    closeBtn.focus();
  }
  function closeDialog(skipFocus) {
    if (skipFocus) dlgReturn = null;
    if (!dlg.open) return;
    if (typeof dlg.close === "function") dlg.close();
    else { dlg.removeAttribute("open"); onDialogClosed(); }
  }
  function onDialogClosed() {
    const t = dlgReturn;
    dlgReturn = null;
    if (t && document.contains(t)) t.focus();
  }
  dlg.addEventListener("close", onDialogClosed);
  dlg.addEventListener("click", function (e) { if (e.target === dlg) closeDialog(); });

  function extraRows(c) {
    const rows = [];
    Object.keys(c).forEach(function (k) {
      if (KNOWN_CLAIM_KEYS.has(k)) return;
      const v = c[k];
      if (v === null || v === undefined || v === "" || (Array.isArray(v) && !v.length)) return;
      if (k === "verification" && typeof v === "object") {
        if (v.method) rows.push(["Verification method", methodText(v.method)]);
        if (v.candidate_source) rows.push(["Candidate source", humanise(v.candidate_source)]);
        if (Array.isArray(v.signals) && v.signals.length) rows.push(["Verification signals", v.signals.map(humanise).join(", ")]);
        if (v.proof_url) rows.push(["Proof page", extLink(v.proof_url, null, "mono")]);
        return;
      }
      let out;
      if (typeof v === "boolean") out = v ? "Yes" : "No";
      else if (typeof v === "number") out = fmtNum(v);
      else if (typeof v === "string") out = safeUrl(v) ? extLink(v, null, "mono") : v;
      else if (Array.isArray(v)) out = v.map(function (x) { return typeof x === "object" ? JSON.stringify(x) : String(x); }).join(", ");
      else out = JSON.stringify(v);
      rows.push([EXTRA_LABEL[k] || humanise(k), out]);
    });
    return rows;
  }
  function claimBlock(data, c, multi) {
    const wrap = h("section", { class: multi ? "ev-claim" : null });
    if (multi) add(wrap, h("h3", { class: "group-title" }, c.label || humanise(c.field)));
    add(wrap, h("p", { class: "dlg-value" }, valueNode(c), c.stale ? [" ", badge("Stale", "warn")] : null, c._historic ? [" ", badge("Superseded", "neutral")] : null));
    add(wrap, h("p", { class: "dlg-meta" }, [periodText(c) ? (c.period ? "Reporting period " : "") + periodText(c) : null, isNum(c.confidence) ? "confidence " + Math.round(c.confidence * 100) + "%" : null, methodText(c.method) || null].filter(Boolean).join(" · ")));
    const evs = (c.evidence_ids || []).map(function (id) { return data.evidence.get(id); }).filter(Boolean);
    add(wrap, h("h3", { class: "group-title" }, "Evidence (" + evs.length + ")"));
    if (!evs.length) add(wrap, h("p", { class: "reason warn" }, "No evidence record was found for this claim in the research file."));
    evs.forEach(function (ev) { add(wrap, evidenceCard(ev)); });
    const rows = [
      ["Field", h("span", { class: "mono" }, c.field || "—")],
      ["Section", SECTION_TITLE[c.section] || humanise(c.section)]
    ];
    if (c.period && (c.period.from || c.period.to)) rows.push(["Reporting period", (c.period.from || "…") + " → " + (c.period.to || "…")]);
    if (c.as_of) rows.push(["As of", fmtDate(c.as_of)]);
    if (c.fiscal_year) rows.push(["Fiscal year", String(c.fiscal_year)]);
    if (c.account_scope) rows.push(["Accounts", c.account_scope === "group" ? "Group accounts" : "Company accounts"]);
    if (c.unit) rows.push(["Unit", c.unit]);
    rows.push(["Confidence", isNum(c.confidence) ? Math.round(c.confidence * 100) + "%" : "—"]);
    rows.push(["Method", methodText(c.method) || "—"]);
    if (c.relationship) rows.push(["Relationship", humanise(c.relationship)]);
    rows.push(["First observed", fmtTime(c.first_observed_at)]);
    rows.push(["Last observed", fmtTime(c.last_observed_at)]);
    if (c.stale) rows.push(["Stale", (c.stale_reason || "Carried forward from an earlier run") + (c.carried_forward_from_run ? " (from " + c.carried_forward_from_run + ")" : "")]);
    if (c._historic) rows.push(["Superseded", fmtTime(c._superseded_at)]);
    extraRows(c).forEach(function (r) { rows.push(r); });
    rows.push(["Claim id", h("span", { class: "mono" }, c.id)]);
    if (multi) add(wrap, h("details", { class: "more" }, h("summary", null, "Claim details"), kvList(rows)));
    else add(wrap, h("h3", { class: "group-title" }, "Claim details"), kvList(rows));
    if (!c._historic) add(wrap, h("p", { class: "small" }, h("a", { href: "#/c/" + encodeURIComponent(data.key) + "?claim=" + encodeURIComponent(c.id) }, "Link to this claim")));
    return wrap;
  }
  function copyBtn(text, label) {
    return h("button", { type: "button", class: "btn small", onclick: function () {
      try {
        navigator.clipboard.writeText(text).then(function () { announce("Copied to clipboard."); }, function () { announce("Copy failed."); });
      } catch (e) {
        announce("Copy is not available in this browser.");
      }
    } }, label);
  }
  function evidenceCard(ev) {
    const card = h("article", { class: "ev" });
    add(card, h("h3", null, ev.source_name || "Source",
      badge(SOURCE_CLASS[ev.source_class] || humanise(ev.source_class) || "Unclassified source", ev.source_class === "company_owned" ? "info" : "ok", true),
      ev._historic ? badge("Previous run", "neutral", true) : null));
    add(card, h("div", null, extLink(ev.source_url, null, "mono")));
    if (ev.claim_span != null && ev.claim_span !== "") add(card, h("blockquote", { "aria-label": "Excerpt from the source" }, String(ev.claim_span)));
    const rows = [];
    if (ev.requested_url && ev.requested_url !== ev.source_url) rows.push(["Requested URL", extLink(ev.requested_url, null, "mono")]);
    if (ev.snapshot_final_url && ev.snapshot_final_url !== ev.source_url) rows.push(["Final URL", extLink(ev.snapshot_final_url, null, "mono")]);
    rows.push(["Retrieved", fmtTime(ev.retrieved_at)]);
    if (ev.http_status != null) rows.push(["HTTP status", String(ev.http_status)]);
    rows.push(["Content SHA-256", ev.content_sha256 ? h("span", null, h("span", { class: "mono" }, ev.content_sha256), " ", copyBtn(ev.content_sha256, "Copy")) : null]);
    rows.push(["Locator", ev.locator ? h("span", { class: "mono" }, ev.locator) : null]);
    rows.push(["Extraction method", methodText(ev.extraction_method)]);
    rows.push(["Licence", ev.licence || null]);
    if (ev.snapshot_content_type) rows.push(["Content type", ev.snapshot_content_type]);
    if (isNum(ev.snapshot_bytes)) rows.push(["Size", fmtNum(ev.snapshot_bytes) + " bytes" + (ev.snapshot_truncated ? " (truncated)" : "")]);
    if (Array.isArray(ev.snapshot_redirect_chain) && ev.snapshot_redirect_chain.length) rows.push(["Redirects", ev.snapshot_redirect_chain.map(String).join(" → ")]);
    rows.push(["Snapshot id", ev.snapshot_id ? h("span", { class: "mono" }, ev.snapshot_id) : null]);
    rows.push(["Evidence id", h("span", { class: "mono" }, ev.id)]);
    add(card, kvList(rows));
    return card;
  }

  function finModel(data, scope) {
    const years = new Set();
    const cells = {};
    data.claims.forEach(function (c) {
      const f = String(c.field || "");
      if (f.indexOf("financials.") !== 0 || c.account_scope !== scope || !c.fiscal_year) return;
      const metric = f.slice(11);
      const y = String(c.fiscal_year);
      years.add(y);
      cells[metric] = cells[metric] || {};
      if (!cells[metric][y] || (cells[metric][y].stale && !c.stale)) cells[metric][y] = c;
    });
    const list = Array.from(years).sort().reverse();
    const ratio = {};
    list.forEach(function (y) {
      const eq = cells.equity && cells.equity[y];
      const ta = cells.total_assets && cells.total_assets[y];
      if (eq && ta && isNum(eq.value) && isNum(ta.value) && ta.value !== 0) ratio[y] = { value: eq.value / ta.value, ids: [eq.id, ta.id] };
    });
    return { years: list, cells: cells, ratio: ratio };
  }
  function scopesOf(data) {
    const s = new Set();
    data.claims.forEach(function (c) { if (String(c.field || "").indexOf("financials.") === 0 && c.account_scope) s.add(c.account_scope); });
    return ["company", "group"].filter(function (x) { return s.has(x); });
  }
  function latestFin(data, scope) {
    const m = finModel(data, scope || "company");
    for (let i = 0; i < m.years.length; i += 1) {
      const y = m.years[i];
      const has = ["revenue", "operating_result", "annual_result"].some(function (k) { return m.cells[k] && m.cells[k][y]; });
      if (has) {
        const pick = function (k) { return m.cells[k] && m.cells[k][y] ? m.cells[k][y] : null; };
        return { year: y, revenue: pick("revenue"), operating_result: pick("operating_result"), annual_result: pick("annual_result"), equity: pick("equity"), total_assets: pick("total_assets"), ratio: m.ratio[y] || null };
      }
    }
    return null;
  }
  function finCellText(metric, c) {
    const v = c.value;
    if (typeof v === "number") return c.unit === "NOK" || !c.unit ? nf.format(Math.round(v)) : fmtNum(v) + " " + c.unit;
    if (typeof v === "boolean") return v ? "Yes" : "No";
    if (metric === "accounting_rules" || metric === "statement_format") return humanise(String(v).replace(/([a-z])([A-Z])/g, "$1 $2").toLowerCase());
    return claimText(c);
  }
  function finTable(data, scope) {
    const m = finModel(data, scope);
    if (!m.years.length) return h("p", { class: "muted" }, "No " + scope + " accounts in this research file.");
    const listed = new Set();
    FIN_GROUPS.forEach(function (g) { g[1].forEach(function (r) { listed.add(r[0]); }); });
    const other = Object.keys(m.cells).filter(function (k) { return !listed.has(k); }).sort().map(function (k) { return [k, humanise(k)]; });
    const groups = other.length ? FIN_GROUPS.concat([["Other items", other]]) : FIN_GROUPS;
    const tbody = h("tbody");
    groups.forEach(function (g) {
      const rows = g[1].filter(function (r) { return r[0] === "equity_ratio" ? Object.keys(m.ratio).length : m.cells[r[0]]; });
      if (!rows.length) return;
      add(tbody, h("tr", { class: "group" }, h("th", { scope: "colgroup", colspan: String(m.years.length + 1) }, g[0])));
      rows.forEach(function (r) {
        const metric = r[0];
        const tr = h("tr", { class: metric === "equity_ratio" ? "derived" : null }, h("th", { scope: "row" }, r[1]));
        m.years.forEach(function (y) {
          if (metric === "equity_ratio") {
            const d = m.ratio[y];
            add(tr, h("td", null, d ? h("button", { type: "button", class: "cellbtn" + (d.value < 0 ? " neg" : ""), "aria-label": "Equity ratio " + y + ": " + fmtPct(d.value) + ". Verify", onclick: function (e) {
              openVerify(data, d.ids, { title: "Equity ratio " + y + " (" + scope + ")", note: "Derived value: equity ÷ total assets = " + fmtPct(d.value) + ". Both inputs and their evidence are shown below.", returnFocus: e.currentTarget });
            } }, fmtPct(d.value)) : dash(" not reported")));
            return;
          }
          const c = m.cells[metric][y];
          if (!c) { add(tr, h("td", null, dash(" not reported"))); return; }
          const text = finCellText(metric, c);
          add(tr, h("td", null, h("button", {
            type: "button", class: "cellbtn" + (isNum(c.value) && c.value < 0 ? " neg" : ""), title: c.stale ? "Stale: carried forward from an earlier run" : null,
            "aria-label": r[1] + " " + y + ": " + claimText(c) + ". Verify",
            onclick: function (e) { openVerify(data, [c.id], { returnFocus: e.currentTarget }); }
          }, text + (c.stale ? " †" : ""))));
        });
        add(tbody, tr);
      });
    });
    const note = (scope === "group" ? "Group" : "Company") + " accounts, NOK. Select a figure to see its source. — means not reported (never zero).";
    return h("div", null, h("p", { class: "small muted", "aria-hidden": "true" }, note), h("div", { class: "table-wrap fit" }, h("table", { class: "fin" },
      h("caption", { class: "sr-only" }, note),
      h("thead", null, h("tr", null, h("th", { scope: "col" }, "Item"), m.years.map(function (y) { return h("th", { scope: "col" }, y); }))),
      tbody)));
  }

  function sectionReason(sec) {
    if (!sec) return null;
    const notes = (sec.notes || []).filter(Boolean);
    if (sec.state === "available") return notes.length ? h("p", { class: "reason" }, notes.join(" · ")) : null;
    const tone = sec.state === "ambiguous" ? "warn" : sec.state === "failed" || sec.state === "blocked" ? "bad" : "";
    return h("p", { class: "reason " + tone }, h("strong", null, (STATE_LABEL[sec.state] || humanise(sec.state) || "Unknown") + ". "), notes.length ? notes.join(" · ") : "No reason was recorded.");
  }
  function claimRowsKv(data, claims, what) {
    return kvList(claims.map(function (c) {
      const extra = c.as_of && !c.period && fmtDate(c.as_of) === String(c.value) ? "" : periodText(c);
      return [c.label || humanise(c.field), h("span", null, valueNode(c), c.stale ? [" ", badge("Stale", "warn")] : null, extra ? h("span", { class: "extra" }, extra) : null), verifyBtn(data, [c.id], { what: (c.label || what || "value") })];
    }));
  }
  function claimsTable(data, claims, section) {
    const tbody = h("tbody");
    claims.forEach(function (c) {
      const tr = h("tr", { "data-claim": c.id },
        h("td", { "data-label": "Claim" }, h("span", null, h("span", { class: "lbl" }, c.label || humanise(c.field)), c.stale ? [" ", badge("Stale", "warn")] : null, h("span", { class: "fld" }, c.field))),
        h("td", { class: "val", "data-label": "Value" }, valueNode(c)),
        h("td", { class: "num", "data-label": "Period / as of" }, periodText(c) || h("span", { class: "dash" }, "—")),
        h("td", { class: "num", "data-label": "Confidence" }, isNum(c.confidence) ? Math.round(c.confidence * 100) + "%" : "—"),
        h("td", { "data-label": "Method" }, methodText(c.method) || "—"),
        h("td", { class: "act" }, verifyBtn(data, [c.id], { what: c.label || c.field })));
      view.rowEls.set(c.id, tr);
      add(tbody, tr);
    });
    return h("div", { class: "table-wrap stack" }, h("table", { class: "claims" },
      h("caption", { class: "sr-only" }, "All claims in " + (SECTION_TITLE[section] || section)),
      h("thead", null, h("tr", null, ["Claim", "Value", "Period / as of", "Confidence", "Method", "Evidence"].map(function (t) { return h("th", { scope: "col" }, t); }))),
      tbody));
  }
  function capped(items, limit, render, noun) {
    const wrap = h("div");
    const list = h("ol", { class: "list" });
    add(wrap, list);
    let shown = 0;
    function more() {
      items.slice(shown, shown + limit).forEach(function (it) { add(list, render(it)); });
      shown = Math.min(items.length, shown + limit);
      btnRow.hidden = shown >= items.length;
      btn.textContent = "Show all " + items.length + " " + noun;
    }
    const btn = h("button", { type: "button", class: "btn small", onclick: function () { limit = items.length; more(); } });
    const btnRow = h("div", { class: "more-row" }, btn);
    add(wrap, btnRow);
    more();
    return wrap;
  }

  function leadershipView(data) {
    const claims = data.bySection.leadership || [];
    if (!claims.length) return null;
    const wrap = h("div");
    const used = new Set();
    const groups = ROLE_GROUPS.map(function (g) { return [g[1], claims.filter(function (c) { return c.field === g[0]; })]; });
    const rest = claims.filter(function (c) { return !ROLE_GROUPS.some(function (g) { return g[0] === c.field; }); });
    if (rest.length) groups.push(["Other roles", rest]);
    groups.forEach(function (g) {
      if (!g[1].length) return;
      add(wrap, h("h3", { class: "group-title" }, g[0]));
      add(wrap, h("ul", { class: "list" }, g[1].map(function (c) {
        used.add(c.id);
        const org = c.holder_organisation_number ? String(c.holder_organisation_number) : "";
        const target = org && resolveRow(org);
        const meta = [c.label, c.role_group && c.role_group !== c.label ? c.role_group : null, c.as_of ? "registered " + fmtDate(c.as_of) : null, c.holder_type ? humanise(c.holder_type) : null, c.elected_by || null].filter(Boolean).join(" · ");
        return h("li", null, h("div", null,
          h("div", { class: "t" }, target ? h("a", { href: "#/c/" + encodeURIComponent(target.file) }, String(c.value)) : claimText(c), c.stale ? [" ", badge("Stale", "warn")] : null),
          h("div", { class: "m" }, meta)), verifyBtn(data, [c.id], { what: c.label + " " + claimText(c) }));
      })));
    });
    return wrap;
  }
  function workplacesView(data) {
    const addr = fieldAll(data, "location.business_address").concat(fieldAll(data, "location.municipality"));
    const subs = fieldAll(data, "location.registered_workplace").slice().sort(function (a, b) { return String(a.value).localeCompare(String(b.value), "nb"); });
    if (!addr.length && !subs.length) return null;
    const wrap = h("div");
    if (addr.length) add(wrap, claimRowsKv(data, addr, "address"));
    if (subs.length) {
      add(wrap, h("h3", { class: "group-title" }, "Registered workplaces (" + subs.length + ")"));
      add(wrap, capped(subs, 12, function (c) {
        const meta = [c.subunit_organisation_number ? "Subunit " + fmtOrg(c.subunit_organisation_number) : null, c.municipality, isNum(c.employees) ? c.employees + " employees" : null, c.started ? "started " + fmtDate(c.started) : null, c.industry].filter(Boolean).join(" · ");
        return h("li", null, h("div", null, h("div", { class: "t" }, claimText(c), c.stale ? [" ", badge("Stale", "warn")] : null), h("div", { class: "m" }, meta)), verifyBtn(data, [c.id], { what: "workplace " + claimText(c) }));
      }, "workplaces"));
    }
    return wrap;
  }
  function websiteView(data) {
    const claims = data.bySection.website || [];
    const cands = ((data.env.website_research || {}).candidates || []).filter(function (c) { return c && typeof c === "object"; });
    if (!claims.length && !cands.length) return null;
    const wrap = h("div");
    if (claims.length) add(wrap, claimRowsKv(data, claims, "website"));
    if (cands.length) {
      add(wrap, h("h3", { class: "group-title" }, "Website candidates checked (" + cands.length + ")"));
      add(wrap, h("div", { class: "table-wrap stack" }, h("table", { class: "claims" },
        h("thead", null, h("tr", null, ["Candidate", "Found via", "Outcome", "Detail"].map(function (t) { return h("th", { scope: "col" }, t); }))),
        h("tbody", null, cands.map(function (c) {
          const outcome = String(c.outcome || "unknown");
          const tone = outcome === "verified" ? "ok" : outcome === "ambiguous" ? "warn" : "neutral";
          const url = c.final_url || c.url;
          return h("tr", null,
            h("td", { class: "val", "data-label": "Candidate" }, outcome === "verified" ? extLink(url, c.domain || prettyUrl(url || "")) : h("span", { class: "mono" }, c.domain || c.url || "—")),
            h("td", { "data-label": "Found via" }, [humanise(c.source), c.detail ? h("span", { class: "fld" }, c.detail) : null]),
            h("td", { "data-label": "Outcome" }, badge(humanise(outcome), tone)),
            h("td", { class: "val", "data-label": "Detail" }, [c.method ? methodText(c.method) : c.reason || "—", Array.isArray(c.signals) && c.signals.length ? h("span", { class: "fld" }, "signals: " + c.signals.join(", ")) : null]));
        })))));
    }
    return wrap;
  }
  function profilesView(data) {
    const claims = prefixed(data, "profile.");
    if (!claims.length) return null;
    return h("ul", { class: "list" }, claims.map(function (c) {
      const platform = String(c.field).slice(8);
      return h("li", null, h("div", null, h("div", { class: "t" }, PLATFORM[platform] || humanise(platform)), h("div", { class: "m" }, extLink(c.value, null), " · ", c.label || "")), verifyBtn(data, [c.id], { what: (PLATFORM[platform] || platform) + " profile" }));
    }));
  }
  function hiringView(data) {
    const jobs = fieldAll(data, "hiring.job_posting").slice().sort(function (a, b) { return String(claimDate(b)).localeCompare(String(claimDate(a))); });
    const other = (data.bySection.hiring || []).filter(function (c) { return c.field !== "hiring.job_posting"; });
    if (!jobs.length && !other.length) return null;
    const wrap = h("div");
    if (jobs.length) {
      add(wrap, h("h3", { class: "group-title" }, "Job postings (" + jobs.length + ")"));
      add(wrap, capped(jobs, 15, function (c) {
        const meta = [c.employer_name ? c.employer_name + (c.employer_organisation_number ? " (" + fmtOrg(c.employer_organisation_number) + ")" : "") : null, Array.isArray(c.work_locations) && c.work_locations.length ? c.work_locations.join(", ") : null, c.date_posted ? "posted " + fmtDate(c.date_posted) : null, c.expires ? "expires " + fmtDate(c.expires) : c.valid_through ? "valid through " + fmtDate(c.valid_through) : null, c.source_system].filter(Boolean).join(" · ");
        return h("li", null, h("div", null, h("div", { class: "t" }, safeUrl(c.url) ? extLink(c.url, claimText(c)) : claimText(c), c.stale ? [" ", badge("Stale", "warn")] : null), h("div", { class: "m" }, meta)), verifyBtn(data, [c.id], { what: "job posting " + claimText(c) }));
      }, "job postings"));
    }
    if (other.length) add(wrap, claimRowsKv(data, other, "hiring"));
    return wrap;
  }
  function activityView(data) {
    const items = prefixed(data, "activity.").slice().sort(function (a, b) { return String(claimDate(b)).localeCompare(String(claimDate(a))); });
    if (!items.length) return null;
    const wrap = h("div");
    const list = h("ol", { class: "timeline", "aria-label": "Dated activity, newest first" });
    let shown = 0;
    let limit = 20;
    const btn = h("button", { type: "button", class: "btn small", onclick: function () { limit = items.length; more(); } });
    const row = h("div", { class: "more-row" }, btn);
    function more() {
      items.slice(shown, limit).forEach(function (c) {
        const d = claimDate(c);
        const text = typeof c.value === "string" && c.value ? c.value : c.value === null || c.value === undefined ? (c.label || humanise(c.field)) : (c.label ? c.label + ": " : "") + claimText(c);
        const src = c.field === "activity.website_news" ? "Company website news" : String(c.field).indexOf("activity.registry") === 0 || c.field === "activity.role_group_changed" ? "Enhetsregisteret" : humanise(String(c.field).slice(9));
        add(list, h("li", null, h("time", { datetime: d ? fmtDate(d) : null }, d ? fmtDate(d) : "Undated"),
          h("div", null, h("div", { class: "t" }, safeUrl(c.url) ? extLink(c.url, text) : text, c.stale ? [" ", badge("Stale", "warn")] : null), h("div", { class: "m" }, src)),
          verifyBtn(data, [c.id], { what: text })));
      });
      shown = Math.min(items.length, limit);
      row.hidden = shown >= items.length;
      btn.textContent = "Show all " + items.length + " items";
    }
    add(wrap, list, row);
    more();
    return wrap;
  }
  function genericView(section) {
    return function (data) {
      const claims = data.bySection[section] || [];
      return claims.length ? claimRowsKv(data, claims) : null;
    };
  }
  function accountsView(data) {
    const scopes = scopesOf(data);
    const notes = [];
    const latest = first(data, "financials.latest_submitted_year");
    if (latest) notes.push(["Latest submitted annual accounts", claimText(latest), verifyBtn(data, [latest.id], { what: "latest submitted year" })]);
    const parent = fieldAll(data, "financials.parent_company_filer");
    if (parent.length) notes.push(["Files as parent company", claimText(parent[0]) + (parent[0].period ? " (" + String(parent[0].period.to || "").slice(0, 4) + ")" : ""), verifyBtn(data, [parent[0].id], { what: "parent company filing" })]);
    if (!scopes.length && !notes.length) return null;
    const wrap = h("div");
    if (notes.length) add(wrap, kvList(notes));
    if (!scopes.length) return wrap;
    let scope = state.scopes[data.key] && scopes.indexOf(state.scopes[data.key]) !== -1 ? state.scopes[data.key] : scopes[0];
    const holder = h("div");
    const seg = h("div", { class: "seg", role: "group", "aria-label": "Accounts scope" });
    function paint() {
      add(clear(holder), finTable(data, scope));
      seg.querySelectorAll("button").forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-scope") === scope ? "true" : "false"); });
    }
    scopes.forEach(function (s) {
      add(seg, h("button", { type: "button", "data-scope": s, onclick: function () { scope = s; state.scopes[data.key] = s; paint(); } }, s === "group" ? "Group accounts" : "Company accounts"));
    });
    if (scopes.length > 1) add(wrap, h("div", { class: "panel-head" }, h("span", { class: "small muted" }, "Company accounts cover this legal entity; group accounts consolidate its subsidiaries."), seg));
    else add(wrap, h("p", { class: "small muted" }, scopes[0] === "group" ? "Only group accounts were found." : "Only company accounts were found; no group accounts are filed."));
    add(wrap, holder);
    paint();
    return wrap;
  }
  const SECTION_VIEWS = {
    legal_identity: genericView("legal_identity"),
    annual_accounts: accountsView,
    leadership: leadershipView,
    workplaces: workplacesView,
    website: websiteView,
    company_profiles: profilesView,
    hiring: hiringView,
    public_activity: activityView,
    contact: genericView("contact"),
    external_identifiers: genericView("external_identifiers")
  };

  function heroFact(label, value, btn) {
    return h("div", null, h("dt", null, label), h("dd", null, h("span", { class: "fv" }, value == null || value === "" ? dash() : value), btn || null));
  }
  function hero(row, data) {
    const env = data ? data.env : null;
    const li = env ? env.legal_identity || {} : {};
    const name = li.legal_name || row._name;
    const brand = li.public_brand || row.brand;
    const status = li.status || row.status;
    const industries = li.industries || row.industries || [];
    const website = li.official_website || row.website;
    const websiteSec = env && env.sections ? env.sections.website : null;
    const c = function (f) { return data ? first(data, f) : null; };
    const v = function (f, what) { const x = c(f); return x ? verifyBtn(data, [x.id], { what: what }) : null; };
    const industryClaim = data ? (fieldAll(data, "identity.industry")[0] || null) : null;
    const employeesClaim = c("identity.employees");
    const card = h("section", { class: "card hero", "aria-labelledby": "co-h" });
    const brreg = c("identifier.brreg_public_page");
    const brregUrl = brreg ? brreg.value : (/^\d{9}$/.test(row.id || "") ? "https://virksomhet.brreg.no/nb/oppslag/enheter/" + row.id : null);
    add(card, h("div", { class: "hero-top" },
      h("div", { class: "hero-name" },
        h("h1", { id: "co-h", tabindex: "-1" }, name),
        brand && norm(brand) !== norm(name) ? h("div", { class: "brandline" }, "Public brand: ", h("strong", null, brand), " ", v("identity.public_brand", "public brand")) : null,
        h("div", { class: "hero-badges" }, statusBadge(status), row.state !== "available" ? stateBadge(row.state, "Research: ") : null,
          (env && env.synthesis && env.synthesis.signals || []).filter(function (s) { return s && s.signal && String(s.signal).indexOf("registry_status_") !== 0; }).map(function (s) { return badge(signalText(s.signal), SEVERITY_TONE[s.severity] || "neutral"); }))),
      h("div", { class: "hero-actions" }, compareButton(row), brregUrl ? extLink(brregUrl, "Brønnøysund register", "btn") : null)));
    const websiteNode = website && (!websiteSec || websiteSec.state === "available")
      ? extLink(website, hostOf(website))
      : websiteSec && data ? h("span", null, stateBadge(websiteSec.state), " ", h("a", {
        class: "small", href: "#/c/" + encodeURIComponent(data.key) + "?s=website", title: (websiteSec.notes || [])[0] || "",
        onclick: function (e) { e.preventDefault(); scrollToSection(data.key, "website"); }
      }, "Why?")) : websiteSec ? stateBadge(websiteSec.state) : null;
    if (!li.legal_name && row.state !== "available") {
      add(card, h("p", { class: "reason bad" }, h("strong", null, "Research " + (STATE_LABEL[row.state] || humanise(row.state) || "incomplete").toLowerCase() + ". "), row.note || "No registry record could be resolved for this input."),
        h("dl", { class: "hero-facts" }, heroFact("Input", inputText(row.input) || row.id), heroFact("Researched", fmtTime((env && env.run && env.run.completed_at) || row.completed_at))));
      return card;
    }
    add(card, h("dl", { class: "hero-facts" },
      heroFact("Organisation number", row.id ? h("span", { class: "mono" }, fmtOrg(row.id)) : inputText(row.input), v("identity.organisation_number", "organisation number")),
      heroFact("Legal form", (li.legal_form || row.form) ? (li.legal_form || row.form) + ((li.legal_form_label || row.form_label) ? " – " + (li.legal_form_label || row.form_label) : "") : null, v("identity.legal_form", "legal form")),
      heroFact("Municipality", li.municipality || row.municipality, v("location.municipality", "municipality")),
      heroFact("Primary industry", industries[0] || null, industryClaim ? verifyBtn(data, [industryClaim.id], { what: "industry" }) : null),
      heroFact("Employees", isNum(li.employees != null ? li.employees : row.employees) ? fmtNum(li.employees != null ? li.employees : row.employees) + (employeesClaim && employeesClaim.as_of ? " (as of " + fmtDate(employeesClaim.as_of) + ")" : "") : null, employeesClaim ? verifyBtn(data, [employeesClaim.id], { what: "employees" }) : null),
      heroFact("Website", websiteNode, v("website.official_url", "official website")),
      heroFact("Founded", li.founded_date ? fmtDate(li.founded_date) : null, v("identity.founded_date", "founding date")),
      heroFact("Researched", fmtTime((env && env.run && env.run.completed_at) || row.completed_at))));
    if (data) add(card, kpis(data));
    return card;
  }
  function kpis(data) {
    const lf = latestFin(data, "company");
    const sec = (data.env.sections || {}).annual_accounts;
    if (!lf) {
      return h("div", { class: "kpis" }, h("div", { class: "kpi" }, h("span", { class: "k" }, "Annual accounts"), h("span", { class: "s" }, sec ? (STATE_LABEL[sec.state] || humanise(sec.state)) + ": " + ((sec.notes || [])[0] || "no company accounts found") : "No company accounts found")));
    }
    const item = function (label, c, fmt, sub) {
      return h("div", { class: "kpi" }, h("span", { class: "k" }, label),
        h("span", { class: "v" + (c && isNum(c.value) && c.value < 0 ? " neg" : "") }, c ? fmt(c.value) : "—"),
        h("span", { class: "s" }, sub), c ? verifyBtn(data, [c.id], { what: label }) : null);
    };
    const sub = "Company accounts " + lf.year;
    const ratio = lf.ratio;
    return h("div", { class: "kpis" },
      item("Revenue", lf.revenue, fmtNokShort, sub),
      item("Operating result", lf.operating_result, fmtNokShort, sub),
      item("Annual result", lf.annual_result, fmtNokShort, sub),
      h("div", { class: "kpi" }, h("span", { class: "k" }, "Equity ratio"),
        h("span", { class: "v" + (ratio && ratio.value < 0 ? " neg" : "") }, ratio ? fmtPct(ratio.value) : "—"),
        h("span", { class: "s" }, ratio ? "Equity " + fmtNokShort(lf.equity.value) + " ÷ assets " + fmtNokShort(lf.total_assets.value) : sub),
        ratio ? verifyBtn(data, ratio.ids, { what: "equity ratio", title: "Equity ratio " + lf.year, note: "Derived value: equity ÷ total assets = " + fmtPct(ratio.value) + "." }) : null));
  }

  function citeButtons(data, ids, numbers) {
    const list = (ids || []).filter(Boolean);
    if (!list.length) return null;
    return h("div", { class: "cites" }, h("span", { class: "lbl" }, "Sources"), list.map(function (id) {
      const c = data.claimById.get(id);
      const n = numbers.get(id);
      return h("button", {
        type: "button", class: "cite",
        "aria-label": "Source " + n + ": " + (c ? (c.label || c.field) + ", " + claimText(c) : "claim " + id),
        title: c ? (c.label || c.field) + ": " + claimText(c) : id,
        onclick: function (e) { revealClaim(data, id, e.currentTarget); }
      }, String(n));
    }));
  }
  function summaryPanel(data) {
    const syn = data.env.synthesis || {};
    const numbers = new Map();
    const number = function (ids) { (ids || []).forEach(function (id) { if (!numbers.has(id)) numbers.set(id, numbers.size + 1); }); };
    (syn.paragraphs || []).forEach(function (p) { number(p.claim_ids); });
    (syn.signals || []).forEach(function (s) { number(s.claim_ids); });
    const panel = h("section", { class: "card panel", id: "s-summary", "aria-labelledby": "h-summary" },
      h("div", { class: "panel-head" }, h("h2", { id: "h-summary", tabindex: "-1" }, "Summary")));
    const paras = (syn.paragraphs || []).filter(function (p) { return p && p.text; });
    if (!paras.length && syn.summary) add(panel, h("p", null, syn.summary));
    if (!paras.length && !syn.summary) add(panel, h("p", { class: "muted" }, "No summary was produced for this input."));
    paras.forEach(function (p) {
      add(panel, h("div", { class: "para" }, h("h3", null, TOPIC_TITLE[p.topic] || humanise(p.topic)), h("p", null, p.text), citeButtons(data, p.claim_ids, numbers)));
    });
    const sigs = (syn.signals || []).filter(function (s) { return s && s.signal; });
    if (sigs.length) {
      add(panel, h("h3", { class: "group-title" }, "Signals"));
      add(panel, h("ul", { class: "signals" }, sigs.map(function (s) {
        return h("li", null, badge(humanise(s.severity || "info"), SEVERITY_TONE[s.severity] || "neutral"), h("span", null, signalText(s.signal)), citeButtons(data, s.claim_ids, numbers));
      })));
    }
    if (syn.method) add(panel, h("p", { class: "method" }, "How this summary was written: " + syn.method));
    return panel;
  }
  function changeValue(v) {
    if (v === null || v === undefined || v === "") return "—";
    if (typeof v === "number") return fmtNum(v);
    if (typeof v === "boolean") return v ? "Yes" : "No";
    if (typeof v === "object") return JSON.stringify(v);
    return String(v);
  }
  function changesPanel(data) {
    const env = data.env;
    const ref = env.refresh || {};
    const changes = (env.changes || []).filter(function (c) { return c && typeof c === "object"; });
    const stale = data.claims.filter(function (c) { return c.stale; });
    const history = (env.history || []).filter(function (x) { return x && x.claim; });
    const panel = h("section", { class: "card panel", id: "s-changes", "aria-labelledby": "h-changes" },
      h("div", { class: "panel-head" }, h("div", { class: "titles" }, h("h2", { id: "h-changes", tabindex: "-1" }, "What changed since the last run"), badge(changes.length + " change" + (changes.length === 1 ? "" : "s"), changes.length ? "info" : "neutral", true))));
    if (ref.is_first_run || !ref.previous_run_id) {
      add(panel, h("p", { class: "muted" }, ref.is_first_run === false ? "No previous run is recorded." : "This is the first run for this company, so there is nothing to compare yet. The next run will list new, removed and changed values here."));
    } else {
      add(panel, h("p", { class: "small muted" }, "Compared with run ", h("span", { class: "mono" }, ref.previous_run_id), " (completed " + fmtTime(ref.previous_completed_at) + "): " +
        [["changed", ref.changed], ["added", ref.added], ["removed", ref.removed], ["unchanged", ref.unchanged], ["carried forward", ref.carried_forward]].filter(function (x) { return isNum(x[1]); }).map(function (x) { return x[1] + " " + x[0]; }).join(", ") + "."));
      if (!changes.length) add(panel, h("p", null, "No values changed since the previous run."));
    }
    if (changes.length) {
      const order = { material: 0, minor: 1 };
      const sorted = changes.slice().sort(function (a, b) { return (order[a.materiality] != null ? order[a.materiality] : 2) - (order[b.materiality] != null ? order[b.materiality] : 2); });
      add(panel, h("ul", { class: "changes" }, sorted.map(function (ch) {
        const prevIds = ch.previous_claim_id && data.claimById.has(ch.previous_claim_id) ? [ch.previous_claim_id] : [];
        return h("li", null,
          h("div", { class: "change-head" }, badge(humanise(ch.type || "change"), "info", true), ch.materiality ? badge(humanise(ch.materiality), ch.materiality === "material" ? "warn" : "neutral", true) : null, h("span", { class: "small muted" }, (SECTION_TITLE[ch.section] || humanise(ch.section)) + " · detected " + fmtTime(ch.detected_at))),
          h("div", { class: "t" }, ch.summary || humanise(ch.field)),
          h("div", { class: "delta" }, h("span", { class: "was" }, h("span", { class: "sr-only" }, "Previous value: "), changeValue(ch.previous_value)), h("span", { class: "arrow", "aria-hidden": "true" }, "→"), h("span", { class: "now" }, h("span", { class: "sr-only" }, "Current value: "), ch.current_value === null || ch.current_value === undefined ? "no longer reported" : changeValue(ch.current_value))),
          h("div", { class: "change-actions" },
            ch.current_claim_id ? verifyBtn(data, [ch.current_claim_id], { label: "Verify current", what: "current value" }) : null,
            prevIds.length ? verifyBtn(data, prevIds, { label: "Previous evidence", what: "previous value", title: "Previous value" }) : (ch.previous_evidence_ids && ch.previous_evidence_ids.length ? h("span", { class: "small muted" }, "Previous evidence ids: " + ch.previous_evidence_ids.join(", ")) : null)));
      })));
    }
    if (stale.length) {
      add(panel, h("p", { class: "reason warn" }, h("strong", null, stale.length + " stale value" + (stale.length === 1 ? "" : "s") + ". "), "Carried forward from the previous run because the source could not be refreshed in this run. They are marked “Stale” wherever they appear."));
    }
    if (history.length) {
      const det = h("details", { class: "more" }, h("summary", null, "Superseded values (" + history.length + ")"));
      add(det, h("ul", { class: "list" }, history.slice().reverse().map(function (entry) {
        const c = entry.claim;
        return h("li", null, h("div", null, h("div", { class: "t" }, (c.label || humanise(c.field)) + ": " + claimText(c)), h("div", { class: "m" }, "Superseded " + fmtTime(entry.superseded_at) + (entry.reason ? " · " + entry.reason : ""))), c.id && data.claimById.has(c.id) ? verifyBtn(data, [c.id], { label: "Evidence", what: "superseded value" }) : null);
      })));
      add(panel, det);
    }
    return panel;
  }
  function unknownsPanel(data) {
    const env = data.env;
    const unknowns = (env.unknowns || []).filter(function (u) { return u && typeof u === "object"; });
    const errors = (env.errors || []).filter(function (e) { return e && typeof e === "object"; });
    if (!unknowns.length && !errors.length) return null;
    const panel = h("section", { class: "card panel", id: "s-unknowns", "aria-labelledby": "h-unknowns" },
      h("div", { class: "panel-head" }, h("div", { class: "titles" }, h("h2", { id: "h-unknowns", tabindex: "-1" }, "Not established in this run"), badge(String(unknowns.length), "warn", true))),
      h("p", { class: "small muted" }, "These were checked but could not be confirmed. They are reported as unknown, never as zero or empty."));
    if (unknowns.length) {
      add(panel, h("ul", { class: "list" }, unknowns.map(function (u) {
        const s = u.availability || u.state;
        return h("li", null, h("div", null, h("div", { class: "t" }, SECTION_TITLE[u.section] || u.label || humanise(u.section), " ", stateBadge(s)), h("div", { class: "m" }, u.reason || "No reason recorded.")),
          u.section ? h("a", { class: "btn small", href: "#/c/" + encodeURIComponent(data.key) + "?s=" + encodeURIComponent(u.section), onclick: function (e) { e.preventDefault(); scrollToSection(data.key, u.section); } }, "Go to section") : null);
      })));
    }
    if (errors.length) {
      add(panel, h("h3", { class: "group-title" }, "Errors during research (" + errors.length + ")"));
      add(panel, h("ul", { class: "list" }, errors.map(function (e) {
        return h("li", null, h("div", null, h("div", { class: "t" }, e.error || "Error"), h("div", { class: "m" }, [humanise(e.source || "agent"), e.state ? humanise(e.state) : null].filter(Boolean).join(" · "), e.url ? [" · ", extLink(e.url, null, "mono")] : null)));
      })));
    }
    return panel;
  }
  function sectionPanel(data, name) {
    const sec = (data.env.sections || {})[name] || { state: "", notes: [] };
    const claims = data.bySection[name] || [];
    const title = SECTION_TITLE[name] || sec.label || humanise(name);
    const panel = h("section", { class: "card panel", id: "s-" + name, "aria-labelledby": "h-" + name });
    add(panel, h("div", { class: "panel-head" }, h("div", { class: "titles" }, h("h2", { id: "h-" + name, tabindex: "-1" }, title), stateBadge(sec.state || "unknown"), h("span", { class: "small muted" }, claims.length + " claim" + (claims.length === 1 ? "" : "s")))));
    if (sec.label && sec.label !== title) add(panel, h("p", { class: "panel-sub" }, sec.label));
    const reason = sectionReason(sec);
    if (reason) add(panel, reason);
    const body = SECTION_VIEWS[name] ? SECTION_VIEWS[name](data) : null;
    if (body) add(panel, body);
    else if (!reason && !claims.length) add(panel, h("p", { class: "muted" }, "Nothing was recorded for this section."));
    const srcs = (sec.sources_checked || []).filter(Boolean);
    if (srcs.length || sec.checked_at) add(panel, h("p", { class: "sources" }, srcs.length ? "Sources checked: " + srcs.join("; ") : "", sec.checked_at ? (srcs.length ? " · " : "") + "checked " + fmtTime(sec.checked_at) : ""));
    if (claims.length) {
      const det = h("details", { class: "more" }, h("summary", null, claims.length === 1 ? "The claim in this section, with confidence and method" : "All " + claims.length + " claims in this section, with confidence and method"));
      const render = function () { if (!det._done) { det._done = true; add(det, claimsTable(data, claims, name)); } };
      det.addEventListener("toggle", function () { if (det.open) render(); });
      view.details[name] = det;
      view.renderers[name] = render;
      add(panel, det);
    }
    return panel;
  }
  function toc(data) {
    const secs = data.env.sections || {};
    const entries = [["summary", "Summary", null], ["changes", "Changes", null]];
    if ((data.env.unknowns || []).length || (data.env.errors || []).length) entries.push(["unknowns", "Not established", null]);
    SECTION_ORDER.forEach(function (name) {
      const st = (secs[name] || {}).state || "";
      entries.push([name, SECTION_TITLE[name] || humanise(name), st]);
    });
    return h("nav", { class: "card toc", "aria-label": "Sections of this profile" }, h("h2", null, "On this page"), h("ol", null, entries.map(function (e) {
      return h("li", null, h("a", {
        href: "#/c/" + encodeURIComponent(data.key) + "?s=" + encodeURIComponent(e[0]),
        onclick: function (ev) { ev.preventDefault(); scrollToSection(data.key, e[0]); }
      }, h("span", null, e[1]), e[2] !== null ? h("span", { class: "dot " + ({ available: "A", not_available: "N", blocked: "B", not_applicable: "X", ambiguous: "M", failed: "F" }[e[2]] || ""), title: STATE_LABEL[e[2]] || "Unknown" }, h("span", { class: "sr-only" }, " (" + (STATE_LABEL[e[2]] || "unknown") + ")")) : null));
    })));
  }
  function scrollToSection(key, name) {
    const el = document.getElementById("s-" + name);
    if (!el) return;
    replaceHash("#/c/" + encodeURIComponent(key) + "?s=" + encodeURIComponent(name));
    el.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
    const head = el.querySelector("h2");
    if (head) head.focus({ preventScroll: true });
  }
  function revealClaim(data, id, opener) {
    const c = data.claimById.get(id);
    let target = opener || null;
    if (c && view.details[c.section]) {
      const det = view.details[c.section];
      if (view.renderers[c.section]) view.renderers[c.section]();
      det.open = true;
      const tr = view.rowEls.get(id);
      if (tr) {
        tr.scrollIntoView({ behavior: "auto", block: "center" });
        tr.classList.add("hl");
        window.setTimeout(function () { tr.classList.remove("hl"); }, 2600);
        target = tr.querySelector(".verify") || target;
      }
    }
    openVerify(data, [id], { returnFocus: target });
  }

  function renderCompany(key, params) {
    const row = resolveRow(key);
    clear(main);
    window.scrollTo(0, 0);
    if (!row) {
      document.title = "Not found — Signalpost Anchor";
      add(main, h("div", { class: "crumbs" }, h("a", { href: listHash() }, "← All companies")),
        h("h1", { tabindex: "-1" }, "Company not found"),
        h("p", { class: "notice" }, "No company with key “" + key + "” is part of this research run."));
      main.querySelector("h1").focus();
      return;
    }
    if (row.file !== key) replaceHash("#/c/" + encodeURIComponent(row.file));
    document.title = row._name + " — Signalpost Anchor";
    const token = state.token;
    const crumbs = h("div", { class: "crumbs" }, h("a", { href: listHash() }, "← All companies"));
    const heroHolder = h("div", null, hero(row, null));
    const bodyHolder = h("div", null, h("p", { class: "notice", role: "status" }, "Loading the full research file…"));
    add(main, crumbs, heroHolder, bodyHolder);
    const h1 = main.querySelector("h1");
    if (h1) h1.focus({ preventScroll: true });
    loadCompany(row).then(function (data) {
      if (token !== state.token) return;
      view.data = data;
      add(clear(heroHolder), hero(row, data));
      const content = h("div", { class: "content" }, summaryPanel(data), changesPanel(data), unknownsPanel(data), SECTION_ORDER.map(function (name) { return sectionPanel(data, name); }));
      add(clear(bodyHolder), h("div", { class: "layout" }, toc(data), content));
      const focusH1 = heroHolder.querySelector("h1");
      if (focusH1 && document.activeElement === document.body) focusH1.focus({ preventScroll: true });
      const claim = params && params.get("claim");
      const sec = params && params.get("s");
      if (claim) revealClaim(data, claim, null);
      else if (sec) scrollToSection(data.key, sec);
    }).catch(function (err) {
      if (token !== state.token) return;
      add(clear(bodyHolder), h("p", { class: "notice error", role: "alert" }, err && err.message ? err.message : "The research file could not be loaded."));
    });
  }

  function cmpDefs() {
    const one = function (f, what, fmt) {
      return function (row, data) {
        const c = first(data, f);
        return c ? { text: fmt ? fmt(c) : claimText(c), ids: [c.id], what: what } : null;
      };
    };
    const fin = function (metric, label) {
      return function (row, data) {
        const lf = latestFin(data, "company");
        const c = lf && lf[metric];
        return c ? { text: fmtNokShort(c.value) + " (" + lf.year + ")", ids: [c.id], what: label, neg: isNum(c.value) && c.value < 0 } : null;
      };
    };
    const people = function (f, what) {
      return function (row, data) {
        const cs = field(data, f);
        return cs.length ? { text: cs.map(claimText).join(", "), ids: cs.map(function (c) { return c.id; }), what: what } : null;
      };
    };
    return [
      ["Registry status", function (row, data) { const c = first(data, "identity.status"); const s = (data.env.legal_identity || {}).status || row.status; return s ? { node: statusBadge(s), text: s, ids: c ? [c.id] : [], what: "registry status" } : null; }],
      ["Research state", function (row) { return { node: stateBadge(row.state), text: row.state }; }],
      ["Legal form", one("identity.legal_form", "legal form")],
      ["Industry", function (row, data) { const c = fieldAll(data, "identity.industry")[0]; return c ? { text: claimText(c), ids: [c.id], what: "industry" } : null; }],
      ["Municipality", one("location.municipality", "municipality")],
      ["Employees", one("identity.employees", "employees", function (c) { return fmtNum(c.value) + (c.as_of ? " (" + fmtDate(c.as_of) + ")" : ""); })],
      ["Revenue (latest)", fin("revenue", "revenue")],
      ["Operating result", fin("operating_result", "operating result")],
      ["Annual result", fin("annual_result", "annual result")],
      ["Equity ratio", function (row, data) {
        const lf = latestFin(data, "company");
        return lf && lf.ratio ? { text: fmtPct(lf.ratio.value) + " (" + lf.year + ")", ids: lf.ratio.ids, what: "equity ratio", neg: lf.ratio.value < 0, title: "Equity ratio " + lf.year, note: "Derived value: equity ÷ total assets = " + fmtPct(lf.ratio.value) + "." } : null;
      }],
      ["Website", function (row, data) {
        const c = first(data, "website.official_url");
        if (c) return { node: extLink(c.value, hostOf(c.value)), text: String(c.value), ids: [c.id], what: "website" };
        const sec = (data.env.sections || {}).website;
        return sec ? { node: h("span", null, stateBadge(sec.state), h("span", { class: "note" }, (sec.notes || [])[0] || "")), text: "state:" + sec.state } : null;
      }],
      ["Company profiles", function (row, data) {
        const cs = prefixed(data, "profile.");
        if (!cs.length) return null;
        return { node: h("span", null, cs.map(function (c, i) { const p = String(c.field).slice(8); return [i ? ", " : "", extLink(c.value, PLATFORM[p] || humanise(p))]; })), text: cs.map(function (c) { return c.field; }).sort().join(","), ids: cs.map(function (c) { return c.id; }), what: "profiles" };
      }],
      ["Hiring", function (row, data) {
        const jobs = fieldAll(data, "hiring.job_posting");
        const other = (data.bySection.hiring || []).filter(function (c) { return c.field !== "hiring.job_posting" && c.field !== "hiring.active_job_ads_nav"; });
        if (!jobs.length && !other.length) {
          const sec = (data.env.sections || {}).hiring;
          return sec ? { node: stateBadge(sec.state), text: "state:" + sec.state } : null;
        }
        const parts = [];
        if (jobs.length) parts.push(jobs.length + " job ad" + (jobs.length === 1 ? "" : "s"));
        other.forEach(function (c) { parts.push(c.field === "hiring.career_page" ? "Careers page" : c.field === "hiring.recruitment_portal" ? "Recruitment portal" : (c.label || humanise(c.field))); });
        return { text: parts.join(", "), ids: jobs.concat(other).slice(0, 12).map(function (c) { return c.id; }), what: "hiring" };
      }],
      ["Chief executive", people("leadership.ceo", "chief executive")],
      ["Board chair", people("leadership.board_chair", "board chair")],
      ["Auditor", people("leadership.auditor", "auditor")],
      ["Registered workplaces", function (row, data) {
        const n = fieldAll(data, "location.registered_workplace").length;
        return { node: h("span", null, String(n), " ", h("a", { class: "small", href: "#/c/" + encodeURIComponent(data.key) + "?s=workplaces" }, "see list")), text: String(n) };
      }],
      ["Latest activity", function (row, data) {
        const items = prefixed(data, "activity.").filter(function (c) { return claimDate(c); }).sort(function (a, b) { return String(claimDate(b)).localeCompare(String(claimDate(a))); });
        const c = items[0];
        return c ? { text: fmtDate(claimDate(c)) + " · " + (c.label || humanise(c.field)), ids: [c.id], what: "latest activity" } : null;
      }],
      ["Signals", function (row, data) {
        const sigs = ((data.env.synthesis || {}).signals || []).filter(function (s) { return s && s.signal; });
        if (!sigs.length) return { text: "None", node: h("span", { class: "muted" }, "None") };
        return { node: h("span", null, sigs.map(function (s) { return [badge(signalText(s.signal), SEVERITY_TONE[s.severity] || "neutral"), " "]; })), text: sigs.map(function (s) { return s.signal; }).join(","), ids: [].concat.apply([], sigs.map(function (s) { return s.claim_ids || []; })), what: "signals" };
      }],
      ["Data found", function (row, data) {
        const live = data.claims.filter(function (c) { return !c.stale; }).length;
        return { node: h("span", null, fmtNum(live) + " claims · " + fmtNum(data.evidence.size) + " evidence", h("br"), sectionsStrip(row.sections)), text: String(live) };
      }]
    ];
  }
  function renderCompare(keys) {
    const rows = [];
    keys.forEach(function (k) { const r = resolveRow(k); if (r && rows.indexOf(r) === -1 && rows.length < MAX_COMPARE) rows.push(r); });
    state.compare = rows.map(function (r) { return String(r.file); });
    saveCompare();
    syncCompareUi();
    const canonical = compareHref();
    if (location.hash !== canonical && rows.length) replaceHash(canonical);
    document.title = "Compare companies — Signalpost Anchor";
    clear(main);
    window.scrollTo(0, 0);
    add(main, h("div", { class: "crumbs" }, h("a", { href: listHash() }, "← All companies")));
    const head = h("div", { class: "page-head" }, h("h1", { tabindex: "-1" }, "Compare companies"),
      h("p", null, rows.length ? "Up to " + MAX_COMPARE + " companies side by side. Select Verify next to a value to see its source. — means not found (never zero). ≠ marks rows where the companies differ." : ""));
    add(main, head);
    main.querySelector("h1").focus({ preventScroll: true });
    if (!rows.length) {
      add(main, h("div", { class: "card empty" }, h("p", null, "No companies selected yet."), h("p", null, "Use “+ Compare” on the company list or on a profile to pick up to " + MAX_COMPARE + " companies."), h("a", { class: "btn primary", href: listHash() }, "Go to the company list")));
      return;
    }
    const holder = h("div", null, h("p", { class: "notice", role: "status" }, "Loading " + rows.length + " research file" + (rows.length === 1 ? "" : "s") + "…"));
    add(main, holder);
    const token = state.token;
    Promise.all(rows.map(function (r) { return loadCompany(r).then(function (d) { return { row: r, data: d }; }, function (err) { return { row: r, error: err }; }); })).then(function (results) {
      if (token !== state.token) return;
      clear(holder);
      const failed = results.filter(function (x) { return x.error; });
      failed.forEach(function (x) { add(holder, h("p", { class: "notice error", role: "alert" }, x.error.message)); });
      const ok = results.filter(function (x) { return x.data; });
      if (!ok.length) return;
      const thead = h("thead", null, h("tr", null, h("th", { scope: "col" }, "Company"), ok.map(function (x) {
        return h("th", { scope: "col" }, h("div", { class: "co-name" },
          h("a", { href: "#/c/" + encodeURIComponent(x.row.file) }, x.row._name),
          h("span", { class: "small muted mono" }, x.row.id ? fmtOrg(x.row.id) : inputText(x.row.input)),
          h("button", { type: "button", class: "btn small", "aria-label": "Remove " + x.row._name + " from compare", onclick: function () {
            const rest = state.compare.filter(function (k) { return k !== String(x.row.file); });
            state.compare = rest;
            saveCompare();
            location.hash = compareHref(rest);
          } }, "Remove")));
      })));
      const tbody = h("tbody");
      cmpDefs().forEach(function (def) {
        const cells = ok.map(function (x) { try { return def[1](x.row, x.data); } catch (e) { return null; } });
        const texts = cells.map(function (c) { return c ? norm(c.text) : ""; });
        const differs = ok.length > 1 && texts.some(function (t) { return t !== texts[0]; });
        add(tbody, h("tr", { class: differs ? "diff" : null }, h("th", { scope: "row" }, def[0], differs ? h("span", { class: "sr-only" }, " (differs)") : null), cells.map(function (c, i) {
          const x = ok[i];
          if (!c) return h("td", { "data-label": x.row._name }, dash());
          return h("td", { "data-label": x.row._name }, h("div", { class: "cell" }, h("span", { class: "v" + (c.neg ? " neg" : "") }, c.node || c.text),
            c.ids && c.ids.length ? verifyBtn(x.data, c.ids, { what: def[0] + " of " + x.row._name, title: c.title || (def[0] + " — " + x.row._name), note: c.note }) : null));
        })));
      });
      add(holder, h("ul", { class: "cmp-cards", "aria-label": "Companies in this comparison" }, ok.map(function (x) {
        return h("li", { class: "card" }, h("div", null, h("a", { href: "#/c/" + encodeURIComponent(x.row.file) }, x.row._name), h("div", { class: "small muted mono" }, x.row.id ? fmtOrg(x.row.id) : inputText(x.row.input))),
          h("button", { type: "button", class: "btn small", "aria-label": "Remove " + x.row._name + " from compare", onclick: function () {
            const rest = state.compare.filter(function (k) { return k !== String(x.row.file); });
            state.compare = rest;
            saveCompare();
            location.hash = compareHref(rest);
          } }, "Remove"));
      })));
      add(holder, h("div", { class: "table-wrap cmp-wrap" }, h("table", { class: "cmp" }, h("caption", null, "Comparison of " + ok.length + " compan" + (ok.length === 1 ? "y" : "ies") + ". Financial figures are the latest filed company accounts."), thead, tbody)));
      if (ok.length < MAX_COMPARE) add(holder, h("p", { class: "small muted" }, "You can add " + (MAX_COMPARE - ok.length) + " more from the ", h("a", { href: listHash() }, "company list"), "."));
    });
  }

  function renderFooter() {
    const f = document.getElementById("footer");
    const run = REPORT.run || {};
    const agent = REPORT.agent || {};
    add(clear(f), 
      h("p", null, (agent.name || "Signalpost Anchor") + (agent.version ? " " + agent.version : "") + " · run ", h("span", { class: "mono" }, run.run_id || "—"), " · completed " + fmtTime(run.completed_at) + " · page generated " + fmtTime(INDEX.generated_at)),
      h("p", null, "Public sources: Brønnøysundregistrene (Enhetsregisteret, Regnskapsregisteret; NLOD 2.0), NAV arbeidsplassen, GLEIF, Wikidata and company-owned websites. Every value opens its evidence: source URL, retrieval time, content SHA-256 and the quoted excerpt."));
  }

  let debounce = 0;
  qInput.addEventListener("input", function () {
    window.clearTimeout(debounce);
    debounce = window.setTimeout(function () {
      state.list.q = qInput.value;
      state.shown = PAGE;
      if (state.lastView !== "list") { location.hash = listHash(); return; }
      writeListHash();
      updateResults();
    }, 140);
  });
  document.getElementById("search-form").addEventListener("submit", function (e) {
    e.preventDefault();
    window.clearTimeout(debounce);
    state.list.q = qInput.value;
    const rows = filteredRows();
    if (rows.length === 1 && state.list.q) { location.hash = "#/c/" + encodeURIComponent(rows[0].file); return; }
    if (state.lastView !== "list") { location.hash = listHash(); return; }
    writeListHash();
    updateResults();
    const firstLink = listRefs && listRefs.list.querySelector("a");
    if (firstLink) firstLink.focus();
  });
  document.querySelector(".skip").addEventListener("click", function (e) {
    e.preventDefault();
    const target = main.querySelector("h1") || main;
    target.focus();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "/" || e.metaKey || e.ctrlKey || e.altKey) return;
    const t = e.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable)) return;
    if (dlg.open) return;
    e.preventDefault();
    qInput.focus();
    qInput.select();
  });
  window.addEventListener("hashchange", route);

  const boot = document.getElementById("boot");
  if (boot) boot.remove();
  if (!window.SP_INDEX) {
    add(main, h("p", { class: "notice error", role: "alert" }, "The research index (data/index.js) could not be loaded."));
    return;
  }
  state.compare = loadCompare();
  renderFooter();
  syncCompareUi();
  if (!location.hash || location.hash === "#") {
    if (!replaceHash("#/")) location.hash = "#/";
  }
  route();
})();
