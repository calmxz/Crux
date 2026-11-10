// PROTOTYPE, throwaway (calmxz/Crux#753). Part of 753-account.html; see that file's header.
// ---------- sign-in and "One more thing" ----------
const MSG = {
  inapp:       ['info', "Google sign-in doesn't work inside the LinkedIn app. Open this page in your browser, or use a code.", 'google'],
  senderday:   ['stop', "We can't send codes right now. Use Continue with Google, or try again tomorrow.", 'code'],
  sendermonth: ['stop', "We can't send codes right now. Use Continue with Google, or try again later.", 'code'],
  toomany:     ['stop', `<b>Too many codes today.</b> Use Continue with Google, or try again tomorrow. ${NS}`, 'code'],
  toomanyreq:  ['stop', `Too many code requests from this network. Try again in an hour, or use Continue with Google. ${NS}`, 'code'],
  region:      ['stop', "Crux isn't available in your region yet.", 'code'],
  codewrong:   ['stop', `That code isn't right. 3 tries left. ${NS}`, 'codefield'],
  codedead:    ['stop', `This code doesn't work any more. Send a new one. ${NS}`, 'codefield'],
};
function msgHtml(k, place) {
  const [kind, text] = MSG[k];
  if (place === 'inline') return `<div class="${kind === 'info' ? 'infobox' : 'err'}">${text}</div>`;
  if (place === 'box') return `<div class="${kind === 'info' ? 'infobox' : 'errbox'}">${text}</div>`;
  return '';
}
function signinCard(st, place) {
  const m = st.msg, at = m && MSG[m][2], here = w => (m && at === w ? msgHtml(m, place) : '');
  const banner = m && place === 'banner' ? `<div class="banner ${MSG[m][0] === 'info' ? 'info' : 'stop'}" style="margin:-12px -12px 10px;border-radius:12px 12px 0 0">${MSG[m][1]}</div>` : '';
  const top = place === 'box' && m ? msgHtml(m, 'box') : '';
  const legal = `<div class="legal"><a>Terms</a> &middot; <a>Privacy Policy</a> &middot; <a>Who runs Crux</a></div>`;
  if (st.step === 'code') return `${banner}<div class="h">Check your email</div><div class="sub">We sent a 6-digit code to ${EMAIL}. It works for 10 minutes. ${NS}</div>
    <div class="codeboxes">${(st.typed || '').padEnd(6).split('').map(c => `<span>${c.trim()}</span>`).join('')}</div>${place !== 'box' ? here('codefield') : ''}${top}
    <span class="btn primary big">Continue ${NS}</span><div class="legal"><a>Send a new code</a> &middot; <a>Use another email</a> ${NS}</div>`;
  if (st.step === 'onemore') return `${banner}<div class="h">One more thing</div>
    <div class="tick ${place === 'box' ? 'bigrow' : ''}">${tb(st.ticks[0])}<span>I am 18 or over</span></div>
    <div class="tick ${place === 'box' ? 'bigrow' : ''}">${tb(st.ticks[1])}<span>I agree to the <a>Terms</a>, and to Crux keeping my learning progress and what I share with the tutor, as the <a>Privacy Policy</a> explains</span></div>
    <span class="btn primary big" ${st.ticks[0] && st.ticks[1] ? '' : 'style="opacity:.45"'}>Start</span>`;
  if (st.step === 'full') return `${banner}<div class="h">One more thing</div><p>Crux is full for now. Try again later.</p>
    <div class="tick">${tb(st.ticked)}<span>Email me if spots open</span></div><span class="btn big">Done ${NS}</span>`;
  if (st.step === 'blocked') return `${banner}<div class="h">One more thing</div><p>This email can't be used to make a Crux account. ${NS}</p><span class="btn big">Back ${NS}</span>`;
  const turn = st.human ? `<div class="turnstile"><span class="box"></span>Verify you are human<span class="cf">Cloudflare<br>Privacy &middot; Terms</span></div>` : '';
  return `${banner}<div class="h" style="font-size:18px">Sign in or sign up ${NS}</div>${top}
    <span class="btn big">G&nbsp; Continue with Google</span>${place !== 'box' ? here('google') : ''}
    <div class="or">or</div><input class="field" placeholder="Your email" value="${st.email ? EMAIL : ''}">${turn}
    <span class="btn primary big">Email me a code</span>${place !== 'box' ? here('code') : ''}${legal}`;
}
function signin(v, phone, st) {
  if (v === 'A') return gatePage(signinCard(st, 'inline'));
  if (v === 'B') {
    if (st.step === 'onemore' || st.step === 'full' || st.step === 'blocked') return gatePage(signinCard(st, 'box'));
    const ex = `<div class="placeholder">The landing page's pre-written example sits beside the sign-in panel: a request, the tutor's narrowing questions and the objectives it proposes. Its content is laid out by the landing-page ticket.</div>`;
    if (phone) return `<div class="gatebar"><span class="brand">Crux</span></div><div style="flex:1;overflow-y:auto"><div style="padding:20px;background:#fff">${signinCard(st, 'box')}</div><div style="padding:14px"><details><summary>See an example ${NS}</summary>${ex}</details></div></div>`;
    return `<div class="gatebar"><span class="brand">Crux</span></div><div class="split"><div class="ex">${ex}</div><div class="pane">${signinCard(st, 'box')}</div></div>`;
  }
  return `<div style="position:relative;flex:1;display:flex;flex-direction:column">${landing()}${dlg('<div style="text-align:right;color:var(--mute)">&times;</div>' + signinCard(st, 'banner'))}</div>`;
}

