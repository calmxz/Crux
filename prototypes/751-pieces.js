// ---------- shared pieces ----------
function objList(sc, opts={}) {
  return '<ul class="obj">' + OBJ.map(o => {
    const s = sc.st[o.n];
    const tr = sc.trouble && sc.trouble[o.n] && s !== 'pa' ? '<div class="trouble">trouble mark: needs 2 in a row</div>' : '';
    const pl = (s === 'pa' && o.n === 1) ? '<div class="passlink">passed in Physics: projectiles, 25 Nov</div>' : (s === 'pa' ? '<div class="sub">passed 9 Nov</div>' : '');
    const fl = (sc.flag && o.n === 3) ? '<div class="trouble" style="cursor:pointer">Option C: slide 30 may have an error, ask your teacher (tap to tell the tutor)</div>' : '';
    return `<li><span class="st ${s}">${LBL[s]}</span><div><div class="${s==='dr'?'dropped':''}">${o.n}. ${o.t}</div>${tr}${pl}${fl}${s==='dr' && !opts.noPick ? '<span class="btn small">Pick back up</span>' : ''}</div></li>`;
  }).join('') + '</ul>';
}
function prefsHtml() { return PREFS.map(p => `<span class="chip">${p} <b title="Remove">&times;</b></span>`).join(''); }
function pausedHtml() { return `<div class="card" style="margin-top:10px"><div class="sub">Paused topic</div><b>${PAUSED.name}</b> <span class="sub">${PAUSED.note}</span> <span class="btn small">Resume</span></div>`; }
function menuHtml(it) {
  let h = '<ol class="menu">' + it.items.map((m,i) => `<li>${i+1}. ${m[0]}${m[1] ? ` <span class="pick">${m[1]}</span>` : ''}</li>`).join('');
  if (it.extra) h += it.extra.map(e => `<li class="extra">${e}</li>`).join('');
  if (it.stop) h += `<li>${it.items.length+1}. Stop for now</li>`;
  return h + '</ol>';
}
function pictureHtml() {
  return `<figure><svg viewBox="0 0 330 120" width="100%" role="img" aria-label="x feeds the inside, the inside feeds the outside">
    <defs><marker id="ar" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#555"/></marker></defs>
    <rect x="4" y="38" width="44" height="34" rx="6" fill="#eef1f6" stroke="#999"/><text x="26" y="60" text-anchor="middle" font-size="14">x</text>
    <rect x="96" y="30" width="86" height="50" rx="8" fill="#fff8ea" stroke="#c27c0e"/><text x="139" y="52" text-anchor="middle" font-size="12">inside</text><text x="139" y="68" text-anchor="middle" font-size="12">u = x^3 - 2</text>
    <rect x="230" y="30" width="94" height="50" rx="8" fill="#eef2ff" stroke="#2f5bea"/><text x="277" y="52" text-anchor="middle" font-size="12">outside</text><text x="277" y="68" text-anchor="middle" font-size="12">y = u^4</text>
    <line x1="48" y1="55" x2="94" y2="55" stroke="#555" marker-end="url(#ar)"/><line x1="182" y1="55" x2="228" y2="55" stroke="#555" marker-end="url(#ar)"/>
    <text x="71" y="24" text-anchor="middle" font-size="11" fill="#c27c0e">x 3x^2</text><text x="205" y="24" text-anchor="middle" font-size="11" fill="#2f5bea">x 4u^3</text>
    <text x="165" y="110" text-anchor="middle" font-size="12">each gear multiplies: dy/dx = 4u^3 * 3x^2</text></svg>
    <figcaption>Two gears: x turns the inside 3x^2 times as fast; the inside turns the outside 4u^3 times as fast. Your answers stopped after the second gear.</figcaption></figure>`;
}
function resultHtml(it) {
  if (it.pass) return `<div class="card"><div class="h ok">Pass: 2 of 2</div><div class="sub">Check on objective 3, 12 Nov</div>
    <ul class="marks"><li><span class="ok">Right</span> Problem 1 <details><summary>Model answer</summary><div class="model">...</div></details></li>
    <li><span class="ok">Right</span> Problem 2 <details><summary>Model answer</summary><div class="model">...</div></details></li></ul>
    <div class="sub" style="margin-top:6px">Objective 3 passed, 12 Nov. Topic mastered: ${TOPIC}.</div></div>`;
  const R = (k, ok, extra='') => `<li><span class="${ok?'ok':'no'}">${ok?'Right':'Wrong'}</span> Problem ${k}${extra}</li>`;
  const tap = '<details><summary>Model answer</summary><div class="model">Let u = ..., so dy/dx = ... (must contain: the inside named, the inside\'s derivative)</div></details>';
  return `<div class="card"><div class="h no">Not yet: 5 of 6</div><div class="sub">Mastery check, 9 Nov</div><ul class="marks">
    ${R(1,true,tap)}${R(2,true,' <span class="sub">(slip fixed)</span>'+tap)}${R(3,true,tap)}
    ${R(4,false,`<div class="model"><b>Model answer:</b> u = 5x^2 + 3, du/dx = 10x, dy/dx = 6u^5 * 10x = 60x(5x^2+3)^5</div><div class="sub"><b>Missing point:</b> multiply by the inside's derivative, 10x</div><div class="row"><span class="btn small">Dispute</span></div>`)}
    ${R(5,true,tap)}${R(6,true,tap)}</ul>
    <div class="sub" style="margin-top:6px">Objectives 1, 2 and 4 passed, 9 Nov.</div></div>`;
}
function ageHtml() { return `<div class="card"><div class="h">Crux is for people 18 and over. Are you under 18?</div><div class="row"><span class="btn">Yes</span><span class="btn">No</span></div></div>`; }
function tickHtml(it) { return `${it.h}<div style="margin-top:6px"><label><input type="checkbox"> ${it.tick}</label></div>`; }

// generic thread renderer; variants override pieces through `how`
function thread(sc, how) {
  return sc.items.map(it => {
    if (how[it.t]) return how[it.t](it, sc);
    switch (it.t) {
      case 'tutor': return `<div class="msg tutor"><div class="who">Tutor</div>${it.h}</div>`;
      case 'me': return `<div class="msg me">${it.h}${it.wait ? `<span class="wait">&#9203; ${it.wait}</span>` : ''}</div>`;
      case 'sys': return `<div class="sysline ${it.k}">${it.h}</div>`;
      case 'label': return `<div class="label">${it.h}</div>`;
      case 'menu': return `<div class="msg tutor"><div class="who">Tutor</div>${menuHtml(it)}<div class="sub" style="margin-top:6px">Reply with a number, or type something else.</div></div>`;
      case 'picture': return `<div class="msg tutor"><div class="who">Tutor</div>Here it is as gears.${pictureHtml()}Now try (x^3 - 2)^4 again: what does the first gear give you?</div>`;
      case 'buttons': return `<div class="row" style="align-self:flex-start">${it.b.map((b,i)=>`<span class="btn ${i===0?'primary':''}">${b}</span>`).join('')}</div>`;
      case 'problem': return `<div class="msg tutor"><div class="who">Problem ${it.k} of ${it.n} &middot; objective ${it.obj}</div><b>${it.h}</b></div>`;
      case 'photo': return `<div class="msg me" style="background:#fff;border:1px solid var(--line);color:var(--ink)"><div class="photo">photo of working</div><div class="sub">Photo answer</div></div>`;
      case 'marking': return `<div class="marking"><span class="dots">Marking</span></div>`;
      case 'result': return resultHtml(it);
      case 'age': return ageHtml();
      case 'tick': return `<div class="sysline stop">${tickHtml(it)}</div>`;
      case 'popup': return `<div class="sysline ${it.k}">${it.h}</div>`;
      case 'objectives': return '';
    }
    return '';
  }).join('');
}
function composer(sc, extra='') {
  const photo = sc.mode === 'check' ? '<button class="btn">Photo</button>' : '<button class="btn" title="Add a file">+ File</button>';
  return `${extra}<div class="composer">${photo}<input placeholder="${sc.mode==='check'?'Your answer, with working':'Message the tutor'}"><button class="btn primary">Send</button></div>`;
}
function topbar(title, right='') { return `<div class="topbar"><span class="brand">Crux</span><span class="title">${title}</span>${right}</div>`; }
