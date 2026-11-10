// PROTOTYPE, throwaway (calmxz/Crux#753). Part of 753-account.html; see that file's header.
// ---------- settings ----------
function settingsSecs(st) {
  const fb = `<div class="fbrow"><b>8 Nov</b> <span class="sub">Helped: yes &middot; Would pay: maybe</span><div style="margin-top:4px">"More worked examples on graphs, please."</div>
      <div class="tick">${tb(true)}<span>Crux may quote this, without my name</span></div>
      <div class="tick">${tb(true)}<span>Share: Personal essay <span class="sub">(the owner can read it up to 8 Nov)</span> ${NS}</span></div>
      <div class="sub">You said Crux may email you about this. ${NS}</div></div>
    <div class="fbrow"><b>2 Nov</b> <span class="sub">Helped: somewhat &middot; Would pay: no</span><div class="sub" style="margin-top:4px">Not quoted, not shared. ${NS}</div></div>`;
  const close = st.locked ? `<span class="btn" style="opacity:.45">Close account</span><div class="sub">A locked account can't be closed. ${NS}</div>` : `<span class="btn danger">Close account</span>`;
  return {
    tutoring: ['Tutoring', `<div>Today's tutoring: 70% used</div><div class="meter"><i style="width:70%"></i></div><div class="sub">This week: 45% used ${NS}</div>`],
    files: ['Files', `<div>Your files: 186 of 200 MB ${NS}</div><div class="meter"><i style="width:93%"></i></div><span class="btn small">See your files</span> <span class="sub">opens the allowance list from #752, without "wasn't added"</span>`],
    feedback: ['Your feedback', `<div class="sub">Untick to withdraw a quote or end a share. ${NS}</div>${fb}`],
    account: ['Account', `<div>${st.trial ? 'Trial link' : EMAIL}</div><div class="row">${st.trial ? '' : close}</div>
      <div class="legal" style="text-align:left"><a>Terms</a> &middot; <a>Privacy Policy</a> &middot; <a>Who runs Crux</a></div><div class="row">${st.hl ? '<span class="btn" style="outline:3px solid #ecc77d">Sign out</span>' : '<span class="btn">Sign out</span>'}</div>`],
  };
}
const secHtml = ([t, h], id) => `<div class="setsec" id="s-${id}"><div class="h">${t}</div>${h}</div>`;
function settings(v, phone, st = {}) {
  const S = settingsSecs(st), tab = st.tab || 'tutoring', keys = Object.keys(S);
  if (v === 'A') {
    const order = st.tab === 'feedback' ? ['feedback', 'account', 'tutoring', 'files'] : st.tab === 'account' ? ['account', 'tutoring', 'files', 'feedback'] : keys;
    const lockB = st.locked ? `<div class="banner stop" style="border-radius:8px;margin-bottom:8px">Your account is locked. <a class="alink">Why?</a> ${NS}</div>` : '';
    const note = st.tab && st.tab !== 'tutoring' ? `<div class="sub">(scrolled to ${S[st.tab][0]})</div>` : '';
    return shell(v, phone, pageMain(v, phone, 'Settings', lockB + note + order.map(k => secHtml(S[k], k)).join('')), { on: 'settings', drawer: st.drawer, overlay: st.over });
  }
  if (v === 'B') {
    const tabs = keys.map(k => `<div class="${k === tab ? 'on' : ''}">${S[k][0]}</div>`).join('');
    const body = `<div style="flex:1;padding:16px;overflow-y:auto"><div style="display:flex;justify-content:space-between"><b>Settings</b><span style="color:var(--mute)">&times;</span></div>${st.locked ? `<div class="errbox">Your account is locked. ${NS}</div>` : ''}${secHtml(S[tab], tab)}</div>`;
    const card = phone ? `<div style="display:flex;flex-direction:column;width:100%"><div class="tabs" style="margin:10px;flex-wrap:wrap">${keys.map(k => `<span class="${k === tab ? 'on' : ''}">${S[k][0]}</span>`).join('')}</div>${body}</div>` : `<div class="tabsv">${tabs}</div>${body}`;
    return shell(v, phone, `<div class="dim" style="flex:1;display:flex;flex-direction:column">${sessionMain(v, phone)}</div>`, { overlay: dlg(card, true) + (st.over || '') });
  }
  return settingsArea(phone, tab, secHtml(S[tab], tab) + (st.locked ? `<div class="errbox">Your account is locked. ${NS}</div>` : ''), st);
}
function settingsArea(phone, on, content, st = {}) {
  const items = [['tutoring', 'Tutoring'], ['files', 'Files'], ['feedback', 'Your feedback'], ['send', 'Send feedback'], ['account', 'Account']];
  const nav = `<div class="setnav"><div class="topbar"><span class="brand">Crux</span></div><div class="it" style="color:var(--me)">&larr; Back to learning</div><div class="sec" style="font-size:11px;text-transform:uppercase;color:var(--mute);padding:12px 16px 4px">${st.trial ? 'Trial link' : EMAIL}</div>
    ${items.map(([k, t]) => `<div class="it ${k === on ? 'on' : ''}">${t}</div>`).join('')}</div>`;
  const label = (items.find(i => i[0] === on) || [0, ''])[1];
  if (phone) return `<div class="topbar"><span class="link">&larr; Settings</span><span class="title">${label}</span></div><div class="home"><div class="wrap">${content}</div></div>`;
  return `<div style="display:flex;flex:1;min-height:0">${nav}<div style="flex:1;display:flex;flex-direction:column;min-width:0"><div class="topbar"><span class="title">${label}</span></div><div class="home"><div class="wrap" style="max-width:600px">${content}</div></div></div></div>`;
}
function signoutScene(v, phone) {
  if (v === 'A') return settings(v, phone, { tab: 'account', hl: true });
  if (v === 'B') return shell(v, phone, sessionMain(v, phone), { pop: `<div class="menupop" style="top:46px;right:12px"><div class="sub" style="cursor:default">${EMAIL}</div><div>Settings</div><div>Sign out</div></div>` });
  return shell(v, phone, sessionMain(v, phone), { acct: true, drawer: phone, pop: `<div class="menupop" style="bottom:20px;left:${phone ? 150 : 200}px"><div>Settings</div><div>Feedback</div><div>Sign out</div></div>` });
}

