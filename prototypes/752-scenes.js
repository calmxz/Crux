// PROTOTYPE, throwaway (calmxz/Crux#752). The scenes each variant is walked through.
const ATT = n => `<span class="chip" style="background:rgba(255,255,255,.2);color:#fff">&#128206; ${n}</span><br>`;
const ALKANES = [ { n:1, t:'Name straight-chain alkanes', s:'sh' }, { n:2, t:'Name branched alkanes', s:'ip' }, { n:3, t:'Draw an alkane from its name', s:'ns' } ];
function allowCard() {
  return `<b>Lecture 9.pdf wasn't added: your files are using 192 of 200 MB.</b> Remove a file to make room. ${NS}
    ${ALLOW.map(a => `<div class="frow"><div style="flex:1"><div class="fn">${a.n}</div><div class="st2">${a.mb} MB${a.s ? ' &middot; ' + a.s : ''}</div></div>${a.s ? '<span class="btn small">Remove</span>' : ''}</div>`).join('')}`;
}
const S = {
  open:     { name:'1. Opening the app', view:'open' },
  list:     { name:'2. The session list', view:'list' },
  list2:    { name:'2b. The session list with progress', view:'list', progress:true },
  manage:   { name:'3. Rename or delete: the menu', view:'manage' },
  rename:   { name:'4. Renaming', view:'rename' },
  manageTop:{ name:'3b. Rename or delete from the top bar (option C)', view:'session', cur:'chain', title:'Chain rule (MATH101 week 6)', both:true, topMenu:true, files:'none', here:true, topic:'Three-layer composites', obj:[ { n:1, t:'Spot the three layers', s:'sh' }, { n:2, t:'Differentiate from the outside in', s:'ip' }, { n:3, t:'Check by expanding', s:'ns' } ] },
  renameTop:{ name:'4b. Renaming in the top bar (option C)', view:'session', cur:'chain', title:'Chain rule (MATH101 week 6)', both:true, renameTop:true, files:'none', here:true, topic:'Three-layer composites', obj:[ { n:1, t:'Spot the three layers', s:'sh' }, { n:2, t:'Differentiate from the outside in', s:'ip' }, { n:3, t:'Check by expanding', s:'ns' } ] },
  sealedMenu:{ name:'4c. The menu on a sealed session', view:'list', sealedMenu:true },
  del:      { name:'5. Delete warning: mastered topics', view:'delete' },
  delCheck: { name:'5b. Delete warning: a half-done check', view:'delete', del:'check' },
  delPassed:{ name:'5c. Delete warning: passed objective and files', view:'delete', del:'passed' },
  delPlain: { name:'5d. Delete warning: nothing on the record', view:'delete', del:'plain' },
  delTyped: { name:'5e. Delete warning: type to confirm', view:'delete', typedConfirm:true },
  mastered: { name:"6. What you've mastered: by date", view:'mastered' },
  mastered2:{ name:"6b. What you've mastered: by session", view:'mastered', grouped:true },
  newS:     { name:'7. New session with a file', view:'new' },
  newread:  { name:'8. The file being read', view:'session', files:'reading', title:'the implicit differentiation part', panelOpen:true,
    thread:[ { t:'me', h: ATT('MATH101 week 7.pdf') + 'the implicit differentiation part' }, { t:'raw', h:'<div class="marking">Reading&hellip;<span class="dots"></span></div>' } ] },
  filestates:{ name:'9. File states in the panel', view:'session', files:'states', panelOpen:true,
    thread: TEACH.concat([ { t:'me', h: ATT('Lecture 7.pdf') + 'this one has the tangent examples' }, { t:'sys', h:`Lecture 7.pdf uploaded successfully. ${NS}` },
      { t:'sys', k:'stop', h:"That's today's tutoring. Answer whenever you like, and the tutor will pick up here tomorrow." },
      { t:'me', h: ATT('worksheet photo.jpg') + 'and the worksheet' } ]) },
  paused:   { name:'10. Files paused for a fault', view:'session', files:'paused', filesOff:true, panelOpen:true,
    thread: TEACH.concat([ { t:'sys', k:'warn', h:`Files are paused while we fix something. Your files are kept, and Lecture 9.pdf will be read when they're back. ${NS}` } ]) },
  viewer:   { name:'11. Reading a file from "as on slide 30"', view:'session', viewer:true },
  remove:   { name:'12. Removing a file', view:'session', removeConfirm:true, panelOpen:true,
    thread: TEACH.concat([ { t:'sys', only:'B', h:'Lecture 8 slides.pptx removed. What the tutor already said about this file stays in the conversation. To erase that too, delete the session.' } ]) },
  allowance:{ name:'13. Allowance full', view:'session',
    thread: TEACH.concat([ { t:'me', h: ATT('Lecture 9.pdf (18 MB)') + 'next lecture' }, { t:'raw', only:'B', h:`<div class="card" style="align-self:center;max-width:92%">${allowCard()}</div>` } ]),
    extra: (v, phone) => v === 'A' ? `<div class="overlay"><div class="card" style="max-width:420px">${allowCard()}<div class="row" style="justify-content:flex-end"><span class="btn">Close</span></div></div></div>`
      : v === 'C' ? `<div class="toast" style="left:12px;right:${phone ? 12 : 312}px;max-width:none;background:#fff;color:inherit;border:1px solid var(--line);bottom:62px">${allowCard()}</div>` : '' },
  wrongtype:{ name:'14. Wrong type or too big', view:'session',
    pins:[ { only:'AC', k:'warn', h:'lecture 6.ppt: Please save this as a PDF or <code>.pptx</code>. <span class="alink">Dismiss</span>' },
           { only:'AC', k:'warn', h:`Full year notes.pdf has 340 pages, over the 100-page limit: upload just the chapter you need. ${NS} <span class="alink">Dismiss</span>` } ],
    thread: TEACH.concat([ { t:'sys', k:'warn', only:'B', h:'lecture 6.ppt: Please save this as a PDF or <code>.pptx</code>.' },
           { t:'sys', k:'warn', only:'B', h:`Full year notes.pdf has 340 pages, over the 100-page limit: upload just the chapter you need. ${NS}` } ]) },
  held:     { name:'15. Held by a harmful file', view:'session', cur:'org', title:'Organic chemistry notes', files:'held', topic:'Naming alkanes', from:'Alkanes handout.pdf', obj:ALKANES, panelOpen:true,
    thread:[ { t:'tutor', h:'2-methylpentane: find the longest chain first.' }, { t:'me', h: ATT('reagents.pdf') + 'also this one' },
      { t:'tutor', h:"I can't help with this file. This session can't continue until you remove it." }, { t:'me', h:'can we just keep going with alkanes' },
      { t:'tutor', h:"I can't help with this file. This session can't continue until you remove it." } ],
    pins:[ { only:'BC', k:'stop', h:`This session is waiting until you remove reagents.pdf. Your progress is kept. ${NS} <span class="btn small">Remove reagents.pdf</span>` } ] },
  sealed:   { name:'16. A sealed session', view:'sealed' },
  sealA:    { name:'16b. Sealed lines, option A: always the name', view:'list', sealMode:'A' },
  sealB:    { name:'16c. Sealed lines, option B: always hidden', view:'list', sealMode:'B' },
  sealC:    { name:'16d. Sealed lines, option C: the name if it has one', view:'list', sealMode:'C' },
  jump:     { name:'17. Jump points in a long conversation', view:'session', jump:true,
    thread:[ { t:'div', h:'Topic: Implicit differentiation' }, { t:'tutor', h:'Here are your objectives...' }, { t:'div', h:'Diagnostic' }, { t:'tutor', h:'Try this one: differentiate y&sup3; = x.' },
      { t:'div', h:'Objective 1: y terms' }, { t:'tutor', h:'Each y term gets a dy/dx...' }, { t:'div', h:'Objective 2: dy/dx' }, { t:'tutor', h:'Now collect the dy/dx terms...' },
      { t:'div', h:'Objective 1 again' }, { t:'tutor', h:'Back to y terms for a moment...' }, { t:'div', h:'Mastery check: result' }, { t:'raw', h:'<div class="card"><div class="h no">Not yet: 3 of 4</div><div class="sub">Mastery check, 9 Nov</div></div>' } ] },
};
S.here = { name:'18. Mastered in this session (panel)', view:'session', cur:'chain', title:'Chain rule (MATH101 week 6)', topic:'Three-layer composites', from:'MATH101 week 6.pdf', panelOpen:true, here:true, files:'none',
  obj:[ { n:1, t:'Spot the three layers', s:'sh' }, { n:2, t:'Differentiate from the outside in', s:'ip' }, { n:3, t:'Check by expanding', s:'ns' } ],
  thread:[ { t:'tutor', h:'You mastered the chain rule. Next up: three-layer composites. Here are the objectives...' }, { t:'me', h:'go' }, { t:'tutor', h:'Take sin(x&sup2; + 1)&sup3;. How many layers do you see?' } ] };
const ORDER = Object.keys(S);
