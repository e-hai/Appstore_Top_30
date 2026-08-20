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
  currentTab: "all",
  selectedApps: new Map(), // map app_id -> app_name
  lastApiData: {
    rankings: null,
    trend: null,
    summary: null,
    meta: null,
  },
  currentDebugTab: "rankings",
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
  tableBody: $("table-body"),
  tableHead: $("table-head"),
  tableCount: $("table-count"),
  empty: $("empty-state"),
  drawerMask: $("drawer-mask"),
  themeButtons: Array.from(document.querySelectorAll(".theme-option")),
  loading: $("loading-bar"),
  tabButtons: Array.from(document.querySelectorAll(".tab-btn")),
  pubDrawer: $("publisher-drawer"),
  pubTitle: $("pub-title"),
  pubMeta: $("pub-meta"),
  pubContent: $("pub-content"),
  pubClose: $("pub-close"),
  trendsSection: $("trends-section"),
  trendsTitle: $("trends-title"),
  trendsChart: $("trends-chart"),
  trendsMeta: $("trends-meta"),
  resetTop5Btn: $("reset-top5-btn"),
  debugBtn: $("debug-btn"),
  debugDrawer: $("debug-drawer"),
  debugClose: $("debug-close"),
  debugCopyBtn: $("debug-copy-btn"),
  debugMeta: $("debug-meta"),
  debugJsonCode: $("debug-json-code"),
  debugTabButtons: Array.from(document.querySelectorAll(".debug-tab-btn")),
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

function chartColor(index) {
  const names = [
    "--chart-1",
    "--chart-2",
    "--chart-3",
    "--chart-4",
    "--chart-5",
  ];
  return getComputedStyle(document.body).getPropertyValue(names[index % names.length]).trim() || "#6366f1";
}

function storeName() {
  return state.store === "play" ? "Google Play" : "App Store";
}

function applyTheme(theme) {
  if (!["light", "dark"].includes(theme)) {
    return;
  }
  document.body.dataset.theme = theme;
  for (const button of els.themeButtons) {
    const active = button.dataset.theme === theme;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", String(active));
  }
}

function setLoading(active) {
  els.loading.classList.toggle("active", active);
}

function isStaticHosting() {
  const host = window.location.hostname;
  return host.includes("github.io") || window.location.protocol === "file:" || (!window.location.port && host !== "localhost" && host !== "127.0.0.1") || window.location.pathname.includes("/docs/");
}

function resolveStaticApiUrl(path) {
  const [pathname, queryString] = path.split("?");
  const params = new URLSearchParams(queryString || "");
  const base = "./api";

  if (pathname === "/api/dates") {
    return `${base}/dates.json`;
  }
  if (pathname === "/api/casual-giants") {
    const region = params.get("region") || "all";
    return region === "all" ? `${base}/casual_giants.json` : `${base}/casual_giants_${region}.json`;
  }
  if (pathname === "/api/meta") {
    const store = params.get("store") || "app_store";
    return `${base}/meta_${store}.json`;
  }
  if (pathname === "/api/category-trends") {
    const store = params.get("store") || "app_store";
    const country = params.get("country") || "us";
    return `${base}/category_trends/${store}_${country}.json`;
  }
  if (pathname === "/api/summary") {
    const store = params.get("store") || "app_store";
    const date = params.get("date") || state.date;
    return `${base}/summary/${store}_${date}.json`;
  }
  if (pathname === "/api/rankings") {
    const store = params.get("store") || "app_store";
    const date = params.get("date") || state.date;
    const country = params.get("country") || "us";
    const chart = params.get("chart") || "free";
    const genre = params.get("genre");
    if (genre && genre !== "36" && genre !== "all") {
      return `${base}/rankings/${store}_${country}_${chart}_${genre}_${date}.json`;
    }
    return `${base}/rankings/${store}_${country}_${chart}_${date}.json`;
  }
  if (pathname === "/api/trend") {
    const store = params.get("store") || "app_store";
    const country = params.get("country") || "us";
    const chart = params.get("chart") || "free";
    return `${base}/trend/${store}_${country}_${chart}.json`;
  }
  return path;
}

async function api(path) {
  let fetchUrl = path;
  if (isStaticHosting() && path.startsWith("/api/")) {
    fetchUrl = resolveStaticApiUrl(path);
  }

  let response = await fetch(fetchUrl);
  if (!response.ok && isStaticHosting() && fetchUrl.includes("/rankings/")) {
    const fallbackUrl = `./api/rankings/${state.store}_${state.country}_${state.chart}_${state.date}.json`;
    if (fetchUrl !== fallbackUrl) {
      response = await fetch(fallbackUrl);
    }
  }
  if (!response.ok && fetchUrl !== path && !isStaticHosting()) {
    // Fallback try original path if local dynamic server
    response = await fetch(path);
  }

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || response.statusText);
  }
  const data = await response.json();
  if (path.includes("/api/rankings")) state.lastApiData.rankings = data;
  else if (path.includes("/api/trend")) state.lastApiData.trend = data;
  else if (path.includes("/api/summary")) state.lastApiData.summary = data;
  else if (path.includes("/api/meta")) state.lastApiData.meta = data;

  if (els.debugDrawer && els.debugDrawer.classList.contains("open")) {
    renderDebugJson();
  }
  return data;
}

function clearSelections() {
  state.selectedApps.clear();
  updateCompareBar();
}

function renderDebugJson() {
  if (!els.debugJsonCode) return;
  const type = state.currentDebugTab || "rankings";
  const data = state.lastApiData[type];
  if (!data) {
    els.debugJsonCode.textContent = `// 暂无 /api/${type} 接口的响应数据，请在页面中进行相应操作...`;
    return;
  }
  els.debugJsonCode.textContent = JSON.stringify(data, null, 2);
  if (els.debugMeta) {
    els.debugMeta.textContent = `当前展示: /api/${type} · 大小: ${JSON.stringify(data).length} 字节`;
  }
}

