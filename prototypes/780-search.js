// PROTOTYPE, throwaway (calmxz/Crux#780). The session search over the sample data, and the page's lines, snippets and empty states.
// ---------- search: word-prefix match, case-insensitive (a stand-in for Postgres full-text search, `simple` config) ----------
const toks = s => s.toLowerCase().split(/[^\p{L}\p{N}²³]+/u).filter(Boolean);
const has = (qt, text) => { const tt = toks(text); return qt.length > 0 && qt.every(w => tt.some(t => t.startsWith(w))); };
function find(s, c, qt) {
  const r = { where:[], hidden:false };
  if (s.sealed) {
    if (c.sealed === 'B') return r;
    if (!s.unnamed && has(qt, s.nm)) r.where.push({ k:'name' });
    return r;
  }
  if (has(qt, s.nm)) r.where.push({ k:'name' });
  s.topics.forEach(t => has(qt, t) && r.where.push({ k:'topic', t }));
  if (c.scope !== 'A') s.files.forEach(f => has(qt, f) && r.where.push({ k:'file', t:f }));
  if (c.scope === 'C') s.msgs.forEach((m, i) => {
    if (m.blocked || !has(qt, m.t)) return;
    if (m.hide === 'check') { if (c.check === 'B') r.hidden = true; return; }
    r.where.push({ k:'msg', i, m });
  });
  return r;
}
function results(c) {
  if (st.emptyCase === 'nos' && scene === 'empty') return { rows:[], total:0 };
  let all = SESSIONS.filter(s => !(s.sealed && c.sealed === 'C'));
  const total = all.length;
  const F = { run: s => s.now.startsWith('On:'), chk: s => s.badge && s.badge[0] === 'chk', wait: s => s.badge && s.badge[0] === 'wait',
    hold: s => s.badge && s.badge[0] === 'hold', mast: s => s.mastered > 0, none: s => !s.now && !s.mastered };
  if (c.filter !== 'A' && st.filt !== 'all') all = all.filter(F[st.filt]);
  const qt = toks(st.q);
  let rows = all.map(s => ({ s, r: qt.length ? find(s, c, qt) : { where:[], hidden:false } }));
  if (qt.length) rows = rows.filter(x => x.r.where.length || x.r.hidden);
  const S = { last:(a, b) => b.s.lastN - a.s.lastN, start:(a, b) => b.s.startN - a.s.startN, name:(a, b) => a.s.nm.localeCompare(b.s.nm), mast:(a, b) => b.s.mastered - a.s.mastered || b.s.lastN - a.s.lastN };
  rows.sort(S[c.sort === 'A' ? 'last' : st.sort]);
  return { rows, total, qt };
}

