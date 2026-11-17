/* PROTOTYPE, throwaway (calmxz/Crux#779). State lives in the address, so every view has its own link.
   Plan: every screen in both themes, one switch per open question, on one page (sub-shape B: themes have no single host page). */
var SCENES = [
  ['learn', 'Learning screen'], ['check', 'Mastery check'], ['pics', 'Pictures and maths'],
  ['shell', 'Sidebar and all-sessions page'], ['record', 'What you\'ve mastered'], ['settings', 'Settings page'],
  ['signin', 'Sign-in page'], ['landing', 'Landing page'], ['guest', 'Guest and trial link'],
  ['owner', 'Owner page'], ['contrast', 'Contrast table']
];
// One switch per open question. Letters match the question's options in chat.
var QS = {
  pal:   { name: 'Dark look', opts: { A: 'Neutral grey', B: 'Blue slate', C: 'Near-black' } },
  bar:   { name: 'Check bar', opts: { A: 'Inverted', B: 'Blue bar', C: 'Raised strip' } },
  pic:   { name: 'Pictures', opts: { A: 'Crux colours', B: 'Mermaid dark', C: 'Light card' } },
  out:   { name: 'Outside parts', opts: { A: 'Follow theme', B: 'Always light' } },
  files: { name: 'Your files', opts: { A: 'As they are', B: 'Dimmed', C: 'Pages inverted' } },
  light: { name: 'Light fixes', opts: { draft: 'As drawn', A: 'All lines', B: 'Controls only' } },
  get:   { name: 'Getting it', opts: { A: 'Device only', B: 'Switch only', C: 'Both' } },
  place: { name: 'Switch place', opts: { A: 'Settings', B: 'Sidebar foot', C: 'Both' } }
};
var DEF = { scene: 'learn', dev: 'desktop', device: 'light', choice: 'device', who: 'account',
  pal: 'A', bar: 'A', pic: 'A', out: 'A', files: 'A', light: 'draft', get: 'C', place: 'A', dlg: '0', hit: '0' };
var S = {};

function readState() {
  var p = new URLSearchParams(location.search);
  Object.keys(DEF).forEach(function (k) { S[k] = p.get(k) || DEF[k]; });
  if (S.scene === 'trial') { S.scene = 'guest'; S.who = 'trial'; }
}
function link(over) {
  var s = Object.assign({}, S, over || {}), p = new URLSearchParams();
  Object.keys(DEF).forEach(function (k) { if (s[k] !== DEF[k]) p.set(k, s[k]); });
  var q = p.toString(); return location.pathname + (q ? '?' + q : '');
}
function go(over) { history.replaceState(null, '', link(over)); render(); }

// Which theme shows, and why: the device setting, the learner's choice, and the "getting it" option.
function effective() {
  if (S.get === 'A') return { theme: S.device, why: 'follows the device (option A: no switch)' };
  if (S.get === 'B') {
    var t = S.choice === 'dark' ? 'dark' : 'light';
    return { theme: t, why: 'the switch says ' + t + (S.choice === 'device' ? ' (light until chosen; option B ignores the device)' : '') };
  }
  if (S.choice === 'device') return { theme: S.device, why: 'the choice is "Match my device", and the device is ' + S.device };
  return { theme: S.choice, why: 'the choice is ' + S.choice + ', whatever the device says' };
}
function signedOutTheme() { // signed-out pages: no switch there, so the device decides (rule question on where the choice lives)
  return S.get === 'B' ? 'light' : S.device;
}

function applyTheme(theme) {
  var root = document.documentElement, k = themeTokens(theme, S.pal, S.light);
  Object.keys(k).forEach(function (n) { root.style.setProperty('--' + n, k[n]); });
  root.dataset.theme = theme; root.dataset.bar = S.bar; root.dataset.picopt = S.pic; root.dataset.files = S.files;
  root.dataset.gdark = (S.out === 'A' && theme === 'dark') ? '1' : '0';
  root.dataset.tdark = root.dataset.gdark;
  root.style.colorScheme = theme;
  return k;
}

