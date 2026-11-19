/* 智掘 AI Discovery · 前端交互（双语） */
(function () {
  'use strict';

  const state = {
    meta: null, clusters: [], filters: null, settings: null, stats: null,
    me: null,
    checked: new Set(), current: null, proposal: null, charts: {}, chartsReady: false,
  };

  const $ = (s) => document.querySelector(s);
  const el = (id) => document.getElementById(id);
  const T = (s) => (window.T ? window.T(s) : s);
  const TF = (s, v) => (window.TF ? window.TF(s, v) : s);

  async function api(path, opts) {
    const o = Object.assign({ headers: {} }, opts || {});
    o.headers = Object.assign({ 'Content-Type': 'application/json' }, o.headers);
    const res = await fetch(path, o);
    let data = {};
    try { data = await res.json(); } catch (e) { data = { error: T('响应解析失败') }; }
    if (res.status === 401 && data.need_login) { location.href = '/login'; throw new Error(T('未登录')); }
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

  function fmt(n) {
    if (n === null || n === undefined) return '—';
    return Number(n).toLocaleString(window.I18N && I18N.getLang() === 'en' ? 'en-US' : 'zh-CN');
  }

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
  let currentPage = 'overview';
  function showPage(name) {
    currentPage = name;
    document.querySelectorAll('.nav a').forEach((a) => a.classList.toggle('active', a.dataset.page === name));
    Object.keys(PAGES).forEach((k) => el('page-' + k).classList.toggle('hidden', k !== name));
    el('crumb').textContent = T(PAGES[name] || name);
    if (name === 'overview') { initCharts(); setTimeout(resizeCharts, 60); }
    if (name === 'library') loadLibrary();
    if (window.innerWidth <= 820) document.body.classList.remove('nav-open');
    window.dispatchEvent(new CustomEvent('page:change', { detail: { name: name } }));
  }
  document.querySelectorAll('.nav a').forEach((a) => {
    a.addEventListener('click', () => { location.hash = a.dataset.page; showPage(a.dataset.page); });
  });

  /* ---------------- 会话身份（服务端下发，不可伪造） ---------------- */
  function applyMe(me) {
    state.me = me;
    const isDecision = me && me.role === 'decision';
    el('userPill').textContent = me
      ? ((me.display || me.username) + (isDecision ? ' · ' + T('决策者') : ' · ' + T('需求发起者')))
      : T('未登录');
    el('roleNotice').innerHTML = (window.I18N && I18N.HTML[isDecision ? 'notice.roleDecision' : 'notice.roleRequester']
      ? (I18N.getLang() === 'en' ? I18N.HTML[isDecision ? 'notice.roleDecision' : 'notice.roleRequester'].en
                                 : I18N.HTML[isDecision ? 'notice.roleDecision' : 'notice.roleRequester'].zh)
      : '');
    el('roleNotice').className = 'notice' + (isDecision ? ' blue' : '');
  }
  el('btnLogout').addEventListener('click', async () => {
    try { await api('/api/logout', { method: 'POST' }); } catch (e) {}
    location.href = '/login';
  });

  /* ---------------- 概览图表 ---------------- */
  function chartText() {
    return {
      records: T('簇内机会记录数'), value: T('机会价值分'), score: T('得分'),
      multi: T('多源指向度'), scale: T('记录规模'), biz: T('商业信号'),
      recordsTip: T('记录数'), sourcesTip: T('来源数'), priorityTip: T('优先级'),
      valueTip: T('价值分'), countUnit: T('条'), shareTip: T('占比'),
    };
  }

  function initCharts() {
    if (!el('chartRank')) return;
    if (state.chartsReady || typeof echarts === 'undefined' || !state.clusters.length) return;
    state.chartsReady = true;
    const cs = state.clusters;
    const m = state.meta;
    const X = chartText();
    const TIP = {
      bg: '#16283c', border: '#3d5266', text: '#eaf2f8',
      extraCss: 'box-shadow:0 6px 20px rgba(16,40,64,.22);border-radius:7px;',
    };

    // 图1：主题簇价值排序（气泡散点：记录数 × 价值分，气泡大小=来源数，颜色=优先级）
    const rank = echarts.init(el('chartRank'));
    rank.setOption({
      grid: { left: 52, right: 22, top: 22, bottom: 44 },
      tooltip: {
        backgroundColor: TIP.bg, borderColor: TIP.border, textStyle: { color: TIP.text, fontSize: 12 },
        extraCssText: TIP.extraCss,
        formatter: (p) => {
          const d = p.data;
          return '<b>' + d[5] + ' ' + d[6] + '</b><br/>' + X.recordsTip + '：' + d[0] + ' ' + X.countUnit +
            '<br/>' + X.valueTip + '：' + d[1] + '<br/>' + X.sourcesTip + '：' + d[2] +
            '<br/>' + X.priorityTip + '：#' + d[3];
        },
      },
      xAxis: { name: X.records, nameGap: 22, nameLocation: 'middle', nameTextStyle: { color: '#33465c' },
        splitLine: { lineStyle: { color: '#eef2f7' } }, axisLabel: { color: '#33465c' } },
      yAxis: { name: X.value, nameGap: 36, nameLocation: 'middle', nameTextStyle: { color: '#33465c' },
        max: 105, splitLine: { lineStyle: { color: '#eef2f7' } }, axisLabel: { color: '#33465c' } },
      series: [{
        type: 'scatter',
        data: cs.map((c) => [c.size, c.score, c.sources.length, c.priority, c.cid, c.cid, c.name]),
        symbolSize: (d) => 9 + Math.min(20, d[2] * 4.5),
        itemStyle: {
          color: (p) => (p.data[3] <= 3 ? '#C0504D' : p.data[3] <= 8 ? '#4F81BD' : '#8AA0B6'),
          opacity: 0.86, borderColor: '#fff', borderWidth: 1.5,
        },
        emphasis: { scale: 1.35, itemStyle: { shadowBlur: 12, shadowColor: 'rgba(16,40,64,.35)' } },
        label: { show: true, position: 'top', fontSize: 10, color: '#33465c',
          formatter: (p) => (p.data[3] <= 6 ? p.data[4] : '') },
      }],
    });
    state.charts.rank = rank;

    // 图2：价值分三维度贡献（Top8 堆叠柱，悬停显示全部维度）
    const top8 = cs.slice(0, 8);
    const contrib = echarts.init(el('chartContrib'));
    contrib.setOption({
      color: ['#2E5C8A', '#4F81BD', '#3F9DB3'],
      tooltip: {
        trigger: 'axis', axisPointer: { type: 'shadow' },
        backgroundColor: TIP.bg, borderColor: TIP.border, textStyle: { color: TIP.text, fontSize: 12 },
        extraCssText: TIP.extraCss,
      },
      legend: { top: 0, itemWidth: 11, itemHeight: 7, textStyle: { fontSize: 10, color: '#33465c' } },
      grid: { left: 42, right: 16, top: 34, bottom: 44 },
      xAxis: { type: 'category', data: top8.map((c) => c.cid), axisLabel: { fontSize: 10, color: '#33465c' } },
      yAxis: { max: 300, splitLine: { lineStyle: { color: '#eef2f7' } }, name: X.score, nameTextStyle: { color: '#33465c' }, axisLabel: { color: '#33465c' } },
      series: [
        { name: X.multi, type: 'bar', stack: 'd', data: top8.map((c) => c.dims.src), barWidth: 16,
          emphasis: { focus: 'series' } },
        { name: X.scale, type: 'bar', stack: 'd', data: top8.map((c) => c.dims.size), emphasis: { focus: 'series' } },
        { name: X.biz, type: 'bar', stack: 'd', data: top8.map((c) => c.dims.biz), emphasis: { focus: 'series' } },
      ],
    });
    state.charts.contrib = contrib;

    // 图3：信息来源多元构成（南丁格尔玫瑰图，悬停查看记录数与占比）——替换原覆盖热力图
    const SHORT = { '阿里云开发者社区': '阿里云', 'Stack Overflow': 'StackOverflow' };
    const srcRows = (m.sources || []).map((s) => ({ name: SHORT[s.name] || s.name, value: s.count }));
    const srcTotal = srcRows.reduce((a, b) => a + b.value, 0) || 1;
    const source = echarts.init(el('chartSource'));
    source.setOption({
      color: ['#2E5C8A', '#4F81BD', '#3F9DB3', '#7BA24A', '#E8A33D', '#8E6BBF', '#C0504D', '#5BA8A0'],
      tooltip: {
        trigger: 'item',
        backgroundColor: TIP.bg, borderColor: TIP.border, textStyle: { color: TIP.text, fontSize: 12 },
        extraCssText: TIP.extraCss,
        formatter: (p) => '<b>' + p.name + '</b><br/>' + X.recordsTip + '：' + p.value + ' ' + X.countUnit +
          '<br/>' + X.shareTip + '：' + (p.value / srcTotal * 100).toFixed(1) + '%',
      },
      legend: { type: 'scroll', orient: 'vertical', right: 4, top: 'center', itemWidth: 10, itemHeight: 8,
        textStyle: { fontSize: 10, color: '#33465c' } },
      series: [{
        type: 'pie', radius: [22, 88], center: ['38%', '54%'], roseType: 'area',
        itemStyle: { borderColor: '#fff', borderWidth: 2, borderRadius: 4 },
        label: { show: true, fontSize: 10, color: '#33465c', formatter: '{d}%' },
        labelLine: { length: 6, length2: 6 },
        emphasis: { scale: true, scaleSize: 6, itemStyle: { shadowBlur: 14, shadowColor: 'rgba(16,40,64,.35)' } },
        data: srcRows,
      }],
    });
    state.charts.source = source;
  }

  function disposeCharts() {
    Object.values(state.charts).forEach((c) => { try { c.dispose(); } catch (e) {} });
    state.charts = {};
    state.chartsReady = false;
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
    el('kpiOppsNote').textContent = TF('占采集总量 {p}% · 阈值 {t}', { p: m.opp_rate, t: '0.60' });
    el('kpiClusters').textContent = fmt(m.clusters);
    const top = cs[0];
    if (top) {
      el('kpiTop').textContent = top.cid;
      el('kpiTopNote').textContent = top.name + ' · ' + top.score.toFixed(1) + ' ' + T('分');
    }
    const mode = state.settings ? state.settings.provider : 'template';
    el('modePill').textContent = mode === 'template' ? T('离线模板模式')
      : (mode === 'ollama' ? T('本地 Ollama') : (T('模型') + '：' + (state.settings.model || 'OpenAI')));
  }

  /* ---------------- 机会选取 ---------------- */
  function renderTable(list) {
    const tb = el('tblBodySelect');
    tb.innerHTML = '';
    if (!list.length) {
      tb.innerHTML = '<tr><td colspan="9" class="empty">' + T('没有符合条件的主题簇') + '</td></tr>';
      el('tblCount').textContent = T('共 0 个');
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
    el('tblCount').textContent = TF('共 {n} 个主题簇', { n: list.length });
    updateSelCount();
  }

  function updateSelCount() {
    el('selCount').textContent = TF('已勾选 {n} 个方向', { n: state.checked.size });
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
    } catch (e) { toast(T('加载失败：') + e.message); }
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
      el('dSub').textContent = c.func + ' ｜ ' + c.industry + ' ｜ ' + c.size + ' ' + T('条机会记录') + ' ｜ ' +
        c.sources.length + ' ' + T('个来源') + ' ｜ ' + T('优先级') + ' ' + c.priority + ' ｜ ' + T('价值分') + ' ' + c.score.toFixed(1);
      const dims = [
        [T('多源指向度'), c.dims.src, ''],
        [T('记录规模'), c.dims.size, ' g'],
        [T('商业信号'), c.dims.biz, ' o'],
      ].map((d) => '<div class="dim"><div class="row"><span>' + d[0] + '</span><b>' + d[1].toFixed(1) +
        '/100</b></div><div class="track"><div class="fill' + d[2] + '" style="width:' + Math.max(2, Math.min(100, d[1])) + '%"></div></div></div>').join('');

      const src = c.sources.map((s) => '<span class="tag">' + esc(s.name) + ' ' + s.count + '</span>').join('');
      const ev = c.evidence.map((m) =>
        '<tr><td><code>' + m.batch + '-' + m.id + '</code></td><td><a href="' + esc(m.link) +
        '" target="_blank" rel="noopener">' + esc(m.title.slice(0, 46)) + '</a></td><td>' + esc(m.src) +
        '</td><td style="text-align:right">' + fmt(m.heat) + '</td></tr>').join('');

      el('dBody').innerHTML =
        '<div class="sec-t">' + T('价值评分') + '（0.293 / 0.5065 / 0.2005）</div>' + dims +
        '<div class="sec-t">' + T('来源覆盖') + '</div><div>' + src + '</div>' +
        '<div class="sec-t">' + T('证据记录') + '（' + T('按热度取前 10 条') + '）</div>' +
        '<table class="mini-table"><thead><tr><th style="width:92px">' + T('编号') + '</th><th>' + T('标题') + '</th>' +
        '<th style="width:80px">' + T('来源') + '</th><th style="width:56px">' + T('热度') + '</th></tr></thead><tbody>' + ev + '</tbody></table>' +
        '<div class="sec-t">' + T('评分解释') + '</div>' +
        '<p style="font-size:12px;color:#33465c;line-height:1.8">' +
        T('多源指向度 = 100 × min(1, 来源数/14)：覆盖来源种类越多，需求越可信；') + '<br/>' +
        T('记录规模 = 100 × min(1, 簇内记录数/100)：固定基准，跨批可比；') + '<br/>' +
        T('商业信号 = 0.6×生均互动热度 + 0.4×需求置信度。') + '</p>';
      el('drawer').classList.add('open');
    } catch (e) { toast(T('加载详情失败：') + e.message); }
  }
  function closeDrawer() { el('drawer').classList.remove('open'); }
  el('dClose').addEventListener('click', closeDrawer);

  el('dSelect').addEventListener('click', async () => {
    if (!state.current) return;
    try {
      await api('/api/select', { method: 'POST', body: JSON.stringify({ cid: state.current.cid }) });
      toast(TF('已选取「{c}」进入备选', { c: state.current.cid }));
    } catch (e) { toast(T('选取失败：') + e.message); }
  });

  el('dGen').addEventListener('click', async () => {
    if (!state.current) return;
    await generate(state.current.cid);
  });

  /* ---------------- 生成策划案 ---------------- */
  async function generate(cid) {
    toast(T('正在生成立项策划案…') + '（' + (state.settings.provider === 'template' ? T('离线模板') : T('模型调用')) + '）', 60000);
    try {
      const r = await api('/api/proposal', { method: 'POST', body: JSON.stringify({ cid: cid }) });
      showProposal(r);
      toast(T('生成完成：') + r.chars + ' ' + T('字数') + ' · ' + (r.mode === 'llm' ? r.model : T('离线模板')), 3200);
      return r;
    } catch (e) {
      toast(T('生成失败：') + e.message, 4000);
      return null;
    }
  }

  function showProposal(p) {
    state.proposal = p;
    el('mTitle').textContent = T('立项策划案') + ' · ' + p.cid;
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
    toast(TF('批量完成：成功 {a}/{b} 份，已存入策划案库', { a: ok, b: ids.length }), 3500);
    showPage('library');
  });

  async function openProposalById(id) {
    try {
      const p = await api('/api/proposals/' + id);
      showProposal(p);
    } catch (err) { toast(T('预览失败：') + err.message); }
  }

  /* ---------------- 策划案库 ---------------- */
  async function loadLibrary() {
    try {
      const data = await api('/api/proposals');
      const tb = el('tblBodyLib');
      tb.innerHTML = '';
      el('libCount').textContent = TF('共 {n} 份', { n: data.items.length });
      if (!data.items.length) {
        tb.innerHTML = '<tr><td colspan="9" class="empty">' + T('暂无策划案，请到「机会选取」生成') + '</td></tr>';
        return;
      }
      data.items.forEach((p) => {
        const tr = document.createElement('tr');
        const modeLabel = p.mode === 'llm' ? T('模型生成') : (p.mode === 'template-fallback' ? T('模板兜底') : T('离线模板'));
        tr.innerHTML =
          '<td>' + p.id + '</td><td><b>' + p.cid + '</b></td><td>' + esc(p.cluster_name) + '</td>' +
          '<td><span class="tag">' + modeLabel + '</span></td>' +
          '<td style="font-size:11px;color:#3f556b">' + esc(p.model) + '</td>' +
          '<td>' + fmt(p.chars) + '</td><td>' + fmt(p.tokens) + '</td>' +
          '<td style="font-size:11px;color:#3f556b">' + p.created_at + '</td>' +
          '<td><button class="btn mini ghost" data-act="view" data-id="' + p.id + '">' + T('预览') + '</button> ' +
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
    } catch (e) { toast(T('加载策划案库失败：') + e.message); }
  }
  el('btnRefreshLib').addEventListener('click', loadLibrary);

  /* ---------------- 设置 ---------------- */
  function fillSettings(s) {
    el('sProvider').value = s.provider || 'template';
    el('sBase').value = s.base_url || '';
    el('sModel').value = s.model || '';
    el('sKey').value = '';
    el('sKey').placeholder = s.api_key_set
      ? (T('已配置：') + s.api_key + T('（留空保持）')) : T('未配置');
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
      toast(T('配置已保存（仅存于本机 SQLite）'));
    } catch (e) { toast(T('保存失败：') + e.message, 3500); }
  });

  el('btnTest').addEventListener('click', async () => {
    el('testResult').textContent = T('测试中…');
    el('testResult').style.color = '#3f556b';
    try {
      const r = await api('/api/test', { method: 'POST', body: '{}' });
      el('testResult').textContent = (r.ok ? '✓ ' : '✗ ') + r.message + '（' + r.ms + ' ms）';
      el('testResult').style.color = r.ok ? '#4d7a2a' : '#c0504d';
    } catch (e) {
      el('testResult').textContent = '✗ ' + e.message;
      el('testResult').style.color = '#c0504d';
    }
  });

  /* ---------------- 语言切换：重绘动态内容 ---------------- */
  window.addEventListener('i18n:change', () => {
    if (state.me) applyMe(state.me);
    if (state.meta) renderOverview();
    if (state.filters) renderTable(state.clusters);
    if (state.settings) fillSettings(state.settings);
    el('crumb').textContent = T(PAGES[currentPage] || currentPage);
    if (currentPage === 'library') loadLibrary();
    if (currentPage === 'overview') { disposeCharts(); initCharts(); setTimeout(resizeCharts, 80); }
  });

  /* ---------------- 论文图放大预览 + 悬停说明 ---------------- */
  (function bindLightbox() {
    const box = el('figLightbox');
    if (!box) return;
    const img = el('lbImg'), cap = el('lbCap'), desc = el('lbDesc'), close = el('lbClose');
    const tip = el('figTip');

    // 悬停：在图上方浮出“这是什么”的说明，并轻微放大
    if (tip) {
      let hideTimer = null;
      document.addEventListener('mouseover', (e) => {
        const card = e.target.closest('.paper-figure');
        if (!card || card.contains(e.relatedTarget)) return;
        const text = card.getAttribute('data-desc') || card.getAttribute('data-cap') || '';
        if (!text) return;
        tip.textContent = text;
        tip.classList.add('show');
        const r = card.getBoundingClientRect();
        // 默认定位在卡片顶部，超出视口上边则放到底部
        let top = r.top - tip.offsetHeight - 10;
        if (top < 8) top = Math.min(r.bottom + 10, window.innerHeight - tip.offsetHeight - 8);
        let left = r.left + r.width / 2 - tip.offsetWidth / 2;
        left = Math.max(8, Math.min(left, window.innerWidth - tip.offsetWidth - 8));
        tip.style.top = top + 'px';
        tip.style.left = left + 'px';
      });
      document.addEventListener('mouseout', (e) => {
        const card = e.target.closest('.paper-figure');
        if (!card || card.contains(e.relatedTarget)) return;
        tip.classList.remove('show');
      });
    }

    document.addEventListener('click', (e) => {
      const card = e.target.closest('.paper-figure');
      if (!card) return;
      // 帮助按钮不触发放大
      if (e.target.closest('.help-btn')) return;
      const zoom = card.getAttribute('data-zoom');
      if (!zoom) return;
      img.src = '/static/' + zoom;
      img.alt = card.getAttribute('data-cap') || '';
      cap.textContent = card.getAttribute('data-cap') || '';
      if (desc) desc.textContent = card.getAttribute('data-desc') || '';
      box.classList.add('open');
      if (tip) tip.classList.remove('show');
    });
    const hide = () => { box.classList.remove('open'); img.src = ''; };
    close.addEventListener('click', hide);
    box.addEventListener('click', (e) => { if (e.target === box || e.target.tagName === 'FIGURE') hide(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && box.classList.contains('open')) hide(); });
  })();

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
      el('statusPill').textContent = h.ok ? T('服务正常') : T('服务异常');
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
      el('statusPill').textContent = T('连接失败');
      el('statusPill').className = 'pill warn';
      toast(T('初始化失败：') + e.message, 5000);
    }
  }

  boot();
})();