function showDebugDrawer() {
  renderDebugJson();
  els.debugDrawer.classList.add("open");
  els.debugDrawer.setAttribute("aria-hidden", "false");
  els.drawerMask.classList.remove("hidden");
}

function closeDebugDrawer() {
  els.debugDrawer.classList.remove("open");
  els.debugDrawer.setAttribute("aria-hidden", "true");
  els.drawerMask.classList.add("hidden");
}

function bindEvents() {
  els.date.addEventListener("change", async () => {
    state.date = els.date.value;
    clearSelections();
    await loadMeta();
    await refresh();
  });
  els.store.addEventListener("change", async () => {
    state.store = els.store.value;
    localStorage.setItem("appstore-store", state.store);
    state.category = "";
    state.subcategory = "";
    clearSelections();
    populateCategorySelect();
    populateSubcategorySelect();
    await loadMeta();
    await refresh();
  });
  els.region.addEventListener("change", async () => {
    state.region = els.region.value;
    clearSelections();
    populateCountrySelect();
    state.country = els.country.value;
    await refresh();
  });
  els.country.addEventListener("change", async () => {
    state.country = els.country.value;
    clearSelections();
    await refresh();
  });
  els.chart.addEventListener("change", async () => {
    state.chart = els.chart.value;
    clearSelections();
    await refresh();
  });
  els.category.addEventListener("change", async () => {
    state.category = els.category.value;
    state.subcategory = "";
    clearSelections();
    populateCategorySelect();
    await refresh();
  });
  els.subcategory.addEventListener("change", async () => {
    state.subcategory = els.subcategory.value;
    clearSelections();
    await refresh();
  });
  els.search.addEventListener("input", () => {
    state.search = els.search.value.trim().toLowerCase();
    renderTable();
  });

  // 调试 JSON 抽屉事件
  if (els.debugBtn) {
    els.debugBtn.addEventListener("click", showDebugDrawer);
  }
  if (els.debugClose) {
    els.debugClose.addEventListener("click", closeDebugDrawer);
  }
  if (els.debugCopyBtn) {
    els.debugCopyBtn.addEventListener("click", () => {
      const code = els.debugJsonCode.textContent;
      navigator.clipboard.writeText(code).then(() => {
        const origText = els.debugCopyBtn.textContent;
        els.debugCopyBtn.textContent = "✅ 已复制";
        setTimeout(() => { els.debugCopyBtn.textContent = origText; }, 1800);
      });
    });
  }
  for (const btn of els.debugTabButtons) {
    btn.addEventListener("click", () => {
      for (const b of els.debugTabButtons) b.classList.remove("active");
      btn.classList.add("active");
      state.currentDebugTab = btn.dataset.type;
      renderDebugJson();
    });
  }

  // 功能一：切页 Tab 响应
  for (const btn of els.tabButtons) {
    btn.addEventListener("click", () => {
      for (const b of els.tabButtons) b.classList.remove("active");
      btn.classList.add("active");
      state.currentTab = btn.dataset.tab;
      renderTable();
    });
  }

  // 宽度自适应 / 全屏展示模式切换
  const btnToggleWidth = document.getElementById("btn-toggle-table-width");
  if (btnToggleWidth) {
    let isFullWidth = false;
    btnToggleWidth.addEventListener("click", () => {
      const grid = document.querySelector(".dashboard-grid");
      if (!grid) return;
      isFullWidth = !isFullWidth;
      grid.classList.toggle("full-table-mode", isFullWidth);
      btnToggleWidth.textContent = isFullWidth ? "📋 双栏对照" : "↔ 宽度自适应";
      btnToggleWidth.title = isFullWidth ? "切换回双栏趋势对照模式" : "切换榜单明细全屏自适应宽度";
    });
  }

  // 功能二：重置榜单趋势为 Top 5
  if (els.resetTop5Btn) {
    els.resetTop5Btn.addEventListener("click", () => {
      clearSelections();
      renderTable();
      renderMainTrendsChart();
    });
  }

  // 智能分析大盘统一入口绑定
  const btnIntelHub = document.getElementById("btn-intel-hub");
  const btnAttribution = document.getElementById("btn-attribution");
  const intelClose = document.getElementById("intel-close");
  if (btnIntelHub) btnIntelHub.addEventListener("click", () => showIntelDrawer('attr'));
  if (btnAttribution) btnAttribution.addEventListener("click", () => showIntelDrawer('attr'));
  if (intelClose) intelClose.addEventListener("click", closeIntelDrawer);

  // 抽屉内 Tab 切页
  const tabAttr = document.getElementById("intel-tab-attr");
  const tabCat = document.getElementById("intel-tab-cat");
  const tabGiants = document.getElementById("intel-tab-giants");
  const panelAttr = document.getElementById("intel-panel-attr");
  const panelCat = document.getElementById("intel-panel-cat");
  const panelGiants = document.getElementById("intel-panel-giants");

  const switchIntelTab = (target) => {
    if (tabAttr) tabAttr.classList.toggle("active", target === 'attr');
    if (tabCat) tabCat.classList.toggle("active", target === 'cat');
    if (tabGiants) tabGiants.classList.toggle("active", target === 'giants');

    if (panelAttr) panelAttr.classList.toggle("hidden", target !== 'attr');
    if (panelCat) panelCat.classList.toggle("hidden", target !== 'cat');
    if (panelGiants) panelGiants.classList.toggle("hidden", target !== 'giants');

    if (target === 'attr') loadAttributionData();
    if (target === 'cat') loadCategoryTrendsData();
    if (target === 'giants') loadCasualGiantsData();
  };

  if (tabAttr) tabAttr.addEventListener("click", () => switchIntelTab('attr'));
  if (tabCat) tabCat.addEventListener("click", () => switchIntelTab('cat'));
  if (tabGiants) tabGiants.addEventListener("click", () => switchIntelTab('giants'));

  // 厂商区域切页按钮
  document.querySelectorAll(".giant-region-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".giant-region-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      loadCasualGiantsData(btn.dataset.region || 'all');
    });
  });

  els.pubClose.addEventListener("click", closePublisherDrawer);
  els.drawerMask.addEventListener("click", () => {
    closePublisherDrawer();
    closeDebugDrawer();
    closeIntelDrawer();
  });

  for (const button of els.themeButtons) {
    button.addEventListener("click", () => {
      applyTheme(button.dataset.theme);
      localStorage.setItem("appstore-theme", button.dataset.theme);
    });
  }
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

