// PROTOTYPE, throwaway (calmxz/Crux#780). Sample sessions for one learner whose clock is New York time.
// Today is 16 Nov. Dates are the learner's own clock, with no time (#772).
// Each session: nm name, now ("On: ..." / "Mastered last: ..."), last (last visit label), lastN (sort key),
// started (label), startN, mastered (count on the Record), pr (progress), badge, topics, files, msgs.
// msgs: { who:'tutor'|'me', t: stored text (tutor maths stays LaTeX, as #771 decided), hide:'check' (earlier
// teaching hidden while a check is open), wait:true (marked as waiting), blocked:true (Google blocked it) }.
const NS = '<span class="nospec">[draft wording]</span>';
const SESSIONS = [
  { id:'impl', nm:'Implicit differentiation (MATH101 week 7)', now:'On: Implicit differentiation', last:'Today', lastN:316, started:'12 Nov', startN:312, mastered:0, pr:[1,4],
    topics:['Implicit differentiation','Related rates (queued)'], files:['MATH101 week 7.pdf','Lecture 8 slides.pptx'],
    msgs:[ {who:'tutor', t:'Differentiate both sides with respect to x. The $y^2$ term becomes $2y \\cdot dy/dx$, as on slide 30 of Lecture 8.'},
           {who:'me', t:'so 2x + 2y dy/dx = 0'} ] },
  { id:'chain', nm:'Chain rule (MATH101 week 6)', now:'Mastered last: The chain rule', last:'Yesterday', lastN:315, started:'3 Nov', startN:303, mastered:2, badge:['wait','1 waiting'],
    topics:['The chain rule','Index laws'], files:['MATH101 week 6.pdf'],
    msgs:[ {who:'tutor', t:'Picture a balloon whose radius grows at 2 cm per second. How fast is the volume changing when r = 5?'},
           {who:'me', t:'can you go over the balloon example again', wait:true} ] },
  { id:'phys', nm:'Projectile motion', now:'On: Range', last:'14 Nov', lastN:314, started:'6 Nov', startN:306, mastered:0, pr:[3,4], badge:['chk','Check open'],
    topics:['Range','Time of flight'], files:[],
    msgs:[ {who:'tutor', t:'A ball thrown at 20 m/s and 30 degrees stays up for $2v\\sin\\theta / g$, about 2 seconds.', hide:'check'},
           {who:'me', t:'so the ball lands after 2 seconds?', hide:'check'},
           {who:'tutor', t:'Problem 2 of 4: how far does it travel before it lands?'} ] },
  { id:'photo', nm:'photosynthesis for my bio quiz', now:'', last:'13 Nov', lastN:313, started:'13 Nov', startN:313, mastered:0,
    topics:[], files:[], msgs:[ {who:'me', t:'photosynthesis for my bio quiz on friday'} ] },
  { id:'new', nm:'New session', now:'', last:'11 Nov', lastN:311, started:'11 Nov', startN:311, mastered:0, topics:[], files:[], msgs:[] },
  { id:'org', nm:'Organic chemistry notes', now:'On: Naming alkanes', last:'10 Nov', lastN:310, started:'1 Nov', startN:301, mastered:0, pr:[1,3], badge:['hold','Remove a file to continue'],
    topics:['Naming alkanes'], files:['Alkanes handout.pdf','reagents.pdf'],
    msgs:[ {who:'tutor', t:'An alkane with five carbons in a chain is pentane.'},
           {who:'me', t:'[a message Google blocked]', blocked:true} ] },
  { id:'stats', nm:'Statistics: confidence intervals', now:'Mastered last: Margin of error', last:'7 Nov', lastN:307, started:'4 Nov', startN:304, mastered:1, ny:true,
    topics:['Margin of error','Confidence intervals'], files:['STAT200 notes.pdf'],
    msgs:[ {who:'tutor', t:'A 95% interval means the method catches the true mean 95 times in 100.'} ] },
  { id:'seal', nm:'Reaction rates', now:'', last:'1 Nov', lastN:301, started:'20 Oct', startN:289, mastered:1, badge:['seal','Sealed'], sealed:true,
    topics:['Rate of reaction'], files:['lab sheet.pdf'],
    msgs:[ {who:'tutor', t:'The rate of change of concentration tells you how fast a balloon of gas fills.'} ] },
  { id:'bio', nm:'Cell respiration (BIO110)', now:'Mastered last: Glycolysis', last:'30 Oct', lastN:299, started:'25 Oct', startN:294, mastered:2,
    topics:['Glycolysis','The Krebs cycle'], files:['BIO110 ch 9.pdf'],
    msgs:[ {who:'tutor', t:'Glycolysis splits one glucose into two pyruvate.'} ] },
  { id:'prod', nm:'Product rule', now:'Mastered last: The product rule', last:'28 Oct', lastN:297, started:'27 Oct', startN:296, mastered:1,
    topics:['The product rule (without quotient-rule shortcuts)'], files:[],
    msgs:[ {who:'tutor', t:'For $x^2 \\sin x$, the product rule gives $2x \\sin x + x^2 \\cos x$.'} ] },
  { id:'limits', nm:'Limits and continuity', now:'On: One-sided limits', last:'26 Oct', lastN:295, started:'24 Oct', startN:293, mastered:0, pr:[2,5],
    topics:['One-sided limits'], files:[], msgs:[ {who:'tutor', t:'As x approaches 0 from the right, 1/x grows without bound.'} ] },
  { id:'basic', nm:'Derivatives basics (MATH101 week 5)', now:'Mastered last: The power rule', last:'22 Oct', lastN:291, started:'15 Oct', startN:284, mastered:2,
    topics:['The power rule','The derivative as a rate of change'], files:['MATH101 week 5.pdf'],
    msgs:[ {who:'tutor', t:'The derivative of x² is 2x: the slope doubles as x doubles.'} ] },
  { id:'chainold', nm:'Chain rule (MATH101 week 6)', now:'On: The chain rule', last:'18 Oct', lastN:287, started:'18 Oct', startN:287, mastered:0, pr:[1,3],
    topics:['The chain rule'], files:[], msgs:[ {who:'tutor', t:'Start with the outside function.'} ] },
  { id:'seal2', nm:'Sealed session', now:'', last:'4 Oct', lastN:273, started:'4 Oct', startN:273, mastered:0, badge:['seal','Sealed'], sealed:true, unnamed:true,
    topics:[], files:[], msgs:[ {who:'me', t:'[a request Google blocked, first words never shown: "synthesis route for"]', blocked:true} ] },
];
// Day numbers: 1 Aug = 209, 1 Sep = 240, 1 Oct = 270, 1 Nov = 301; today (16 Nov) = 316.
function dayLabel(n) { for (const [m, s] of [['Nov',301],['Oct',270],['Sep',240],['Aug',209]]) if (n >= s) return `${n - s + 1} ${m}`; }
// Filler so the list is long; each has a name, a line and dates only.
[['Vectors in 3D','Mastered last: Dot product',268,1],['Integration by parts','On: Choosing u',262,0],['Spanish past tense','Mastered last: Preterite',255,1],
 ['Python list comprehensions','Mastered last: Filters',249,1],['Supply and demand','',244,0],['Kinematics','Mastered last: Displacement',240,2],
 ['Probability basics','On: Independent events',233,0],['Linear equations','Mastered last: Two-step equations',229,1],['Ohm\'s law','',220,0],
 ['French revolution causes','Mastered last: The Estates-General',214,1]].forEach(([nm, now, n, m], i) => {
  const lbl = dayLabel(n);
  SESSIONS.push({ id:'f' + i, nm, now, last: lbl, lastN:n, started: lbl, startN:n, mastered:m, topics: now ? [now.replace(/^(On|Mastered last): /, '')] : [], files:[], msgs:[] });
});
const TOTAL = SESSIONS.length;
const SEALMSG = `<b>This session is sealed.</b> Nobody can open it, including Crux's owner. Your other sessions keep working. Please don't upload that file again. To reply, email Crux at its address and quote flag 4821.`;
