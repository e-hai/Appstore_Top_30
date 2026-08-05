const state = {
  dates: [],
  meta: null,
  date: "",
  region: "north_america",
  country: "us",
  chart: "free",
  store: "app_store",
  category: "",
  subcategory: "",
  summary: null,
  rows: [],
  hasPrevious: false,
  search: "",
};

const $ = (id) => document.getElementById(id);

const els = {
  date: $("date-select"),
  store: $("store-select"),
  region: $("region-select"),
  country: $("country-select"),
  chart: $("chart-select"),
  category: $("category-select"),
  subcategory: $("subcategory-select"),
  search: $("search-input"),
  summary: $("summary-grid"),
  distribution: $("distribution"),
  tableBody: $("table-body"),
  tableHead: $("table-head"),
  tableCount: $("table-count"),
  empty: $("empty-state"),
  drawer: $("trend-drawer"),
  drawerMask: $("drawer-mask"),
  trendTitle: $("trend-title"),
  trendMeta: $("trend-meta"),
  trendChart: $("trend-chart"),
  trendClose: $("trend-close"),
  sidebarToggle: $("sidebar-toggle"),
  theme: $("theme-select"),
  loading: $("loading-bar"),
};

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[ch]);
}

function setLoading(active) {
  els.loading.classList.toggle("active", active);
}

function applySidebarState(collapsed) {
  document.body.classList.toggle("sidebar-collapsed", collapsed);
  els.sidebarToggle.setAttribute("aria-expanded", String(!collapsed));
  els.sidebarToggle.setAttribute("aria-label", collapsed ? "展开侧边栏" : "收起侧边栏");
  els.sidebarToggle.title = collapsed ? "展开侧边栏" : "收起侧边栏";
}

async function api(path) {
  const response = await fetch(path);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || response.statusText);
  }
  return response.json();
}

function bindEvents() {
  els.date.addEventListener("change", async () => {
    state.date = els.date.value;
    await loadMeta();
    await refresh();
  });
  els.store.addEventListener("change", async () => {
    state.store = els.store.value;
    localStorage.setItem("appstore-store", state.store);
    state.category = "";
    state.subcategory = "";
    populateCategorySelect();
    populateSubcategorySelect();
    await loadMeta();
    await refresh();
  });
  els.region.addEventListener("change", async () => {
    state.region = els.region.value;
    populateCountrySelect();
    state.country = els.country.value;
    await refresh();
  });
  els.country.addEventListener("change", async () => {
    state.country = els.country.value;
    await refresh();
  });
  els.chart.addEventListener("change", async () => {
    state.chart = els.chart.value;
    await refresh();
  });
  els.category.addEventListener("change", async () => {
    state.category = els.category.value;
    state.subcategory = "";
    populateSubcategorySelect();
    await refresh();
  });
  els.subcategory.addEventListener("change", async () => {
    state.subcategory = els.subcategory.value;
    await refresh();
  });
  els.search.addEventListener("input", () => {
    state.search = els.search.value.trim().toLowerCase();
    renderTable();
  });
  els.trendClose.addEventListener("click", closeTrend);
  els.drawerMask.addEventListener("click", closeTrend);
  els.sidebarToggle.addEventListener("click", () => {
    const collapsed = document.body.classList.toggle("sidebar-collapsed");
    applySidebarState(collapsed);
    localStorage.setItem("appstore-sidebar", collapsed ? "collapsed" : "expanded");
  });
  els.theme.addEventListener("change", () => {
    document.body.dataset.theme = els.theme.value;
    localStorage.setItem("appstore-theme", els.theme.value);
  });
}

async function loadMeta() {
  state.meta = await api(
    `/api/meta?date=${encodeURIComponent(state.date)}&store=${encodeURIComponent(state.store)}`
  );
}

function populateDateSelect() {
  els.date.innerHTML = "";
  for (const item of state.dates) {
    const option = document.createElement("option");
    option.value = item.date;
    const counts = item.stores[state.store] || {};
    option.textContent = `${item.date} · ${counts.countries || 0} 国`;
    els.date.appendChild(option);
  }
  if (!state.dates.some((item) => item.date === state.date)) {
    state.date = state.dates[state.dates.length - 1].date;
  }
  els.date.value = state.date;
}

function populateRegionSelect() {
  els.region.innerHTML = "";
  for (const [key, spec] of Object.entries(state.meta.regions)) {
    const option = document.createElement("option");
    option.value = key;
    option.textContent = spec.name;
    els.region.appendChild(option);
  }
  if (!state.meta.regions[state.region]) {
    state.region = Object.keys(state.meta.regions)[0];
  }
  els.region.value = state.region;
}

