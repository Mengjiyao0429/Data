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

      // ===== 全流程转化 · 三种可视化组合（替换传统漏斗）=====
      const stages = d.funnel || [];
      const total = stages.length ? stages[0].value : 1;
      const sk = d.sankey || { nodes: [], links: [] };

      // (1) 桑基流向图：采集 → 机会/非机会 → 各主题簇，宽度即规模
      mk('insFunnel').setOption({
        tooltip: { trigger: 'item', triggerOn: 'mousemove',
          formatter: (p) => p.dataType === 'edge'
            ? `${p.data.source} → ${p.data.target}<br/>${p.data.value.toLocaleString()} 条`
            : `${p.name}` },
        series: [{
          type: 'sankey', left: 8, right: 96, top: 12, bottom: 12,
          data: sk.nodes, links: sk.links,
          nodeWidth: 16, nodeGap: 10, draggable: false,
          emphasis: { focus: 'adjacency' },
          label: { color: '#33445a', fontSize: 11, fontWeight: 500 },
          lineStyle: { color: 'gradient', opacity: 0.42, curveness: 0.5 },
          itemStyle: { borderWidth: 0, color: (p) =>
            p.name === '采集清洗去重' ? '#3E6FB0'
            : p.name === 'AI应用机会' ? '#5C9E6E'
            : p.name === '未构成机会' ? '#B9C4D1'
            : ['#4F81BD', '#E08A4B', '#7BA24A', '#9B7EBD', '#3F9DB3', '#C0504D', '#8AA0B6', '#7BA24A', '#5DA89A', '#E8894A'][(p.dataIndex - 3) % 10] },
        }],
      });

      // (2) 环形进度：机会率 / 簇覆盖率 / 高价值率 三层同心环
      const opp = stages[1] ? stages[1].value : 0;
      const clu = stages[2] ? stages[2].value : 0;
      const oppRate = total ? +(opp / total * 100).toFixed(1) : 0;
      const covRate = opp ? +(clu / opp * 100).toFixed(1) : 0;
      const valRate = opp ? +(Math.min(clu, opp) / opp * 100).toFixed(1) : 0;
      mk('insFunnelRate').setOption({
        tooltip: { trigger: 'item', formatter: (p) => `${p.seriesName}<br/>${p.value}%` },
        legend: { bottom: 0, itemWidth: 12, itemHeight: 8, textStyle: { fontSize: 10, color: '#5b6b7c' } },
        series: [
          { name: '机会率', type: 'pie', radius: ['72%', '86%'], center: ['50%', '44%'], silent: true,
            label: { show: false }, labelLine: { show: false },
            data: [{ value: oppRate, itemStyle: { color: '#5C9E6E' } },
                   { value: 100 - oppRate, itemStyle: { color: '#eef2f7' } }] },
          { name: '簇覆盖率', type: 'pie', radius: ['52%', '66%'], center: ['50%', '44%'], silent: true,
            label: { show: false }, labelLine: { show: false },
            data: [{ value: covRate, itemStyle: { color: '#4F81BD' } },
                   { value: 100 - covRate, itemStyle: { color: '#eef2f7' } }] },
          { name: '高价值方向', type: 'pie', radius: ['30%', '44%'], center: ['50%', '44%'],
            label: { show: true, position: 'center', formatter: () => `{a|${oppRate}%}\n{b|机会占比}`,
              rich: { a: { fontSize: 26, fontWeight: 700, color: '#2E5C8A', lineHeight: 34 },
                      b: { fontSize: 11, color: '#5b6b7c' } } },
            data: [{ value: valRate, itemStyle: { color: '#E08A4B' } },
                   { value: 100 - valRate, itemStyle: { color: '#eef2f7' } }] },
        ],
      });

      // (3) 阶梯瀑布：逐级收窄的下降台阶，标注每级数值与保留率
      const wfNames = stages.map((s) => s.name);
      const wfVals = stages.map((s) => s.value);
      const wfColors = ['#3E6FB0', '#5C9E6E', '#E08A4B'];
      mk('insWaterfall').setOption({
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' },
          formatter: (ps) => ps.filter((p) => p.seriesName !== '占位').map((p) =>
            `${p.name}<br/>${p.value.toLocaleString()} 条 · 保留 ${(p.value / total * 100).toFixed(1)}%`).join('<br/>') },
        grid: { left: 92, right: 56, top: 24, bottom: 30 },
        xAxis: { type: 'value', max: total, axisLabel: { show: false }, splitLine: { show: false }, axisTick: { show: false } },
        yAxis: { type: 'category', inverse: true, data: wfNames,
          axisLabel: { color: '#33445a', fontSize: 11, fontWeight: 500 }, axisLine: { show: false }, axisTick: { show: false } },
        series: [
          { name: '占位', type: 'bar', stack: 'wf', silent: true, itemStyle: { color: 'transparent' },
            data: wfVals.map((v, i) => total - v), barWidth: 26 },
          { name: '规模', type: 'bar', stack: 'wf', barWidth: 26,
            label: { show: true, position: 'right', color: '#33445a', fontSize: 11, fontWeight: 600,
              formatter: (p) => `${wfVals[p.dataIndex].toLocaleString()} · ${(wfVals[p.dataIndex] / total * 100).toFixed(1)}%` },
            data: wfVals.map((v, i) => ({ value: v, itemStyle: { color: wfColors[i % wfColors.length], borderRadius: [0, 5, 5, 0] } })) },
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
