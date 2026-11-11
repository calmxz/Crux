// PROTOTYPE, throwaway (calmxz/Crux#754). Part of 754-landing.html; see that file's header.
// The landing page in three variants. A: a long page in sections, guest mode opens the app.
// B: one screen led by the start box, with Request access and Who runs Crux further down the same page.
// C: the public link opens the app shell as a guest, with the landing page's parts in the start area.
const OWNBOX = (o = {}) => `<div class="bigask" ${o.id ? `id="${o.id}"` : ''}><textarea placeholder="What do you want to learn? Type a topic" ${o.dis ? 'disabled' : ''}>${o.typed || ''}</textarea>
  <div class="row" style="justify-content:space-between;align-items:center"><span class="sub">${o.wake ? 'Starting the tutor&hellip; ' + NS : ''}</span><span class="btn primary" ${o.dis || (o.ticks && !(o.ticks[0] && o.ticks[1])) ? 'style="opacity:.45"' : ''}>Start</span></div>
  ${o.ticks ? `<div style="border-top:1px solid var(--line);margin-top:8px;padding-top:4px">${ticks(o.ticks)}</div>` : ''}</div><div class="limitline">${LIMIT}</div>`;
function ticks(t = [false, false]) {
  return `<div class="tick">${tb(t[0])}<span>I am 18 or over</span></div><div class="tick">${tb(t[1])}<span>I agree to the <a>Trial Terms</a> and <a>Privacy Notice</a></span></div>`;
}
// what sits where guest mode would be, by state
function guestPart(v, mode, o = {}) {
  const line = (kind, t) => `<div class="sysline ${kind}" style="display:block;max-width:none">${t}</div>`;
  if (mode === 'eu') return line('', REGION);
  if (mode === 'full') return line('stop', DAY) + (v === 'B' ? '' : '<div class="sub" style="margin-top:6px">(the demo video stays on the page)</div>');
  if (mode === 'fullmonth') return line('stop', MONTH) + `<div class="sub" style="margin-top:6px">${NS}: the month's wording is a question (see the note).</div>`;
  if (mode === 'paused') return line('warn', 'Guest mode is paused while we fix something. ' + NS);
  if (mode === 'down') return line('stop', 'Crux can\'t be reached right now. Try again in a few minutes. ' + NS) + OWNBOX({ dis: true });
  const ready = !o.ticks || (o.ticks[0] && o.ticks[1]);
  const samples = v === 'B' ? `<div class="sub" style="margin-top:12px">Or try a sample topic, about 10 minutes, with a 2-problem check at the end:</div><div class="chips2" ${ready ? '' : 'style="opacity:.45"'}>${SAMPLES.map(s => `<span>${s.t}</span>`).join('')}</div>`
    : `<div class="sub" style="margin:4px 0 8px">A sample topic: about 10 minutes, taught then checked with 2 problems. It earns nothing. ${NS}</div><div class="samples ${o.phone ? 'col' : ''}">${SAMPLES.map(s => `<div class="scard"><div class="t">${s.t}</div><div class="s">${s.s}</div></div>`).join('')}</div>
      <div class="sub" style="margin:16px 0 8px">Or your own topic: ${NS}</div>`;
  const box = OWNBOX({ wake: mode === 'wake', typed: mode === 'wake' ? 'slope of a line' : '', ticks: o.ticks });
  if (v === 'C') return box;
  return v === 'B' ? box + samples : samples + box;
}
const reqAllowed = mode => !['eu', 'post', 'open'].includes(mode);
const EXAMPLE = `<div class="example"><div class="msg me" style="align-self:flex-end">I have a stats exam, help with hypothesis testing</div>
  <div class="msg tutor">Two quick questions: is this for a course (which one)? And which part worries you most: setting up the hypotheses, or reading a p-value?</div>
  <div class="msg me" style="align-self:flex-end">STAT101, p-values</div>
  <div class="msg tutor"><b>Topic: Reading a p-value</b><br>1. Say what a p-value measures<br>2. Decide at a 5% level<br>3. Explain a result in plain words<br>Say "go" to start, or change any of these.</div>
  <div class="sub">A written example, not a live tutor. ${NS}</div></div>`;
const ladderTop = (mode, o = {}) => `<div class="gatebar"><span class="brand">Crux</span><span style="flex:1"></span>${reqAllowed(mode) ? `<span class="btn small" ${mode === 'down' ? 'style="opacity:.45"' : ''}>Request access</span>&nbsp;` : ''}${mode === 'open' ? '<span class="btn small">Sign in or sign up</span>' : ''}</div>`;

