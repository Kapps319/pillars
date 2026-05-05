/* =====================================================
   PILLARS — Personal dashboard
   State persists per-device via localStorage.
   Export/Import JSON for cross-device backup.
===================================================== */

const STORAGE_KEY = "pillars.state.v1";
function loadSavedState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch { return null; }
}
let _saveTimer = null;
function saveState() {
  // Debounce + double-write (localStorage + sessionStorage backup)
  clearTimeout(_saveTimer);
  _saveTimer = setTimeout(() => {
    try {
      const json = JSON.stringify(state);
      localStorage.setItem(STORAGE_KEY, json);
      try { sessionStorage.setItem(STORAGE_KEY, json); } catch {}
    } catch {}
  }, 80);
}
function saveStateNow() {
  // Synchronous save — used on pagehide/visibilitychange before iOS suspends.
  clearTimeout(_saveTimer);
  try {
    const json = JSON.stringify(state);
    localStorage.setItem(STORAGE_KEY, json);
    try { sessionStorage.setItem(STORAGE_KEY, json); } catch {}
  } catch {}
}

const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
const id = () => Math.random().toString(36).slice(2, 9);
const today = () => new Date().toISOString().slice(0, 10); // YYYY-MM-DD

// ---------- State (starts empty per user request — fresh slate from May 5) ----------
const _rawState = {
  startedOn: "2026-05-05",
  // I · To-Do
  tasks: [],
  taskFilter: "all",
  newTaskPrio: "red",
  // II · Sanctuary
  sanctuary: [],
  // III · Finances
  balance: 0,
  expenses: [], // {id, label, amount, date}
  // IV · Priorities
  priorities: [],
  prioFilter: "all",
  newPrioPrio: "red",
  // V · Wellness
  wellness: {
    waterToday: 0,
    waterDate: today(),
    supplements: [
      // {id, name, log: { 'YYYY-MM-DD': { am: bool, mid: bool, pm: bool } } }
    ],
    weekStart: weekStartISO(),
    meals: [], // {id, name, p, c, f, date}
  },
};

// Deep Proxy so any mutation — nested or shallow — triggers an auto-save.
function makeReactive(obj) {
  if (obj === null || typeof obj !== "object") return obj;
  for (const k of Object.keys(obj)) obj[k] = makeReactive(obj[k]);
  return new Proxy(obj, {
    set(target, prop, value) {
      target[prop] = makeReactive(value);
      saveState();
      return true;
    },
    deleteProperty(target, prop) {
      delete target[prop];
      saveState();
      return true;
    },
  });
}
const state = makeReactive(_rawState);

// ---------- Helpers ----------
function weekStartISO() {
  // Monday of current week
  const d = new Date();
  const dow = (d.getDay() + 6) % 7; // Mon=0
  d.setDate(d.getDate() - dow);
  d.setHours(0,0,0,0);
  return d.toISOString().slice(0,10);
}
function weekDates(startISO) {
  const out = [];
  const start = new Date(startISO + "T00:00:00");
  for (let i = 0; i < 7; i++) {
    const d = new Date(start);
    d.setDate(d.getDate() + i);
    out.push(d.toISOString().slice(0,10));
  }
  return out;
}
function dayLabel(iso) {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString(undefined, { weekday: "short" });
}
function dayNum(iso) {
  return new Date(iso + "T00:00:00").getDate();
}
function fmtMoney(n) {
  return Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("is-on");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.remove("is-on"), 1800);
}

// ---------- Clock & greeting ----------
function tickClock() {
  const d = new Date();
  $("#clock").textContent = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
}
function setGreeting() {
  const h = new Date().getHours();
  const part = h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
  const dateStr = new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "short" });
  $("#greeting").textContent = `${dateStr} · ${part}.`;
}

