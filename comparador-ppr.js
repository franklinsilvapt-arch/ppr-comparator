(function () {
  // Auto-mount: se o elemento host estiver vazio, injecta o markup.
  // Usado quando o ficheiro é carregado via <script src> no Webflow.
  // Em modo iframe standalone (markup inline), o host já tem .lpc-
  // container e salta-se este passo.
  var host = document.getElementById('lf-pc-calc');
  if (host && !host.querySelector('.lpc-container')) {
    host.innerHTML = `<div class="lpc-container">

  <!-- HEADER -->
  <div class="lpc-card">
    <div class="lpc-section-label">
      <span>Escolhe até 3 PPR para comparar</span>
      <span class="lpc-counter" id="lpc-counter">0 / 3 selecionados</span>
    </div>
    <div class="lpc-slots" id="lpc-slots">
      <div class="lpc-slot" data-slot="0">
        <div class="lpc-slot-label"><span class="lpc-slot-dot"></span>PPR 1</div>
        <div class="lpc-slot-wrap">
          <input type="text" class="lpc-slot-input" placeholder="Pesquisar..." autocomplete="off">
          <button type="button" class="lpc-slot-clear" aria-label="Remover">×</button>
        </div>
      </div>
      <div class="lpc-slot" data-slot="1">
        <div class="lpc-slot-label"><span class="lpc-slot-dot"></span>PPR 2</div>
        <div class="lpc-slot-wrap">
          <input type="text" class="lpc-slot-input" placeholder="Pesquisar..." autocomplete="off">
          <button type="button" class="lpc-slot-clear" aria-label="Remover">×</button>
        </div>
      </div>
      <div class="lpc-slot" data-slot="2">
        <div class="lpc-slot-label"><span class="lpc-slot-dot"></span>PPR 3</div>
        <div class="lpc-slot-wrap">
          <input type="text" class="lpc-slot-input" placeholder="Pesquisar..." autocomplete="off">
          <button type="button" class="lpc-slot-clear" aria-label="Remover">×</button>
        </div>
      </div>
    </div>
    <div id="lpc-dropdown-portal" style="position:relative;"></div>
  </div>

  <!-- CHART -->
  <div class="lpc-chart-card">
    <div class="lpc-tabs-header">
      <div class="lpc-tabs-title">Rentabilidade acumulada</div>
      <div class="lpc-tabs-controls">
        <div class="lpc-tabs" id="lpc-period-tabs">
          <button class="lpc-tab" data-period="ytd">YTD</button>
          <button class="lpc-tab" data-period="1y">1 ano</button>
          <button class="lpc-tab" data-period="3y">3 anos</button>
          <button class="lpc-tab" data-period="5y">5 anos</button>
          <button class="lpc-tab" data-period="10y">10 anos</button>
          <button class="lpc-tab is-active" data-period="since">Desde início</button>
        </div>
        <div class="lpc-tabs lpc-mode-toggle" id="lpc-mode-tabs">
          <button class="lpc-tab is-active" data-mode="eur">1.000€</button>
          <button class="lpc-tab" data-mode="pct">%</button>
        </div>
      </div>
    </div>
    <div class="lpc-benchmark-row">
      <label class="lpc-benchmark-toggle" for="lpc-benchmark-checkbox">
        <input type="checkbox" id="lpc-benchmark-checkbox">
        <span class="lpc-benchmark-text">sobrepor ETF de referência</span>
        <span class="lpc-info-icon" tabindex="0" aria-label="Sobrepõe ao gráfico o ETF de referência consoante o nível de risco de cada PPR seleccionado: risco 1-2 → LifeStrategy 20; risco 3 → LifeStrategy 40; risco 4 → LifeStrategy 60; risco 5 → LifeStrategy 80; risco 6-7 → iShares MSCI World. Os ETFs não são PPRs (sem benefício fiscal), servem apenas como referência de mercado.">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.33"></circle><path d="M8 7v4M8 5.5v.01" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"></path></svg>
          <span class="lpc-tip-bubble">Sobrepõe ao gráfico o ETF de referência consoante o nível de risco de cada PPR seleccionado: risco 1-2 → LifeStrategy 20; risco 3 → LifeStrategy 40; risco 4 → LifeStrategy 60; risco 5 → LifeStrategy 80; risco 6-7 → iShares MSCI World. Os ETFs não são PPRs (sem benefício fiscal), servem apenas como referência de mercado.</span>
        </span>
      </label>
    </div>
    <div class="lpc-chart-canvas-wrap">
      <canvas id="lpc-chart"></canvas>
    </div>
    <div id="lpc-chart-note" class="lpc-chart-note"></div>
    <div id="lpc-benchmark-note" class="lpc-chart-note" style="display:none"></div>
    <div class="lpc-returns-strip" id="lpc-returns-strip"></div>
    <div id="lpc-risk-warning"></div>
  </div>

  <!-- COMPARE TABLE -->
  <div class="lpc-card">
    <div class="lpc-section-title" style="margin-bottom: 24px;">Comparação detalhada</div>
    <div class="lpc-table-wrap">
      <table class="lpc-table" id="lpc-compare-table">
        <thead><tr id="lpc-compare-head"></tr></thead>
        <tbody id="lpc-compare-body"></tbody>
      </table>
    </div>
  </div>

  <!-- RISK TABLE -->
  <div class="lpc-card">
    <div class="lpc-section-title" style="margin-bottom: 24px;">Métricas de risco</div>
    <div class="lpc-table-wrap">
      <table class="lpc-table" id="lpc-risk-table">
        <thead><tr id="lpc-risk-head"></tr></thead>
        <tbody id="lpc-risk-body"></tbody>
      </table>
    </div>
  </div>

  <!-- FOOTER: data de actualização -->
  <div class="lpc-footer-updated" id="lpc-updated">
    <span class="lpc-updated-dot"></span>
    <span id="lpc-updated-text">A carregar dados...</span>
  </div>

</div>`;
  }
})();

