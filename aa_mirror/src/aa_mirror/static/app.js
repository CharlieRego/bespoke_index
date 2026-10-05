(function () {
  "use strict";

  function readJson(id) {
    var el = document.getElementById(id);
    return el ? JSON.parse(el.textContent) : null;
  }

  // Sortable tables: click a header to sort by its column's data-v values.
  document.querySelectorAll("table.sortable").forEach(function (table) {
    table.querySelectorAll("th").forEach(function (th, idx) {
      th.addEventListener("click", function () {
        var num = th.dataset.type === "num";
        var dir = th.dataset.dir === "desc" ? "asc" : "desc";
        table.querySelectorAll("th").forEach(function (h) { delete h.dataset.dir; });
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

  // Filters on the leaderboard tables.
  var table = document.getElementById("leaderboard");
  var text = document.getElementById("filter-text");
  var creator = document.getElementById("filter-creator");
  var indexed = document.getElementById("filter-indexed");
  var count = document.getElementById("row-count");
  function applyFilter() {
    if (!table) return;
    var q = text ? text.value.trim().toLowerCase() : "";
    var c = creator ? creator.value : "";
    var shown = 0;
    Array.prototype.forEach.call(table.tBodies[0].rows, function (r) {
      var ok = (!q || r.textContent.toLowerCase().indexOf(q) !== -1) &&
        (!c || r.dataset.creator === c) &&
        (!indexed || !indexed.checked || r.cells[2].dataset.v !== "");
      r.hidden = !ok;
      if (ok) shown++;
    });
    if (count) count.textContent = shown + " shown";
  }
  [text, creator, indexed].forEach(function (el) { if (el) el.addEventListener("input", applyFilter); });
  applyFilter();

  // Refresh button.
  var btn = document.getElementById("refresh-btn");
  var msg = document.getElementById("refresh-msg");
  function poll(runId) {
    fetch("/api/status", { credentials: "same-origin" }).then(function (r) { return r.json(); }).then(function (s) {
      var lr = s.last_run;
      if (lr && lr.id === runId && lr.status !== "running") {
        msg.textContent = "Run #" + runId + " finished: " + lr.status + ". Reloading…";
        setTimeout(function () { location.reload(); }, 800);
      } else {
        setTimeout(function () { poll(runId); }, 2000);
      }
    }).catch(function () { setTimeout(function () { poll(runId); }, 5000); });
  }
  if (btn) {
    btn.addEventListener("click", function () {
      btn.disabled = true;
      msg.textContent = "Requesting refresh…";
      fetch("/api/refresh", {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-Requested-With": "aa-mirror" }
      }).then(function (r) { return r.json(); }).then(function (res) {
        if (res.accepted) {
          msg.textContent = "Run #" + res.run_id + " started…";
          poll(res.run_id);
        } else {
          msg.textContent = "Not started: " + res.message;
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

  // Charts.
  function whenChart(fn) {
    if (window.Chart) return fn();
    window.addEventListener("load", function () { if (window.Chart) fn(); });
  }
  function label(ctx) {
    var p = ctx.raw;
    return p.name + (p.creator ? " (" + p.creator + ")" : "") + ": " + p.x + ", " + p.y;
  }
  function scatter(id, points, xTitle, yTitle, xLog) {
    var el = document.getElementById(id);
    if (!el) return;
    new Chart(el, {
      type: "scatter",
      data: { datasets: [{ data: points, pointRadius: 4, backgroundColor: "rgba(37,99,235,0.6)" }] },
      options: {
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: label } } },
        scales: {
          x: { type: xLog ? "logarithmic" : "linear", title: { display: true, text: xTitle } },
          y: { title: { display: true, text: yTitle } }
        },
        onClick: function (e, els) {
          if (els.length) location.href = "/model/" + encodeURIComponent(points[els[0].index].id);
        }
      }
    });
  }

  var models = readJson("chart-data");
  if (models) whenChart(function () {
    function pts(xk, yk, positiveX) {
      return models.filter(function (m) {
        return m[xk] !== null && m[yk] !== null && (!positiveX || m[xk] > 0);
      }).map(function (m) {
        return { x: m[xk], y: m[yk], name: m.name, creator: m.creator_name, id: m.model_id };
      });
    }
    scatter("chart-price", pts("price_blended", "intelligence_index", true), "Blended USD / 1M tokens", "Intelligence Index", true);
    scatter("chart-iq-speed", pts("output_tps", "intelligence_index"), "Output tokens/s", "Intelligence Index", false);
    var top = models.filter(function (m) { return m.output_tps !== null; })
      .sort(function (a, b) { return b.output_tps - a.output_tps; }).slice(0, 25);
    var el = document.getElementById("chart-speed");
    if (el) new Chart(el, {
      type: "bar",
      data: { labels: top.map(function (m) { return m.name; }), datasets: [{ data: top.map(function (m) { return m.output_tps; }), backgroundColor: "rgba(16,185,129,0.7)" }] },
      options: { indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { title: { display: true, text: "tokens/s" } } } }
    });
  });

  var series = readJson("series-data");
  if (series) whenChart(function () {
    var labels = series.map(function (s) { return s.started_at.slice(0, 10); });
    var a = document.getElementById("hist-iq");
    if (a) new Chart(a, {
      type: "line",
      data: { labels: labels, datasets: [{ label: "Intelligence Index", data: series.map(function (s) { return s.intelligence_index; }), spanGaps: true }] }
    });
    var b = document.getElementById("hist-price-speed");
    if (b) new Chart(b, {
      type: "line",
      data: { labels: labels, datasets: [
        { label: "Blended $/1M", data: series.map(function (s) { return s.price_blended; }), yAxisID: "y", spanGaps: true },
        { label: "Output tok/s", data: series.map(function (s) { return s.output_tps; }), yAxisID: "y1", spanGaps: true }
      ] },
      options: { scales: { y: { position: "left" }, y1: { position: "right", grid: { drawOnChartArea: false } } } }
    });
  });
})();
