// PROTOTYPE, throwaway (calmxz/Crux#780). The all-sessions page inside #752's chosen shell (sidebar on desktop,
// drawer on a phone). Each scene is one question; its options switch with ?opt=. The rest of the page uses the
// defaults in DEF, which are placeholders, not recommendations. The search really runs over the sample data.
const DEF = { entry:'D', layout:'D', scope:'C', typing:'A', hit:'A', check:'A', sealed:'A', filter:'A', sort:'A', menu:'A', paging:'A', empty:'A' };
const SCENES = {
  entry: { name:'Where the page opens from', opts:{
    A:{ name:'A link beside the full list', note:'The sidebar keeps every session, as now. "All sessions" sits beside the Sessions heading and opens the page in the main area.' },
    B:{ name:'A shorter sidebar', note:'The sidebar shows the 10 most recent sessions, then "All sessions (24)". Older sessions are found only on the page.' },
    C:{ name:'A search box in the sidebar', note:'The sidebar keeps every session and gains a search box under "+ New session". Typing in it opens the page with the search already run; "All sessions" also opens it empty.' },
    D:{ name:'A shorter sidebar, with a search button by "Crux"', note:'The owner’s mix of B and C. The sidebar shows the 10 most recent sessions, then "All sessions (24)". A search button sits at the right of the sidebar’s top bar, in line with "Crux"; it opens the page with the cursor in its search box.' } } },
  layout: { name:'How the page lists sessions', opts:{
    A:{ name:'Lines, as in the sidebar', note:'Each session is a sidebar line (name and badges; "On:" or "Mastered last:" and the last visit; the progress bar), only wider.' },
    B:{ name:'A table', note:'Columns: Session, Now, Mastered, Last visit, Started. On a phone the table becomes lines with a fourth row, "Started 12 Nov".' },
    C:{ name:'Lines under date headings', note:'Sidebar lines grouped under "This week", "Earlier in November", then each month.' },
    D:{ name:'Lines without the topic row', note:'On the page only: the name and its badges, then the last visit, then the progress bar. No "On:" or "Mastered last:". The sidebar keeps its full line (#752).' },
    E:{ name:'Name and last visit only', note:'On the page only: the name, then the last visit. No badges, no topic row, no progress bar. The sidebar keeps its full line (#752).' } } },
  scope: { name:'What the search looks through', opts:{
    A:{ name:'Names and topics', note:'Session names, and the names of topics in each session (under way, mastered, queued).' },
    B:{ name:'Names, topics and file names', note:'A, plus the names of each session\'s files ("MATH101 week 7.pdf"). Not what is inside the files.' },
    C:{ name:'B, plus the conversations', note:'B, plus every message in each conversation, the learner\'s and the tutor\'s. Tutor maths is stored as LaTeX (#771), so "y²" does not find a message showing y², while "y^2" finds it and more.' } } },
  typing: { name:'When results appear', opts:{
    A:{ name:'As you type', note:'The list narrows with each letter, after a short pause.' },
    B:{ name:'On Enter', note:'Nothing changes until Enter or Search.' } } },
  hit: { name:'How a match in a conversation shows (if the search reads conversations)', opts:{
    A:{ name:'One snippet per session', note:'The newest matching message, with "and 1 more" when there are others. Tapping the snippet opens the session at that message, highlighted.' },
    B:{ name:'Every matching message', note:'Each matching message under its session. Each opens the session at that message, highlighted.' },
    C:{ name:'A mark, then find in the session', note:'The line only says "in the conversation". Opening it shows a find bar in the session, "1 of 2", with up and down.' } } },
  check: { name:'A session with an open check (if the search reads conversations)', opts:{
    A:{ name:'Its earlier teaching is not searched', note:'While its check is open, the earlier teaching is hidden (mastery-check.md), so the search skips it. Searching "ball" does not find Projectile motion by its teaching.' },
    B:{ name:'Listed, opening at the check', note:'A match in the hidden teaching lists the session with "Check open: matches show after the check", and opening it goes to the check. The text itself is never shown.' } } },
  sealed: { name:'Sealed sessions on the page', opts:{
    A:{ name:'Listed, found by name only', note:'Listed with "Sealed", as in the sidebar. The search finds a sealed session by its name only, never by its topics, files or conversation. An unnamed one ("Sealed session") is never found.' },
    B:{ name:'Listed, never found', note:'Listed with "Sealed" when nothing is searched; any search leaves them out.' },
    C:{ name:'Not on the page', note:'Sealed sessions stay only in the sidebar.' } } },
  filter: { name:'Filters', opts:{
    A:{ name:'None', note:'Search and sort only.' },
    B:{ name:'By badge', note:'All, Under way, Check open, Waiting, Remove a file: the sidebar\'s states.' },
    C:{ name:'By progress', note:'All, Under way, Mastered something, Nothing yet.' } } },
  sort: { name:'Sort', opts:{
    A:{ name:'Last visit only', note:'Newest visit first, as the sidebar.' },
    B:{ name:'Last visit, started, name', note:'A menu: Last visit (default), Started, Name A to Z.' },
    C:{ name:'B, plus most mastered', note:'B, plus Most mastered.' } } },
  menu: { name:'Rename and delete on the page', opts:{
    A:{ name:'The same menu on each line', note:'Each line has the sidebar\'s "⋯" with Rename and Delete (a sealed line: Delete greyed out).' },
    B:{ name:'No menu', note:'Lines only open their session. Rename and delete stay in the sidebar and the session\'s title.' } } },
  paging: { name:'A long list', opts:{
    A:{ name:'Every session at once', note:'All 24 load together.' },
    B:{ name:'A batch, then Show more', note:'The first 15 (a placeholder number), then "Show 9 more".' },
    C:{ name:'Batches that load as you scroll', note:'The owner’s "A, maybe with lazy loading". The first 15 load (a placeholder number); when Maya scrolls near the end, the next batch loads by itself, with a brief "Loading..." line. No button.' } } },
  empty: { name:'Nothing to show', opts:{
    A:{ name:'Short line and Clear', note:'No match: the line and "Clear search". No sessions: the line and "+ New session".' },
    B:{ name:'Line that says what was searched', note:'As A, and the no-match line names what the search looks through.' } } },
};
const ORDER = Object.keys(SCENES);
const SEED = { scope:'balloon', hit:'ball', check:'ball', sealed:'rate', typing:'', empty:'zebra' };
const qp = new URLSearchParams(location.search);
let scene = ORDER.includes(qp.get('scene')) ? qp.get('scene') : 'entry';
let opt = SCENES[scene].opts[qp.get('opt')] ? qp.get('opt') : 'A';
let device = qp.get('device') === 'desktop' ? 'desktop' : 'phone';
let st = fresh(); if (qp.has('q')) st.q = qp.get('q');
if (qp.get('case') === 'nos') st.emptyCase = 'nos';
function fresh() { return { q: SEED[scene] || '', pend:null, filt:'all', sort:'last', view:'page', open:null, menuFor:null, more:false, drawer: scene === 'entry', emptyCase:'none', flash:'' }; }
function cfg() {
  const c = Object.assign({}, DEF, { [scene]: opt });
  if (scene === 'hit' || scene === 'check') c.scope = 'C';
  if (scene === 'sealed') c.scope = 'C';
  return c;
}