// ---------- the feedback page ----------
function fbParts(st) {
  const r = (opts, on) => `<div class="radios">${opts.map(o => `<span class="${o === on ? 'on' : ''}">${o}</span>`).join('')}</div>`;
  const shareList = st.listOpen ? `<div class="menupop" style="position:static;margin-top:4px;box-shadow:none"><div style="background:#eef2ff">Implicit differentiation (MATH101 week 7)</div><div>Chain rule (MATH101 week 6)</div><div>Personal essay</div><div>Cell respiration (BIO110)</div><div style="border-top:1px solid var(--line)">all my sessions</div></div>` : '';
  const share = st.nosess ? '' : `<div class="tick">${tb(st.share)}<span>Share: <span class="btn small">Implicit differentiation (MATH101 week 7) &#9662;</span>${shareList}${st.share ? `<div class="errbox" style="background:var(--warn);color:#5c3a00">This shares everything you wrote, including anything personal</div>` : ''}</span></div>`;
  return {
    q12: `<div class="q">Did Crux help you understand your topic? <span class="sub">(required)</span></div>${r(['yes', 'somewhat', 'no'], st.filled ? 'yes' : '')}
      <div class="q">Would you pay for Crux? <span class="sub">(required)</span></div>${r(['yes', 'maybe', 'no'], st.filled ? 'maybe' : '')}`,
    q34: `<div class="q">What would make Crux better for you?</div><textarea class="ta">${st.filled ? 'More worked examples on graphs, please.' : ''}</textarea><div class="count">${st.filled ? 39 : 0} / 2,000</div>
      <div class="q">Anything else?</div><textarea class="ta"></textarea><div class="count">0 / 2,000</div>`,
    ticks: `<div style="margin-top:14px"><div class="tick">${tb(false)}<span>Crux may quote this, without my name</span></div>${st.trial ? '' : `<div class="tick">${tb(false)}<span>You can email me about this</span></div>`}${share}</div>`,
    send: `${st.toomany ? `<div class="errbox">You've sent a lot of feedback today. Please try again tomorrow.</div>` : ''}<div class="row" style="justify-content:flex-end"><span class="btn primary" ${st.toomany ? 'style="opacity:.45"' : ''}>Send</span></div>`,
  };
}
const SENT = `<div class="h">Thanks, your feedback was sent. ${NS}</div><div class="row"><span class="btn">Back to learning ${NS}</span></div>`;
const FBLOCK = `<div class="errbox">Your account is locked, so you can't send feedback. You can still untick a quote or a share in Settings, under Your feedback. ${NS}</div>`;
function feedback(v, phone, st = {}) {
  const P = fbParts(st), all = P.q12 + P.q34 + P.ticks + P.send;
  const body = st.sent ? SENT : st.locked ? FBLOCK : all;
  if (v === 'A') return shell(v, phone, pageMain(v, phone, 'Feedback', `<div class="h">Feedback</div>${body}`, { trial: st.trial }), { on: 'feedback', trial: st.trial });
  if (v === 'B') {
    if (st.sent) return shell(v, phone, sessionMain(v, phone) + `<div class="toast" style="bottom:70px">Thanks, your feedback was sent. ${NS}</div>`);
    const panel = `<div class="fbpanel"><div style="display:flex;justify-content:space-between"><b>Feedback</b><span style="color:var(--mute)">Close</span></div>${body}</div>`;
    if (phone) return `<div style="flex:1;display:flex;flex-direction:column;min-height:0"><div class="topbar"><span class="title">Feedback</span><span class="link">Close</span></div><div class="home">${body}</div></div>`;
    return shell(v, phone, sessionMain(v, phone, { panel, trial: st.trial }), { trial: st.trial });
  }
  const step = st.step || 1, steps = `<div class="steps">${[1, 2, 3].map(i => `<span class="${i <= step ? 'on' : ''}"></span>`).join('')}</div><div class="sub">Step ${step} of 3 ${NS}</div>`;
  const parts = { 1: P.q12 + '<div class="row" style="justify-content:flex-end"><span class="btn primary">Next</span></div>', 2: P.q34 + '<div class="row" style="justify-content:flex-end"><span class="btn">Back</span><span class="btn primary">Next</span></div>', 3: P.ticks + P.send };
  return settingsArea(phone, 'send', st.sent ? SENT : st.locked ? FBLOCK : steps + parts[step], st);
}

