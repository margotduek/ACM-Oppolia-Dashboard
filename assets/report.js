/* Oppolia · filtro de rango de fechas para los dashboards.
   Recalcula, desde data.json, todo lo que es 100% derivable de Meta Ads.
   Las secciones con juicio cualitativo (calidad de leads, citas, playbook)
   no se tocan aquí — ver README para por qué. */
(function () {
  "use strict";

  function num(x) {
    var n = parseFloat(x);
    return isNaN(n) ? 0 : n;
  }

  function actionValue(actions, type) {
    if (!actions) return 0;
    for (var i = 0; i < actions.length; i++) {
      if (actions[i].action_type === type) return num(actions[i].value);
    }
    return 0;
  }

  function fmtMoney(n) {
    return "$" + Math.round(n).toLocaleString("es-MX");
  }
  function fmtInt(n) {
    return Math.round(n).toLocaleString("es-MX");
  }
  function fmtPct(n) {
    return n.toFixed(2) + "%";
  }
  function fmtDateEs(d) {
    return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" }).replace(".", "");
  }

  function inRange(row, start, end) {
    return row.date_start >= start && row.date_start <= end;
  }

  function filterRows(rows, start, end) {
    return (rows || []).filter(function (r) {
      return inRange(r, start, end);
    });
  }

  function sumMetrics(rows) {
    var m = { spend: 0, impressions: 0, clicks: 0, reach: 0, leads: 0 };
    rows.forEach(function (r) {
      m.spend += num(r.spend);
      m.impressions += num(r.impressions);
      m.clicks += num(r.clicks);
      m.reach += num(r.reach);
      m.leads += actionValue(r.actions, "lead");
    });
    m.ctr = m.impressions ? (m.clicks / m.impressions) * 100 : 0;
    m.cpc = m.clicks ? m.spend / m.clicks : 0;
    m.cpm = m.impressions ? (m.spend / m.impressions) * 1000 : 0;
    m.cpl = m.leads ? m.spend / m.leads : 0;
    return m;
  }

  function groupBy(rows, keyFn) {
    var map = {};
    var order = [];
    rows.forEach(function (r) {
      var k = keyFn(r);
      if (!map[k]) {
        map[k] = [];
        order.push(k);
      }
      map[k].push(r);
    });
    return order.map(function (k) {
      var m = sumMetrics(map[k]);
      m.key = k;
      return m;
    });
  }

  function daysBetween(start, end) {
    var a = new Date(start + "T00:00:00");
    var b = new Date(end + "T00:00:00");
    return Math.round((b - a) / 86400000) + 1;
  }

  function shiftDate(dateStr, deltaDays) {
    var d = new Date(dateStr + "T00:00:00");
    d.setDate(d.getDate() + deltaDays);
    return d.toISOString().slice(0, 10);
  }

  // ---- render helpers -------------------------------------------------

  function renderBars(container, items, opts) {
    if (!container) return;
    opts = opts || {};
    var color = opts.color || "#C9A24B";
    var max = Math.max.apply(null, items.map(function (i) { return i.value; }).concat([0.0001]));
    container.innerHTML = items
      .map(function (i) {
        var w = max ? (i.value / max) * 100 : 0;
        return (
          '<div class="bar-row"><div class="bar-lab"' +
          (opts.labelWidth ? ' style="width:' + opts.labelWidth + 'px"' : "") +
          ">" +
          i.label +
          '</div><div class="bar-track"><div class="bar-fill" style="width:' +
          w.toFixed(1) +
          "%;background:" +
          color +
          '"></div></div><div class="bar-val">' +
          i.display +
          "</div></div>"
        );
      })
      .join("");
  }

  function renderDonut(svg, segments, opts) {
    if (!svg) return;
    opts = opts || {};
    var r = opts.r || 74;
    var sw = opts.strokeWidth || 26;
    var cx = opts.cx || r + sw / 2 + 2;
    var cy = cx;
    var total = segments.reduce(function (s, x) { return s + x.value; }, 0) || 1;
    var circumference = 2 * Math.PI * r;
    var offset = 0;
    var circles = segments
      .map(function (seg) {
        var frac = seg.value / total;
        var dash = frac * circumference;
        var c =
          '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" fill="none" stroke="' + seg.color +
          '" stroke-width="' + sw + '" stroke-dasharray="' + dash.toFixed(2) + " " + (circumference - dash).toFixed(2) +
          '" stroke-dashoffset="' + (-offset).toFixed(2) + '" transform="rotate(-90 ' + cx + " " + cy + ')"/>';
        offset += dash;
        return c;
      })
      .join("");
    var size = cx * 2;
    var centerText =
      '<text x="' + cx + '" y="' + (cy - 2) + '" text-anchor="middle" font-size="' + (opts.bigFont || 32) +
      '" font-weight="700" fill="#2A2724">' + Math.round(total) + "</text>" +
      '<text x="' + cx + '" y="' + (cy + 18) + '" text-anchor="middle" font-size="11" fill="#8A8378" letter-spacing="1">' +
      (opts.centerLabel || "") + "</text>";
    svg.setAttribute("viewBox", "0 0 " + size + " " + size);
    svg.setAttribute("width", size);
    svg.setAttribute("height", size);
    svg.innerHTML = circles + centerText;
  }

  function renderFunnel(container, steps) {
    if (!container) return;
    var max = steps.length ? steps[0].value || 1 : 1;
    container.innerHTML = steps
      .map(function (s, i) {
        var w = (s.value / max) * 100;
        var conv = i > 0 && steps[i - 1].value ? ((s.value / steps[i - 1].value) * 100).toFixed(1) + "% del paso previo" : "";
        return (
          '<div class="frow"><div class="flab">' + s.label + '</div><div class="fbarwrap"><div class="fbar" style="width:' +
          w.toFixed(1) + "%;background:" + s.color + '">' + fmtInt(s.value) + "</div>" +
          (conv ? '<span class="fconv">' + conv + "</span>" : "") + "</div></div>"
        );
      })
      .join("");
  }

  function renderTrend(svg, series, opts) {
    if (!svg) return;
    opts = opts || {};
    var W = 720, H = 240, left = 34, right = 686, top = 34, bottom = 206;
    var n = series.length;
    var x = function (i) { return n > 1 ? left + (i * (right - left)) / (n - 1) : left; };
    var maxSpend = Math.max.apply(null, series.map(function (s) { return s.spend; }).concat([0.0001]));
    var maxLeads = Math.max.apply(null, series.map(function (s) { return s.leads; }).concat([0.0001]));
    var ySpend = function (v) { return bottom - (v / maxSpend) * (bottom - top); };
    var yLeads = function (v) { return bottom - (v / maxLeads) * (bottom - top); };

    var gridlines = [34, 77, 120, 163, 206]
      .map(function (y) { return '<line x1="34" y1="' + y + '" x2="686" y2="' + y + '" stroke="#E7E1D7"/>'; })
      .join("");

    var spendPts = series.map(function (s, i) { return x(i).toFixed(0) + "," + ySpend(s.spend).toFixed(0); }).join(" ");
    var leadPts = series.map(function (s, i) { return x(i).toFixed(0) + "," + yLeads(s.leads).toFixed(0); }).join(" ");
    var leadDots = series
      .map(function (s, i) {
        return '<circle cx="' + x(i).toFixed(0) + '" cy="' + yLeads(s.leads).toFixed(0) + '" r="3" fill="#C9A24B"/>';
      })
      .join("");

    var labelEvery = Math.max(1, Math.ceil(n / 18));
    var labels = series
      .map(function (s, i) {
        if (i % labelEvery !== 0 && i !== n - 1) return "";
        var d = s.date.slice(5).replace("-", "-");
        return '<text x="' + x(i).toFixed(0) + '" y="230" font-size="9" fill="#8A8378" text-anchor="middle">' + d + "</text>";
      })
      .join("");

    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.innerHTML =
      gridlines +
      '<polyline points="' + spendPts + '" fill="none" stroke="#2A2724" stroke-width="2.5"/>' +
      '<polyline points="' + leadPts + '" fill="none" stroke="#C9A24B" stroke-width="2.5"/>' +
      leadDots +
      labels;
  }

  function renderTableRows(tbody, rowsHtml) {
    if (!tbody) return;
    tbody.innerHTML = rowsHtml.join("");
  }

  // ---- public API -------------------------------------------------------

  function computeReport(data, start, end) {
    var daily = filterRows(data.daily, start, end);
    var kpis = sumMetrics(daily);

    var byCampaign = groupBy(filterRows(data.campaign_insights_daily, start, end), function (r) { return r.campaign_name; })
      .sort(function (a, b) { return b.spend - a.spend; });

    var byAd = groupBy(filterRows(data.ad_insights_daily, start, end), function (r) { return r.ad_name; })
      .sort(function (a, b) { return b.spend - a.spend; });

    var ageGenderRows = filterRows(data.by_age_gender_daily, start, end);
    var byAge = groupBy(ageGenderRows, function (r) { return r.age; });
    var byGender = groupBy(ageGenderRows, function (r) { return r.gender; });

    var byRegion = groupBy(filterRows(data.by_region_daily, start, end), function (r) { return r.region; })
      .sort(function (a, b) { return b.spend - a.spend; });

    var byPlatform = groupBy(filterRows(data.by_platform_daily, start, end), function (r) { return r.publisher_platform; })
      .sort(function (a, b) { return b.spend - a.spend; });

    var series = daily
      .slice()
      .sort(function (a, b) { return a.date_start < b.date_start ? -1 : 1; })
      .map(function (r) { return { date: r.date_start, spend: num(r.spend), leads: actionValue(r.actions, "lead") }; });

    return { kpis: kpis, byCampaign: byCampaign, byAd: byAd, byAge: byAge, byGender: byGender, byRegion: byRegion, byPlatform: byPlatform, series: series };
  }

  function previousPeriod(start, end) {
    var len = daysBetween(start, end);
    var prevEnd = shiftDate(start, -1);
    var prevStart = shiftDate(prevEnd, -(len - 1));
    return { start: prevStart, end: prevEnd };
  }

  window.OppoliaReport = {
    num: num,
    fmtMoney: fmtMoney,
    fmtInt: fmtInt,
    fmtPct: fmtPct,
    fmtDateEs: fmtDateEs,
    daysBetween: daysBetween,
    shiftDate: shiftDate,
    computeReport: computeReport,
    previousPeriod: previousPeriod,
    renderBars: renderBars,
    renderDonut: renderDonut,
    renderFunnel: renderFunnel,
    renderTrend: renderTrend,
    renderTableRows: renderTableRows,
  };
})();
