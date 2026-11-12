// PROTOTYPE, throwaway (calmxz/Crux#755). Part of 755-owner.html. Content blocks, part 2: feedback, counts,
// money, switches; then the session readers and the dialogs.

// ---------- Feedback ----------
function bFb() {
  const rows = D.feedback.map(f => R(`${f.unread ? '<span class="dot"></span>' : ''}<span class="sub">${f.when} &middot; ${f.from} &middot; Helped: ${f.helped} &middot; Would pay: ${f.pay}</span>
    <div style="margin:3px 0;white-space:pre-wrap">${f.text}</div>
    <div class="sub">${f.quote ? 'May be quoted' : 'Not for quoting'}${f.email ? ` &middot; You can email: ${f.email}` : ''}${f.published ? ` &middot; <b>Published:</b> ${f.published}` : ''}</div>`,
    f.quote && !f.published ? btn('Mark published&hellip;') : '')).join('');
  return BLK('fb', `Feedback <span class="badge wait">2 unread</span>`, rows + '<div class="sub" style="margin-top:6px">Anonymous unless the learner ticked "You can email me about this". Shown as plain text.</div>');
}
function bQuotes() {
  return BLK('quotes', 'Withdrawn quotes to remove', R('<b>"Too slow to start in the morning. Took almost a minute."</b><div class="sub">Published on: LinkedIn post, 9 Nov &middot; withdrawn 12 Nov &middot; remove by <b>26 Nov</b></div>', btn('Mark removed', 'primary')));
}
function bShares() {
  return BLK('shares', 'Shared sessions', R('<b>Personal essay</b> <span class="sub">&middot; shared up to 8 Nov</span><div class="sub">From a feedback answer. Later messages stay closed.</div>', btn('Read', 'primary'))
    + R('<b>All my sessions</b> <span class="sub">&middot; 3 sessions, shared up to 2 Nov</span>', btn('Read', 'primary')));
}

// ---------- Counts ----------
function bPath() {
  const t = isTrial(), w = X.st.window;
  const win = t ? `<div class="row"><span class="btn small greyed">Start the window</span><span class="sub">Works once sign-up is open. Nothing in the trial counts.</span></div>`
    : w === 'today' ? `<div class="infobox">Window started today, 11 Mar. Day 1 of 56. <span class="link">Undo (today only)</span></div>`
    : w === 'none' ? `<div class="row">${btn('Start the window', 'primary')}<span class="sub">Press it on the day of the first public post. No past date; the start can't be changed later.</span></div>`
    : `<div class="sub">Window: day 23 of 56 &middot; started 17 Feb &middot; judged at the end of 13 Apr</div>`;
  const bar = BAR.map(b => `<div class="money"><span style="width:220px">${t ? 0 : b[1]} / ${b[2]} ${b[0]}</span>${meter(t ? 0 : b[1], b[2])}</div>`).join('');
  const path = `<table class="tbl"><tr><th>The path</th><th>Learners</th></tr>${PATH.map(p => `<tr><td>${p[0]}</td><td>${t ? '&ndash;' : p[1]}</td></tr>`).join('')}</table>`;
  return BLK('path', 'The go-public bar', win + `<h3>Go needs all three inside the window</h3>${bar}<div class="sub">${t ? '' : 'Limit hit on 2 of 56 days'}</div><h3>The path</h3>${path}`);
}
function bArrivals() {
  return BLK('arrivals', 'Arrivals by source', `<table class="tbl"><tr><th>Source</th><th>Today</th><th>Last 7 days</th><th>Since the first post</th></tr>${D.arrivals.map(a => `<tr><td>${a[0]}</td><td>${a[1]}</td><td>${a[2]}</td><td>${a[3]}</td></tr>`).join('')}</table>`);
}
function bTurned() {
  const t = isTrial();
  const k = (n, l) => `<div class="k"><div class="n">${n}</div><div class="l">${l}</div></div>`;
  return BLK('turned', 'Other counts', `<div class="kv">${t ? k(3, 'Trial links turned away yesterday') + k(5, 'Guest mode stops yesterday')
    : k(4, 'Learners stopped by their own limit, yesterday') + k('30', 'Told Crux is full: 30, 12 ticked email') + k('2 of 56', 'Days the budget turned a learner away') + k(6, 'Code requests refused: the sender ran out')}
    ${k(2, 'Under-18 endings, dated: 4 Nov, 9 Nov')}</div>`);
}

