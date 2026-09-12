// CORDIS → SDG Web Prototype
// Client-side execution with static pre-indexed JSON assets.
// Never uses an external API key or backend server.

const SDG_META = {
  1: { name: "No Poverty", color: "#E5243B" },
  2: { name: "Zero Hunger", color: "#DDA63A" },
  3: { name: "Good Health and Well-being", color: "#4C9F38" },
  4: { name: "Quality Education", color: "#C5192D" },
  5: { name: "Gender Equality", color: "#FF3A21" },
  6: { name: "Clean Water and Sanitation", color: "#26BDE2" },
  7: { name: "Affordable and Clean Energy", color: "#FCC30B" },
  8: { name: "Decent Work and Economic Growth", color: "#A21942" },
  9: { name: "Industry, Innovation and Infrastructure", color: "#FD6925" },
  10: { name: "Reduced Inequalities", color: "#DD1367" },
  11: { name: "Sustainable Cities and Communities", color: "#FD9D24" },
  12: { name: "Responsible Consumption and Production", color: "#BF8B2E" },
  13: { name: "Climate Action", color: "#3F7E44" },
  14: { name: "Life Below Water", color: "#0A97D9" },
  15: { name: "Life on Land", color: "#56C02B" },
  16: { name: "Peace, Justice and Strong Institutions", color: "#00689D" },
  17: { name: "Partnerships for the Goals", color: "#19486A" }
};

// Application State
const state = {
  projectsIndex: [],
  filteredProjects: [],
  corpusSummary: null,
  currentPage: 1,
  pageSize: 50,
  searchQuery: "",
  levelFilter: "all",
  sdgFilter: "all",
  bandFilter: "all",
  sortBy: "id-asc",
  loadedShards: new Map() // prefix -> project details map
};

// Initialize Application
document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  setupFilterListeners();
  setupModalListeners();
  setupProjectsTableListeners();
  setupUrlRouting();
  loadStaticData();
});

// Setup Navigation Tabs
function setupTabs() {
  const tabButtons = document.querySelectorAll(".tab-btn");
  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const tabName = btn.dataset.tab;
      switchTab(tabName);
    });
  });

  const headerProvLink = document.getElementById("header-provenance-link");
  if (headerProvLink) {
    headerProvLink.addEventListener("click", (e) => {
      e.preventDefault();
      switchTab("provenance");
    });
  }
}

window.switchTab = switchTab;

