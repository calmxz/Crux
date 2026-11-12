// PROTOTYPE, throwaway (calmxz/Crux#755). Part of 755-owner.html. Content blocks, part 1: needs you, trial, safety.
// Blocks are the owner page's parts; each variant decides where they sit. A block never sets the page layout.
const BLK = (id, title, inner, o = {}) => `<div class="blk ${X.focus === id ? 'focus' : ''}" ${X.focus === id ? 'id="focus"' : ''} data-b="${id}">
  <div style="display:flex;gap:8px;align-items:center;justify-content:space-between;flex-wrap:wrap"><h2 style="margin:0">${title}</h2>${o.right || ''}</div>${inner}</div>`;
const R = (main, acts = '', o = {}) => `<div class="orow" ${o.style ? `style="${o.style}"` : ''}><div class="main">${main}</div><div class="acts">${acts}</div></div>`;

// ---------- Needs you: what the owner must act on, in the daily email's order ----------
function needsItems() {
  const t = isTrial(), st = X.st;
  const it = [];
  if (st.urgent) it.push({ ic:'&#9888;', u:true, b:'flags', t:t ? 'Flag 4844: Link 7 locked at once. Sealed: anything sexual involving minors' : 'Flag 4835: an account locked at once. Sealed: anything sexual involving minors', s:'Pushed to your phone. You see only the date and the kind.' });
  if (t) it.push({ ic:'&#9993;', b:'reqs', t:'3 requests waiting', s:'Oldest: 16 days left' });
  it.push({ ic:'&#9873;', b:'flags', t:t ? 'Flag 4812 on Link 12: 3 declines in 7 days' : 'Flag 4821 on an account: 3 declines in 7 days', s:'Read the sessions, then decide' });
  if (t) it.push({ ic:'&#128187;', b:'links', t:'Link 9 is used on 4 browsers', s:'More than 3' });
  if (!t) it.push({ ic:'&#9201;', b:'closures', t:'1 closed account is erased tomorrow. Check the Crux inbox for a contest.', s:'Flag 4790, closed 10 Mar' });
  if (!t) it.push({ ic:'&#9654;', b:'cap', t:'Learner cap full (25 of 25). Raise it before you re-share.', s:'Told Crux is full: 30, 12 ticked email' });
  it.push({ ic:'&#128172;', b:'fb', t:'2 new feedback answers', s:'1 may be quoted' });
  it.push({ ic:'&#10006;', b:'quotes', t:'1 quote permission withdrawn', s:'Published on a LinkedIn post. Remove it by 26 Nov' });
  if (!t) it.push({ ic:'&#128230;', b:'entered', t:'A copy asked for by email, still to be sent', s:'Entered 1 Mar. Check the request is really the learner\'s, then run the script' });
  return it;
}
function bNeeds() {
  const it = needsItems();
  return BLK('needs', 'Needs you', it.map(i => `<div class="need ${i.u ? 'urgent' : ''}"><span class="ic">${i.ic}</span><div style="flex:1"><div>${i.t}</div><div class="sub">${i.s}</div></div><span class="link sub">Open &#8250;</span></div>`).join(''),
    { right:`<span class="sub">${TODAY()} ${NS}</span>` });
}

// ---------- Trial ----------
function bReqs() {
  if (!isTrial()) return '';
  const rows = D.reqs.map((r, i) => R(`<b>${r.email}</b><div class="sub">Asked ${r.when} &middot; ${r.left} days left ${NS}</div>${X.st.dupe && i === 2 ? '<div class="sub" style="color:#7a4b00">You are the duplicate check: Crux keeps no record of past requests.</div>' : ''}`,
    btn('Approve', 'primary') + btn('Decline'))).join('');
  return BLK('reqs', `Requests <span class="badge wait">${D.reqs.length} waiting</span>`, rows + `<div class="sub" style="margin-top:6px">A request not decided in 30 days is declined. Approving emails a private link and erases the email.</div>`);
}
function bLinks() {
  if (!isTrial()) return '';
  const rows = D.links.map(l => R(`<b>Link ${l.n}</b> ${NS} <span class="sub">&middot; made ${l.made}</span>${X.st.flaglink && l.n === 12 ? ' <span class="badge hold">Flag 4812</span>' : ''}`,
    `<span class="${l.br > 3 ? 'badge hold' : 'sub'}">${l.br} browser${l.br > 1 ? 's' : ''}${l.br > 3 ? ': more than 3' : ''}</span>` + btn('Switch off'))).join('');
  return BLK('links', `Trial links <span class="sub">${D.links.length} live</span>`, rows + '<div class="sub" style="margin-top:6px">You never see a link\'s key. Browsers are counted by random IDs.</div>');
}
function bDead() {
  if (!isTrial()) return '';
  return BLK('dead', 'Dead links', D.dead.map(d => R(`<b>Link ${d.n}</b> <span class="sub">&middot; ${d.when}</span><div class="sub">${d.why}</div>`)).join('') +
    '<div class="sub" style="margin-top:6px">Listed while their stubs last: until the trial ends, or 12 months after the link died. A link that died by a Yes keeps only "Ended".</div>');
}
function bNotice() {
  if (!isTrial()) return '';
  return BLK('notice', 'Notices to link holders', `<div class="sub">Shown once per link at the holder's next visit. A holder who does not visit cannot be reached.</div>${R('A data breach: a notice saying what happened ' + NS, btn('Write a notice'))}`);
}
function bEndTrial() {
  if (!isTrial()) return '';
  const set = X.st.ending;
  return BLK('endtrial', 'End the trial', set
    ? `<div class="infobox">The trial ends on <b>30 Nov</b>. Link holders see the date at their next visit. ${NS}</div><div class="sub">On that date every link dies, waiting requests are declined, and Request access goes. Guest mode stays.</div>`
    : `<div class="sub">Pick a date at least 7 days ahead. Link holders see it. The daily job ends the trial on that date, whether or not Crux will open.</div><div class="row">${btn('End the trial&hellip;', 'red')}</div>`);
}

