// PROTOTYPE, throwaway (calmxz/Crux#754). The landing page, guest mode and trial links. See 754-landing.html.
// Held fixed in every variant: the session screen (#751), the app shell (#752), the sign-in card page and the
// opening-page pattern (#753), the refused-upload pinned line, the age card and the re-mark notices in the thread.
const NS = '<span class="nospec">[no spec wording]</span>';
const OPEN = t => `<div class="callout" style="margin-top:8px"><b>Open question:</b> ${t}</div>`;
const tb = on => `<span class="tb ${on ? 'on' : ''}">${on ? '&#10003;' : ''}</span>`;
const LIMIT = 'Guest mode: up to 10 tutor replies. Nothing is saved. Don\'t type personal details.';
const UPLOAD = 'Uploading your own files needs a trial link.';
const REGION = 'Crux isn\'t available in your region yet.';
const DAY = 'Guest mode is full for today. Back tomorrow.';
const MONTH = 'Guest mode is full for this month. Back on 1 Dec.';
const LINKNOTE = 'This link is for you only. Anyone with it sees your sessions and uses your limit. If it\'s used on more than 3 browsers, it may be switched off. Don\'t type or upload personal details, such as your name on a problem sheet.';
const DEVNOTE = 'To use Crux on another device, open your invite email there and tap the link.';
const REQLINE = 'Trial places are limited. Request once; we\'ll email you a private link if you\'re approved. We keep your email only until we approve or decline your request, at most 30 days. <a>Privacy Notice</a>';
const SAMPLES = [
  { t:'Solve a two-step equation', s:'Algebra &middot; about 10 minutes' },
  { t:'Work out a percentage change', s:'Everyday maths &middot; about 10 minutes' },
  { t:'Write a clear topic sentence', s:'Writing &middot; about 10 minutes' },
];
const SESS = [
  { nm:'Implicit differentiation (MATH101 week 7)', ln:'On: Implicit differentiation', when:'Today', pr:[1, 4] },
  { nm:'Chain rule (MATH101 week 6)', ln:'Mastered last: The chain rule', when:'Yesterday' },
  { nm:'Personal essay', ln:'On: Thesis statements', when:'6 Nov', pr:[2, 3] },
];
const legal = (o = {}) => o.open ? '<a>Terms of Use</a> &middot; <a>Privacy Policy</a> &middot; <a>Who runs Crux</a>' : '<a>Trial Terms</a> &middot; <a>Privacy Notice</a> &middot; <a>Who runs Crux</a>';
const video = cap => `<div class="video"><span class="play">&#9654;</span><span class="vcap">${cap || 'Demo video: one learner, from a typed request to a passed check'} ${NS}</span></div>`;
const AGE18 = `<span class="age18">Crux is for adults (18+)</span> ${NS}`;
const gatePage = (card, wide) => `<div class="gatebar"><span class="brand">Crux</span></div><div class="gate"><div class="card ${wide ? 'wide' : ''}">${card}</div></div>`;
const dlg = card => `<div class="dlg"><div class="card">${card}</div></div>`;
const banner = (kind, html, x = true) => `<div class="banner ${kind}"><span>${html}</span>${x ? '<span class="link">Dismiss</span>' : ''}</div>`;

// ---------- the guest's app shell (#752 shell; what it holds is this ticket's question G1) ----------
function gside(p, o = {}) {
  const cur = o.cur ? `<div class="sline cur"><div class="nm">${o.cur}</div><div class="ln">This tab only ${NS}</div></div>` : `<div class="sline"><div class="ln">Your guest session shows here ${NS}</div></div>`;
  return `<div class="side" style="${p ? 'position:absolute;left:0;top:0;bottom:0;width:86%;z-index:9;box-shadow:6px 0 20px rgba(0,0,0,.2)' : ''}">
    <div class="topbar"><span class="brand">Crux</span><span class="badge seal">Guest</span></div>
    <div class="sec">Your topic</div>${cur}
    <div class="sec">Sample topics</div>${SAMPLES.map((s, i) => `<div class="sline ${o.sample === i ? 'cur' : ''}"><div class="nm">${s.t}</div><div class="ln">${s.s}</div></div>`).join('')}
    <div style="flex:1"></div>
    <div style="padding:12px 14px;border-top:1px solid var(--line)">${o.noReq ? '' : '<span class="btn primary" style="display:block;text-align:center">Request access</span><div class="sub" style="margin-top:4px">Your own trial link: saved sessions and your own files. ' + NS + '</div>'}
    <div class="sub" style="margin-top:8px">${legal()}</div></div></div>`;
}
function gtop(p, title, o = {}) {
  const right = (o.count ? `<span class="counter">${o.count}</span>` : '') + (o.topReq ? '<span class="btn small">Request access</span><span class="btn small">Sign in</span>' : '');
  return `<div class="topbar">${p ? '<span class="brand">&#9776;</span>' : ''}<span class="title">${title}</span>${right}</div>`;
}
function composer(o = {}) {
  if (o.off) return `<div class="lockline" style="color:#3b4252">${o.off}</div>`;
  const pins = o.pins ? `<div class="pins" style="padding-top:8px">${o.pins}</div>` : '';
  return `${pins}<div class="composer"><span class="btn" title="Add files">&#128206;</span><input placeholder="${o.ph || 'Reply to the tutor'}"><span class="btn primary">Send</span></div>`;
}
function grail(o = {}) {
  const objs = o.objs || [['ip', 'In progress', 'Read a slope from a graph'], ['ns', 'Not started', 'Write y = mx + b from two points'], ['ns', 'Not started', 'Explain what the slope means']];
  return `<div class="rail"><div class="h">${o.topic || 'Slope of a line'}</div><ul class="obj">${objs.map(x => `<li><span class="st ${x[0]}">${x[1]}</span>${x[2]}</li>`).join('')}</ul>
    ${o.foot || `<div class="sub" style="margin-top:12px">Files</div><div class="sub">${UPLOAD} ${NS}</div>`}</div>`;
}
function gsession(p, o = {}) {
  return gtop(p, o.title || 'Slope of a line', { count: o.count }) + (o.strip && p ? `<div class="strip"><span>${o.strip}</span><span>&#9662;</span></div>` : '') + (o.checkbar || '') +
    `<div class="body"><div style="flex:1;display:flex;flex-direction:column;min-width:0"><div class="thread">${o.thread}</div>${composer(o.comp || {})}</div>${!p ? grail(o.rail || {}) : ''}</div>`;
}
function gapp(p, main, o = {}) {
  const side = gside(p, o);
  const extra = o.overlay || '';
  if (p) return `<div style="display:flex;flex-direction:column;flex:1;min-height:0;position:relative">${main}${o.drawer ? '<div class="overlay" style="z-index:8"></div>' + side : ''}${extra}</div>`;
  return `<div style="display:flex;flex:1;min-height:0;position:relative">${side}<div style="flex:1;display:flex;flex-direction:column;min-width:0;position:relative">${main}</div>${extra}</div>`;
}

