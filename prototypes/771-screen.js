// ---------- the screen ----------
const LEARNER = "I got 5(3x² + 1)⁴. Is that it?";
function shell(threadHTML, extraRail) {
  const desk = device==='desktop';
  return `<div class="topbar"><span class="brand">Crux</span><span class="title">Chain rule (MATH101 week 6)</span></div>
    ${desk?'':'<div class="strip"><span>Objectives</span><span>2 of 4 ▾</span></div>'}
    <div class="body"><div class="thread" id="thread">${threadHTML}</div>
    ${desk?`<div class="rail"><b>Chain rule</b><div style="font-size:12px;color:var(--mute)">from week6-slides.pdf</div><ol style="padding-left:18px">
      <li>Spot the inner and outer function <span style="color:var(--ok)">shown</span></li><li>Differentiate ${maths()==='C'?'<span class="uni">(3x² + 1)⁵</span>':km('(3x^2+1)^5',false)} and similar <span style="color:#c27c0e">in progress</span></li><li>Chain rule with roots</li><li>Chain rule twice</li></ol>${extraRail||''}</div>`:''}</div>
    <div class="composer"><input placeholder="Reply to the tutor" aria-label="Reply to the tutor"><button class="btn">File</button><button class="btn primary">Send</button></div>`;
}
const maths = () => scene==='maths' ? opt : mathsOpt;
const before = () => `<div class="msg tutor"><div class="who">Tutor</div><p>Try it: what is the derivative of ${maths()==='C'?'<span class="uni">(3x² + 1)⁵</span>':km('(3x^2+1)^5',false)}?</p></div>`;
const mine = (wait) => `<div class="msg me">${LEARNER}${wait?'<span class="wait">'+wait+'</span>':''}</div>`;

let timer = null, t0 = 0, phase = '';
function stop() { if (timer) cancelAnimationFrame(timer); timer = null; }
function play() { stop(); t0 = performance.now(); phase=''; loop(); }
function unitsAt(ms) { return Math.max(0, (ms - FIRST_WORD_MS) / 1000 * WPS[speed]); }