// ---------- I · TO-DO ----------
function renderTasks() {
  const ul = $("#task-list");
  const filter = state.taskFilter;
  const list = filter === "all" ? state.tasks : state.tasks.filter(t => t.prio === filter);
  ul.innerHTML = list.map(t => `
    <li class="task ${t.done ? "is-done" : ""}" data-prio="${t.prio}">
      <button class="check" data-task-toggle="${t.id}" aria-label="Toggle"></button>
      <span class="dot dot-${t.prio}"></span>
      <span class="task-text">${escapeHtml(t.text)}</span>
      <button class="row-del" data-task-del="${t.id}" aria-label="Delete">×</button>
    </li>
  `).join("");
  $("#task-empty").hidden = state.tasks.length > 0;
  // counts
  const open = state.tasks.filter(t => !t.done);
  $("#count-all").textContent = open.length;
  $("#count-red").textContent = open.filter(t => t.prio === "red").length;
  $("#count-yellow").textContent = open.filter(t => t.prio === "yellow").length;
  $("#count-green").textContent = open.filter(t => t.prio === "green").length;
}
function bindTodo() {
  $$('.tasks-card .seg-btn, [data-pillar="todo"] .seg-btn').forEach(b => {
    b.addEventListener("click", () => {
      $$('[data-pillar="todo"] .seg-btn').forEach(x => x.classList.remove("is-active"));
      b.classList.add("is-active");
      state.taskFilter = b.dataset.filter;
      renderTasks();
    });
  });
  $$('[data-pillar="todo"] .prio').forEach(b => {
    b.addEventListener("click", () => {
      $$('[data-pillar="todo"] .prio').forEach(x => { x.classList.remove("is-active"); x.setAttribute("aria-checked","false"); });
      b.classList.add("is-active"); b.setAttribute("aria-checked","true");
      state.newTaskPrio = b.dataset.prio;
    });
  });
  $("#task-form").addEventListener("submit", e => {
    e.preventDefault();
    const text = $("#task-text").value.trim();
    if (!text) return;
    state.tasks.unshift({ id: id(), text, prio: state.newTaskPrio, done: false });
    $("#task-text").value = "";
    renderTasks();
  });
  $("#task-list").addEventListener("click", e => {
    const tog = e.target.closest("[data-task-toggle]");
    const del = e.target.closest("[data-task-del]");
    if (tog) {
      const t = state.tasks.find(x => x.id === tog.dataset.taskToggle);
      if (t) { t.done = !t.done; renderTasks(); }
    } else if (del) {
      state.tasks = state.tasks.filter(x => x.id !== del.dataset.taskDel);
      renderTasks();
    }
  });
}

// ---------- II · SANCTUARY ----------
function renderSanc() {
  const ul = $("#sanc-list");
  ul.innerHTML = state.sanctuary.map(s => `
    <li class="sanc-item ${s.done ? "is-done" : ""}">
      <button class="check" data-sanc-toggle="${s.id}" aria-label="Toggle"></button>
      <span class="task-text">${escapeHtml(s.text)}</span>
      <button class="row-del" data-sanc-del="${s.id}" aria-label="Delete">×</button>
    </li>
  `).join("");
  $("#sanc-empty").hidden = state.sanctuary.length > 0;
}
function bindSanc() {
  $("#sanc-form").addEventListener("submit", e => {
    e.preventDefault();
    const text = $("#sanc-text").value.trim();
    if (!text) return;
    state.sanctuary.unshift({ id: id(), text, done: false });
    $("#sanc-text").value = "";
    renderSanc();
  });
  $("#sanc-list").addEventListener("click", e => {
    const tog = e.target.closest("[data-sanc-toggle]");
    const del = e.target.closest("[data-sanc-del]");
    if (tog) {
      const s = state.sanctuary.find(x => x.id === tog.dataset.sancToggle);
      if (s) { s.done = !s.done; renderSanc(); }
    } else if (del) {
      state.sanctuary = state.sanctuary.filter(x => x.id !== del.dataset.sancDel);
      renderSanc();
    }
  });
  $("#sanc-reset").addEventListener("click", () => {
    if (state.sanctuary.length && confirm("Clear all sanctuary items?")) {
      state.sanctuary = [];
      renderSanc();
    }
  });
}

