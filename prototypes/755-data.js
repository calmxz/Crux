// PROTOTYPE, throwaway (calmxz/Crux#755). Part of 755-owner.html; see that file's header.
// Sample data only. Emails are example.com placeholders; counts and money are made up for the mock.
const NS = '<span class="nospec">[no spec wording]</span>';
const OPEN = t => `<div class="callout" style="margin-top:8px"><b>Open question:</b> ${t}</div>`;
const tb = on => `<span class="tb ${on ? 'on' : ''}">${on ? '&#10003;' : ''}</span>`;
const sw = on => `<span class="sw ${on ? 'on' : ''}"><i></i></span>`;
const btn = (t, k = '') => `<span class="btn small ${k}">${t}</span>`;
const meter = (a, b) => `<div class="meter"><i style="width:${Math.min(100, a / b * 100)}%"></i></div>`;
const usd = n => 'USD ' + n.toFixed(2);

// X is the scene's context, set by the switcher before each render: stage, focus block, state flags.
let X = { stage:'trial', focus:'', st:{} };
const isTrial = () => X.stage === 'trial';
const TODAY = () => isTrial() ? 'Mon 16 Nov' : 'Thu 11 Mar';

const D = {
  reqs: [
    { email:'maria.reyes@example.com', when:'Today 07:12', left:30 },
    { email:'jun.dela.cruz@example.com', when:'Yesterday 21:40', left:29 },
    { email:'k.tan@example.com', when:'2 Nov', left:16 },
  ],
  links: [
    { n:14, made:'12 Nov', br:1 },
    { n:12, made:'9 Nov', br:2 },
    { n:9, made:'4 Nov', br:4 },
    { n:7, made:'2 Nov', br:1 },
  ],
  dead: [
    { n:11, why:'Switched off: "Shared in a group chat; used on 6 browsers."', when:'10 Nov' },
    { n:5, why:'Ended', when:'6 Nov' },
  ],
  feedback: [
    { when:'Today 06:50', unread:true, helped:'yes', pay:'yes', text:'The check felt fair. I liked that it made me show working before marking.', quote:true, email:null, from:'account' },
    { when:'Yesterday', unread:true, helped:'yes', pay:'maybe', text:'Explanations were clear, but the tutor waited too long before giving a hint on the second objective.', quote:false, email:'paolo.g@example.com', from:'account' },
    { when:'8 Nov', unread:false, helped:'no', pay:'no', text:'Too slow to start in the morning. Took almost a minute.', quote:true, email:null, from:'trial link', published:'LinkedIn post, 9 Nov' },
  ],
  arrivals: [ ['linkedin', 12, 61, 140], ['facebook', 4, 30, 88], ['other sites', 1, 6, 15], ['direct', 3, 19, 52] ],
};

// The path and the bar (opening only; nothing in the trial counts).
const PATH = [ ['Signed up', 31], ['Started a topic', 26], ['Reached a mastery check', 19], ['Mastered a topic', 14],
  ['Came back', 12], ['Came back after mastering', 6], ['Mastered a second topic', 3] ];
const BAR = [ ['mastered', 14, 20], ['came back after mastering', 6, 8], ['masters who said "yes"', 5, 8] ];

// The switches (live-faults.md): each part, plus guest mode.
const PARTS = [ ['The mastery check', 'checks'], ['Files', 'files'], ['The lookup', 'lookup'], ['The whole tutor', 'tutor'], ['Guest mode', 'guest'] ];
const partOn = k => !(X.st.off || []).includes(k);

// Which blocks each variant groups into an area. A shows every block on one page.
const AREAS_B = [
  ['today', 'Today', ['needs']],
  ['trial', 'Trial', ['reqs', 'links', 'dead', 'notice', 'endtrial'], 'trial'],
  ['safety', 'Safety', ['flags', 'closures', 'entered', 'reported']],
  ['feedback', 'Feedback', ['fb', 'quotes', 'shares']],
  ['counts', 'Counts', ['path', 'arrivals', 'turned']],
  ['money', 'Money and limits', ['money', 'settings', 'cap']],
  ['switches', 'Switches', ['switches']],
];
const AREAS_C = [
  ['inbox', 'Needs you', ['needs']],
  ['numbers', 'Numbers', ['path', 'arrivals', 'turned', 'money']],
  ['records', 'Lists', ['links', 'dead', 'fb', 'shares', 'entered', 'reported']],
  ['settings', 'Settings', ['switches', 'settings', 'cap', 'notice', 'endtrial']],
];
const areaOf = (areas, blk) => (areas.find(a => a[2].includes(blk)) || areas[0])[0];
const visibleAreas = areas => areas.filter(a => !(a[3] === 'trial' && !isTrial()));