function btnGroup(key, label, opts) {
  var h = '<span class="grp"><span class="lbl">' + label + '</span>';
  Object.keys(opts).forEach(function (o) {
    h += '<button data-k="' + key + '" data-v="' + o + '" class="' + (S[key] === o ? 'on' : '') + '" title="' + opts[o] + '">' + (o.length === 1 ? o : opts[o]) + '</button>';
  });
  return h + '</span>';
}
function renderBar() {
  var h = '<span class="grp"><span class="lbl">Scene</span><button data-step="-1" aria-label="Previous scene">&larr;</button><select id="sc">';
  SCENES.forEach(function (s) { h += '<option value="' + s[0] + '"' + (S.scene === s[0] ? ' selected' : '') + '>' + s[1] + '</option>'; });
  h += '</select><button data-step="1" aria-label="Next scene">&rarr;</button></span>';
  h += btnGroup('dev', 'View', { desktop: 'Desktop', phone: 'Phone' });
  h += btnGroup('device', 'Device set to', { light: 'Light', dark: 'Dark' });
  Object.keys(QS).forEach(function (k) { h += btnGroup(k, QS[k].name, QS[k].opts); });
  h += '<button id="axe">Run axe</button>';
  document.getElementById('bar').innerHTML = h;
}

function renderNote(eff) {
  var q = Object.keys(QS).map(function (k) { return QS[k].name + ' <b>' + S[k] + '</b> (' + QS[k].opts[S[k]] + ')'; }).join(' · ');
  document.getElementById('note').innerHTML =
    '<p><b>PROTOTYPE #779 (throwaway).</b> Every screen in both themes. All wording is draft unless the spec already has it. ' +
    'Colours are drafts; the spec records none yet.</p>' +
    '<p><b>Showing:</b> ' + (eff.signedOut ? 'signed-out page, ' + eff.theme + ' (no switch here, so the device decides)' : eff.theme + ' theme, because ' + eff.why) + '.</p>' +
    '<p><b>Options:</b> ' + q + '</p><p id="axeout"></p>';
}

function render() {
  readState();
  var scene = window['scene_' + S.scene] ? S.scene : 'learn';
  var signedOut = scene === 'signin' || scene === 'landing';
  var eff = signedOut ? { theme: signedOutTheme(), signedOut: true } : effective();
  var k = applyTheme(eff.theme);
  renderBar(); renderNote(eff);
  var dev = document.getElementById('device');
  dev.className = 'device ' + S.dev + (S.dev === 'phone' && (scene === 'shell' || scene === 'settings' && S.place !== 'A') ? ' drawer' : '');
  dev.innerHTML = window['scene_' + scene](k, eff);
  drawMaths(); drawDiagrams(eff.theme, k);
}

// KaTeX: elements with data-tex. An element with data-raw shows the source in the code style instead.
function drawMaths() {
  if (!window.katex) return;
  document.querySelectorAll('[data-tex]').forEach(function (el) {
    katex.render(el.getAttribute('data-tex'), el, { displayMode: el.hasAttribute('data-display'), throwOnError: false });
  });
}

var mmSeq = 0;
function mermaidConfig(theme, k) {
  var c = { startOnLoad: false, securityLevel: 'strict', fontFamily: 'system-ui, "Segoe UI", sans-serif' };
  if (S.pic === 'B') { c.theme = theme === 'dark' ? 'dark' : 'default'; return c; }
  if (S.pic === 'C') { c.theme = 'default'; return c; }
  c.theme = 'base';
  c.themeVariables = { darkMode: theme === 'dark', background: k.pic, primaryColor: k.picNode, primaryTextColor: k.picInk,
    primaryBorderColor: k.picNodeLine, secondaryColor: k.surface2, tertiaryColor: k.surface2, lineColor: k.picLine,
    textColor: k.picInk, mainBkg: k.picNode, nodeBorder: k.picNodeLine, edgeLabelBackground: k.pic, clusterBkg: k.surface2,
    actorBkg: k.picNode, actorBorder: k.picNodeLine, actorTextColor: k.picInk, actorLineColor: k.picLine,
    signalColor: k.picLine, signalTextColor: k.picInk, noteBkgColor: k.surface2, noteTextColor: k.picInk, noteBorderColor: k.picLine,
    labelBoxBkgColor: k.picNode, labelBoxBorderColor: k.picNodeLine, labelTextColor: k.picInk, loopTextColor: k.picInk,
    sequenceNumberColor: k.picInk, transitionColor: k.picLine, transitionLabelColor: k.picInk, stateLabelColor: k.picInk,
    stateBkg: k.picNode, labelBackgroundColor: k.pic, compositeBackground: k.surface2, altBackground: k.surface2,
    specialStateColor: k.picLine, innerEndBackground: k.picLine };
  return c;
}
function drawDiagrams(theme, k) {
  var els = document.querySelectorAll('[data-mermaid]');
  if (!els.length || !window.mermaid) return;
  mermaid.initialize(mermaidConfig(theme, k));
  els.forEach(function (el) {
    var id = 'mm' + (++mmSeq);
    mermaid.render(id, el.getAttribute('data-mermaid')).then(function (r) {
      el.innerHTML = r.svg; measurePicture(el);
    }).catch(function (e) { el.textContent = 'Mermaid error: ' + e.message; });
  });
}