function populateCountrySelect() {
  els.country.innerHTML = "";
  const countries = state.meta.regions[state.region].countries;
  for (const country of countries) {
    const option = document.createElement("option");
    option.value = country.code;
    option.textContent = country.name;
    els.country.appendChild(option);
  }
  if (!countries.some((c) => c.code === state.country)) {
    state.country = countries[0].code;
  }
  els.country.value = state.country;
}

function populateChartSelect() {
  els.chart.innerHTML = "";
  for (const [key, name] of Object.entries(state.meta.charts)) {
    const option = document.createElement("option");
    option.value = key;
    option.textContent = name;
    els.chart.appendChild(option);
  }
  els.chart.value = state.chart;
}

function populateCategorySelect() {
  els.category.innerHTML = "";
  const options = [
    ["", "全部分类（总榜）"],
    ["apps", "应用"],
    ["games", "游戏"],
  ];
  for (const [value, name] of options) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = name;
    els.category.appendChild(option);
  }
  els.category.value = state.category;
}

function populateSubcategorySelect() {
  els.subcategory.innerHTML = "";
  let genres = [];
  let placeholder = "";
  if (state.category === "apps") {
    genres = state.meta.app_genres || [];
    if (!genres.some((g) => g.id === state.subcategory) && genres.length > 0) {
      state.subcategory = genres[0].id;
    }
  } else if (state.category === "games") {
    genres = state.meta.game_genres || [];
    placeholder = "全部游戏";
  } else if (state.category === "root") {
    placeholder = "总榜";
  }
  if (placeholder) {
    const all = document.createElement("option");
    all.value = "";
    all.textContent = placeholder;
    els.subcategory.appendChild(all);
  }
  for (const genre of genres) {
    const option = document.createElement("option");
    option.value = genre.id;
    option.textContent = genre.name;
    els.subcategory.appendChild(option);
  }
  if (!genres.some((g) => g.id === state.subcategory)) {
    state.subcategory = "";
  }
  els.subcategory.value = state.subcategory;
  els.subcategory.disabled = state.category === "" || state.category === "root";
}

function filterParams() {
  if (state.store === "play") {
    if (state.category === "" || state.category === "root") {
      return "&genre=all";
    }
    if (state.category === "apps") {
      return `&genre=${encodeURIComponent(state.subcategory)}`;
    }
    if (state.category === "games") {
      return state.subcategory
        ? `&genre=${encodeURIComponent(state.subcategory)}`
        : "&genre=GAME";
    }
    return "";
  }
  if (state.category === "" || state.category === "root") {
    return "&genre=36";
  }
  if (state.category === "apps") {
    return `&genre=${encodeURIComponent(state.subcategory)}`;
  }
  if (state.category === "games") {
    return state.subcategory
      ? `&genre=${encodeURIComponent(state.subcategory)}`
      : "&genre=6014";
  }
  return "";
}

async function refresh() {
  setLoading(true);
  try {
    const summaryUrl = `/api/summary?date=${encodeURIComponent(state.date)}`;
    const rankingUrl =
      `/api/rankings?date=${encodeURIComponent(state.date)}` +
      `&country=${encodeURIComponent(state.country)}` +
      `&chart=${encodeURIComponent(state.chart)}` +
      `&store=${encodeURIComponent(state.store)}` +
      filterParams();
    const [summary, rankings] = await Promise.all([
      api(`${summaryUrl}&store=${encodeURIComponent(state.store)}`),
      api(rankingUrl),
    ]);
    state.summary = summary;
    state.rows = rankings.rows;
    state.hasPrevious = rankings.has_previous;
    renderSummary();
    renderDistribution();
    renderTable();
  } finally {
    setLoading(false);
  }
}

function renderSummary() {
  const summary = (state.summary.summaries || []).find(
    (s) => s.country === state.country && s.chart === state.chart
  );
  const counts = state.summary.counts || {};
  if (!summary) {
    els.summary.innerHTML = "<div class=\"empty-state\">暂无数据</div>";
    return;
  }
  const items = [
    ["榜单条目", summary.entries, ""],
    ["分类数", summary.genres, ""],
    ["新上榜", summary.new, "new"],
    ["跌出榜单", summary.left, "down"],
    ["上升", summary.up, "up"],
    ["下降", summary.down, "down"],
    ["持平", summary.same, ""],
    ["覆盖国家", counts.countries || 0, "accent"],
  ];
  els.summary.innerHTML = items
    .map(
      ([label, value, tone]) =>
        `<div class="stat"><span class="label">${esc(label)}</span>` +
        `<span class="value ${tone ? ` ${tone}` : ""}">${esc(value)}</span></div>`
    )
    .join("");
}