// ---------- III · FINANCES ----------
function renderFinances() {
  $("#balance-amount").textContent = fmtMoney(state.balance);
  // expenses since startedOn
  const since = state.startedOn;
  const rel = state.expenses.filter(e => e.date >= since);
  const total = rel.reduce((s, e) => s + Number(e.amount), 0);
  $("#spent-total").textContent = "AED " + fmtMoney(total);
  const ul = $("#tx-list");
  ul.innerHTML = rel.slice(0, 12).map(e => `
    <li class="tx">
      <div class="tx-meta">
        <p class="tx-label">${escapeHtml(e.label)}</p>
        <p class="muted small mono">${prettyDate(e.date)}</p>
      </div>
      <span class="tx-amount neg mono">− AED ${fmtMoney(e.amount)}</span>
      <button class="row-del" data-tx-del="${e.id}" aria-label="Delete">×</button>
    </li>
  `).join("");
  $("#tx-empty").hidden = rel.length > 0;
}
function prettyDate(iso) {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}
function bindFinances() {
  $("#edit-balance").addEventListener("click", () => {
    openModal({
      title: "Edit balance",
      fields: [{ name: "balance", label: "Current balance (AED)", type: "number", value: state.balance, step: "0.01" }],
      onSave: v => { state.balance = Number(v.balance) || 0; renderFinances(); }
    });
  });
  $("#add-tx").addEventListener("click", () => {
    openModal({
      title: "Log expense",
      fields: [
        { name: "label", label: "What was it?", type: "text", required: true },
        { name: "amount", label: "Amount (AED)", type: "number", step: "0.01", required: true },
        { name: "date", label: "Date", type: "date", value: today() }
      ],
      onSave: v => {
        if (!v.label || !v.amount) return;
        state.expenses.unshift({ id: id(), label: v.label, amount: Number(v.amount), date: v.date || today() });
        state.expenses.sort((a,b) => b.date.localeCompare(a.date));
        renderFinances();
        toast("Expense logged");
      }
    });
  });
  $("#tx-list").addEventListener("click", e => {
    const del = e.target.closest("[data-tx-del]");
    if (del) {
      state.expenses = state.expenses.filter(x => x.id !== del.dataset.txDel);
      renderFinances();
    }
  });
}

// ---------- IV · PRIORITIES ----------
function renderPrios() {
  const ul = $("#prio-list");
  const filter = state.prioFilter;
  const list = filter === "all" ? state.priorities : state.priorities.filter(t => t.prio === filter);
  ul.innerHTML = list.map(t => `
    <li class="task ${t.done ? "is-done" : ""}" data-prio="${t.prio}">
      <button class="check" data-prio-toggle="${t.id}" aria-label="Toggle"></button>
      <span class="dot dot-${t.prio}"></span>
      <span class="task-text">${escapeHtml(t.text)}</span>
      <button class="row-del" data-prio-del="${t.id}" aria-label="Delete">×</button>
    </li>
  `).join("");
  $("#prio-empty").hidden = state.priorities.length > 0;
  const open = state.priorities.filter(t => !t.done);
  $("#pcount-all").textContent = open.length;
  $("#pcount-red").textContent = open.filter(t => t.prio === "red").length;
  $("#pcount-yellow").textContent = open.filter(t => t.prio === "yellow").length;
  $("#pcount-green").textContent = open.filter(t => t.prio === "green").length;
}
function bindPrios() {
  $$('[data-pillar="priorities"] .seg-btn').forEach(b => {
    b.addEventListener("click", () => {
      $$('[data-pillar="priorities"] .seg-btn').forEach(x => x.classList.remove("is-active"));
      b.classList.add("is-active");
      state.prioFilter = b.dataset.pfilter;
      renderPrios();
    });
  });
  $$('[data-pillar="priorities"] .prio').forEach(b => {
    b.addEventListener("click", () => {
      $$('[data-pillar="priorities"] .prio').forEach(x => { x.classList.remove("is-active"); x.setAttribute("aria-checked","false"); });
      b.classList.add("is-active"); b.setAttribute("aria-checked","true");
      state.newPrioPrio = b.dataset.pprio;
    });
  });
  $("#prio-form").addEventListener("submit", e => {
    e.preventDefault();
    const text = $("#prio-text").value.trim();
    if (!text) return;
    state.priorities.unshift({ id: id(), text, prio: state.newPrioPrio, done: false });
    $("#prio-text").value = "";
    renderPrios();
  });
  $("#prio-list").addEventListener("click", e => {
    const tog = e.target.closest("[data-prio-toggle]");
    const del = e.target.closest("[data-prio-del]");
    if (tog) {
      const t = state.priorities.find(x => x.id === tog.dataset.prioToggle);
      if (t) { t.done = !t.done; renderPrios(); }
    } else if (del) {
      state.priorities = state.priorities.filter(x => x.id !== del.dataset.prioDel);
      renderPrios();
    }
  });
}