// ---------- A: a long page in sections ----------
function landingA(p, mode, o = {}) {
  const hero = `<div class="sect"><h1>A tutor that teaches one topic until you can prove you know it. ${NS}</h1>
    <p class="sub" style="font-size:15px">Type a topic. Crux narrows it, teaches it step by step, then checks you with problems you haven't seen. ${NS}</p>${AGE18}
    ${mode === 'open' ? '' : `<div style="margin-top:14px;max-width:560px">${video()}</div>`}</div>`;
  const body = mode === 'open' ? `<div class="sect"><h2>What a session looks like ${NS}</h2>${EXAMPLE}<div class="row"><span class="btn primary">Sign in or sign up</span></div></div>`
    : `<div class="sect"><h2>Try it as a guest ${NS}</h2>${guestPart('A', mode, { phone: p })}</div>`;
  const req = reqAllowed(mode) ? `<div class="sect"><h2>Want your own files and saved sessions? ${NS}</h2><p class="sub">Ask for a trial link. ${REQLINE}</p><span class="btn primary" ${mode === 'down' ? 'style="opacity:.45"' : ''}>Request access</span></div>` : '';
  return ladderTop(mode) + `<div class="lp">${o.topBanner || ''}${hero}${body}${req}<div class="foot">${legal({ open: mode === 'open' })}</div></div>`;
}

// ---------- B: one screen led by the start box; the rest further down the page ----------
function landingB(p, mode, o = {}) {
  const left = `<h1>Learn one topic properly. ${NS}</h1><p class="sub" style="font-size:15px;margin-bottom:14px">Crux teaches it step by step, then checks you with problems you haven't seen. ${NS}</p>
    ${mode === 'open' ? EXAMPLE + '<div class="row"><span class="btn primary">Sign in or sign up</span></div>' : guestPart('B', mode, { ...o, ticks: o.ticks || [false, false] })}`;
  const right = `${video()}<div style="margin-top:10px">${AGE18}</div>`;
  const req = reqAllowed(mode) ? `<div class="sect" id="${o.req ? 'focus' : ''}"><h2>Request access ${NS}</h2>${o.req ? reqCard(o.req, true) : `<p class="sub">Your own trial link: saved sessions, your own files and photo answers. ${NS}</p><span class="btn primary">Request access</span>`}</div>` : '';
  const who = o.who ? `<div class="sect" id="focus">${whoCard()}</div>` : '';
  return ladderTop(mode) + `<div class="lp">${o.topBanner || ''}<div class="hero2 ${p ? 'ph' : ''}"><div class="l">${left}</div><div class="r">${right}</div></div>${req}${who}<div class="foot">${legal({ open: mode === 'open' })}</div></div>`;
}

// ---------- C: straight into the app as a guest ----------
function landingC(p, mode, o = {}) {
  const noGuest = ['eu', 'open'].includes(mode);
  const startArea = `<div class="home"><div class="wrap" style="max-width:600px">${o.topBanner || ''}
    <div style="max-width:420px;margin:0 auto 14px">${mode === 'open' ? '' : video()}</div>
    <div style="text-align:center;margin-bottom:12px">${AGE18}</div>
    ${mode === 'open' ? EXAMPLE + '<div class="row"><span class="btn primary">Sign in or sign up</span></div>' : guestPart('C', mode)}
    ${mode === 'open' || noGuest ? '' : `<div class="sub" style="margin-top:10px">Or pick a sample topic ${p ? 'from &#9776;' : 'on the left'}. ${NS}</div>`}
    <div class="sub" style="text-align:center;margin-top:18px">${legal({ open: mode === 'open' })}</div></div></div>`;
  const top = `<div class="topbar">${p && !noGuest ? '<span class="brand">&#9776;</span>' : ''}<span class="title">${noGuest ? 'Crux' : 'New guest session ' + NS}</span>${reqAllowed(mode) ? '<span class="btn small">Request access</span>' : ''}${mode === 'open' ? '<span class="btn small">Sign in or sign up</span>' : ''}</div>`;
  if (noGuest) return `<div style="display:flex;flex-direction:column;flex:1;min-height:0;position:relative">${top}${startArea}${o.overlay || ''}</div>`;
  return gapp(p, top + startArea, { noReq: !reqAllowed(mode), overlay: o.overlay, drawer: o.drawer });
}
const landing = (v, p, mode, o = {}) => v === 'A' ? landingA(p, mode, o) : v === 'B' ? landingB(p, mode, o) : landingC(p, mode, o);

