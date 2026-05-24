/**
 * FIFA World Cup 2026 — Winner Predictor Dashboard
 * Interactive JavaScript: Charts, Tables, H2H Simulator, Modals
 */

// ── State ─────────────────────────────────────────────────────────────────
let DATA = null;          // Parsed predictions.json
let allTeamsChart = null;
let h2hChart = null;
let eloHistChart = null;

// Team → flag emoji mapping
const FLAGS = {
  "Mexico":                "🇲🇽", "South Africa":           "🇿🇦", "South Korea":  "🇰🇷",
  "Czechia":               "🇨🇿", "Canada":                 "🇨🇦", "Bosnia and Herzegovina": "🇧🇦",
  "Qatar":                 "🇶🇦", "Switzerland":            "🇨🇭", "Brazil":       "🇧🇷",
  "Morocco":               "🇲🇦", "Haiti":                  "🇭🇹", "Scotland":     "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
  "United States":         "🇺🇸", "Paraguay":               "🇵🇾", "Australia":    "🇦🇺",
  "Türkiye":               "🇹🇷", "Germany":                "🇩🇪", "Curaçao":      "🇨🇼",
  "Ivory Coast":           "🇨🇮", "Ecuador":                "🇪🇨", "Netherlands":  "🇳🇱",
  "Japan":                 "🇯🇵", "Sweden":                 "🇸🇪", "Tunisia":      "🇹🇳",
  "Belgium":               "🇧🇪", "Egypt":                  "🇪🇬", "Iran":         "🇮🇷",
  "New Zealand":           "🇳🇿", "Spain":                  "🇪🇸", "Cape Verde":   "🇨🇻",
  "Saudi Arabia":          "🇸🇦", "Uruguay":                "🇺🇾", "France":       "🇫🇷",
  "Senegal":               "🇸🇳", "Iraq":                   "🇮🇶", "Norway":       "🇳🇴",
  "Argentina":             "🇦🇷", "Algeria":                "🇩🇿", "Austria":      "🇦🇹",
  "Jordan":                "🇯🇴", "Portugal":               "🇵🇹", "DR Congo":     "🇨🇩",
  "Uzbekistan":            "🇺🇿", "Colombia":               "🇨🇴", "England":      "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
  "Croatia":               "🇭🇷", "Ghana":                  "🇬🇭", "Panama":       "🇵🇦",
};

const GROUP_COLORS = {
  A:"#4fa3f7", B:"#34d399", C:"#f5c842", D:"#f472b6",
  E:"#a78bfa", F:"#fb923c", G:"#f87171", H:"#38bdf8",
  I:"#4ade80", J:"#fbbf24", K:"#c084fc", L:"#f9a8d4",
};

const ELO_LINE_COLORS = [
  "#f5c842","#4fa3f7","#34d399","#f472b6","#a78bfa","#fb923c","#f87171","#38bdf8","#60a5fa","#86efac"
];

// ── Utilities ────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const flag = team => FLAGS[team] || "🏳️";

function pctColor(pct, max) {
  const ratio = pct / (max || 1);
  if (ratio > 0.6) return "#f5c842";
  if (ratio > 0.3) return "#4fa3f7";
  if (ratio > 0.1) return "#34d399";
  return "#8b9cbf";
}

function heatWidth(val, maxVal) {
  return Math.round((val / (maxVal || 1)) * 100);
}

// ── Data Loading ─────────────────────────────────────────────────────────
async function loadData() {
  try {
    // Try relative path from web/ folder
    let resp = await fetch("../output/predictions.json");
    if (!resp.ok) resp = await fetch("./output/predictions.json");
    if (!resp.ok) throw new Error("Not found");
    DATA = await resp.json();
    initDashboard();
  } catch (e) {
    $("loadingOverlay").classList.add("hidden");
    $("errorOverlay").classList.remove("hidden");
  }
}

