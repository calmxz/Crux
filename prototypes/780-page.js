// PROTOTYPE, throwaway (calmxz/Crux#780). The session screen, the sidebar, the shell and the switch bar. Loads last.
function sessionHtml(c) {
  const s = SESSIONS.find(x => x.id === st.open.id), qt = toks(st.q);
  if (s.sealed) return `<div class="page"><div class="card" style="max-width:520px;margin:30px auto">${SEALMSG}</div></div>`;
  const checkOpen = s.badge && s.badge[0] === 'chk';
  const found = s.msgs.map((m, i) => i).filter(i => !s.msgs[i].blocked && !(checkOpen && s.msgs[i].hide) && has(qt, s.msgs[i].t));
  const at = st.open.at != null ? +st.open.at : (c.hit === 'C' && found.length ? found[found.length - 1] : null);
  const fb = c.hit === 'C' && found.length && scene !== 'entry' ? `<div class="findbar">Find: <b>${esc(st.q)}</b> &middot; ${found.length - found.indexOf(at)} of ${found.length} <span class="btn small">&#9650;</span><span class="btn small">&#9660;</span><span style="flex:1"></span><span class="a" data-act="back">Close</span> ${NS}</div>` : '';
  let th = checkOpen ? '<div class="sysline">Mastery check: problem 2 of 4. Earlier teaching is hidden until the check ends.</div>' : '';
  s.msgs.forEach((m, i) => { if (checkOpen && m.hide) return; if (m.blocked) { th += `<div class="sysline">${esc(m.t)}</div>`; return; }
    th += `<div class="msg ${m.who === 'me' ? 'me' : 'tutor'} ${i === at ? 'found' : ''}">${msgHtml(m.t, i === at ? qt : [])}${m.wait ? '<div class="sub" style="color:#dfe6ff">Waiting</div>' : ''}</div>`; });
  if (!s.msgs.length) th += '<div class="sysline">[the session screen from #751]</div>';
  return `${fb}<div class="thread">${th}</div>`;
}
function sidebar(c, phone) {
  const lst = SESSIONS.slice().sort((a, b) => b.lastN - a.lastN);
  const short = c.entry === 'B' || c.entry === 'D';
  const shown = short ? lst.slice(0, 10) : lst;
  const onPage = st.view === 'page';
  const lines = shown.map(s => `<div class="sline ${st.open && st.open.id === s.id ? 'cur' : ''}" data-open="${s.id}" data-side="1"><div class="nm">${s.nm}${badge(s.badge)}</div><div class="ln">${lastLine(s)}</div>${prog(s.pr)}<span class="more">&#8943;</span></div>`).join('');
  const allLine = short ? `<div class="sline ${onPage ? 'cur' : ''}" data-act="page"><div class="nm a">All sessions (${TOTAL}) ${NS}</div></div>` : '';
  const box = c.entry === 'C' ? `<div style="padding:0 14px 8px"><input id="sq" type="search" placeholder="Search sessions" style="width:100%;font:inherit;border:1px solid #c9ced8;border-radius:8px;padding:6px 9px"> ${NS}</div>` : '';
  const link = !short ? `<a data-act="page" style="${onPage ? 'font-weight:700' : ''}">All sessions</a>` : '';
  const pos = phone ? 'position:absolute;left:0;top:0;bottom:0;width:86%;z-index:9;box-shadow:6px 0 20px rgba(0,0,0,.2)' : '';
  return `<div class="side" style="${pos}"><div class="topbar"><span class="brand">Crux</span><span style="flex:1"></span>${c.entry === 'D' ? `<span class="btn small" data-act="search" title="Search sessions" aria-label="Search sessions">&#128269;</span>` : ''}</div>
    <div style="padding:10px 14px"><span class="btn primary" style="display:block;text-align:center">+ New session</span></div>${box}
    <div class="sec"><span>Sessions</span>${link}</div><div class="list">${lines}${allLine}</div>
    <div class="sline" style="border-top:1px solid var(--line)"><div class="nm">&#9733; What you've mastered</div></div>
    <div class="sline"><div class="ln">Feedback &middot; Settings</div></div></div>`;
}
function menuPop(c) {
  if (!st.menuFor) return '';
  const s = SESSIONS.find(x => x.id === st.menuFor);
  const del = s.sealed ? '<div style="color:#8a909c">Delete<div class="sub">A sealed session can\'t be deleted.</div></div>' : '<div class="danger">Delete</div>';
  return `<div class="menupop" style="top:${st.menuY}px;right:24px">${s.sealed ? '' : '<div>Rename</div>'}${del}</div>`;
}
function screen(phone) {
  const c = cfg();
  const title = st.view === 'page' ? 'All sessions' : SESSIONS.find(x => x.id === st.open.id).nm;
  const top = `<div class="topbar">${phone ? '<span class="brand" data-act="drawer">&#9776;</span>' : ''}<span class="title">${title}</span>${st.view === 'session' ? '<span class="a" data-act="page" style="font-size:13px">&lsaquo; All sessions <span class="nospec">[draft]</span></span>' : ''}</div>`;
  const main = `<div class="main">${top}${st.view === 'page' ? pageHtml(c, phone) : sessionHtml(c)}${menuPop(c)}</div>`;
  if (phone) return `${main}${st.drawer ? '<div class="overlay" data-act="drawer"></div>' + sidebar(c, phone) : ''}`;
  return sidebar(c, phone) + main;
}

// ---------- switch bar (prototype only, not part of the design) ----------
function addr(o, d) { const u = new URL(location); u.search = ''; u.searchParams.set('scene', scene); u.searchParams.set('opt', o || opt); u.searchParams.set('device', d || device); return u; }
function render() {
  const sc = SCENES[scene], o = sc.opts[opt], phone = device === 'phone';
  const ae = document.activeElement, fid = ae && ae.id, pos = fid ? ae.selectionStart : 0;
  const oldPg = document.querySelector('#device .page'), keep = oldPg ? oldPg.scrollTop : 0;
  const dv = document.getElementById('device'); dv.className = 'device ' + device; dv.innerHTML = screen(phone);
  const pg = document.querySelector('#device .page');
  if (pg) { if (st.keepScroll) pg.scrollTop = keep; st.keepScroll = false;
    pg.addEventListener('scroll', () => { const lz = document.getElementById('lazy'); if (!lz || st.lazyT) return;
      if (lz.getBoundingClientRect().top < pg.getBoundingClientRect().bottom + 40) st.lazyT = setTimeout(() => { st.lazyT = null; st.more = true; st.keepScroll = true; render(); }, 500); }); }
  const c = cfg(), { rows } = st.view === 'page' ? results(c) : { rows:[] };
  const qt = toks(st.q);
  const looked = c.scope === 'A' ? 'names and topics' : c.scope === 'B' ? 'names, topics and file names' : 'names, topics, file names and conversations';
  const skipped = c.scope === 'C' ? ' Never searched: messages Google blocked, sealed sessions\' topics, files and conversations' + (c.check === 'A' ? ', and teaching hidden by an open check' : '') + '.' : '';
  document.getElementById('note').innerHTML = `<p><b>PROTOTYPE, throwaway (#780).</b> Question: <b>${sc.name}</b>. <b>Option ${opt}: ${o.name}.</b> ${o.note}</p>
    <p class="sub">State: ${qt.length ? `search "${esc(st.q)}" -> ${rows.length} session(s)` : 'no search'}; looks through ${looked}.${skipped} Defaults elsewhere on the page are placeholders. Red italic text is draft wording. ${st.flash}</p>`;
  const bar = document.getElementById('bar');
  bar.innerHTML = `<select id="sc">${ORDER.map(k => `<option value="${k}" ${k === scene ? 'selected' : ''}>${SCENES[k].name}</option>`).join('')}</select>
    <span class="grp">Option ${Object.keys(sc.opts).map(k => `<button data-o="${k}" class="${k === opt ? 'on' : ''}">${k}</button>`).join('')}</span>
    <span class="grp"><button data-d="phone" class="${phone ? 'on' : ''}">Phone</button><button data-d="desktop" class="${phone ? '' : 'on'}">Desktop</button></span>
    ${scene === 'empty' ? `<span class="grp">Case <button data-case="none" class="${st.emptyCase === 'none' ? 'on' : ''}">No match</button><button data-case="nos" class="${st.emptyCase === 'nos' ? 'on' : ''}">No sessions</button></span>` : ''}
    <button id="reset">Reset</button>`;
  const u = addr(); if (st.emptyCase === 'nos') u.searchParams.set('case', 'nos'); history.replaceState(null, '', u);
  if (fid && document.getElementById(fid)) { const el = document.getElementById(fid); el.focus(); try { el.setSelectionRange(pos, pos); } catch (e) {} }
}
document.getElementById('bar').addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  if (b.dataset.o) { opt = b.dataset.o; const q = st.q; st = fresh(); st.q = q; }
  if (b.dataset.d) device = b.dataset.d;
  if (b.dataset.case) { st.emptyCase = b.dataset.case; }
  if (b.id === 'reset') st = fresh();
  render();
});
document.getElementById('bar').addEventListener('change', e => { if (e.target.id === 'sc') { scene = e.target.value; opt = 'A'; st = fresh(); render(); } });
const dev = document.getElementById('device');
dev.addEventListener('click', e => {
  const t = e.target, c = cfg();
  const a = t.closest('[data-act]'), m = t.closest('[data-menu]'), f = t.closest('[data-filt]'), tr = t.closest('[data-try]'), o = t.closest('[data-open]');
  st.flash = '';
  if (m) { st.menuFor = st.menuFor === m.dataset.menu ? null : m.dataset.menu; st.menuY = m.getBoundingClientRect().top - dev.getBoundingClientRect().top + 22; return render(); }
  st.menuFor = null;
  if (a) { const k = a.dataset.act;
    if (k === 'page' || k === 'search') { st.view = 'page'; st.open = null; st.drawer = false; }
    if (k === 'search') { render(); const q = document.getElementById('q'); q.focus(); q.select(); return; }
    if (k === 'drawer') st.drawer = !st.drawer;
    if (k === 'clear') { st.q = ''; st.pend = null; }
    if (k === 'more') st.more = true;
    if (k === 'go') { st.q = st.pend != null ? st.pend : st.q; st.pend = null; }
    if (k === 'back') { st.view = 'page'; st.open = null; }
    return render(); }
  if (f) { st.filt = f.dataset.filt; return render(); }
  if (tr) { st.q = tr.dataset.try; st.pend = null; return render(); }
  if (o) { const side = o.dataset.side; st.open = { id:o.dataset.open, at: side ? null : (t.closest('.hit') ? t.closest('.hit').dataset.at : null) };
    if (side) st.q = st.q; st.view = 'session'; st.drawer = false; return render(); }
  render();
});
dev.addEventListener('input', e => {
  const c = cfg();
  if (e.target.id === 'q') { if (c.typing === 'B') st.pend = e.target.value; else { st.q = e.target.value; render(); } }
  if (e.target.id === 'sq') { st.q = e.target.value; st.pend = null; st.view = 'page'; st.open = null; st.drawer = false; render(); document.getElementById('q') && document.getElementById('q').focus(); }
});
dev.addEventListener('keydown', e => { if (e.target.id === 'q' && e.key === 'Enter' && cfg().typing === 'B') { st.q = e.target.value; st.pend = null; render(); } });
dev.addEventListener('change', e => { if (e.target.dataset.act === 'sort') { st.sort = e.target.value; render(); } });
render();