// ---------- the entry ticks (guest and trial link) ----------
function ticksCard(o = {}) {
  return `<div class="h">${o.trial ? 'Welcome to your trial ' + NS : 'Before you start ' + NS}</div>${o.trial ? `<div class="infobox">${LINKNOTE}</div>` : `<div class="sub">${LIMIT}</div>`}
    ${ticks(o.t)}<span class="btn primary big" ${o.t && o.t[0] && o.t[1] ? '' : 'style="opacity:.45"'}>${o.trial ? 'Open Crux ' + NS : 'Start'}</span>
    ${o.again ? `<div class="sub" style="margin-top:8px">The Trial Terms changed on 2 Dec. <a>What changed</a> ${NS}</div>` : ''}`;
}
function ticksScene(v, p, o = {}) {
  if (o.trial) {
    if (v === 'A') return gatePage(ticksCard(o));
    if (v === 'B') return tapp(p, tstart(p, `<div class="sub" style="margin-top:6px"><b>${o.again ? 'The Trial Terms changed on 2 Dec. <a>What changed</a> ' + NS : 'Welcome to your trial. ' + NS}</b></div><div class="infobox">${LINKNOTE}</div>${ticks(o.t)}`, o.t && o.t[0] && o.t[1]), { empty: !o.again });
    return tapp(p, tstart(p), { empty: !o.again, overlay: dlg(ticksCard(o)) });
  }
  if (v === 'A') return gatePage(ticksCard(o));
  if (v === 'B') return landingB(p, 'trial', { ticks: o.t || [false, false] });
  return landingC(p, 'trial', { overlay: dlg(ticksCard(o)) });
}

// ---------- Request access ----------
function reqCard(state, inline) {
  if (state === 'done') return `<div class="h">Request received ${NS}</div><p>If you're approved, we'll email you a private link. Check your spam folder too. ${NS}</p><p class="sub">We keep your email only until we approve or decline your request, at most 30 days.</p>${inline ? '' : '<span class="btn big">Back to Crux ' + NS + '</span>'}`;
  return `${inline ? '' : `<div class="h">Request access ${NS}</div>`}<p class="sub" style="margin-top:0">${REQLINE}</p>
    <input class="field" value="${state === 'region' || state === 'filled' ? 'sam@example.com' : ''}" placeholder="Your email"><div class="turnstile"><span class="box"></span>Verify you are human<span class="cf">CLOUDFLARE<br>Turnstile</span></div>
    <div class="tick">${tb(state !== 'form')}<span>I am 18 or over</span></div><span class="btn primary big">Send request ${NS}</span>
    ${state === 'region' ? `<div class="err">${REGION}</div>` : ''}`;
}
function reqScene(v, p, state) {
  if (v === 'A') return gatePage(reqCard(state));
  if (v === 'B') return landingB(p, 'trial', { req: state });
  return landingC(p, 'trial', { overlay: dlg(reqCard(state)) });
}

// ---------- Who runs Crux ----------
const whoCard = () => `<div class="h">Who runs Crux</div><p>Crux is built by [the owner's name], in the Philippines. ${NS}</p>
  <p>Questions about your data, or to have it deleted: <a>privacy@[the domain]</a><br>For anything else: <a>[the owner's LinkedIn]</a> ${NS}</p>
  <p class="sub">During the trial only (owner, 11 Nov). From opening, the officer's title, postal address and phone come back.</p>`;
function whoScene(v, p) {
  if (v === 'A') return gatePage(whoCard() + '<span class="btn big">Back</span>', true);
  if (v === 'B') return landingB(p, 'trial', { who: true });
  return landingC(p, 'trial', { overlay: dlg(whoCard() + '<span class="btn big">Close</span>') });
}

// ---------- Sign in during the trial (the #753 card, held fixed; what a non-owner sees is a rule question) ----------
const signinTrial = () => gatePage(`<div class="h">Sign in or sign up</div><span class="btn big">Continue with Google</span><div class="or">or</div>
  <input class="field" value="sam@example.com"><span class="btn primary big">Email me a code</span>
  <div class="err">Sign-up isn't open yet. To try Crux, use guest mode or ask for a trial link. ${NS} <a>Request access</a></div>`);
