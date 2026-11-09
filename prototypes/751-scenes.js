// ---------- shared data: one learner (Mara), one topic, spec wording ----------
const TOPIC = 'The chain rule for polynomials';
const FILE = 'MATH101 week 6 slides.pdf';
const OBJ = [
  { n:1, t:'Spot the inside and outside of a composite' },
  { n:2, t:'Differentiate a two-layer composite' },
  { n:3, t:'Differentiate a composite inside a power, (ax^n + b)^m' },
  { n:4, t:'Explain why the inside\'s derivative multiplies' },
  { n:5, t:'Three-layer composites' },
];
const LBL = { ns:'not started', ip:'in progress', sh:'shown', pa:'passed', dr:'dropped' };
const PREFS = ['Use real-world examples', 'Shorter steps'];
const PAUSED = { name:'Exponent rules', note:'prerequisite, paused: 1 of 3 shown' };

const S = {}; // scenes
const t = (h) => ({ t:'tutor', h });
const me = (h, wait) => ({ t:'me', h, wait });
const sys = (h, k='info') => ({ t:'sys', h, k });
const lab = (h) => ({ t:'label', h });
const NS = '<span class="nospec">[no spec wording]</span>';

S.teach = { name:'1. Teaching, with objectives and statuses', mode:'teach',
  st:{1:'pa',2:'sh',3:'ip',4:'ns',5:'dr'}, trouble:{3:true}, paused:true,
  items:[
    { t:'objectives' },
    t('You passed spotting the inside and outside in your physics session on 25 Nov. Here it\'s the first step of every chain-rule problem, so we\'ll need it. Want a quick problem to skip the teaching, or shall I teach it as usual?'),
    me('quick problem'),
    t('Fresh one: in y = (4x - 1)^3, what is the inside?'),
    me('4x - 1, and the outside is u^3'),
    t('Right, and you named both parts. Now objective 3, as on slide 30. Slide 30 looks like it has a typo: it drops the 6x ... worth checking with your teacher. Try this: differentiate (3x^2 + 1)^5. What\'s the inside\'s derivative?'),
    me('6x, so 5(3x^2+1)^4 * 6x = 30x(3x^2+1)^4'),
    t('That\'s right, and your working shows each step. Since objective 3 gave you trouble earlier, it needs 2 fresh problems in a row with no help. Here\'s the second: differentiate (x^3 - 2)^4.'),
  ]};

S.stuck = { name:'2. Never ready, and a picture', mode:'teach',
  st:{1:'pa',2:'sh',3:'ip',4:'ns',5:'dr'}, trouble:{3:true},
  items:[
    t('That\'s 3 misses on objective 3. What\'s not clicking?'),
    me('idk it just doesn\'t'),
    t('Here\'s the pattern I see: every answer forgets the inside\'s derivative. You get 4(x^3 - 2)^3 and stop. What would help?'),
    { t:'menu', items:[
      ['Explain it a completely different way', 'recommended'],
      ['Check for a missing basic'], ['Drop this objective'], ['Stop for now'] ] },
    me('1'),
    t('Which way would you like? Simpler words, a picture, or a real-world example (your preference)?'),
    me('a picture'),
    { t:'picture' },
  ]};

S.offer = { name:'3. The check offer', mode:'teach',
  st:{1:'pa',2:'sh',3:'sh',4:'sh',5:'dr'}, trouble:{3:true},
  items:[
    t('That\'s objective 4 shown. Every objective is shown, so you\'re ready for the mastery check.'),
    t('6 problems: 1 each on objectives 1 and 2, 2 each on objectives 3 and 4. Closed book: no notes, no searching and no other AI. Ready?'),
    { t:'buttons', b:['Start the check','Not yet'] },
  ]};

S.problem = { name:'4. A check problem, photo answer', mode:'check', k:3, n:6, done:2,
  st:{1:'pa',2:'sh',3:'sh',4:'sh',5:'dr'},
  items:[
    { t:'problem', k:3, n:6, obj:3, h:'Using the chain rule, differentiate y = (2x^3 - 5)^4.' },
    me('24x^2(2x^3-5)^3'),
    t('Please show your working for this one'),
    { t:'photo' },
  ]};

S.marking = { name:'5. Marking, and the end step', mode:'check', k:6, n:6, done:6,
  st:{1:'pa',2:'sh',3:'sh',4:'sh',5:'dr'},
  items:[
    { t:'problem', k:6, n:6, obj:4, h:'Explain why the inside\'s derivative multiplies in d/dx (x^2 + 1)^3.' },
    me('because a small change in x changes the inside by 2x times as much, and the outside responds to the inside, so the rates multiply'),
    { t:'marking' },
    lab('the end step, after the last problem'),
    t('Problem 2 has a slip in the last line. Can you fix it?'),
    t('Walk me through this step'),
  ]};

S.result = { name:'6. The result, model answers, Dispute', mode:'result',
  st:{1:'pa',2:'pa',3:'ip',4:'pa',5:'dr'}, trouble:{3:true},
  items:[
    { t:'result', pass:false },
    t('Objective 3 goes back to teaching. Your next check covers only it, with 2 problems.'),
  ]};

