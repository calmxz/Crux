// PROTOTYPE, throwaway (calmxz/Crux#753). Sign-up, settings, feedback and closing an account.
// The app shell (sidebar on desktop, drawer on a phone) is fixed, as decided in #752. Variants differ in how
// each surface is built: A = pages, B = dialogs and panels over the app, C = a separate settings area.
const NS = '<span class="nospec">[no spec wording]</span>';
const OPEN = t => `<div class="callout" style="margin-top:8px"><b>Open question:</b> ${t}</div>`;
const EMAIL = 'ana@example.com';
const SESS = [
  { nm:'Implicit differentiation (MATH101 week 7)', ln:'On: Implicit differentiation', when:'Today', pr:[1,4] },
  { nm:'Chain rule (MATH101 week 6)', ln:'Mastered last: The chain rule', when:'Yesterday' },
  { nm:'Personal essay', ln:'On: Thesis statements', when:'6 Nov', pr:[2,3] },
  { nm:'Cell respiration (BIO110)', ln:'Mastered last: Glycolysis', when:'30 Oct' },
];
const CURNAME = SESS[0].nm;

// ---------- shell pieces (the #752 sidebar, held fixed) ----------
function sline(s, cur) {
  const bar = s.pr ? `<div style="display:flex;gap:6px;align-items:center;margin-top:3px"><div class="meter" style="flex:1;height:5px;margin:0"><i style="width:${s.pr[0] / s.pr[1] * 100}%"></i></div><span class="sub">${s.pr[0]} of ${s.pr[1]}</span></div>` : '';
  return `<div class="sline ${cur ? 'cur' : ''}"><div class="nm">${s.nm}</div><div class="ln">${s.ln ? s.ln + ' &middot; ' : ''}${s.when}</div>${bar}<span class="more">&#8943;</span></div>`;
}
function sideFooter(v, o) {
  const who = o.trial ? 'Trial link' : EMAIL;
  const m = `<div class="sline" style="border-top:1px solid var(--line)"><div class="nm">&#9733; What you've mastered</div></div>`;
  if (v === 'A') return m + `<div class="sline ${o.on === 'feedback' ? 'cur' : ''}"><div class="nm">Feedback</div></div>
    <div class="sline ${o.on === 'settings' ? 'cur' : ''}"><div class="nm">&#9881; Settings</div><div class="ln">${who}</div></div>`;
  if (v === 'B') return m;
  return m + `<div class="sline ${o.acct ? 'cur' : ''}"><div class="nm">&#8943; Account</div><div class="ln">${who}</div></div>`;
}
function sidebar(v, phone, o) {
  return `<div class="side" style="${phone ? 'position:absolute;left:0;top:0;bottom:0;width:86%;z-index:9;box-shadow:6px 0 20px rgba(0,0,0,.2)' : ''}">
    <div class="topbar"><span class="brand">Crux</span></div><div style="padding:10px 14px"><span class="btn primary" style="display:block;text-align:center">+ New session</span></div>
    <div class="sec">Sessions</div>${SESS.map((s, i) => sline(s, !o.on && i === 0)).join('')}<div style="flex:1"></div>${sideFooter(v, o)}</div>`;
}
function topbar(v, phone, title, o = {}) {
  const right = v === 'B' ? `${o.noFeedback ? '' : '<span class="btn small">Feedback</span>'}<span class="avatar" title="${o.trial ? 'Trial link' : EMAIL}">${o.trial ? 'T' : 'A'}</span>` : (o.menu ? '<span class="link">&#8943;</span>' : '');
  return `<div class="topbar">${phone ? '<span class="brand">&#9776;</span>' : ''}<span class="title">${title}</span>${right}</div>`;
}
function thread(o = {}) {
  const age = o.age ? `<div class="card" style="align-self:center;max-width:340px"><b>Crux is for people 18 and over. Are you under 18?</b><div class="row"><span class="btn">Yes</span><span class="btn">No</span></div></div>` : '';
  return `<div class="thread"><div class="divider">Objective 1: y terms</div>
    <div class="msg tutor"><div class="who">Tutor</div>When you differentiate y&sup2; with respect to x, what extra factor appears?</div>
    <div class="msg me">2y times dy/dx?</div>
    <div class="msg tutor"><div class="who">Tutor</div>Yes. Now try x&sup2; + y&sup2; = 25 on your own.</div>${age}</div>`;
}
function composer(o = {}) {
  if (o.lock) return `<div class="lockline">${o.lock}</div>`;
  return `<div class="composer"><span class="btn" title="Add files">&#128206;</span><input placeholder="Reply to the tutor"><span class="btn primary">Send</span></div>`;
}
function rail(o = {}) {
  const x = o.lock ? '<span class="x" style="opacity:.35">&times;</span>' : '<span class="x">&times;</span>';
  return `<div class="rail"><div class="h">Implicit differentiation</div><ul class="obj">
    <li><span class="st ip">In progress</span>Differentiate y terms</li><li><span class="st ns">Not started</span>Solve for dy/dx</li>
    <li><span class="st ns">Not started</span>Tangent lines</li><li><span class="st ns">Not started</span>Second derivatives</li></ul>
    <div class="sub" style="margin-top:12px">Files</div><div class="frow"><span class="ic">PDF</span><div><div class="fn">MATH101 week 7.pdf</div><div class="st2">12 pages</div></div>${x}</div></div>`;
}
function sessionMain(v, phone, o = {}) {
  return topbar(v, phone, CURNAME, { ...o, menu: true }) + (o.bannerTop || '') +
    `<div class="body"><div style="flex:1;display:flex;flex-direction:column;min-width:0">${thread(o)}${composer(o)}</div>${!phone && !o.noRail ? (o.panel || rail(o)) : ''}</div>`;
}
function shell(v, phone, main, o = {}) {
  const side = sidebar(v, phone, o);
  const extra = (o.pop || '') + (o.overlay || '');
  if (phone) return `${o.appBanner || ''}<div style="display:flex;flex-direction:column;flex:1;min-height:0;position:relative">${main}${o.drawer ? '<div class="overlay" style="z-index:8"></div>' + side : ''}${extra}</div>`;
  return `${o.appBanner || ''}<div style="display:flex;flex:1;min-height:0;position:relative">${side}<div style="flex:1;display:flex;flex-direction:column;min-width:0;position:relative">${main}</div>${extra}</div>`;
}
const pageMain = (v, phone, title, html, o = {}) => topbar(v, phone, title, o) + `<div class="home"><div class="wrap" style="max-width:640px">${html}</div></div>`;
const gatePage = card => `<div class="gatebar"><span class="brand">Crux</span></div><div class="gate"><div class="card">${card}</div></div>`;
const dlg = (card, wide) => `<div class="dlg ${wide ? 'wide' : ''}"><div class="card">${card}</div></div>`;
const tb = on => `<span class="tb ${on ? 'on' : ''}">${on ? '&#10003;' : ''}</span>`;
const landing = () => `<div class="gatebar"><span class="brand">Crux</span><span style="flex:1"></span><span class="btn small">Sign in</span></div>
  <div class="gate" style="align-items:flex-start"><div class="placeholder" style="max-width:640px;width:100%">Landing page: the pre-written example, the 18+ line, guest mode. Laid out by "Prototype: the landing page, guest mode and trial links", not here.</div></div>`;

