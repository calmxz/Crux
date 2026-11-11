// PROTOTYPE, throwaway (calmxz/Crux#754). Part of 754-landing.html; see that file's header.
const SAME = 'Same in all three variants (held fixed from #751 and #752).';
const S = {
  land:      { g:'Landing page', name:'1 During the trial', r:(v, p) => landing(v, p, 'trial') },
  landeu:    { g:'Landing page', name:'2 From the EU or the UK', r:(v, p) => landing(v, p, 'eu') },
  landwake:  { g:'Landing page', name:'3 Start tapped while the backend wakes', r:(v, p) => landing(v, p, 'wake'), open:'should Start show anything while the backend wakes? Cloud Run usually wakes in seconds, so the spec only says the landing page shows meanwhile. Here Start shows "Starting the tutor..." until the first reply.' },
  landdown:  { g:'Landing page', name:'4 The backend can\'t be reached', r:(v, p) => landing(v, p, 'down') },
  landfull:  { g:'Landing page', name:'5 Guest mode full, before typing', r:(v, p) => landing(v, p, 'full'), open:'trial.md: "Someone who has not typed sees only that line and the video." Here that replaces only the guest part, and Request access stays. Should Request access go too?' },
  landmonth: { g:'Landing page', name:'6 Guest mode full for the month', r:(v, p) => landing(v, p, 'fullmonth'), open:'wording. trial.md says "Guest mode is full for today. Back tomorrow." and "(for the month, Back on 1 Dec.)", which reads "Guest mode is full for today. Back on 1 Dec." The ticket quotes "Guest mode is full for this month". Which is the month\'s line?' },
  landpause: { g:'Landing page', name:'7 Guest mode paused (owner switch)', r:(v, p) => landing(v, p, 'paused') },
  landpost:  { g:'Landing page', name:'8 After the trial, guest mode stays', r:(v, p) => landing(v, p, 'post') },
  landopen:  { g:'Landing page', name:'9 From opening: the pre-written example', r:(v, p) => landing(v, p, 'open'), open:'does the demo video stay once sign-up opens? trial.md has the video "in place of the pre-written example" during the trial; here the example replaces both the video and guest mode.' },
  who:       { g:'Landing page', name:'10 Who runs Crux', r:(v, p) => whoScene(v, p) },
  signin:    { g:'Landing page', name:'11 Sign in during the trial, not the owner', r:(v, p) => signinTrial(), open:'rule question. accounts.md lets only the owner\'s emails sign in during the trial, but says nothing of what anyone else sees. Shown: a refusal under Email me a code, pointing to guest mode and Request access. The other way: no Sign in on the landing page during the trial, with the owner using the sign-in page\'s own address.' },
  gticks:    { g:'Guest mode', name:'12 Entry ticks', r:(v, p) => ticksScene(v, p, { t:[true, false] }) },
  gunder:    { g:'Guest mode', name:'13 Own topic under way', r:(v, p) => GS.under(v, p), open:'G1, the guest\'s sidebar: here it holds the guest session, the sample topics, Request access and the trial\'s terms links, with no Record, Feedback or Settings. And should the reply count show all along (here "7 of 10 replies left" in the top bar), or only near the end?' },
  glimit:    { g:'Guest mode', name:'14 Own topic: the 10-reply limit', r:(v, p) => GS.limit(v, p) },
  gupload:   { g:'Guest mode', name:'15 Tried to upload a file', r:(v, p) => GS.upload(v, p), note:SAME },
  gsample:   { g:'Guest mode', name:'16 Sample topic under way', r:(v, p) => GS.sample(v, p) },
  gmini:     { g:'Guest mode', name:'17 The 2-problem mini check', r:(v, p) => GS.mini(v, p), open:'the check bar reads "Mini check" in place of #751\'s "Mastery check", since a sample earns nothing. Typing only, so no Photo button.' },
  gresult:   { g:'Guest mode', name:'18 Mini check result', r:(v, p) => GS.result(v, p), open:'what follows a sample\'s result? The after-mastery menu would offer related topics; here the tutor offers another sample, the guest\'s own topic, or Request access.' },
  gage:      { g:'Guest mode', name:'19 The age question', r:(v, p) => GS.age(v, p), note:SAME },
  gageyes:   { g:'Guest mode', name:'20 After Yes: the guest session ends', r:(v, p) => landing(v, p, 'trial'), open:'age.md gives a guest no message. Here the tab goes back to the landing page, and the entry ticks show again at the next Start.' },
  gblock:    { g:'Guest mode', name:'21 Google blocks a message', r:(v, p) => GS.block(v, p), open:'misuse.md: the guest "sees the block message, and that guest session ends". There is no wording; here the line ends the session and "Back to the start" goes to the landing page.' },
  stopday:   { g:'Guest stops', name:'22 Full for today, mid-conversation', r:(v, p) => GS.stopday(v, p) },
  stopcare:  { g:'Guest stops', name:'23 The stop caught a message in distress', r:(v, p) => GS.stopcare(v, p) },
  stopmini:  { g:'Guest stops', name:'24 Mini check stopped at the caps', r:(v, p) => GS.stopmini(v, p) },
  stopgoogle:{ g:'Guest stops', name:'25 Google\'s cap: mini check dropped', r:(v, p) => GS.stopgoogle(v, p) },
  pausedin:  { g:'Guest stops', name:'26 Guest mode paused mid-conversation', r:(v, p) => GS.pausedin(v, p) },
  req:       { g:'Request access', name:'27 The form', r:(v, p) => reqScene(v, p, 'form') },
  reqdone:   { g:'Request access', name:'28 Request received', r:(v, p) => reqScene(v, p, 'done') },
  reqeu:     { g:'Request access', name:'29 From the EU or the UK', r:(v, p) => reqScene(v, p, 'region') },
  mailin:    { g:'Request access', name:'30 Email: the invite', r:() => MAILS.invite() },
  mailno:    { g:'Request access', name:'31 Email: the decline', r:() => MAILS.decline() },
  tfirst:    { g:'Trial link', name:'32 First open: ticks and the link notice', r:(v, p) => ticksScene(v, p, { trial:true, t:[true, true] }) },
  tdevice:   { g:'Trial link', name:'33 One-time device note', r:(v, p) => noteScene(v, p, 'device') },
  tapp:      { g:'Trial link', name:'34 In the app', r:(v, p) => tappScene(v, p), note:SAME + ' The sidebar foot reads "Trial link" where an account shows its email.' },
  tset:      { g:'Trial link', name:'35 Settings (no Account part, from #753)', r:(v, p) => tsettings(v, p), note:SAME },
  tunknown:  { g:'Trial link', name:'36 A link Crux doesn\'t know', r:(v, p) => endScene(v, p, 'unknown') },
  tnetwork:  { g:'Trial link', name:'37 Network refused (10 wrong links)', r:(v, p) => endScene(v, p, 'network') },
  toff:      { g:'Link ends', name:'38 Switched off by the owner', r:(v, p) => endScene(v, p, 'off') },
  tmisuse:   { g:'Link ends', name:'39 Switched off for misuse', r:(v, p) => endScene(v, p, 'misuse') },
  tyes:      { g:'Link ends', name:'40 After Yes: access ended', r:(v, p) => endScene(v, p, 'yes') },
  tyeslate:  { g:'Link ends', name:'41 Back later on a link ended by Yes', r:(v, p) => endScene(v, p, 'yeslate') },
  tended:    { g:'Link ends', name:'42 The trial has ended', r:(v, p) => endScene(v, p, 'ended') },
  tlocked:   { g:'Link ends', name:'43 Locked by a sealed flag', r:(v, p) => lockedLink(), note:'Same in all three variants: #753\'s lock page, with the trial link\'s wording.' },
  nterms:    { g:'Notices', name:'44 Trial Terms changed: ticks again', r:(v, p) => ticksScene(v, p, { trial:true, again:true, t:[true, false] }) },
  nending:   { g:'Notices', name:'45 The trial is ending', r:(v, p) => noteScene(v, p, 'ending') },
  nbreach:   { g:'Notices', name:'46 A data breach', r:(v, p) => noteScene(v, p, 'breach') },
  ndismiss:  { g:'Notices', name:'47 A misuse flag dismissed', r:(v, p) => noteScene(v, p, 'dismiss'), note:'A re-mark notice is a line in the thread, decided in #751, so it is not shown here.' },
};
const ORDER = Object.keys(S);
const VARIANTS = [
  { key:'A', name:'Pages', note:'the landing page is a long page in sections: the video at the top, then "Try it as a guest" (sample cards, then your own topic), then Request access. Starting opens the guest app. The entry ticks, Request access, Who runs Crux, an ended link and the holder\'s notices are each a plain page holding one card, like #753\'s sign-in and opening pages.' },
  { key:'B', name:'Start box first', note:'the landing page is one screen led by the own-topic start box, with sample topics as chips under it and the video beside it. The entry ticks show inside the start box from the outset, and Start and the sample chips work only once both are ticked (owner, Q2). Request access and Who runs Crux are sections further down the same page. An ended link opens the landing page with a red banner. The holder\'s notices are a banner across the top of the app.' },
  { key:'C', name:'Straight into the app', note:'the public link opens the app shell as a guest: sample topics in the sidebar, and the start area holding the video, the 18+ line and the start box, with Request access and Sign in in the top bar. The entry ticks, Request access, Who runs Crux, an ended link and the holder\'s notices are dialogs over the app.' },
];