function showAttributionDrawer() {
  const attrDrawer = document.getElementById("attribution-drawer");
  if (!attrDrawer) return;
  attrDrawer.classList.add("open");
  attrDrawer.setAttribute("aria-hidden", "false");
  els.drawerMask.classList.remove("hidden");
}

function closeAttributionDrawer() {
  const attrDrawer = document.getElementById("attribution-drawer");
  if (!attrDrawer) return;
  attrDrawer.classList.remove("open");
  attrDrawer.setAttribute("aria-hidden", "true");
  els.drawerMask.classList.add("hidden");
}

function renderQuantSummary() {
  const qs = state.quantSummary || {};
  const elSpiker = document.getElementById("quant-top-spiker");
  const elStable = document.getElementById("quant-top-stable");
  const elVol = document.getElementById("quant-avg-volatility");
  const elCount = document.getElementById("quant-spiking-count");

  if (elSpiker) elSpiker.innerHTML = qs.top_spiker_name ? `${esc(qs.top_spiker_name)} <span class="badge up">${qs.top_spiker_val}</span>` : "-";
  if (elStable) elStable.innerHTML = qs.top_stable_name ? `${esc(qs.top_stable_name)} <span class="badge first">${qs.top_stable_val}</span>` : "-";
  if (elVol) {
    const volNum = parseFloat(qs.avg_volatility || 0);
    const label = volNum < 0.5 ? "低竞争" : volNum < 2.0 ? "中等热度" : "强洗牌";
    elVol.textContent = qs.avg_volatility ? `${qs.avg_volatility} (${label})` : "-";
  }
  if (elCount) elCount.innerHTML = `<span class="badge up">🚀 ${qs.spiking_count || 0} 款飙升</span> <span class="badge new">🆕 ${qs.new_count || 0} 款新上榜</span>`;

  // 渲染归因分析抽屉内容 (Attribution Drawer Content)
  const attr = state.marketAttribution || {};
  const elMeta = document.getElementById("attr-meta");
  const elSummary = document.getElementById("attribution-summary-drawer");
  const elList = document.getElementById("attribution-factors-list-drawer");

  if (elMeta) elMeta.textContent = `${attr.date || state.date || "今日"} · ${attr.country_name || ""} ${attr.chart_name || ""}`;
  if (elSummary) elSummary.textContent = attr.exec_summary || "暂无当日归因洞察数据";
  if (elList && attr.factors) {
    elList.innerHTML = attr.factors
      .map(
        (f) => `
        <div class="factor-item">
          <div class="factor-icon">${f.icon}</div>
          <div class="factor-content">
            <div class="factor-title">${esc(f.title)}</div>
            <div class="factor-detail">${esc(f.detail)}</div>
          </div>
        </div>`
      )
      .join("");
  }

  // Helper function to build 4-pillar inline pills HTML
  const buildCommercialPillarsHtml = (a) => {
    const p = a.driver?.pillars;
    if (!p) return '';
    return `
      <div class="attr-pill-row">
        <span class="attr-pillar-pill">📦 <strong>版本:</strong> ${esc(p.aso_version || '-')}</span>
        <span class="attr-pillar-pill">🎯 <strong>宣传:</strong> ${esc(p.ua_sov || '-')}</span>
        <span class="attr-pillar-pill">🎉 <strong>活动:</strong> ${esc(p.liveops || '-')}</span>
        <span class="attr-pillar-pill">💰 <strong>收费:</strong> ${esc(p.monetization || '-')}</span>
      </div>`;
  };

  // Helper function to build multi-channel news card HTML
  const buildCommercialReportsHtml = (a) => {
    if (!a.commercial_reports || !a.commercial_reports.length) return '';
    return `
      <div class="attr-news-card">
        <div class="attr-news-header">📰 全网新闻与商业平台报道</div>
        ${a.commercial_reports.map(r => `
          <div class="attr-news-item">
            <a class="attr-news-link" href="${esc(r.url)}" target="_blank" rel="noopener">[${esc(r.platform)}] ${esc(r.title)} ↗</a>
            <div class="attr-news-snippet">${esc(r.snippet)}</div>
          </div>
        `).join('')}
      </div>`;
  };

  // Helper function to render a unified modern App Card
  const renderAppCard = (a, extraBadgeHtml = '') => `
    <div class="attr-card">
      <div class="attr-card-header">
        <div class="attr-card-left">
          <span class="attr-rank-badge">#${a.curr_rank}</span>
          <div class="attr-app-info">
            <div class="attr-app-name">${esc(a.name)}</div>
            <div class="attr-app-dev">${esc(a.genre_name)} · ${esc(a.developer)}</div>
          </div>
        </div>
        <div style="display:flex; gap:6px; align-items:center;">
          <span class="badge ${a.driver?.badge_cls || 'up'}">${esc(a.driver?.tag || '异动')}</span>
          ${extraBadgeHtml}
        </div>
      </div>
      <div class="attr-summary-box">
        ${esc(a.driver?.detail || '')}
      </div>
      ${buildCommercialPillarsHtml(a)}
      ${buildCommercialReportsHtml(a)}
    </div>`;

  // 渲染 🚀 今日冲榜爆发 Top 3
  const elRising = document.getElementById("attr-rising-list");
  if (elRising) {
    elRising.innerHTML = (attr.rising_apps && attr.rising_apps.length > 0)
      ? attr.rising_apps.map(a => renderAppCard(a, `<span class="badge up">▲ +${a.rank_change}</span>`)).join("")
      : '<div class="no-data" style="font-size:11px; color:var(--text-3); text-align:center; padding:8px;">今日无明显爆发 App</div>';
  }

  // 渲染 👑 最强留存霸榜 Top 3
  const elStableList = document.getElementById("attr-stable-list");
  if (elStableList) {
    elStableList.innerHTML = (attr.stable_apps && attr.stable_apps.length > 0)
      ? attr.stable_apps.map(a => renderAppCard(a, `<span class="badge first">留存榜</span>`)).join("")
      : '<div class="no-data" style="font-size:11px; color:var(--text-3); text-align:center; padding:8px;">暂无数据</div>';
  }

  // 渲染 📉 流量回调下滑 Top 3
  const elFalling = document.getElementById("attr-falling-list");
  if (elFalling) {
    elFalling.innerHTML = (attr.falling_apps && attr.falling_apps.length > 0)
      ? attr.falling_apps.map(a => renderAppCard(a, `<span class="badge down">▼ ${a.rank_change}</span>`)).join("")
      : '<div class="no-data" style="font-size:11px; color:var(--text-3); text-align:center; padding:8px;">今日无明显下滑 App</div>';
  }

  // 渲染 🆕 今日新上榜 App
  const elNew = document.getElementById("attr-new-list");
  if (elNew) {
    elNew.innerHTML = (attr.new_apps && attr.new_apps.length > 0)
      ? attr.new_apps.map(a => renderAppCard(a, `<span class="badge new">NEW</span>`)).join("")
      : '<div class="no-data" style="font-size:11px; color:var(--text-3); text-align:center; padding:8px;">今日无新上榜 App</div>';
  }
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
    state.quantSummary = rankings.quant_summary || {};
    state.marketAttribution = rankings.market_attribution || {};
    state.hasPrevious = rankings.has_previous;
    renderQuantSummary();
    renderTable();
    await renderMainTrendsChart();
  } finally {
    setLoading(false);
  }
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

