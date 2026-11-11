// PROTOTYPE, throwaway (calmxz/Crux#754). Part of 754-landing.html; see that file's header.
// Trial links: how an ended link and a notice show. A: a plain page with one card (the #753 opening page).
// B: the public landing page with a banner (ended), or a banner across the app (notices). C: a dialog.
const ENDS = {
  off:     { h:'This trial link was switched off ' + NS, b:'Crux\'s owner switched it off: it was used on more than 3 browsers. ' + NS + ' Its sessions have been erased.', req:true },
  misuse:  { h:'This trial link was switched off ' + NS, b:'The tutor declined 3 of your requests (making drugs or other illegal goods), and the owner read those sessions. The owner switched this link off, and its sessions have been erased. ' + NS, req:true },
  yes:     { h:'Your trial has ended ' + NS, b:'Crux is for people 18 and over, so this trial link has been switched off and its sessions have been erased. ' + NS, ok:true },
  yeslate: { h:'This trial link has ended ' + NS, b:'It no longer works. ' + NS, ok:true },
  ended:   { h:'The trial has ended', b:'Thanks for trying Crux. You can still try it as a guest. ' + NS, guest:true },
  unknown: { h:'This link doesn\'t work ' + NS, b:'Open the whole link from your invite email. If it still doesn\'t work, you can request access again. ' + NS, req:true },
  network: { h:'Too many wrong links ' + NS, b:'Your network tried too many links that don\'t work. Try again in an hour. ' + NS },
};
function endCard(k, inBanner) {
  const e = ENDS[k];
  const btn = e.req ? '<span class="btn primary small">Request access</span>' : e.guest ? '<span class="btn primary small">Try it as a guest</span>' : e.ok ? '<span class="btn small">OK</span>' : '';
  if (inBanner) return `<b>${e.h}.</b> ${e.b} ${btn}`;
  return `<div class="h">${e.h}</div><p>${e.b}</p>${btn.replace('small', 'big')}`;
}
function endScene(v, p, k) {
  const mode = k === 'ended' ? 'post' : 'trial';
  if (v === 'A') return gatePage(endCard(k));
  if (v === 'B') return landingB(p, mode, { topBanner: banner('stop', endCard(k, true), false) });
  return landingC(p, mode, { overlay: dlg(endCard(k)) });
}
const lockedLink = () => gatePage(`<div class="h">Your trial link is locked ${NS}</div><p>One of your sessions was sealed, and your trial link is locked while Crux's owner decides. Nobody can open the sealed session, including Crux's owner. To reply, email Crux at its address and quote flag 4821.</p><p class="sub">You can still read your other sessions. The tutor can't reply.</p><span class="btn primary big">Read my sessions</span><div class="sub" style="margin-top:8px">No Sign out: a trial link has none. ${NS}</div>`);

// ---------- notices at the holder's next visit ----------
const NOTES = {
  device:  { h:'You\'re in ' + NS, b:DEVNOTE },
  ending:  { h:'The trial ends on 15 Jan ' + NS, b:'After that, this link stops working and everything in it is erased. Until then, you can untick a quote or a share in Settings, under Your feedback. ' + NS },
  breach:  { h:'A data breach ' + NS, b:'[what happened, what it touched and what Crux did: written at the time] ' + NS },
  dismiss: { h:'Crux\'s owner read some of your sessions ' + NS, b:'The tutor declined 3 of your requests (making drugs or other illegal goods, methods of self-harm), so the owner read those sessions on Saturday. No action was taken.' },
};
function noteScene(v, p, k) {
  const n = NOTES[k], main = k === 'device' ? tstart(p) : tsession(p);
  const o = k === 'device' ? { empty: true } : {};
  if (v === 'A') return gatePage(`<div class="h">${n.h}</div><p>${n.b}</p><span class="btn primary big">Continue</span>`);
  if (v === 'B') return tapp(p, main, { ...o, appBanner: banner(k === 'breach' || k === 'dismiss' ? 'warn' : 'info', `<b>${n.h}.</b> ${n.b}`) });
  return tapp(p, main, { ...o, overlay: dlg(`<div class="h">${n.h}</div><p>${n.b}</p><span class="btn primary big">OK</span>`) });
}

// ---------- the trial link's app and Settings (held fixed from #753: no Account part) ----------
const tappScene = (v, p) => tapp(p, tsession(p));
const tsettings = (v, p) => tapp(p, `<div class="topbar">${p ? '<span class="brand">&#9776;</span>' : ''}<span class="title">Settings</span></div><div class="home"><div class="wrap" style="max-width:640px">
  <div class="setsec"><div class="h">Tutoring</div><div class="fbrow">Shorter explanations <span class="link">Remove</span></div></div>
  <div class="setsec"><div class="h">Files</div><div class="meter"><i style="width:93%"></i></div><div class="sub">186 of 200 MB &middot; <a class="alink2">See your files</a></div></div>
  <div class="setsec"><div class="h">Your feedback</div><div class="fbrow">"The check was fair and hard." &middot; Quote allowed <span class="link">Untick</span></div></div>
  <div class="setsec"><div class="sub"><a class="alink2">Trial Terms</a> &middot; <a class="alink2">Trial Privacy Notice</a> &middot; <a class="alink2">Who runs Crux</a></div></div></div></div>`, { on: 'settings' });

// ---------- emails ----------
const mail = (subj, body) => `<div class="mail"><div class="env"><div class="hd">From: Crux &lt;hello@[the domain]&gt; ${NS}<br>To: sam@example.com<br>Subject: ${subj} ${NS}</div><div class="bd">${body}</div></div></div>`;
const MAILS = {
  invite: () => mail('Your Crux trial link', '<p>You\'re in. Tap to start: <span class="btn primary small">Open Crux</span></p><p>Using another device? Open this email there and tap the same link. Keep this email: it\'s your only way back in. Trial places are limited, so a lost link may not be replaced.</p>'),
  decline: () => mail('About your Crux request', '<p>Thanks for asking about Crux. The trial is limited for now. If Crux opens to everyone, you\'ll be able to sign up then. Follow <a class="alink2">[the owner\'s LinkedIn]</a> to hear when it does.</p>'),
};