// ---------- V · WELLNESS ----------
function renderHydration() {
  // reset cups if date changed
  if (state.wellness.waterDate !== today()) {
    state.wellness.waterDate = today();
    state.wellness.waterToday = 0;
  }
  const wrap = $("#cups");
  let html = "";
  for (let i = 0; i < 8; i++) {
    html += `<button class="cup ${i < state.wellness.waterToday ? "is-on" : ""}" data-cup="${i}" aria-label="Cup ${i+1}"></button>`;
  }
  wrap.innerHTML = html;
  $("#water-count").textContent = state.wellness.waterToday;
}
function bindHydration() {
  $("#cups").addEventListener("click", e => {
    const btn = e.target.closest(".cup");
    if (!btn) return;
    const i = Number(btn.dataset.cup);
    // toggle: if cup is on and it's the last on, decrement. Else fill up to i+1.
    if (i + 1 === state.wellness.waterToday) {
      state.wellness.waterToday = i;
    } else {
      state.wellness.waterToday = i + 1;
    }
    renderHydration();
  });
}

function renderSupps() {
  // build header for week
  const weekStart = state.wellness.weekStart;
  const days = weekDates(weekStart);
  const thead = $("#supp-table thead tr");
  thead.innerHTML = `<th class="supp-name-col">Supplement</th>` + days.map(d => {
    return `<th class="day-col" colspan="3"><span class="day-name">${dayLabel(d)}</span><span class="day-num mono">${dayNum(d)}</span></th>`;
  }).join("");
  // body rows
  const tbody = $("#supp-tbody");
  if (!state.wellness.supplements.length) {
    tbody.innerHTML = `<tr><td colspan="${1 + 7*3}" class="empty-cell">No supplements yet. Tap "+ Add supplement".</td></tr>`;
    return;
  }
  tbody.innerHTML = state.wellness.supplements.map(s => {
    const cells = days.map(d => {
      const log = (s.log || {})[d] || { am:false, mid:false, pm:false };
      return ["am","mid","pm"].map(slot => `
        <td class="slot-cell"><button class="slot ${log[slot] ? "is-on" : ""}" data-supp="${s.id}" data-date="${d}" data-slot="${slot}" aria-label="${slot} ${d}"></button></td>
      `).join("");
    }).join("");
    return `<tr>
      <td class="supp-name">
        <span>${escapeHtml(s.name)}</span>
        <button class="row-del" data-supp-del="${s.id}" aria-label="Delete">×</button>
      </td>
      ${cells}
    </tr>`;
  }).join("");
}
function bindSupps() {
  $("#add-supp").addEventListener("click", () => {
    openModal({
      title: "Add supplement",
      fields: [{ name: "name", label: "Supplement name", type: "text", required: true, placeholder: "e.g. Creatine 5g" }],
      onSave: v => {
        if (!v.name) return;
        state.wellness.supplements.push({ id: id(), name: v.name, log: {} });
        renderSupps();
      }
    });
  });
  $("#supp-tbody").addEventListener("click", e => {
    const slot = e.target.closest(".slot");
    const del = e.target.closest("[data-supp-del]");
    if (slot) {
      const s = state.wellness.supplements.find(x => x.id === slot.dataset.supp);
      if (!s) return;
      s.log = s.log || {};
      s.log[slot.dataset.date] = s.log[slot.dataset.date] || { am:false, mid:false, pm:false };
      const k = slot.dataset.slot;
      s.log[slot.dataset.date][k] = !s.log[slot.dataset.date][k];
      slot.classList.toggle("is-on");
    } else if (del) {
      if (!confirm("Remove this supplement and all its logs?")) return;
      state.wellness.supplements = state.wellness.supplements.filter(x => x.id !== del.dataset.suppDel);
      renderSupps();
    }
  });
  $("#wellness-reset").addEventListener("click", () => {
    if (!confirm("Start a new week? Supplement check marks and meals reset; supplements list and balance stay.")) return;
    state.wellness.weekStart = weekStartISO();
    state.wellness.supplements.forEach(s => s.log = {});
    state.wellness.meals = [];
    state.wellness.waterToday = 0;
    renderSupps();
    renderMeals();
    renderHydration();
    toast("Fresh week");
  });
}