function updateCompareBar() {
  const count = state.selectedApps.size;
  if (els.resetTop5Btn) {
    els.resetTop5Btn.classList.toggle("hidden", count === 0);
  }
}

// 勾选实时触发更新
async function onSelectionChanged() {
  updateCompareBar();
  if (state.selectedApps.size > 0) {
    await updateInlineTrends(Array.from(state.selectedApps.keys()), true);
  } else {
    await renderMainTrendsChart();
  }
}

function renderTable() {
  els.tableHead.innerHTML =
    "<tr><th class='cb-th' title='勾选多款应用进行同屏对比'><span class='cb-th-label'>对比 (多选)</span></th><th>排名</th><th>应用</th><th>开发者</th><th>分类</th><th>价格</th><th>排名变动</th></tr>";

  // 1. 根据品类与子分类过滤 (支持静态托管即时筛选)
  let rows = state.rows;
  if (state.subcategory) {
    rows = rows.filter((r) => String(r.genre_id) === String(state.subcategory));
  } else if (state.category === "games") {
    rows = rows.filter((r) => {
      const gid = String(r.genre_id || "");
      return gid === "6014" || gid.startsWith("70") || gid === "GAME" || (r.genre_name && r.genre_name.includes("游戏"));
    });
  } else if (state.category === "apps") {
    rows = rows.filter((r) => {
      const gid = String(r.genre_id || "");
      return gid !== "6014" && !gid.startsWith("70") && gid !== "GAME" && (!r.genre_name || !r.genre_name.includes("游戏"));
    });
  }

  // 2. 根据搜索过滤
  const query = state.search;
  rows = rows.filter((row) => {
    if (!query) return true;
    return `${row.name} ${row.developer}`.toLowerCase().includes(query);
  });

  // 3. 根据异动 Tab (Movers & Shakers) 过滤与排序
  if (state.currentTab === "up") {
    rows = rows.filter((r) => r.status === "up" && r.rank_change > 0)
               .sort((a, b) => b.rank_change - a.rank_change);
  } else if (state.currentTab === "new") {
    rows = rows.filter((r) => r.status === "new");
  } else if (state.currentTab === "down") {
    rows = rows.filter((r) => r.status === "down" && r.rank_change < 0)
               .sort((a, b) => a.rank_change - b.rank_change);
  }

  els.tableCount.textContent = `${rows.length} 条记录`;
  els.empty.classList.toggle("hidden", rows.length > 0);

  els.tableBody.innerHTML = rows
    .map((row) => {
      const isChecked = state.selectedApps.has(String(row.app_id)) ? "checked" : "";
      return `
        <tr data-app-id="${row.app_id}" data-app-name="${esc(row.name)}">
          <td class="cb-cell"><input type="checkbox" class="row-checkbox app-select-cb" data-app-id="${row.app_id}" data-app-name="${esc(row.name)}" ${isChecked} title="勾选加入同屏走势对比"></td>
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
          <td class="dev-cell"><a class="dev-link" data-dev="${esc(row.developer)}">${esc(row.developer)}</a></td>
          <td>${esc(row.genre_name)}</td>
          <td class="num">${priceText(row)}</td>
          <td class="num">${badgeFor(row)}</td>
        </tr>`;
    })
    .join("");

  // 绑定行复选框 Checkboxes (勾选即实时刷新图表)
  els.tableBody.querySelectorAll(".app-select-cb").forEach((cb) => {
    cb.addEventListener("click", async (e) => {
      e.stopPropagation();
      const appId = String(cb.dataset.appId);
      const appName = cb.dataset.appName;
      if (cb.checked) {
        if (state.selectedApps.size >= 5) {
          alert("最多可同时选择 5 款应用进行同屏对比！");
          cb.checked = false;
          return;
        }
        state.selectedApps.set(appId, appName);
      } else {
        state.selectedApps.delete(appId);
      }
      await onSelectionChanged();
    });
  });

  // 绑定开发者点击事件 (功能三)
  els.tableBody.querySelectorAll(".dev-link").forEach((link) => {
    link.addEventListener("click", (e) => {
      e.stopPropagation();
      showPublisherMatrix(link.dataset.dev);
    });
  });

  // 点击表格行直接更新右侧趋势面板
  els.tableBody.querySelectorAll("tr[data-app-id]").forEach((tr) => {
    tr.addEventListener("click", (e) => {
      if (e.target.tagName === "INPUT" || e.target.closest(".cb-cell") || e.target.classList.contains("dev-link")) return;
      els.tableBody.querySelectorAll("tr.selected").forEach((r) => r.classList.remove("selected"));
      tr.classList.add("selected");
      updateInlineTrends([tr.dataset.appId], true, tr.dataset.appName);
    });
  });
}

