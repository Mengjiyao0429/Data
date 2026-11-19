/* 智掘 AI Discovery · 数据分析看板 + 智能问答（双语） */
(function () {
  'use strict';
  const el = (id) => document.getElementById(id);
  const T = (s) => (window.T ? window.T(s) : s);
  const PALETTE = ['#2E5C8A', '#4F81BD', '#7BA7CD', '#3F9DB3', '#7BA24A', '#E8894A', '#C0504D', '#8AA0B6', '#9B7EBD', '#5DA89A'];
  let charts = {};
  let loaded = false;

  function pieOption(title, data, unit) {
    return {
      color: PALETTE,
      tooltip: { trigger: 'item', formatter: (p) => `${p.name}<br/>${p.value} (${p.data.pct}%)` },
      legend: { type: 'scroll', orient: 'vertical', right: 4, top: 'center', textStyle: { fontSize: 11 },
                formatter: (n) => n.length > 12 ? n.slice(0, 12) + '…' : n },
      series: [{
        name: title, type: 'pie', radius: ['38%', '68%'], center: ['36%', '52%'],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: '#fff', borderWidth: 2 },
        label: { show: true, formatter: '{d}%', fontSize: 10 },
        data: data.slice(0, 12).map((d) => ({ name: d.name, value: d.value, pct: d.pct })),
      }],
    };
  }

  async function loadInsight(force) {
    if (loaded && !force) { setTimeout(resize, 60); return; }
    try {
      const r = await fetch('/api/analytics');
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || T('加载失败'));
      if (force) { dispose(); }
      loaded = true;
      const mk = (id) => { const box = el(id); if (!box) return null; const c = echarts.init(box); charts[id] = c; return c; };

      const stages = d.funnel || [];
      const total = stages.length ? stages[0].value : 1;
      const sk = d.sankey || { nodes: [], links: [] };

      const SK = {};
      SK[T('采集清洗去重')] = '#2563eb';
      SK[T('AI应用机会')] = '#0d9488';
      SK[T('未构成机会')] = '#94a3b8';
      SK[T('其他机会')] = '#64748b';
      const RAW_SK = { '采集清洗去重': '#2563eb', 'AI应用机会': '#0d9488', '未构成机会': '#94a3b8', '其他机会': '#64748b' };
      const TOP_COLORS = ['#e11d48', '#7c3aed', '#ea580c', '#0891b2', '#16a34a',
                          '#d946ef', '#ca8a04', '#4f46e5', '#db2777', '#0d9488'];
      const nodeColor = (name, idx) => RAW_SK[name] || SK[name] || TOP_COLORS[(idx - 3 + TOP_COLORS.length) % TOP_COLORS.length];
      const labelOf = (name) => (T(name) || name);

      const c1 = mk('insFunnel');
      if (c1) {
        const skNodes = sk.nodes.map((n, i) => ({ name: labelOf(n.name), itemStyle: { color: nodeColor(n.name, i) } }));
        const skLinks = sk.links.map((l) => ({
          source: labelOf(l.source), target: labelOf(l.target), value: l.value,
          lineStyle: { color: nodeColor(l.target, sk.nodes.findIndex((n) => n.name === l.target)) },
        }));
        c1.setOption({
          backgroundColor: 'transparent',
          tooltip: { trigger: 'item', triggerOn: 'mousemove',
            formatter: (p) => p.dataType === 'edge'
              ? `<b>${p.data.source} → ${p.data.target}</b><br/>${p.data.value.toLocaleString()} ${T('条')}`
              : `<b>${p.name}</b>` },
          series: [{
            type: 'sankey', left: 10, right: 116, top: 14, bottom: 14,
            data: skNodes, links: skLinks,
            nodeWidth: 18, nodeGap: 11, draggable: false,
            emphasis: { focus: 'adjacency' },
            label: { color: '#1e293b', fontSize: 11, fontWeight: 500 },
            lineStyle: { opacity: 0.34, curveness: 0.52 },
            itemStyle: { borderWidth: 0 },
          }],
        }, true);
      }

      const opp = stages[1] ? stages[1].value : 0;
      const clu = stages[2] ? stages[2].value : 0;
      const oppRate = total ? +(opp / total * 100).toFixed(1) : 0;
      const covRate = opp ? +(clu / opp * 100).toFixed(1) : 0;
      const valRate = opp ? +(Math.min(clu, opp) / opp * 100).toFixed(1) : 0;
      const c2 = mk('insFunnelRate');
      if (c2) c2.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item', formatter: (p) => `${p.seriesName}<br/>${p.value}%` },
        legend: { bottom: 2, itemWidth: 11, itemHeight: 7, textStyle: { fontSize: 10, color: '#64748b' } },
        series: [
          { name: T('机会率'), type: 'pie', radius: ['72%', '88%'], center: ['50%', '44%'], silent: true,
            label: { show: false }, labelLine: { show: false },
            data: [{ value: oppRate, itemStyle: { color: '#0d9488' } },
                   { value: 100 - oppRate, itemStyle: { color: '#e8eef4' } }] },
          { name: T('簇覆盖率'), type: 'pie', radius: ['52%', '68%'], center: ['50%', '44%'], silent: true,
            label: { show: false }, labelLine: { show: false },
            data: [{ value: covRate, itemStyle: { color: '#2563eb' } },
                   { value: 100 - covRate, itemStyle: { color: '#e8eef4' } }] },
          { name: T('高价值方向'), type: 'pie', radius: ['30%', '46%'], center: ['50%', '44%'],
            label: { show: true, position: 'center', formatter: () => `{a|${oppRate}%}\n{b|${T('机会占比')}}`,
              rich: { a: { fontSize: 26, fontWeight: 700, color: '#0f766e', lineHeight: 32 },
                      b: { fontSize: 10, color: '#64748b' } } },
            data: [{ value: valRate, itemStyle: { color: '#ea580c' } },
                   { value: 100 - valRate, itemStyle: { color: '#e8eef4' } }] },
        ],
      });

      const c3 = mk('insSourcePie'); if (c3) c3.setOption(pieOption(T('来源'), d.source_share));
      const c4 = mk('insFuncPie'); if (c4) c4.setOption(pieOption(T('功能类别'), d.func_share));
      const c5 = mk('insIndPie'); if (c5) c5.setOption(pieOption(T('所属行业'), d.industry_share));

      const c6 = mk('insConf'); if (c6) c6.setOption({
        color: ['#4F81BD'],
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: d.confidence_hist.map((x) => x.bucket) },
        yAxis: { type: 'value' },
        series: [{ type: 'bar', data: d.confidence_hist.map((x) => x.count), barWidth: '60%' }],
      });

      const c7 = mk('insBatchBar'); if (c7) c7.setOption({
        color: ['#3F9DB3'],
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: d.opp_by_batch.map((x) => x.batch) },
        yAxis: { type: 'value' },
        series: [{ type: 'bar', data: d.opp_by_batch.map((x) => x.opps), barWidth: '55%',
                  label: { show: true, position: 'top', fontSize: 10 } }],
      });

      const vt = d.value_top.slice().reverse();
      const c8 = mk('insValueBar'); if (c8) c8.setOption({
        color: ['#7BA24A'],
        tooltip: { trigger: 'axis' },
        grid: { left: 108, right: 28 },
        xAxis: { type: 'value' },
        yAxis: { type: 'category', data: vt.map((x) => x.cid + ' ' + (x.name || '').slice(0, 8)), axisLabel: { fontSize: 10 } },
        series: [{ type: 'bar', data: vt.map((x) => x.score), label: { show: true, position: 'right', fontSize: 10 } }],
      });
    } catch (e) {
      const box = el('insFunnel');
      if (box) box.innerHTML = '<p class="hint">' + T('加载失败：') + e.message + '</p>';
    }
  }

  function dispose() {
    Object.values(charts).forEach((c) => { try { c.dispose(); } catch (e) {} });
    charts = {};
  }
  function resize() { Object.values(charts).forEach((c) => c.resize && c.resize()); }

  /* 问答 */
  async function ask(q) {
    q = (q || el('askInput').value || '').trim();
    if (!q) return;
    el('askAnswer').textContent = T('正在检索本地分析结果…');
    try {
      const r = await fetch('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' },
                                          body: JSON.stringify({ question: q }) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || T('提问失败'));
      el('askAnswer').textContent = d.answer || T('（无回答）');
    } catch (e) {
      el('askAnswer').textContent = T('错误：') + e.message;
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    const btn = el('btnAsk');
    if (btn) btn.addEventListener('click', () => ask());
    const inp = el('askInput');
    if (inp) inp.addEventListener('keydown', (e) => { if (e.key === 'Enter') ask(); });
    document.querySelectorAll('.ask-q').forEach((b) => b.addEventListener('click', () => ask(b.textContent.trim())));
  });

  window.addEventListener('page:change', (e) => {
    if (e.detail.name === 'insight') loadInsight(false);
    if (e.detail.name === 'ask') resize();
  });
  window.addEventListener('resize', () => { if (loaded) resize(); });
  window.addEventListener('i18n:change', () => {
    if (!el('page-insight').classList.contains('hidden')) loadInsight(true);
    else { loaded = false; }
  });
})();