function renderMeals() {
  const meals = state.wellness.meals.filter(m => m.date === today());
  const tot = meals.reduce((a, m) => ({ p: a.p + (+m.p||0), c: a.c + (+m.c||0), f: a.f + (+m.f||0) }), { p:0, c:0, f:0 });
  $("#tot-p").textContent = tot.p;
  $("#tot-c").textContent = tot.c;
  $("#tot-f").textContent = tot.f;
  $("#tot-k").textContent = tot.p*4 + tot.c*4 + tot.f*9;
  const ul = $("#meal-list");
  ul.innerHTML = meals.map(m => `
    <li class="meal">
      <span class="meal-name">${escapeHtml(m.name)}</span>
      <span class="mono small muted">${m.p}P · ${m.c}C · ${m.f}F</span>
      <button class="row-del" data-meal-del="${m.id}" aria-label="Delete">×</button>
    </li>
  `).join("");
  $("#meal-empty").hidden = meals.length > 0;
}
function bindMeals() {
  $("#add-meal").addEventListener("click", () => {
    openModal({
      title: "Log meal or snack",
      fields: [
        { name: "name", label: "What did you eat?", type: "text", required: true },
        { name: "p", label: "Protein (g)", type: "number", min: "0", value: "0" },
        { name: "c", label: "Carbs (g)",   type: "number", min: "0", value: "0" },
        { name: "f", label: "Fat (g)",     type: "number", min: "0", value: "0" },
      ],
      onSave: v => {
        if (!v.name) return;
        state.wellness.meals.unshift({
          id: id(), name: v.name,
          p: Number(v.p)||0, c: Number(v.c)||0, f: Number(v.f)||0,
          date: today()
        });
        renderMeals();
        toast("Meal logged");
      }
    });
  });
  $("#meal-list").addEventListener("click", e => {
    const del = e.target.closest("[data-meal-del]");
    if (del) {
      state.wellness.meals = state.wellness.meals.filter(x => x.id !== del.dataset.mealDel);
      renderMeals();
    }
  });
}

// ---------- Modal ----------
function openModal({ title, fields, onSave }) {
  const dlg = $("#modal");
  $("#modal-title").textContent = title;
  $("#modal-body").innerHTML = fields.map(f => `
    <label class="field">
      <span>${f.label}</span>
      <input name="${f.name}" type="${f.type}"
        ${f.required ? "required" : ""}
        ${f.step ? `step="${f.step}"` : ""}
        ${f.min !== undefined ? `min="${f.min}"` : ""}
        ${f.placeholder ? `placeholder="${f.placeholder}"` : ""}
        value="${f.value !== undefined ? f.value : ""}" />
    </label>
  `).join("");
  dlg.showModal();
  const form = $("#modal-form");
  const onCancel = () => dlg.close("cancel");
  $("#modal-cancel").onclick = onCancel;
  form.onsubmit = e => {
    e.preventDefault();
    const fd = new FormData(form);
    const v = {};
    fields.forEach(f => v[f.name] = fd.get(f.name));
    onSave(v);
    dlg.close("save");
  };
}