// ---------- Safety ----------
const FLAGS_TRIAL = [
  { no:4812, home:'Link 12', what:'3 declines in 7 days', kinds:'making drugs or other illegal goods (2), methods of self-harm (1)', when:'15 Nov', rec:'No warning for a link: there is no email', acts:['Read 1 session', 'Dismiss', 'Switch the link off'] },
  { no:4844, home:'Link 7', sealed:true, urgent:true, what:'Sealed: anything sexual involving minors', when:'Today 05:31', rec:'Link locked. You see only the date and the kind.', acts:['Lift the lock', 'Switch the link off', 'Mark "Reported"'] },
  { no:4840, home:'Link 14', sealed:true, what:'Sealed: blocked by Google (prohibited content)', when:'14 Nov', rec:'1 on this link, so no lock. A second locks it.', acts:['Lift the seal', 'Switch the link off'] },
];
const FLAGS_OPEN = [
  { no:4821, home:'An account', what:'3 declines in 7 days', kinds:'making drugs or other illegal goods (2), methods of self-harm (1)', when:'10 Mar', rec:'No warning on record', acts:['Read 2 sessions', 'Warn', 'Dismiss'] },
  { no:4802, home:'An account', what:'3 declines in 7 days', kinds:'weapons (3)', when:'8 Mar', rec:'A warning on record (warned 20 Feb)', acts:['Read 1 session', 'Close', 'Dismiss'] },
  { no:4830, home:'An account', what:'A flag raised at once: a threat against a real person', when:'9 Mar', rec:'Pushed to your phone', acts:['Read 1 session', 'Close with no warning', 'Dismiss'] },
  { no:4835, home:'An account', sealed:true, urgent:true, what:'Sealed: anything sexual involving minors', when:'Today 05:31', rec:'Account locked. You see only the date and the kind.', acts:['Close the account', 'Lift the lock', 'Mark "Reported"'] },
  { no:4840, home:'An account', sealed:true, what:'Sealed: blocked by Google (prohibited content)', when:'7 Mar', rec:'1 on this account, so no lock. A second locks it.', acts:['Lift the seal', 'Close the account'] },
];
const flagList = () => (isTrial() ? FLAGS_TRIAL : FLAGS_OPEN).filter(f => X.st.urgent || !f.urgent);
const flagRow = f => R(`<b>Flag ${f.no}</b> &middot; ${f.home} ${f.home.startsWith('Link') ? NS : ''} <span class="sub">&middot; ${f.when}</span>${f.sealed ? ' <span class="badge seal">Sealed</span>' : ''}
  <div>${f.what}${f.kinds ? `: ${f.kinds}` : ''}</div><div class="sub">${f.rec}</div>`,
  f.acts.map((a, i) => btn(a, i === 0 && a.startsWith('Read') ? 'primary' : (/Close|Switch the link off/.test(a) ? 'red' : ''))).join(''), { style:f.urgent ? 'background:#fff6f6' : '' });
function bFlags() {
  return BLK('flags', `Flags <span class="badge hold">${flagList().length} open</span>`, flagList().map(flagRow).join('') +
    '<div class="sub" style="margin-top:6px">A flag shows chat text only, never a file or a photo. A sealed flag shows no session at all. The learner hears only after you decide.</div>');
}
function bClosures() {
  if (isTrial()) return '';
  const c = X.st.contest;
  return BLK('closures', 'Misuse closures', R(`<b>Flag 4790</b> &middot; closed 10 Mar &middot; erased on <b>18 Mar</b> ${c ? '<span class="badge wait">Erasure held</span>' : ''}<div class="sub">${c ? 'Contest entered 15 Mar. The sessions you read stay until you decide.' : 'A contest that arrives in the 7 days is entered here. It holds the erasure until you decide.'}</div>`,
    c ? btn('Restore the account', 'primary') + btn('Keep the closure') : btn('Enter a contest')));
}
function bEntered() {
  const t = isTrial();
  const rows = t ? '<div class="emptyline">Nothing entered. Links have no email, so copies by email do not apply.</div>'
    : R('<b>A copy of their data</b> &middot; ana.lim@example.com<div class="sub">Entered 1 Mar &middot; within a month: by 1 Apr. Check the request is really the learner\'s, then run the export script.</div>', btn('Mark sent') + ' ' + NS)
    + R('<b>Delete a session</b> during a misuse closure &middot; flag 4790<div class="sub">Entered 12 Mar</div>', btn('Done') + ' ' + NS);
  return BLK('entered', 'Requests from the Crux email', rows, { right:btn('Enter a request&hellip;') });
}
function bReported() {
  return BLK('reported', 'Reported hold', R(`<b>Flag 4701</b> &middot; reported ${isTrial() ? '3 Nov' : '3 Feb'} &middot; anything sexual involving minors<div class="sub">${isTrial() ? 'A trial link: no email.' : 'Account email: r.cruz@example.com'} Kept sealed until the authorities say what to do. Nobody can open it.</div>`, btn('Erase', 'red')));
}
