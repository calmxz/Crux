// PROTOTYPE, throwaway (calmxz/Crux#754). Part of 754-landing.html; see that file's header.
// Guest mode inside the app shell. The session screen is #751's, held fixed; these scenes look the same in
// every variant, apart from the reply count's place (gap question) and where a guest lands after an ending.
const OWNT = `<div class="msg me">slope of a line</div>
  <div class="msg tutor"><div class="who">Tutor</div>Here's what we'll cover:<br>1. Read a slope from a graph<br>2. Write y = mx + b from two points<br>3. Explain what the slope means<br>Say "go" to start, or change any of these.</div>
  <div class="msg me">go</div><div class="divider">Objective 1: Read a slope from a graph</div>
  <div class="msg tutor"><div class="who">Tutor</div>A line passes through (0, 1) and (2, 5). How much does y go up when x goes up by 1?</div>`;
const vidLine = () => `<div style="align-self:center;width:300px">${video()}</div>`;
const SAMPLET = `<div class="divider">Sample topic: ${SAMPLES[0].t}</div>
  <div class="msg tutor"><div class="who">Tutor</div>We'll learn to solve equations like 3x + 4 = 19 in two steps. First: what could you do to both sides to get 3x on its own?</div>
  <div class="msg me">take away 4</div><div class="msg tutor"><div class="who">Tutor</div>Right: 3x = 15. Now the second step?</div>`;