(function () {
  'use strict';

  var root = document.getElementById('lf-pc-calc');
  if (!root) return;

  // Garante viewport meta: quando o HTML é servido standalone (ex: raw
  // GitHub Pages), sem isto o mobile renderiza a ~980px e as media
  // queries não disparam - tudo fica minúsculo. Webflow já inclui o
  // viewport na página, por isso aqui só adicionamos se não existir.
  if (!document.querySelector('meta[name="viewport"]')) {
    var _vp = document.createElement('meta');
    _vp.name = 'viewport';
    _vp.content = 'width=device-width, initial-scale=1';
    document.head.appendChild(_vp);
  }

  // =========================================================
  // CONFIG: URL do JSON publicado. Override via window.LF_PPR_DATA_URL.
  // =========================================================
  var DATA_URL = (typeof window !== 'undefined' && window.LF_PPR_DATA_URL)
    || 'https://franklinsilvapt-arch.github.io/ppr-comparator/data/latest.json';

  // Dados mock para fallback/preview
  var MOCK_FUNDS = [
    { id: 'mock-a', name: 'Fundo Exemplo A', manager: 'Gestora A', isin: 'PT0000000001',
      tec: 1.25, minSubs: 100, riskClass: 4,
      returns: { ytd: 6.5, '1y': 13.1, '3y': 28.4, '5y': 44.2, '10y': null, since: 44.2, ann: 7.1 },
      risk: { vol: 8.1, sharpe: 1.05, maxDD: -11.8, var95: -1.9, beta: 0.74 } },
    { id: 'mock-b', name: 'Fundo Exemplo B', manager: 'Gestora B', isin: 'PT0000000002',
      tec: 1.85, minSubs: 250, riskClass: 5,
      returns: { ytd: 8.2, '1y': 14.0, '3y': 32.5, '5y': 48.1, '10y': null, since: 48.1, ann: 7.6 },
      risk: { vol: 9.8, sharpe: 0.92, maxDD: -14.2, var95: -2.4, beta: 0.82 } },
    { id: 'mock-c', name: 'Fundo Exemplo C', manager: 'Gestora C', isin: 'PT0000000003',
      tec: 1.70, minSubs: 500, riskClass: 5,
      returns: { ytd: 9.4, '1y': 15.8, '3y': 35.1, '5y': 52.4, '10y': null, since: 52.4, ann: 8.2 },
      risk: { vol: 11.9, sharpe: 0.86, maxDD: -17.1, var95: -3.0, beta: 0.97 } }
  ];

  var FUNDS = MOCK_FUNDS.slice();
  var DATA_AS_OF = null;
  var USING_MOCK = true;
  var LOAD_ERROR = null;
  var BENCHMARK = null;  // {labels, data, ticker, name} do JSON backend
  var BENCHMARKS_BY_TICKER = {};  // {V20A: {labels, data, ticker, name, risk}, ...}

  // Paleta (design system): azul primário, laranja acento, verde acento.
  var SERIES_COLORS = ['#155EEF', '#FD8D2B', '#12B76A', '#8E44AD', '#B42318', '#0D9488'];
  var BASE_EUR = 1000;
  var MAX_SELECT = 3;
  var PREFERRED_DEFAULTS = ['invest-ar', 'casa-inv-sg-founders', 'sgf-dr-financas'];

  var state = { selected: [null, null, null], period: 'since', mode: 'eur', showBenchmark: false };
  var selectorState = { query: '', activeSlot: -1, highlightIdx: 0 };
  var chart = null;

  function normalizeBackendFund(f) {
    return {
      id: f.id, name: f.name, manager: f.manager,
      isin: f.isin, tec: f.tec,
      minSubs: f.min_subs,
      riskClass: f.risk_class,
      benchmarkTicker: f.benchmark_ticker || null,
      returns: f.returns || {},
      risk: f.risk || {},
      dataOrigin: f.data_origin || 'historical',
      _backendSeries: f.series || null,
      _lastDate: f.last_price_date || null
    };
  }

  var NA = '<span style="color:#96A0B0">-</span>';
  var INFO_SVG = '<svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">'
    + '<circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.33"></circle>'
    + '<path d="M8 7v4M8 5.5v.01" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"></path>'
    + '</svg>';

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function labelWithTip(label, tip) {
    if (!tip) return label;
    var safe = escapeHtml(tip);
    // sem title= para não duplicar com a bolha custom (que trata hover + tap)
    return '<span class="lpc-label-tip">' + label
      + '<span class="lpc-info-icon" tabindex="0" aria-label="' + safe + '">'
      + INFO_SVG
      + '<span class="lpc-tip-bubble">' + safe + '</span>'
      + '</span></span>';
  }

  function fmt(v, suf, dp) {
    if (dp == null) dp = 2;
    if (suf == null) suf = '';
    if (v == null || Number.isNaN(v)) return NA;
    return v.toFixed(dp).replace('.', ',') + suf;
  }
  function formatPct(v) {
    if (v == null || Number.isNaN(v)) return NA;
    var color = v >= 0 ? 'var(--green-text)' : '#B42318';
    var sign = v >= 0 ? '+' : '';
    return '<span style="color:' + color + ';font-weight:600">'
      + sign + v.toFixed(2).replace('.', ',') + '%</span>';
  }
  // Formato pt-PT manual - ponto separador de milhares, sem dependência
  // de toLocaleString (algumas runtimes Chart.js ignoram o locale).
  // Ex: 1234567 → "1.234.567 €"
  function fmtNumPT(n) {
    var s = Math.round(n).toString();
    var neg = s.charAt(0) === '-';
    if (neg) s = s.substring(1);
    s = s.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    return neg ? '-' + s : s;
  }
  function fmtEur(v) {
    return fmtNumPT(v) + '€';
  }
  function fmtEurDec(v) { return fmtEur(v); }

  // -----------------------------------------------------------
  // BADGE
  // -----------------------------------------------------------
  function updateBadge() {
    var badge = document.getElementById('lpc-updated');
    var text = document.getElementById('lpc-updated-text');
    if (USING_MOCK || !DATA_AS_OF) {
      badge.classList.add('is-stale');
      text.textContent = 'Dados de demonstração';
      badge.title = LOAD_ERROR
        ? 'Fetch falhou: ' + LOAD_ERROR + '\nURL: ' + DATA_URL
        : 'A carregar...';
      return;
    }
    var d = new Date(DATA_AS_OF);
    var formatted = d.toLocaleDateString('pt-PT', { day: 'numeric', month: 'long', year: 'numeric' });
    var daysOld = Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24));
    text.textContent = 'Atualizado a ' + formatted;
    var withHist = FUNDS.filter(function (f) { return f.dataOrigin === 'historical'; }).length;
    badge.title = FUNDS.length + ' fundos carregados (' + withHist + ' com histórico real).';
    if (daysOld > 14) badge.classList.add('is-stale');
    else badge.classList.remove('is-stale');
  }

  // -----------------------------------------------------------
  // SYNTHETIC SERIES (para fundos sem histórico real)
  // -----------------------------------------------------------
  function generateSeries(fund, period) {
    var points = { ytd: 90, '1y': 252, '3y': 756, '5y': 1260, '10y': 2520, since: 2520 };
    var n = points[period] || 252;
    var ret = fund.returns[period];
    if (ret == null || Number.isNaN(ret)) {
      ret = fund.returns['10y'];
      if (ret == null) ret = fund.returns['5y'];
      if (ret == null) ret = fund.returns['3y'];
      if (ret == null) ret = fund.returns['1y'];
      if (ret == null) return null;
    }
    var target = ret / 100;
    var seed = 0;
    for (var i = 0; i < fund.id.length; i++) seed = (seed * 31 + fund.id.charCodeAt(i)) >>> 0;
    var rand = function () { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 0xFFFFFFFF; };
    var volTable = [2, 4, 7, 10, 14, 18, 25];
    var annualVol = (fund.risk && fund.risk.vol)
      || (fund.riskClass ? volTable[Math.min(6, Math.max(0, fund.riskClass - 1))] : 8);
    var vol = annualVol / 100 / Math.sqrt(252);
    var drift = Math.pow(1 + target, 1 / n) - 1;
    var data = [];
    var value = 100;
    var labels = [];
    var today = new Date();
    for (var j = 0; j < n; j++) {
      var date = new Date(today);
      date.setDate(date.getDate() - (n - 1 - j));
      labels.push(date.toISOString().slice(0, 10));
      var shock = (rand() * 2 - 1) * vol * 1.7;
      value = value * (1 + drift + shock);
      data.push(value);
    }
    var finalReturn = (data[data.length - 1] - 100) / 100;
    var adjustFactor = (1 + target) / (1 + finalReturn);
    for (var k = 1; k < data.length; k++) {
      var w = k / (data.length - 1);
      data[k] = 100 + (data[k] - 100) * (1 + (adjustFactor - 1) * w);
    }
    return { labels: labels, data: data };
  }

  // -----------------------------------------------------------
  // SELECTOR (3 slots independentes, dropdown partilhada)
  // -----------------------------------------------------------
  // state.selected é um array de tamanho MAX_SELECT (3) onde cada
  // posição é um fund.id ou null. Os helpers selectedIds() abstraem
  // isto para quem precisa da lista densa de ids seleccionados.
  function selectedIds() {
    return state.selected.filter(function (id) { return !!id; });
  }

  function renderSelector() {
    var slots = root.querySelectorAll('.lpc-slot');
    slots.forEach(function (slot, i) {
      var id = state.selected[i];
      var f = id ? FUNDS.find(function (x) { return x.id === id; }) : null;
      var input = slot.querySelector('.lpc-slot-input');
      var dot = slot.querySelector('.lpc-slot-dot');
      if (f) {
        slot.classList.add('is-filled');
        input.value = f.name;
        input.readOnly = true;
        dot.style.background = SERIES_COLORS[i];
      } else {
        slot.classList.remove('is-filled');
        if (selectorState.activeSlot !== i) input.value = '';
        input.readOnly = false;
        dot.style.background = 'var(--border-primary)';
      }
    });
    var count = selectedIds().length;
    document.getElementById('lpc-counter').textContent = count + ' / ' + MAX_SELECT + ' selecionados';
    renderDropdown();
  }

  function filterFunds(query) {
    var q = (query || '').trim().toLowerCase();
    var already = selectedIds();
    var pool = FUNDS.filter(function (f) { return already.indexOf(f.id) === -1; });
    if (!q) return pool.slice(0, 300);
    return pool.filter(function (f) {
      return (f.name || '').toLowerCase().indexOf(q) !== -1
          || (f.manager || '').toLowerCase().indexOf(q) !== -1;
    }).slice(0, 300);
  }

  // Dropdown partilhada - é posicionada por baixo do slot activo via
  // o container do próprio slot (append/remove do DOM).
  var dropdownEl = null;
  function ensureDropdown() {
    if (!dropdownEl) {
      dropdownEl = document.createElement('div');
      dropdownEl.id = 'lpc-dropdown';
      dropdownEl.className = 'lpc-dropdown';
      // Lenis (smooth-scroll do Webflow) intercepta wheel events
      // globalmente. data-lenis-prevent marca este elemento como
      // excluido do Lenis - o browser trata native scroll da lista.
      dropdownEl.setAttribute('data-lenis-prevent', '');
    }
    return dropdownEl;
  }

  function renderDropdown() {
    var dd = ensureDropdown();
    var slotIdx = selectorState.activeSlot;
    if (slotIdx < 0 || state.selected[slotIdx]) {
      dd.classList.remove('is-open');
      if (dd.parentNode) dd.parentNode.removeChild(dd);
      // Dropdown fechou: refazer cálculo de altura para encolher o
      // iframe de volta ao tamanho natural.
      __sendHeight();
      return;
    }
    var slots = root.querySelectorAll('.lpc-slot');
    var slot = slots[slotIdx];
    var wrap = slot.querySelector('.lpc-slot-wrap');
    if (dd.parentNode !== wrap) {
      if (dd.parentNode) dd.parentNode.removeChild(dd);
      wrap.appendChild(dd);
    }
    var matches = filterFunds(selectorState.query);
    if (selectorState.highlightIdx >= matches.length) selectorState.highlightIdx = 0;
    if (!matches.length) {
      dd.innerHTML = '<div class="lpc-option-empty">Nenhum PPR encontrado</div>';
    } else {
      dd.innerHTML = matches.map(function (f, i) {
        return '<div class="lpc-option ' + (i === selectorState.highlightIdx ? 'is-highlighted' : '')
          + '" data-id="' + f.id + '">' + f.name + '</div>';
      }).join('');
      dd.querySelectorAll('.lpc-option').forEach(function (opt) {
        opt.addEventListener('mousedown', function (e) {
          e.preventDefault();
          selectFundInSlot(slotIdx, opt.dataset.id);
        });
      });
    }
    dd.classList.add('is-open');
    // Dropdown abriu: forçar recálculo para expandir o iframe e
    // acomodar a lista, sobretudo no PPR 3 que fica mais abaixo
    // e cuja lista extrapolava o fundo do iframe (overflow:hidden).
    // Double-rAF garante que o layout do dropdown está completo
    // antes de lermos as dimensões via getBoundingClientRect.
    requestAnimationFrame(function () {
      requestAnimationFrame(__sendHeight);
    });
  }

  function selectFundInSlot(slotIdx, id) {
    if (slotIdx < 0 || slotIdx >= MAX_SELECT) return;
    // Se já está noutro slot, mudar de slot em vez de duplicar
    var existing = state.selected.indexOf(id);
    if (existing !== -1 && existing !== slotIdx) {
      state.selected[existing] = null;
    }
    state.selected[slotIdx] = id;
    selectorState.query = '';
    selectorState.highlightIdx = 0;
    selectorState.activeSlot = -1;
    renderAll();
  }

  function clearSlot(slotIdx) {
    state.selected[slotIdx] = null;
    renderAll();
  }

  // Devolve lista de {fund, slot} só com slots preenchidos. Usado nos
  // render do chart + tabelas para preservar a cor por slot (idx 0/1/2).
  function pairedSelected() {
    var out = [];
    for (var i = 0; i < state.selected.length; i++) {
      var id = state.selected[i];
      if (!id) continue;
      var f = FUNDS.find(function (x) { return x.id === id; });
      if (f) out.push({ fund: f, slot: i });
    }
    return out;
  }

  // -----------------------------------------------------------
  // CHART
  // -----------------------------------------------------------
  function renderChart() {
    var canvas = document.getElementById('lpc-chart');
    var ctx = canvas.getContext('2d');
    var pairs = pairedSelected();

    var estimated = [];
    var seriesList = pairs.map(function (p) {
      var f = p.fund;
      var real = f._backendSeries && f._backendSeries[state.period];
      if (real && real.data && real.data.length) {
        return { labels: real.labels, dataPct: real.data, _real: true };
      }
      var synth = generateSeries(f, state.period);
      if (!synth) return null;
      estimated.push(f.name);
      return {
        labels: synth.labels,
        dataPct: synth.data.map(function (v) { return +(v - 100).toFixed(2); }),
        _real: false
      };
    });

    var validSeries = seriesList.filter(Boolean);

    // Preparar benchmarks necessários - um por ticker distinto entre os
    // PPRs seleccionados (V20A/V40A/V60A/V80A/IWDA). Mesmo quando a
    // regra 'máx 2 risk_classes' esconde as linhas do chart, o objecto
    // fica disponível para calcular o delta per-cartão na strip.
    var benchByTicker = {};
    pairs.forEach(function (p) {
      var t = p.fund.benchmarkTicker;
      if (!t || benchByTicker[t]) return;
      var b = BENCHMARKS_BY_TICKER[t];
      if (!b || !b.labels || !b.labels.length) return;
      benchByTicker[t] = {
        ticker: t, name: b.name,
        labels: b.labels.slice(), rawData: b.data.slice(),
        dataPct: null
      };
    });
    var distinctTickers = Object.keys(benchByTicker);
    var benchmarksVisible = state.showBenchmark && distinctTickers.length > 0 && distinctTickers.length <= 2;
    var benchmarksHiddenMixed = state.showBenchmark && distinctTickers.length > 2;

    // Rebase à data comum. Quando há múltiplos fundos, corta ao fundo
    // com menos histórico. Quando o toggle do benchmark está activo,
    // inclui também o início do(s) ETF(s) no cutoff - mesmo quando as
    // linhas do benchmark vão ficar escondidas (>2 tickers): assim a
    // delta per-cartão é calculada sobre a MESMA janela que o chart
    // mostra e é honestamente comparável.
    var cutoffSources = validSeries.map(function (s) { return s.labels[0]; });
    if (state.showBenchmark && distinctTickers.length > 0) {
      distinctTickers.forEach(function (t) { cutoffSources.push(benchByTicker[t].labels[0]); });
    }
    if (cutoffSources.length >= 2) {
      var cutoff = cutoffSources.reduce(function (a, b) { return a > b ? a : b; });
      validSeries.forEach(function (s) {
        if (s.labels[0] >= cutoff) return;
        var idx = s.labels.findIndex(function (l) { return l >= cutoff; });
        if (idx > 0) {
          var base = s.dataPct[idx];
          s.labels = s.labels.slice(idx);
          s.dataPct = s.dataPct.slice(idx).map(function (v) { return +(v - base).toFixed(2); });
        }
      });
    }

    // Rebasear cada benchmark ao cutoff visível (preços → % a partir do
    // primeiro valor no cutoff). Feito SEMPRE que o ticker está em uso,
    // independentemente do chart estar a desenhá-los - serve também a
    // delta per-cartão.
    var chartCutoff = validSeries.length ? validSeries.map(function (s) { return s.labels[0]; })
      .reduce(function (a, b) { return a > b ? a : b; }) : null;
    distinctTickers.forEach(function (t) {
      var b = benchByTicker[t];
      var anchor = chartCutoff || b.labels[0];
      var idx = b.labels.findIndex(function (l) { return l >= anchor; });
      if (idx < 0) { b.labels = []; b.dataPct = []; return; }
      var base = b.rawData[idx];
      if (!base || !isFinite(base)) { b.labels = []; b.dataPct = []; return; }
      b.labels = b.labels.slice(idx);
      b.dataPct = b.rawData.slice(idx).map(function (v) { return +((v / base - 1) * 100).toFixed(2); });
    });

    // União de labels (funds + benchmarks que vão ser desenhados)
    var allLabelsSet = new Set();
    validSeries.forEach(function (s) { s.labels.forEach(function (l) { allLabelsSet.add(l); }); });
    if (benchmarksVisible) {
      distinctTickers.forEach(function (t) {
        benchByTicker[t].labels.forEach(function (l) { allLabelsSet.add(l); });
      });
    }
    var labels = Array.from(allLabelsSet).sort();
    var isEur = state.mode === 'eur';

    var datasets = pairs.map(function (p, i) {
      var s = seriesList[i];
      if (!s) return null;
      var m = new Map(s.labels.map(function (l, j) { return [l, s.dataPct[j]]; }));
      var alignedPct = labels.map(function (l) { return m.has(l) ? m.get(l) : null; });
      var data = alignedPct.map(function (v) {
        if (v == null) return null;
        return isEur ? +(BASE_EUR * (1 + v / 100)).toFixed(2) : +v.toFixed(2);
      });
      return {
        label: p.fund.name, data: data, spanGaps: true,
        borderColor: SERIES_COLORS[p.slot],
        backgroundColor: SERIES_COLORS[p.slot] + '15',
        borderWidth: 2,
        borderDash: s._real ? [] : [4, 4],
        pointRadius: 0, pointHoverRadius: 4,
        tension: 0.1, fill: false
      };
    }).filter(Boolean);

    // Datasets dos benchmarks (cinza tracejado). Só desenhar quando há
    // 1-2 tickers distintos (regra multi-risco). Segundo ticker usa dash
    // pattern diferente para o distinguir.
    if (benchmarksVisible) {
      distinctTickers.forEach(function (t, bi) {
        var b = benchByTicker[t];
        if (!b.labels.length) return;
        var m = new Map(b.labels.map(function (l, j) { return [l, b.dataPct[j]]; }));
        var alignedPct = labels.map(function (l) { return m.has(l) ? m.get(l) : null; });
        var data = alignedPct.map(function (v) {
          if (v == null) return null;
          return isEur ? +(BASE_EUR * (1 + v / 100)).toFixed(2) : +v.toFixed(2);
        });
        datasets.push({
          label: t + ' · ' + b.name, data: data, spanGaps: true,
          borderColor: '#6B7280',
          backgroundColor: 'transparent',
          borderWidth: 1.5,
          borderDash: bi === 0 ? [6, 4] : [2, 3],
          pointRadius: 0, pointHoverRadius: 3,
          tension: 0.1, fill: false
        });
      });
    }

    var noteEl = document.getElementById('lpc-chart-note');
    if (noteEl) {
      var baseTxt = isEur
        ? 'Investimento simulado de ' + fmtNumPT(BASE_EUR) + '€ no início do período.'
        : 'Retorno acumulado em % desde o início do período.';
      var estTxt = estimated.length
        ? ' Curva estimada (tracejada) para: ' + estimated.join(', ') + '.'
        : '';
      noteEl.textContent = baseTxt + estTxt;
    }

    if (chart) chart.destroy();

    chart = new Chart(ctx, {
      type: 'line',
      data: { labels: labels, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#121721',
            padding: 10,
            titleFont: { size: 12, family: 'Inter, sans-serif' },
            bodyFont: { size: 13, family: 'Inter, sans-serif' },
            cornerRadius: 12,
            callbacks: {
              title: function (items) {
                var d = new Date(labels[items[0].dataIndex]);
                return d.toLocaleDateString('pt-PT', { day: '2-digit', month: 'short', year: 'numeric' });
              },
              label: function (item) {
                return ' ' + item.dataset.label + ': '
                  + (isEur ? fmtEurDec(item.parsed.y)
                           : ((item.parsed.y >= 0 ? '+' : '') + item.parsed.y.toFixed(2).replace('.', ',') + '%'));
              }
            }
          }
        },
        scales: {
          x: {
            type: 'category',
            grid: { display: false },
            ticks: {
              font: { size: 11, family: 'Inter, sans-serif' },
              color: '#96A0B0',
              maxTicksLimit: 6,
              autoSkip: true,
              callback: function (val) {
                var label = this.getLabelForValue(val);
                var d = new Date(label);
                if (state.period === 'ytd' || state.period === '1y') {
                  return d.toLocaleDateString('pt-PT', { month: 'short' });
                }
                return d.getFullYear();
              }
            }
          },
          y: {
            ticks: {
              callback: function (v) {
                if (isEur) return fmtEurDec(v);
                return (v >= 0 ? '+' : '') + v.toFixed(2).replace('.', ',') + '%';
              },
              font: { size: 11.5, family: 'Inter, sans-serif' },
              color: '#697386'
            },
            grid: { color: '#F2F4F7' }
          }
        }
      }
    });

    // returns strip - usa o valor final da série rebased (coerente com
    // o que o gráfico mostra). Em modo €, o valor final fica como
    // destaque principal e a % como secundário.
    var strip = document.getElementById('lpc-returns-strip');
    strip.innerHTML = '';
    pairs.forEach(function (p, i) {
      var f = p.fund;
      var s = seriesList[i];
      var finalPct = (s && s.dataPct && s.dataPct.length)
        ? s.dataPct[s.dataPct.length - 1]
        : null;
      var naHtml = '<div class="lpc-return-value"><span style="color:#96A0B0">-</span></div>';
      var valueHtml;
      if (finalPct == null || Number.isNaN(finalPct)) {
        valueHtml = naHtml;
      } else {
        var pctStr = (finalPct >= 0 ? '+' : '') + finalPct.toFixed(2).replace('.', ',') + '%';
        var pctCls = finalPct >= 0 ? 'pos' : 'neg';
        if (isEur) {
          var finalEur = BASE_EUR * (1 + finalPct / 100);
          var intPart = Math.floor(finalEur);
          var dec = Math.round((finalEur - intPart) * 100).toString().padStart(2, '0');
          valueHtml =
            '<div class="lpc-return-value">' + fmtNumPT(intPart) + ',' + dec + '€</div>'
            + '<div class="lpc-return-sub ' + pctCls + '">' + pctStr + '</div>';
        } else {
          valueHtml = '<div class="lpc-return-value ' + pctCls + '">' + pctStr + '</div>';
        }
      }
      // Delta vs ETF de referência - só aparece se o toggle está ligado
      // e se o fundo tem benchmark_ticker mapeado.
      var vsHtml = '';
      if (state.showBenchmark && f.benchmarkTicker && benchByTicker[f.benchmarkTicker]) {
        var bench = benchByTicker[f.benchmarkTicker];
        var benchFinalPct = (bench.dataPct && bench.dataPct.length)
          ? bench.dataPct[bench.dataPct.length - 1] : null;
        if (benchFinalPct != null && finalPct != null) {
          var delta = +(finalPct - benchFinalPct).toFixed(2);
          var deltaStr = (delta >= 0 ? '+' : '') + delta.toFixed(2).replace('.', ',') + ' p.p.';
          var deltaCls = delta >= 0 ? 'pos' : 'neg';
          vsHtml = '<div class="lpc-return-vs-bench">'
            + 'vs ' + f.benchmarkTicker + ' ('
            + (benchFinalPct >= 0 ? '+' : '') + benchFinalPct.toFixed(2).replace('.', ',') + '%'
            + '): <span class="' + deltaCls + '">' + deltaStr + '</span>'
            + '</div>';
        }
      }
      var cell = document.createElement('div');
      cell.className = 'lpc-return-cell';
      cell.innerHTML =
        '<div class="lpc-return-name">'
        + '<span class="lpc-swatch" style="background:' + SERIES_COLORS[p.slot] + '"></span>'
        + '<span class="lpc-return-name-text">' + f.name + '</span>'
        + '</div>'
        + valueHtml
        + vsHtml;
      strip.appendChild(cell);
    });

    // Nota do benchmark - mostra quando o toggle está on: explica o(s)
    // ETF(s) ou avisa que foram escondidos do chart por excesso de riscos.
    var benchNoteEl = document.getElementById('lpc-benchmark-note');
    if (benchNoteEl) {
      if (benchmarksHiddenMixed) {
        benchNoteEl.style.display = '';
        benchNoteEl.textContent =
          'Seleccionaste PPR de ' + distinctTickers.length + ' níveis de risco diferentes - '
          + 'ETFs de referência escondidos no gráfico para não saturar. '
          + 'A diferença de rentabilidade vs cada ETF continua visível em cada cartão abaixo.';
      } else if (benchmarksVisible && distinctTickers.length) {
        benchNoteEl.style.display = '';
        var names = distinctTickers.map(function (t) { return t; }).join(' + ');
        benchNoteEl.textContent = 'Referência (linha cinza): ' + names
          + '. ETFs não são PPR - sem benefício fiscal, mas com liquidez imediata.';
      } else {
        benchNoteEl.style.display = 'none';
        benchNoteEl.textContent = '';
      }
    }

    // Warnings - perfil de risco divergente + frequência de dados
    renderWarnings(pairs);
  }

  var WARN_SVG = '<svg width="18" height="18" viewBox="0 0 20 20" fill="none">'
    + '<path d="M10 2.5l8.5 15H1.5l8.5-15z" stroke="#B54708" stroke-width="1.5" stroke-linejoin="round"/>'
    + '<path d="M10 8v4M10 14.5v.01" stroke="#B54708" stroke-width="1.6" stroke-linecap="round"/>'
    + '</svg>';

  function renderWarnings(pairs) {
    var el = document.getElementById('lpc-risk-warning');
    if (!el) return;
    var warnings = [];

    // Risk class divergence (≥2 classes de distância entre fundos)
    var classes = pairs
      .map(function (p) { return p.fund.riskClass; })
      .filter(function (v) { return v != null; });
    if (classes.length >= 2) {
      var mn = Math.min.apply(null, classes);
      var mx = Math.max.apply(null, classes);
      if (mx - mn >= 2) {
        warnings.push('Comparação com perfis de risco diferentes (classe ' + mn + ' vs ' + mx
          + '). Rentabilidades de fundos com maior exposição a acções não são directamente '
          + 'comparáveis com as de fundos mais conservadores - o risco assumido é substancialmente distinto.');
      }
    }

    // Frequência mensal (Oxy Capital): avisar que as métricas de risco
    // e o detalhe do gráfico são menos precisos que os PPRs com histórico
    // diário. Detecção pelo prefixo do nome - todos os Oxy começam
    // por 'OXY CAPITAL'.
    var monthly = pairs
      .map(function (p) { return p.fund.name; })
      .filter(function (n) { return /^oxy capital/i.test(n); });
    if (monthly.length) {
      warnings.push('O(s) fundo(s) ' + monthly.join(', ')
        + ' publicam cotações apenas em base mensal (não diária). '
        + 'O gráfico mostra um ponto por mês e as métricas de risco '
        + '(volatilidade, drawdown, VaR) são calculadas com essa granularidade - '
        + 'menos precisas do que para PPRs com cotação diária.');
    }

    if (!warnings.length) { el.innerHTML = ''; return; }
    el.innerHTML = warnings.map(function (w) {
      return '<div class="lpc-warning">' + WARN_SVG + '<span>' + w + '</span></div>';
    }).join('');
  }

  // -----------------------------------------------------------
  // COMPARE TABLE
  // -----------------------------------------------------------
  function renderCompareTable() {
    var pairs = pairedSelected();
    var head = document.getElementById('lpc-compare-head');
    var body = document.getElementById('lpc-compare-body');
    head.innerHTML = '<th></th>' + pairs.map(function (p) {
      return '<th class="lpc-fund-col">'
        + '<span class="lpc-swatch-inline" style="background:' + SERIES_COLORS[p.slot] + '"></span>'
        + p.fund.name
        + '<span class="lpc-fund-meta">' + (p.fund.manager || '') + '</span>'
        + '</th>';
    }).join('');

    var rows = [
      { label: 'ISIN',                    render: function (f) { return f.isin || NA; } },
      { label: 'Data de início do PPR',
        tip: 'Data da primeira cotação disponível para este PPR. Pode ser posterior à data de constituição oficial se a fonte de dados não tem histórico mais antigo.',
        render: function (f) {
          var s = f._backendSeries && f._backendSeries.since;
          if (!s || !s.labels || !s.labels.length) return NA;
          var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s.labels[0]);
          return m ? (m[3] + '/' + m[2] + '/' + m[1]) : s.labels[0];
        } },
      { label: 'TEC (custo anual)',       tip: 'Taxa de encargos correntes. Percentagem anual cobrada pela gestora sobre o valor do fundo.',
        render: function (f) { return fmt(f.tec, '%'); } },
      { label: 'Subscrição mínima',       render: function (f) { return f.minSubs == null ? NA : fmtNumPT(f.minSubs) + '€'; } },
      { label: 'Classe de risco',         tip: 'Indicador sintético de risco (ISR) numa escala de 1 (menor risco, potencial retorno menor) a 7 (maior risco, potencial retorno maior). Definido pela gestora ao abrigo do regime PPR.',
        render: function (f) {
          if (f.riskClass == null) return NA;
          var rc = f.riskClass;
          var bars = '';
          for (var i = 1; i <= 7; i++) {
            bars += '<span class="lpc-risk-bar h' + i
              + (i <= rc ? ' is-filled' : '') + '"></span>';
          }
          return '<span class="lpc-risk-pill" aria-label="Classe de risco '
            + rc + ' em 7">'
            + '<span class="lpc-risk-bars" aria-hidden="true">' + bars + '</span>'
            + '<span>' + rc + '/7</span>'
            + '</span>';
        } },
      { label: 'Rentabilidade 1 ano',     render: function (f) { return formatPct(f.returns['1y']); } },
      { label: 'Rentabilidade 3 anos',
        tip: 'Valor anualizado: retorno médio por ano nos últimos 3 anos. Equivale à taxa anual constante que, capitalizada durante 3 anos, produziria o retorno total acumulado no período. Mostrado apenas para fundos com pelo menos 3 anos de histórico.',
        render: function (f) { return formatPct(f.returns['3y']); } },
      { label: 'Rentabilidade 5 anos',
        tip: 'Valor anualizado: retorno médio por ano nos últimos 5 anos. Mostrado apenas para fundos com pelo menos 5 anos de histórico.',
        render: function (f) { return formatPct(f.returns['5y']); } },
      { label: 'Rentabilidade 10 anos',
        tip: 'Valor anualizado: retorno médio por ano nos últimos 10 anos. Mostrado apenas para fundos com pelo menos 10 anos de histórico.',
        render: function (f) { return formatPct(f.returns['10y']); } },
      { label: 'Retorno anualizado',
        tip: 'CAGR (Compound Annual Growth Rate) calculado sobre todo o histórico disponível. Equivale à taxa anual constante que, aplicada ao capital inicial, produziria o retorno total acumulado desde a primeira cotação até hoje.',
        render: function (f) {
          var v = formatPct(f.returns.ann);
          if (f.returns.ann == null) return v;
          var yrs = f.returns.ann_years;
          if (yrs) v += ' <span style="color:#96A0B0;font-weight:500;font-size:11px">(' + yrs.toLocaleString('pt-PT').replace('.', ',') + 'a)</span>';
          return v;
        } }
    ];

    body.innerHTML = rows.map(function (r) {
      return '<tr><th scope="row">' + labelWithTip(r.label, r.tip) + '</th>'
        + pairs.map(function (p) { return '<td>' + r.render(p.fund) + '</td>'; }).join('')
        + '</tr>';
    }).join('');
  }

  // -----------------------------------------------------------
  // RISK TABLE
  // -----------------------------------------------------------
  // Para cada data em fundLabels, devolve o último close do benchmark
  // em ou antes dessa data. O benchmark vem diário e é maior do que a
  // série downsampled do fundo; isto dá-nos preços alinhados.
  function alignBenchmarkToLabels(fundLabels, bench) {
    if (!bench || !bench.labels || !bench.labels.length) return null;
    var out = new Array(fundLabels.length);
    var bi = 0;
    for (var i = 0; i < fundLabels.length; i++) {
      var target = fundLabels[i];
      while (bi + 1 < bench.labels.length && bench.labels[bi + 1] <= target) bi++;
      // se o primeiro benchmark label é posterior ao fund label, pula
      if (bench.labels[bi] > target) {
        out[i] = null;
      } else {
        out[i] = bench.data[bi];
      }
    }
    return out;
  }

  // Calcula beta entre a série rebased do fundo (dataPct) e a do benchmark
  // alinhada. Retornos sample-a-sample; beta = cov(fund, bench) / var(bench).
  function betaFromRebasedSeries(labels, dataPct, bench) {
    var benchAligned = alignBenchmarkToLabels(labels, bench);
    if (!benchAligned) return null;
    var fundPx = dataPct.map(function (v) { return 1 + v / 100; });
    var fundR = [], benchR = [];
    for (var i = 1; i < labels.length; i++) {
      if (benchAligned[i] == null || benchAligned[i - 1] == null) continue;
      if (fundPx[i - 1] <= 0 || benchAligned[i - 1] <= 0) continue;
      fundR.push(fundPx[i] / fundPx[i - 1] - 1);
      benchR.push(benchAligned[i] / benchAligned[i - 1] - 1);
    }
    if (fundR.length < 10) return null;
    var meanF = fundR.reduce(function (a, b) { return a + b; }, 0) / fundR.length;
    var meanB = benchR.reduce(function (a, b) { return a + b; }, 0) / benchR.length;
    var cov = 0, varB = 0;
    for (var j = 0; j < fundR.length; j++) {
      cov += (fundR[j] - meanF) * (benchR[j] - meanB);
      varB += (benchR[j] - meanB) * (benchR[j] - meanB);
    }
    if (varB <= 0) return null;
    return cov / varB;
  }

  // Recalcula vol/sharpe/maxDD/VaR a partir de uma série dataPct (% desde
  // a base) - usado quando comparamos múltiplos fundos e queremos métricas
  // sobre a janela comum (não desde a inception de cada um). A série é
  // downsampled (~250 pts), por isso anualizamos pela frequência efectiva.
  function riskFromRebasedSeries(labels, dataPct) {
    if (!labels || labels.length < 10) return {};
    // converte % em "preço" relativo
    var px = dataPct.map(function (v) { return 1 + v / 100; });
    var rets = [];
    for (var i = 1; i < px.length; i++) {
      if (px[i - 1] > 0) rets.push(px[i] / px[i - 1] - 1);
    }
    if (rets.length < 5) return {};
    // anualização: nº médio de samples por ano
    var firstD = new Date(labels[0]);
    var lastD = new Date(labels[labels.length - 1]);
    var years = (lastD - firstD) / (365.25 * 86400000);
    if (years <= 0) return {};
    var samplesPerYear = rets.length / years;
    var mean = rets.reduce(function (a, b) { return a + b; }, 0) / rets.length;
    var variance = rets.reduce(function (a, b) { return a + (b - mean) * (b - mean); }, 0) / rets.length;
    var std = Math.sqrt(variance);
    var vol = std * Math.sqrt(samplesPerYear) * 100;
    var rf = 0.025;
    var sharpe = std > 0 ? (mean * samplesPerYear - rf) / (std * Math.sqrt(samplesPerYear)) : null;
    // max drawdown sobre a série de preços relativos
    var peak = px[0], maxDD = 0;
    for (var j = 0; j < px.length; j++) {
      if (px[j] > peak) peak = px[j];
      var dd = (px[j] - peak) / peak;
      if (dd < maxDD) maxDD = dd;
    }
    // VaR 95% sobre os retornos por sample (não anualizado)
    var sorted = rets.slice().sort(function (a, b) { return a - b; });
    var idx = Math.floor(sorted.length * 0.05);
    var var95 = sorted[idx] * 100;
    return {
      vol: vol,
      sharpe: sharpe,
      maxDD: maxDD * 100,
      var95: var95,
      samplesPerYear: samplesPerYear
    };
  }

  function renderRiskTable() {
    var pairs = pairedSelected();
    var head = document.getElementById('lpc-risk-head');
    var body = document.getElementById('lpc-risk-body');
    head.innerHTML = '<th></th>' + pairs.map(function (p) {
      return '<th class="lpc-fund-col">'
        + '<span class="lpc-swatch-inline" style="background:' + SERIES_COLORS[p.slot] + '"></span>'
        + p.fund.name + '</th>';
    }).join('');

    // Constrói as séries 'since' rebased à data comum (mesma lógica do chart).
    // Quando há 2+ fundos seleccionados, métricas são recalculadas sobre essa
    // janela. Com 1 fundo, mostra os valores pré-calculados (toda a história).
    var rebasedRisk = pairs.map(function () { return null; });
    var rebaseInfo = null;
    if (pairs.length >= 2) {
      var rebased = pairs.map(function (p) {
        var s = p.fund._backendSeries && p.fund._backendSeries.since;
        if (!s || !s.labels || !s.labels.length) return null;
        return { labels: s.labels.slice(), dataPct: s.data.slice() };
      });
      var withData = rebased.filter(Boolean);
      if (withData.length >= 2) {
        var cutoff = withData.map(function (s) { return s.labels[0]; })
          .reduce(function (a, b) { return a > b ? a : b; });
        rebased.forEach(function (s) {
          if (!s) return;
          if (s.labels[0] >= cutoff) return;
          var idx = s.labels.findIndex(function (l) { return l >= cutoff; });
          if (idx > 0) {
            var base = s.dataPct[idx];
            s.labels = s.labels.slice(idx);
            s.dataPct = s.dataPct.slice(idx).map(function (v) { return +(v - base).toFixed(4); });
          }
        });
        rebasedRisk = rebased.map(function (s) {
          if (!s) return null;
          var r = riskFromRebasedSeries(s.labels, s.dataPct);
          if (BENCHMARK) {
            r.beta = betaFromRebasedSeries(s.labels, s.dataPct, BENCHMARK);
          }
          return r;
        });
        // Data final = DATA_AS_OF (latest_data_date global do JSON) para
        // coerência com o rodapé 'Atualizado a …'. Tecnicamente, o MIN
        // de last_price_date dos fundos seleccionados seria a 'janela
        // comum exacta', mas a diferença é tipicamente de 1-3 dias e a
        // inconsistência visual com o rodapé confunde mais que ajuda.
        var lastDate = DATA_AS_OF ||
          withData[0].labels[withData[0].labels.length - 1];
        rebaseInfo = { from: cutoff, to: lastDate };
      }
    }

    function pickRisk(p, key) {
      var idx = pairs.indexOf(p);
      var rb = rebasedRisk[idx];
      if (rb && rb[key] != null && isFinite(rb[key])) return rb[key];
      return p.fund.risk ? p.fund.risk[key] : null;
    }

    var rows = [
      { label: 'Volatilidade anual',
        tip: 'Desvio-padrão anualizado dos retornos. Mede quanto o fundo oscila.',
        render: function (p) { return fmt(pickRisk(p, 'vol'), '%', 2); } },
      { label: 'Sharpe Ratio',
        tip: 'Retorno em excesso por unidade de risco (usa taxa sem risco de 2,5%). Acima de 1 é considerado bom.',
        render: function (p) { return fmt(pickRisk(p, 'sharpe'), '', 2); } },
      { label: 'Drawdown máximo',
        tip: 'Maior queda do valor do fundo desde um pico, no período analisado.',
        render: function (p) {
          var v = pickRisk(p, 'maxDD');
          return v == null ? NA
            : '<span style="color:#B42318;font-weight:600">' + v.toFixed(2).replace('.', ',') + '%</span>';
        } },
      { label: 'VaR (95%)',
        tip: 'Perda máxima esperada num período típico, com 95% de confiança. Quando há comparação multi-fundo, é calculado sobre amostragem semanal/mensal da janela comum.',
        render: function (p) { return fmt(pickRisk(p, 'var95'), '%', 2); } },
      { label: 'Beta',
        tip: 'Sensibilidade do fundo aos movimentos do mercado global de acções, medida contra o MSCI World (ETF URTH em EUR). Beta = 1 significa que o fundo oscila ao mesmo ritmo do mercado; Beta < 1 é menos volátil; Beta > 1 amplifica os movimentos. Quando há comparação multi-fundo, é recalculado sobre a janela comum.',
        render: function (p) { return fmt(pickRisk(p, 'beta'), '', 2); } }
    ];

    var bodyHtml = rows.map(function (r) {
      return '<tr><th scope="row">' + labelWithTip(r.label, r.tip) + '</th>'
        + pairs.map(function (p) { return '<td>' + r.render(p) + '</td>'; }).join('')
        + '</tr>';
    }).join('');

    if (rebaseInfo) {
      bodyHtml += '<tr><td colspan="' + (pairs.length + 1) + '" '
        + 'style="padding-top:14px;font-size:12px;color:#5C6878;text-align:center;border:none">'
        + 'Todas as métricas (incluindo Beta) calculadas sobre a janela '
        + 'comum dos fundos seleccionados ('
        + rebaseInfo.from + ' → ' + rebaseInfo.to + ').'
        + '</td></tr>';
    }
    body.innerHTML = bodyHtml;
  }

  // -----------------------------------------------------------
  // WIRING
  // -----------------------------------------------------------
  root.querySelectorAll('#lpc-period-tabs .lpc-tab').forEach(function (btn) {
    btn.addEventListener('click', function () {
      root.querySelectorAll('#lpc-period-tabs .lpc-tab').forEach(function (b) { b.classList.remove('is-active'); });
      btn.classList.add('is-active');
      state.period = btn.dataset.period;
      renderAll();
    });
  });
  root.querySelectorAll('#lpc-mode-tabs .lpc-tab').forEach(function (btn) {
    btn.addEventListener('click', function () {
      root.querySelectorAll('#lpc-mode-tabs .lpc-tab').forEach(function (b) { b.classList.remove('is-active'); });
      btn.classList.add('is-active');
      state.mode = btn.dataset.mode;
      renderAll();
    });
  });
  var benchCheckbox = document.getElementById('lpc-benchmark-checkbox');
  if (benchCheckbox) {
    benchCheckbox.addEventListener('change', function () {
      state.showBenchmark = benchCheckbox.checked;
      renderAll();
    });
  }

  function renderAll() {
    renderSelector();
    renderChart();
    renderCompareTable();
    renderRiskTable();
  }

  function wireSlots() {
    var slots = root.querySelectorAll('.lpc-slot');
    slots.forEach(function (slot) {
      var idx = parseInt(slot.dataset.slot, 10);
      var input = slot.querySelector('.lpc-slot-input');
      var clearBtn = slot.querySelector('.lpc-slot-clear');

      function openDropdown() {
        // Slot preenchido: não abrir dropdown. Utilizador só pode limpar
        // via botão × - evita perder a seleção por engano ao clicar.
        if (state.selected[idx]) return;
        selectorState.activeSlot = idx;
        selectorState.query = '';
        selectorState.highlightIdx = 0;
        renderDropdown();
      }
      // focus: desktop + mobile normal flow
      input.addEventListener('focus', openDropdown);
      // click: fallback para iOS Safari em iframe cross-origin, onde
      // focus nem sempre dispara no primeiro tap (sobretudo se o
      // utilizador tinha outro input focado antes).
      input.addEventListener('click', openDropdown);
      input.addEventListener('blur', function () {
        setTimeout(function () {
          if (selectorState.activeSlot === idx) {
            selectorState.activeSlot = -1;
            renderDropdown();
          }
        }, 150);
      });
      input.addEventListener('input', function (e) {
        if (state.selected[idx]) return;
        selectorState.activeSlot = idx;
        selectorState.query = e.target.value;
        selectorState.highlightIdx = 0;
        renderDropdown();
      });
      input.addEventListener('keydown', function (e) {
        if (state.selected[idx]) return;
        var matches = filterFunds(selectorState.query);
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          selectorState.highlightIdx = Math.min(matches.length - 1, selectorState.highlightIdx + 1);
          renderDropdown();
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          selectorState.highlightIdx = Math.max(0, selectorState.highlightIdx - 1);
          renderDropdown();
        } else if (e.key === 'Enter' && matches[selectorState.highlightIdx]) {
          e.preventDefault();
          selectFundInSlot(idx, matches[selectorState.highlightIdx].id);
        } else if (e.key === 'Escape') {
          selectorState.activeSlot = -1;
          renderDropdown();
          input.blur();
        }
      });
      clearBtn.addEventListener('click', function (e) {
        e.preventDefault();
        clearSlot(idx);
      });
    });
  }

  // -----------------------------------------------------------
  // DATA LOADING
  // -----------------------------------------------------------
  async function fetchWithRetry(url, opts, attempts) {
    attempts = attempts || 3;
    var lastErr;
    for (var i = 0; i < attempts; i++) {
      try {
        var res = await fetch(url, opts);
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res;
      } catch (e) {
        lastErr = e;
        // Backoff exponencial: 300ms, 900ms, 2700ms. Cobre blips
        // transitórios do CDN do GitHub Pages (503/timeout ocasionais).
        if (i < attempts - 1) {
          await new Promise(function (r) { setTimeout(r, 300 * Math.pow(3, i)); });
        }
      }
    }
    throw lastErr;
  }

  async function loadData() {
    try {
      var bust = Math.floor(Date.now() / (5 * 60 * 1000));
      var url = DATA_URL + (DATA_URL.indexOf('?') !== -1 ? '&' : '?') + 'v=' + bust;
      var res = await fetchWithRetry(url, { cache: 'no-store' }, 3);
      var json = await res.json();
      if (!json.funds || !Array.isArray(json.funds) || json.funds.length === 0) {
        throw new Error('JSON sem fundos');
      }
      // Mostrar apenas fundos com histórico diário real. Os CMVM-only
      // (que apareciam com curva tracejada estimada) são ocultados do
      // selector - evita sugerir comparações pouco fidedignas.
      FUNDS = json.funds
        .filter(function (f) { return !f.hidden && f.data_origin === 'historical'; })
        .map(normalizeBackendFund);
      DATA_AS_OF = json.latest_data_date || json.data_as_of || null;
      BENCHMARK = json.benchmark || null;
      BENCHMARKS_BY_TICKER = json.benchmarks || {};
      USING_MOCK = false;
    } catch (e) {
      LOAD_ERROR = e.message || String(e);
      if (console && console.warn) console.warn('[comparador-ppr] fetch falhou após retries, usando mock:', LOAD_ERROR);
      USING_MOCK = true;
    }
    // Arranque sem fundos seleccionados - utilizador escolhe activamente
    // via os 3 slots. Evita a impressão errada de que os 3 default são
    // sempre a comparação relevante.
    state.selected = [null, null, null];
    updateBadge();
  }

  // Tooltip positioning - calculado em JS para escapar a containing
  // blocks com overflow (ex: .lpc-table-wrap com overflow-x:auto) que
  // antes cortavam a bolha em Chrome. Também uniformiza comportamento
  // entre Safari e Chrome, onde a estratégia anterior de left:50% +
  // translateX dentro de tabela rendia mal em Safari desktop.
  function positionTip(icon) {
    var bubble = icon.querySelector('.lpc-tip-bubble');
    if (!bubble) return;
    // getBoundingClientRect funciona com visibility:hidden, logo
    // medimos a bolha sem a mostrar.
    var ir = icon.getBoundingClientRect();
    var br = bubble.getBoundingClientRect();
    var margin = 8;
    var gap = 6;
    var vw = document.documentElement.clientWidth || window.innerWidth;
    var vh = document.documentElement.clientHeight || window.innerHeight;

    var iconCenterX = ir.left + ir.width / 2;
    var x = iconCenterX - br.width / 2;
    var y = ir.top - br.height - gap;
    var below = false;
    // Sem espaço acima: vira para baixo.
    if (y < margin) {
      y = ir.bottom + gap;
      below = true;
    }
    // Clamp horizontal para não cortar nas margens do viewport.
    if (x < margin) x = margin;
    if (x + br.width > vw - margin) x = vw - br.width - margin;

    // Posiciona a seta sobre o centro do ícone (relativa à bolha).
    var arrowX = iconCenterX - x;
    if (arrowX < 12) arrowX = 12;
    if (arrowX > br.width - 12) arrowX = br.width - 12;

    bubble.style.setProperty('--lpc-tip-x', Math.round(x) + 'px');
    bubble.style.setProperty('--lpc-tip-y', Math.round(y) + 'px');
    bubble.style.setProperty('--lpc-arrow-x', Math.round(arrowX) + 'px');
    bubble.classList.toggle('is-below', below);
  }
  function showTip(icon) {
    var bubble = icon.querySelector('.lpc-tip-bubble');
    if (!bubble) return;
    positionTip(icon);
    bubble.classList.add('is-visible');
  }
  function hideTip(icon) {
    var bubble = icon.querySelector('.lpc-tip-bubble');
    if (bubble) bubble.classList.remove('is-visible');
  }

  // Hover (desktop): mouseover/out delegados com check de relatedTarget
  // para não piscar quando o cursor passa entre filhos do mesmo ícone.
  root.addEventListener('mouseover', function (e) {
    var icon = e.target && e.target.closest ? e.target.closest('.lpc-info-icon') : null;
    if (!icon) return;
    if (e.relatedTarget && icon.contains(e.relatedTarget)) return;
    showTip(icon);
  });
  root.addEventListener('mouseout', function (e) {
    var icon = e.target && e.target.closest ? e.target.closest('.lpc-info-icon') : null;
    if (!icon) return;
    if (e.relatedTarget && icon.contains(e.relatedTarget)) return;
    // Preserva tooltips "pinned" por tap até próximo click.
    if (icon.classList.contains('is-open')) return;
    hideTip(icon);
  });
  // Teclado (Tab/Shift+Tab para acessibilidade)
  root.addEventListener('focusin', function (e) {
    var icon = e.target && e.target.closest ? e.target.closest('.lpc-info-icon') : null;
    if (icon) showTip(icon);
  });
  root.addEventListener('focusout', function (e) {
    var icon = e.target && e.target.closest ? e.target.closest('.lpc-info-icon') : null;
    if (!icon) return;
    if (icon.classList.contains('is-open')) return;
    hideTip(icon);
  });

  // Tap (mobile) toggle - o title nativo não dispara em touch. Tap num
  // ícone pinna a bolha (classe is-open) até nova interacção; tap fora
  // fecha tudo.
  root.addEventListener('click', function (e) {
    var icon = e.target && e.target.closest ? e.target.closest('.lpc-info-icon') : null;
    // Fecha outras bolhas pinnadas.
    root.querySelectorAll('.lpc-info-icon.is-open').forEach(function (el) {
      if (el !== icon) {
        el.classList.remove('is-open');
        hideTip(el);
      }
    });
    if (icon) {
      e.preventDefault();
      e.stopPropagation();
      var wasOpen = icon.classList.toggle('is-open');
      if (wasOpen) showTip(icon); else hideTip(icon);
    }
  });
  // Esc fecha tudo.
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      root.querySelectorAll('.lpc-info-icon.is-open').forEach(function (el) {
        el.classList.remove('is-open');
      });
      root.querySelectorAll('.lpc-tip-bubble.is-visible').forEach(function (b) {
        b.classList.remove('is-visible');
      });
    }
  });
  // Reposiciona bolhas visíveis em scroll/resize - com position:fixed
  // o browser não reposiciona automaticamente quando o ícone se move.
  var __repositionOpenTips = function () {
    root.querySelectorAll('.lpc-tip-bubble.is-visible').forEach(function (b) {
      var icon = b.parentElement;
      if (icon && icon.classList && icon.classList.contains('lpc-info-icon')) {
        positionTip(icon);
      }
    });
  };
  window.addEventListener('scroll', __repositionOpenTips, { passive: true });
  window.addEventListener('resize', __repositionOpenTips);

  async function init() {
    if (typeof Chart === 'undefined') { setTimeout(init, 50); return; }
    try { await loadData(); } catch (e) {
      if (console && console.warn) console.warn('loadData failed:', e);
    }
    try { wireSlots(); } catch (e) {
      if (console && console.warn) console.warn('wireSlots failed:', e);
    }
    try { renderAll(); } catch (e) {
      if (console && console.warn) console.warn('renderAll failed:', e);
    }
    try { reportHeight(); } catch (e) {
      if (console && console.warn) console.warn('reportHeight failed:', e);
    }
  }

  var __sendHeight = function () {};
  var __scheduleHeight = function () {};
  function reportHeight() {
    if (window.parent === window) return;
    var last = 0;
    var t = null;
    __sendHeight = function send() {
      // scrollHeight ignora overflow:hidden (que temos no html/body para
      // esconder scrollbars internas). getBoundingClientRect iria dar
      // apenas a altura da viewport do iframe (ex. 2400px do fallback do
      // Webflow), não a altura real do conteúdo.
      var h = Math.ceil(Math.max(
        document.body ? document.body.scrollHeight : 0,
        document.documentElement.scrollHeight
      ));
      // Se houver um dropdown de selector aberto (PPR 1/2/3), estende
      // a altura para incluir o seu bottom: dropdowns são position:
      // absolute e não entram no scrollHeight, logo ficam clipados
      // pelo overflow:hidden de #lf-pc-calc. Sobretudo no PPR 3 (mais
      // abaixo no layout), o dropdown extrapolava o fundo do iframe.
      // Fallback: mesmo que o rect do dropdown ainda não esteja
      // laid-out (acabou de ser apendido ao DOM), usar a base do
      // slot-wrap + max-height conhecido (320px) como estimativa
      // garantida.
      var dd = document.querySelector('.lpc-dropdown.is-open');
      if (dd) {
        var scrollY = window.pageYOffset ||
          (document.documentElement && document.documentElement.scrollTop) || 0;
        var r = dd.getBoundingClientRect();
        var bottomFromDd = r.height > 0 ? r.bottom + scrollY : 0;
        var wrap = dd.parentElement;
        var bottomFromWrap = 0;
        if (wrap) {
          var wr = wrap.getBoundingClientRect();
          bottomFromWrap = wr.bottom + scrollY + 6 + 320;
        }
        var bottom = Math.max(bottomFromDd, bottomFromWrap) + 12;
        if (bottom > h) h = Math.ceil(bottom);
      }
      // Threshold de 4px evita postMessage spam por reflows espúrios de
      // 1-2px (hover, tooltips, font-loading) que em Chrome mobile
      // com Lenis smooth scroll conseguiam empancar o scroll da página
      // mãe ao fim de alguns segundos.
      if (h && Math.abs(h - last) > 4) {
        last = h;
        window.parent.postMessage({ type: 'ppr-height', height: h }, '*');
      }
    };
    __scheduleHeight = function () {
      if (t) return;
      // Debounce agressivo (200ms) — mais um colchão para não saturar
      // o parent em Chrome mobile.
      t = setTimeout(function () { t = null; __sendHeight(); }, 200);
    };
    __sendHeight();
    // ResizeObserver: Safari 13.1+ (May 2020). Em Safari antigos não
    // existe; caímos num fallback com setInterval leve.
    try {
      if (typeof ResizeObserver !== 'undefined') {
        new ResizeObserver(__scheduleHeight).observe(document.documentElement);
      } else {
        setInterval(__scheduleHeight, 1000);
      }
    } catch (err) {
      setInterval(__scheduleHeight, 1000);
    }
    window.addEventListener('load', __sendHeight);
    // Um só re-fire após ~500ms para capturar a altura pós-layout do
    // Chart.js + fontes. Os 1500/3000ms anteriores causavam flushes
    // desnecessários que em Chrome mobile chegavam a empancar a Lenis.
    setTimeout(__sendHeight, 600);
  }

  // Forwards APENAS o wheel event para a página mãe. Safari desktop
  // em iframe cross-origin não propaga wheel nativamente (o scroll
  // "trava" ao passar o rato sobre o iframe) — daí o workaround via
  // postMessage.
  //
  // Em mobile NÃO fazemos forward de touch: os browsers móveis já
  // propagam touch scroll através de iframes nativamente. O nosso
  // forward anterior estava a competir com o scroll nativo e causava
  // tremor. -webkit-overflow-scrolling:touch + overscroll-behavior:
  // contain nos scrollables internos (.lpc-dropdown, .lpc-table-wrap)
  // cuidam do resto.
  function forwardScroll() {
    try {
      if (window.parent === window) return;
      window.addEventListener('wheel', function (e) {
        // Se estiver sobre um elemento com scroll interno activo
        // (dropdown, tabela com overflow), aplica o scroll directamente
        // nesse elemento em vez de forwardar. Safari cross-origin
        // ignora o scroll nativo em alguns casos, por isso fazemos à
        // mão: scrollTop += deltaY.
        var el = e.target;
        while (el && el !== document.body) {
          if (el.nodeType === 1) {
            var cs = getComputedStyle(el);
            var oy = cs.overflowY;
            if ((oy === 'auto' || oy === 'scroll') && el.scrollHeight > el.clientHeight) {
              var st = el.scrollTop;
              var atTop = st <= 0 && e.deltaY < 0;
              var atBottom = st + el.clientHeight >= el.scrollHeight - 1 && e.deltaY > 0;
              if (!atTop && !atBottom) {
                e.preventDefault();
                el.scrollTop = st + e.deltaY;
                return;
              }
              break;
            }
          }
          el = el.parentNode;
        }
        e.preventDefault();
        window.parent.postMessage({ type: 'ppr-scroll', deltaY: e.deltaY }, '*');
      }, { passive: false });
    } catch (err) {
      // Safari antigo ou contexto restrito: o embed continua a
      // funcionar, só sem forward de scroll. Melhor que crashar.
      if (console && console.warn) console.warn('forwardScroll: ' + err);
    }
  }
  forwardScroll();

  init();
})();
