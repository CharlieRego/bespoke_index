(function () {
  "use strict";

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

  function readJson(id) {
    var el = document.getElementById(id);
    return el ? JSON.parse(el.textContent) : null;
  }
  function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

  // Theme toggle (per-viewer convenience only).
  var redraws = [];
  var themeBtn = document.getElementById("theme-btn");
  if (themeBtn) themeBtn.addEventListener("click", function () {
    var dark = css("color-scheme") === "dark";
    var next = dark ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("aa-theme", next); } catch (e) {}
    redraws.forEach(function (fn) { fn(); });
  });

  // UTC timestamps -> viewer's local time.
  $$("time[data-utc]").forEach(function (t) {
    if (!t.dataset.utc) return;
    var d = new Date(t.dataset.utc);
    if (isNaN(d)) return;
    t.title = t.dataset.utc;
    t.textContent = d.toLocaleString(undefined, { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" });
  });

  // Creator colours: fixed for the big labs, hashed for the rest.
  var FIXED = {
    "Anthropic": "#d97757", "OpenAI": "#10a37f", "Google": "#4285f4", "Meta": "#8b5cf6", "xAI": "#64748b",
    "DeepSeek": "#2f5bea", "Alibaba": "#ff7a1a", "Mistral": "#e8590c", "Amazon": "#f59e0b", "Microsoft": "#00a4ef",
    "NVIDIA": "#76b900", "Moonshot AI": "#ec4899", "Z AI": "#14b8a6", "MiniMax": "#e11d48", "Cohere": "#a855f7"
  };
  var PALETTE = ["#0ea5e9", "#f43f5e", "#84cc16", "#a855f7", "#eab308", "#06b6d4", "#f97316", "#22c55e", "#6366f1", "#d946ef", "#14b8a6", "#ef4444"];
  function colorFor(creator) {
    if (!creator) return "#94a3b8";
    if (FIXED[creator]) return FIXED[creator];
    var h = 0;
    for (var i = 0; i < creator.length; i++) h = (h * 31 + creator.charCodeAt(i)) >>> 0;
    return PALETTE[h % PALETTE.length];
  }
  $$("[data-swatch]").forEach(function (el) { el.style.background = colorFor(el.dataset.swatch); });

  function shortName(n) {
    return (n || "").replace(/,?\s*Default Fallback/i, "").replace(/\(\s*\)/, "").trim();
  }
  function clip(s, n) { return s.length > n ? s.slice(0, n - 1) + "…" : s; }
  function pos(v) { return typeof v === "number" && v > 0; }
  function fmtNum(v, d) { return v == null ? "–" : v.toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d }); }
  function fmtMoney(v) { return v == null ? "–" : "$" + (v >= 0.1 ? fmtNum(v, 2) : fmtNum(v, 3)); }

  // Sortable tables.
  $$("table.sortable").forEach(function (table) {
    $$("th", table).forEach(function (th, idx) {
      th.addEventListener("click", function () {
        var num = th.dataset.type === "num";
        var dir = th.dataset.dir === "desc" ? "asc" : "desc";
        $$("th", table).forEach(function (h) { delete h.dataset.dir; });
        th.dataset.dir = dir;
        var body = table.tBodies[0];
        var rows = Array.prototype.slice.call(body.rows);
        rows.sort(function (a, b) {
          var va = a.cells[idx].dataset.v, vb = b.cells[idx].dataset.v;
          if (va === "" && vb === "") return 0;
          if (va === "") return 1;
          if (vb === "") return -1;
          var c = num ? parseFloat(va) - parseFloat(vb) : va.localeCompare(vb);
          return dir === "asc" ? c : -c;
        });
        rows.forEach(function (r) { body.appendChild(r); });
      });
    });
  });

  // Refresh button.
  var btn = document.getElementById("refresh-btn");
  var msg = document.getElementById("refresh-msg");
  function poll(runId) {
    fetch("/api/status", { credentials: "same-origin" }).then(function (r) { return r.json(); }).then(function (s) {
      var lr = s.last_run;
      if (lr && lr.id === runId && lr.status !== "running") {
        msg.textContent = "Run #" + runId + " " + lr.status + ", reloading…";
        setTimeout(function () { location.reload(); }, 800);
      } else {
        setTimeout(function () { poll(runId); }, 2000);
      }
    }).catch(function () { setTimeout(function () { poll(runId); }, 5000); });
  }
  if (btn) {
    btn.addEventListener("click", function () {
      btn.disabled = true;
      msg.textContent = "Requesting…";
      fetch("/api/refresh", {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-Requested-With": "aa-mirror" }
      }).then(function (r) { return r.json(); }).then(function (res) {
        if (res.accepted) {
          msg.textContent = "Run #" + res.run_id + " started…";
          poll(res.run_id);
        } else {
          msg.textContent = res.message;
          btn.disabled = false;
        }
      }).catch(function () {
        msg.textContent = "Request failed.";
        btn.disabled = false;
      });
    });
    var running = document.getElementById("status").dataset.running;
    if (running) {
      btn.disabled = true;
      msg.textContent = "Run #" + running + " in progress…";
      poll(parseInt(running, 10));
    }
  }

  // ---------- Charts ----------
  function whenChart(fn) {
    var go = function () {
      if (!window.Chart) return;
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(fn); else fn();
    };
    if (window.Chart) return go();
    window.addEventListener("load", go);
  }
  function logTicks(fmt) {
    return function (v) {
      var m = +(v / Math.pow(10, Math.floor(Math.log10(v)))).toPrecision(2);
      return m === 1 || m === 3 ? fmt(v) : "";
    };
  }

  var valueLabels = {
    id: "valueLabels",
    afterDatasetsDraw: function (chart, args, opts) {
      if (!opts || !opts.format) return;
      var ctx = chart.ctx, horizontal = chart.options.indexAxis === "y";
      ctx.save();
      ctx.font = "600 11px Inter, system-ui, sans-serif";
      ctx.fillStyle = css("--fg-2");
      chart.getDatasetMeta(0).data.forEach(function (el, i) {
        var v = chart.data.datasets[0].data[i];
        if (v == null) return;
        var text = opts.format(v);
        if (horizontal) {
          ctx.textAlign = "left"; ctx.textBaseline = "middle";
          ctx.fillText(text, el.x + 5, el.y);
        } else {
          ctx.textAlign = "center"; ctx.textBaseline = "bottom";
          ctx.fillText(text, el.x, el.y - 4);
        }
      });
      ctx.restore();
    }
  };

  var quadrant = {
    id: "quadrant",
    beforeDatasetsDraw: function (chart, args, opts) {
      if (!opts || opts.x == null || opts.y == null) return;
      var xs = chart.scales.x, ys = chart.scales.y, a = chart.chartArea, ctx = chart.ctx;
      var xp = xs.getPixelForValue(opts.x), yp = ys.getPixelForValue(opts.y);
      ctx.save();
      ctx.fillStyle = css("--quadrant");
      if (opts.goodX === "low") ctx.fillRect(a.left, a.top, xp - a.left, yp - a.top);
      else ctx.fillRect(xp, a.top, a.right - xp, yp - a.top);
      ctx.strokeStyle = css("--line");
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(xp, a.top); ctx.lineTo(xp, a.bottom);
      ctx.moveTo(a.left, yp); ctx.lineTo(a.right, yp);
      ctx.stroke();
      ctx.restore();
    }
  };

  var pointLabels = {
    id: "pointLabels",
    afterDatasetsDraw: function (chart) {
      var ctx = chart.ctx, ds = chart.data.datasets[0];
      if (!ds || !ds.data) return;
      ctx.save();
      ctx.font = "500 10.5px Inter, system-ui, sans-serif";
      ctx.fillStyle = css("--fg-2");
      ctx.textBaseline = "middle";
      var placed = [];
      chart.getDatasetMeta(0).data.forEach(function (el, i) {
        var p = ds.data[i];
        if (!p.label) return;
        var text = clip(shortName(p.name), 26), w = ctx.measureText(text).width;
        var right = el.x + 8 + w < chart.chartArea.right;
        var x = right ? el.x + 7 : el.x - 7 - w, y = el.y;
        var box = { x: x, y: y - 6, w: w, h: 12 };
        var hit = placed.some(function (b) { return box.x < b.x + b.w && box.x + box.w > b.x && box.y < b.y + b.h && box.y + box.h > b.y; });
        if (hit) return;
        placed.push(box);
        ctx.textAlign = "left";
        ctx.fillText(text, x, y);
      });
      ctx.restore();
    }
  };

  function baseOptions() {
    var grid = css("--line"), tick = css("--muted");
    Chart.defaults.font.family = "Inter, system-ui, sans-serif";
    Chart.defaults.color = tick;
    return {
      responsive: true, maintainAspectRatio: false, animation: { duration: 250 },
      plugins: {
        legend: { display: false },
        tooltip: { backgroundColor: "rgba(15,23,42,.92)", padding: 10, cornerRadius: 8, titleFont: { weight: "600" } }
      },
      scales: {
        x: { grid: { color: grid, drawTicks: false }, border: { display: false }, ticks: { color: tick, padding: 6 } },
        y: { grid: { color: grid, drawTicks: false }, border: { display: false }, ticks: { color: tick, padding: 6 } }
      }
    };
  }

  function median(arr) {
    var s = arr.slice().sort(function (a, b) { return a - b; });
    if (!s.length) return null;
    var m = Math.floor(s.length / 2);
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
  }

  var charts = {};
  function draw(id, config) {
    if (charts[id]) charts[id].destroy();
    var el = document.getElementById(id);
    if (!el) return;
    charts[id] = new Chart(el, config);
  }
  function goToModel(list) {
    return function (e, els) { if (els.length) location.href = "/model/" + encodeURIComponent(list[els[0].index].model_id); };
  }

  function vbar(id, list, key, fmt) {
    var o = baseOptions();
    o.plugins.valueLabels = { format: fmt };
    o.plugins.tooltip.callbacks = {
      title: function (items) { return list[items[0].dataIndex].name; },
      label: function (item) { return (list[item.dataIndex].creator_name || "") + ": " + fmt(item.raw); }
    };
    o.scales.x.grid.display = false;
    o.scales.x.ticks.autoSkip = false;
    o.scales.x.ticks.maxRotation = 60;
    o.scales.x.ticks.minRotation = list.length > 12 ? 45 : 0;
    o.scales.x.ticks.callback = function (v, i) { return clip(shortName(list[i].name), 24); };
    o.scales.y.beginAtZero = true;
    o.scales.y.grace = "8%";
    o.layout = { padding: { top: 14, left: 24 } };
    o.onClick = goToModel(list);
    draw(id, {
      type: "bar",
      data: { labels: list.map(function (m) { return m.name; }), datasets: [{
        data: list.map(function (m) { return m[key]; }),
        backgroundColor: list.map(function (m) { return colorFor(m.creator_name); }),
        borderRadius: 4, maxBarThickness: 34
      }] },
      options: o, plugins: [valueLabels]
    });
  }

  function hbar(id, list, key, fmt, logX) {
    var box = document.getElementById(id).parentNode;
    box.style.height = Math.max(180, list.length * 22 + 50) + "px";
    var o = baseOptions();
    o.indexAxis = "y";
    o.plugins.valueLabels = { format: fmt };
    o.plugins.tooltip.callbacks = {
      title: function (items) { return list[items[0].dataIndex].name; },
      label: function (item) { return (list[item.dataIndex].creator_name || "") + ": " + fmt(item.raw); }
    };
    o.scales.y.grid.display = false;
    o.scales.y.ticks.autoSkip = false;
    o.scales.y.ticks.font = { size: 11 };
    o.scales.y.ticks.callback = function (v, i) { return clip(shortName(list[i].name), 22); };
    o.scales.x.ticks.maxRotation = 0;
    o.layout = { padding: { right: 8 } };
    var vals = list.map(function (m) { return m[key]; });
    if (logX) {
      o.scales.x.type = "logarithmic";
      o.scales.x.min = Math.pow(10, Math.floor(Math.log10(Math.min.apply(null, vals))));
      o.scales.x.max = Math.max.apply(null, vals) * 4;
      o.scales.x.ticks.callback = logTicks(fmt);
    } else {
      o.scales.x.beginAtZero = true;
      o.scales.x.grace = "18%";
    }
    o.onClick = goToModel(list);
    draw(id, {
      type: "bar",
      data: { labels: list.map(function (m) { return m.name; }), datasets: [{
        data: list.map(function (m) { return m[key]; }),
        backgroundColor: list.map(function (m) { return colorFor(m.creator_name); }),
        borderRadius: 3, barThickness: 14
      }] },
      options: o, plugins: [valueLabels]
    });
  }

  function scatter(id, list, xKey, xTitle, xFmt, logX, goodX) {
    var pts = list.filter(function (m) { return pos(m[xKey]) && m.intelligence_index != null; });
    var ranked = pts.slice().sort(function (a, b) { return b.intelligence_index - a.intelligence_index; });
    var labelSet = {};
    ranked.slice(0, pts.length > 60 ? 6 : 14).forEach(function (m) { labelSet[m.model_id] = true; });
    var data = pts.map(function (m) {
      return { x: m[xKey], y: m.intelligence_index, name: m.name, creator: m.creator_name, model_id: m.model_id, label: !!labelSet[m.model_id] };
    });
    var o = baseOptions();
    o.plugins.quadrant = { x: median(pts.map(function (m) { return m[xKey]; })), y: median(pts.map(function (m) { return m.intelligence_index; })), goodX: goodX };
    o.plugins.tooltip.callbacks = {
      title: function (items) { return items[0].raw.name; },
      label: function (item) { return (item.raw.creator || "") + " · Intelligence " + fmtNum(item.raw.y, 1) + " · " + xFmt(item.raw.x); }
    };
    o.scales.x.type = logX ? "logarithmic" : "linear";
    o.scales.x.title = { display: true, text: xTitle, color: css("--muted"), font: { weight: "500" } };
    o.scales.x.ticks.maxRotation = 0;
    o.scales.x.ticks.autoSkipPadding = 18;
    o.scales.x.ticks.callback = logX ? logTicks(xFmt) : function (v) { return fmtNum(v, 0); };
    o.scales.y.title = { display: true, text: "Intelligence Index", color: css("--muted"), font: { weight: "500" } };
    o.onClick = function (e, els) { if (els.length) location.href = "/model/" + encodeURIComponent(data[els[0].index].model_id); };
    draw(id, {
      type: "scatter",
      data: { datasets: [{
        data: data,
        pointRadius: data.length > 120 ? 3.5 : 5.5, pointHoverRadius: 7,
        pointBackgroundColor: data.map(function (p) { return colorFor(p.creator); }),
        pointBorderColor: css("--surface"), pointBorderWidth: 1
      }] },
      options: o, plugins: [quadrant, pointLabels]
    });
  }

  function highlight(el, list, key, asc, fmt) {
    var rows = list.filter(function (m) { return key === "intelligence_index" ? m[key] != null : pos(m[key]); })
      .sort(function (a, b) { return asc ? a[key] - b[key] : b[key] - a[key]; }).slice(0, 5);
    var max = rows.reduce(function (acc, m) { return Math.max(acc, m[key]); }, 0) || 1;
    el.innerHTML = "";
    if (!rows.length) { el.innerHTML = '<p class="muted">No data in this selection.</p>'; return; }
    rows.forEach(function (m) {
      var row = document.createElement("a");
      row.className = "hl-row";
      row.href = "/model/" + encodeURIComponent(m.model_id);
      var sw = document.createElement("span"); sw.className = "swatch"; sw.style.background = colorFor(m.creator_name);
      var nm = document.createElement("span"); nm.className = "name"; nm.textContent = shortName(m.name); nm.title = m.name;
      var val = document.createElement("b"); val.textContent = fmt(m[key]);
      var bar = document.createElement("span"); bar.className = "bar";
      var fill = document.createElement("i"); fill.style.background = colorFor(m.creator_name);
      fill.style.width = (asc ? (rows[0][key] / m[key]) : (m[key] / max)) * 100 + "%";
      bar.appendChild(fill);
      row.append(sw, nm, val, bar);
      el.appendChild(row);
    });
  }

  // ---------- LLM leaderboard ----------
  var models = readJson("chart-data");
  var table = document.getElementById("leaderboard");
  if (models && $("#preset")) {
    var state = { preset: "frontier" };
    var text = $("#filter-text"), creator = $("#filter-creator"), indexed = $("#filter-indexed");
    var byId = {};
    models.forEach(function (m) { byId[m.model_id] = m; });
    var BAR_CAP = 30;

    function select() {
      var q = text.value.trim().toLowerCase(), c = creator.value;
      var base = models.filter(function (m) {
        return (!q || ((m.name || "") + " " + (m.creator_name || "")).toLowerCase().indexOf(q) !== -1) &&
          (!c || m.creator_name === c) &&
          (!indexed.checked || m.intelligence_index != null);
      });
      var withIq = base.filter(function (m) { return m.intelligence_index != null; })
        .sort(function (a, b) { return b.intelligence_index - a.intelligence_index; });
      if (state.preset === "frontier") {
        if (c || q) return withIq.slice(0, BAR_CAP);
        var seen = {};
        return withIq.filter(function (m) {
          var k = m.creator_name || m.model_id;
          if (seen[k]) return false;
          seen[k] = true;
          return true;
        }).slice(0, 20);
      }
      if (state.preset === "top") return withIq.slice(0, BAR_CAP);
      if (state.preset === "new") {
        var cutoff = new Date(Date.now() - 90 * 864e5).toISOString().slice(0, 10);
        return base.filter(function (m) { return m.release_date && m.release_date >= cutoff; })
          .sort(function (a, b) { return (b.intelligence_index || -1) - (a.intelligence_index || -1); });
      }
      return base;
    }

    function render() {
      var sel = select();
      var ids = {};
      sel.forEach(function (m) { ids[m.model_id] = true; });
      Array.prototype.forEach.call(table.tBodies[0].rows, function (r) { r.hidden = !ids[r.dataset.id]; });
      $("#row-count").textContent = sel.length + " of " + models.length + " models";
      $$("[data-shown]").forEach(function (el) { el.textContent = sel.length + " models"; });

      highlight($('[data-hl="intelligence_index"]'), sel, "intelligence_index", false, function (v) { return fmtNum(v, 1); });
      highlight($('[data-hl="output_tps"]'), sel, "output_tps", false, function (v) { return fmtNum(v, 0) + " tok/s"; });
      highlight($('[data-hl="price_blended"]'), sel, "price_blended", true, fmtMoney);

      whenChart(function () {
        var iq = sel.filter(function (m) { return m.intelligence_index != null; })
          .sort(function (a, b) { return b.intelligence_index - a.intelligence_index; }).slice(0, 40);
        vbar("chart-iq", iq, "intelligence_index", function (v) { return fmtNum(v, 0); });
        scatter("chart-iq-price", sel, "price_blended", "Price (USD per 1M tokens, log)", fmtMoney, true, "low");
        scatter("chart-iq-speed", sel, "output_tps", "Output speed (tokens/s)", function (v) { return fmtNum(v, 0) + " tok/s"; }, false, "high");
        var speed = sel.filter(function (m) { return pos(m.output_tps); }).sort(function (a, b) { return b.output_tps - a.output_tps; }).slice(0, BAR_CAP);
        hbar("chart-speed", speed, "output_tps", function (v) { return fmtNum(v, 0); });
        var price = sel.filter(function (m) { return pos(m.price_blended); }).sort(function (a, b) { return a.price_blended - b.price_blended; }).slice(0, BAR_CAP);
        hbar("chart-price", price, "price_blended", fmtMoney, true);
        var lat = sel.map(function (m) { return Object.assign({}, m, { latency: pos(m.ttfa_s) ? m.ttfa_s : m.ttft_s }); })
          .filter(function (m) { return pos(m.latency); }).sort(function (a, b) { return a.latency - b.latency; }).slice(0, BAR_CAP);
        hbar("chart-latency", lat, "latency", function (v) { return fmtNum(v, v < 10 ? 2 : 0) + "s"; }, lat.length && lat[lat.length - 1].latency / lat[0].latency > 50);
      });
    }

    $$("#preset button").forEach(function (b) {
      b.addEventListener("click", function () {
        state.preset = b.dataset.preset;
        $$("#preset button").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
        render();
      });
    });
    var t;
    text.addEventListener("input", function () { clearTimeout(t); t = setTimeout(render, 150); });
    creator.addEventListener("change", render);
    indexed.addEventListener("change", render);
    render();
    redraws.push(render);
  }

  // ---------- Media leaderboard ----------
  var media = readJson("media-data");
  if (media) {
    var mtext = $("#filter-text"), mcount = $("#row-count");
    var drawMedia = function () {
      whenChart(function () {
        var top = media.filter(function (m) { return m.elo != null; }).sort(function (a, b) { return b.elo - a.elo; }).slice(0, 25);
        var box = document.getElementById("chart-elo").parentNode;
        box.style.height = Math.max(200, top.length * 24 + 50) + "px";
        var o = baseOptions();
        o.indexAxis = "y";
        o.plugins.valueLabels = { format: function (v) { return fmtNum(v, 0); } };
        o.plugins.tooltip.callbacks = { label: function (item) { return (top[item.dataIndex].creator_name || "") + ": ELO " + fmtNum(item.raw, 0); } };
        o.scales.y.grid.display = false;
        o.scales.y.ticks.autoSkip = false;
        o.scales.y.ticks.callback = function (v, i) { return clip(top[i].name || "", 32); };
        var lo = top.length ? top[top.length - 1].elo : 0;
        o.scales.x.min = Math.floor((lo - 40) / 50) * 50;
        o.scales.x.grace = "6%";
        draw("chart-elo", {
          type: "bar",
          data: { labels: top.map(function (m) { return m.name; }), datasets: [{
            data: top.map(function (m) { return m.elo; }),
            backgroundColor: top.map(function (m) { return colorFor(m.creator_name); }),
            borderRadius: 3, barThickness: 15
          }] },
          options: o, plugins: [valueLabels]
        });
      });
    };
    if (mtext && table) {
      var applyMedia = function () {
        var q = mtext.value.trim().toLowerCase(), shown = 0;
        Array.prototype.forEach.call(table.tBodies[0].rows, function (r) {
          var ok = !q || r.textContent.toLowerCase().indexOf(q) !== -1;
          r.hidden = !ok;
          if (ok) shown++;
        });
        if (mcount) mcount.textContent = shown + " models";
      };
      mtext.addEventListener("input", applyMedia);
      applyMedia();
    }
    drawMedia();
    redraws.push(drawMedia);
  }

  // ---------- Model history ----------
  var series = readJson("series-data");
  if (series) {
    var drawSeries = function () {
      whenChart(function () {
        var labels = series.map(function (s) { return s.started_at.slice(0, 10); });
        var accent = css("--accent");
        var o1 = baseOptions();
        draw("hist-iq", {
          type: "line",
          data: { labels: labels, datasets: [{ label: "Intelligence Index", data: series.map(function (s) { return s.intelligence_index; }), borderColor: accent, backgroundColor: accent, spanGaps: true, tension: 0.25 }] },
          options: o1
        });
        var o2 = baseOptions();
        o2.plugins.legend = { display: true, labels: { boxWidth: 10 } };
        o2.scales.y1 = { position: "right", grid: { drawOnChartArea: false }, border: { display: false } };
        draw("hist-price-speed", {
          type: "line",
          data: { labels: labels, datasets: [
            { label: "Blended $/1M", data: series.map(function (s) { return s.price_blended || null; }), yAxisID: "y", borderColor: "#f59e0b", backgroundColor: "#f59e0b", spanGaps: true, tension: 0.25 },
            { label: "Output tok/s", data: series.map(function (s) { return s.output_tps || null; }), yAxisID: "y1", borderColor: "#10b981", backgroundColor: "#10b981", spanGaps: true, tension: 0.25 }
          ] },
          options: o2
        });
      });
    };
    drawSeries();
    redraws.push(drawSeries);
  }

  var evals = readJson("eval-data");
  if (evals) {
    var drawEvals = function () {
      whenChart(function () {
        var rows = evals.filter(function (e) { return e.v != null; });
        var box = document.getElementById("chart-evals").parentNode;
        box.style.height = Math.max(180, rows.length * 24 + 50) + "px";
        var o = baseOptions();
        o.indexAxis = "y";
        o.plugins.valueLabels = { format: function (v) { return fmtNum(v, 1); } };
        o.scales.y.grid.display = false;
        o.scales.y.ticks.autoSkip = false;
        o.scales.x.beginAtZero = true;
        o.scales.x.max = 100;
        draw("chart-evals", {
          type: "bar",
          data: { labels: rows.map(function (e) { return e.k; }), datasets: [{ data: rows.map(function (e) { return e.v; }), backgroundColor: css("--accent"), borderRadius: 3, barThickness: 14 }] },
          options: o, plugins: [valueLabels]
        });
      });
    };
    drawEvals();
    redraws.push(drawEvals);
  }
})();
