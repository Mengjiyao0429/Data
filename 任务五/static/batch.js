/* 任务五 · 需求驱动批次前端（独立模块，不干扰基线看板） */
(function () {
  'use strict';

  const $ = (s) => document.querySelector(s);
  const el = (id) => document.getElementById(id);

  const S = { bid: null, data: null, timer: null, detailCid: null, proposal: null };
  const PAL = ['#2E5C8A', '#4F81BD', '#7BA7CD', '#3F9DB3', '#7BA24A', '#E8894A', '#C0504D'];

  async function api(path, opts) {
    const o = Object.assign({ headers: {} }, opts || {});
    o.headers = Object.assign({ 'Content-Type': 'application/json' }, o.headers);
    const res = await fetch(path, o);
    let d = {};
    try { d = await res.json(); } catch (e) { d = { error: '响应解析失败' }; }
    if (!res.ok) throw new Error(d.error || ('HTTP ' + res.status));
    return d;
  }

  function toast(msg, ms) {
    const t = el('toast');
    if (!t) return;
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(toast._t);
    toast._t = setTimeout(() => t.classList.remove('show'), ms || 2600);
  }

  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function fmt(n) { return (n === null || n === undefined || n === '') ? '—' : Number(n).toLocaleString('zh-CN'); }

  function md(mdText) {
    const lines = esc(mdText).split('\n');
    const out = [];
    let inList = false;
    const close = () => { if (inList) { out.push('</ul>'); inList = false; } };
    lines.forEach((raw) => {
      const l = raw.trim();
      if (!l) { close(); return; }
      const inline = l.replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/(https?:\/\/[^\s<)]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
      if (/^###\s/.test(l)) { close(); out.push('<h3>' + inline.slice(4) + '</h3>'); return; }
      if (/^##\s/.test(l)) { close(); out.push('<h2>' + inline.slice(3) + '</h2>'); return; }
      if (/^#\s/.test(l)) { close(); out.push('<h1>' + inline.slice(2) + '</h1>'); return; }
      if (/^&gt;\s/.test(l)) { close(); out.push('<blockquote>' + inline.slice(5) + '</blockquote>'); return; }
      if (/^[-*]\s/.test(l)) { if (!inList) { out.push('<ul>'); inList = true; } out.push('<li>' + inline.slice(2) + '</li>'); return; }
      close();
      out.push('<p>' + inline + '</p>');
    });
    close();
    return out.join('\n');
  }

  /* ---------------- 来源清单 ---------------- */
  async function loadSources() {
    const box = el('rqSources');
    if (!box) return;
    try {
      const d = await api('/api/sources');
      box.innerHTML = d.items.map((it) => {
        const on = d.default.indexOf(it.key) >= 0 || it.key === 'csdn' ? 'checked' : '';
        return '<label class="chk"><input type="checkbox" value="' + it.key + '" ' + on + '> ' + esc(it.label) + '</label>';
      }).join('');
      el('rqHint').textContent = d.proxy ? ('网络代理可用：' + d.proxy) : '未检测到代理（GitHub/HN 可能失败，可勾选本地回放）';
    } catch (e) { box.textContent = '来源加载失败：' + e.message; }
  }

  function chosenSources() {
    return Array.from(el('rqSources').querySelectorAll('input:checked')).map((x) => x.value);
  }

  /* ---------------- 批次列表 ---------------- */
  async function loadBatches() {
    const tb = el('tblBatches');
    if (!tb) return;
    try {
      const d = await api('/api/batches');
      if (!d.items.length) {
        tb.innerHTML = '<tr><td colspan="9" class="empty">还没有批次，先在上方发起一次需求</td></tr>';
        return;
      }
      tb.innerHTML = d.items.map((b) => {
        const st = b.status === 'done' ? '<span class="tag ok">已完成</span>'
          : b.status === 'running' ? '<span class="tag warn">采集中…</span>'
            : b.status === 'failed' ? '<span class="tag bad">失败</span>' : esc(b.status || '—');
        return '<tr>' +
          '<td><b>' + esc(b.bid) + '</b></td>' +
          '<td>' + esc(b.query) + (b.note ? '<div class="muted">' + esc(b.note) + '</div>' : '') + '</td>' +
          '<td class="muted">' + (b.sources || []).map(esc).join('、') + '</td>' +
          '<td>' + fmt(b.records) + '</td><td>' + fmt(b.opportunities) + '</td><td>' + fmt(b.clusters) + '</td>' +
          '<td>' + st + '</td><td>' + (b.elapsed ? b.elapsed + 's' : '—') + '</td>' +
          '<td><button class="btn mini" data-open="' + esc(b.bid) + '">查看</button> ' +
          '<button class="btn mini ghost" data-rep="' + esc(b.bid) + '"' + (b.status === 'done' ? '' : ' disabled') + '>报告</button></td>' +
          '</tr>';
      }).join('');
      tb.querySelectorAll('[data-open]').forEach((b) => b.addEventListener('click', () => openBatch(b.dataset.open)));
      tb.querySelectorAll('[data-rep]').forEach((b) => b.addEventListener('click',
        () => window.open('/api/batches/' + b.dataset.rep + '/report', '_blank')));
      if (d.items.some((b) => b.status === 'running')) schedulePoll(loadBatches, 3000);
    } catch (e) { tb.innerHTML = '<tr><td colspan="9" class="empty">列表加载失败：' + esc(e.message) + '</td></tr>'; }
  }

  function schedulePoll(fn, ms) {
    if (S.timer) clearTimeout(S.timer);
    S.timer = setTimeout(fn, ms || 3000);
  }

  /* ---------------- 发起需求 ---------------- */
  async function startRequirement() {
    const q = el('rqQuery').value.trim();
    if (!q) { toast('请填写需求关键词'); el('rqQuery').focus(); return; }
    const srcs = chosenSources();
    if (!srcs.length) { toast('请至少勾选一个采集来源'); return; }
    const target = Number(el('rqTarget').value || 600);
    el('btnRunReq').disabled = true;
    try {
      const r = await api('/api/requirements', { method: 'POST', body: JSON.stringify({ query: q, sources: srcs, target: target, note: el('rqNote').value.trim() }) });
      toast('已创建批次 ' + r.bid + '，正在采集…', 3200);
      S.bid = r.bid;
      location.hash = 'batch/' + r.bid;
      renderBatchLoading(r.bid);
      await pollBatch(r.bid);
      loadBatches();
    } catch (e) { toast('发起失败：' + e.message, 4000); }
    finally { el('btnRunReq').disabled = false; }
  }

  /* ---------------- 批次详情 ---------------- */
  function renderBatchLoading(bid) {
    el('bNotice').className = 'notice blue';
    el('bNotice').innerHTML = '批次 <b>' + esc(bid) + '</b> 正在采集与计算，页面会自动刷新（通常 20–90 秒）。';
    ['bKpiRecords', 'bKpiOpps', 'bKpiClusters', 'bKpiTop'].forEach((id) => { el(id).textContent = '—'; });
    el('bTblClusters').innerHTML = '<tr><td colspan="8" class="empty">计算中…</td></tr>';
    el('bTblRecords').innerHTML = '<tr><td colspan="7" class="empty">计算中…</td></tr>';
  }

  async function pollBatch(bid) {
    try {
      const d = await api('/api/batches/' + bid);
      if (d.status === 'done') { renderBatch(d); return d; }
      if (d.status === 'failed') {
        el('bNotice').className = 'notice';
        el('bNotice').innerHTML = '批次 <b>' + esc(bid) + '</b> 执行失败：' + esc(d.info.error || '未知错误');
        return d;
      }
      renderBatchLoading(bid);
      await new Promise((r) => { S.timer = setTimeout(r, 3500); });
      return await pollBatch(bid);
    } catch (e) {
      el('bNotice').textContent = '批次状态读取失败：' + e.message;
    }
    return null;
  }

  async function openBatch(bid) {
    S.bid = bid;
    S.detailCid = null;
    el('bDetailCard').classList.add('hidden');
    el('page-batch').classList.remove('hidden');
    el('page-new').classList.add('hidden');
    document.querySelectorAll('.nav a').forEach((a) => a.classList.toggle('active', a.dataset.page === 'batch'));
    el('crumb').textContent = '批次分析 · ' + bid;
    const d = await pollBatch(bid);
    if (d && d.status === 'done') loadRecords(bid);
  }

  function renderBatch(d) {
    const m = d.meta;
    const info = d.info;
    el('bNotice').className = 'notice blue';
    el('bNotice').innerHTML = '批次 <b>' + esc(info.bid) + '</b>：需求「' + esc(info.query) + '」；来源 ' +
      (info.sources || []).map(esc).join('、') + '；发起 ' + esc(info.created_at || '') +
      '；耗时 ' + (info.elapsed || '—') + 's；聚类 k=' + (info.clusters || 0) +
      '；轮廓系数 ' + (info.silhouette === null || info.silhouette === undefined ? '—' : info.silhouette);
    el('bKpiRecords').textContent = fmt(m.total_records);
    el('bKpiOpps').textContent = fmt(m.total_opportunities);
    el('bKpiOppsNote').textContent = '占本批次 ' + m.opp_rate + '% · 阈值 0.50';
    el('bKpiClusters').textContent = fmt(m.clusters);
    if (d.clusters.length) {
      const top = d.clusters[0];
      el('bKpiTop').textContent = top.cid;
      el('bKpiTopNote').textContent = top.name + ' · ' + Number(top.score).toFixed(1) + ' 分';
    }
    drawFunnel(m);
    drawRank(d.clusters);
    renderClusterTable(d.clusters);
  }

  function drawFunnel(m) {
    if (typeof echarts === 'undefined') return;
    const box = el('bChartFunnel');
    const c = echarts.getInstanceByDom(box) || echarts.init(box);
    const t = m.total_records || 1;
    const rOpp = m.total_opportunities / t * 100;
    const rClu = m.total_opportunities ? m.clusters / m.total_opportunities * 100 : 0;
    c.setOption({
      tooltip: { trigger: 'item', formatter: (p) => `${p.seriesName}<br/>${p.value.toFixed(1)}%` },
      legend: { bottom: 0, itemWidth: 12, itemHeight: 8, textStyle: { fontSize: 10, color: '#5b6b7c' } },
      series: [
        { name: '机会占比', type: 'pie', radius: ['58%', '78%'], center: ['50%', '44%'], silent: true,
          label: { show: false }, labelLine: { show: false },
          data: [{ value: rOpp, itemStyle: { color: '#5C9E6E' } },
                 { value: 100 - rOpp, itemStyle: { color: '#eef2f7' } }] },
        { name: '簇覆盖率', type: 'pie', radius: ['34%', '52%'], center: ['50%', '44%'],
          label: { show: true, position: 'center', formatter: () => `{a|${rOpp.toFixed(1)}%}\n{b|机会占比}`,
            rich: { a: { fontSize: 24, fontWeight: 700, color: '#2E5C8A', lineHeight: 30 },
                    b: { fontSize: 11, color: '#5b6b7c' } } },
          data: [{ value: rClu, itemStyle: { color: '#4F81BD' } },
                 { value: 100 - rClu, itemStyle: { color: '#eef2f7' } }] },
      ],
    }, true);
  }

  function drawRank(cs) {
    if (typeof echarts === 'undefined' || !cs.length) return;
    const box = el('bChartRank');
    const c = echarts.getInstanceByDom(box) || echarts.init(box);
    c.setOption({
      grid: { left: 60, right: 20, top: 20, bottom: 56 },
      tooltip: { trigger: 'axis', formatter: (p) => p[0].name + '：' + p[0].value + ' 分' },
      xAxis: { type: 'category', data: cs.map((x) => x.cid), axisLabel: { fontSize: 11 } },
      yAxis: { type: 'value', max: 100, axisLabel: { fontSize: 11 } },
      series: [{
        type: 'bar', barMaxWidth: 22,
        itemStyle: { color: (p) => (p.dataIndex === 0 ? '#C0504D' : '#4F81BD') },
        label: { show: true, position: 'top', fontSize: 10, formatter: (p) => p.value.toFixed(1) },
        data: cs.map((x) => Number(x.score)),
      }],
    }, true);
  }

  function renderClusterTable(cs) {
    const tb = el('bTblClusters');
    if (!cs.length) { tb.innerHTML = '<tr><td colspan="8" class="empty">本批次未形成机会簇</td></tr>'; return; }
    tb.innerHTML = cs.map((c) => '<tr data-cid="' + esc(c.cid) + '" style="cursor:pointer">' +
      '<td><b>' + esc(c.cid) + '</b></td><td>' + esc(c.name) + '</td><td>' + esc(c.func || '—') + '</td>' +
      '<td>' + esc(c.industry || '—') + '</td><td>' + c.size + '</td><td>' + (c.sources || []).length + '</td>' +
      '<td>' + Number(c.score).toFixed(1) + '</td><td>' + c.priority + '</td></tr>').join('');
    tb.querySelectorAll('tr[data-cid]').forEach((tr) => tr.addEventListener('click', () => openCluster(tr.dataset.cid)));
  }

  async function openCluster(cid) {
    S.detailCid = cid;
    try {
      const c = await api('/api/batches/' + S.bid + '/clusters/' + cid);
      const dims = c.dims || { src: 0, size: 0, biz: 0 };
      el('bDetailCard').classList.remove('hidden');
      el('bDetailTitle').textContent = cid + ' · ' + c.name;
      el('bDetailHint').textContent = c.size + ' 条机会记录 · 价值 ' + Number(c.score).toFixed(1) + ' · 优先级 ' + c.priority;
      const bar = (lab, v, color) => '<div class="dim-row"><span>' + lab + '</span>' +
        '<div class="dim-bar"><i style="width:' + Math.max(0, Math.min(100, v)) + '%;background:' + color + '"></i></div>' +
        '<b>' + Number(v).toFixed(1) + '</b></div>';
      el('bDetail').innerHTML =
        '<div class="dim-box">' + bar('多源指向', dims.src, '#2E5C8A') + bar('记录规模', dims.size, '#3F9DB3') +
        bar('商业信号', dims.biz, '#E8894A') + '</div>' +
        '<div class="chips">' + (c.sources || []).map((s) => '<span class="chip">' + esc(s.name) + ' ' + s.count + '</span>').join('') + '</div>' +
        '<table class="mini-table"><thead><tr><th style="width:118px">编号</th><th>标题</th><th style="width:112px">来源</th><th style="width:92px">置信度</th><th style="width:110px">原始链接</th></tr></thead><tbody>' +
        (c.evidence || []).map((e) => '<tr><td>' + esc(e.batch + '-' + e.id) + '</td><td>' + esc(e.title) + '</td><td>' + esc(e.src) + '</td><td>' + esc(e.conf) + '</td>' +
          '<td>' + (e.link ? '<a href="' + esc(e.link) + '" target="_blank" rel="noopener">打开原文</a>' : '—') + '</td></tr>').join('') +
        '</tbody></table>' +
        '<div class="actions" style="margin-top:12px"><button class="btn primary" id="btnBGen">生成本批次立项策划案</button></div>';
      el('btnBGen').addEventListener('click', genProposal);
    } catch (e) { toast('详情读取失败：' + e.message); }
  }

  async function genProposal() {
    if (!S.bid || !S.detailCid) return;
    const btn = el('btnBGen');
    btn.disabled = true;
    btn.textContent = '生成中…';
    try {
      const r = await api('/api/batches/' + S.bid + '/proposal', { method: 'POST', body: JSON.stringify({ cid: S.detailCid }) });
      S.proposal = r;
      el('bmTitle').textContent = '立项策划案 · ' + S.bid + ' · ' + r.cid;
      el('bmBody').innerHTML = md(r.markdown);
      el('bmMd').href = '/api/proposals/' + r.id + '/download?fmt=md';
      el('bmDocx').href = '/api/proposals/' + r.id + '/download?fmt=docx';
      el('bModal').classList.add('show');
    } catch (e) { toast('生成失败：' + e.message, 4000); }
    finally { btn.disabled = false; btn.textContent = '生成本批次立项策划案'; }
  }

  async function loadRecords(bid) {
    const tb = el('bTblRecords');
    const q = el('bQ').value.trim();
    const only = el('bOnlyOpp').value;
    tb.innerHTML = '<tr><td colspan="7" class="empty">加载中…</td></tr>';
    try {
      const d = await api('/api/batches/' + bid + '/records?limit=100&only_opp=' + only + '&q=' + encodeURIComponent(q));
      el('bQCount').textContent = '命中 ' + d.total + ' 条（显示前 ' + d.items.length + ' 条）';
      if (!d.items.length) { tb.innerHTML = '<tr><td colspan="7" class="empty">没有符合条件的记录</td></tr>'; return; }
      tb.innerHTML = d.items.map((r) => '<tr>' +
        '<td><b>' + esc(r.batch + '-' + r.id) + '</b></td>' +
        '<td title="' + esc(r.snippet) + '">' + esc((r.title || '').slice(0, 78)) + '</td>' +
        '<td>' + esc(r.source) + '</td><td>' + esc(r.time || '—') + '</td>' +
        '<td>' + (r.is_opp === '1' ? '<span class="tag ok">机会</span>' : '<span class="tag">否</span>') + '</td>' +
        '<td>' + esc(r.conf || '—') + '</td>' +
        '<td>' + (r.link ? '<a href="' + esc(r.link) + '" target="_blank" rel="noopener">原文</a> ' : '') +
        '<span class="muted" title="' + esc(r.snapshot) + '">快照</span></td>' +
        '</tr>').join('');
    } catch (e) { tb.innerHTML = '<tr><td colspan="7" class="empty">读取失败：' + esc(e.message) + '</td></tr>'; }
  }

  /* ---------------- 事件绑定 ---------------- */
  function bind() {
    if (el('btnRunReq')) el('btnRunReq').addEventListener('click', startRequirement);
    if (el('btnBQ')) el('btnBQ').addEventListener('click', () => loadRecords(S.bid));
    if (el('bQ')) el('bQ').addEventListener('keydown', (e) => { if (e.key === 'Enter') loadRecords(S.bid); });
    if (el('btnBReport')) el('btnBReport').addEventListener('click',
      () => { if (S.bid) window.open('/api/batches/' + S.bid + '/report', '_blank'); });
    if (el('bmClose')) el('bmClose').addEventListener('click', () => el('bModal').classList.remove('show'));
    if (el('bModal')) el('bModal').addEventListener('click', (e) => { if (e.target.id === 'bModal') el('bModal').classList.remove('show'); });

    window.addEventListener('page:change', (e) => {
      const name = e.detail.name;
      if (name === 'new') loadBatches();
      if (name === 'batch') {
        const hash = (location.hash || '').replace('#', '');
        const parts = hash.split('/');
        const bid = parts[0] === 'batch' && parts[1] ? decodeURIComponent(parts[1]) : S.bid;
        if (bid) openBatch(bid);
        else el('bNotice').textContent = '还没有选择批次：请先在「需求发起」发起一次需求。';
      }
    });

    loadSources();
    loadBatches();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind);
  else bind();
})();
