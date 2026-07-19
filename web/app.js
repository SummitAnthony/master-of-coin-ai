"use strict";

// Self-contained dashboard for the Master of Coin AI financial advisor.
// Zero dependencies: interactions and charts are drawn directly in the app.

const state = { sessionId: null, latestDashboard: null, currency: "USD", theme: localStorage.getItem("moc-theme") || "light" };

const $ = (sel) => document.querySelector(sel);

async function api(path, options) {
  const resp = await fetch(path, options);
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      detail = (await resp.json()).detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return resp.json();
}

function setStatus(text) {
  $("#status-pill").textContent = text;
}

function icon(name) {
  return `<svg><use href="#${name}"></use></svg>`;
}

function fmtMoney(value) {
  if (value === null || value === undefined) return "n/a";
  const n = Math.round(Number(value));
  const s = Math.abs(n).toLocaleString("en-US");
  return (n < 0 ? "(" + state.currency + " " + s + ")" : state.currency + " " + s);
}

function fmtPct(value) {
  if (value === null || value === undefined) return "n/a";
  return Number(value).toFixed(2) + "%";
}

const chartTheme = {
  light: {
    surface: "rgba(255,255,255,0.18)",
    grid: "rgba(28,28,30,0.08)",
    text: "#6E6E73",
    series: ["#6D5EF7", "#17C964", "#FF5C5C"],
    fill: "rgba(109,94,247,0.18)",
  },
  dark: {
    surface: "rgba(255,255,255,0.02)",
    grid: "rgba(255,255,255,0.08)",
    text: "#A2A6B3",
    series: ["#8B7CFF", "#4ADE80", "#FB7185"],
    fill: "rgba(139,124,255,0.2)",
  },
};

function currentChartTheme() {
  return chartTheme[state.theme] || chartTheme.light;
}

// --- minimal canvas charts ------------------------------------------------
function clearCanvas(ctx, w, h) {
  const theme = currentChartTheme();
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = theme.surface;
  ctx.fillRect(0, 0, w, h);
}

function axes(ctx, pad, w, h) {
  const theme = currentChartTheme();
  ctx.strokeStyle = theme.grid;
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let i = 1; i < 4; i += 1) {
    const y = pad + ((h - pad * 2) / 4) * i;
    ctx.moveTo(pad, y);
    ctx.lineTo(w - pad, y);
  }
  ctx.stroke();
}

function drawLineChart(canvas, labels, datasets) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height, pad = 40;
  clearCanvas(ctx, w, h);
  axes(ctx, pad, w, h);
  const all = datasets.flatMap((d) => d.data).filter((v) => v !== null && v !== undefined).map(Number);
  if (!all.length) return;
  const max = Math.max(...all, 0), min = Math.min(...all, 0);
  const span = max - min || 1;
  const theme = currentChartTheme();
  const colors = theme.series;
  const x = (i) => pad + (labels.length === 1 ? (w - 2 * pad) / 2 : (i * (w - 2 * pad)) / (labels.length - 1));
  const y = (v) => h - pad - ((Number(v) - min) / span) * (h - 2 * pad);
  datasets.forEach((ds, di) => {
    ctx.strokeStyle = colors[di % colors.length];
    ctx.lineWidth = 2.25;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    let started = false;
    const points = [];
    ds.data.forEach((v, i) => {
      if (v === null || v === undefined) return;
      const px = x(i), py = y(v);
      points.push([px, py]);
      if (!started) { ctx.moveTo(px, py); started = true; } else ctx.lineTo(px, py);
    });
    ctx.stroke();
    if (di === 0 && points.length > 1) {
      const gradient = ctx.createLinearGradient(0, pad, 0, h - pad);
      gradient.addColorStop(0, theme.fill);
      gradient.addColorStop(1, "rgba(109,94,247,0)");
      ctx.lineTo(points[points.length - 1][0], h - pad);
      ctx.lineTo(points[0][0], h - pad);
      ctx.closePath();
      ctx.fillStyle = gradient;
      ctx.fill();
    }
    points.forEach(([px, py]) => {
      ctx.fillStyle = colors[di % colors.length];
      ctx.beginPath();
      ctx.arc(px, py, 3, 0, Math.PI * 2);
      ctx.fill();
    });
  });
  ctx.fillStyle = theme.text;
  ctx.font = "12px SF Pro Display, Segoe UI";
  labels.forEach((lab, i) => ctx.fillText(lab, x(i) - 18, h - pad + 14));
  datasets.forEach((ds, di) => {
    ctx.fillStyle = colors[di % colors.length];
    ctx.fillText(ds.label, pad + 6, pad + 12 + di * 14);
  });
}

