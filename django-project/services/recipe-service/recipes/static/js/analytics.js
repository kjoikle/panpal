(function () {
  'use strict';

  function el(id) { return document.getElementById(id); }

  function number(n) { return (typeof n === 'number') ? n : 0; }

  function formatPct(n) {
    if (!n && n !== 0) return '—';
    return (n * 100).toFixed(1) + '%';
  }

  var url = window.ANALYTICS_URL || '/analytics/';

  fetch(url, { credentials: 'same-origin' })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.error) {
        console.error('analytics error', data.error);
        return;
      }

      var totalImpr = number(data.total_impressions);
      var totalClicks = number(data.total_clicks);
      var impressionsBy = (data.impressions_by_variant || []).reduce(function (acc, item) {
        acc[item.variant] = item.count; return acc;
      }, {});
      var clicksBy = (data.clicks_by_variant || []).reduce(function (acc, item) {
        acc[item.variant] = item.count; return acc;
      }, {});

      el('total-impressions').textContent = totalImpr;
      el('total-clicks').textContent = totalClicks;
      el('conversion').textContent = totalImpr ? formatPct(totalClicks / totalImpr) : '—';

      // Variant labels from the page (server-side injected into template)
      var variantALabel = (window.VARIANT_A_LABEL || document.querySelector('strong') && document.querySelector('strong').textContent) || 'A';
      // But the template uses visible text, so we'll infer labels from table note if possible
      var labels = {
        A: (window.VARIANT_A_LABEL || '{{A}}'),
        B: (window.VARIANT_B_LABEL || '{{B}}')
      };

      // Build table rows
      var tbody = el('variant-rows');
      tbody.innerHTML = '';
      ['A','B'].forEach(function (v) {
        var impr = number(impressionsBy[v]);
        var clk = number(clicksBy[v]);
        var conv = impr ? (clk / impr) : null;

        var tr = document.createElement('tr');
        var tdVariant = document.createElement('td'); tdVariant.textContent = v; tr.appendChild(tdVariant);
        var tdLabel = document.createElement('td'); tdLabel.textContent = (v === 'A') ? (window.__VARIANT_LABEL_A || 'kudos') : (window.__VARIANT_LABEL_B || 'thanks'); tr.appendChild(tdLabel);
        var tdImpr = document.createElement('td'); tdImpr.textContent = impr; tr.appendChild(tdImpr);
        var tdClk = document.createElement('td'); tdClk.textContent = clk; tr.appendChild(tdClk);
        var tdConv = document.createElement('td'); tdConv.textContent = (conv === null) ? '—' : formatPct(conv); tr.appendChild(tdConv);

        tbody.appendChild(tr);
      });

      // Prepare chart datasets
      var ctxI = document.getElementById('impressionsChart').getContext('2d');
      var ctxC = document.getElementById('clicksChart').getContext('2d');

      var labelsArr = ['A','B'];
      var displayLabels = [window.__VARIANT_LABEL_A || 'A', window.__VARIANT_LABEL_B || 'B'];
      var impressionsData = labelsArr.map(function (v) { return number(impressionsBy[v]); });
      var clicksData = labelsArr.map(function (v) { return number(clicksBy[v]); });

      new Chart(ctxI, {
        type: 'bar',
        data: {
          labels: displayLabels,
          datasets: [{ label: 'Impressions', data: impressionsData, backgroundColor: ['#4f46e5','#ec4899'] }]
        },
        options: { responsive: true, maintainAspectRatio: false }
      });

      new Chart(ctxC, {
        type: 'bar',
        data: {
          labels: displayLabels,
          datasets: [{ label: 'Clicks', data: clicksData, backgroundColor: ['#0ea5a4','#f59e0b'] }]
        },
        options: { responsive: true, maintainAspectRatio: false }
      });

    })
    .catch(function (err) { console.error('fetch analytics failed', err); });

})();