// ---------- the trial link's app (the account shell from #752 and #753, with "Trial link" in place of the email) ----------
function tside(p, o = {}) {
  const line = (s, i) => `<div class="sline ${!o.on && i === 0 ? 'cur' : ''}"><div class="nm">${s.nm}</div><div class="ln">${s.ln} &middot; ${s.when}</div>${s.pr ? `<div style="display:flex;gap:6px;align-items:center;margin-top:3px"><div class="meter" style="flex:1;height:5px;margin:0"><i style="width:${s.pr[0] / s.pr[1] * 100}%"></i></div><span class="sub">${s.pr[0]} of ${s.pr[1]}</span></div>` : ''}<span class="more">&#8943;</span></div>`;
  return `<div class="side" style="${p ? 'position:absolute;left:0;top:0;bottom:0;width:86%;z-index:9;box-shadow:6px 0 20px rgba(0,0,0,.2)' : ''}">
    <div class="topbar"><span class="brand">Crux</span></div><div style="padding:10px 14px"><span class="btn primary" style="display:block;text-align:center">+ New session</span></div>
    <div class="sec">Sessions</div>${(o.empty ? [] : SESS).map(line).join('')}<div style="flex:1"></div>
    <div class="sline" style="border-top:1px solid var(--line)"><div class="nm">&#9733; What you've mastered</div></div>
    <div class="sline ${o.on === 'feedback' ? 'cur' : ''}"><div class="nm">Feedback</div></div>
    <div class="sline ${o.on === 'settings' ? 'cur' : ''}"><div class="nm">&#9881; Settings</div><div class="ln">Trial link ${NS}</div></div></div>`;
}
function tthread(extra = '') {
  return `<div class="divider">Objective 1: y terms</div>
    <div class="msg tutor"><div class="who">Tutor</div>When you differentiate y&sup2; with respect to x, what extra factor appears?</div>
    <div class="msg me">2y times dy/dx?</div>
    <div class="msg tutor"><div class="who">Tutor</div>Yes. Now try x&sup2; + y&sup2; = 25 on your own.</div>${extra}`;
}
function trail() {
  return `<div class="rail"><div class="h">Implicit differentiation</div><ul class="obj">
    <li><span class="st ip">In progress</span>Differentiate y terms</li><li><span class="st ns">Not started</span>Solve for dy/dx</li>
    <li><span class="st ns">Not started</span>Tangent lines</li><li><span class="st ns">Not started</span>Second derivatives</li></ul>
    <div class="sub" style="margin-top:12px">Files</div><div class="frow"><span class="ic">PDF</span><div><div class="fn">MATH101 week 7.pdf</div><div class="st2">12 pages</div></div><span class="x">&times;</span></div></div>`;
}
function tsession(p, o = {}) {
  return `<div class="topbar">${p ? '<span class="brand">&#9776;</span>' : ''}<span class="title">${SESS[0].nm}</span><span class="link">&#8943;</span></div>${o.top || ''}
    <div class="body"><div style="flex:1;display:flex;flex-direction:column;min-width:0"><div class="thread">${tthread(o.extra)}</div>${composer(o.comp || {})}</div>${!p ? trail() : ''}</div>`;
}
function tapp(p, main, o = {}) {
  const side = tside(p, o);
  if (p) return `${o.appBanner || ''}<div style="display:flex;flex-direction:column;flex:1;min-height:0;position:relative">${main}${o.drawer ? '<div class="overlay" style="z-index:8"></div>' + side : ''}${o.overlay || ''}</div>`;
  return `${o.appBanner || ''}<div style="display:flex;flex:1;min-height:0;position:relative">${side}<div style="flex:1;display:flex;flex-direction:column;min-width:0;position:relative">${main}</div>${o.overlay || ''}</div>`;
}
const tstart = (p, extra, ready) => `<div class="topbar">${p ? '<span class="brand">&#9776;</span>' : ''}<span class="title">New session</span></div>
  <div class="home"><div class="wrap" style="max-width:560px;margin-top:40px"><div class="bigask"><textarea placeholder="What do you want to learn? Type a topic, add your files, or both"></textarea><div class="row" style="justify-content:space-between"><span class="btn">Add files</span><span class="btn primary" ${extra && !ready ? 'style="opacity:.45"' : ''}>Start</span></div>${extra ? `<div style="border-top:1px solid var(--line);margin-top:8px;padding-top:4px">${extra}</div>` : ''}</div></div></div>`;
