/* 任务五 · 数据分析占比看板 + 智能问答 */
(function () {
  'use strict';
  const el = (id) => document.getElementById(id);
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

  async function loadInsight() {
    if (loaded) { setTimeout(resize, 60); return; }
    try {
      const r = await fetch('/api/analytics');
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || '加载失败');
      loaded = true;
      const mk = (id) => { const c = echarts.init(el(id)); charts[id] = c; return c; };

      // ===== 全流程转化 · 彩色桑基流向 + 环形占比 =====
      const stages = d.funnel || [];
      const total = stages.length ? stages[0].value : 1;
      const sk = d.sankey || { nodes: [], links: [] };

      // 科研调色板：高辨识度多色，节点与流向按主题着色
      const SK = {
        '采集清洗去重': '#2563eb',   // 靛蓝
        'AI应用机会':   '#0d9488',   // 青绿
        '未构成机会':   '#94a3b8',   // 灰蓝
        '其他机会':     '#64748b',
      };
      const TOP_COLORS = ['#e11d48', '#7c3aed', '#ea580c', '#0891b2', '#16a34a',
                          '#d946ef', '#ca8a04', '#4f46e5', '#db2777', '#0d9488'];
      const nodeColor = (name, idx) => SK[name] || TOP_COLORS[(idx - 3 + TOP_COLORS.length) % TOP_COLORS.length];

      // (1) 彩色桑基流向图：采集 → 机会/非机会 → 各主题簇，宽度即规模
      const skNodes = sk.nodes.map((n, i) => ({ ...n, itemStyle: { color: nodeColor(n.name, i) } }));
      const skLinks = sk.links.map((l) => ({
        ...l,
        lineStyle: { color: nodeColor(l.target, sk.nodes.findIndex((n) => n.name === l.target)) },
      }));
      mk('insFunnel').setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item', triggerOn: 'mousemove',
          formatter: (p) => p.dataType === 'edge'
            ? `<b>${p.data.source} → ${p.data.target}</b><br/>${p.data.value.toLocaleString()} 条`
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
      });

      // (2) 环形进度：机会率 / 簇覆盖率 / 高价值方向 三层同心环
      const opp = stages[1] ? stages[1].value : 0;
      const clu = stages[2] ? stages[2].value : 0;
      const oppRate = total ? +(opp / total * 100).toFixed(1) : 0;
      const covRate = opp ? +(clu / opp * 100).toFixed(1) : 0;
      const valRate = opp ? +(Math.min(clu, opp) / opp * 100).toFixed(1) : 0;
      mk('insFunnelRate').setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item', formatter: (p) => `${p.seriesName}<br/>${p.value}%` },
        legend: { bottom: 2, itemWidth: 12, itemHeight: 8, textStyle: { fontSize: 11, color: '#64748b' } },
        series: [
          { name: '机会率', type: 'pie', radius: ['72%', '88%'], center: ['50%', '44%'], silent: true,
            label: { show: false }, labelLine: { show: false },
            data: [{ value: oppRate, itemStyle: { color: '#0d9488' } },
                   { value: 100 - oppRate, itemStyle: { color: '#e8eef4' } }] },
          { name: '簇覆盖率', type: 'pie', radius: ['52%', '68%'], center: ['50%', '44%'], silent: true,
            label: { show: false }, labelLine: { show: false },
            data: [{ value: covRate, itemStyle: { color: '#2563eb' } },
                   { value: 100 - covRate, itemStyle: { color: '#e8eef4' } }] },
          { name: '高价值方向', type: 'pie', radius: ['30%', '46%'], center: ['50%', '44%'],
            label: { show: true, position: 'center', formatter: () => `{a|${oppRate}%}\n{b|机会占比}`,
              rich: { a: { fontSize: 30, fontWeight: 700, color: '#0f766e', lineHeight: 36 },
                      b: { fontSize: 11, color: '#64748b' } } },
            data: [{ value: valRate, itemStyle: { color: '#ea580c' } },
                   { value: 100 - valRate, itemStyle: { color: '#e8eef4' } }] },
        ],
      });

      mk('insSourcePie').setOption(pieOption('来源', d.source_share));
      mk('insFuncPie').setOption(pieOption('功能', d.func_share));
      mk('insIndPie').setOption(pieOption('行业', d.industry_share));

      mk('insConf').setOption({
        color: ['#4F81BD'],
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: d.confidence_hist.map((x) => x.bucket) },
        yAxis: { type: 'value' },
        series: [{ type: 'bar', data: d.confidence_hist.map((x) => x.count), barWidth: '60%' }],
      });

      mk('insBatchBar').setOption({
        color: ['#3F9DB3'],
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: d.opp_by_batch.map((x) => x.batch) },
        yAxis: { type: 'value' },
        series: [{ type: 'bar', data: d.opp_by_batch.map((x) => x.opps), barWidth: '55%',
                  label: { show: true, position: 'top', fontSize: 10 } }],
      });

      const vt = d.value_top.slice().reverse();
      mk('insValueBar').setOption({
        color: ['#7BA24A'],
        tooltip: { trigger: 'axis' },
        grid: { left: 120, right: 30 },
        xAxis: { type: 'value' },
        yAxis: { type: 'category', data: vt.map((x) => x.cid + ' ' + (x.name || '').slice(0, 8)), axisLabel: { fontSize: 10 } },
        series: [{ type: 'bar', data: vt.map((x) => x.score), label: { show: true, position: 'right', fontSize: 10 } }],
      });
    } catch (e) {
      el('insFunnel').innerHTML = '<p class="hint">加载失败：' + e.message + '</p>';
    }
  }

  function resize() { Object.values(charts).forEach((c) => c.resize && c.resize()); }

  /* 问答 */
  async function ask(q) {
    q = (q || el('askInput').value || '').trim();
    if (!q) return;
    el('askAnswer').textContent = '正在检索本地分析结果…';
    try {
      const r = await fetch('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' },
                                          body: JSON.stringify({ question: q }) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || '提问失败');
      el('askAnswer').textContent = d.answer || '（无回答）';
    } catch (e) {
      el('askAnswer').textContent = '错误：' + e.message;
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
    if (e.detail.name === 'insight') loadInsight();
    if (e.detail.name === 'ask') resize();
  });
  window.addEventListener('resize', () => { if (loaded) resize(); });
})();