// 主看板内联趋势更新 (右侧分栏)
async function updateInlineTrends(appIds, isCustom = false, singleName = null) {
  if (!appIds || !appIds.length || !els.trendsChart) return;
  setLoading(true);
  try {
    const countryVal = state.country || (els.country ? els.country.value : "") || "us";
    const chartVal = state.chart || (els.chart ? els.chart.value : "") || "free";
    const storeVal = state.store || (els.store ? els.store.value : "") || "app_store";

    const url =
      `/api/trend?app_id=${encodeURIComponent(appIds[0])}&app_ids=${encodeURIComponent(appIds.join(","))}` +
      `&country=${encodeURIComponent(countryVal)}` +
      `&chart=${encodeURIComponent(chartVal)}` +
      `&store=${encodeURIComponent(storeVal)}` +
      filterParams();
    const data = await api(url);

    const countryCode = countryVal ? countryVal.toUpperCase() : "";
    const chartName = (state.meta && state.meta.charts && state.meta.charts[chartVal]) ? state.meta.charts[chartVal] : chartVal;

    if (isCustom) {
      if (els.trendsTitle) {
        els.trendsTitle.textContent = singleName
          ? `📈 ${singleName} · 排名趋势`
          : `📈 竞品对比走势 (${appIds.length} 款应用)`;
      }
      if (els.trendsMeta) {
        els.trendsMeta.textContent = `${countryCode} · ${chartName} · 已选定 ${appIds.length} 款对比视角`;
      }
    } else {
      if (els.trendsTitle) {
        els.trendsTitle.textContent = "📈 榜单趋势";
      }
      if (els.trendsMeta) {
        els.trendsMeta.textContent = `${countryCode} · ${chartName} · 默认显示当前榜单 Top 5 应用大盘走势`;
      }
    }

    renderMultiTrendChart(data, appIds, els.trendsChart);
  } catch (err) {
    console.error("updateInlineTrends error:", err);
    els.trendsChart.innerHTML = '<div class="empty-state">更新榜单趋势失败</div>';
  } finally {
    setLoading(false);
  }
}

// 主看板默认 Top 5 渲染
async function renderMainTrendsChart() {
  if (!state.rows || !state.rows.length) {
    if (els.trendsChart) {
      els.trendsChart.innerHTML = '<div class="empty-state">当前筛选条件下暂无趋势数据</div>';
    }
    return;
  }
  if (state.selectedApps.size > 0) {
    await updateInlineTrends(Array.from(state.selectedApps.keys()), true);
  } else {
    const top5Apps = state.rows.slice(0, 5);
    const appIds = top5Apps.map((r) => String(r.app_id));
    await updateInlineTrends(appIds, false);
  }
}