// ---------- switcher (prototype only, not part of the design) ----------
const qp = new URLSearchParams(location.search);
let vi = Math.max(0, VARIANTS.findIndex(v => v.key === (qp.get('variant') || 'A')));
let scene = ORDER.includes(qp.get('scene')) ? qp.get('scene') : 'land';
let device = qp.get('device') === 'phone' ? 'phone' : 'desktop';
const sel = document.getElementById('scene');
const groups = [...new Set(ORDER.map(k => S[k].g))];
sel.innerHTML = groups.map(g => `<optgroup label="${g}">${ORDER.filter(k => S[k].g === g).map(k => `<option value="${k}">${S[k].name}</option>`).join('')}</optgroup>`).join('');
function render() {
  const v = VARIANTS[vi], sc = S[scene], phone = device === 'phone';
  const d = document.getElementById('device');
  d.className = 'device ' + device;
  d.innerHTML = sc.r(v.key, phone);
  const f = d.querySelector('#focus'), sc2 = f && f.closest('.lp');
  if (sc2) sc2.scrollTop = f.offsetTop - sc2.offsetTop;
  document.getElementById('vlab').textContent = `${v.key} (${v.name})`;
  document.getElementById('dev').textContent = phone ? 'Phone' : 'Desktop';
  document.getElementById('note').innerHTML = `<p><b>PROTOTYPE, throwaway.</b> Variant ${v.key}: ${v.note} <i>Scene: ${sc.name}.</i>${sc.note ? ' <b>' + sc.note + '</b>' : ''} Red italic text has no spec wording yet.</p>${sc.open ? OPEN(sc.open) : ''}`;
  sel.value = scene;
  const u = new URL(location); u.searchParams.set('variant', v.key); u.searchParams.set('scene', scene); u.searchParams.set('device', device);
  history.replaceState(null, '', u);
}
document.getElementById('prev').onclick = () => { vi = (vi + VARIANTS.length - 1) % VARIANTS.length; render(); };
document.getElementById('next').onclick = () => { vi = (vi + 1) % VARIANTS.length; render(); };
document.getElementById('dev').onclick = () => { device = device === 'phone' ? 'desktop' : 'phone'; render(); };
sel.onchange = () => { scene = sel.value; render(); };
document.addEventListener('keydown', e => {
  if (e.target.closest('input,textarea,select,[contenteditable]')) return;
  if (e.key === 'ArrowLeft') document.getElementById('prev').click();
  if (e.key === 'ArrowRight') document.getElementById('next').click();
  const i = ORDER.indexOf(scene);
  if (e.key === 'ArrowDown') { scene = ORDER[(i + 1) % ORDER.length]; render(); e.preventDefault(); }
  if (e.key === 'ArrowUp') { scene = ORDER[(i + ORDER.length - 1) % ORDER.length]; render(); e.preventDefault(); }
});
render();