// ---------- steps on opening, the lock, the under-18 closure ----------
const CARDS = {
  keep: v => `<div class="h">Your account closes on 10 Nov.</div><p style="font-size:14px">Everything in it is erased that day, unless you keep it. ${NS}</p>
    <span class="btn primary big">Keep my account</span><span class="btn big">Sign out</span>${v === 'A' ? `<div class="sub" style="text-align:center;margin-top:4px">It still closes on 10 Nov. You can come back and keep it until then.</div>` : ''}<span class="btn big">Send me a copy first</span>
    ${v === 'A' ? `<div class="legal"><a>Your feedback</a>: untick a quote or a share ${NS}</div>` : ''}`,
  terms: () => `<div class="h">Crux's terms changed</div><p style="font-size:14px">Crux's terms changed: <i>Crux now keeps your time zone with your account, to show reset times in your own clock.</i> <span class="nospec">[example change]</span></p>
    <div class="legal" style="text-align:left"><a>Read the new Terms</a> &middot; <a>What changed</a> ${NS}</div><div class="row" style="justify-content:flex-end"><span class="btn">Close my account</span><span class="btn primary">Agree</span></div>`,
  lockclose: v => `<div class="h">Your account is locked ${NS}</div><p style="font-size:14px">Crux's owner closed your account on 3 Nov. The tutor declined 3 of your requests (making drugs or other illegal goods), and the owner read those sessions. Your account will be erased on 10 Nov. To contest this, reply to the email we sent you before then; nothing is erased until the owner decides. ${NS}</p>
    <p class="sub">You can still read your sessions and what you've mastered. The tutor can't reply. ${NS}</p>${v !== 'C' ? '<span class="btn primary big">Read my sessions</span>' : ''}<span class="btn big">Sign out</span>`,
  lockseal: v => `<div class="h">Your account is locked ${NS}</div><p style="font-size:14px">One of your sessions was sealed, and your account is locked while Crux's owner decides. Nobody can open the sealed session, including Crux's owner. To reply, email Crux at its address and quote flag 4821. ${NS}</p>
    <p class="sub">You can still read your other sessions. The tutor can't reply. ${NS}</p>${v !== 'C' ? '<span class="btn primary big">Read my sessions</span>' : ''}<span class="btn big">Sign out</span>`,
  u18: () => `<div class="h">Your account is closed ${NS}</div><p style="font-size:14px">Crux is for people 18 and over, so your account and everything in it have been erased. ${NS}</p><span class="btn big">OK ${NS}</span>`,
};
function opening(v, phone, key, o = {}) {
  const card = CARDS[key](v);
  if (v === 'A') return gatePage(card);
  if (v === 'B') return shell(v, phone, `<div class="dim" style="flex:1;display:flex;flex-direction:column">${sessionMain(v, phone, { noFeedback: true })}</div>`, { overlay: dlg(card) });
  return shell(v, phone, topbar(v, phone, o.title || CURNAME) + `<div class="gate"><div class="card">${card}</div></div>`, o);
}
function lockedSession(v, phone, o = {}) {
  const line = `Your account is locked, so the tutor can't reply. <a class="alink">Why?</a> ${NS}`;
  if (v === 'A') return shell(v, phone, sessionMain(v, phone, { ...o, lock: line, bannerTop: `<div class="banner stop">Your account is locked. <a class="alink">Why?</a> ${NS}</div>` }), o);
  if (v === 'B') return shell(v, phone, sessionMain(v, phone, { ...o, lock: line, noFeedback: true }), { ...o, appBanner: `<div class="banner stop">Your account is locked. You can read your sessions; the tutor can't reply. <a class="alink">Why?</a> ${NS}</div>` });
  return shell(v, phone, sessionMain(v, phone, { ...o, lock: line }), o);
}