// ---------- Money ----------
function bMoney() {
  const t = isTrial();
  return BLK('money', 'Money', `<div class="money"><span style="width:200px">This month: ${usd(3.1)} of ${usd(8)}</span>${meter(3.1, 8)}<span class="sub">${usd(4.9)} left</span></div>
    <div class="money"><span style="width:200px">Today: ${usd(0.42)} of ${usd(2)}</span>${meter(0.42, 2)}<span class="sub">the ceiling</span></div>
    ${t ? `<div class="money"><span style="width:200px">Guest mode today: ${usd(0.09)} of ${usd(0.25)}</span>${meter(0.09, 0.25)}<span class="sub">month ${usd(0.8)} of ${usd(2)}</span></div>` : ''}
    <div class="money"><span style="width:200px">Your share: ${usd(1.2)} of ${usd(3)}</span>${meter(1.2, 3)}${btn('Raise&hellip;')}</div>
    <div class="money"><span style="width:200px">Distress check's pot today</span><span class="sub">${usd(0.01)} of ${usd(0.05)}</span></div>
    <h3>Crux's count beside Google's bill</h3><table class="tbl"><tr><th>Day</th><th>Crux</th><th>Google billed</th><th>Gap</th></tr><tr><td>${t ? '15 Nov' : '10 Mar'}</td><td>${usd(0.38)}</td><td>${usd(0.39)}</td><td>3%</td></tr></table>
    <div class="sub">Crux cannot read the credits left. Check them in Google Cloud. ${NS}</div>`);
}
function bSettings() {
  const t = isTrial();
  const f = (l, v, s = '') => R(`${l}<div class="sub">${s}</div>`, `<input class="field" style="width:110px;margin:0" value="${v}">`);
  return BLK('settings', 'Limits you can change', f('The daily ceiling', 'USD 2.00', 'No calendar day spends more, apart from a started check')
    + f('Each learner\'s tutoring limit: a day', '2 sittings\' worth', 'A sitting\'s worth is about USD 0.045') + f('Each learner\'s tutoring limit: a week', '4 sittings\' worth')
    + (t ? '' : f('The learner cap', '25', 'Every account ever made counts'))
    + f('Guest mode: a day', 'USD 0.25') + f('Guest mode: a month', 'USD 2.00')
    + f('Your share', 'USD 3.00', 'Re-marks and the distress check spend from it') + f('The distress check\'s pot', 'USD 0.05 a day')
    + `<div class="row">${btn('Save', 'primary')}<span class="sub">Before any raise in the money, raise Google's cap first.</span></div>`);
}
function bCap() {
  if (isTrial()) return '';
  return BLK('cap', 'The learner cap and the let-in list', `<div class="infobox"><b>Learner cap full (25 of 25). Raise it before you re-share.</b> &middot; 25 + 2 let in</div>`
    + R('ben.ocampo@example.com<div class="sub">Added 9 Mar &middot; erased at sign-up or on 16 Mar</div>', `<label class="sub">${tb(false)} Keep until I remove it</label>` + btn('Remove'))
    + R('lea.santos@example.com<div class="sub">Added 2 Mar &middot; kept until you remove it, or sign-up</div><div class="sub" style="color:#8a1c1c">This email was blocked for misuse. It starts a new, empty account.</div>', `<label class="sub">${tb(true)} Keep until I remove it</label>` + btn('Remove'))
    + `<div class="row"><input class="field" style="flex:1;margin:0" placeholder="Email to let in">${btn('Add', 'primary')}</div>`);
}

// ---------- Switches ----------
function bSwitches() {
  const rm = X.st.remark;
  return BLK('switches', 'Switches', PARTS.map(p => R(`<b>${p[0]}</b>${!partOn(p[1]) ? ' <span class="badge hold">Off</span>' : ''}`, `${sw(partOn(p[1]))}`)).join('')
    + (rm ? `<div class="infobox"><b>Re-marking after a marking fault:</b> 41 of 120 marks done ${meter(41, 120)}Checks stay off until the re-marks finish. ${btn('Switch checks back on')} <span class="sub">(after the re-marks)</span> ${NS}</div>` : '')
    + '<div class="sub" style="margin-top:6px">They apply to your own account on live too. Learners see what is paused.</div>');
}

const ALLB = { needs:bNeeds, reqs:bReqs, links:bLinks, dead:bDead, notice:bNotice, endtrial:bEndTrial, flags:bFlags, closures:bClosures,
  entered:bEntered, reported:bReported, fb:bFb, quotes:bQuotes, shares:bShares, path:bPath, arrivals:bArrivals, turned:bTurned,
  money:bMoney, settings:bSettings, cap:bCap, switches:bSwitches };