const sampleRail = (st = ['ip', 'In progress']) => ({ topic: SAMPLES[0].t, objs: [[st[0], st[1], 'Solve ax + b = c in two steps']], foot: `<div class="sub" style="margin-top:12px">Sample topic: nothing is saved. ${NS}</div>` });
const COUNT = n => `${n} of 10 replies left ${NS}`;
const GS = {
  under: (v, p) => gapp(p, gsession(p, { thread: OWNT, count: COUNT(7), strip: '0 of 3' }), { cur: 'Slope of a line' }),
  limit: (v, p) => gapp(p, gsession(p, { count: COUNT(0), thread: OWNT + `<div class="msg me">4</div><div class="msg tutor"><div class="who">Tutor</div>Yes, the slope is 2. That's objective 1 shown.</div>
    <div class="sysline warn">That's the end of guest mode for your own topic<div class="row" style="justify-content:center"><span class="btn small">${SAMPLES[0].t}</span><span class="btn small">${SAMPLES[1].t}</span><span class="btn small">${SAMPLES[2].t}</span><span class="btn small primary">Request access</span></div></div>`,
    comp: { off: 'Your own topic has used its 10 replies. ' + NS } }), { cur: 'Slope of a line' }),
  sample: (v, p) => gapp(p, gsession(p, { title: SAMPLES[0].t, thread: SAMPLET, strip: '0 of 1', rail: sampleRail() }), { sample: 0 }),
  mini: (v, p) => gapp(p, gsession(p, { title: SAMPLES[0].t, checkbar: `<div class="checkbar"><span>Mini check &middot; Problem 1 of 2 &middot; closed book ${NS}</span></div>`,
    thread: `<div class="msg tutor"><div class="who">Problem 1</div>Solve 5x &minus; 7 = 18. Show your working.</div><div class="msg me">5x = 25, so x = 5</div><div class="marking">Marking<span class="dots"></span></div>`,
    comp: { ph: 'Your answer' }, rail: sampleRail(['sh', 'Shown']) }), { sample: 0 }),
  result: (v, p) => gapp(p, gsession(p, { title: SAMPLES[0].t, rail: sampleRail(['pa', 'Passed']),
    thread: `<div class="divider">Mini check: result ${NS}</div><div class="card" style="align-self:stretch;max-width:520px"><div class="h"><span class="ok">Pass</span> &middot; 2 of 2</div>
      <ul class="marks"><li><span class="ok">Right</span> Problem 1: 5x &minus; 7 = 18 <details><summary>Model answer</summary><div class="model">5x = 25, x = 5</div></details></li><li><span class="ok">Right</span> Problem 2: 2x + 9 = 1</li></ul>
      <div class="sub" style="margin-top:8px">A sample topic earns nothing, and nothing is saved. ${NS}</div></div>
      <div class="sysline">That's the sample. Try another, try your own topic, or ask for a trial link. ${NS}<div class="row" style="justify-content:center"><span class="btn small">Another sample</span><span class="btn small">Your own topic</span><span class="btn small primary">Request access</span></div></div>` }), { sample: 0 }),
  upload: (v, p) => gapp(p, gsession(p, { thread: OWNT, count: COUNT(7), strip: '0 of 3',
    comp: { pins: `<div class="pin warn" style="display:flex;gap:8px;align-items:center"><span style="flex:1">${UPLOAD}</span><span class="btn small primary">Request access</span><span class="link">Dismiss</span></div>` } }), { cur: 'Slope of a line' }),
  age: (v, p) => gapp(p, gsession(p, { count: COUNT(6), thread: OWNT + `<div class="msg me">idk im only 15 lol</div><div class="card" style="align-self:center;max-width:340px"><b>Crux is for people 18 and over. Are you under 18?</b><div class="row"><span class="btn">Yes</span><span class="btn">No</span></div></div>` }), { cur: 'Slope of a line' }),
  block: (v, p) => gapp(p, gsession(p, { count: COUNT(6), thread: OWNT + `<div class="msg me">[a message Google blocks as prohibited content]</div><div class="sysline stop">The tutor can't help with this, so this guest session has ended. ${NS}</div>`,
    comp: { off: 'This guest session has ended. <a>Back to the start</a> ' + NS } }), { cur: 'Slope of a line' }),
  stopday: (v, p) => gapp(p, gsession(p, { count: COUNT(5), thread: OWNT + `<div class="msg me">is it 2?</div><div class="sysline stop">${DAY}</div>${vidLine()}`, comp: { off: DAY } }), { cur: 'Slope of a line' }),
  stopcare: (v, p) => gapp(p, gsession(p, { count: COUNT(5), thread: OWNT + `<div class="msg me">i cant do this anymore, i dont want to be here</div><div class="sysline stop">${DAY}</div>
    <div class="sysline care">[the care line: the build ticket drafts it for the owner]<br>Philippines: call 1553. Elsewhere: findahelpline.com</div>${vidLine()}`, comp: { off: DAY } }), { cur: 'Slope of a line' }),
  stopmini: (v, p) => gapp(p, gsession(p, { title: SAMPLES[0].t, checkbar: `<div class="checkbar"><span>Mini check &middot; Problem 2 of 2 &middot; closed book ${NS}</span></div>`, rail: sampleRail(['sh', 'Shown']),
    thread: `<div class="msg tutor"><div class="who">Problem 2</div>Solve 2x + 9 = 1. Show your working.</div><div class="msg me">2x = -8, x = -4</div><div class="sysline stop">${DAY}</div>${vidLine()}`, comp: { off: DAY } }), { sample: 0 }),
  stopgoogle: (v, p) => gapp(p, gsession(p, { title: SAMPLES[0].t, rail: sampleRail(['sh', 'Shown']),
    thread: `<div class="msg tutor"><div class="who">Problem 2</div>Solve 2x + 9 = 1. Show your working.</div><div class="msg me">2x = -8, x = -4</div><div class="sysline stop">${MONTH}<br>Your mini check was dropped. ${NS}</div>${vidLine()}`, comp: { off: MONTH } }), { sample: 0 }),
  pausedin: (v, p) => gapp(p, gsession(p, { count: COUNT(5), thread: OWNT + `<div class="msg me">is it 2?</div><div class="sysline warn">Guest mode is paused while we fix something. ${NS}</div>${vidLine()}`, comp: { off: 'Guest mode is paused. ' + NS } }), { cur: 'Slope of a line' }),
};