S.mastered = { name:'7. Mastered, and the after-mastery menu', mode:'teach', notice:true,
  st:{1:'pa',2:'pa',3:'pa',4:'pa',5:'dr'},
  items:[
    { t:'result', pass:true },
    t('That\'s the chain rule for polynomials mastered. What next?'),
    { t:'menu', items:[
      ['The product rule (slides 19-27)', 'my pick: next in your slides'],
      ['Implicit differentiation (slides 28-36)'],
      ['Related rates'] ],
      extra:[ 'Finish the chain rule: three-layer composites (you dropped this)',
              'Back to derivatives: implicit differentiation (slides 37-45) <span class="nospec">[shown only after an unrelated topic]</span>' ],
      stop:true },
  ]};

S.back = { name:'8. Back after 9 days, mid-check', mode:'check', k:4, n:6, done:3,
  st:{1:'pa',2:'sh',3:'sh',4:'sh',5:'dr'},
  items:[
    t('Welcome back. You\'re partway through your mastery check, 3 of 6 answered. It\'s been 9 days: continue, or refresh first? You can also ask for a recap of the objectives you\'ve already answered.'),
    { t:'buttons', b:['Continue','Refresh first'] },
    me('[taps Continue]'),
    sys('You left during problem 4, so here\'s a fresh one'),
    { t:'problem', k:4, n:6, obj:3, h:'Using the chain rule, differentiate y = (5x^2 + 3)^6.' },
  ]};

S.limits = { name:'9. Spending limits and a stopped message', mode:'teach',
  st:{1:'pa',2:'sh',3:'ip',4:'ns',5:'dr'},
  items:[
    { t:'popup', k:'warn', h:'You\'ve used 75% of today\'s tutoring. ' + NS },
    t('Good. One more on objective 3: differentiate (2x + 7)^5.'),
    sys('That\'s today\'s tutoring. Answer whenever you like, and the tutor will pick up here tomorrow.', 'stop'),
    me('10(2x+7)^4', 'Waiting: answered when you\'re back tomorrow'),
    sys('You\'ve used today\'s tutoring. Back tomorrow.', 'stop'),
    me('honestly I don\'t want to be here anymore', 'Waiting'),
    sys('Care line ' + NS + '<br><b>Philippines: call 1553. Elsewhere: findahelpline.com</b>', 'care'),
    lab('other limit messages'),
    sys('You\'ve used this week\'s tutoring. Back Monday.', 'stop'),
    sys('Crux is full for today. Back tomorrow.', 'stop'),
    { t:'tick', h:'Crux has used this month\'s tutoring budget. Back on 1 Dec.', tick:'Email me when it\'s back' },
    sys('[after "Start the check" at a full limit] You\'ve used today\'s tutoring. Back tomorrow. Your check is ready when you\'re back', 'stop'),
  ]};

S.faults = { name:'10. Faults, blocks and re-marks', mode:'teach',
  st:{1:'pa',2:'pa',3:'pa',4:'pa',5:'dr'},
  items:[
    lab('a part switched off'),
    sys('Checks are paused while we fix something; your progress is kept', 'warn'),
    me('can we keep going on objective 3?', 'The tutor is down while we fix something. Your message is saved: tap it to try again.'),
    sys('You can dispute this when they\'re back.', 'warn'),
    lab('the AI provider slow or blocking'),
    sys('The tutor is busy right now. Try again in a minute.', 'warn'),
    sys('The tutor couldn\'t answer that. Try asking another way.', 'warn'),
    sys('The tutor can\'t continue that reply', 'warn'),
    sys('We couldn\'t mark that one because our AI provider\'s filter stopped the marking. This doesn\'t count against you. Here\'s a new problem.', 'warn'),
    sys('We couldn\'t check that dispute. Try again later.', 'warn'),
    lab('re-marks after a marking fault'),
    sys('We found a fault in our marking and re-marked your check from 20 Feb. Problem 3 was marked right but isn\'t. Take a check on that objective any time.', 'stop'),
    sys('We found a fault in our marking and re-marked your check from 20 Feb. Problem 2 was marked wrong but is right, so \'chain rule\' is passed.', 'info'),
    sys('A mark in this check changed after a fault in our marking. You\'ll see it in your result.', 'info'),
  ]};

S.age = { name:'11. Age question, misuse holds', mode:'teach',
  st:{1:'pa',2:'sh',3:'ip',4:'ns',5:'dr'},
  items:[
    me('sorry I\'m only 15 so we haven\'t done this in class'),
    { t:'age' },
    me('why?'),
    sys('please tap Yes or No'),
    lab('misuse: a locked account and a sealed session'),
    sys('Your account is locked. ' + NS + ' (says it is locked, and how to reply)', 'stop'),
    sys('This session is sealed. Flag 2041. ' + NS, 'stop'),
  ]};

S.fileflag = { name:'12. Unchecked file error: Q6 options A, B, C (layout A)', mode:'teach', flag:true,
  st:{1:'pa',2:'sh',3:'sh',4:'ip',5:'dr'},
  items:[
    lab('Option B: a fixed line when she opens the session'),
    sys('Reminder: slide 30 may have an error (it drops the 6x). Worth checking with your teacher, then tell me what they said. ' + NS),
    t('Welcome back. Last time we were on objective 4: why the inside\'s derivative multiplies. Ready to pick up?'),
    lab('Option A: see "Files" in the rail (phone: tap the Objectives strip). Option C: see objective 3'),
  ]};

const ORDER = ['teach','stuck','offer','problem','marking','result','mastered','back','limits','faults','age','fileflag'];