function buildCubicPath(points) {
  if (!points || points.length < 2) return "";
  if (points.length === 2) return `M ${points[0].x},${points[0].y} L ${points[1].x},${points[1].y}`;
  let d = `M ${points[0].x.toFixed(1)},${points[0].y.toFixed(1)}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i === 0 ? i : i - 1];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2 < points.length ? i + 2 : i + 1];

    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;

    d += ` C ${cp1x.toFixed(1)},${cp1y.toFixed(1)} ${cp2x.toFixed(1)},${cp2y.toFixed(1)} ${p2.x.toFixed(1)},${p2.y.toFixed(1)}`;
  }
  return d;
}

function renderMultiTrendChart(data, appIds, container = els.trendsChart, fallbackMap = null) {
  if (!container) return;
  const muted = getComputedStyle(document.body).getPropertyValue("--muted-foreground").trim() || "#8f99a7";
  const grid = getComputedStyle(document.body).getPropertyValue("--border").trim() || "#29313e";
  const width = 620;
  const height = 310;
  const pad = { top: 32, right: 26, bottom: 45, left: 42 };

  const trendsMap = (data && data.trends) ? data.trends : (data || {});

  // 1. 收集所有日期与最大排名
  const allDatesSet = new Set();
  let maxRank = 30;
  for (const aid of appIds) {
    const key = String(aid);
    const rows = trendsMap[key] || trendsMap[aid] || [];
    for (const r of rows) {
      allDatesSet.add(r.date);
      maxRank = Math.max(maxRank, Number(r.best_rank));
    }
  }
  const dates = Array.from(allDatesSet).sort();
  if (!dates.length) {
    container.innerHTML = "<div class=\"empty-state\">当前筛选条件下暂无历史对比数据</div>";
    return;
  }

  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const range = Math.max(1, maxRank - 1);
  const xAt = (index) =>
    dates.length === 1 ? pad.left + plotW / 2 : pad.left + (index / (dates.length - 1)) * plotW;
  const yAt = (rank) => pad.top + ((rank - 1) / range) * plotH;

  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("role", "img");



  // 2. Y 轴刻度背景虚线
  const rawTicks = maxRank >= 30 ? [1, 10, 20, 30, maxRank] : [1, maxRank];
  const ticks = Array.from(new Set(rawTicks));
  for (const tick of ticks) {
    const y = yAt(tick);
    const line = document.createElementNS(ns, "line");
    line.setAttribute("x1", pad.left);
    line.setAttribute("y1", y);
    line.setAttribute("x2", width - pad.right);
    line.setAttribute("y2", y);
    line.setAttribute("stroke", grid);
    line.setAttribute("stroke-dasharray", "3 4");
    line.setAttribute("opacity", "0.6");
    svg.appendChild(line);

    const text = document.createElementNS(ns, "text");
    text.setAttribute("x", pad.left - 10);
    text.setAttribute("y", y + 4);
    text.setAttribute("text-anchor", "end");
    text.setAttribute("fill", muted);
    text.setAttribute("font-size", "10.5");
    text.setAttribute("font-weight", "500");
    text.textContent = tick;
    svg.appendChild(text);
  }

  const appMetaList = [];

  // 3. 绘制平滑贝塞尔曲线 (Cubic Splines) 与节点 Tag
  appIds.forEach((aid, idx) => {
    const key = String(aid);
    const rows = trendsMap[key] || trendsMap[aid] || [];
    const color = chartColor(idx);
    const dateToRank = new Map(rows.map((r) => [r.date, Number(r.best_rank)]));

    const appName = (rows.length > 0 ? rows[0].name : null) ||
                    state.selectedApps.get(key) ||
                    state.selectedApps.get(aid) ||
                    (fallbackMap ? fallbackMap.get(key) : null) ||
                    `App ${aid}`;

    const group = document.createElementNS(ns, "g");
    group.setAttribute("class", `chart-line-group line-group-${idx}`);

    const points = [];
    dates.forEach((d, dIdx) => {
      if (dateToRank.has(d)) {
        points.push({ x: xAt(dIdx), y: yAt(dateToRank.get(d)), rank: dateToRank.get(d), date: d });
      }
    });

    const appPoints = [];
    points.forEach((p) => {
      appPoints.push({ p, color, group, idx });
    });

    const lastRank = points.length > 0 ? points[points.length - 1].rank : "-";
    appMetaList.push({ key, name: appName, color, lastRank, index: idx, points: appPoints });

    if (points.length > 1) {
      const pathD = buildCubicPath(points);

      // 主折线
      const path = document.createElementNS(ns, "path");
      path.setAttribute("d", pathD);
      path.setAttribute("fill", "none");
      path.setAttribute("stroke", color);
      path.setAttribute("stroke-width", "2.8");
      path.setAttribute("stroke-linecap", "round");
      path.setAttribute("stroke-linejoin", "round");
      group.appendChild(path);
    }
  });

  // 3.5 智能防重叠布局算法 (De-collision Layout Algorithm for Rank Badges)
  const pointsByDate = new Map();
  appMetaList.forEach((meta) => {
    meta.points.forEach((item) => {
      const d = item.p.date;
      if (!pointsByDate.has(d)) pointsByDate.set(d, []);
      pointsByDate.get(d).push(item);
    });
  });

  pointsByDate.forEach((pts) => {
    pts.sort((a, b) => a.p.y - b.p.y);
    pts.forEach((item, pIdx) => {
      const defaultY = item.p.y - 20;
      const overlaps = pts.slice(0, pIdx).some((prev) => Math.abs(prev.labelY - defaultY) < 16);
      if (overlaps) {
        const altY = item.p.y + 7;
        const altOverlaps = pts.slice(0, pIdx).some((prev) => Math.abs(prev.labelY - altY) < 16);
        if (!altOverlaps) {
          item.labelY = altY;
        } else {
          const maxY = Math.max(...pts.slice(0, pIdx).map((prev) => prev.labelY));
          item.labelY = maxY + 16;
        }
      } else {
        item.labelY = defaultY;
      }
    });
  });

  // 3.6 渲染所有节点的外环、内圆及避让后的排名 Pill 标签
  appMetaList.forEach((meta) => {
    meta.points.forEach((item) => {
      const { p, color, group, labelY } = item;

      // 节点外环
      const halo = document.createElementNS(ns, "circle");
      halo.setAttribute("cx", p.x);
      halo.setAttribute("cy", p.y);
      halo.setAttribute("r", "5");
      halo.setAttribute("fill", color);
      group.appendChild(halo);

      // 节点内白圆
      const dot = document.createElementNS(ns, "circle");
      dot.setAttribute("cx", p.x);
      dot.setAttribute("cy", p.y);
      dot.setAttribute("r", "3");
      dot.setAttribute("fill", "#ffffff");
      group.appendChild(dot);

      // 动态计算 Pill 标签宽度 (适应单双三位数)
      const rankStr = `#${p.rank}`;
      const badgeW = rankStr.length <= 2 ? 22 : rankStr.length === 3 ? 26 : 32;
      const badgeH = 15;

      const rect = document.createElementNS(ns, "rect");
      rect.setAttribute("x", p.x - badgeW / 2);
      rect.setAttribute("y", labelY);
      rect.setAttribute("width", badgeW);
      rect.setAttribute("height", badgeH);
      rect.setAttribute("rx", "4");
      rect.setAttribute("ry", "4");
      rect.setAttribute("fill", color);
      group.appendChild(rect);

      // 排名文字
      const rankText = document.createElementNS(ns, "text");
      rankText.setAttribute("x", p.x);
      rankText.setAttribute("y", labelY + 11);
      rankText.setAttribute("text-anchor", "middle");
      rankText.setAttribute("fill", "#ffffff");
      rankText.setAttribute("font-size", "9.5");
      rankText.setAttribute("font-weight", "800");
      rankText.textContent = rankStr;
      group.appendChild(rankText);
    });

    svg.appendChild(meta.points[0].group);
  });

  // 4. X 轴日期刻度
  dates.forEach((d, index) => {
    const cx = xAt(index);
    const dateText = document.createElementNS(ns, "text");
    dateText.setAttribute("x", cx);
    dateText.setAttribute("y", height - 12);
    dateText.setAttribute("text-anchor", "middle");
    dateText.setAttribute("fill", muted);
    dateText.setAttribute("font-size", "10.5");
    dateText.setAttribute("font-weight", "500");
    dateText.textContent = d.slice(5);
    svg.appendChild(dateText);
  });

  container.innerHTML = "";
  container.appendChild(svg);

  // 5. 渲染图表下方的现代化图例卡片网格 (.trends-legend-grid)
  const legendWrap = document.createElement("div");
  legendWrap.className = "trends-legend-grid";
  appMetaList.forEach((item) => {
    const card = document.createElement("div");
    card.className = "trend-legend-card";
    card.dataset.index = item.index;
    card.innerHTML = `
      <span class="legend-dot" style="background:${item.color};"></span>
      <span class="legend-app-name" title="${esc(item.name)}">${esc(item.name)}</span>
      <span class="legend-rank-badge">#${item.lastRank}</span>
    `;

    // 悬浮图例卡片高亮对应折线
    card.addEventListener("mouseenter", () => {
      svg.querySelectorAll(".chart-line-group").forEach((g, i) => {
        g.classList.toggle("dimmed", i !== item.index);
        g.classList.toggle("highlighted", i === item.index);
      });
      card.classList.add("active");
    });
    card.addEventListener("mouseleave", () => {
      svg.querySelectorAll(".chart-line-group").forEach((g) => {
        g.classList.remove("dimmed", "highlighted");
      });
      card.classList.remove("active");
    });

    legendWrap.appendChild(card);
  });
  container.appendChild(legendWrap);
}