function switchTab(tabName) {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

  const targetBtn = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
  const targetPane = document.getElementById(`tab-${tabName}`);

  if (targetBtn && targetPane) {
    targetBtn.classList.add("active");
    targetPane.classList.add("active");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

// Load Search Index and Corpus Summary
async function loadStaticData() {
  try {
    const [summaryRes, indexRes] = await Promise.all([
      fetch("data/corpus_summary.json"),
      fetch("data/projects_index.json")
    ]);

    if (!summaryRes.ok || !indexRes.ok) {
      throw new Error(`Data fetch failed: summary=${summaryRes.status}, index=${indexRes.status}`);
    }

    state.corpusSummary = await summaryRes.json();
    state.projectsIndex = await indexRes.json();

    renderCorpusSummary();
    renderEvaluationMetrics();
    renderSdgDistribution();
    populateSdgFilterDropdown();
    applyFilters();
    checkUrlForProject();
  } catch (err) {
    console.error("Failed to load static prototype data:", err);
    document.getElementById("projects-table-body").innerHTML = `
      <tr>
        <td colspan="6" class="loading-cell" style="color: var(--danger);">
          Failed to load static datasets (<code>data/projects_index.json</code>). Ensure files are generated with <code>python prototype/build_data.py</code>.
        </td>
      </tr>
    `;
  }
}

// Render Summary Stats
function renderCorpusSummary() {
  if (!state.corpusSummary) return;
  const counts = state.corpusSummary.corpus_shape || {};
  document.getElementById("stat-total").textContent = Number(counts.total_projects || 23451).toLocaleString();
  document.getElementById("stat-target").textContent = Number(counts.projects_with_target || 9394).toLocaleString();
  document.getElementById("stat-goal").textContent = Number(counts.projects_goal_level_only || 6882).toLocaleString();
  document.getElementById("stat-none").textContent = Number(counts.projects_unassigned || 7175).toLocaleString();
}

// Render Evaluation Metrics (Condition 1 Guard)
function renderEvaluationMetrics() {
  if (!state.corpusSummary || !state.corpusSummary.validation_metrics) return;
  const vm = state.corpusSummary.validation_metrics;
  const eval100 = vm.evaluation_100 || {};
  const tLevel = eval100.target_level;
  const ceiling = eval100.recall_ceiling;
  const dev50 = vm.development_50;

  if (tLevel) {
    const prec = Number(tLevel.precision).toFixed(3);
    const rec = Number(tLevel.recall).toFixed(3);
    const precEl = document.getElementById("eval-metric-precision");
    if (precEl) precEl.textContent = prec;
    const recEl = document.getElementById("eval-metric-recall");
    if (recEl) recEl.textContent = rec;
    const prosePrecEl = document.getElementById("eval-prose-precision");
    if (prosePrecEl) prosePrecEl.textContent = prec;
  }

  if (ceiling) {
    const ceilVal = Number(ceiling.ceiling).toFixed(3);
    const unreach = ceiling.with_no_evidence_at_any_threshold;
    const totalPairs = ceiling.reference_pairs;
    const pairStr = `${unreach} of ${totalPairs}`;

    const ceilEl = document.getElementById("eval-metric-ceiling");
    if (ceilEl) ceilEl.textContent = ceilVal;
    const pairsEl = document.getElementById("eval-metric-ceiling-unreachable");
    if (pairsEl) pairsEl.textContent = `${pairStr} reference pairs`;

    const proseCeilEl = document.getElementById("eval-prose-ceiling");
    if (proseCeilEl) proseCeilEl.textContent = ceilVal;
    const prosePairsEl = document.getElementById("eval-prose-unreachable-pairs");
    if (prosePairsEl) prosePairsEl.textContent = pairStr;
    const figCeilEl = document.getElementById("fig-caption-ceiling");
    if (figCeilEl) figCeilEl.textContent = ceilVal;
    const figPairsEl = document.getElementById("fig-caption-unreachable");
    if (figPairsEl) figPairsEl.textContent = pairStr;
  }

  if (dev50) {
    const kappaVal = Number(dev50.cohens_kappa).toFixed(3);
    const kappaEl = document.getElementById("eval-metric-kappa");
    if (kappaEl) kappaEl.textContent = kappaVal;
    const proseKappaEl = document.getElementById("eval-prose-kappa");
    if (proseKappaEl) proseKappaEl.textContent = kappaVal;
    const reproKappaEl = document.getElementById("eval-repro-kappa");
    if (reproKappaEl) reproKappaEl.textContent = kappaVal;
  }



  if (tLevel && ceiling) {
    const reproMetricsEl = document.getElementById("eval-repro-metrics");
    if (reproMetricsEl) {
      reproMetricsEl.textContent = `P=${Number(tLevel.precision).toFixed(3)}, R=${Number(tLevel.recall).toFixed(3)}, Ceiling=${Number(ceiling.ceiling).toFixed(3)}`;
    }
  }
}

// Populate SDG Dropdown Filter
function populateSdgFilterDropdown() {
  const select = document.getElementById("sdg-filter");
  for (let i = 1; i <= 17; i++) {
    const opt = document.createElement("option");
    opt.value = String(i);
    opt.textContent = `SDG ${i}: ${SDG_META[i]?.name || ""}`;
    select.appendChild(opt);
  }
}

// Setup Event Listeners
function setupFilterListeners() {
  const searchInput = document.getElementById("search-input");
  const clearSearchBtn = document.getElementById("clear-search-btn");
  const levelFilter = document.getElementById("level-filter");
  const sdgFilter = document.getElementById("sdg-filter");
  const bandFilter = document.getElementById("band-filter");
  const sortSelect = document.getElementById("sort-select");
  const pageSizeSelect = document.getElementById("page-size-select");
  const resetBtn = document.getElementById("reset-filters-btn");

  let debounceTimer = null;
  searchInput.addEventListener("input", (e) => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      state.searchQuery = e.target.value.trim().toLowerCase();
      state.currentPage = 1;
      applyFilters();
    }, 180);
  });

  clearSearchBtn.addEventListener("click", () => {
    searchInput.value = "";
    state.searchQuery = "";
    state.currentPage = 1;
    applyFilters();
  });

  levelFilter.addEventListener("change", (e) => {
    state.levelFilter = e.target.value;
    state.currentPage = 1;
    applyFilters();
  });

  sdgFilter.addEventListener("change", (e) => {
    state.sdgFilter = e.target.value;
    state.currentPage = 1;
    applyFilters();
  });

  bandFilter.addEventListener("change", (e) => {
    state.bandFilter = e.target.value;
    state.currentPage = 1;
    applyFilters();
  });

  sortSelect.addEventListener("change", (e) => {
    state.sortBy = e.target.value;
    applyFilters();
  });

  pageSizeSelect.addEventListener("change", (e) => {
    state.pageSize = parseInt(e.target.value, 10);
    state.currentPage = 1;
    renderProjectsTable();
  });

  resetBtn.addEventListener("click", resetAllFilters);

  // Quick Presets
  document.querySelectorAll(".preset-btn[data-preset]").forEach(btn => {
    btn.addEventListener("click", () => {
      const preset = btn.dataset.preset;
      applyPreset(preset);
    });
  });

  // Stat Card click filtering
  document.getElementById("card-target").addEventListener("click", () => {
    levelFilter.value = "target";
    state.levelFilter = "target";
    state.currentPage = 1;
    applyFilters();
  });
  document.getElementById("card-goal").addEventListener("click", () => {
    levelFilter.value = "goal_only";
    state.levelFilter = "goal_only";
    state.currentPage = 1;
    applyFilters();
  });
  document.getElementById("card-none").addEventListener("click", () => {
    levelFilter.value = "none";
    state.levelFilter = "none";
    state.currentPage = 1;
    applyFilters();
  });
  document.getElementById("card-total").addEventListener("click", resetAllFilters);
}

