// PROTOTYPE, throwaway (calmxz/Crux#755). Part of 755-owner.html; see that file's header.
// A scene sets the stage (trial or open), the block in focus, any state, a dialog or a reader.
const T = 'trial', O = 'open';
const S = {
  entry:     { g:'Reaching it', name:'1 Where the owner reaches it', stage:T, entry:true, open:'where the owner reaches the owner page is this ticket\'s question (#753 left it open). A: "Owner page" at the sidebar foot, above Feedback. B: no link in the app; its own address, bookmarked or from the daily email. C: "Owner" at the sidebar foot with a count of what needs a decision.' },
  notowner:  { g:'Reaching it', name:'2 Anyone else at its address', stage:T, all:() => notFound(), note:'Same in all three.', open:'the spec says every other account, test addresses included, and anyone signed out is "turned away". Shown: the same "page not found" as an unknown address, so the page\'s existence is not given away. The other way: a refusal saying the page is the owner\'s.' },
  todayT:    { g:'First view', name:'3 During the trial', stage:T, focus:'needs' },
  todayO:    { g:'First view', name:'4 From opening', stage:O, focus:'needs' },
  urgent:    { g:'First view', name:'5 A flag raised at once (pushed to the phone)', stage:T, focus:'flags', st:{ urgent:true }, urgentPick:true },
  reqs:      { g:'Trial', name:'6 Requests waiting', stage:T, focus:'reqs', st:{ dupe:true }, open:'a request shows its email, since the owner is the duplicate check. Is the email, the date and the days left enough to decide on?' },
  links:     { g:'Trial', name:'7 Trial links and browser counts', stage:T, focus:'links', open:'how is a link named? The owner never sees its key, and a link has no email. Shown: "Link 14" with the date it was made (a draft).' },
  linkoff:   { g:'Trial', name:'8 Switching a link off asks for a reason', stage:T, focus:'links', dlg:'reason' },
  dead:      { g:'Trial', name:'9 Dead links', stage:T, focus:'dead' },
  notice:    { g:'Trial', name:'10 A notice to link holders', stage:T, focus:'notice', open:'rule gap. trial.md has a breach notice shown at the holder\'s next visit, but nothing says where the owner writes it. Shown: "Write a notice" on the owner page. The other way: the release script posts it.' },
  endtrial:  { g:'Trial', name:'11 Ending the trial: pick a date', stage:T, focus:'endtrial', dlg:'end' },
  ending:    { g:'Trial', name:'12 The end date is set', stage:T, focus:'endtrial', st:{ ending:true }, open:'can the end date be changed or taken back once set? The spec says only that it is at least 7 days ahead and link holders see it.' },
  flaglink:  { g:'Safety', name:'13 A flag on a trial link', stage:T, focus:'flags', st:{ flaglink:true } },
  readflag:  { g:'Safety', name:'14 Reading a flagged session', stage:T, focus:'flags', reader:'flag' },
  dismiss:   { g:'Safety', name:'15 Dismissing a flag', stage:T, focus:'flags', dlg:'dismiss' },
  flagacct:  { g:'Safety', name:'16 Flags on accounts: the three rows', stage:O, focus:'flags', open:'does an unsealed flag show the account\'s email? The spec gives the email only for a session marked "Reported". Shown: no email, just "An account" and the flag number, which the learner\'s messages quote.' },
  warn:      { g:'Safety', name:'17 Warning', stage:O, focus:'flags', dlg:'warn' },
  close:     { g:'Safety', name:'18 Closing after a warning', stage:O, focus:'flags', dlg:'close', pick:'f4802' },
  sealed:    { g:'Safety', name:'19 A sealed flag: marking it "Reported"', stage:O, focus:'flags', st:{ urgent:true }, urgentPick:true, dlg:'report' },
  closure:   { g:'Safety', name:'20 A misuse closure waiting', stage:O, focus:'closures' },
  contest:   { g:'Safety', name:'21 A contest entered: erasure held', stage:O, focus:'closures', st:{ contest:true }, open:'"Keep the closure" after a contest: is the account erased that day, or on the original day 8 if still ahead? The spec says only that the contest holds the erasure until the owner decides.' },
  entered:   { g:'Safety', name:'22 Entering a request from the Crux email', stage:O, focus:'entered', dlg:'enter', open:'a copy asked for by email: does the owner mark it sent, or does the export script record that? The daily email lists it until it is sent.' },
  reported:  { g:'Safety', name:'23 The reported hold', stage:O, focus:'reported' },
  fb:        { g:'Feedback', name:'24 Feedback answers', stage:O, focus:'fb' },
  publish:   { g:'Feedback', name:'25 Marking a quote published', stage:O, focus:'fb', dlg:'publish' },
  quotes:    { g:'Feedback', name:'26 A withdrawn quote to remove', stage:T, focus:'quotes' },
  shares:    { g:'Feedback', name:'27 Shared sessions', stage:O, focus:'shares', open:'a share comes from a feedback answer, which is anonymous unless its email tick is given. Shown: no email on a share.' },
  readshare: { g:'Feedback', name:'28 Reading a shared session', stage:O, focus:'shares', reader:'share' },
  pathT:     { g:'Counts', name:'29 The bar during the trial', stage:T, focus:'path' },
  path:      { g:'Counts', name:'30 The bar and the path, window running', stage:O, focus:'path' },
  window:    { g:'Counts', name:'31 Start the window', stage:O, focus:'path', st:{ window:'none' } },
  undo:      { g:'Counts', name:'32 Started today: the same-day undo', stage:O, focus:'path', st:{ window:'today' } },
  arrivals:  { g:'Counts', name:'33 Arrivals by source', stage:O, focus:'arrivals' },
  turned:    { g:'Counts', name:'34 Other counts', stage:O, focus:'turned' },
  money:     { g:'Money', name:'35 Money and Google\'s bill', stage:O, focus:'money' },
  raise:     { g:'Money', name:'36 A raise: Google\'s cap first', stage:O, focus:'money', dlg:'raise', open:'the spec says the page "reminds" the owner to raise Google\'s cap first. Shown: a line in the dialog plus a tick. The other way: the line alone.' },
  settings:  { g:'Money', name:'37 Limits you can change', stage:O, focus:'settings' },
  cap:       { g:'Money', name:'38 Cap full and the let-in list', stage:O, focus:'cap' },
  switches:  { g:'Switches', name:'39 The switches', stage:O, focus:'switches' },
  partoff:   { g:'Switches', name:'40 Switching a part off', stage:O, focus:'switches', dlg:'partoff', open:'does a switch ask to confirm, or act at once? Shown: a confirm, since it changes what every learner sees.' },
  remark:    { g:'Switches', name:'41 Re-marks after a marking fault', stage:O, focus:'switches', st:{ off:['checks'], remark:true } },
  mailT:     { g:'Daily email', name:'42 The daily email in the trial', stage:T, all:v => dailyMail(v) },
  mailO:     { g:'Daily email', name:'43 The daily email from opening', stage:O, all:v => dailyMail(v) },
};
const ORDER = Object.keys(S);
const VARIANTS = [
  { key:'A', name:'One long page', r:VA, note:'the owner page sits in the main area of the owner\'s own app, opened from "Owner page" at the sidebar foot. One scrolling page: "Needs you" first, in the daily email\'s order, then Trial, Safety, Feedback, Counts, Money and limits, and Switches. Sessions open in the main area; actions open dialogs. Daily email: one list.' },
  { key:'B', name:'Its own app', r:VB, note:'the owner page is its own app at its own address, with no link from the learner app and "Back to Crux" in its top bar. Its own menu (a tab row on a phone) has one page per area: Today, Trial, Safety, Feedback, Counts, Money and limits, Switches. Safety and Feedback are a list beside the open item, and sessions open beside the list. Daily email: grouped by area, each with a link.' },
  { key:'C', name:'Inbox first', r:VC, note:'"Owner" at the sidebar foot shows a count. It opens an inbox: one card per thing that needs a decision (each request, flag, feedback answer, quote to remove), with its actions on the card, under a dark strip showing money and the switches all along. Numbers, Lists and Settings are tabs. Daily email: "Needs you", then "For your information".' },
];