// ── Init ──────────────────────────────────────────────────────────────────
function initDashboard() {
  $("loadingOverlay").classList.add("hidden");
  $("mainContent").style.display = "block";

  // Header meta
  $("simCount").textContent = `${(DATA.meta.n_simulations || 50000).toLocaleString()} simulations`;
  $("teamCount").textContent = `${DATA.meta.num_teams || 48} teams`;
  $("lastUpdated").textContent = DATA.meta.generated_at
    ? "Generated " + new Date(DATA.meta.generated_at).toLocaleDateString()
    : "Ready";

  const teams = Object.values(DATA.predictions);
  const maxChamp = Math.max(...teams.map(t => t.champion_pct));

  buildPodium(teams, maxChamp);
  buildAllTeamsChart(teams, "champion", "all");
  buildProbTable(teams);
  buildH2HSimulator(teams);
  buildEloHistory();
  buildGroups(teams, maxChamp);
  populateFilterGroups();
  attachEvents(teams, maxChamp);
}

// ── Podium ────────────────────────────────────────────────────────────────
function buildPodium(teams, maxChamp) {
  const top5 = [...teams].sort((a, b) => b.champion_pct - a.champion_pct).slice(0, 5);
  const grid = $("podiumGrid");
  grid.innerHTML = "";

  top5.forEach((t, i) => {
    const rank = i + 1;
    const barPct = (t.champion_pct / maxChamp * 100).toFixed(1);
    const card = document.createElement("div");
    card.className = `podium-card rank-${rank}`;
    card.innerHTML = `
      <div class="podium-rank">#${rank}</div>
      <span class="podium-flag">${flag(t.team)}</span>
      <div class="podium-team">${t.team}</div>
      <div class="podium-group">Group ${t.group}</div>
      <div class="podium-pct">${t.champion_pct.toFixed(2)}%</div>
      <div class="podium-label">chance to win</div>
      <div class="podium-bar-wrap">
        <div class="podium-bar-fill" style="width:0%" data-target="${barPct}%"></div>
      </div>
      <div class="podium-elo">ELO: ${t.elo}</div>
    `;
    card.addEventListener("click", () => openTeamModal(t));
    grid.appendChild(card);
  });

  // Animate bars after paint
  requestAnimationFrame(() => {
    document.querySelectorAll(".podium-bar-fill").forEach(el => {
      el.style.width = el.dataset.target;
    });
  });
}

// ── All Teams Chart ───────────────────────────────────────────────────────
function buildAllTeamsChart(teams, sortBy = "champion", filterGroup = "all") {
  let filtered = filterGroup === "all" ? [...teams]
    : teams.filter(t => t.group === filterGroup);

  filtered.sort((a, b) =>
    sortBy === "elo" ? b.elo - a.elo
    : sortBy === "group" ? a.group.localeCompare(b.group) || b.champion_pct - a.champion_pct
    : b.champion_pct - a.champion_pct
  );

  const labels   = filtered.map(t => `${flag(t.team)} ${t.team}`);
  const champPct = filtered.map(t => t.champion_pct);
  const colors   = filtered.map(t => GROUP_COLORS[t.group] || "#4fa3f7");

  const ctx = $("allTeamsChart").getContext("2d");
  if (allTeamsChart) allTeamsChart.destroy();

  allTeamsChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Championship %",
        data: champPct,
        backgroundColor: colors.map(c => c + "88"),
        borderColor: colors,
        borderWidth: 1.5,
        borderRadius: 4,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      onClick: (e, elements) => {
        if (elements.length) {
          const idx = elements[0].index;
          openTeamModal(filtered[idx]);
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#111927",
          borderColor: "rgba(255,255,255,0.1)",
          borderWidth: 1,
          titleColor: "#f0f4ff",
          bodyColor: "#8b9cbf",
          callbacks: {
            title: items => filtered[items[0].dataIndex].team,
            label: item => [
              `🏆 Win: ${item.raw.toFixed(2)}%`,
              `ELO: ${filtered[item.dataIndex].elo}`,
              `Group: ${filtered[item.dataIndex].group}`,
            ]
          }
        }
      },
      scales: {
        x: {
          ticks: {
            color: "#8b9cbf",
            font: { size: 11 },
            maxRotation: 45,
          },
          grid: { color: "rgba(255,255,255,0.04)" },
        },
        y: {
          ticks: {
            color: "#8b9cbf",
            callback: v => v.toFixed(1) + "%",
            font: { size: 11 },
          },
          grid: { color: "rgba(255,255,255,0.06)" },
        }
      }
    }
  });
}

