// PROTOTYPE, throwaway (calmxz/Crux#753). Part of 753-account.html; see that file's header.
// ---------- scenes ----------
const L = 'Your account is locked';
const S = {
  signin:      { g:'Sign-in', name:'1 Sign-in page', r:(v, p) => signin(v, p, { step:'start' }) },
  human:       { g:'Sign-in', name:'2 Email me a code: human check', r:(v, p) => signin(v, p, { step:'start', email:true, human:true }) },
  code:        { g:'Sign-in', name:'3 Typing the code', r:(v, p) => signin(v, p, { step:'code', typed:'4821' }) },
  codewrong:   { g:'Sign-in', name:'4 Wrong code', r:(v, p) => signin(v, p, { step:'code', typed:'482190', msg:'codewrong' }) },
  codedead:    { g:'Sign-in', name:'5 Code expired, or 5 wrong tries', r:(v, p) => signin(v, p, { step:'code', typed:'', msg:'codedead' }) },
  inapp:       { g:'Sign-in', name:'6 Inside the LinkedIn app', r:(v, p) => signin(v, p, { step:'start', msg:'inapp' }) },
  senderday:   { g:'Sign-in', name:'7 Sender out for the day', r:(v, p) => signin(v, p, { step:'start', email:true, msg:'senderday' }) },
  sendermonth: { g:'Sign-in', name:'8 Sender out for the month', r:(v, p) => signin(v, p, { step:'start', email:true, msg:'sendermonth' }) },
  toomany:     { g:'Sign-in', name:'9 Too many codes today (per email)', r:(v, p) => signin(v, p, { step:'start', email:true, msg:'toomany' }) },
  toomanyreq:  { g:'Sign-in', name:'10 Too many requests (per hour, email or network)', r:(v, p) => signin(v, p, { step:'start', email:true, msg:'toomanyreq' }) },
  region:      { g:'Sign-in', name:'11 From the EU or the UK', r:(v, p) => signin(v, p, { step:'start', email:true, msg:'region' }) },
  onemore:     { g:'Sign-in', name:'12 One more thing (Start off until both ticks)', r:(v, p) => signin(v, p, { step:'onemore', ticks:[true, false] }) },
  onemore2:    { g:'Sign-in', name:'13 One more thing, both ticked', r:(v, p) => signin(v, p, { step:'onemore', ticks:[true, true] }) },
  full:        { g:'Sign-in', name:'14 Crux is full for now', r:(v, p) => signin(v, p, { step:'full', ticked:true }) },
  blocked:     { g:'Sign-in', name:'15 Blocked email (misuse)', r:(v, p) => signin(v, p, { step:'blocked' }) },
  keep:        { g:'On opening', name:'16 Keep my account / Sign out', r:(v, p) => opening(v, p, 'keep'), open:'feedback.md lets a learner in the 7-day closing untick a quote or a share, but this step comes before anything else. A puts a "Your feedback" link on the card; B has no way there; C leaves the sidebar usable behind the card.' },
  terms:       { g:'On opening', name:'17 Terms changed', r:(v, p) => opening(v, p, 'terms') },
  lockclose:   { g:'On opening', name:'18 Locked: misuse closure (7 days)', r:(v, p) => v === 'C' ? opening(v, p, 'lockclose', { title: L }) : v === 'B' ? lockedSession(v, p, { overlay: dlg(CARDS.lockclose(v)) }) : opening(v, p, 'lockclose') },
  lockseal:    { g:'On opening', name:'19 Locked: sealed flag', r:(v, p) => v === 'C' ? opening(v, p, 'lockseal', { title: L }) : v === 'B' ? lockedSession(v, p, { overlay: dlg(CARDS.lockseal(v)) }) : opening(v, p, 'lockseal') },
  lockread:    { g:'On opening', name:'20 Reading a session while locked', r:(v, p) => lockedSession(v, p), open:'can a locked learner still remove files (the greyed &times;) and delete sessions? A lock is read-only, which would say no. Deleting is erasing, which the learner may want before the owner decides.' },
  lockage:     { g:'On opening', name:'21 Locked, with the age question open', r:(v, p) => lockedSession(v, p, { age:true }) },
  u18:         { g:'On opening', name:'22 After Yes: the under-18 closure', r:(v, p) => v === 'C' ? shell(v, p, topbar(v, p, CURNAME) + `<div class="thread"><div class="sysline stop">Your account is closed. Crux is for people 18 and over, so your account and everything in it have been erased. ${NS}</div></div>` + composer({ lock:'Signing you out&hellip; ' + NS })) : opening(v, p, 'u18') },
  settings:    { g:'Settings', name:'23 Settings', r:(v, p) => settings(v, p, {}) },
  files200:    { g:'Settings', name:'24 Settings: files', r:(v, p) => settings(v, p, { tab:'files' }) },
  yourfb:      { g:'Settings', name:'25 Settings: Your feedback', r:(v, p) => settings(v, p, { tab:'feedback' }) },
  account:     { g:'Settings', name:'26 Settings: account', r:(v, p) => settings(v, p, { tab:'account' }) },
  setlocked:   { g:'Settings', name:'27 Settings while locked', r:(v, p) => settings(v, p, { tab:'account', locked:true }) },
  signout:     { g:'Settings', name:'28 Where Sign out is', r:(v, p) => signoutScene(v, p) },
  feedback:    { g:'Feedback', name:'29 Feedback page', r:(v, p) => feedback(v, p, { step:1 }) },
  fbshare:     { g:'Feedback', name:'30 Share ticked, list open', r:(v, p) => feedback(v, p, { step:3, filled:true, share:true, listOpen:true }) },
  fbnosess:    { g:'Feedback', name:'31 No sessions: no share choice', r:(v, p) => feedback(v, p, { step:3, nosess:true }) },
  fbtrial:     { g:'Feedback', name:'32 Trial link: no email tick', r:(v, p) => feedback(v, p, { step:3, trial:true }) },
  fbsent:      { g:'Feedback', name:'33 Sent', r:(v, p) => feedback(v, p, { sent:true }) },
  fbtoomany:   { g:'Feedback', name:'34 Too many sends today', r:(v, p) => feedback(v, p, { step:3, filled:true, toomany:true }) },
  fblocked:    { g:'Feedback', name:'35 Locked or closing: cannot send', r:(v, p) => feedback(v, p, { locked:true }) },
  close:       { g:'Closing', name:'36 Close account: confirm', r:(v, p) => closing(v, p, {}) },
  closecopy:   { g:'Closing', name:'37 Confirm, copy asked for', r:(v, p) => closing(v, p, { copy:true }) },
  closed:      { g:'Closing', name:'38 Just after closing', r:(v, p) => closedScene(v, p), open:'what does the learner see right after closing? There is no spec wording. A signs out to the sign-in page with a note; B goes straight to Keep my account / Sign out; C signs out to the landing page with a banner.' },
  mailclose:   { g:'Closing', name:'39 Email: your account closes', r:(v, p) => MAILS.close(v) },
  mailcopy:    { g:'Closing', name:'40 Email: your copy', r:(v, p) => MAILS.copy(v) },
};
const ORDER = Object.keys(S);
const VARIANTS = [
  { key:'A', name:'Pages', note:'everything is a page. Sign-in is one card that changes step by step, with messages under the button they are about. Steps on opening and the lock are a full page with no app around them. Settings and Feedback are pages in the main area, linked from the sidebar footer. Sign out is in Settings.' },
  { key:'B', name:'Dialogs and panels', note:'the app stays behind. Sign-in sits beside the landing page\'s example, with messages in a box at the top. Steps on opening are dialogs over the dimmed app. The lock is a banner across the app. Settings is a dialog with tabs. Feedback is a panel beside the conversation. Feedback and an account menu (Settings, Sign out) are in the top bar. Spec wording says "a settings page" and "one page"; choosing B changes that wording.' },
  { key:'C', name:'Separate settings area', note:'sign-in is a dialog over the landing page, with messages as a banner at its top. Steps on opening and the lock are cards in the main area, with the sidebar still usable. Settings is its own area, with its own menu in place of the sidebar, and holds Send feedback as a three-step form. An Account item in the sidebar footer opens Settings, Feedback and Sign out.' },
];