// ---------- drawing ----------
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
function markWords(text, qt) {
  return esc(text).replace(/[\p{L}\p{N}²³]+/gu, w => qt.some(q => w.toLowerCase().startsWith(q)) ? `<mark>${w}</mark>` : w);
}
function drawMath(tex) {   // a tiny stand-in for KaTeX: enough to show that y^2 is drawn as y²
  return esc(tex).replace(/\\cdot/g, '·').replace(/\\sin/g, 'sin ').replace(/\\cos/g, 'cos ').replace(/\\theta/g, 'θ').replace(/\^(\w)/g, '<sup>$1</sup>');
}
function msgHtml(t, qt) { return t.split(/(\$[^$]+\$)/).map(p => p.startsWith('$') ? `<i>${drawMath(p.slice(1, -1))}</i>` : markWords(p, qt || [])).join(''); }
const badge = b => b ? `<span class="badge ${b[0]}">${b[1]}</span>` : '';
const prog = pr => pr ? `<div class="prog">${Array.from({ length: pr[1] }, (_, i) => `<span class="s ${i < pr[0] ? 'd' : ''}"></span>`).join('')}<span class="sub" style="margin-left:6px">${pr[0]} of ${pr[1]}</span></div>` : '';
function nowLine(s) { return s.now; }
function lastLine(s, bare) { const n = bare ? '' : nowLine(s); return `${n ? n + ' &middot; ' : ''}${s.last}${s.ny && scene === 'layout' ? ' <span class="nospec">(8:00 pm on 7 Nov in New York, 8 Nov in Philippine time)</span>' : ''}`; }
function hitsHtml(x, c) {
  const { s, r } = x, qt = toks(st.q); let h = '';
  if (!qt.length) return '';
  const other = r.where.filter(w => w.k === 'topic' || w.k === 'file');
  if (!r.where.some(w => w.k === 'name')) other.slice(0, 2).forEach(w => h += `<div class="sub">${w.k === 'topic' ? 'Topic' : 'File'}: ${markWords(w.t, qt)} ${NS}</div>`);
  const msgs = r.where.filter(w => w.k === 'msg').reverse();
  if (msgs.length) {
    const snip = w => `<div class="hit" data-open="${s.id}" data-at="${w.i}"><span class="who">${w.m.who === 'me' ? 'You' : 'Tutor'}</span>${msgHtml(w.m.t, qt)}${w.m.wait ? ' <span class="sub">(waiting)</span>' : ''}</div>`;
    if (c.hit === 'A') h += snip(msgs[0]) + (msgs.length > 1 ? `<div class="sub">and ${msgs.length - 1} more in this conversation ${NS}</div>` : '');
    else if (c.hit === 'B') h += msgs.map(snip).join('');
    else h += `<div class="sub"><span class="tag">in the conversation ${NS}</span></div>`;
  }
  if (r.hidden) h += `<div class="sub">Check open: matches in its earlier teaching show after the check ${NS}</div>`;
  return h;
}
function more(s, c) { return c.menu === 'A' ? `<span class="more" data-menu="${s.id}" title="Rename or delete">&#8943;</span>` : ''; }
function line(x, c, phone) {
  const s = x.s;
  const extra = c.layout === 'B' && phone ? `<div class="sub">Started ${s.started}${s.mastered ? ` &middot; ${s.mastered} mastered` : ''} ${NS}</div>` : '';
  const bare = c.layout === 'D' || c.layout === 'E';
  return `<div class="sline" data-open="${s.id}"><div class="nm">${markWords(s.nm, toks(st.q))}${c.layout === 'E' ? '' : badge(s.badge)}</div><div class="ln">${lastLine(s, bare)}</div>${c.layout === 'E' ? '' : prog(s.pr)}${extra}${hitsHtml(x, c)}${more(s, c)}</div>`;
}
function tableHtml(rows, c) {
  return `<table class="t"><tr><th>Session</th><th>Now</th><th>Mastered</th><th>Last visit</th><th>Started</th>${c.menu === 'A' ? '<th></th>' : ''}</tr>${rows.map(x => { const s = x.s;
    return `<tr data-open="${s.id}"><td><b>${markWords(s.nm, toks(st.q))}</b>${badge(s.badge)}${hitsHtml(x, c)}</td><td class="sub">${nowLine(s) || ''}${prog(s.pr)}</td><td>${s.mastered || ''}</td><td>${s.last}</td><td>${s.started}</td>${c.menu === 'A' ? `<td><span class="a" data-menu="${s.id}">&#8943;</span></td>` : ''}</tr>`; }).join('')}</table>`;
}
function period(n) { return n >= 310 ? 'This week' : n >= 301 ? 'Earlier in November' : n >= 270 ? 'October' : n >= 240 ? 'September' : 'August'; }
function listHtml(rows, c, phone) {
  if (c.layout === 'B' && !phone) return tableHtml(rows, c);
  if (c.layout === 'C' && c.sort === 'A') {
    let h = '', cur = '';
    rows.forEach(x => { const p = period(x.s.lastN); if (p !== cur) { h += (cur ? '</div>' : '') + `<div class="grp-h">${p} ${NS}</div><div class="rows">`; cur = p; } h += line(x, c, phone); });
    return h + (cur ? '</div>' : '');
  }
  return `<div class="rows">${rows.map(x => line(x, c, phone)).join('')}</div>`;
}
const SEARCHED = { A:'session names and topics', B:'session names, topics and file names', C:'session names, topics, file names and conversations' };
function emptyHtml(c, total) {
  if (!total) return `<div class="empty"><p>No sessions yet. ${NS}</p><span class="btn primary">+ New session</span></div>`;
  return `<div class="empty"><p>No sessions match "${esc(st.q)}". ${NS}</p>${c.empty === 'B' ? `<p class="sub">The search looks through ${SEARCHED[c.scope]}. ${NS}</p>` : ''}<span class="btn" data-act="clear">Clear search</span></div>`;
}
function controls(c) {
  let h = '';
  const chips = c.filter === 'B' ? [['all', 'All'], ['run', 'Under way'], ['chk', 'Check open'], ['wait', 'Waiting'], ['hold', 'Remove a file']]
    : c.filter === 'C' ? [['all', 'All'], ['run', 'Under way'], ['mast', 'Mastered something'], ['none', 'Nothing yet']] : [];
  if (chips.length) h += chips.map(([k, l]) => `<span class="chipf ${st.filt === k ? 'on' : ''}" data-filt="${k}">${l}</span>`).join('') + ` ${NS}`;
  if (c.sort !== 'A') h += `<span style="flex:1"></span><select data-act="sort">${[['last', 'Last visit'], ['start', 'Started'], ['name', 'Name A to Z']].concat(c.sort === 'C' ? [['mast', 'Most mastered']] : []).map(([k, l]) => `<option value="${k}" ${st.sort === k ? 'selected' : ''}>${l}</option>`).join('')}</select>`;
  return h ? `<div class="controls">${h}</div>` : '';
}
function pageHtml(c, phone) {
  const { rows, total } = results(c);
  const limit = (c.paging === 'B' || c.paging === 'C') && !st.more ? 15 : Infinity;
  const shown = rows.slice(0, limit);
  const val = st.pend != null ? st.pend : st.q;
  const count = toks(st.q).length ? `${rows.length} of ${total} sessions match ${NS}` : `${total} sessions ${NS}`;
  return `<div class="page"><div class="wrap"><h1>All sessions</h1><div class="sub">${count}</div>
    <div class="search"><input id="q" type="search" placeholder="Search your sessions" value="${esc(val)}" autocomplete="off">${c.typing === 'B' ? '<span class="btn" data-act="go">Search</span>' : ''}</div>
    ${c.typing === 'B' ? `<div class="sub" style="margin:-4px 0 8px">Press Enter to search ${NS}</div>` : ''}
    ${controls(c)}${rows.length ? listHtml(shown, c, phone) : emptyHtml(c, total)}
    ${rows.length > shown.length && c.paging === 'C' ? `<div id="lazy" class="sub" style="text-align:center;padding:12px">Loading... ${NS}</div>` : ''}
    ${rows.length > shown.length && c.paging === 'B' ? `<div style="text-align:center;margin-top:10px"><span class="btn" data-act="more">Show ${rows.length - shown.length} more ${NS}</span></div>` : ''}
    <p class="sub" style="margin-top:14px">Try: ${['balloon', 'ball', 'y²', 'y^2', 'pdf', 'rate', 'chain', 'synthesis'].map(w => `<span class="a" data-try="${w}">${w}</span>`).join(' &middot; ')} <span class="nospec">(prototype helper)</span></p>
  </div></div>`;
}