function renderDistribution() {
  const counts = new Map();
  for (const row of state.rows) {
    const key = row.genre_name || "未分类";
    counts.set(key, (counts.get(key) || 0) + 1);
  }
  const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10);
  if (!sorted.length) {
    els.distribution.innerHTML = "<div class=\"empty-state\">暂无数据</div>";
    return;
  }
  const max = sorted[0][1];
  els.distribution.innerHTML = sorted
    .map(([name, count]) => {
      const width = Math.max(4, Math.round((count / max) * 100));
      return (
        `<div class="bar-row"><span class="bar-label" title="${esc(name)}">${esc(name)}</span>` +
        `<div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div>` +
        `<span class="bar-value">${count}</span></div>`
      );
    })
    .join("");
}

function badgeFor(row) {
  if (row.status === "new" && !state.hasPrevious) {
    return `<span class="badge first">首日</span>`;
  }
  if (row.status === "new") {
    return `<span class="badge new">新上榜</span>`;
  }
  if (row.status === "up") {
    return `<span class="badge up">▲ +${row.rank_change}</span>`;
  }
  if (row.status === "down") {
    return `<span class="badge down">▼ ${Math.abs(row.rank_change)}</span>`;
  }
  return `<span class="badge same">持平</span>`;
}

function priceText(row) {
  if (row.price_amount == null) return "-";
  if (Number(row.price_amount) === 0) return "免费";
  return `${Number(row.price_amount).toFixed(2)} ${esc(row.price_currency || "")}`.trim();
}

function renderTable() {
  els.tableHead.innerHTML =
    "<tr><th>排名</th><th>应用</th><th>开发者</th><th>分类</th><th>价格</th><th>评分</th><th>变化</th></tr>";
  const query = state.search;
  const rows = state.rows.filter((row) => {
    if (!query) return true;
    return `${row.name} ${row.developer}`.toLowerCase().includes(query);
  });
  els.tableCount.textContent = `${rows.length} 条记录 · 点击应用查看排名趋势`;
  els.empty.classList.toggle("hidden", rows.length > 0);
  els.tableBody.innerHTML = rows
    .map(
      (row) => `
        <tr data-app-id="${row.app_id}" data-app-name="${esc(row.name)}">
          <td class="rank-cell">${row.curr_rank ?? "-"}</td>
          <td>
            <div class="app-cell">
              ${row.icon_url ? `<img class="app-icon" src="${esc(row.icon_url)}" alt="">` : `<span class="app-icon"></span>`}
              <div>
                <div class="app-name">${esc(row.name)}</div>
                <div class="app-id">id ${row.app_id}</div>
              </div>
            </div>
          </td>
          <td class="dev-cell">${esc(row.developer)}</td>
          <td>${esc(row.genre_name)}</td>
          <td class="num">${priceText(row)}</td>
          <td class="num">${row.rating != null ? Number(row.rating).toFixed(2) : "-"}</td>
          <td>${badgeFor(row)}</td>
        </tr>`
    )
    .join("");

  els.tableBody.querySelectorAll("tr[data-app-id]").forEach((tr) => {
    tr.addEventListener("click", () => {
      els.tableBody.querySelectorAll("tr.selected").forEach((r) => r.classList.remove("selected"));
      tr.classList.add("selected");
      showTrend(tr.dataset.appId, tr.dataset.appName, state.country);
    });
  });
}

async function showTrend(appId, name, country = state.country) {
  const url =
    `/api/trend?app_id=${encodeURIComponent(appId)}` +
    `&country=${encodeURIComponent(country)}` +
    `&chart=${encodeURIComponent(state.chart)}` +
    `&store=${encodeURIComponent(state.store)}`;
  const data = await api(url);
  els.trendTitle.textContent = `${name} · 排名趋势`;
  els.trendMeta.textContent = `${state.summary.date} · ${country.toUpperCase()} · ${state.meta.charts[state.chart]}`;
  if (!data.rows.length) {
    els.trendChart.innerHTML = "<div class=\"empty-state\">暂无历史数据</div>";
  } else {
    renderTrendChart(data.rows);
  }
  els.drawer.classList.add("open");
  els.drawer.setAttribute("aria-hidden", "false");
  els.drawerMask.classList.remove("hidden");
}

function closeTrend() {
  els.drawer.classList.remove("open");
  els.drawer.setAttribute("aria-hidden", "true");
  els.drawerMask.classList.add("hidden");
}

