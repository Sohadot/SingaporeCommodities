/**
 * Node Power Index — Sovereign Analytical Tool
 * SingaporeCommodities.com
 *
 * Eight-dimension radar chart for comparative commodity node assessment.
 * Pure JavaScript + SVG. No external dependencies. No API. No AI.
 * Data sovereignty maintained through local JSON.
 */

(() => {
  "use strict";

  // ─── Node Data ────────────────────────────────────────────────────────────
  const NODES = {
    singapore: {
      name: "Singapore",
      layer: "Coordination",
      tagline: "The node that organizes movement without owning it.",
      scores: {
        maritime_routing: 10,
        financial_structuring: 9,
        storage_logistics: 9,
        commodity_transformation: 7,
        price_formation: 8,
        regulatory_framework: 10,
        strategic_location: 10,
        trade_finance: 9
      },
      key_commodities: ["LNG", "Crude Oil", "Bunkering", "Fuel Oil", "Naphtha"],
      benchmarks: ["MOPS", "JKM-linked", "SICOM TSR 20"]
    },
    london: {
      name: "London",
      layer: "Pricing",
      tagline: "Where prices are discovered, not commodities.",
      scores: {
        maritime_routing: 5,
        financial_structuring: 10,
        storage_logistics: 5,
        commodity_transformation: 4,
        price_formation: 10,
        regulatory_framework: 9,
        strategic_location: 7,
        trade_finance: 10
      },
      key_commodities: ["Crude Oil", "Metals", "Gold", "Natural Gas"],
      benchmarks: ["Brent ICE", "LBMA Gold", "LME Metals", "ICE Gasoil"]
    },
    geneva: {
      name: "Geneva",
      layer: "Structuring",
      tagline: "Where deals are structured in silence.",
      scores: {
        maritime_routing: 2,
        financial_structuring: 10,
        storage_logistics: 3,
        commodity_transformation: 2,
        price_formation: 8,
        regulatory_framework: 9,
        strategic_location: 6,
        trade_finance: 10
      },
      key_commodities: ["Crude Oil", "Coal", "Agri", "Metals"],
      benchmarks: ["OTC contracts", "Platts-linked"]
    },
    rotterdam: {
      name: "Rotterdam",
      layer: "Routing",
      tagline: "Europe's commodity warehouse.",
      scores: {
        maritime_routing: 9,
        financial_structuring: 7,
        storage_logistics: 10,
        commodity_transformation: 8,
        price_formation: 7,
        regulatory_framework: 8,
        strategic_location: 9,
        trade_finance: 7
      },
      key_commodities: ["Crude Oil", "Fuel Oil", "Gasoil", "LNG", "Coal"],
      benchmarks: ["ARA Barges", "NWE Naphtha CIF", "ICE Gasoil-linked"]
    },
    shanghai: {
      name: "Shanghai",
      layer: "Demand",
      tagline: "Where commodities become products.",
      scores: {
        maritime_routing: 8,
        financial_structuring: 7,
        storage_logistics: 8,
        commodity_transformation: 10,
        price_formation: 8,
        regulatory_framework: 6,
        strategic_location: 9,
        trade_finance: 7
      },
      key_commodities: ["Iron Ore", "Copper", "Crude Oil", "LNG", "Coal"],
      benchmarks: ["SHFE Copper", "INE Crude", "SHFE Rebar"]
    },
    dubai: {
      name: "Dubai",
      layer: "Routing",
      tagline: "The crossroads of East-West energy flows.",
      scores: {
        maritime_routing: 8,
        financial_structuring: 7,
        storage_logistics: 8,
        commodity_transformation: 5,
        price_formation: 7,
        regulatory_framework: 7,
        strategic_location: 9,
        trade_finance: 8
      },
      key_commodities: ["Crude Oil", "Fuel Oil", "Gold", "Agri", "Metals"],
      benchmarks: ["DME Oman Crude", "DGCX", "Dubai/Oman differential"]
    }
  };

  const DIMENSIONS = [
    { key: "maritime_routing",        label: "Maritime Routing" },
    { key: "financial_structuring",   label: "Financial Structuring" },
    { key: "storage_logistics",       label: "Storage & Logistics" },
    { key: "commodity_transformation",label: "Transformation" },
    { key: "price_formation",         label: "Price Formation" },
    { key: "regulatory_framework",    label: "Regulatory Framework" },
    { key: "strategic_location",      label: "Strategic Location" },
    { key: "trade_finance",           label: "Trade Finance" }
  ];

  const LAYER_COLORS = {
    Coordination: "#C9A24A",
    Pricing:      "#7B8CDE",
    Structuring:  "#9B59B6",
    Routing:      "#2ECC71",
    Demand:       "#E74C3C"
  };

  // ─── SVG Radar Chart ────────────────────────────────────────────────────
  function computeRadarPoints(scores, cx, cy, radius) {
    const n = DIMENSIONS.length;
    return DIMENSIONS.map((dim, i) => {
      const angle = (2 * Math.PI * i) / n - Math.PI / 2;
      const value = scores[dim.key] / 10;
      return {
        x: cx + radius * value * Math.cos(angle),
        y: cy + radius * value * Math.sin(angle),
        ax: cx + (radius + 28) * Math.cos(angle),
        ay: cy + (radius + 28) * Math.sin(angle),
        gx: cx + radius * Math.cos(angle),
        gy: cy + radius * Math.sin(angle),
        label: dim.label,
        score: scores[dim.key]
      };
    });
  }

  function buildRadarSVG(nodeKey, compareKey) {
    const node = NODES[nodeKey];
    const compare = compareKey && compareKey !== "none" ? NODES[compareKey] : null;
    const cx = 200;
    const cy = 200;
    const radius = 130;
    const n = DIMENSIONS.length;

    let svg = `<svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Node Power Index radar chart for ${node.name}">`;

    // Grid rings
    for (let ring = 1; ring <= 5; ring++) {
      const r = (radius / 5) * ring;
      const ringPoints = Array.from({ length: n }, (_, i) => {
        const angle = (2 * Math.PI * i) / n - Math.PI / 2;
        return `${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`;
      }).join(" ");
      svg += `<polygon points="${ringPoints}" fill="none" stroke="#1a2035" stroke-width="1"/>`;
    }

    // Grid spokes
    for (let i = 0; i < n; i++) {
      const angle = (2 * Math.PI * i) / n - Math.PI / 2;
      const ex = cx + radius * Math.cos(angle);
      const ey = cy + radius * Math.sin(angle);
      svg += `<line x1="${cx}" y1="${cy}" x2="${ex}" y2="${ey}" stroke="#1a2035" stroke-width="1"/>`;
    }

    // Compare area (behind primary)
    if (compare) {
      const cPoints = computeRadarPoints(compare.scores, cx, cy, radius);
      const cPath = cPoints.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ") + " Z";
      const cColor = LAYER_COLORS[compare.layer] || "#888";
      svg += `<path d="${cPath}" fill="${cColor}" fill-opacity="0.12" stroke="${cColor}" stroke-width="1.5" stroke-dasharray="4,3"/>`;
    }

    // Primary area
    const pts = computeRadarPoints(node.scores, cx, cy, radius);
    const path = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ") + " Z";
    const color = LAYER_COLORS[node.layer] || "#C9A24A";
    svg += `<path d="${path}" fill="${color}" fill-opacity="0.25" stroke="${color}" stroke-width="2"/>`;

    // Data points
    pts.forEach(p => {
      svg += `<circle cx="${p.x.toFixed(2)}" cy="${p.y.toFixed(2)}" r="4" fill="${color}" stroke="#05070D" stroke-width="1.5"/>`;
    });

    // Dimension labels and scores
    pts.forEach(p => {
      const anchor = p.ax > cx + 5 ? "start" : p.ax < cx - 5 ? "end" : "middle";
      svg += `<text x="${p.ax.toFixed(2)}" y="${p.ay.toFixed(2)}" text-anchor="${anchor}" dominant-baseline="middle" fill="#8892aa" font-size="9" font-family="JetBrains Mono, monospace">${p.label}</text>`;
      svg += `<text x="${p.ax.toFixed(2)}" y="${(p.ay + 11).toFixed(2)}" text-anchor="${anchor}" dominant-baseline="middle" fill="${color}" font-size="10" font-weight="600" font-family="JetBrains Mono, monospace">${p.score}</text>`;
    });

    // Center label
    svg += `<text x="${cx}" y="${cy - 8}" text-anchor="middle" fill="#ffffff" font-size="13" font-weight="700" font-family="Barlow, sans-serif">${node.name}</text>`;
    svg += `<text x="${cx}" y="${cy + 10}" text-anchor="middle" fill="${color}" font-size="10" font-family="JetBrains Mono, monospace">${node.layer} Node</text>`;

    if (compare) {
      const cColor = LAYER_COLORS[compare.layer] || "#888";
      svg += `<text x="${cx}" y="${cy + 26}" text-anchor="middle" fill="${cColor}" font-size="9" font-family="JetBrains Mono, monospace">vs. ${compare.name}</text>`;
    }

    svg += `</svg>`;
    return svg;
  }

  // ─── Score Table ────────────────────────────────────────────────────────
  function buildScoreTable(nodeKey, compareKey) {
    const node = NODES[nodeKey];
    const compare = compareKey && compareKey !== "none" ? NODES[compareKey] : null;
    const color = LAYER_COLORS[node.layer] || "#C9A24A";

    let html = `<table class="npi-table" role="grid" aria-label="Node Power Index scores for ${node.name}">`;
    html += `<thead><tr>
      <th scope="col">Dimension</th>
      <th scope="col" style="color:${color}">${node.name}</th>
      ${compare ? `<th scope="col" style="color:${LAYER_COLORS[compare.layer] || "#888"}">${compare.name}</th>` : ""}
      <th scope="col">Bar</th>
    </tr></thead><tbody>`;

    DIMENSIONS.forEach(dim => {
      const score = node.scores[dim.key];
      const cScore = compare ? compare.scores[dim.key] : null;
      const barWidth = (score / 10) * 100;
      const diff = cScore !== null ? score - cScore : null;
      const diffStr = diff !== null ? (diff > 0 ? `<span class="npi-diff npi-diff-pos">+${diff}</span>` : diff < 0 ? `<span class="npi-diff npi-diff-neg">${diff}</span>` : `<span class="npi-diff">=</span>`) : "";

      html += `<tr>
        <td class="npi-dim-label">${dim.label}</td>
        <td class="npi-score" style="color:${color}">${score} ${diffStr}</td>
        ${compare ? `<td class="npi-score" style="color:${LAYER_COLORS[compare.layer] || "#888"}">${cScore}</td>` : ""}
        <td class="npi-bar-cell"><div class="npi-bar-track"><div class="npi-bar-fill" style="width:${barWidth}%;background:${color}"></div></div></td>
      </tr>`;
    });

    html += `</tbody></table>`;
    return html;
  }

  // ─── Node Profile Card ───────────────────────────────────────────────────
  function buildProfileCard(nodeKey) {
    const node = NODES[nodeKey];
    const color = LAYER_COLORS[node.layer] || "#C9A24A";
    const total = Object.values(node.scores).reduce((a, b) => a + b, 0);
    const max = Object.keys(node.scores).length * 10;
    const pct = Math.round((total / max) * 100);

    return `
      <div class="npi-profile">
        <div class="npi-profile-header">
          <span class="npi-layer-badge" style="background:${color}20;color:${color};border-color:${color}40">${node.layer} Node</span>
          <span class="npi-composite">${pct}<span class="npi-composite-label">/100</span></span>
        </div>
        <p class="npi-tagline">"${node.tagline}"</p>
        <div class="npi-meta">
          <div class="npi-meta-block">
            <span class="npi-meta-label">Key Commodities</span>
            <span class="npi-meta-value">${node.key_commodities.join(" · ")}</span>
          </div>
          <div class="npi-meta-block">
            <span class="npi-meta-label">Benchmarks</span>
            <span class="npi-meta-value">${node.benchmarks.join(" · ")}</span>
          </div>
        </div>
      </div>
    `;
  }

  // ─── Main Render ────────────────────────────────────────────────────────
  function renderNPI(nodeKey, compareKey) {
    const radarEl = document.getElementById("npi-radar");
    const tableEl = document.getElementById("npi-table");
    const profileEl = document.getElementById("npi-profile");

    if (!radarEl || !tableEl || !profileEl) return;

    radarEl.innerHTML = buildRadarSVG(nodeKey, compareKey);
    tableEl.innerHTML = buildScoreTable(nodeKey, compareKey);
    profileEl.innerHTML = buildProfileCard(nodeKey);
  }

  // ─── Init ────────────────────────────────────────────────────────────────
  function initNPI() {
    const nodeSelect = document.getElementById("npi-node-select");
    const compareSelect = document.getElementById("npi-compare-select");

    if (!nodeSelect) return;

    const update = () => {
      const nodeKey = nodeSelect.value;
      const compareKey = compareSelect ? compareSelect.value : "none";
      if (NODES[nodeKey]) {
        renderNPI(nodeKey, compareKey);
      }
    };

    nodeSelect.addEventListener("change", update);
    if (compareSelect) compareSelect.addEventListener("change", update);

    // Initial render
    update();
  }

  // Export for main.js to call
  window.SCI = window.SCI || {};
  window.SCI.initNPI = initNPI;

})();
