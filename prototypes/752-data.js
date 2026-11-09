// PROTOTYPE, throwaway (calmxz/Crux#752). Sample data shared by every scene and variant.
const NS = '<span class="nospec">[no spec wording]</span>';
const SESSIONS = [
  { id:'impl', pr:[1,4,'ship'],  nm:'Implicit differentiation (MATH101 week 7)', ln:'On: Implicit differentiation', when:'Today' },
  { id:'chain', pr:[1,3,'sip'], nm:'Chain rule (MATH101 week 6)', ln:'Mastered last: The chain rule', when:'Yesterday', badge:['wait','1 waiting'] },
  { id:'phys', pr:[3,4,'sssp'],  nm:'Projectile motion', ln:'On: Range', when:'6 Nov', badge:['chk','Check open'] },
  { id:'photo', nm:'photosynthesis for my bio quiz', ln:'', when:'5 Nov' },
  { id:'new',   nm:'New session', ln:'', when:'4 Nov' },
  { id:'org', pr:[1,3,'sip'],   nm:'Organic chemistry notes', ln:'On: Naming alkanes', when:'2 Nov', badge:['hold','Remove a file to continue'] },
  { id:'seal',  nm:'Reaction rates', ln:'', when:'1 Nov', badge:['seal','Sealed'], sealed:true },
  { id:'seal2', nm:'<span class="nospec" style="font-size:13px">[first words of the blocked request]</span>', when:'4 Oct', badge:['seal','Sealed'], sealed:true, unnamed:true, demo:true },
  { id:'bio',   nm:'Cell respiration (BIO110)', ln:'Mastered last: Glycolysis', when:'30 Oct' },
  { id:'prod',  nm:'Product rule', ln:'Mastered last: The product rule', when:'28 Oct' },
  { id:'basic', nm:'Derivatives basics (MATH101 week 5)', ln:'Mastered last: The power rule', when:'22 Oct' },
];
const OBJ = [
  { n:1, t:'Differentiate y terms with the chain rule', s:'sh' },
  { n:2, t:'Solve for dy/dx', s:'ip' },
  { n:3, t:"Find a tangent's slope at a point", s:'ns' },
  { n:4, t:'Second derivatives, implicitly', s:'ns' },
];
const LBL = { ns:'not started', ip:'in progress', sh:'shown', pa:'passed', dr:'dropped' };
// file states: ok, reading, waiting, failed, held, paused
const FILES = {
  plain:  [ { n:'MATH101 week 7.pdf', m:'42 pages, 6 MB', s:'ok' }, { n:'Lecture 8 slides.pptx', m:'31 slides, 9 MB', s:'ok' } ],
  states: [ { n:'MATH101 week 7.pdf', m:'42 pages, 6 MB', s:'ok', mark:true },
            { n:'Lecture 8 slides.pptx', m:'9 MB', s:'reading' },
            { n:'worksheet photo.jpg', m:'1 page, 2 MB', s:'waiting' },
            { n:'scan-notes.pdf', m:'', s:'failed' } ],
  paused: [ { n:'MATH101 week 7.pdf', m:'42 pages, 6 MB', s:'ok' }, { n:'Lecture 9.pdf', m:'4 MB', s:'paused' } ],
  held:   [ { n:'Alkanes handout.pdf', m:'8 pages, 1 MB', s:'ok' }, { n:'reagents.pdf', m:'12 pages, 3 MB', s:'held' } ],
  reading:[ { n:'MATH101 week 7.pdf', m:'6 MB', s:'reading' } ],
  none: [],
};
const MASTERED = [
  { t:'The chain rule', d:'3 Nov', s:'Chain rule (MATH101 week 6)' },
  { t:'Index laws', note:'prerequisite topic', d:'1 Nov', s:'Chain rule (MATH101 week 6)' },
  { t:'Glycolysis', d:'30 Oct', s:'Cell respiration (BIO110)' },
  { t:'The product rule (without quotient-rule shortcuts)', note:'narrower name: an objective was dropped', d:'28 Oct', s:'Product rule' },
  { t:'The Krebs cycle', d:'27 Oct', s:'Cell respiration (BIO110)' },
  { t:'The power rule', d:'22 Oct', s:'Derivatives basics (MATH101 week 5)' },
  { t:'The derivative as a rate of change', d:'20 Oct', s:'Derivatives basics (MATH101 week 5)' },
];
const PASSED = [
  { t:'Time of flight', topic:'Range', d:'6 Nov', s:'Projectile motion', note:'opens at the check: a check is open there' },
  { t:'Implicit y terms', topic:'Implicit differentiation', d:'8 Nov', s:'Implicit differentiation (MATH101 week 7)', note:'' },
];
const ALLOW = [
  { n:'Organic chem full textbook.pdf', mb:88, s:'Organic chemistry notes' },
  { n:'Physics lab videos stills.pdf', mb:41, s:'Projectile motion' },
  { n:'MATH101 week 6.pdf', mb:24, s:'Chain rule (MATH101 week 6)' },
  { n:'Lecture 8 slides.pptx', mb:9, s:'Implicit differentiation (MATH101 week 7)' },
  { n:'... 9 smaller files', mb:30, s:'' },
];
const JUMPS = ['Topic: Implicit differentiation', 'Diagnostic', 'Objective 1: y terms', 'Objective 2: dy/dx', 'Objective 1 again', 'Mastery check: result'];
const TEACH = [
  { t:'tutor', h:'Differentiate both sides with respect to x, <a class="alink" data-act="viewer">as on slide 30</a> of Lecture 8. The y² term becomes 2y · dy/dx. Your turn: differentiate x² + y² = 25.' },
  { t:'me', h:'2x + 2y dy/dx = 0' },
  { t:'tutor', h:'Right. Now get dy/dx on its own.' },
];
const SEALMSG = `<b>This session is sealed.</b> Nobody can open it, including Crux's owner. Your other sessions keep working. Please don't upload that file again. To reply, answer the email from Crux and quote flag 4821. ${NS}`;