// ---------- closing an account ----------
function closeCard(st, inline) {
  const copy = st.copy ? `<div class="infobox">&#10003; We'll email ${EMAIL} a copy on 10 Nov, as a private link that works for 7 days. ${NS}</div>` : '<span class="btn">Send me a copy first</span>';
  return `<div class="h">Close your account? ${NS}</div><p style="font-size:14px">This erases your 4 sessions, your files, and your record of 3 mastered topics on 10 Nov. Until then, open Crux and choose Keep my account to stop it. ${NS}</p>
    <div class="row" style="${inline ? '' : 'flex-direction:column'}">${copy}<span class="btn red">Close account</span><span class="btn">Cancel</span></div>`;
}
function closing(v, phone, st = {}) {
  if (v === 'A') return settings(v, phone, { tab: 'account', over: dlg(closeCard(st) + `<div class="sub" style="margin-top:8px">Type <b>delete</b> to confirm</div><input class="field" placeholder="delete">`) });
  if (v === 'B') return settings(v, phone, { tab: 'account', over: dlg(closeCard(st)) });
  const S = settingsSecs({});
  return settingsArea(phone, 'account', `<div class="setsec"><div class="h">Account</div><div>${EMAIL}</div><div class="row"><span class="btn">Sign out</span></div>
    <div class="card" style="border-color:#e8b4b4;margin-top:12px">${closeCard(st, true)}</div></div>`);
}
function closedScene(v, phone) {
  const note = `Your account closes on 10 Nov. We've emailed you. Sign in before then to keep it. ${NS}`;
  if (v === 'A') return gatePage(`<div class="infobox">${note}</div>` + signinCard({ step: 'start' }, 'inline'));
  if (v === 'B') return opening('B', phone, 'keep');
  return `<div class="banner info">${note}</div>` + landing();
}

// ---------- emails ----------
function mail(subject, body) {
  return `<div class="mail"><div class="env"><div class="hd"><b>From:</b> Crux &middot; <b>To:</b> ${EMAIL}<br><b>Subject:</b> ${subject}</div><div class="bd">${body}</div></div></div>`;
}
const MAILS = {
  close: v => mail(`Your Crux account closes on 10 Nov ${NS}`, `<p>Your Crux account closes on 3 Nov. Sign in to keep it.</p><p class="sub">(The spec's example says 3 Nov; the scenes here use 10 Nov.)</p>${v === 'B' ? '<p><a class="alink2">https://crux.example/sign-in</a></p>' : '<span class="btn primary">Sign in to Crux ' + NS + '</span>'}`),
  copy: v => mail(`Your copy of your Crux data ${NS}`, `<p>Here is the copy of your Crux data you asked for. Your account and everything else has been erased. ${NS}</p>
    ${v === 'B' ? '<p><a class="alink2">https://storage.googleapis.com/crux-copies/...signed-link</a></p>' : '<span class="btn primary">Download your copy (zip) ' + NS + '</span>'}
    <p style="font-size:14px">This link works until 17 Nov. Keep it private: anyone with the link can open your data. ${NS}</p><p class="sub">A missed link can't be made again. ${NS}</p>`),
};

