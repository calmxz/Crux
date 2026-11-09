// PROTOTYPE, throwaway (calmxz/Crux#752). Three app shells around the one session screen from #751.
const CUR = 'impl', CURNAME = 'Implicit differentiation (MATH101 week 7)';
function recTabs(g) { return `<div class="tabs" style="margin:4px 0 8px"><span class="${g ? '' : 'on'}">By date</span><span class="${g ? 'on' : ''}">By session</span></div>`; }
function masteredGrouped() {
  const by = {};
  MASTERED.forEach(m => (by[m.s] = by[m.s] || []).push(`<div class="mrow"><b>${m.t}</b>${m.note ? ` <span class="sub">(${m.note})</span>` : ''}<div class="sub">mastered ${m.d}</div></div>`));
  PASSED.forEach(p => (by[p.s] = by[p.s] || []).push(`<div class="mrow"><b>${p.t}</b> <span class="sub">objective on ${p.topic}, not yet mastered</span><div class="sub">passed ${p.d}</div></div>`));
  return `<div class="h">What you've mastered</div>${recTabs(true)}<div class="sub">Read-only. Grouped by session, most recent visit first.</div>` + Object.keys(by).map(k => `<div class="divider"><a>${k}</a></div>${by[k].join('')}`).join('');
}
function masteredHtml(sc) {
  if (sc && sc.grouped) return masteredGrouped();
  return `<div class="h">What you've mastered</div>${recTabs(false)}<div class="sub">Read-only. Each line opens its session.</div>
    ${MASTERED.map(m => `<div class="mrow"><b>${m.t}</b>${m.note ? ` <span class="sub">(${m.note})</span>` : ''}<div class="sub">${m.d} &middot; <a>${m.s}</a></div></div>`).join('')}
    <div class="sub" style="margin-top:14px">Objectives passed on topics not yet mastered</div>
    ${PASSED.map(p => `<div class="mrow"><b>${p.t}</b> <span class="sub">on ${p.topic}</span><div class="sub">${p.d} &middot; <a>${p.s}</a> ${p.note ? ' (' + p.note + ')' : ''}</div></div>`).join('')}`;
}
const DEL = {
  mastered:['Chain rule (MATH101 week 6)', 'This deletes everything in it, including 2 mastered topics from your record.'],
  check:   ['Projectile motion', `This deletes everything in it, including your half-done mastery check and 1 passed objective from your record. ${NS}`],
  passed:  ['Implicit differentiation (MATH101 week 7)', `This deletes everything in it, including 1 passed objective from your record and 2 files. ${NS}`],
  plain:   ['photosynthesis for my bio quiz', `This deletes everything in it. ${NS}`],
};
function deleteDlg(sc) {
  const k = (sc && sc.del) || 'mastered', d = DEL[k], typed = sc && sc.typedConfirm;
  const conf = typed ? `<div class="sub" style="margin-top:6px">Type <b>delete</b> to confirm ${NS}</div><input style="width:100%;font:inherit;border:1px solid var(--line);border-radius:6px;padding:6px;margin-top:4px" placeholder="delete">` : '';
  return `<div class="overlay"><div class="card"><b>Delete "${d[0]}"?</b>
    <p style="font-size:14px">${d[1]} It can't be undone. ${NS}</p>${conf}
    <div class="row" style="justify-content:flex-end"><span class="btn">Cancel</span><span class="btn" style="background:#b42318;color:#fff;border-color:#b42318;${typed ? 'opacity:.45' : ''}">Delete session</span></div></div></div>`;
}
function menuPop(top, left, sealed, right) {
  const pos = right != null ? `right:${right}px` : `left:${left}px`;
  const del = sealed ? `<div style="color:#8a909c;cursor:default">Delete<div class="sub">A sealed session can't be deleted. ${NS}</div></div>` : '<div class="danger">Delete</div>';
  return `<div class="menupop" style="top:${top}px;${pos}">${sealed ? '' : '<div>Rename</div>'}${del}</div>`;
}
function renameRow() { return `<div class="sline"><input value="Chain rule (MATH101 week 6)" style="width:100%;font:inherit;border:1px solid var(--me);border-radius:6px;padding:4px 6px"></div>`; }
function sealedCard() { return `<div class="card" style="max-width:520px;margin:30px auto">${SEALMSG}<div class="sub" style="margin-top:8px">It can't be opened or deleted.</div></div>`; }
function newThread(v) {
  return `<div class="thread"><div class="sysline">What would you like to learn? Type a topic, add your files, or both. ${NS}</div></div>
    <div class="pins"><div class="pin info">&#128206; MATH101 week 7.pdf &middot; 6 MB <span class="alink">&times;</span></div></div>`;
}
function topbar(v, phone, sc, title) {
  if (v === 'A') {
    const t = sc.renameTop ? `<input class="title" value="${title}" style="font:inherit;border:1px solid var(--me);border-radius:6px;padding:4px 6px">` : `<span class="title">${title}</span>`;
    return `<div class="topbar">${phone ? '<span class="brand" data-act="drawer">&#9776;</span>' : ''}${t}${sc.both ? '<span class="link" title="Rename or delete">&#8943;</span>' : ''}</div>`;
  }
  if (v === 'B') return `<div class="topbar"><span class="link">&larr; Home</span><span class="title">${title}</span>${sc.jump ? '<span class="btn small">Jump &#9662;</span>' : ''}<span class="link" title="Rename or delete">&#8943;</span></div>`;
  return `<div class="topbar"><span class="brand">Crux</span><span class="title" style="cursor:pointer">${title} &#9662;</span></div>`;
}
function sessionScreen(sc, v, phone, title) {
  if (sc.view === 'new') return topbar(v, phone, sc, 'New session') + `<div class="body"><div style="flex:1;display:flex;flex-direction:column">${newThread(v)}${composer({ typed:'the implicit differentiation part', ph:'' })}</div></div>`;
  return topbar(v, phone, sc, title || sc.title || CURNAME) + sessionBody(sc, v, phone) + (sc.viewer && (v === 'B' || (v === 'A' && phone)) ? viewerHtml(true) : '');
}
const VARIANTS = [
  { key:'A', name:'Sidebar', note:'the session list is a sidebar on desktop and a drawer (&#9776;) on a phone; opening the app goes back to the last session; "What you\'ve mastered" opens in the main area; files show their state in the panel; jump points are a list in the panel.', fn: shellA },
  { key:'B', name:'Home page', note:'opening the app shows a home page: a "What do you want to learn?" box, then Sessions and What you\'ve mastered as tabs; a session is full width with &larr; Home; rename and delete are in the session\'s &#8943; menu; file states are lines in the conversation; jump points are a Jump menu in the top bar.', fn: shellB },
  { key:'C', name:'Title switcher', note:'no list page: the session\'s title is a drop-down that lists sessions, New session and What you\'ve mastered; mastered opens as a sheet over the session; jump points are chips along the top of the conversation; a file opens inside the conversation.', fn: shellC },
];
function shellA(sc, phone) {
  const v = 'A', cur = sc.cur || CUR;
  let main;
  if (sc.view === 'mastered') main = topbar(v, phone, sc, "What you've mastered") + `<div class="home"><div class="wrap">${masteredHtml(sc)}</div></div>`;
  else if (sc.view === 'sealed') main = topbar(v, phone, sc, 'Reaction rates') + `<div class="home">${sealedCard()}</div>`;
  else main = sessionScreen(sc, v, phone);
  const lines = SESSIONS.map(s => (sc.view === 'rename' && s.id === 'chain') ? renameRow() : sessLine(s, s.id === (sc.view === 'sealed' ? 'seal' : cur), v)).join('');
  const side = `<div class="side" style="${phone ? 'position:absolute;left:0;top:0;bottom:0;width:86%;z-index:9;box-shadow:6px 0 20px rgba(0,0,0,.2)' : ''}">
    <div class="topbar"><span class="brand">Crux</span></div><div style="padding:10px 14px"><span class="btn primary" style="display:block;text-align:center">+ New session</span></div>
    <div class="sec">Sessions</div>${lines}<div style="flex:1"></div><div class="sline" style="border-top:1px solid var(--line)"><div class="nm">&#9733; What you've mastered</div></div></div>`;
  const drawer = !phone || ['list', 'manage', 'rename'].includes(sc.view) || sc.sealedMenu;
  const sealedIdx = SESSIONS.findIndex(x => x.sealed);
  let pop = sc.view === 'manage' ? menuPop(phone ? 240 : 236, phone ? 170 : 150) : '';
  if (sc.sealedMenu) pop = menuPop(phone ? 116 + sealedIdx * 58 : 136 + sealedIdx * 50, phone ? 120 : 110, true);
  if (sc.topMenu) pop = menuPop(46, 0, false, 12);
  const dlg = sc.view === 'delete' ? deleteDlg(sc) : '';
  const ex = sc.extra ? sc.extra(v, phone) : '';
  if (phone) return `<div style="display:flex;flex-direction:column;flex:1;min-height:0;position:relative">${main}${drawer ? '<div class="overlay" style="z-index:8"></div>' + side : ''}${pop}${dlg}${ex}</div>`;
  return `<div style="display:flex;flex:1;min-height:0;position:relative">${side}<div style="flex:1;display:flex;flex-direction:column;min-width:0">${main}</div>${pop}${dlg}${ex}</div>`;
}
function homeHtml(sc, phone) {
  const tab = sc.view === 'mastered' ? 'm' : 's';
  const lines = SESSIONS.map(s => sessLine(s, false, 'B')).join('');
  return `<div class="topbar"><span class="brand">Crux</span><span class="title"></span><span class="link">Settings</span></div><div class="home"><div class="wrap">
    <div class="bigask"><textarea placeholder="What do you want to learn? Type a topic, add your files, or both. (no spec wording)"></textarea><div class="row" style="justify-content:space-between"><span class="btn">&#128206; Add files</span><span class="btn primary">Start</span></div></div>
    <div class="tabs"><span class="${tab === 's' ? 'on' : ''}">Sessions</span><span class="${tab === 'm' ? 'on' : ''}">What you've mastered</span></div>
    <div class="card" style="padding:0 0 4px">${tab === 's' ? lines : `<div style="padding:12px">${masteredHtml(sc)}</div>`}</div></div></div>`;
}
function shellB(sc, phone) {
  const v = 'B';
  const home = ['open', 'list', 'mastered', 'sealed', 'delete-home'].includes(sc.view) || (sc.view === 'new');
  let h;
  if (sc.view === 'new') h = homeHtml(sc, phone).replace('<textarea placeholder', '<textarea style="min-height:40px" placeholder').replace('</textarea>', 'the implicit differentiation part</textarea><div class="pin info" style="margin:4px 0">&#128206; MATH101 week 7.pdf &middot; 6 MB <span class="alink">&times;</span></div>');
  else if (home) h = homeHtml(sc, phone);
  else h = sessionScreen(sc, v, phone, sc.view === 'manage' || sc.view === 'delete' || sc.view === 'rename' ? 'Chain rule (MATH101 week 6)' : null);
  if (sc.view === 'sealed') h += `<div class="overlay">${sealedCard().replace('margin:30px auto', 'margin:0')}</div>`;
  if (sc.view === 'manage') h += menuPop(48, phone ? 230 : 1010);
  if (sc.view === 'rename') h = h.replace('<span class="title">Chain rule (MATH101 week 6)</span>', `<input class="title" value="Chain rule (MATH101 week 6)" style="font:inherit;border:1px solid var(--me);border-radius:6px;padding:4px 6px">`);
  if (sc.view === 'delete') h += deleteDlg(sc);
  if (sc.jump) h += `<div class="dropdown" style="left:auto;right:${phone ? 10 : 330}px;width:260px">${JUMPS.map((j, i) => `<div class="sline ${i === 3 ? 'cur' : ''}"><div class="ln" style="color:inherit">${j}</div></div>`).join('')}</div>`;
  if (sc.extra) h += sc.extra(v, phone);
  return `<div style="display:flex;flex-direction:column;flex:1;min-height:0;position:relative">${h}</div>`;
}
function shellC(sc, phone) {
  const v = 'C';
  let h = sessionScreen(sc, v, phone);
  if (sc.viewer) h = h.replace('as on slide 30</a> of Lecture 8.', `as on slide 30</a> of Lecture 8.<div style="margin-top:6px;border:1px solid var(--line);border-radius:8px;overflow:hidden">${viewerHtml(false).replace('width:380px;border-left:1px solid var(--line)', '')}</div>`);
  const drop = ['list', 'manage', 'rename', 'sealed'].includes(sc.view);
  if (drop) {
    const lines = SESSIONS.map(s => (sc.view === 'rename' && s.id === 'chain') ? renameRow() : (sc.view === 'sealed' && s.sealed) ? sessLine(s, true, v) + `<div style="padding:8px 14px;font-size:13px;background:#f6f7f9">${SEALMSG}</div>` : sessLine(s, s.id === CUR, v)).join('');
    h += `<div class="dropdown"><input placeholder="Find a session"><div class="sline"><div class="nm" style="color:var(--me)">+ New session</div></div>${lines}<div class="sline"><div class="nm">&#9733; What you've mastered</div></div></div>`;
    if (sc.view === 'manage') h += menuPop(phone ? 250 : 250, phone ? 200 : 250);
  }
  if (sc.view === 'mastered') h += `<div class="sheet" style="top:52px">${masteredHtml(sc)}</div>`;
  if (sc.view === 'delete') h += deleteDlg(sc);
  if (sc.removeConfirm) h += `<div class="overlay">${removePop().replace('margin-top:8px;', 'max-width:360px;')}</div>`;
  if (sc.extra) h += sc.extra(v, phone);
  return `<div style="display:flex;flex-direction:column;flex:1;min-height:0;position:relative">${h}</div>`;
}