// ── Probability Table ─────────────────────────────────────────────────────
function buildProbTable(teams, search = "", sortCol = "champion_pct") {
  let filtered = teams.filter(t =>
    t.team.toLowerCase().includes(search.toLowerCase())
  );
  filtered.sort((a, b) => b[sortCol] - a[sortCol]);

  const maxVals = {
    r32_pct: Math.max(...teams.map(t => t.r32_pct)),
    r16_pct: Math.max(...teams.map(t => t.r16_pct)),
    qf_pct:  Math.max(...teams.map(t => t.qf_pct)),
    semi_pct: Math.max(...teams.map(t => t.semi_pct)),
    finalist_pct: Math.max(...teams.map(t => t.finalist_pct)),
    champion_pct: Math.max(...teams.map(t => t.champion_pct)),
  };

  const tbody = $("probTableBody");
  tbody.innerHTML = filtered.map((t, i) => `
    <tr data-team="${t.team}">
      <td>${i + 1}</td>
      <td>${flag(t.team)} ${t.team}</td>
      <td><span class="group-badge">${t.group}</span></td>
      <td>${t.elo}</td>
      <td class="heat-cell" style="--heat-w:${heatWidth(t.r32_pct, maxVals.r32_pct)}%">
        ${t.r32_pct?.toFixed(1) ?? "—"}%
      </td>
      <td class="heat-cell" style="--heat-w:${heatWidth(t.r16_pct, maxVals.r16_pct)}%">
        ${t.r16_pct?.toFixed(1) ?? "—"}%
      </td>
      <td class="heat-cell" style="--heat-w:${heatWidth(t.qf_pct, maxVals.qf_pct)}%">
        ${t.qf_pct?.toFixed(1) ?? "—"}%
      </td>
      <td class="heat-cell" style="--heat-w:${heatWidth(t.semi_pct, maxVals.semi_pct)}%">
        ${t.semi_pct?.toFixed(1) ?? "—"}%
      </td>
      <td class="heat-cell" style="--heat-w:${heatWidth(t.finalist_pct, maxVals.finalist_pct)}%">
        ${t.finalist_pct?.toFixed(1) ?? "—"}%
      </td>
      <td class="win-cell">${t.champion_pct?.toFixed(2) ?? "—"}%</td>
    </tr>
  `).join("");

  tbody.querySelectorAll("tr").forEach((row, i) => {
    row.addEventListener("click", () => openTeamModal(filtered[i]));
  });
}

// ── H2H Simulator ─────────────────────────────────────────────────────────
function buildH2HSimulator(teams) {
  const sorted = [...teams].sort((a, b) => b.elo - a.elo);
  const options = sorted.map(t => `<option value="${t.team}">${flag(t.team)} ${t.team}</option>`).join("");

  $("teamA").innerHTML = options;
  $("teamB").innerHTML = options;

  // Default: Argentina vs France
  const argIdx = sorted.findIndex(t => t.team === "Argentina");
  const fraIdx = sorted.findIndex(t => t.team === "France");
  $("teamA").selectedIndex = argIdx >= 0 ? argIdx : 0;
  $("teamB").selectedIndex = fraIdx >= 0 ? fraIdx : 1;

  updateH2H();

  $("teamA").addEventListener("change", updateH2H);
  $("teamB").addEventListener("change", updateH2H);
  $("swapBtn").addEventListener("click", () => {
    const tmp = $("teamA").value;
    $("teamA").value = $("teamB").value;
    $("teamB").value = tmp;
    updateH2H();
  });
}