// ---------- switcher (prototype only, not part of the design) ----------
const qp = new URLSearchParams(location.search);
let vi = Math.max(0, VARIANTS.findIndex(v => v.key === (qp.get('variant') || 'A')));
let scene = ORDER.includes(qp.get('scene')) ? qp.get('scene') : 'signin';
let device = qp.get('device') === 'phone' ? 'phone' : 'desktop';
const sel = document.getElementById('scene');
const groups = [...new Set(ORDER.map(k => S[k].g))];
sel.innerHTML = groups.map(g => `<optgroup label="${g}">${ORDER.filter(k => S[k].g === g).map(k => `<option value="${k}">${S[k].name}</option>`).join('')}</optgroup>`).join('');
function render() {
  const v = VARIANTS[vi], sc = S[scene], phone = device === 'phone';
  const d = document.getElementById('device');
  d.className = 'device ' + device;
  d.innerHTML = sc.r(v.key, phone);
  document.getElementById('vlab').textContent = `${v.key} (${v.name})`;
  document.getElementById('dev').textContent = phone ? 'Phone' : 'Desktop';
  document.getElementById('note').innerHTML = `<p><b>PROTOTYPE, throwaway.</b> Variant ${v.key}: ${v.note} <i>Scene: ${sc.name}.</i> Red italic text has no spec wording yet.</p>${sc.open ? OPEN(sc.open) : ''}`;
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
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); const i = ORDER.indexOf(scene) + (e.key === 'ArrowDown' ? 1 : -1); scene = ORDER[(i + ORDER.length) % ORDER.length]; render(); }
});
render();