function frameStream(ms) {
  const u = unitsAt(ms), doneAll = u >= TOTAL_W;
  let body = before() + mine(u<=0 ? 'Sending...' : '');
  if (u <= 0) body += '<div class="typing">The tutor is writing<span class="dots"></span></div>';
  else if (opt==='A') body += `<div class="msg tutor"><div class="who">Tutor</div>${doneAll ? fullHTML(mathsOpt) : replyHTML(u)}</div>`;
  else if (opt==='B') { const k = doneAll ? REPLY.length-1 : blocksDone(u);
    if (k>=0) body += `<div class="msg tutor"><div class="who">Tutor</div>${REPLY.slice(0,k+1).map(b=>b.t==='p'?'<p>'+inl(b.s,mathsOpt)+'</p>':b.t==='d'?km(b.s,true):graphSVG()).join('')}</div>`;
    if (!doneAll) body += '<div class="typing">The tutor is writing<span class="dots"></span></div>'; }
  else { body += doneAll ? `<div class="msg tutor"><div class="who">Tutor</div>${fullHTML(mathsOpt)}</div>` : '<div class="typing">The tutor is writing<span class="dots"></span></div>'; }
  const secs = (TOTAL_W / WPS[speed] + FIRST_WORD_MS/1000).toFixed(1);
  status(`t = ${(ms/1000).toFixed(1)} s. The whole reply takes about ${secs} s at ${WPS[speed]} words a second (a guess). ${doneAll?'Done.':''}`);
  return { body, done: doneAll };
}
function frameBreak(ms) {
  const breakU = TOTAL_W*BREAK_AT, breakMs = FIRST_WORD_MS + breakU/WPS[speed]*1000;
  const partial = () => `<div class="msg tutor faded"><div class="who">Tutor</div>${replyHTML(breakU)}</div>`;
  let body = before(), done = false, s = '';
  if (ms < breakMs) { const u = unitsAt(ms); body += mine(u<=0?'Sending...':'') + (u<=0 ? '<div class="typing">The tutor is writing<span class="dots"></span></div>' : `<div class="msg tutor"><div class="who">Tutor</div>${replyHTML(u)}</div>`); s = 'Streaming...'; }
  else if (cause==='block') { // decided in #735, shown for contrast: same under every option
    const after = ms - breakMs - 600;
    body += mine(after<0?'':'');
    if (after < 0) { body += '<div class="typing">The tutor is writing<span class="dots"></span></div>'; s='Google blocked the reply partway (#735): the words are removed and nothing is saved. A hidden retry runs.'; }
    else { const u = after/1000*WPS[speed]; done = u>=TOTAL_W; body += `<div class="msg tutor"><div class="who">Tutor</div>${done?fullHTML('A'):replyHTML(u)}</div>`; s='Decided in #735, the same under every option: removed, then one hidden retry ("Explain in your own words").'; }
  }
  else if (opt==='A') {
    const after = ms - breakMs;
    if (cause==='net') { // learner's connection: backend carries on and saves; screen fetches when back
      if (after < 3500) { body += mine('') + `<div class="msg tutor"><div class="who">Tutor</div>${replyHTML(breakU)}</div><div class="sysline warn"><span class="nospec">Connection lost. Reconnecting...</span></div>`; s='The phone lost signal for 3.5 s. Meanwhile Crux finishes the reply by itself.'; }
      else { body += mine('') + `<div class="msg tutor"><div class="who">Tutor</div>${fullHTML('A')}</div>`; done=true; s='Back online: the screen fetches the finished reply and shows it whole.'; }
    } else { // Crux failed partway: words removed, answered again by itself
      if (after < 1500) { body += mine('Sending...') + '<div class="sysline"><span class="nospec">The reply broke off, so the tutor is starting again.</span></div>'; s='Crux\'s own instance stopped partway: nothing was saved, the words so far are removed.'; }
      else { const u = (after-1500-FIRST_WORD_MS)/1000*WPS[speed]; done = u>=TOTAL_W; body += mine(u<=0?'Sending...':'') + '<div class="sysline"><span class="nospec">The reply broke off, so the tutor is starting again.</span></div>' + (u<=0?'<div class="typing">The tutor is writing<span class="dots"></span></div>':`<div class="msg tutor"><div class="who">Tutor</div>${done?fullHTML('A'):replyHTML(u)}</div>`); s='Answered again from the start, with no tap. The first try\'s words are paid for and thrown away.'; }
    }
  }
  else if (opt==='B') {
    if (phase!=='retry') { body += mine('') + partial() + '<div class="sysline warn"><span class="nospec">The reply was cut off.</span> <button class="btn" data-act="retry">Try again</button></div>'; s = cause==='net' ? 'The phone lost signal. The backend stops too, so when the phone is back there is nothing to fetch.' : 'Crux\'s own instance stopped partway.'; }
    else { const u = unitsAt(ms - retryAt); done = u>=TOTAL_W; body += mine(u<=0?'Sending...':'') + (u<=0?'<div class="typing">The tutor is writing<span class="dots"></span></div>':`<div class="msg tutor"><div class="who">Tutor</div>${done?fullHTML('A'):replyHTML(u)}</div>`); s='Try again: a second model call; the new reply replaces the cut one.'; }
  }
  else {
    if (phase!=='retry') { body += mine('') + '<div class="sysline warn"><span class="nospec">No reply.</span> <button class="btn" data-act="retry">Try again</button></div>'; s = cause==='net' ? 'The phone lost signal. The words so far are removed; nothing was saved.' : 'Crux\'s own instance stopped partway. The words so far are removed.'; }
    else { const u = unitsAt(ms - retryAt); done = u>=TOTAL_W; body += mine(u<=0?'Sending...':'') + (u<=0?'<div class="typing">The tutor is writing<span class="dots"></span></div>':`<div class="msg tutor"><div class="who">Tutor</div>${done?fullHTML('A'):replyHTML(u)}</div>`); s='Try again: a second model call.'; }
  }
  status(`t = ${(ms/1000).toFixed(1)} s. ${s}`);
  return { body, done: done || ((opt!=='A' && cause!=='block') && ms>=breakMs && phase!=='retry') };
}
let retryAt = 0;
function frameMaths() {
  const m = opt;
  const disp = (tex, u) => m==='C' ? '<span class="uni disp">'+u+'</span>' : km(tex,true);
  const aligned = R`\begin{aligned} y &= \sqrt{2x^3 - x} = \left(2x^3 - x\right)^{1/2} \\ y' &= \tfrac{1}{2}\left(2x^3 - x\right)^{-1/2} \cdot \left(6x^2 - 1\right) \\ &= \frac{6x^2 - 1}{2\sqrt{2x^3 - x}} \end{aligned}`;
  const alignedU = 'y = √(2x³ − x) = (2x³ − x)^(1/2)<br>y′ = ½ (2x³ − x)^(−1/2) · (6x² − 1)<br>&nbsp;&nbsp;= (6x² − 1) / (2√(2x³ − x))';
  const f = (tex,u) => m==='C' ? '<span class="uni">'+u+'</span>' : km(tex,false);
  const body = before()
   + `<div class="label">Teaching: a reply with inline maths and a long display equation</div><div class="msg tutor"><div class="who">Tutor</div>${fullHTML(m==='C'?'C':'A')}</div>`
   + `<div class="label">Teaching: worked steps on aligned lines</div><div class="msg tutor"><div class="who">Tutor</div><p>Here is how a root goes:</p>${disp(aligned, alignedU)}<p>The ${f(R`\tfrac12`,'½')} comes down, and the power drops by one to ${f('-1/2','−1/2')}.</p></div>`
   + `<div class="label">Mastery check: a problem (shown whole, never streamed)</div><div class="checkbar">Mastery check · Problem 2 of 4 · closed book</div><div class="msg tutor"><div class="who">Tutor</div><p>Differentiate ${f(R`y = \frac{1}{\left(4 - x^2\right)^3}`,'y = 1 / (4 − x²)³')}. Show your working.</p></div>`
   + `<div class="label">The result card: a wrong problem's model answer</div><div class="card"><b>Not yet · 3 of 4</b><div style="margin-top:6px">Problem 2 <span style="color:#b42318;font-weight:600">✗</span></div><div class="model">Model answer: ${f(R`y' = \frac{6x}{\left(4 - x^2\right)^4}`,'y′ = 6x / (4 − x²)⁴')}<br><span style="font-size:12px">Missing point: the minus sign from the inner derivative ${f('-2x','−2x')}.</span></div></div>`
   + `<div class="label">The mistake mark on a file (spec example, learning-screen.md)</div><div class="mark"><b>Slide 30 may have a mistake.</b> It shows ${f(R`5\left(3x^2+1\right)^4`,'5(3x² + 1)⁴')}. A possible correction is ${f(R`5\left(3x^2+1\right)^4 \cdot 6x`,'5(3x² + 1)⁴ · 6x')}, but it could be wrong too. Ask your teacher, then tell the tutor what they said.</div>`;
  status(device==='desktop' ? 'Desktop: the rail on the right also holds maths in an objective name.' : 'Phone: scroll the thread. Each label names a surface where maths shows.');
  return { body, done:true };
}
function status(s) { document.getElementById('status').textContent = s; }