function updateH2H() {
  const teamA = $("teamA").value;
  const teamB = $("teamB").value;
  if (teamA === teamB) return;

  const ra = DATA.ratings[teamA] || 1500;
  const rb = DATA.ratings[teamB] || 1500;
  $("eloA").textContent = `ELO: ${ra}`;
  $("eloB").textContent = `ELO: ${rb}`;

  // Get H2H data or compute from ELO diff
  const h2h = DATA.head_to_head?.[teamA]?.[teamB];
  let pWin, pDraw, pLoss, koWin, koLoss;

  if (h2h) {
    pWin  = h2h.win_pct;
    pDraw = h2h.draw_pct;
    pLoss = h2h.loss_pct;
    // estimate KO from win + half draw
    koWin  = Math.round((pWin + pDraw * 0.52) * 10) / 10;
    koLoss = Math.round((100 - koWin) * 10) / 10;
  } else {
    // Fallback ELO calculation
    const diff = ra - rb;
    const rawWin = 1 / (1 + Math.pow(10, -diff / 400));
    const drawProb = 0.24 * Math.exp(-0.0012 * diff * diff);
    pWin  = Math.round((rawWin * (1 - drawProb)) * 1000) / 10;
    pDraw = Math.round(drawProb * 1000) / 10;
    pLoss = Math.round(100 - pWin - pDraw);
    koWin  = Math.round((pWin + pDraw * 0.52) * 10) / 10;
    koLoss = Math.round(100 - koWin);
  }

  const winColor  = "#4fa3f7";
  const drawColor = "#a78bfa";
  const lossColor = "#f87171";

  $("h2hBars").innerHTML = `
    <div style="font-size:0.8rem;font-weight:600;margin-bottom:8px;color:#f0f4ff">
      Group Stage Probabilities
    </div>
    <div class="h2h-bar-row">
      <div class="h2h-bar-label" style="color:${winColor}">${flag(teamA)}</div>
      <div class="h2h-bar-track">
        <div class="h2h-bar-seg" style="width:${pWin}%;background:${winColor}"></div>
      </div>
      <div class="h2h-bar-pct" style="color:${winColor}">${pWin.toFixed(1)}%</div>
    </div>
    <div class="h2h-bar-row">
      <div class="h2h-bar-label" style="color:${drawColor}">Draw</div>
      <div class="h2h-bar-track">
        <div class="h2h-bar-seg" style="width:${pDraw}%;background:${drawColor}"></div>
      </div>
      <div class="h2h-bar-pct" style="color:${drawColor}">${pDraw.toFixed(1)}%</div>
    </div>
    <div class="h2h-bar-row">
      <div class="h2h-bar-label" style="color:${lossColor}">${flag(teamB)}</div>
      <div class="h2h-bar-track">
        <div class="h2h-bar-seg" style="width:${pLoss}%;background:${lossColor}"></div>
      </div>
      <div class="h2h-bar-pct" style="color:${lossColor}">${pLoss.toFixed(1)}%</div>
    </div>
  `;

  $("h2hKnockout").innerHTML = `
    <div class="h2h-ko-title">Knockout / Penalty Scenario</div>
    <div class="h2h-ko-row">
      <div class="h2h-ko-team">${flag(teamA)} ${teamA}</div>
      <div class="h2h-ko-pct" style="color:${koWin > 50 ? '#34d399' : '#f87171'}">${koWin}%</div>
    </div>
    <div class="h2h-ko-row">
      <div class="h2h-ko-team">${flag(teamB)} ${teamB}</div>
      <div class="h2h-ko-pct" style="color:${koLoss > 50 ? '#34d399' : '#f87171'}">${koLoss}%</div>
    </div>
    <div style="font-size:0.72rem;color:#4a5568;margin-top:8px">
      Includes penalty shootout probability (≈52/48 to stronger team)
    </div>
  `;

  // Doughnut chart
  const ctx = $("h2hChart").getContext("2d");
  if (h2hChart) h2hChart.destroy();
  h2hChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: [`${teamA} win`, "Draw", `${teamB} win`],
      datasets: [{
        data: [pWin, pDraw, pLoss],
        backgroundColor: [winColor + "cc", drawColor + "cc", lossColor + "cc"],
        borderColor: [winColor, drawColor, lossColor],
        borderWidth: 2,
        hoverOffset: 8,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "65%",
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            color: "#8b9cbf",
            font: { size: 12 },
            padding: 16,
            boxWidth: 14,
          }
        },
        tooltip: {
          backgroundColor: "#111927",
          borderColor: "rgba(255,255,255,0.1)",
          borderWidth: 1,
          callbacks: { label: i => ` ${i.label}: ${i.raw.toFixed(1)}%` }
        }
      }
    }
  });
}

// ── ELO History Chart ─────────────────────────────────────────────────────
let eloActiveTeams = null;

