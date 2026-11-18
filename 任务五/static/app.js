/* 任务五 前端交互 */
(function () {
  'use strict';

  const state = {
    meta: null, clusters: [], filters: null, settings: null, stats: null,
    me: null,
    checked: new Set(), current: null, proposal: null, charts: {}, chartsReady: false,
  };

  const $ = (s) => document.querySelector(s);
  const el = (id) => document.getElementById(id);

  async function api(path, opts) {
    const o = Object.assign({ headers: {} }, opts || {});
    o.headers = Object.assign({ 'Content-Type': 'application/json' }, o.headers);
    const res = await fetch(path, o);
    let data = {};
    try { data = await res.json(); } catch (e) { data = { error: '响应解析失败' }; }
    if (res.status === 401 && data.need_login) { location.href = '/login'; throw new Error('未登录'); }
    if (!res.ok) throw new Error(data.error || ('HTTP ' + res.status));
    return data;
  }

  function toast(msg, ms) {
    const t = el('toast');
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(toast._t);
    toast._t = setTimeout(() => t.classList.remove('show'), ms || 2600);
  }

  function fmt(n) { return (n === null || n === undefined) ? '—' : Number(n).toLocaleString('zh-CN'); }

  /* ---------------- Markdown -> HTML（先转义再渲染，避免注入） ---------------- */
  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function inline(s) {
    return s
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/(https?:\/\/[^\s<)]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
  }
  function mdToHtml(md) {
    const lines = esc(md || '').split('\n');
    const out = [];
    let list = false;
    const closeList = () => { if (list) { out.push('</ul>'); list = false; } };
    lines.forEach((raw) => {
      const line = raw.trim();
      if (!line) { closeList(); return; }
      if (/^###\s/.test(line)) { closeList(); out.push('<h3>' + inline(line.slice(4)) + '</h3>'); return; }
      if (/^##\s/.test(line)) { closeList(); out.push('<h2>' + inline(line.slice(3)) + '</h2>'); return; }
      if (/^#\s/.test(line)) { closeList(); out.push('<h1>' + inline(line.slice(2)) + '</h1>'); return; }
      if (/^&gt;\s/.test(line)) { closeList(); out.push('<blockquote>' + inline(line.slice(5)) + '</blockquote>'); return; }
      if (/^[-*]\s/.test(line)) {
        if (!list) { out.push('<ul>'); list = true; }
        out.push('<li>' + inline(line.slice(2)) + '</li>'); return;
      }
      if (/^---+$/.test(line)) { closeList(); out.push('<hr>'); return; }
      closeList();
      out.push('<p>' + inline(line) + '</p>');
    });
    closeList();
    return out.join('\n');
  }

  /* ---------------- 页面切换 ---------------- */
  const PAGES = { new: '需求发起', overview: '概览看板', insight: '数据分析', batch: '批次分析', select: '机会选取', ask: '智能问答', library: '策划案库', settings: '系统设置' };
  function showPage(name) {
    document.querySelectorAll('.nav a').forEach((a) => a.classList.toggle('active', a.dataset.page === name));
    Object.keys(PAGES).forEach((k) => el('page-' + k).classList.toggle('hidden', k !== name));
    el('crumb').textContent = PAGES[name] || name;
    if (name === 'overview') { initCharts(); setTimeout(resizeCharts, 60); }
    if (name === 'library') loadLibrary();
    window.dispatchEvent(new CustomEvent('page:change', { detail: { name: name } }));
  }
  document.querySelectorAll('.nav a').forEach((a) => {
    a.addEventListener('click', () => { location.hash = a.dataset.page; showPage(a.dataset.page); });
  });

  /* ---------------- 会话身份（服务端下发，不可伪造） ---------------- */
  function applyMe(me) {
    state.me = me;
    const isDecision = me && me.role === 'decision';
    el('userPill').textContent = me ? ((me.display || me.username) + (isDecision ? ' · 决策者' : ' · 需求发起者')) : '未登录';
    el('roleNotice').textContent = isDecision
      ? '当前角色为「决策者」：可修改模型配置、查看审计日志，也可选取机会并生成策划案。'
      : '当前角色为「需求发起者」：可浏览、选取机会、生成策划案；系统配置仅决策者可修改。';
    el('roleNotice').className = 'notice' + (isDecision ? ' blue' : '');
  }
  el('btnLogout').addEventListener('click', async () => {
    try { await api('/api/logout', { method: 'POST' }); } catch (e) {}
    location.href = '/login';
  });

  /* ---------------- 概览图表 ---------------- */
  const PALETTE = ['#2E5C8A', '#4F81BD', '#7BA7CD', '#3F9DB3', '#7BA24A', '#E8894A', '#C0504D', '#8AA0B6'];

  function initCharts() {
    if (state.chartsReady || typeof echarts === 'undefined' || !state.clusters.length) return;
    state.chartsReady = true;
    const cs = state.clusters;
    const m = state.meta;

    const funnel = echarts.init(el('chartFunnel'));
    const t = m.total_records || 1;
    const rOpp = m.total_opportunities / t * 100;
    const rClu = m.total_opportunities ? m.clusters / m.total_opportunities * 100 : 0;
    funnel.setOption({
      tooltip: { trigger: 'item', formatter: (p) => `${p.seriesName}<br/>${p.value.toFixed(1)}%` },
      legend: { bottom: 0, itemWidth: 12, itemHeight: 8, textStyle: { fontSize: 10, color: '#5b6b7c' } },
      series: [
        { name: '机会占比', type: 'pie', radius: ['58%', '78%'], center: ['50%', '44%'], silent: true,
          label: { show: false }, labelLine: { show: false },
          data: [{ value: rOpp, itemStyle: { color: '#5C9E6E' } },
                 { value: 100 - rOpp, itemStyle: { color: '#eef2f7' } }] },
        { name: '簇覆盖率', type: 'pie', radius: ['34%', '52%'], center: ['50%', '44%'],
          label: { show: true, position: 'center', formatter: () => `{a|${rOpp.toFixed(1)}%}\n{b|机会占比}`,
            rich: { a: { fontSize: 26, fontWeight: 700, color: '#2E5C8A', lineHeight: 32 },
                    b: { fontSize: 11, color: '#5b6b7c' } } },
          data: [{ value: rClu, itemStyle: { color: '#4F81BD' } },
                 { value: 100 - rClu, itemStyle: { color: '#eef2f7' } }] },
      ],
    });
    state.charts.funnel = funnel;

    const rank = echarts.init(el('chartRank'));
    rank.setOption({
      grid: { left: 56, right: 26, top: 24, bottom: 44 },
      tooltip: {
        formatter: (p) => {
          const d = p.data;
          return '<b>' + d[5] + ' ' + d[6] + '</b><br/>记录数：' + d[0] + '<br/>价值分：' + d[1] +
            '<br/>来源数：' + d[2] + '<br/>优先级：' + d[3];
        },
      },
      xAxis: { name: '簇内机会记录数', nameGap: 24, nameLocation: 'middle', splitLine: { lineStyle: { color: '#eef2f7' } } },
      yAxis: { name: '机会价值分', nameGap: 40, nameLocation: 'middle', max: 105, splitLine: { lineStyle: { color: '#eef2f7' } } },
      series: [{
        type: 'scatter',
        data: cs.map((c) => [c.size, c.score, c.sources.length, c.priority, c.cid, c.cid, c.name]),
        symbolSize: (d) => 9 + Math.min(20, d[2] * 4.5),
        itemStyle: {
          color: (p) => (p.data[3] <= 3 ? '#C0504D' : p.data[3] <= 8 ? '#4F81BD' : '#8AA0B6'),
          opacity: 0.86, borderColor: '#fff', borderWidth: 1.5,
        },
        label: {
          show: true, position: 'top', fontSize: 10, color: '#41576e',
          formatter: (p) => (p.data[3] <= 6 ? p.data[4] : ''),
        },
      }],
    });
    state.charts.rank = rank;

    const top8 = cs.slice(0, 8);
    const contrib = echarts.init(el('chartContrib'));
    contrib.setOption({
      color: ['#2E5C8A', '#4F81BD', '#3F9DB3'],
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { top: 0, itemWidth: 12, itemHeight: 8, textStyle: { fontSize: 11 } },
      grid: { left: 46, right: 18, top: 40, bottom: 52 },
      xAxis: { type: 'category', data: top8.map((c) => c.cid), axisLabel: { fontSize: 11 } },
      yAxis: { max: 300, splitLine: { lineStyle: { color: '#eef2f7' } }, name: '得分', nameGap: 26 },
      series: [
        { name: '多源指向度', type: 'bar', stack: 'd', data: top8.map((c) => c.dims.src), barWidth: 18 },
        { name: '记录规模', type: 'bar', stack: 'd', data: top8.map((c) => c.dims.size) },
        { name: '商业信号', type: 'bar', stack: 'd', data: top8.map((c) => c.dims.biz) },
      ],
    });
    state.charts.contrib = contrib;

    const SHORT = { '阿里云开发者社区': '阿里云', 'Stack Overflow': 'StackOverflow' };
    const srcNames = m.sources.slice(0, 8).map((s) => {
      const n = SHORT[s.name] || s.name;
      return n.length > 7 ? n.slice(0, 7) + '…' : n;
    });
    const heatData = [];
    cs.forEach((c, yi) => {
      srcNames.forEach((sn, xi) => {
        const f = c.sources.find((s) => s.name === sn);
        heatData.push([xi, yi, f ? f.count : 0]);
      });
    });
    const heat = echarts.init(el('chartHeat'));
    heat.setOption({
      tooltip: { formatter: (p) => srcNames[p.data[0]] + ' × ' + cs[p.data[1]].cid + '：' + p.data[2] + ' 条' },
      grid: { left: 64, right: 20, top: 18, bottom: 62 },
      xAxis: { type: 'category', data: srcNames, axisLabel: { rotate: 32, fontSize: 10 } },
      yAxis: { type: 'category', data: cs.map((c) => c.cid), axisLabel: { fontSize: 10 }, inverse: true },
      visualMap: { min: 0, max: Math.max(3, ...heatData.map((d) => d[2])), orient: 'horizontal',
        left: 'center', bottom: 0, itemWidth: 12, itemHeight: 90, textStyle: { fontSize: 10 },
        inRange: { color: ['#f3f7fc', '#9dbfdc', '#4F81BD', '#2E5C8A'] } },
      series: [{ type: 'heatmap', data: heatData, itemStyle: { borderColor: '#fff', borderWidth: 1 } }],
    });
    state.charts.heat = heat;
  }

  function resizeCharts() {
    Object.values(state.charts).forEach((c) => { try { c.resize(); } catch (e) {} });
  }
  window.addEventListener('resize', resizeCharts);

  /* ---------------- 概览 KPI ---------------- */
  function renderOverview() {
    const m = state.meta, cs = state.clusters;
    el('kpiRecords').textContent = fmt(m.total_records);
    el('kpiOpps').textContent = fmt(m.total_opportunities);
    el('kpiOppsNote').textContent = '占采集总量 ' + m.opp_rate + '% · 阈值 0.50';
    el('kpiClusters').textContent = fmt(m.clusters);
    const top = cs[0];
    if (top) {
      el('kpiTop').textContent = top.cid;
      el('kpiTopNote').textContent = top.name + ' · ' + top.score.toFixed(1) + ' 分';
    }
    const mode = state.settings ? state.settings.provider : 'template';
    el('modePill').textContent = mode === 'template' ? '离线模板模式'
      : (mode === 'ollama' ? '本地 Ollama' : ('模型：' + (state.settings.model || 'OpenAI 兼容')));
  }

  /* ---------------- 机会选取 ---------------- */
  function renderTable(list) {
    const tb = el('tblBodySelect');
    tb.innerHTML = '';
    if (!list.length) {
      tb.innerHTML = '<tr><td colspan="9" class="empty">没有符合条件的主题簇</td></tr>';
      el('tblCount').textContent = '共 0 个';
      return;
    }
    list.forEach((c) => {
      const tr = document.createElement('tr');
      if (state.checked.has(c.cid)) tr.classList.add('sel');
      const pcls = c.priority <= 3 ? 'p1' : (c.priority <= 8 ? 'p2' : 'p3');
      const w = Math.max(6, Math.min(100, c.score));
      tr.innerHTML =
        '<td><input type="checkbox" data-cid="' + c.cid + '"' + (state.checked.has(c.cid) ? ' checked' : '') + '></td>' +
        '<td><b>' + c.cid + '</b></td>' +
        '<td>' + esc(c.name) + '</td>' +
        '<td><span class="tag">' + esc(c.func) + '</span></td>' +
        '<td>' + esc(c.industry) + '</td>' +
        '<td>' + c.size + '</td>' +
        '<td>' + c.sources.length + '</td>' +
        '<td><div class="score-cell"><span style="width:34px;font-weight:600">' + c.score.toFixed(1) + '</span>' +
        '<div class="bar" style="width:' + w + 'px"></div></div></td>' +
        '<td><span class="pri ' + pcls + '">' + c.priority + '</span></td>';
      tr.addEventListener('click', (e) => {
        if (e.target.tagName === 'INPUT') return;
        openDrawer(c.cid);
      });
      tb.appendChild(tr);
    });
    tb.querySelectorAll('input[type=checkbox]').forEach((cb) => {
      cb.addEventListener('change', (e) => {
        const cid = e.target.dataset.cid;
        if (e.target.checked) state.checked.add(cid); else state.checked.delete(cid);
        e.target.closest('tr').classList.toggle('sel', e.target.checked);
        updateSelCount();
      });
    });
    el('tblCount').textContent = '共 ' + list.length + ' 个主题簇';
    updateSelCount();
  }

  function updateSelCount() {
    el('selCount').textContent = '已勾选 ' + state.checked.size + ' 个方向';
    el('btnGenBatch').disabled = state.checked.size === 0;
  }

  async function loadClusters() {
    const q = el('qInput').value.trim();
    const industry = el('fIndustry').value;
    const func = el('fFunc').value;
    const minSrc = el('fSrc').value;
    const url = '/api/clusters?q=' + encodeURIComponent(q) +
      '&industry=' + encodeURIComponent(industry) +
      '&func=' + encodeURIComponent(func) + '&min_src=' + encodeURIComponent(minSrc);
    try {
      const data = await api(url);
      renderTable(data.items);
    } catch (e) { toast('加载失败：' + e.message); }
  }

  ['qInput', 'fIndustry', 'fFunc', 'fSrc'].forEach((id) => {
    el(id).addEventListener(id === 'qInput' ? 'input' : 'change', () => {
      clearTimeout(loadClusters._t);
      loadClusters._t = setTimeout(loadClusters, id === 'qInput' ? 320 : 0);
    });
  });

  el('btnClearSel').addEventListener('click', () => {
    state.checked.clear();
    renderTable(state.clusters);
  });

  /* ---------------- 抽屉 ---------------- */
  async function openDrawer(cid) {
    try {
      const c = await api('/api/clusters/' + encodeURIComponent(cid));
      state.current = c;
      el('dTitle').textContent = c.cid + ' · ' + c.name;
      el('dSub').textContent = c.func + ' ｜ ' + c.industry + ' ｜ ' + c.size + ' 条机会记录 ｜ ' +
        c.sources.length + ' 个来源 ｜ 优先级 ' + c.priority + ' ｜ 价值分 ' + c.score.toFixed(1);
      const dims = [
        ['多源指向度', c.dims.src, ''],
        ['记录规模', c.dims.size, ' g'],
        ['商业信号', c.dims.biz, ' o'],
      ].map((d) => '<div class="dim"><div class="row"><span>' + d[0] + '</span><b>' + d[1].toFixed(1) +
        '/100</b></div><div class="track"><div class="fill' + d[2] + '" style="width:' + Math.max(2, Math.min(100, d[1])) + '%"></div></div></div>').join('');

      const src = c.sources.map((s) => '<span class="tag">' + esc(s.name) + ' ' + s.count + '</span>').join('');
      const ev = c.evidence.map((m) =>
        '<tr><td><code>' + m.batch + '-' + m.id + '</code></td><td><a href="' + esc(m.link) +
        '" target="_blank" rel="noopener">' + esc(m.title.slice(0, 46)) + '</a></td><td>' + esc(m.src) +
        '</td><td style="text-align:right">' + fmt(m.heat) + '</td></tr>').join('');

      el('dBody').innerHTML =
        '<div class="sec-t">价值评分（权重 0.35 / 0.35 / 0.30）</div>' + dims +
        '<div class="sec-t">来源覆盖</div><div>' + src + '</div>' +
        '<div class="sec-t">证据记录（按热度取前 10 条）</div>' +
        '<table class="mini-table"><thead><tr><th style="width:92px">编号</th><th>标题</th>' +
        '<th style="width:80px">来源</th><th style="width:56px">热度</th></tr></thead><tbody>' + ev + '</tbody></table>' +
        '<div class="sec-t">评分解释</div>' +
        '<p style="font-size:12px;color:#5b6b7d;line-height:1.8">' +
        '多源指向度 = 100 × min(1, 来源数/14)：覆盖来源种类越多，需求越可信；<br/>' +
        '记录规模 = 100 × min(1, 簇内记录数/100)：固定基准，跨批可比；<br/>' +
        '商业信号 = 0.7×生均互动热度 + 0.3×需求置信度（置信度经金标 isotonic 校准）。</p>';
      el('drawer').classList.add('open');
    } catch (e) { toast('加载详情失败：' + e.message); }
  }
  function closeDrawer() { el('drawer').classList.remove('open'); }
  el('dClose').addEventListener('click', closeDrawer);

  el('dSelect').addEventListener('click', async () => {
    if (!state.current) return;
    try {
      await api('/api/select', { method: 'POST', body: JSON.stringify({ cid: state.current.cid }) });
      toast('已选取「' + state.current.cid + '」进入备选');
    } catch (e) { toast('选取失败：' + e.message); }
  });

  el('dGen').addEventListener('click', async () => {
    if (!state.current) return;
    await generate(state.current.cid);
  });

  /* ---------------- 生成策划案 ---------------- */
  async function generate(cid) {
    toast('正在生成立项策划案…（' + (state.settings.provider === 'template' ? '离线模板' : '模型调用') + '）', 60000);
    try {
      const r = await api('/api/proposal', { method: 'POST', body: JSON.stringify({ cid: cid }) });
      showProposal(r);
      toast('生成完成：' + r.chars + ' 字 · ' + (r.mode === 'llm' ? r.model : '离线模板'), 3200);
      return r;
    } catch (e) {
      toast('生成失败：' + e.message, 4000);
      return null;
    }
  }

  function showProposal(p) {
    state.proposal = p;
    el('mTitle').textContent = '立项策划案 · ' + p.cid;
    el('mBody').innerHTML = mdToHtml(p.markdown);
    el('modal').classList.add('open');
  }
  el('mClose').addEventListener('click', () => el('modal').classList.remove('open'));
  el('mDownloadMd').addEventListener('click', () => {
    if (state.proposal) window.location.href = '/api/proposals/' + state.proposal.id + '/download?fmt=md';
  });
  el('mDownloadDocx').addEventListener('click', () => {
    if (state.proposal) window.location.href = '/api/proposals/' + state.proposal.id + '/download?fmt=docx';
  });

  el('btnGenBatch').addEventListener('click', async () => {
    const ids = Array.from(state.checked);
    if (!ids.length) return;
    let ok = 0;
    for (const cid of ids) {
      const r = await generate(cid);
      if (r) ok += 1;
    }
    toast('批量完成：成功 ' + ok + '/' + ids.length + ' 份，已存入策划案库', 3500);
    showPage('library');
  });

  async function openProposalById(id) {
    try {
      const p = await api('/api/proposals/' + id);
      showProposal(p);
    } catch (err) { toast('预览失败：' + err.message); }
  }

  /* ---------------- 策划案库 ---------------- */
  async function loadLibrary() {
    try {
      const data = await api('/api/proposals');
      const tb = el('tblBodyLib');
      tb.innerHTML = '';
      el('libCount').textContent = '共 ' + data.items.length + ' 份';
      if (!data.items.length) {
        tb.innerHTML = '<tr><td colspan="9" class="empty">暂无策划案，请到「机会选取」生成</td></tr>';
        return;
      }
      data.items.forEach((p) => {
        const tr = document.createElement('tr');
        tr.innerHTML =
          '<td>' + p.id + '</td><td><b>' + p.cid + '</b></td><td>' + esc(p.cluster_name) + '</td>' +
          '<td><span class="tag">' + (p.mode === 'llm' ? '模型生成' : (p.mode === 'template-fallback' ? '模板兜底' : '离线模板')) + '</span></td>' +
          '<td style="font-size:11.5px;color:#6b7c90">' + esc(p.model) + '</td>' +
          '<td>' + fmt(p.chars) + '</td><td>' + fmt(p.tokens) + '</td>' +
          '<td style="font-size:11.5px;color:#6b7c90">' + p.created_at + '</td>' +
          '<td><button class="btn mini ghost" data-act="view" data-id="' + p.id + '">预览</button> ' +
          '<button class="btn mini ghost" data-act="md" data-id="' + p.id + '">MD</button> ' +
          '<button class="btn mini ghost" data-act="docx" data-id="' + p.id + '">Word</button></td>';
        tb.appendChild(tr);
      });
      tb.querySelectorAll('button[data-act]').forEach((b) => {
        b.addEventListener('click', async (e) => {
          e.stopPropagation();
          const id = b.dataset.id, act = b.dataset.act;
          if (act === 'md' || act === 'docx') {
            window.location.href = '/api/proposals/' + id + '/download?fmt=' + act;
            return;
          }
          openProposalById(id);
        });
      });
    } catch (e) { toast('加载策划案库失败：' + e.message); }
  }
  el('btnRefreshLib').addEventListener('click', loadLibrary);

  /* ---------------- 设置 ---------------- */
  function fillSettings(s) {
    el('sProvider').value = s.provider || 'template';
    el('sBase').value = s.base_url || '';
    el('sModel').value = s.model || '';
    el('sKey').value = '';
    el('sKey').placeholder = s.api_key_set ? ('已配置：' + s.api_key + '（留空保持）') : '未配置';
    el('sTemp').value = s.temperature || '0.4';
    el('sMaxTok').value = s.max_tokens || '2000';
    el('sTimeout').value = s.timeout || '60';
  }

  el('btnSave').addEventListener('click', async () => {
    const patch = {
      provider: el('sProvider').value,
      base_url: el('sBase').value.trim(),
      model: el('sModel').value.trim(),
      temperature: el('sTemp').value.trim() || '0.4',
      max_tokens: el('sMaxTok').value.trim() || '2000',
      timeout: el('sTimeout').value.trim() || '60',
    };
    const key = el('sKey').value.trim();
    if (key) patch.api_key = key;
    try {
      const r = await api('/api/settings', { method: 'POST', body: JSON.stringify(patch) });
      state.settings = r.settings;
      fillSettings(r.settings);
      renderOverview();
      toast('配置已保存（仅存于本机 SQLite）');
    } catch (e) { toast('保存失败：' + e.message, 3500); }
  });

  el('btnTest').addEventListener('click', async () => {
    el('testResult').textContent = '测试中…';
    el('testResult').style.color = '#6b7c90';
    try {
      const r = await api('/api/test', { method: 'POST', body: '{}' });
      el('testResult').textContent = (r.ok ? '✓ ' : '✗ ') + r.message + '（' + r.ms + ' ms）';
      el('testResult').style.color = r.ok ? '#4d7a2a' : '#c0504d';
    } catch (e) {
      el('testResult').textContent = '✗ ' + e.message;
      el('testResult').style.color = '#c0504d';
    }
  });

  /* ---------------- 启动 ---------------- */
  async function boot() {
    try {
      const me = await api('/api/me');
      if (!me.authenticated) { location.href = '/login'; return; }
      applyMe(me.user);
      const [b, h] = await Promise.all([api('/api/bootstrap'), fetch('/health').then((r) => r.json())]);
      state.meta = b.meta;
      state.clusters = b.clusters;
      state.filters = b.filters;
      state.settings = b.settings;
      state.stats = b.stats;

      (b.filters.industries || []).forEach((x) => {
        const o = document.createElement('option'); o.value = x; o.textContent = x; el('fIndustry').appendChild(o);
      });
      (b.filters.funcs || []).forEach((x) => {
        const o = document.createElement('option'); o.value = x; o.textContent = x; el('fFunc').appendChild(o);
      });

      renderOverview();
      renderTable(state.clusters);
      fillSettings(b.settings);
      el('statusPill').textContent = h.ok ? '服务正常' : '服务异常';
      el('statusPill').className = 'pill ' + (h.ok ? 'ok' : 'warn');
      initCharts();
      const raw = (location.hash || '').replace('#', '');
      const parts = raw.split('/');
      const page = parts[0];
      if (page && PAGES[page]) showPage(page);
      if (parts[1]) {
        const arg = decodeURIComponent(parts[1]);
        setTimeout(() => {
          if (page === 'select') openDrawer(arg);
          if (page === 'library') openProposalById(arg);
        }, 150);
      }
    } catch (e) {
      el('statusPill').textContent = '连接失败';
      el('statusPill').className = 'pill warn';
      toast('初始化失败：' + e.message, 5000);
    }
  }

  boot();
})();