function loop() {
  const ms = performance.now() - t0;
  const fr = scene==='stream' ? frameStream(ms) : scene==='brk' ? frameBreak(ms) : frameMaths();
  const th = document.getElementById('thread');
  const atEnd = th.scrollHeight - th.scrollTop - th.clientHeight < 40;
  th.innerHTML = fr.body;
  th.className = 'thread ' + ({A:'m-scroll',B:'m-wrap',C:''}[maths()]);
  th.querySelectorAll('.katex-display').forEach(el => { el.tabIndex = 0; el.setAttribute('role','group'); });
  th.querySelectorAll('[data-act="retry"]').forEach(el => el.onclick = () => { phase='retry'; retryAt = performance.now()-t0; if (!timer) loop(); });
  if (scene!=='maths' && atEnd) th.scrollTop = th.scrollHeight;
  timer = fr.done ? null : requestAnimationFrame(loop);
}

function render() {
  stop();
  const sc = SCENES[scene], o = sc.opts[opt];
  const d = document.getElementById('device');
  d.className = 'device ' + device;
  d.innerHTML = shell('');
  const btn = (k,v,cur,lab) => `<button data-k="${k}" data-v="${v}" class="${cur===v?'on':''}">${lab}</button>`;
  document.getElementById('bar').innerHTML =
    `<select id="sc">${ORDER.map(k=>`<option value="${k}" ${k===scene?'selected':''}>${SCENES[k].name}</option>`).join('')}</select>
     <span class="grp">Option ${Object.keys(sc.opts).map(k=>btn('opt',k,opt,k)).join('')}</span>
     <span class="grp">${btn('device','phone',device,'Phone 390')}${btn('device','small',device,'Phone 320')}${btn('device','desktop',device,'Desktop')}</span>
     ${scene!=='maths'?`<span class="grp">Speed ${btn('speed','slow',speed,'8/s')}${btn('speed','typical',speed,'25/s')}${btn('speed','fast',speed,'60/s')}</span>`:''}
     ${scene==='stream'&&opt==='A'?`<span class="grp">${btn('raw', raw?'0':'1', 'x', raw?'Raw maths: on':'Raw maths: off')}</span>`:''}
     ${scene==='brk'?`<span class="grp">Cause ${btn('cause','net',cause,'Phone loses signal')}${btn('cause','server',cause,'Crux fails')}${btn('cause','block',cause,'Google blocks (decided)')}</span>`:''}
     ${scene!=='maths'?'<button id="replay">Replay</button>':''}`;
  document.getElementById('note').innerHTML = `<p><b>PROTOTYPE, throwaway (#771).</b> ${sc.name} · <b>Option ${opt}: ${o.name}.</b> ${o.note}</p><p style="color:var(--mute)" id="status"></p><p style="font-size:12px;color:var(--mute)">Red italic text has no spec wording yet (draft). Speeds are guesses, not measured.</p>`;
  const u = new URL(location); u.searchParams.set('scene',scene); u.searchParams.set('opt',opt); u.searchParams.set('device',device);
  ['speed','cause','raw'].forEach(k=>u.searchParams.delete(k));
  if (scene!=='maths') u.searchParams.set('speed',speed);
  if (scene==='brk') u.searchParams.set('cause',cause);
  if (scene==='stream' && raw) u.searchParams.set('raw','1');
  history.replaceState(null,'',u);
  document.getElementById('sc').onchange = e => { scene = e.target.value; opt='A'; render(); };
  document.querySelectorAll('.bar [data-k]').forEach(b => b.onclick = () => {
    const k=b.dataset.k, v=b.dataset.v;
    if (k==='opt') opt=v; if (k==='device') device=v; if (k==='speed') speed=v; if (k==='cause') cause=v; if (k==='raw') raw = v==='1';
    render(); });
  const rp = document.getElementById('replay'); if (rp) rp.onclick = play;
  play();
}
render();
