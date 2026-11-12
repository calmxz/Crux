// PROTOTYPE, throwaway (calmxz/Crux#755). Part of 755-owner.html. Variant C: inbox first, inside the owner's app.
// "Owner" at the sidebar foot carries a count of what needs a decision. Each item is a card with its own actions;
// a status strip shows money and the switches all along. Numbers, Lists and Settings are tabs.
function cStrip() {
  const off = PARTS.filter(x => !partOn(x[1])).map(x => x[0]);
  return `<div class="strip2"><span>${isTrial() ? 'Trial' : 'Open'}</span><span class="pill">Month ${usd(3.1)} of ${usd(8)}</span><span class="pill">Today ${usd(0.42)} of ${usd(2)}</span><span class="pill">Your share ${usd(1.2)} of ${usd(3)}</span>
    ${off.length ? off.map(o => `<span class="pill off">${o}: off</span>`).join('') : '<span class="pill">All parts on</span>'}${X.st.remark ? '<span class="pill">Re-marking 41 of 120</span>' : ''}${!isTrial() ? '<span class="pill">Cap 25 of 25</span>' : ''}</div>`;
}
const card = (t, s, acts, o = {}) => `<div class="card2 ${o.u ? 'urgent' : ''} ${o.f ? 'blk focus' : ''}" ${o.f ? 'id="focus"' : ''}><div class="t">${t}</div><div class="s">${s}</div>${o.body || ''}<div class="row">${acts}</div></div>`;
function cInbox() {
  const t = isTrial(), f = k => X.focus === k;
  let h = '';
  flagList().filter(x => x.urgent).forEach(x => { h += card(`&#9888; Flag ${x.no}: ${x.home} locked at once`, `${x.what} &middot; ${x.when} &middot; pushed to your phone`, x.acts.map(a => btn(a, /Close|Switch/.test(a) ? 'red' : '')).join(''), { u:true, f:f('flags') }); });
  if (t) D.reqs.forEach((r, i) => { h += card(`Request: ${r.email}`, `Asked ${r.when} &middot; ${r.left} days left ${NS}`, btn('Approve', 'primary') + btn('Decline'), { f:f('reqs') && i === 0 }); });
  flagList().filter(x => !x.urgent).forEach((x, i) => { h += card(`Flag ${x.no}: ${x.home}${x.sealed ? ' <span class="badge seal">Sealed</span>' : ''}`, `${x.what}${x.kinds ? ': ' + x.kinds : ''} &middot; ${x.when} &middot; ${x.rec}`, x.acts.map(a => btn(a, a.startsWith('Read') ? 'primary' : (/Close|Switch/.test(a) ? 'red' : ''))).join(''), { f:f('flags') && i === 0 && !X.st.urgent }); });
  if (t) h += card('Link 9 is used on 4 browsers', 'More than 3 &middot; made 4 Nov', btn('Switch off'), { f:f('links') });
  if (!t) h += card('1 closed account is erased tomorrow. Check the Crux inbox for a contest.', `Flag 4790 &middot; closed 10 Mar${X.st.contest ? ' &middot; contest entered: erasure held' : ''}`, X.st.contest ? btn('Restore the account', 'primary') + btn('Keep the closure') : btn('Enter a contest'), { f:f('closures') });
  if (!t) h += card('Learner cap full (25 of 25). Raise it before you re-share.', '25 + 2 let in &middot; Told Crux is full: 30, 12 ticked email', btn('Raise the cap&hellip;') + btn('Let in an email&hellip;'), { f:f('cap') });
  D.feedback.filter(x => x.unread).forEach((x, i) => { h += card(`New feedback &middot; Helped: ${x.helped} &middot; Would pay: ${x.pay}`, `${x.when} &middot; ${x.from}${x.email ? ' &middot; You can email: ' + x.email : ''} &middot; ${x.quote ? 'May be quoted' : 'Not for quoting'}`, (x.quote ? btn('Mark published&hellip;') : '') + btn('Mark read'), { body:`<div style="margin-top:4px">${x.text}</div>`, f:f('fb') && i === 0 }); });
  h += card('Quote withdrawn: remove by 26 Nov', '"Too slow to start in the morning. Took almost a minute." &middot; published on: LinkedIn post, 9 Nov', btn('Mark removed', 'primary'), { f:f('quotes') });
  if (!t) h += card('A copy asked for by email, still to be sent', 'ana.lim@example.com &middot; entered 1 Mar &middot; by 1 Apr. Check the request is really the learner\'s, then run the export script.', btn('Mark sent') + ' ' + NS, { f:f('entered') });
  return `<div class="inbox">${h}<div class="sub" style="text-align:center;margin:12px 0">A card leaves when it is decided. ${NS}</div></div>`;
}
function VC(sc, p) {
  if (sc.entry) return oapp(p, sessionMain(p), { owner:'C', drawer:p });
  if (sc.reader) return oapp(p, otop(p, 'Owner') + cStrip() + reader(sc.reader), { owner:'C', on:true });
  const cur = sc.area || (['reqs', 'flags', 'closures', 'cap', 'fb', 'quotes', 'needs'].includes(X.focus) || !X.focus ? 'inbox' : (X.focus === 'entered' && !isTrial() ? 'inbox' : areaOf(AREAS_C, X.focus)));
  const tabs = `<div class="ptabs">${AREAS_C.map(a => `<span class="${a[0] === cur ? 'on' : ''}">${a[1]}${a[0] === 'inbox' ? ` <span class="badge hold">${cCount()}</span>` : ''}</span>`).join('')}</div>`;
  const body = cur === 'inbox' ? cInbox() : AREAS_C.find(a => a[0] === cur)[2].map(b => ALLB[b]()).join('');
  return oapp(p, otop(p, 'Owner') + cStrip() + tabs + `<div class="op lp ${p ? 'phoneop' : ''}"><div class="sect">${body}</div></div>`, { owner:'C', on:true, overlay:dlgWrap(sc) });
}
const cCount = () => (cInbox().match(/class="card2/g) || []).length;
