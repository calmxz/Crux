// PROTOTYPE, throwaway (calmxz/Crux#752). Shared pieces: the session screen settled in #751, plus files.
function badge(b) { return b ? `<span class="badge ${b[0]}">${b[1]}</span>` : ''; }
function sessLine(s, cur, v) {
  const mode = window.CURSC && CURSC.sealMode;
  if (s.demo && !mode) return '';
  const ln = s.sealed ? 'Sealed: tap to see why' : (s.ln || '&nbsp;');
  if (s.sealed && mode) s = Object.assign({}, s, { nm: mode === 'B' || (mode === 'C' && s.unnamed) ? 'Sealed session' : s.nm });
  return `<div class="sline ${cur ? 'cur' : ''} ${s.sealed ? 'sealed' : ''}" data-sess="${s.id}"><div class="nm">${s.nm}${badge(s.badge)}</div>
    <div class="ln">${ln} &middot; ${s.when}</div>${(window.CURSC && CURSC.progress && s.pr) ? progBar(s.pr) : ''}${v !== 'B' ? '<span class="more" title="Rename or delete">&#8943;</span>' : ''}</div>`;
}
function progBar(pr) {
  const m = { s:'sh', i:'ip', p:'ns', h:'sh' };
  return `<div style="display:flex;gap:3px;align-items:center;margin-top:4px;max-width:180px">${pr[2].split('').map(c => `<span class="seg ${m[c]}" style="flex:1;height:5px;border-radius:3px;background:${c === 'p' ? '#e3e6ec' : ''}"></span>`).join('')}<span class="sub" style="margin-left:6px;white-space:nowrap">${pr[0]} of ${pr[1]}</span></div>`;
}
function listHtml(v, cur) { return SESSIONS.map(s => sessLine(s, s.id === cur, v)).join(''); }
function objHtml(list) {
  return '<ul class="obj">' + (list || OBJ).map(o => `<li><span class="st ${o.s}">${LBL[o.s]}</span><div>${o.n}. ${o.t}</div></li>`).join('') + '</ul>';
}
const INTHREAD = ['reading', 'waiting', 'failed', 'paused'];
function fileRow(f, v, sc) {
  const x = sc.check ? '' : `<span class="x" title="Remove" data-act="remove">&times;</span>`;
  let st = `<div class="st2">${f.m}</div>`;
  if (f.s === 'reading') st = '<div class="st2">Reading&hellip;</div>';
  if (f.s === 'waiting') st = `<div class="wt">Your file is saved. It'll be read when you're back tomorrow.</div>`;
  if (f.s === 'paused') st = `<div class="wt">Saved. It'll be read when files are back. ${NS}</div>`;
  if (f.s === 'failed') return `<div class="frow"><span class="ic">PDF</span><div><div class="fn">${f.n}</div><div class="bad">Couldn't read this file, so it wasn't added. Try again, or use another file.</div><span class="alink">Dismiss</span></div></div>`;
  if (f.s === 'held') st = `<div class="bad">The tutor can't help with this file. Remove it to continue. ${NS}</div><span class="btn small" style="margin-top:4px">Remove file</span>`;
  const mark = f.mark ? `<div class="mmark"><b>Slide 30 may have a mistake.</b> It shows 5(3x&sup2; + 1)&#8308;. A possible correction is 5(3x&sup2; + 1)&#8308; &middot; 6x, but it could be wrong too. Ask your teacher, then <a>tell the tutor what they said</a>. <a>No one to ask, go with the correction</a></div>` : '';
  const ext = f.n.split('.').pop().toUpperCase();
  return `<div class="frow"><span class="ic">${ext}</span><div style="flex:1"><div class="fn">${f.n}</div>${st}${mark}</div>${x}</div>`;
}
function filesHtml(sc, v) {
  let fs = FILES[sc.files || 'plain'];
  if (v === 'B') fs = fs.filter(f => !INTHREAD.includes(f.s));
  if (sc.removed || (sc.removeConfirm && v === 'B')) fs = fs.filter(f => f.n !== 'Lecture 8 slides.pptx');
  const pop = (sc.removeConfirm && v === 'A') ? removePop() : '';
  return `<div class="sub" style="margin-top:14px">Files</div>${fs.map(f => fileRow(f, v, sc)).join('') || '<div class="sub">No files yet</div>'}${pop}`;
}
function removePop() {
  return `<div class="card" style="margin-top:8px;box-shadow:0 6px 16px rgba(0,0,0,.12)"><b>Remove Lecture 8 slides.pptx?</b>
    <p style="margin:6px 0;font-size:13px">What the tutor already said about this file stays in the conversation. To erase that too, delete the session.</p>
    <div class="row"><span class="btn small">Cancel</span><span class="btn small primary">Remove</span></div></div>`;
}
function hereHtml() {
  return `<div class="sub" style="margin-top:14px">Mastered in this session ${NS}</div>` + MASTERED.filter(m => m.s === 'Chain rule (MATH101 week 6)').map(m => `<div class="frow"><span class="st pa">mastered</span><div style="flex:1">${m.t}${m.note ? ` <span class="sub">(${m.note})</span>` : ''}<div class="sub">${m.d} &middot; <a class="alink">see the check</a></div></div></div>`).join('');
}
function jumpList() { return `<div class="sub" style="margin-top:14px">Jump to</div>` + JUMPS.map((j, i) => `<div class="frow" style="cursor:pointer"><span>${j}</span>${i === 3 ? '<span class="x">&#9664; here</span>' : ''}</div>`).join(''); }
function railInner(sc, v) {
  return `<div class="sub">Topic</div><b>${sc.topic || 'Implicit differentiation'}</b><div class="sub">from ${sc.from || 'MATH101 week 7.pdf'}</div>
    <div style="margin-top:10px">${objHtml(sc.obj)}</div>${sc.here ? hereHtml() : ''}${(sc.jump && v === 'A') ? jumpList() : ''}${filesHtml(sc, v)}`;
}
function threadItem(it, v) {
  if (it.only && it.only !== v) return ''; if (it.not && it.not.includes(v)) return '';
  if (it.t === 'tutor') return `<div class="msg tutor"><div class="who">Tutor</div>${it.h}</div>`;
  if (it.t === 'me') return `<div class="msg me">${it.h}</div>`;
  if (it.t === 'sys') return `<div class="sysline ${it.k || ''}">${it.h}</div>`;
  if (it.t === 'div') return `<div class="divider" id="${it.id || ''}">${it.h}</div>`;
  return it.h;
}
function threadFileLines(sc) {
  return FILES[sc.files || 'plain'].filter(f => INTHREAD.includes(f.s)).map(f => {
    if (f.s === 'reading') return `<div class="sysline">${f.n}: Reading&hellip;</div>`;
    if (f.s === 'waiting') return `<div class="sysline warn">${f.n}: Your file is saved. It'll be read when you're back tomorrow.</div>`;
    if (f.s === 'paused') return `<div class="sysline warn">${f.n}: saved. It'll be read when files are back. ${NS}</div>`;
    return `<div class="sysline stop">${f.n}: Couldn't read this file, so it wasn't added. Try again, or use another file. <span class="alink">Dismiss</span></div>`;
  }).join('');
}
function composer(sc) {
  const off = sc.filesOff ? 'disabled title="Files are paused"' : '';
  return `<div class="composer"><button class="btn" ${off}>&#128206; File</button><input placeholder="${sc.ph || 'Reply to the tutor'}" value="${sc.typed || ''}"><button class="btn primary">Send</button></div>`;
}
function pinsHtml(sc, v) {
  const p = (sc.pins || []).filter(x => !x.only || x.only.includes(v));
  return p.length ? `<div class="pins" style="padding-bottom:6px">${p.map(x => `<div class="pin ${x.k}">${x.h}</div>`).join('')}</div>` : '';
}
function sessionBody(sc, v, phone) {
  const items = (sc.thread || TEACH).map(it => threadItem(it, v)).join('') + (v === 'B' ? threadFileLines(sc) : '');
  const chips = (sc.jump && v === 'C') ? `<div class="jumpchips">${JUMPS.map((j, i) => `<span class="${i === 3 ? 'on' : ''}">${j}</span>`).join('')}</div>` : '';
  const strip = phone ? `<div class="segs">${(sc.obj || OBJ).map(o => `<span class="seg ${o.s}"></span>`).join('')}<span class="cap">1 of 4 &#9662;</span></div>` : '';
  const drop = (phone && sc.panelOpen && !(sc.viewer && v !== 'C')) ? `<div class="sheet" style="top:46px">${railInner(sc, v)}</div>` : '';
  const main = `<div style="flex:1;display:flex;flex-direction:column;min-width:0;position:relative">${strip}${drop}<div class="thread">${chips}${items}</div>${pinsHtml(sc, v)}${composer(sc)}${sc.dropzone && !phone ? '<div class="drop">Drop files to add them to this session</div>' : ''}</div>`;
  const side = phone ? '' : (sc.viewer && v === 'A' ? viewerHtml(false) : `<div class="rail">${railInner(sc, v)}</div>`);
  return `<div class="body">${main}${side}</div>`;
}
function viewerHtml(full) {
  return `<div class="viewer" style="${full ? 'position:absolute;inset:0;z-index:8' : 'width:380px;border-left:1px solid var(--line)'}">
    <div class="vbar"><b style="flex:1">Lecture 8 slides.pptx</b><span>Slide 30 of 31</span><span class="btn small">&times; Close</span></div>
    <div class="slide hl"><b>Implicit differentiation</b><br><br>x&sup2; + y&sup2; = 25<br>d/dx(x&sup2;) + d/dx(y&sup2;) = 0<br>2x + 2y &middot; dy/dx = 0<br><br><i>Speaker notes: treat y as a function of x.</i></div>
    <div class="thumbs">${[27, 28, 29, 30, 31].map(n => `<span class="${n === 30 ? 'on' : ''}">${n}</span>`).join('')}</div></div>`;
}