// ---------- Theme ----------
function bindTheme() {
  const btn = $('[data-theme-toggle]');
  const apply = () => {
    const t = document.documentElement.dataset.theme;
    btn.innerHTML = t === "dark"
      ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>`
      : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;
  };
  apply();
  btn.addEventListener("click", () => {
    document.documentElement.dataset.theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    apply();
  });
}

// ---------- Export / Import ----------
function bindExportImport() {
  $("#export-btn").addEventListener("click", () => {
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `pillars-${today()}.json`;
    document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 100);
    toast("Exported");
  });
  $("#import-input").addEventListener("change", async e => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      const text = await file.text();
      const obj = JSON.parse(text);
      Object.assign(state, obj);
      renderAll();
      toast("Imported");
    } catch (err) {
      toast("Import failed");
    }
    e.target.value = "";
  });
}

// ---------- Util ----------
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c]));
}

// ---------- Render all ----------
function renderAll() {
  renderTasks();
  renderSanc();
  renderFinances();
  renderPrios();
  renderHydration();
  renderSupps();
  renderMeals();
  saveState();
}

// ---------- Install hint ----------
function bindInstallCard() {
  const card = $("#install-card");
  if (!card) return;
  // Hide if running as installed PWA (standalone)
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches
    || window.navigator.standalone === true;
  if (isStandalone) return;
  // Show on iPad / iPhone Safari, or any non-standalone browser
  card.hidden = false;
  $("#install-close").addEventListener("click", () => { card.hidden = true; });
}

// ---------- Init ----------
function initApp() {
  // Hydrate state from localStorage (or sessionStorage backup) if available
  let saved = loadSavedState();
  if (!saved) {
    try { const raw = sessionStorage.getItem(STORAGE_KEY); if (raw) saved = JSON.parse(raw); } catch {}
  }
  if (saved && typeof saved === "object") {
    // Assign through the Proxy so each value gets re-wrapped reactive
    for (const k of Object.keys(saved)) state[k] = saved[k];
    if (!state.wellness) state.wellness = { waterToday: 0, waterDate: today(), supplements: [], weekStart: weekStartISO(), meals: [] };
  }

  // Save aggressively when iOS may suspend the app
  window.addEventListener("pagehide", saveStateNow);
  window.addEventListener("beforeunload", saveStateNow);
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") saveStateNow(); });
  bindInstallCard();
  setGreeting();
  tickClock();
  setInterval(tickClock, 30 * 1000);
  bindTodo();
  bindSanc();
  bindFinances();
  bindPrios();
  bindHydration();
  bindSupps();
  bindMeals();
  bindTheme();
  bindExportImport();
  renderAll();
}

// ---------- Lock screen ----------
// Passcode hash (SHA-256). Compare hashes, never store plaintext.
// In-memory unlock flag — re-prompts on every page reload (more secure).
const PASSCODE_HASH = "e9ab39f01d431c5250493a3dc493bba9c43f73a4461c72b5135ee09738582af7";

async function sha256Hex(str) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join("");
}

function setupLockScreen() {
  const screen = document.getElementById("lock-screen");
  const dots = document.getElementById("lock-dots");
  const pad = document.getElementById("lock-pad");
  const msg = document.getElementById("lock-msg");
  let entry = "";
  let busy = false;

  const renderDots = () => {
    [...dots.children].forEach((d, i) => d.classList.toggle("is-on", i < entry.length));
  };

  const fail = () => {
    screen.classList.add("is-shake");
    msg.textContent = "Incorrect passcode";
    msg.classList.add("is-error");
    setTimeout(() => {
      screen.classList.remove("is-shake");
      entry = "";
      renderDots();
    }, 380);
  };

  const succeed = () => {
    screen.style.transition = "opacity 280ms ease";
    screen.style.opacity = "0";
    setTimeout(() => {
      screen.hidden = true;
      document.body.classList.remove("is-locked");
      initApp();
    }, 280);
  };

  const tryUnlock = async () => {
    if (busy) return;
    busy = true;
    msg.textContent = "";
    msg.classList.remove("is-error");
    const h = await sha256Hex(entry);
    if (h === PASSCODE_HASH) succeed();
    else fail();
    busy = false;
  };

  const press = (key) => {
    if (key === "del") {
      entry = entry.slice(0, -1);
      msg.textContent = "";
      msg.classList.remove("is-error");
      renderDots();
      return;
    }
    if (entry.length >= 4) return;
    entry += key;
    renderDots();
    if (entry.length === 4) setTimeout(tryUnlock, 120);
  };

  pad.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-key]");
    if (!btn) return;
    press(btn.dataset.key);
  });

  // Physical keyboard support
  document.addEventListener("keydown", (e) => {
    if (screen.hidden) return;
    if (/^[0-9]$/.test(e.key)) press(e.key);
    else if (e.key === "Backspace") press("del");
  });
}

document.body.classList.add("is-locked");
setupLockScreen();