// ---------- Readers: a flagged session (chat text only, up to the flag) and a shared one (up to the tick) ----------
function reader(kind) {
  const flag = kind === 'flag';
  const head = flag ? `<b>Flag ${isTrial() ? '4812 &middot; Link 12' : '4821 &middot; an account'}</b> &middot; session 1 of ${isTrial() ? 1 : 2} &middot; chat text only, up to the flag`
    : '<b>Shared: Personal essay</b> &middot; up to the tick, 8 Nov';
  const th = flag ? `<div class="msg me">What do I need to know about solubility for my chem quiz?</div>
    <div class="msg tutor"><div class="who">Tutor</div>Let's start with what "soluble" means. Which dissolves faster in warm water: sugar or sand?</div>
    <div class="msg me">ok but how would i make [a controlled drug] at home</div>
    <div class="msg tutor declined"><div class="who">Tutor &middot; declined: making drugs or other illegal goods</div>I can't help with making that. We can keep going with solubility, though.</div>
    <div class="sysline">[a file was here: files are never shown on a flag] ${NS}</div>
    <div class="cutline">The flag, 15 Nov. Nothing after this is shown, apart from new declines while the flag waits.</div>`
    : `<div class="msg me">Help me write a thesis statement for my personal essay.</div><div class="msg tutor"><div class="who">Tutor</div>What is the one thing you want the reader to believe about you by the end?</div>
    <div class="cutline">Shared up to here, 8 Nov. Later messages stay closed.</div>`;
  const acts = flag ? (isTrial() ? btn('Dismiss') + btn('Switch the link off', 'red') : btn('Warn') + btn('Dismiss')) : '';
  return `<div class="reader"><div class="readhead"><span class="link">&#8249; Back</span> &nbsp; ${head}<div class="row">${acts}</div></div><div class="thread">${th}</div></div>`;
}

// ---------- Dialogs ----------
const DLG = {
  reason: () => `<h2>Switch off Link 9?</h2><div class="sub">Its sessions, files and photos are erased. The holder's ended page shows your reason. The person may request again.</div><input class="field" placeholder="Reason the holder sees" value="Used on more than 3 browsers."><div class="row">${btn('Switch off', 'red')}${btn('Cancel')}</div>`,
  end: () => `<h2>End the trial</h2><div class="sub">At least 7 days ahead. Link holders see this date. On it: every link dies, waiting requests are declined, Request access goes. Guest mode stays.</div><input class="field" value="30 Nov"><div class="sub">Earliest: 23 Nov</div><div class="row">${btn('Set the date', 'red')}${btn('Cancel')}</div>`,
  raise: () => `<h2>Raise your share</h2><div class="infobox"><b>Raise Google's cap first.</b> The Crux project's cap is about USD 11.50: the learners' USD 8, your USD 3 and a margin. ${NS}</div><input class="field" value="USD 4.00"><label class="tick">${tb(true)} I raised Google's cap ${NS}</label><div class="row">${btn('Raise', 'primary')}${btn('Cancel')}</div>`,
  enter: () => `<h2>Enter a request from the Crux email</h2><div class="sub">For requests Crux cannot know about otherwise.</div><div class="radios">${['A copy of their data', 'A contest of a misuse closure', 'Delete a session during a closing', 'Delete the account'].map((r, i) => `<label class="tick">${tb(i === 0)} ${r}</label>`).join('')}</div><input class="field" placeholder="The learner's email"><div class="row">${btn('Enter', 'primary')}${btn('Cancel')}</div>${NS}`,
  warn: () => `<h2>Warn: flag 4821</h2><div class="sub">Crux emails the learner. The count goes back to 0 and the warning stays on record.</div><div class="infobox">"This breaks Crux's terms. Another time closes your account."</div><div class="row">${btn('Send the warning', 'primary')}${btn('Cancel')}</div>`,
  dismiss: () => `<h2>Dismiss: flag ${isTrial() ? '4812' : '4821'}</h2><div class="infobox">${isTrial() ? 'The holder sees this as a notice at their next visit:' : 'Crux emails the learner:'} "The tutor declined 3 of your requests (making drugs or other illegal goods, methods of self-harm), so the owner read those sessions on Saturday. No action was taken."</div><div class="row">${btn('Dismiss', 'primary')}${btn('Cancel')}</div>`,
  report: () => `<h2>Mark flag ${isTrial() ? '4844' : '4835'} "Reported"</h2><div class="sub">It stays sealed past the usual erasure, until the authorities say what to do. At that erasure it moves to the reported hold, ${isTrial() ? 'and a link has no email' : 'and you can see the account\'s email, so a report can name it'}.</div><div class="row">${btn('Mark "Reported"', 'red')}${btn('Cancel')}</div>`,
  publish: () => `<h2>Mark as published</h2><div class="sub">Where did you publish it?</div><input class="field" value="LinkedIn post, 12 Nov"><div class="row">${btn('Mark published', 'primary')}${btn('Cancel')}</div>`,
  partoff: () => `<h2>Switch off the mastery check?</h2><div class="sub">Checks under way pause as half-done. Learners see: "Checks are paused while we fix something; your progress is kept"</div><div class="row">${btn('Switch off', 'red')}${btn('Cancel')}</div>${NS}`,
  close: () => `<h2>Close the account: flag 4802</h2><div class="sub">The account locks for 7 days, then is erased on day 8. Crux emails the reason, the date, and that replying before then contests it.</div><div class="row">${btn('Close the account', 'red')}${btn('Cancel')}</div>`,
};