// ---------- switcher (prototype only, not part of the design) ----------
const qp = new URLSearchParams(location.search);
let vi = Math.max(0, VARIANTS.findIndex(v => v.key === (qp.get('variant') || 'A')));
let scene = ORDER.includes(qp.get('scene')) ? qp.get('scene') : 'todayT';
let device = qp.get('device') === 'phone' ? 'phone' : 'desktop';
const sel = document.getElementById('scene');
const groups = [...new Set(ORDER.map(k => S[k].g))];
sel.innerHTML = groups.map(g => `<optgroup label="${g}">${ORDER.filter(k => S[k].g === g).map(k => `<option value="${k}">${S[k].name}</option>`).join('')}</optgroup>`).join('');
function render() {
  const v = VARIANTS[vi], sc = S[scene], phone = device === 'phone';
  X = { stage:sc.stage, focus:sc.focus || '', st:sc.st || {} };
  const d = document.getElementById('device');
  d.className = 'device ' + device;
  d.innerHTML = sc.all ? sc.all(v.key, phone) : v.r(sc, phone);
  const f = d.querySelector('#focus'), box = f && f.closest('.lp');
  if (box && sc.focus !== 'needs') box.scrollTop += f.getBoundingClientRect().top - box.getBoundingClientRect().top - 12;
  document.getElementById('vlab').textContent = `${v.key} (${v.name})`;
  document.getElementById('dev').textContent = phone ? 'Phone' : 'Desktop';
  document.getElementById('note').innerHTML = `<p><b>PROTOTYPE, throwaway.</b> Variant ${v.key}: ${v.note} <i>Scene: ${sc.name} (${sc.stage === T ? 'the trial' : 'from opening'}).</i>${sc.note ? ' <b>' + sc.note + '</b>' : ''} The yellow outline marks the part the scene is about. Red italic text has no spec wording yet.</p>${sc.open ? OPEN(sc.open) : ''}`;
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