function drawBarChart(canvas, labels, data) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height, pad = 40;
  clearCanvas(ctx, w, h);
  axes(ctx, pad, w, h);
  const vals = data.map(Number);
  const max = Math.max(...vals, 0) || 1;
  const theme = currentChartTheme();
  const bw = (w - 2 * pad) / (labels.length * 1.6);
  vals.forEach((v, i) => {
    const bh = (v / max) * (h - 2 * pad);
    const bx = pad + 10 + i * (bw * 1.6);
    const gradient = ctx.createLinearGradient(0, h - pad - bh, 0, h - pad);
    gradient.addColorStop(0, theme.series[0]);
    gradient.addColorStop(1, "rgba(109,94,247,0.08)");
    ctx.fillStyle = gradient;
    roundRect(ctx, bx, h - pad - bh, bw, bh, 8);
    ctx.fill();
    ctx.fillStyle = theme.text;
    ctx.font = "12px SF Pro Display, Segoe UI";
    ctx.fillText(labels[i], bx, h - pad + 14);
  });
}

function roundRect(ctx, x, y, width, height, radius) {
  const r = Math.min(radius, width / 2, height / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + width, y, x + width, y + height, r);
  ctx.arcTo(x + width, y + height, x, y + height, r);
  ctx.arcTo(x, y + height, x, y, r);
  ctx.arcTo(x, y, x + width, y, r);
  ctx.closePath();
}

function drawDemoCharts() {
  drawLineChart($("#margin-chart"), ["FY20", "FY21", "FY22", "FY23", "FY24"], [
    { label: "Revenue", data: [492, 641, 762, 718, 894] },
    { label: "Net Profit", data: [112, 218, 276, 168, 236] },
  ]);
  drawBarChart($("#revenue-chart"), ["FY20", "FY21", "FY22", "FY23", "FY24"], [492, 641, 762, 718, 894]);
}

function drawTenYearCharts() {
  const labels = ["FY15", "FY16", "FY17", "FY18", "FY19", "FY20", "FY21", "FY22", "FY23", "FY24"];
  drawLineChart($("#margin-chart"), labels, [
    { label: "Revenue", data: [288, 316, 362, 418, 455, 492, 641, 762, 718, 894] },
    { label: "Net Profit", data: [54, 68, 82, 96, 104, 112, 218, 276, 168, 236] },
  ]);
  drawBarChart($("#revenue-chart"), labels, [288, 316, 362, 418, 455, 492, 641, 762, 718, 894]);
}

