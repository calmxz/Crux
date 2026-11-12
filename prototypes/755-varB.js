// PROTOTYPE, throwaway (calmxz/Crux#755). Part of 755-owner.html. Variant B: its own app at its own address.
// No link from the learner app; the owner opens /owner (bookmarked, or from the daily email). Its own menu, one page per area.
const areaCount = id => ({ today:needsItems().length, trial:isTrial() ? D.reqs.length : 0, safety:flagList().length, feedback:2 })[id] || 0;
function bTop(p) {
  return `<div class="topbar">${p ? '' : ''}<span class="brand">Crux</span><span class="badge seal">Owner</span>${stageBadge()}<span class="title"></span><span class="sub">crux&hellip;/owner ${NS}</span><span class="btn small">Back to Crux</span></div>`;
}
function bNav(p, cur) {
  const as = visibleAreas(AREAS_B);
  if (p) return `<div class="ptabs">${as.map(a => `<span class="${a[0] === cur ? 'on' : ''}">${a[1]}${areaCount(a[0]) ? ` <span class="badge wait">${areaCount(a[0])}</span>` : ''}</span>`).join('')}</div>`;
  return `<div class="onav"><div style="padding:10px 16px" class="sub">Owner</div>${as.map(a => `<div class="it ${a[0] === cur ? 'on' : ''}"><span>${a[1]}</span>${areaCount(a[0]) ? `<span class="badge wait">${areaCount(a[0])}</span>` : ''}</div>`).join('')}</div>`;
}
// Safety and Feedback are a list beside the open item; the other areas are plain pages of blocks.
function bSafety(p, sc) {
  const fl = flagList();
  const items = fl.map(f => ({ k:'f' + f.no, t:`Flag ${f.no}${f.sealed ? ' <span class="badge seal">Sealed</span>' : ''}`, s:`${f.home} &middot; ${f.when}`, d:() => BLK('flags', `Flag ${f.no}`, flagRow(f)) }))
    .concat(isTrial() ? [] : [{ k:'closures', t:'Misuse closures', s:'1: erased on 18 Mar', d:bClosures }])
    .concat([{ k:'entered', t:'Requests from the Crux email', s:isTrial() ? 'None' : '2 entered', d:bEntered }, { k:'reported', t:'Reported hold', s:'1', d:bReported }]);
  const pick = sc.pick || (['closures', 'entered', 'reported'].includes(X.focus) ? X.focus : (sc.urgentPick ? 'f' + fl.find(f => f.urgent).no : 'f' + fl[0].no));
  const cur = items.find(i => i.k === pick) || items[0];
  const det = sc.reader ? reader(sc.reader) : `<div class="det">${cur.d()}${cur.k.startsWith('f') ? '<div class="sub">The sessions open here, beside the list.</div>' : ''}</div>`;
  const list = `<div class="list">${items.map(i => `<div class="li ${i.k === cur.k ? 'on' : ''}"><div><b>${i.t}</b></div><div class="sub">${i.s}</div></div>`).join('')}</div>`;
  if (p) return sc.reader ? reader(sc.reader) : `<div class="op lp phoneop"><div class="sect">${list.replace('class="list"', 'class="list" style="width:auto;border:0"')}${cur.d()}</div></div>`;
  return `<div class="md">${list}${det}</div>`;
}
function bFeedbackArea(p, sc) {
  if (sc.reader) return reader(sc.reader);
  const fb = D.feedback;
  const list = `<div class="list" ${p ? 'style="width:auto;border:0"' : ''}>${fb.map((f, i) => `<div class="li ${i === 0 ? 'on' : ''}">${f.unread ? '<span class="dot"></span>' : ''}<b>${f.when}</b> <span class="sub">&middot; ${f.from}</span><div class="sub">Helped: ${f.helped} &middot; Would pay: ${f.pay}</div><div class="sub" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${f.text}</div></div>`).join('')}
    <div class="li"><b>Withdrawn quotes to remove</b><div class="sub">1: by 26 Nov</div></div><div class="li"><b>Shared sessions</b><div class="sub">2</div></div></div>`;
  const det = (X.focus === 'quotes' ? bQuotes() : X.focus === 'shares' ? bShares() : bFb());
  if (p) return `<div class="op lp phoneop"><div class="sect">${det}</div></div>`;
  return `<div class="md">${list}<div class="det">${det}</div></div>`;
}
function VB(sc, p) {
  if (sc.entry) return oapp(p, sessionMain(p), { owner:'B' });
  const cur = sc.area || areaOf(AREAS_B, X.focus || 'needs');
  let main;
  if (cur === 'safety') main = bSafety(p, sc);
  else if (cur === 'feedback') main = bFeedbackArea(p, sc);
  else {
    const a = AREAS_B.find(x => x[0] === cur);
    main = `<div class="op lp ${p ? 'phoneop' : ''}"><div class="sect"><h1>${a[1]}</h1>${a[2].map(b => ALLB[b]()).join('')}</div></div>`;
  }
  const inner = p ? `${bNav(p, cur)}<div style="flex:1;display:flex;flex-direction:column;min-height:0">${main}</div>` : `<div style="flex:1;display:flex;min-height:0">${bNav(p, cur)}${main}</div>`;
  return `<div style="display:flex;flex-direction:column;flex:1;min-height:0;position:relative">${bTop(p)}${inner}${dlgWrap(sc)}</div>`;
}