// 功能三：开发者矩阵分析 (Publisher Portfolio)
async function showPublisherMatrix(developer) {
  setLoading(true);
  try {
    const url = `/api/publisher?developer=${encodeURIComponent(developer)}&date=${encodeURIComponent(state.date)}&store=${encodeURIComponent(state.store)}`;
    const data = await api(url);
    els.pubTitle.textContent = `${developer} · 产品矩阵`;
    els.pubMeta.textContent = `${data.date} · 共 ${data.apps.length} 款在榜应用`;

    if (!data.apps.length) {
      els.pubContent.innerHTML = "<div class=\"empty-state\">该发行商在当前日期暂无更多榜单记录</div>";
    } else {
      els.pubContent.innerHTML = data.apps
        .map(
          (app) => `
          <div class="pub-card">
            <div class="pub-card-head">
              ${app.icon_url ? `<img class="app-icon" src="${esc(app.icon_url)}" alt="">` : `<span class="app-icon"></span>`}
              <div>
                <div class="pub-card-name">${esc(app.name)}</div>
                <div class="pub-card-id">id: ${esc(app.app_id)}</div>
              </div>
            </div>
            <div class="pub-entry-grid">
              ${app.entries
                .map(
                  (e) => `
                  <div class="pub-entry-item">
                    <span class="pub-entry-country">${esc(e.country.toUpperCase())}</span>
                    <span class="pub-entry-rank">#${e.rank}</span>
                    <div class="pub-entry-chart">${esc(e.chart)} · ${esc(e.genre)}</div>
                  </div>`
                )
                .join("")}
            </div>
          </div>`
        )
        .join("");
    }

    els.pubDrawer.classList.add("open");
    els.pubDrawer.setAttribute("aria-hidden", "false");
    els.drawerMask.classList.remove("hidden");
  } catch (err) {
    console.error("showPublisherMatrix error:", err);
    alert("开启开发者矩阵失败: " + (err.message || err));
  } finally {
    setLoading(false);
  }
}

function closePublisherDrawer() {
  els.pubDrawer.classList.remove("open");
  els.pubDrawer.setAttribute("aria-hidden", "true");
  els.drawerMask.classList.add("hidden");
}

async function showIntelDrawer(tabName = 'attr') {
  const elDrawer = document.getElementById("intel-drawer");
  if (!elDrawer) return;

  const tabAttr = document.getElementById("intel-tab-attr");
  const tabCat = document.getElementById("intel-tab-cat");
  const tabGiants = document.getElementById("intel-tab-giants");
  const panelAttr = document.getElementById("intel-panel-attr");
  const panelCat = document.getElementById("intel-panel-cat");
  const panelGiants = document.getElementById("intel-panel-giants");

  if (tabAttr) tabAttr.classList.toggle("active", tabName === 'attr');
  if (tabCat) tabCat.classList.toggle("active", tabName === 'cat');
  if (tabGiants) tabGiants.classList.toggle("active", tabName === 'giants');

  if (panelAttr) panelAttr.classList.toggle("hidden", tabName !== 'attr');
  if (panelCat) panelCat.classList.toggle("hidden", tabName !== 'cat');
  if (panelGiants) panelGiants.classList.toggle("hidden", tabName !== 'giants');

  if (tabName === 'cat') loadCategoryTrendsData();
  else if (tabName === 'giants') loadCasualGiantsData();
  else loadAttributionData();

  elDrawer.classList.add("open");
  elDrawer.setAttribute("aria-hidden", "false");
  els.drawerMask.classList.remove("hidden");
}

function closeIntelDrawer() {
  const elDrawer = document.getElementById("intel-drawer");
  if (elDrawer) {
    elDrawer.classList.remove("open");
    elDrawer.setAttribute("aria-hidden", "true");
  }
  els.drawerMask.classList.add("hidden");
}