function animateNumber(el) {
  const target = Number(el.dataset.count);
  if (!Number.isFinite(target)) return;
  const text = el.textContent;
  const prefix = text.includes("৳") ? "৳" : "";
  const suffix = text.includes("%") ? "%" : text.includes("x") ? "x" : text.includes("M") ? "M" : "";
  const decimals = text.includes(".") ? text.split(".")[1].replace(/[^0-9].*$/, "").length : 0;
  const start = performance.now();
  const duration = 900;
  function tick(now) {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const value = target * eased;
    el.textContent = `${prefix}${value.toFixed(decimals)}${suffix}`;
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

function toggleTheme() {
  state.theme = state.theme === "dark" ? "light" : "dark";
  document.body.dataset.theme = state.theme;
  localStorage.setItem("moc-theme", state.theme);
  if (state.latestDashboard) {
    renderDashboard(state.latestDashboard);
  } else {
    drawDemoCharts();
  }
}

function openCommandPalette() {
  const palette = $("#command-palette");
  palette.classList.add("open");
  palette.setAttribute("aria-hidden", "false");
  $("#palette-input").focus();
}

function closeCommandPalette() {
  const palette = $("#command-palette");
  palette.classList.remove("open");
  palette.setAttribute("aria-hidden", "true");
}

function scrollToTarget(target) {
  const targetEl = target ? document.querySelector(target) : null;
  if (targetEl) {
    window.requestAnimationFrame(() => targetEl.scrollIntoView({ behavior: "smooth", block: "start" }));
  } else {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

function setProductView(viewName, target = null, activeHref = null) {
  document.querySelectorAll("[data-product-view]").forEach((view) => {
    const isActive = view.dataset.productView === viewName;
    view.hidden = !isActive;
    view.classList.toggle("active", isActive);
  });
  document.querySelectorAll(".rail-nav a[data-view]").forEach((link) => {
    const targetHref = activeHref || (viewName === "dashboard" ? "#dashboard-view" : `#${viewName}-view`);
    link.classList.toggle("active", link.getAttribute("href") === targetHref);
  });
  closeCommandPalette();
  scrollToTarget(target || (viewName === "dashboard" ? "#dashboard-view" : `#${viewName}-view`));
}

function activateNavigation(trigger) {
  const view = trigger.dataset.view;
  if (!view) return;
  const href = trigger.getAttribute("href");
  const target = trigger.dataset.target || href || `#${view}-view`;
  setProductView(view, target, href || target);
}

function setChartRange(button) {
  const range = button.dataset.chartRange || "5Y";
  button.closest(".segmented-control")?.querySelectorAll("button").forEach((item) => {
    item.classList.toggle("active", item === button);
  });
  if (range === "10Y") {
    drawTenYearCharts();
  } else if (state.latestDashboard) {
    renderDashboard(state.latestDashboard);
  } else {
    drawDemoCharts();
  }
  setStatus(`${range} chart range selected`);
}

function advisorFields() {
  return Array.from($("#advisor-modal").querySelectorAll("input, textarea, select"));
}

function openAdvisorModal(source = null) {
  const modal = $("#advisor-modal");
  const card = source && typeof source.closest === "function" ? source.closest(".advisor-card") : null;
  if (card) {
    const fields = advisorFields();
    const tags = Array.from(card.querySelectorAll(".knowledge-tags span")).map((tag) => tag.textContent).join(", ");
    fields[0].value = card.querySelector("h2")?.textContent || "Custom Advisor";
    fields[1].value = card.querySelector("p")?.textContent || "Committee Advisor";
    fields[2].value = "Executive Committee";
    fields[7].value = advisorInitials(fields[0].value);
    fields[8].value = card.querySelector(".advisor-description")?.textContent || fields[8].value;
    fields[9].value = tags || fields[9].value;
    fields[10].value = `Strengthen ${fields[0].value} recommendations for board decisions.`;
  }
  modal.classList.add("open");
  modal.setAttribute("aria-hidden", "false");
}

function closeAdvisorModal() {
  const modal = $("#advisor-modal");
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
}

function runCommitteeAnalysis() {
  setProductView("committee");
  const timeline = $("#discussion-timeline");
  timeline.classList.remove("is-running");
  void timeline.offsetWidth;
  timeline.classList.add("is-running");
  document.querySelector(".consensus-meter").style.setProperty("--consensus", "92");
}

function setCommitteePreset(button) {
  document.querySelectorAll("[data-committee-preset]").forEach((item) => {
    item.classList.toggle("active", item === button);
  });
  setStatus(`${button.dataset.committeePreset} selected`);
}

function setAdvisorMode(button) {
  document.querySelectorAll("[data-advisor-mode]").forEach((item) => {
    item.classList.toggle("active", item === button);
  });
  setStatus(button.dataset.advisorMode === "custom" ? "Custom advisor mode selected" : "Built-in advisor mode selected");
}

function openConfigureAdvisor(button) {
  const card = button.closest(".advisor-card");
  openAdvisorModal(card);
  const name = card?.querySelector("h2")?.textContent || "Advisor";
  setStatus(`Configuring ${name}`);
}

function editCommittee() {
  setProductView("committee", ".advisor-grid", "#committee-view");
  setStatus("Drag advisors to reorder, use the cross to remove, or add a specialist.");
}

function advisorInitials(name) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("") || "AI";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function advisorCardTemplate(advisor) {
  const tags = (advisor.tags || ["Custom", "Committee", "Analysis"]).map((tag) => `<span>${escapeHtml(tag)}</span>`).join("");
  const initials = advisor.initials || advisorInitials(advisor.name);
  return `
    <button class="advisor-remove-icon" type="button" data-remove-advisor aria-label="Remove ${escapeHtml(advisor.name)}"><svg><use href="#icon-x"></use></svg></button>
    <div class="advisor-topline"><span class="advisor-avatar">${escapeHtml(initials)}</span><span class="status-dot online"></span></div>
    <h2>${escapeHtml(advisor.name)}</h2>
    <p>${escapeHtml(advisor.role)}</p>
    <div class="advisor-description">${escapeHtml(advisor.description)}</div>
    <div class="knowledge-tags">${tags}</div>
    <div class="advisor-meta"><span>Confidence</span><strong>${escapeHtml(advisor.confidence || "87%")}</strong></div>
    <div class="advisor-actions"><button type="button" data-configure-advisor>Configure</button><button type="button" data-duplicate-advisor>Duplicate</button></div>
  `;
}

function addAdvisorToCommittee(advisor) {
  const grid = document.querySelector(".advisor-grid");
  const addCard = grid.querySelector(".add-card");
  const card = document.createElement("article");
  card.className = "advisor-card";
  card.draggable = true;
  card.innerHTML = advisorCardTemplate(advisor);
  grid.insertBefore(card, addCard);
  wireAdvisorReorder();
  updateCommitteeSummary();
  setStatus(`${advisor.name} added to committee`);
  return card;
}

function removeCommitteeAdvisor(button) {
  const card = button.closest(".advisor-card");
  if (!card) return;
  const name = card.querySelector("h2")?.textContent || "Advisor";
  card.classList.add("removing");
  window.setTimeout(() => {
    card.remove();
    const firstAdvisor = document.querySelector(".advisor-card[draggable='true']");
    document.querySelectorAll(".advisor-card").forEach((item) => item.classList.remove("chair"));
    firstAdvisor?.classList.add("chair");
    updateCommitteeSummary();
    setStatus(`${name} removed from committee`);
  }, 160);
}

function duplicateCommitteeAdvisor(button) {
  const card = button.closest(".advisor-card");
  if (!card) return;
  const tags = Array.from(card.querySelectorAll(".knowledge-tags span")).map((tag) => tag.textContent);
  addAdvisorToCommittee({
    name: `${card.querySelector("h2")?.textContent || "Advisor"} Copy`,
    role: card.querySelector("p")?.textContent || "Committee Advisor",
    description: card.querySelector(".advisor-description")?.textContent || "Custom advisor copied from committee.",
    tags,
    confidence: card.querySelector(".advisor-meta strong")?.textContent || "87%",
  });
}

function updateCommitteeSummary() {
  const cards = Array.from(document.querySelectorAll(".advisor-grid .advisor-card[draggable='true']"));
  const count = cards.length;
  const label = `${count} Advisor${count === 1 ? "" : "s"} Active`;
  document.querySelectorAll("[data-committee-count]").forEach((node) => { node.textContent = label; });
  document.querySelectorAll("[data-committee-count-compact]").forEach((node) => { node.textContent = String(count); });

  const avatars = document.querySelector(".committee-avatars");
  if (!avatars) return;
  avatars.innerHTML = cards.slice(0, 5).map((card) => {
    const name = card.querySelector("h2")?.textContent || "Advisor";
    return `<span data-role="${escapeHtml(name)}">${escapeHtml(advisorInitials(name))}</span>`;
  }).join("") + `<button id="quick-add-advisor" class="avatar-add" type="button" aria-label="Add advisor">+</button>`;
}

function installMarketplaceAdvisor(button) {
  const card = button.closest(".marketplace-card");
  const advisor = card?.dataset.advisor || "Advisor";
  const tags = Array.from(card.querySelectorAll(".knowledge-tags span")).map((tag) => tag.textContent);
  addAdvisorToCommittee({
    name: advisor,
    role: "Marketplace Specialist",
    description: card.querySelector("p")?.textContent || "Specialist advisor installed from the marketplace.",
    tags,
    confidence: "86%",
  });
  button.textContent = "Installed";
  button.disabled = true;
}

function wireAdvisorReorder() {
  let dragged = null;
  document.querySelectorAll(".advisor-card[draggable='true']").forEach((card) => {
    if (card.dataset.reorderWired === "true") return;
    card.dataset.reorderWired = "true";
    card.addEventListener("dragstart", () => {
      dragged = card;
      card.classList.add("dragging");
    });
    card.addEventListener("dragend", () => {
      card.classList.remove("dragging");
      dragged = null;
    });
    card.addEventListener("dragover", (event) => event.preventDefault());
    card.addEventListener("drop", () => {
      if (!dragged || dragged === card) return;
      card.parentNode.insertBefore(dragged, card);
      document.querySelectorAll(".advisor-card").forEach((item) => item.classList.remove("chair"));
      document.querySelector(".advisor-card[draggable='true']")?.classList.add("chair");
      updateCommitteeSummary();
    });
  });
}

// --- rendering ------------------------------------------------------------
function renderDashboard(dash) {
  state.latestDashboard = dash;
  if (dash.entity && dash.entity.currency) state.currency = dash.entity.currency;
  if (dash.entity && dash.entity.company_name) {
    const greeting = $("#greeting");
    if (greeting) greeting.textContent = "Welcome, " + dash.entity.company_name;
  }
  $("#period-label").textContent = "— " + dash.latest_period;
  const grid = $("#scorecard-grid");
  grid.innerHTML = "";
  dash.scorecard.forEach((s) => {
    const div = document.createElement("div");
    div.className = "kpi " + s.status;
    div.innerHTML = `<div class="name">${s.metric}</div><div class="val">${fmtPct(s.value)}</div>`;
    grid.appendChild(div);
  });
  drawLineChart($("#margin-chart"), dash.charts.margin_trend.labels, dash.charts.margin_trend.datasets);
  drawBarChart($("#revenue-chart"), dash.charts.revenue.labels, dash.charts.revenue.data);
  const n = dash.narrative;
  $("#narrative").innerHTML =
    `<h3>Executive summary</h3><p>${n.executive_summary || "—"}</p>` +
    `<h3>Risk commentary</h3><p>${n.risk_commentary || "—"}</p>` +
    `<h3>Recommendations</h3><ul>${(n.recommendations || []).map((r) => `<li>${r}</li>`).join("")}</ul>`;
}

async function handleUpload(file) {
  setStatus("Uploading…");
  $("#dropzone").classList.remove("dragging");
  const form = new FormData();
  form.append("file", file);
  const up = await api("/api/upload", { method: "POST", body: form });
  state.sessionId = up.session_id;
  setStatus(`${up.summary.company_name}: ${up.summary.n_periods} periods`);
  const analysis = await api("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: state.sessionId, include_narrative: true }),
  });
  renderDashboard(analysis.dashboard);
}

async function runScenario() {
  if (!state.sessionId) {
    $("#scenario-result").textContent = "Upload a financial statement before running a scenario.";
    setStatus("Upload a statement to run scenarios");
    return;
  }
  const assumptions = {
    revenue_pct: $("#s-revenue").value,
    cogs_pct: $("#s-cogs").value,
    price_per_mt_pct: $("#s-price").value,
    opex_pct: $("#s-opex").value,
    finance_cost_pct: $("#s-finance").value,
  };
  const res = await api("/api/scenario", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: state.sessionId, assumptions, include_narrative: false }),
  });
  renderDashboard(res.dashboard);
  $("#scenario-result").textContent = `Scenario applied (${res.comparison.metric_deltas.length} metric deltas).`;
}