// The drawn colours of a diagram, as the spec's contrast test would read them.
function toHex(c) {
  var m = (c || '').match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?/);
  if (!m || (m[4] !== undefined && +m[4] === 0)) return null;
  return '#' + [m[1], m[2], m[3]].map(function (v) { return ('0' + Math.round(+v).toString(16)).slice(-2); }).join('');
}
function measurePicture(el) {
  var out = el.parentNode.querySelector('.drawn'); if (!out) return;
  var bg = toHex(getComputedStyle(el.closest('.pic')).backgroundColor), worst = {};
  function take(kind, fg, against, need) {
    if (!fg || !against) return;
    var r = ratio(fg, against); if (!worst[kind] || r < worst[kind].r) worst[kind] = { r: r, need: need };
  }
  el.querySelectorAll('.node, .actor, g[id*="state"], rect.actor').forEach(function (n) {
    var shape = n.matches('rect') ? n : n.querySelector('rect, polygon, circle, path'); if (!shape) return;
    var fill = toHex(getComputedStyle(shape).fill), stroke = toHex(getComputedStyle(shape).stroke);
    var txt = n.querySelector('.nodeLabel, span, text, tspan');
    take('box text', txt ? toHex(getComputedStyle(txt).color === 'rgb(0, 0, 0)' && txt.tagName.toLowerCase() !== 'span' ? getComputedStyle(txt).fill : getComputedStyle(txt).color) : null, fill || bg, 4.5);
    take('box edge', stroke || fill, bg, 3);
  });
  el.querySelectorAll('.flowchart-link, path.transition, .messageLine0, .messageLine1, line.actor-line').forEach(function (p) {
    take('arrows', toHex(getComputedStyle(p).stroke), bg, 3);
  });
  el.querySelectorAll('.messageText, .edgeLabel span, .edgeLabel p').forEach(function (t) {
    var c = t.tagName.toLowerCase() === 'text' ? getComputedStyle(t).fill : getComputedStyle(t).color;
    take('arrow text', toHex(c), bg, 4.5);
  });
  out.innerHTML = 'Drawn colours, worst of each: ' + Object.keys(worst).map(function (n) {
    var w = worst[n], ok = w.r >= w.need;
    return n + ' <b class="' + (ok ? 'ok' : '') + '" style="' + (ok ? '' : 'color:var(--stopInk);background:var(--stop);padding:0 3px') + '">' + w.r.toFixed(1) + ':1' + (ok ? '' : ' FAILS ' + w.need) + '</b>';
  }).join(' · ');
}

function runAxe() {
  var o = document.getElementById('axeout');
  if (!window.axe) { o.textContent = 'axe not loaded.'; return; }
  o.textContent = 'axe running...';
  axe.run(document.getElementById('device'), { runOnly: ['color-contrast'] }).then(function (r) {
    var n = r.violations.reduce(function (a, v) { return a + v.nodes.length; }, 0);
    var inc = r.incomplete.reduce(function (a, v) { return a + v.nodes.length; }, 0);
    var first = r.violations.length ? r.violations[0].nodes.slice(0, 4).map(function (x) { return '<code>' + x.target.join(' ') + '</code> ' + (x.any[0] ? x.any[0].message : ''); }).join('<br>') : '';
    o.innerHTML = '<b>axe colour-contrast on this view:</b> ' + n + ' failing, ' + inc + ' it could not judge (pictures, overlaps).' + (first ? '<br>' + first : '');
    window.__axe = { failing: n, incomplete: inc };
  });
}

document.addEventListener('click', function (e) {
  var b = e.target.closest('[data-k]');
  if (b) { var o = {}; o[b.dataset.k] = b.dataset.v; go(o); return; }
  var st = e.target.closest('[data-step]');
  if (st) { step(+st.dataset.step); return; }
  var g = e.target.closest('[data-go]');
  if (g) { e.preventDefault(); go(JSON.parse(g.dataset.go)); return; }
  if (e.target.id === 'axe') runAxe();
});
document.addEventListener('change', function (e) { if (e.target.id === 'sc') go({ scene: e.target.value }); });
function step(d) {
  var i = SCENES.findIndex(function (s) { return s[0] === S.scene; });
  go({ scene: SCENES[(i + d + SCENES.length) % SCENES.length][0] });
}
document.addEventListener('keydown', function (e) {
  if (e.target.closest('input, textarea, select, [contenteditable]')) return;
  if (e.key === 'ArrowLeft') step(-1); if (e.key === 'ArrowRight') step(1);
});
window.addEventListener('load', render);