function applyPreset(preset) {
  resetAllFilters(false);
  const searchInput = document.getElementById("search-input");
  const levelSelect = document.getElementById("level-filter");
  const bandSelect = document.getElementById("band-filter");

  if (preset === "hyphen-titles") {
    // Binding Rule 1: Audit hyphen-leading titles (101073045, 101275778)
    searchInput.value = "101073045";
    state.searchQuery = "101073045";
  } else if (preset === "sample") {
    searchInput.value = "10103";
    state.searchQuery = "10103";
  } else if (preset === "high-band") {
    bandSelect.value = "high";
    state.bandFilter = "high";
  } else if (preset === "unassigned") {
    levelSelect.value = "none";
    state.levelFilter = "none";
  }

  state.currentPage = 1;
  applyFilters();
}

function resetAllFilters(reapply = true) {
  state.searchQuery = "";
  state.levelFilter = "all";
  state.sdgFilter = "all";
  state.bandFilter = "all";
  state.sortBy = "id-asc";
  state.currentPage = 1;

  document.getElementById("search-input").value = "";
  document.getElementById("level-filter").value = "all";
  document.getElementById("sdg-filter").value = "all";
  document.getElementById("band-filter").value = "all";
  document.getElementById("sort-select").value = "id-asc";

  if (reapply) applyFilters();
}

// Filter and Sort Engine
function applyFilters() {
  const query = state.searchQuery;
  const level = state.levelFilter;
  const sdg = state.sdgFilter;
  const band = state.bandFilter;

  state.filteredProjects = state.projectsIndex.filter(p => {
    // Level filter
    if (level !== "all" && p.level !== level) {
      return false;
    }

    // SDG Goal filter
    if (sdg !== "all") {
      if (!p.goals || !p.goals.includes(sdg)) {
        return false;
      }
    }

    // Band filter
    if (band !== "all") {
      if (p.band !== band) {
        return false;
      }
    }

    // Search query filter (Project ID, Acronym, Title)
    if (query) {
      const matchId = p.id.toLowerCase().includes(query);
      const matchAcronym = p.acronym && p.acronym.toLowerCase().includes(query);
      const matchTitle = p.title && p.title.toLowerCase().includes(query);
      if (!matchId && !matchAcronym && !matchTitle) {
        return false;
      }
    }

    return true;
  });

  // Sort
  sortProjects(state.filteredProjects, state.sortBy);
  renderProjectsTable();
}