function resetScenario() {
  ["revenue", "cogs", "price", "opex", "finance"].forEach((k) => {
    const slider = $("#s-" + k);
    slider.value = 0;
    $("#o-" + k).textContent = "0";
  });
  $("#scenario-result").textContent = "Scenario reset. Ready to model margin, cost, price, and finance-cost changes.";
}

async function sendChat(message) {
  const log = $("#chat-log");
  log.insertAdjacentHTML("beforeend", `<div class="msg user">${message}</div>`);
  if (!state.sessionId) {
    log.insertAdjacentHTML("beforeend", `<div class="msg assistant">Upload a financial statement first so the committee can answer from your uploaded facts.</div>`);
    log.scrollTop = log.scrollHeight;
    return;
  }
  const res = await api("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: state.sessionId, message }),
  });
  log.insertAdjacentHTML("beforeend", `<div class="msg assistant">${res.reply}</div>`);
  log.scrollTop = log.scrollHeight;
}

function exportReport(kind) {
  if (!state.sessionId) {
    setStatus("Upload a statement before exporting reports");
    return;
  }
  window.open(`/api/export/${kind}?session_id=${state.sessionId}`, "_blank");
}

function wire() {
  document.body.dataset.theme = state.theme;
  drawDemoCharts();
  document.querySelectorAll("[data-count]").forEach(animateNumber);
  wireAdvisorReorder();
  updateCommitteeSummary();

  $("#theme-toggle").addEventListener("click", toggleTheme);
  $("#command-trigger").addEventListener("click", openCommandPalette);
  $("#palette-close").addEventListener("click", closeCommandPalette);
  $("#run-committee").addEventListener("click", runCommitteeAnalysis);
  $("#edit-committee").addEventListener("click", editCommittee);
  document.querySelectorAll("[data-chart-range]").forEach((button) => {
    button.addEventListener("click", () => setChartRange(button));
  });
  document.querySelectorAll("[data-committee-preset]").forEach((button) => {
    button.addEventListener("click", () => setCommitteePreset(button));
  });
  document.querySelectorAll("[data-advisor-mode]").forEach((button) => {
    button.addEventListener("click", () => setAdvisorMode(button));
  });
  document.querySelector(".committee-avatars").addEventListener("click", (e) => {
    if (e.target.closest("#quick-add-advisor")) openAdvisorModal();
  });
  $("#advisor-modal-close").addEventListener("click", closeAdvisorModal);
  $("#advisor-modal-cancel").addEventListener("click", closeAdvisorModal);
  $("#advisor-modal").addEventListener("click", (e) => {
    if (e.target.id === "advisor-modal") closeAdvisorModal();
  });
  $("#advisor-modal").querySelector("form").addEventListener("submit", (e) => {
    e.preventDefault();
    const fields = Array.from(e.currentTarget.querySelectorAll("input, textarea, select"));
    addAdvisorToCommittee({
      name: fields[0]?.value || "Custom Advisor",
      role: fields[1]?.value || "Committee Advisor",
      description: fields[8]?.value || "Custom committee advisor configured for executive decisions.",
      tags: (fields[9]?.value || "Custom, Knowledge, Objective").split(",").map((tag) => tag.trim()).filter(Boolean).slice(0, 4),
      confidence: "84%",
    });
    closeAdvisorModal();
  });
  $("#command-palette").addEventListener("click", (e) => {
    if (e.target.id === "command-palette") closeCommandPalette();
  });
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      openCommandPalette();
    }
    if (e.key === "Escape") { closeCommandPalette(); closeAdvisorModal(); }
  });

  document.querySelectorAll("[data-view]").forEach((trigger) => {
    trigger.addEventListener("click", (e) => {
      e.preventDefault();
      activateNavigation(trigger);
    });
  });

  $("#settings-theme-toggle").addEventListener("click", toggleTheme);
  $("#settings-command-palette").addEventListener("click", openCommandPalette);
  document.querySelectorAll("[data-settings-action='theme']").forEach((button) => {
    button.addEventListener("click", toggleTheme);
  });

  document.querySelectorAll("[data-open-advisor-modal]").forEach((trigger) => {
    trigger.addEventListener("click", openAdvisorModal);
  });

  document.querySelectorAll("[data-install-advisor]").forEach((button) => {
    button.addEventListener("click", () => installMarketplaceAdvisor(button));
  });

  document.querySelector(".advisor-grid").addEventListener("click", (e) => {
    const removeButton = e.target.closest("[data-remove-advisor]");
    const duplicateButton = e.target.closest("[data-duplicate-advisor]");
    const configureButton = e.target.closest("[data-configure-advisor]");
    if (removeButton) removeCommitteeAdvisor(removeButton);
    if (duplicateButton) duplicateCommitteeAdvisor(duplicateButton);
    if (configureButton) openConfigureAdvisor(configureButton);
  });

  $("#dropzone").addEventListener("dragover", (e) => { e.preventDefault(); $("#dropzone").classList.add("dragging"); });
  $("#dropzone").addEventListener("dragleave", () => $("#dropzone").classList.remove("dragging"));
  $("#dropzone").addEventListener("drop", (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file).catch((err) => setStatus("Error: " + err.message));
  });

  $("#file").addEventListener("change", (e) => {
    if (e.target.files[0]) handleUpload(e.target.files[0]).catch((err) => setStatus("Error: " + err.message));
  });
  $("#run-scenario").addEventListener("click", () => runScenario().catch((err) => ($("#scenario-result").textContent = "Error: " + err.message)));
  $("#reset-scenario").addEventListener("click", resetScenario);
  ["revenue", "cogs", "price", "opex", "finance"].forEach((k) => {
    const slider = $("#s-" + k);
    slider.addEventListener("input", () => ($("#o-" + k).textContent = slider.value));
  });
  $("#chat-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const input = $("#chat-input");
    const msg = input.value.trim();
    if (msg) { sendChat(msg).catch((err) => alert(err.message)); input.value = ""; }
  });
  document.querySelectorAll("[data-export]").forEach((btn) => {
    btn.addEventListener("click", () => {
      exportReport(btn.dataset.export);
      closeCommandPalette();
    });
  });
  document.querySelectorAll("[data-command]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const command = btn.dataset.command || "";
      if (command.toLowerCase().includes("toggle")) toggleTheme();
      if (command.toLowerCase().includes("scenario")) runScenario().catch((err) => ($("#scenario-result").textContent = "Error: " + err.message));
      if (command.toLowerCase().includes("explain")) {
        $("#chat-input").value = "Why did gross margin fall?";
        $("#chat-input").focus();
      }
      closeCommandPalette();
    });
  });
}

wire();
