// ---------- PROTOTYPE, throwaway (#771). Nothing here is production code. ----------
const R = String.raw;
const SCENES = {
  stream: { name:'1. While a reply arrives', opts:{
    A:{ name:'Word by word', note:'The reply shows word by word as it arrives. A maths piece and a picture show once they are complete, so no raw LaTeX shows (switch "Raw maths" on to see what holding them back prevents).' },
    B:{ name:'A paragraph at a time', note:'Each paragraph shows whole once it has fully arrived. The learner sees "The tutor is writing..." under the last one until the next.' },
    C:{ name:'Whole when done', note:'Nothing shows until the whole reply has arrived; "The tutor is writing..." shows meanwhile. The first word on screen then comes after the whole reply is written, not within the 5 seconds (README "the tutor starts replying within about 5 seconds"): a recorded change.' } } },
  brk: { name:'2. When a reply breaks partway', opts:{
    A:{ name:'Crux finishes it by itself', note:'No tap needed. A lost connection shows a reconnecting line under the words so far; when the phone is back, the finished reply shows whole. Crux either finishes the same reply or answers again as a background answer (hosting.md); which one is left to the build. If Crux itself fails partway, the words so far go and the tutor answers again from the start.' },
    B:{ name:'Keep the words, offer Try again', note:'What arrived stays, faded, with "The reply was cut off" and a Try again button. Try again asks the model again, and the new reply replaces the cut one. Nothing is saved until a reply finishes. Departs from README\'s "a reply is never cut off midway": a recorded change.' },
    C:{ name:'Remove the words, offer Try again', note:'What arrived is removed, and the learner\'s message shows "No reply" with a Try again button. Try again asks the model again. Matches how a reply Google blocks is removed (ai-layer.md), but the learner has to tap.' } } },
  maths: { name:'3. How maths shows', opts:{
    A:{ name:'Drawn maths; a long line scrolls sideways', note:'The tutor writes LaTeX and the screen draws it with KaTeX. A display equation too wide for the screen scrolls sideways inside its own box; the box can take keyboard focus (needed for the axe check).' },
    B:{ name:'Drawn maths; a long line breaks', note:'As A, but a long display equation breaks after = or + onto the next line (KaTeX\'s documented CSS). Aligned working cannot break, so a too-wide line of it still scrolls.' },
    C:{ name:'Plain text maths, nothing drawn', note:'No maths library on the screen. The tutor writes maths in plain characters: x², √(…), a/b. Lines wrap like words. SymPy and the tools still read LaTeX, which the tutor sends separately (ai-layer.md).' } } },
};
const ORDER = ['stream','brk','maths'];
const qp = new URLSearchParams(location.search);
let scene = ORDER.includes(qp.get('scene')) ? qp.get('scene') : 'stream';
let opt = (qp.get('opt')||'A').toUpperCase(); if (!SCENES[scene].opts[opt]) opt = 'A';
let device = ['phone','small','desktop'].includes(qp.get('device')) ? qp.get('device') : 'phone';
let speed = ['slow','typical','fast'].includes(qp.get('speed')) ? qp.get('speed') : 'typical';
let cause = ['net','server','block'].includes(qp.get('cause')) ? qp.get('cause') : 'net';
let raw = qp.get('raw') === '1';
let mathsOpt = (qp.get('mathsopt')||'A').toUpperCase(); if (!'ABC'.includes(mathsOpt)) mathsOpt = 'A';
const WPS = { slow:8, typical:25, fast:60 };   // words per second: guesses, not measured
const FIRST_WORD_MS = 1500;                     // guess: time to the first word
const BREAK_AT = 0.45;                          // the break happens 45% into the reply

// ---------- the reply ----------
const REPLY = [
  { t:'p', s:"Good, you've got the outer part. Now the inner part: with $u = 3x^2 + 1$, the chain rule gives" },
  { t:'d', s:R`\frac{d}{dx}\left(3x^2+1\right)^5 = 5\left(3x^2+1\right)^4 \cdot \frac{d}{dx}\left(3x^2+1\right) = 5\left(3x^2+1\right)^4 \cdot 6x = 30x\left(3x^2+1\right)^4`,
    u:'d/dx (3x² + 1)⁵ = 5(3x² + 1)⁴ · d/dx (3x² + 1) = 5(3x² + 1)⁴ · 6x = 30x(3x² + 1)⁴' },
  { t:'p', s:"So the slope is the outer derivative times $\\frac{du}{dx}$. Here is the same idea on a curve you know: $y = x^2$ and its tangent at $x = 1$." },
  { t:'g' },
  { t:'p', s:"**Your turn:** differentiate $y = \\sqrt{2x^3 - x}$. Write each step." },
];
// unicode twins for option C of the maths scene
const UNI = { 'u = 3x^2 + 1':'u = 3x² + 1', '\\frac{du}{dx}':'du/dx', 'y = x^2':'y = x²', 'x = 1':'x = 1', 'y = \\sqrt{2x^3 - x}':'y = √(2x³ − x)' };