function buildEloHistory() {
  const hist = DATA.elo_history;
  if (!hist) return;

  const teamNames = Object.keys(hist);
  eloActiveTeams = new Set(teamNames);

  // Build legend toggles
  const legendContainer = $("legendToggles");
  legendContainer.innerHTML = "";
  teamNames.forEach((team, i) => {
    const color = ELO_LINE_COLORS[i % ELO_LINE_COLORS.length];
    const btn = document.createElement("button");
    btn.className = "legend-btn active";
    btn.textContent = `${flag(team)} ${team}`;
    btn.style.background = color;
    btn.style.borderColor = color;
    btn.style.color = "#080c14";
    btn.dataset.team = team;
    btn.dataset.color = color;
    btn.addEventListener("click", () => {
      if (eloActiveTeams.has(team)) {
        eloActiveTeams.delete(team);
        btn.classList.remove("active");
        btn.style.background = "transparent";
        btn.style.color = color;
      } else {
        eloActiveTeams.add(team);
        btn.classList.add("active");
        btn.style.background = color;
        btn.style.color = "#080c14";
      }
      renderEloChart();
    });
    legendContainer.appendChild(btn);
  });

  renderEloChart();
}

function renderEloChart() {
  const hist = DATA.elo_history;
  const teamNames = Object.keys(hist).filter(t => eloActiveTeams.has(t));

  // Gather all years
  const yearSet = new Set();
  teamNames.forEach(t => hist[t].forEach(d => yearSet.add(d.year)));
  const years = [...yearSet].sort((a, b) => a - b);

  const datasets = teamNames.map((team, i) => {
    const colorIdx = Object.keys(hist).indexOf(team);
    const color = ELO_LINE_COLORS[colorIdx % ELO_LINE_COLORS.length];
    const yearMap = {};
    hist[team].forEach(d => yearMap[d.year] = d.elo);
    return {
      label: team,
      data: years.map(y => yearMap[y] ?? null),
      borderColor: color,
      backgroundColor: color + "18",
      borderWidth: 2,
      pointRadius: 4,
      pointHoverRadius: 6,
      tension: 0.35,
      spanGaps: true,
      fill: false,
    };
  });

  const ctx = $("eloHistoryChart").getContext("2d");
  if (eloHistChart) eloHistChart.destroy();

  eloHistChart = new Chart(ctx, {
    type: "line",
    data: { labels: years, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#111927",
          borderColor: "rgba(255,255,255,0.1)",
          borderWidth: 1,
          titleColor: "#f0f4ff",
          bodyColor: "#8b9cbf",
          callbacks: {
            label: item => ` ${item.dataset.label}: ${item.raw?.toFixed(0) ?? "—"}`
          }
        }
      },
      scales: {
        x: {
          ticks: { color: "#8b9cbf", font: { size: 11 } },
          grid: { color: "rgba(255,255,255,0.04)" },
        },
        y: {
          ticks: { color: "#8b9cbf", font: { size: 11 } },
          grid: { color: "rgba(255,255,255,0.06)" },
        }
      }
    }
  });
}

// ── Groups Grid ───────────────────────────────────────────────────────────
function buildGroups(teams, maxChamp) {
  const groups = DATA.groups;
  const teamMap = {};
  teams.forEach(t => teamMap[t.team] = t);

  const grid = $("groupsGrid");
  grid.innerHTML = "";

  Object.entries(groups).forEach(([groupName, groupTeams]) => {
    const color = GROUP_COLORS[groupName] || "#4fa3f7";
    const card = document.createElement("div");
    card.className = "group-card";

    const sorted = [...groupTeams].sort((a, b) =>
      (teamMap[b]?.champion_pct || 0) - (teamMap[a]?.champion_pct || 0)
    );

    card.innerHTML = `
      <div class="group-card-header" style="border-left: 3px solid ${color}">
        Group ${groupName}
      </div>
      ${sorted.map(team => {
        const t = teamMap[team];
        if (!t) return "";
        return `
          <div class="group-team-row" data-team="${team}">
            <div class="group-team-name">
              <span>${flag(team)}</span>
              <span>${team}</span>
            </div>
            <div class="group-team-pcts">
              <div>
                <div class="group-pct-label">Win</div>
                <div class="group-pct-val">${t.champion_pct.toFixed(2)}%</div>
              </div>
            </div>
          </div>
        `;
      }).join("")}
    `;
    grid.appendChild(card);
  });

  grid.querySelectorAll("[data-team]").forEach(el => {
    el.addEventListener("click", () => {
      const t = teamMap[el.dataset.team];
      if (t) openTeamModal(t);
    });
  });
}

