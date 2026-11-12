// PROTOTYPE, throwaway (calmxz/Crux#755). Part of 755-owner.html. Shared shell pieces, then variant A (one long page).

// ---------- the owner's own app (the #752 shell with the #753 sidebar foot) ----------
const OSESS = [ ['Staging smoke test', 'On: Two-step equations', 'Today'], ['Read-through of the check', 'Mastered last: Percentages', '9 Nov'] ];
function oside(p, o = {}) {
  const ownerItem = o.owner === 'A' ? `<div class="sline ${o.on ? 'cur' : ''}"><div class="nm">&#9881;&#65038; Owner page</div></div>`
    : o.owner === 'C' ? `<div class="sline ${o.on ? 'cur' : ''}"><div class="nm">Owner <span class="badge hold">${cCount()}</span></div><div class="ln">Needs you ${NS}</div></div>` : '';
  return `<div class="side" style="${p ? 'position:absolute;left:0;top:0;bottom:0;width:86%;z-index:9;box-shadow:6px 0 20px rgba(0,0,0,.2)' : ''}">
    <div class="topbar"><span class="brand">Crux</span></div><div style="padding:10px 14px"><span class="btn primary" style="display:block;text-align:center">+ New session</span></div>
    <div class="sec">Sessions</div>${OSESS.map((s, i) => `<div class="sline ${!o.on && i === 0 ? 'cur' : ''}"><div class="nm">${s[0]}</div><div class="ln">${s[1]} &middot; ${s[2]}</div><span class="more">&#8943;</span></div>`).join('')}
    <div style="flex:1"></div>
    <div class="sline" style="border-top:1px solid var(--line)"><div class="nm">&#9733; What you've mastered</div></div>
    ${ownerItem}<div class="sline"><div class="nm">Feedback</div></div>
    <div class="sline"><div class="nm">&#9881; Settings</div><div class="ln">owner@example.com</div></div></div>`;
}
// The owner's app: sidebar on desktop, drawer on a phone. main is the main area's html.
function oapp(p, main, o = {}) {
  if (p) return `<div style="display:flex;flex-direction:column;flex:1;min-height:0;position:relative">${main}${o.drawer ? '<div class="overlay" style="z-index:8"></div>' + oside(p, o) : ''}${o.overlay || ''}</div>`;
  return `<div style="display:flex;flex:1;min-height:0;position:relative">${oside(p, o)}<div style="flex:1;display:flex;flex-direction:column;min-width:0;position:relative">${main}</div>${o.overlay || ''}</div>`;
}
const otop = (p, title, right = '') => `<div class="topbar">${p ? '<span class="brand">&#9776;</span>' : ''}<span class="title">${title}</span>${right}</div>`;
const stageBadge = () => `<span class="badge ${isTrial() ? 'wait' : 'chk'}">${isTrial() ? 'Trial' : 'Open'}</span>`;
const dlgWrap = sc => sc.dlg ? `<div class="dlg"><div class="card">${DLG[sc.dlg]()}</div></div>` : '';
const sessionMain = p => otop(p, 'Staging smoke test') + `<div class="body"><div class="thread"><div class="msg tutor"><div class="who">Tutor</div>Solve 3x + 4 = 19. What would you do first?</div><div class="msg me">Take 4 from both sides</div></div></div>`;

// ---------- Variant A: one long page in the owner's app ----------
const SECTS_A = [
  ['', ['needs']], ['Trial', ['reqs', 'links', 'dead', 'notice', 'endtrial']], ['Safety', ['flags', 'closures', 'entered', 'reported']],
  ['Feedback', ['fb', 'quotes', 'shares']], ['Counts', ['path', 'arrivals', 'turned']], ['Money and limits', ['money', 'settings', 'cap']], ['Switches', ['switches']],
];
function VA(sc, p) {
  if (sc.entry) return oapp(p, sessionMain(p), { owner:'A', drawer:p });
  if (sc.reader) return oapp(p, otop(p, 'Owner page', stageBadge()) + reader(sc.reader), { owner:'A', on:true });
  const sects = SECTS_A.filter(s => s[1].some(b => ALLB[b]() !== ''));
  const jump = `<div class="jumpchips" style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px">${sects.filter(s => s[0]).map(s => `<span class="chip">${s[0]}</span>`).join('')}</div>`;
  const body = sects.map(s => `<div class="sect">${s[0] ? `<h1 style="font-size:18px">${s[0]}</h1>` : `<h1>Owner page ${stageBadge()}</h1>${jump}`}${s[1].map(b => ALLB[b]()).join('')}</div>`).join('');
  return oapp(p, otop(p, 'Owner page', stageBadge()) + `<div class="op lp ${p ? 'phoneop' : ''}">${body}</div>`, { owner:'A', on:true, overlay:dlgWrap(sc) });
}