function km(tex, display) {
  try { return katex.renderToString(tex, { displayMode:display, throwOnError:true, output:'htmlAndMathml' }); }
  catch (e) { console.error('KaTeX', e.message); return '<span class="rawtex">'+tex+'</span>'; }
}
function inl(s, mode) { // inline text with $..$ maths and **bold**
  return s.split(/(\$[^$]+\$)/).map(part => {
    if (part.startsWith('$')) { const tex = part.slice(1,-1); return mode==='C' ? '<span class="uni">'+(UNI[tex]||tex)+'</span>' : km(tex,false); }
    return part.replace(/\*\*([^*]+)\*\*/g,'<b>$1</b>');
  }).join('');
}
function graphSVG() {
  const W=260,H=170, X=x=>20+(x+0.5)*(220/3), Y=y=>150-(y+1)*(130/5);
  let pts=[]; for (let i=0;i<=40;i++){ const x=-0.5+i*3/40; pts.push(X(x).toFixed(1)+','+Y(x*x).toFixed(1)); }
  return `<figure><svg viewBox="0 0 ${W} ${H}" style="width:100%;max-width:${W}px;height:auto;display:block" role="img" aria-label="Graph of y = x squared from x = -0.5 to 2.5, with the tangent at x = 1">
    <rect x="0" y="0" width="${W}" height="${H}" fill="#fafbfc" stroke="#e3e6ec"/>
    <line x1="${X(-0.5)}" y1="${Y(0)}" x2="${X(2.5)}" y2="${Y(0)}" stroke="#9aa3b5"/><line x1="${X(0)}" y1="${Y(-1)}" x2="${X(0)}" y2="${Y(4)}" stroke="#9aa3b5"/>
    <polyline points="${pts.join(' ')}" fill="none" stroke="#2f5bea" stroke-width="2"/>
    <line x1="${X(0)}" y1="${Y(-1)}" x2="${X(2.5)}" y2="${Y(4)}" stroke="#c27c0e" stroke-width="2" stroke-dasharray="5 3"/>
    <circle cx="${X(1)}" cy="${Y(1)}" r="4" fill="#c27c0e"/></svg>
    <figcaption>y = x², with its tangent at x = 1 (slope 2)</figcaption></figure>`;
}
// tokens: each word is one token; an inline maths piece is one token; a display piece is one token
function tokens() {
  const out = [];
  REPLY.forEach((b,bi) => {
    if (b.t==='p') b.s.split(/(\$[^$]+\$)/).forEach(part => {
      if (part.startsWith('$')) out.push({bi, kind:'m', s:part, w:Math.max(2, Math.round(part.length/4))});
      else part.split(/(?<=\s)/).filter(Boolean).forEach(w => out.push({bi, kind:'w', s:w, w:1}));
    });
    if (b.t==='d') out.push({bi, kind:'d', s:b.s, w:Math.round(b.s.length/4)});
    if (b.t==='g') out.push({bi, kind:'g', w:12});
  });
  return out;
}
const TOK = tokens();
const TOTAL_W = TOK.reduce((a,t)=>a+t.w,0);
// html of the reply with the first `n` word-units arrived. partial = how far into the current token
function replyHTML(units, mode) {
  let html = '', used = 0, open = null;
  const blocks = REPLY.map(()=>[]); let lastBi = -1, waiting = null;
  for (const t of TOK) {
    if (used >= units) break;
    const have = Math.min(t.w, units-used); used += t.w; lastBi = t.bi;
    const done = have >= t.w;
    if (t.kind==='w') blocks[t.bi].push(t.s.replace(/\*\*/g,''));
    else if (t.kind==='m') { if (done) blocks[t.bi].push(inl(t.s,'A')); else if (raw) blocks[t.bi].push('<span class="rawtex">'+t.s.slice(0, Math.ceil(t.s.length*have/t.w))+'</span>'); else waiting='m'; }
    else if (t.kind==='d') { if (done) blocks[t.bi].push(km(t.s,true)); else if (raw) blocks[t.bi].push('<div class="rawtex">'+t.s.slice(0, Math.ceil(t.s.length*have/t.w))+'</div>'); else waiting='d'; }
    else if (t.kind==='g') { blocks[t.bi].push(done ? graphSVG() : '<div class="picwait">Checking the graph<span class="dots"></span></div>'); }
  }
  REPLY.forEach((b,bi) => { if (!blocks[bi].length) return; html += b.t==='p' ? '<p>'+blocks[bi].join('')+(bi===lastBi?'<span class="caret"></span>':'')+'</p>' : blocks[bi].join(''); });
  return html;
}
function fullHTML(mode) { // whole reply, drawn per maths option
  return REPLY.map(b => b.t==='p' ? '<p>'+inl(b.s,mode)+'</p>' : b.t==='d' ? (mode==='C' ? '<span class="uni disp">'+b.u+'</span>' : km(b.s,true)) : graphSVG()).join('');
}
// paragraph-at-a-time: blocks fully arrived by `units`
function blocksDone(units) {
  let used=0, done=-1;
  REPLY.forEach((b,bi) => { const w = TOK.filter(t=>t.bi===bi).reduce((a,t)=>a+t.w,0); used+=w; if (used<=units) done=bi; });
  return done;
}