// ── Team Modal ────────────────────────────────────────────────────────────
function openTeamModal(t) {
  const modal = $("teamModal");
  $("modalContent").innerHTML = `
    <div class="modal-team-header">
      <div class="modal-flag">${flag(t.team)}</div>
      <div>
        <div class="modal-team-name">${t.team}</div>
        <span class="modal-group-tag">Group ${t.group}</span>
      </div>
    </div>
    <div class="modal-stats">
      <div class="modal-stat-card">
        <div class="modal-stat-label">🏆 Champion %</div>
        <div class="modal-stat-val">${t.champion_pct.toFixed(2)}%</div>
      </div>
      <div class="modal-stat-card">
        <div class="modal-stat-label">ELO Rating</div>
        <div class="modal-stat-val" style="color:#4fa3f7">${t.elo}</div>
      </div>
      <div class="modal-stat-card">
        <div class="modal-stat-label">Finalist %</div>
        <div class="modal-stat-val" style="color:#a78bfa">${t.finalist_pct?.toFixed(1) ?? "—"}%</div>
      </div>
      <div class="modal-stat-card">
        <div class="modal-stat-label">Semi-Final %</div>
        <div class="modal-stat-val" style="color:#34d399">${t.semi_pct?.toFixed(1) ?? "—"}%</div>
      </div>
      <div class="modal-stat-card">
        <div class="modal-stat-label">Quarter-Final %</div>
        <div class="modal-stat-val" style="color:#fb923c">${t.qf_pct?.toFixed(1) ?? "—"}%</div>
      </div>
      <div class="modal-stat-card">
        <div class="modal-stat-label">Round of 16 %</div>
        <div class="modal-stat-val" style="color:#f472b6">${t.r16_pct?.toFixed(1) ?? "—"}%</div>
      </div>
    </div>
    <div style="text-align:center;padding-top:8px">
      <button
        onclick="document.getElementById('teamA').value='${t.team}'; updateH2H(); closeModal(); document.getElementById('teamA').scrollIntoView({behavior:'smooth'})"
        style="background:rgba(79,163,247,0.1);border:1px solid rgba(79,163,247,0.3);color:#4fa3f7;padding:8px 18px;border-radius:8px;cursor:pointer;font-size:0.85rem"
      >
        Simulate match with ${t.team}
      </button>
    </div>
  `;

  $("modalOverlay").classList.remove("hidden");

  $("modalClose").onclick = closeModal;
  $("modalOverlay").onclick = e => {
    if (e.target === $("modalOverlay")) closeModal();
  };
}

function closeModal() {
  $("modalOverlay").classList.add("hidden");
}

// ── Filter dropdowns ──────────────────────────────────────────────────────
function populateFilterGroups() {
  const sel = $("filterGroup");
  "ABCDEFGHIJKL".split("").forEach(g => {
    const opt = document.createElement("option");
    opt.value = g;
    opt.textContent = `Group ${g}`;
    sel.appendChild(opt);
  });
}

// ── Event Wiring ──────────────────────────────────────────────────────────
function attachEvents(teams, maxChamp) {
  $("sortSelect").addEventListener("change", () => {
    buildAllTeamsChart(teams, $("sortSelect").value, $("filterGroup").value);
  });
  $("filterGroup").addEventListener("change", () => {
    buildAllTeamsChart(teams, $("sortSelect").value, $("filterGroup").value);
  });
  $("teamSearch").addEventListener("input", () => {
    buildProbTable(teams, $("teamSearch").value, $("tableSort").value);
  });
  $("tableSort").addEventListener("change", () => {
    buildProbTable(teams, $("teamSearch").value, $("tableSort").value);
  });

  // Keyboard: Escape closes modal
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") closeModal();
  });
}

// ── Bootstrap ─────────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", loadData);

// Expose for inline onclick
window.updateH2H  = updateH2H;
window.closeModal = closeModal;