async function loadCasualGiantsData(region = 'all') {
  setLoading(true);
  try {
    const url = `/api/casual-giants?region=${encodeURIComponent(region)}`;
    const res = await api(url);
    const publishers = res.publishers || [];

    const elSub = document.getElementById("intel-drawer-sub");
    if (elSub) {
      elSub.textContent = `🎮 20大休闲巨头动态矩阵 (已追踪 ${res.total} 家核心厂商)`;
    }

    const renderGameItem = (g, badgeCls, badgeText) => `
      <div class="giant-game-item">
        <div class="giant-game-head">
          <span class="giant-game-name">${g.icon || '🎮'} ${esc(g.name)}</span>
          <span class="${badgeCls}">${esc(g.status || badgeText)}</span>
        </div>
        <div style="font-size:10px; color:var(--text-2); margin-top:2px;">
          ${g.release_date ? `发布时间: <code>${esc(g.release_date)}</code> · ` : g.expected_date ? `预计上线: <code>${esc(g.expected_date)}</code> · ` : ''}
          ${esc(g.desc || '')}
        </div>
      </div>`;

    const renderPubCard = (p) => `
      <div class="giant-pub-card">
        <div class="giant-pub-header">
          <div>
            <span class="giant-pub-name">${esc(p.name)}</span>
            <span style="font-size:11px; color:var(--text-3); margin-left:6px;">${esc(p.country)}</span>
          </div>
          <span class="giant-pub-tag">${esc(p.category)}</span>
        </div>
        <div class="giant-pub-desc">${esc(p.desc)}</div>

        <!-- 🟢 已发布经典爆款 -->
        <div class="giant-game-group">
          <div class="giant-game-title">🟢 已发布爆款游戏 (${p.published_games?.length || 0})</div>
          ${(p.published_games || []).map(g => renderGameItem(g, 'game-badge-published', '已发布')).join('')}
        </div>

        <!-- 🚀 近期新发布/热播中 -->
        <div class="giant-game-group">
          <div class="giant-game-title">🚀 近期新发布游戏 (${p.new_games?.length || 0})</div>
          ${(p.new_games || []).map(g => renderGameItem(g, 'game-badge-new', '新发布')).join('')}
        </div>

        <!-- ⏳ 准备发布 / 预预约 / 软发射中 -->
        <div class="giant-game-group">
          <div class="giant-game-title">⏳ 准备发布 / 预预约中 (${p.upcoming_games?.length || 0})</div>
          ${(p.upcoming_games || []).map(g => renderGameItem(g, 'game-badge-upcoming', '准备发布')).join('')}
        </div>
      </div>`;

    const elList = document.getElementById("casual-giants-list");
    if (elList) {
      elList.innerHTML = publishers.length
        ? publishers.map(renderPubCard).join("")
        : '<div class="no-data">暂无厂商数据</div>';
    }
  } catch (err) {
    console.error("loadCasualGiantsData error:", err);
  } finally {
    setLoading(false);
  }
}

async function loadAttributionData() {
  renderQuantSummary();
}

async function loadCategoryTrendsData() {
  setLoading(true);
  try {
    const countryVal = state.country || (els.country ? els.country.value : "") || "us";
    const url = `/api/category-trends?date=${encodeURIComponent(state.date)}&country=${encodeURIComponent(countryVal)}&store=${encodeURIComponent(state.store)}`;
    const data = await api(url);

    const elSub = document.getElementById("intel-drawer-sub");
    if (elSub) {
      elSub.textContent = `${data.country_display || countryVal.toUpperCase()} · 每日品类飙升 Top 3 与 流量回调 Top 3`;
    }

    const renderCategoryCard = (cat) => `
      <div class="attr-card">
        <div class="attr-card-header">
          <div class="attr-card-left">
            <span class="attr-rank-badge" style="width:auto; padding:0 8px; font-size:12px;">TOP ${cat.rank}</span>
            <div class="attr-app-info">
              <div class="attr-app-name" style="font-size:14px; font-weight:700;">${esc(cat.category_name)}</div>
              <div class="attr-app-dev" style="color:var(--accent); font-weight:600;">爆款代表: ${esc((cat.representative_apps || []).join(' / '))}</div>
            </div>
          </div>
          <span class="badge ${cat.badge_cls || 'up'}">${esc(cat.growth_score)}</span>
        </div>

        <div class="attr-summary-box">
          ${esc(cat.summary || '')}
        </div>

        <div style="font-size:11.5px; color:var(--text); background:var(--surface); border:1px solid var(--border); border-left:3.5px solid var(--accent); padding:8px 10px; border-radius:6px; font-weight:600;">
          ${esc(cat.recommendation || '')}
        </div>

        ${cat.news_reports && cat.news_reports.length ? `
          <div class="attr-news-card">
            <div class="attr-news-header">📰 行业深度研究与报道引述</div>
            ${cat.news_reports.map(r => `
              <div class="attr-news-item">
                <a class="attr-news-link" href="${esc(r.url)}" target="_blank" rel="noopener">[${esc(r.platform)}] ${esc(r.title)} ↗</a>
                <div class="attr-news-snippet">${esc(r.snippet)}</div>
              </div>
            `).join('')}
          </div>` : ''}
      </div>`;

    const elRising = document.getElementById("category-rising-list");
    if (elRising) {
      elRising.innerHTML = (data.rising_categories && data.rising_categories.length)
        ? data.rising_categories.map(c => renderCategoryCard(c)).join("")
        : '<div class="no-data">暂无数据</div>';
    }

    const elDeclining = document.getElementById("category-declining-list");
    if (elDeclining) {
      elDeclining.innerHTML = (data.declining_categories && data.declining_categories.length)
        ? data.declining_categories.map(c => renderCategoryCard(c)).join("")
        : '<div class="no-data">暂无数据</div>';
    }
  } catch (err) {
    console.error("loadCategoryTrendsData error:", err);
  } finally {
    setLoading(false);
  }
}

async function init() {
  applyTheme(localStorage.getItem("appstore-theme") || "dark");
  state.store = localStorage.getItem("appstore-store") || "app_store";
  els.store.value = state.store;
  bindEvents();

  setLoading(true);
  try {
    const datesRes = await api("/api/dates");
    state.dates = datesRes.dates;
    if (!state.dates.length) {
      els.empty.classList.remove("hidden");
      return;
    }
    populateDateSelect();
    await loadMeta();
    populateRegionSelect();
    populateCountrySelect();
    populateChartSelect();
    populateCategorySelect();
    populateSubcategorySelect();
    await refresh();
  } finally {
    setLoading(false);
  }
}

document.addEventListener("DOMContentLoaded", init);
