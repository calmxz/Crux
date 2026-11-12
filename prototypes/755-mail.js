// PROTOTYPE, throwaway (calmxz/Crux#755). Part of 755-owner.html. The owner's daily email, and a non-owner turned away.
// Lines are operations.md's list, in its order; which appear depends on the day. Each variant lays them out its own way.
function mailLines() {
  const t = isTrial();
  return [
    { a:'money', need:false, l:t ? 'The month\'s budget is at 50%.' : 'The month\'s budget is at 80%.' },
    !t && { a:'money', need:true, l:'The learner cap filled.' },
    !t && { a:'money', need:false, l:'Your share is at 80%.' },
    !t && { a:'money', need:false, l:'Google +35%: 3.5 Flash-Lite output tokens +USD 0.10' },
    { a:'counts', need:false, l:t ? '3 trial links turned away. Guest mode stopped 5 times.' : '4 learners turned away yesterday.' },
    !t && { a:'counts', need:false, l:'6 code requests refused: the sender\'s share ran out.' },
    { a:'feedback', need:false, l:'2 new feedback answers' },
    { a:'feedback', need:true, l:'1 quote permission withdrawn' },
    t && { a:'trial', need:true, l:'3 requests waiting' },
    { a:'safety', need:true, l:t ? 'Flag 4812: Link 12, 3 declines in 7 days' : 'Flag 4821: an account, 3 declines in 7 days' },
    !t && { a:'safety', need:true, l:'1 closed account is erased tomorrow. Check the Crux inbox for a contest.' },
    !t && { a:'safety', need:true, l:'A copy asked for by email, still to be sent' },
    { a:'switches', need:false, l:'1 required email still unsent: an idle warning. 1 check paused by repeated blocks.' },
    { a:'switches', need:false, l:'The monthly AI test round did not run.' },
  ].filter(Boolean);
}
function dailyMail(v, p) {
  const L = mailLines(), sub = `Crux, ${TODAY()}: ${L.filter(x => x.need).length} things need you ${NS}`;
  let bd;
  if (v === 'A') bd = `<ul>${L.map(x => `<li>${x.l}</li>`).join('')}</ul><p><a>Open the owner page</a></p>`;
  else if (v === 'B') bd = AREAS_B.filter(a => L.some(x => x.a === a[0])).map(a => `<h3 style="margin:12px 0 4px">${a[1]}</h3><ul style="margin:0">${L.filter(x => x.a === a[0]).map(x => `<li>${x.l}</li>`).join('')}</ul><a class="sub">Open ${a[1]} &#8250;</a>`).join('');
  else bd = `<h3 style="margin:0 0 4px">Needs you</h3>${L.filter(x => x.need).map(x => `<div class="need"><span class="ic">&#9679;</span><div style="flex:1">${x.l}</div><a class="sub">Open &#8250;</a></div>`).join('')}
    <h3 style="margin:14px 0 4px">For your information</h3><ul style="margin:0">${L.filter(x => !x.need).map(x => `<li>${x.l}</li>`).join('')}</ul>`;
  return `<div class="mail"><div class="env"><div class="hd"><b>${sub}</b><br>From: Crux &middot; To: you &middot; about 8 am Philippine time</div><div class="bd">${bd}<p class="sub">Feedback shows as a count only, never the words or the sender.</p></div></div></div>`;
}
const notFound = () => `<div class="gatebar"><span class="brand">Crux</span></div><div class="gate"><div class="card"><h2>Page not found</h2><p class="sub">The address may be wrong, or the page may have moved.</p><span class="btn">Go to Crux</span></div></div>`;