function sortProjects(list, sortBy) {
  list.sort((a, b) => {
    if (sortBy === "id-asc") {
      return a.id.localeCompare(b.id);
    } else if (sortBy === "id-desc") {
      return b.id.localeCompare(a.id);
    } else if (sortBy === "acronym-asc") {
      return (a.acronym || "").localeCompare(b.acronym || "");
    }
    return 0;
  });
}

// Render Projects Table & Pagination
function renderProjectsTable() {
  const tbody = document.getElementById("projects-table-body");
  const countEl = document.getElementById("results-count");
  const total = state.filteredProjects.length;

  if (total === 0) {
    countEl.textContent = "0 projects match the selected criteria";
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="loading-cell">No matching projects found. Try clearing or relaxing filters.</td>
      </tr>
    `;
    renderPagination(0);
    return;
  }

  const startIdx = (state.currentPage - 1) * state.pageSize;
  const endIdx = Math.min(startIdx + state.pageSize, total);
  const pageItems = state.filteredProjects.slice(startIdx, endIdx);

  countEl.textContent = `Showing ${startIdx + 1}–${endIdx} of ${total.toLocaleString()} projects (${(total / 23451 * 100).toFixed(1)}% of corpus)`;

  let html = "";
  pageItems.forEach(p => {
    const levelClass = p.level === "target" ? "badge-target" : (p.level === "goal_only" ? "badge-goal" : "badge-none");
    const levelText = p.level === "target" ? "Target" : (p.level === "goal_only" ? "Goal Only" : "Unassigned");
    const bandClass = p.band === "high" ? "band-high" : (p.band === "medium" ? "band-medium" : (p.band === "low" ? "band-low" : "band-none"));
    const bandText = p.band && p.band !== "none" ? p.band : "&mdash;";

    // Render SDG chips
    let sdgsHtml = "";
    if (p.goals && p.goals.length > 0) {
      sdgsHtml = p.goals.map(s => {
        const goalNum = parseInt(s, 10);
        const color = SDG_META[goalNum]?.color || "#64748b";
        return `<span class="sdg-chip" style="background-color: ${color};">SDG ${s}</span>`;
      }).join("");
    } else {
      sdgsHtml = `<span style="color: var(--text-muted); font-size: 0.75rem;">None</span>`;
    }

    // Preserve hyphen-leading titles (Binding Rule 1): escapeHtml safely encodes for HTML display without altering characters
    const safeTitle = escapeHtml(p.title || "");
    const safeAcronym = escapeHtml(p.acronym || "");

    html += `
      <tr class="project-row" tabindex="0" data-project-id="${p.id}" role="button" aria-label="Inspect project ${p.id}: ${safeAcronym}">
        <td class="col-id"><a href="https://cordis.europa.eu/project/id/${p.id}" target="_blank" rel="noopener" class="cordis-outbound-link mono" title="Open CORDIS project record ${p.id} (external site, opens in new tab)" aria-label="Open project ${p.id} on CORDIS (leaves site)">${p.id}&nbsp;<span class="external-icon">&nearr;</span></a></td>
        <td class="col-acronym">${safeAcronym}</td>
        <td class="col-title"><a href="#project=${p.id}" class="project-title-link" tabindex="-1">${safeTitle}</a></td>
        <td class="col-level"><span class="badge-level ${levelClass}">${levelText}</span></td>
        <td class="col-sdgs">${sdgsHtml}</td>
        <td class="col-band"><span class="badge-band ${bandClass}">${bandText}</span></td>
      </tr>
    `;
  });

  tbody.innerHTML = html;
  renderPagination(total);
}

function renderPagination(total) {
  const totalPages = Math.ceil(total / state.pageSize) || 1;
  const current = state.currentPage;

  const topPag = document.getElementById("top-pagination");
  const bottomPag = document.getElementById("bottom-pagination");

  if (totalPages <= 1) {
    topPag.innerHTML = "";
    bottomPag.innerHTML = "";
    return;
  }

  let pagHtml = `
    <button class="page-btn" ${current === 1 ? "disabled" : ""} onclick="changePage(1)">&laquo;</button>
    <button class="page-btn" ${current === 1 ? "disabled" : ""} onclick="changePage(${current - 1})">&lsaquo; Prev</button>
    <span style="font-size: 0.8rem; font-weight: 600; padding: 0 0.5rem;">Page ${current} of ${totalPages}</span>
    <button class="page-btn" ${current === totalPages ? "disabled" : ""} onclick="changePage(${current + 1})">Next &rsaquo;</button>
    <button class="page-btn" ${current === totalPages ? "disabled" : ""} onclick="changePage(${totalPages})">&raquo;</button>
  `;

  topPag.innerHTML = pagHtml;
  bottomPag.innerHTML = pagHtml;
}

window.changePage = function(page) {
  state.currentPage = page;
  renderProjectsTable();
  window.scrollTo({ top: 380, behavior: "smooth" });
};

// Project Detail Modal
function setupModalListeners() {
  const backdrop = document.getElementById("project-modal-backdrop");
  const closeBtn = document.getElementById("modal-close-btn");

  closeBtn.addEventListener("click", closeProjectModal);
  backdrop.addEventListener("click", (e) => {
    if (e.target === backdrop) closeProjectModal();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && backdrop.classList.contains("open")) {
      closeProjectModal();
    }
  });
}

function closeProjectModal() {
  document.getElementById("project-modal-backdrop").classList.remove("open");
  if (window.location.hash.startsWith("#project")) {
    try {
      history.replaceState(null, "", window.location.pathname + window.location.search);
    } catch (_) {
      window.location.hash = "";
    }
  }
}

window.openProjectModal = async function(projectId) {
  const targetHash = `#project=${projectId}`;
  if (window.location.hash !== targetHash) {
    try {
      history.replaceState(null, "", targetHash);
    } catch (_) {
      window.location.hash = targetHash;
    }
  }

  const backdrop = document.getElementById("project-modal-backdrop");
  const bodyEl = document.getElementById("modal-body");

  backdrop.classList.add("open");
  bodyEl.innerHTML = `<div class="modal-loading">Fetching project details from shard...</div>`;

  try {
    const project = await fetchProjectDetail(projectId);
    if (!project) {
      bodyEl.innerHTML = `<div class="modal-loading" style="color: var(--danger);">Project ${projectId} not found in shard.</div>`;
      return;
    }

    renderProjectDetail(project);
  } catch (err) {
    console.error("Error fetching project detail:", err);
    bodyEl.innerHTML = `<div class="modal-loading" style="color: var(--danger);">Failed to load details for project ${projectId}.</div>`;
  }
};

async function fetchProjectDetail(projectId) {
  const prefix = projectId.slice(0, 5);
  if (state.loadedShards.has(prefix)) {
    return state.loadedShards.get(prefix)[projectId];
  }

  const res = await fetch(`data/projects/${prefix}.json`);
  if (!res.ok) throw new Error(`Shard ${prefix}.json failed to load`);
  const shardData = await res.json();
  state.loadedShards.set(prefix, shardData);
  return shardData[projectId];
}

function renderProjectDetail(project) {
  const modalIdEl = document.getElementById("modal-project-id");
  if (modalIdEl) {
    modalIdEl.href = `https://cordis.europa.eu/project/id/${project.id}`;
    modalIdEl.target = "_blank";
    modalIdEl.rel = "noopener";
    modalIdEl.title = `Open CORDIS project record ${project.id} on cordis.europa.eu (external site, opens in new tab)`;
    modalIdEl.setAttribute("aria-label", `Open project ${project.id} on CORDIS (leaves site)`);
    modalIdEl.innerHTML = `Project ${project.id}&nbsp;<span class="external-icon">&nearr;</span>`;
  }
  document.getElementById("modal-project-acronym").textContent = project.acronym || "NO ACRONYM";

  // Binding Rule 1: Hyphen-leading titles (101073045, 101275778) preserved without escaping
  document.getElementById("modal-project-title").textContent = project.title;

  const levelBadge = document.getElementById("modal-level-badge");
  const hasTarget = project.assignments && project.assignments.some(a => a.level === "target");
  const hasGoal = project.assignments && project.assignments.length > 0;
  const levelClass = hasTarget ? "badge-target" : (hasGoal ? "badge-goal" : "badge-none");
  const levelText = hasTarget ? "Target-Level Assigned" : (hasGoal ? "Goal-Only Assigned" : "Unassigned");
  levelBadge.className = `badge-level ${levelClass}`;
  levelBadge.textContent = levelText;

  const bodyEl = document.getElementById("modal-body");

  // Binding Rule 3: Prominently surface sources_present vs sources_absent
  const presentList = project.sources_present || [];
  const absentList = project.sources_absent || [];

  const presentPills = presentList.length > 0
    ? presentList.map(s => `<span class="source-pill-present">${escapeHtml(s)}</span>`).join("")
    : `<span style="font-size: 0.75rem; color: var(--text-muted);">None</span>`;

  const absentPills = absentList.length > 0
    ? absentList.map(s => `<span class="source-pill-absent">${escapeHtml(s)}</span>`).join("")
    : `<span style="font-size: 0.75rem; color: var(--text-muted);">None</span>`;

  const sourcesBoxHtml = `
    <div class="sources-comparison-box">
      <div class="sources-comparison-title">CORDIS Source Field Coverage</div>
      <div class="sources-cols">
        <div>
          <div class="sources-col-label sources-present-label">&check; Sources Present in CORDIS Record:</div>
          <div class="pill-list">${presentPills}</div>
        </div>
        <div>
          <div class="sources-col-label sources-absent-label">&empty; Sources Absent in CORDIS Record:</div>
          <div class="pill-list">${absentPills}</div>
        </div>
      </div>
      <div class="sources-caption">
        Surfaced prominently to distinguish between fields that contained text but matched no SDG vocabulary vs. fields entirely absent in the raw CORDIS project payload.
      </div>
    </div>
  `;

  // Binding Rule 2: Explanation & Prompt SHA-256 Section 3.7 Parked Status Marker
  const explanationText = project.explanation_marker || "";
  const promptHash = project.prompt_marker || "";

  const parkedMarkerHtml = `
    <div class="parked-marker-box">
      <div class="parked-marker-header">
        <span>Parked Status Marker</span>
      </div>
      <div class="parked-marker-text">
        Model explanation generation parked under methodology specification: <code>${escapeHtml(explanationText)}</code>
      </div>
      <div class="parked-marker-hash">
        Prompt Marker: <code>${escapeHtml(promptHash)}</code>
      </div>
    </div>
  `;

  // If Unassigned
  if (!project.assignments || project.assignments.length === 0) {
    bodyEl.innerHTML = `
      ${sourcesBoxHtml}
      <div class="unassigned-notice">
        <h3>No SDG Targets or Goals Assigned</h3>
        <p>This project did not reach the calibrated relevance scoring threshold for any of the 169 SDG targets or 17 goals.</p>
        <p style="margin-top: 0.6rem; font-size: 0.8rem; color: var(--text-muted);">
          30.6% of the Horizon Europe corpus (7,175 projects) is unassigned by design to prevent spurious or false-positive topic attribution.
        </p>
      </div>
      ${parkedMarkerHtml}
    `;
    return;
  }

  let html = sourcesBoxHtml;
  html += `<h3 style="font-size: 1rem; font-weight: 700; margin-bottom: 1rem; color: var(--text-secondary);">
    Assigned SDGs &amp; Multi-Field Evidence (${project.assignments.length} total)
  </h3>`;

  project.assignments.forEach((a, idx) => {
    const goalNum = parseInt(a.goal_uri.split("/").pop(), 10) || 0;
    const goalMeta = SDG_META[goalNum] || { name: `SDG ${goalNum}`, color: "#0284c7" };
    const targetNum = a.target_uri.split("/").pop();
    const scoreVal = a.score !== null && a.score !== undefined ? Number(a.score).toFixed(2) : "N/A";
    const bandClass = a.confidence_band === "high" ? "band-high" : (a.confidence_band === "medium" ? "band-medium" : "band-low");

    html += `
      <div class="detail-assignment-card">
        <div class="assignment-header">
          <div class="assignment-target-title">
            <span class="sdg-num-badge" style="background-color: ${goalMeta.color}; margin-right: 0.4rem;">
              SDG ${goalNum}
            </span>
            Target ${escapeHtml(targetNum)}
          </div>
          <div class="assignment-scores">
            <span class="badge-band ${bandClass}">Confidence: ${a.confidence_band}</span>
            <span class="score-badge">Score: ${scoreVal}</span>
          </div>
        </div>

        <div class="assignment-body">
          <div style="font-size: 0.9rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.4rem;">
            ${escapeHtml(a.target_label || a.goal_label || "")}
          </div>

          <div class="evidence-section" style="margin-top: 0.6rem;">
            <div class="evidence-label">Matched Vocabulary &amp; Field Evidence:</div>
            <div class="evidence-block">${escapeHtml(a.evidence || "No evidence text recorded")}</div>
          </div>

          <div style="margin-top: 0.75rem; font-size: 0.75rem; color: var(--text-muted); display: flex; gap: 1rem; flex-wrap: wrap;">
            <span>Target URI: <code class="mono">${escapeHtml(a.target_uri)}</code></span>
            <span>Goal URI: <code class="mono">${escapeHtml(a.goal_uri)}</code></span>
            <span>Level: <code>${escapeHtml(a.level)}</code></span>
          </div>
        </div>
      </div>
    `;
  });

  html += parkedMarkerHtml;
  bodyEl.innerHTML = html;
}

// Render SDG Distribution View
function renderSdgDistribution() {
  if (!state.corpusSummary) return;
  const grid = document.getElementById("sdg-grid");
  const goalsData = (state.corpusSummary.distributions && state.corpusSummary.distributions.goals) || [];

  let html = "";
  for (let i = 1; i <= 17; i++) {
    const goalData = goalsData.find(g => String(g.goal_id) === String(i));
    const count = goalData ? goalData.projects : 0;
    const pct = (count / 23451 * 100).toFixed(1);
    const meta = SDG_META[i] || { name: `SDG ${i}`, color: "#0284c7" };

    html += `
      <div class="sdg-card" onclick="inspectSdg(${i})">
        <div class="sdg-card-bar" style="background-color: ${meta.color};"></div>
        <div class="sdg-card-header">
          <span class="sdg-num-badge" style="background-color: ${meta.color};">Goal ${i}</span>
          <span class="sdg-count-badge">${Number(count).toLocaleString()} Projects</span>
        </div>
        <div class="sdg-card-title">${meta.name}</div>
        <div class="sdg-card-pct">${pct}% of analyzed corpus</div>
      </div>
    `;
  }

  grid.innerHTML = html;
}

window.inspectSdg = function(goalNum) {
  const breakdownCard = document.getElementById("target-breakdown-card");
  const titleEl = document.getElementById("target-breakdown-title");
  const bodyEl = document.getElementById("target-breakdown-body");
  const filterBtn = document.getElementById("filter-by-selected-sdg-btn");
  const closeBtn = document.getElementById("close-target-breakdown-btn");

  const meta = SDG_META[goalNum];
  const goalsData = (state.corpusSummary.distributions && state.corpusSummary.distributions.goals) || [];
  const goalObj = goalsData.find(g => String(g.goal_id) === String(goalNum));
  const count = goalObj ? goalObj.projects : 0;

  titleEl.innerHTML = `<span class="sdg-num-badge" style="background-color: ${meta.color}; margin-right: 0.5rem;">Goal ${goalNum}</span> ${meta.name} &bull; ${Number(count).toLocaleString()} Projects`;

  filterBtn.onclick = () => {
    document.getElementById("sdg-filter").value = String(goalNum);
    state.sdgFilter = String(goalNum);
    switchTab("explorer");
    applyFilters();
  };

  closeBtn.onclick = () => {
    breakdownCard.style.display = "none";
  };

  const allTargets = (state.corpusSummary.distributions && state.corpusSummary.distributions.most_linked_targets) || [];
  const targets = allTargets.filter(t => t.key.startsWith(`${goalNum}.`));
  if (targets.length === 0) {
    bodyEl.innerHTML = `<p style="color: var(--text-secondary); font-size: 0.9rem; padding: 0.5rem 0;">
      Broad goal-level mappings. Click below to explore all projects assigned to SDG ${goalNum}.
    </p>`;
  } else {
    const maxCount = Math.max(...targets.map(t => t.count), 1);
    let tableHtml = `
      <table class="targets-table">
        <thead>
          <tr>
            <th style="width: 140px;">Target</th>
            <th style="width: 120px; text-align: right;">Projects</th>
            <th class="bar-cell">Corpus Relative Frequency</th>
          </tr>
        </thead>
        <tbody>
    `;

    targets.forEach(t => {
      const pctBar = (t.count / maxCount * 100).toFixed(1);
      tableHtml += `
        <tr>
          <td><strong class="mono">Target ${escapeHtml(t.key)}</strong></td>
          <td style="text-align: right;" class="mono font-bold">${Number(t.count).toLocaleString()}</td>
          <td class="bar-cell">
            <div class="progress-bar-bg">
              <div class="progress-bar-fill" style="width: ${pctBar}%; background-color: ${meta.color};"></div>
            </div>
          </td>
        </tr>
      `;
    });

    tableHtml += `</tbody></table>`;
    bodyEl.innerHTML = tableHtml;
  }

  breakdownCard.style.display = "block";
  breakdownCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
};

// HTML Escaping Helper (preserves hyphen-leading titles)
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Projects Table Row Interactions (Reachable by Tab & Enter, Click anywhere, Middle-click in new tab)
function setupProjectsTableListeners() {
  const tbody = document.getElementById("projects-table-body");
  if (!tbody) return;

  function getRowProjectId(target) {
    const row = target.closest("tr.project-row");
    return row ? row.dataset.projectId : null;
  }

  // Left-click (or modifier click) anywhere on the row
  tbody.addEventListener("click", (e) => {
    // Direct click on outbound CORDIS link navigates externally in new tab without opening modal
    if (e.target.closest(".cordis-outbound-link")) {
      return;
    }

    const projectId = getRowProjectId(e.target);
    if (!projectId) return;

    if (e.ctrlKey || e.metaKey || e.shiftKey) {
      e.preventDefault();
      const url = new URL(window.location.href);
      url.hash = `project=${projectId}`;
      window.open(url.href, "_blank");
      return;
    }

    e.preventDefault();
    openProjectModal(projectId);
  });

  // Middle-click (auxclick with button 1) anywhere on the row opens project in new tab
  tbody.addEventListener("auxclick", (e) => {
    if (e.button !== 1) return;
    if (e.target.closest(".cordis-outbound-link")) {
      return;
    }
    const projectId = getRowProjectId(e.target);
    if (!projectId) return;

    e.preventDefault();
    const url = new URL(window.location.href);
    url.hash = `project=${projectId}`;
    window.open(url.href, "_blank");
  });

  // Keyboard navigation: Enter or Space on focused row opens inspector
  tbody.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      if (e.target.closest(".cordis-outbound-link")) {
        return;
      }
      const projectId = getRowProjectId(e.target);
      if (!projectId) return;

      e.preventDefault();
      openProjectModal(projectId);
    }
  });
}

function checkUrlForProject() {
  const hashMatch = window.location.hash.match(/#project[=-]([0-9a-zA-Z]+)/);
  const searchMatch = new URLSearchParams(window.location.search).get("project");
  const projectId = searchMatch || (hashMatch ? hashMatch[1] : null);
  if (projectId) {
    openProjectModal(projectId);
  }
}

function setupUrlRouting() {
  window.addEventListener("hashchange", () => {
    if (window.location.hash === "#provenance" || window.location.hash === "#tab-provenance") {
      switchTab("provenance");
      return;
    }
    const hashMatch = window.location.hash.match(/#project[=-]([0-9a-zA-Z]+)/);
    if (hashMatch) {
      openProjectModal(hashMatch[1]);
    } else {
      const backdrop = document.getElementById("project-modal-backdrop");
      if (backdrop && backdrop.classList.contains("open")) {
        closeProjectModal();
      }
    }
  });

  window.addEventListener("popstate", () => {
    checkUrlForProject();
  });
}