function renderTrendChart(rows) {
  const cssVar = (name, fallback) =>
    getComputedStyle(document.body).getPropertyValue(name).trim() || fallback;
  const accent = cssVar("--chart-1", "#0f766e");
  const muted = cssVar("--muted-foreground", "#71717a");
  const grid = cssVar("--border", "#e4e4e7");
  const textColor = cssVar("--foreground", "#111111");
  const width = 620;
  const height = 280;
  const pad = { top: 24, right: 26, bottom: 42, left: 46 };
  const ranks = rows.map((row) => Number(row.best_rank));
  const maxRank = Math.max(30, ...ranks);
  const minRank = 1;
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const xAt = (index) =>
    rows.length === 1
      ? pad.left + plotW / 2
      : pad.left + (index / (rows.length - 1)) * plotW;
  const yAt = (rank) => pad.top + ((rank - minRank) / (maxRank - minRank)) * plotH;

  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("role", "img");

  const ticks = maxRank >= 30 ? [1, 10, 20, 30, maxRank] : [1, maxRank];
  for (const tick of ticks) {
    const y = yAt(tick);
    const line = document.createElementNS(ns, "line");
    line.setAttribute("x1", pad.left);
    line.setAttribute("y1", y);
    line.setAttribute("x2", width - pad.right);
    line.setAttribute("y2", y);
    line.setAttribute("stroke", grid);
    line.setAttribute("stroke-dasharray", "3 4");
    svg.appendChild(line);
    const text = document.createElementNS(ns, "text");
    text.setAttribute("x", pad.left - 10);
    text.setAttribute("y", y + 4);
    text.setAttribute("text-anchor", "end");
    text.setAttribute("fill", muted);
    text.setAttribute("font-size", "11");
    text.textContent = tick;
    svg.appendChild(text);
  }

  if (rows.length > 1) {
    const path = document.createElementNS(ns, "path");
    const points = rows.map((row, index) => `${xAt(index)},${yAt(Number(row.best_rank))}`);
    path.setAttribute("d", `M${points.join(" L")}`);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", accent);
    path.setAttribute("stroke-width", "2.5");
    path.setAttribute("stroke-linecap", "round");
    path.setAttribute("stroke-linejoin", "round");
    svg.appendChild(path);
  }

  rows.forEach((row, index) => {
    const cx = xAt(index);
    const cy = yAt(Number(row.best_rank));
    const dot = document.createElementNS(ns, "circle");
    dot.setAttribute("cx", cx);
    dot.setAttribute("cy", cy);
    dot.setAttribute("r", "4");
    dot.setAttribute("fill", accent);
    svg.appendChild(dot);

    const dateText = document.createElementNS(ns, "text");
    dateText.setAttribute("x", cx);
    dateText.setAttribute("y", height - 16);
    dateText.setAttribute("text-anchor", "middle");
    dateText.setAttribute("fill", muted);
    dateText.setAttribute("font-size", "10");
    dateText.textContent = row.date.slice(5);
    svg.appendChild(dateText);

    const rankText = document.createElementNS(ns, "text");
    rankText.setAttribute("x", cx);
    rankText.setAttribute("y", cy - 9);
    rankText.setAttribute("text-anchor", "middle");
    rankText.setAttribute("fill", textColor);
    rankText.setAttribute("font-size", "11");
    rankText.setAttribute("font-weight", "600");
    rankText.textContent = row.best_rank;
    svg.appendChild(rankText);
  });

  els.trendChart.innerHTML = "";
  els.trendChart.appendChild(svg);
}

async function init() {
  const applyTheme = (theme) => {
    if (["light", "dark"].includes(theme)) {
      document.body.dataset.theme = theme;
      els.theme.value = theme;
    }
  };
  const savedTheme = localStorage.getItem("appstore-theme");
  if (savedTheme) {
    applyTheme(savedTheme);
  }
  const savedStore = localStorage.getItem("appstore-store");
  if (savedStore === "play" || savedStore === "app_store") {
    state.store = savedStore;
    els.store.value = savedStore;
  }
  applySidebarState(localStorage.getItem("appstore-sidebar") === "collapsed");
  bindEvents();
  try {
    const params = new URLSearchParams(location.search);
    if (params.has("theme")) {
      applyTheme(params.get("theme"));
    }
    if (params.has("category")) {
      state.category = params.get("category");
    }
    if (params.has("subcategory")) {
      state.subcategory = params.get("subcategory");
    }
    const datesData = await api("/api/dates");
    state.dates = datesData.dates;
    if (!state.dates.length) {
      document.querySelector("main").innerHTML =
        "<div class=\"panel empty-state\">还没有数据，请先运行 python3 -m appstore_top30 run。</div>";
      return;
    }
    state.date = state.dates[state.dates.length - 1].date;
    const latestForStore = [...state.dates].reverse().find(
      (item) => item.stores[state.store] && item.stores[state.store].countries > 0
    );
    if (latestForStore) {
      state.date = latestForStore.date;
    }
    await loadMeta();
    populateDateSelect();
    populateRegionSelect();
    populateCountrySelect();
    populateChartSelect();
    populateCategorySelect();
    populateSubcategorySelect();
    await refresh();
  } catch (error) {
    document.querySelector("main").innerHTML =
      `<div class="panel empty-state">加载失败：${esc(error.message)}</div>`;
  }
}

init();
