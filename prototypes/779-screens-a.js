/* PROTOTYPE, throwaway (calmxz/Crux#779). Shared pieces, the learning screen, the check and the pictures.
   Screen wording comes from the spec files where they have it; anything else is marked (draft). */
var SESSIONS = [
  ['Derivatives: the chain rule', 'Today', 60, ''], ['Personal essay', 'Yesterday', 30, 'wait'],
  ['Photosynthesis', 'Mon', 100, ''], ['SQL joins', '12 Nov', 45, 'chk'], ['Supply and demand', '10 Nov', 80, ''],
  ['Kirchhoff\'s laws', '8 Nov', 20, ''], ['The French Revolution', '6 Nov', 100, ''], ['Binary search', '3 Nov', 70, ''],
  ['Cell division', '1 Nov', 10, ''], ['Bayes\' theorem', '29 Oct', 55, '']
];

// The theme choice. Wording varies by "getting it" option; under A there is no switch.
function themeControl(compact) {
  if (S.get === 'A') return '';
  var choices = S.get === 'B' ? [['light', 'Light'], ['dark', 'Dark']] : [['device', compact ? 'Device' : 'Match my device'], ['light', 'Light'], ['dark', 'Dark']];
  var cur = S.get === 'B' && S.choice === 'device' ? 'light' : S.choice;
  return '<span class="seg" role="group" aria-label="Theme">' + choices.map(function (c) {
    return '<button aria-pressed="' + (cur === c[0]) + '" data-go=\'{"choice":"' + c[0] + '"}\'>' + c[1] + '</button>';
  }).join('') + '</span>';
}
function sideFootTheme() {
  if (S.get === 'A' || S.place === 'A') return '';
  return '<div><span class="small mute">Theme (draft)</span><span class="tagnew">new</span><div style="margin-top:4px">' + themeControl(true) + '</div></div>';
}

function sidebar(cur, opt) {
  opt = opt || {};
  var h = '<aside class="side"><div class="top"><span class="brand">Crux</span>';
  if (!opt.guest) h += '<button class="iconbtn" aria-label="Search your sessions" data-go=\'{"scene":"shell"}\'>&#128269;</button>';
  h += '<button class="btn small">+ New</button></div><div class="list"><div class="sec">Sessions</div>';
  var list = opt.guest ? [['Derivatives: the chain rule', 'Now', 40, '']] : SESSIONS;
  list.forEach(function (s, i) {
    h += '<div class="sline' + (i === cur ? ' cur' : '') + '"><div class="nm">' + s[0] +
      (s[3] === 'wait' ? '<span class="badge wait">Waiting</span>' : '') + (s[3] === 'chk' ? '<span class="badge chk">Check</span>' : '') +
      '</div><div class="ln">' + s[1] + '</div><div class="pbar' + (s[2] === 100 ? ' full' : '') + '"><i style="width:' + s[2] + '%"></i></div></div>';
  });
  if (!opt.guest) h += '<div class="allline"><a data-go=\'{"scene":"shell"}\'>All sessions (24)</a></div>';
  h += '</div><div class="foot">';
  if (opt.guest) h += '<span class="small mute">7 of 10 replies used (draft)</span>';
  else h += '<a data-go=\'{"scene":"record"}\'>What you\'ve mastered</a><a>Feedback</a>';
  if (!opt.guest) h += sideFootTheme() + '<a data-go=\'{"scene":"settings"}\'>&#9881; Settings</a><span class="em">' + (opt.trial ? 'Trial link' : 'maria.santos@example.com') + '</span>';
  if (opt.owner) h += '<a data-go=\'{"scene":"owner"}\'>Owner</a>';
  return h + '</div></aside>';
}
function topbar(title, extra) {
  return '<div class="topbar"><button class="iconbtn" aria-label="Open the sidebar">&#9776;</button><span class="title">' + title + '</span>' + (extra || '') + '</div>';
}
function objectives() {
  var o = [['pass', 'State the chain rule', 'Passed 14 Nov'], ['pass', 'Spot the inner function', 'Passed today'],
    ['shown', 'Differentiate a composite', 'Shown'], ['', 'Chain rule with the product rule', 'Not yet'], ['', 'Use it on a rate problem', 'Not yet &#9888; trouble']];
  var rail = '<div class="rail"><h3>Objectives</h3><ul class="obj">' + o.map(function (x) {
    return '<li><span class="st ' + x[0] + '"></span><span>' + x[1] + '<br><span class="small ' + (x[0] === 'pass' ? 'ok' : 'mute') + '">' + x[2] + '</span></span></li>';
  }).join('') + '</ul><h2 style="font-size:13px;margin:14px 0 4px">Files</h2><div class="small"><a>chain-rule-notes.pdf</a> <span class="mute">12 pages</span></div></div>';
  var strip = '<div class="strip">' + o.map(function (x) { return '<i class="' + x[0] + '"></i>'; }).join('') + '<span>2 of 5 &#9662;</span></div>';
  return { rail: rail, strip: strip };
}
function graphSvg(tangent) {
  var pts = [], i; for (i = -20; i <= 20; i++) { var x = i / 10; pts.push((150 + x * 60).toFixed(1) + ',' + (170 - x * x * 35).toFixed(1)); }
  var g = '<svg viewBox="0 0 300 190" role="img" aria-label="Graph of y = x squared from -2 to 2, tangent at x = 1">';
  for (i = 30; i <= 270; i += 30) g += '<line class="g-grid" x1="' + i + '" y1="10" x2="' + i + '" y2="180" stroke-width="1"/>';
  g += '<line class="g-axis" x1="20" y1="170" x2="285" y2="170" stroke-width="1.5"/><line class="g-axis" x1="150" y1="10" x2="150" y2="182" stroke-width="1.5"/>';
  g += '<polyline class="g-curve" stroke-width="2.5" points="' + pts.join(' ') + '"/>';
  if (tangent) g += '<line class="g-curve" stroke-width="1.5" stroke-dasharray="5 3" x1="150" y1="170" x2="270" y2="30"/>';
  g += '<circle class="g-mark" cx="210" cy="135" r="5"/><text class="g-text" x="218" y="150">(1, 1)</text><text class="g-text" x="272" y="165">x</text><text class="g-text" x="155" y="20">y</text></svg>';
  return g;
}
function picture(kind, body, caption) {
  return '<div class="pic"><div class="cap">' + caption + '</div>' + (kind === 'mermaid' ? '<div data-mermaid="' + body + '">Drawing...</div>' : body) +
    '<div class="drawn small mute">' + (kind === 'graph' ? 'Graph colours are Crux\'s own; see the contrast table.' : '') + '</div></div>';
}
var FLOW = 'flowchart LR\n  A[Outer function f] --> B[Inner function g]\n  B --> C[Multiply the two derivatives]';

function thread(k) {
  return '<div class="thread">' +
    '<div class="msg me">What does the chain rule say?</div>' +
    '<div class="msg tutor"><div class="who">Tutor</div>It says that for a function inside a function, <span data-tex="\\frac{d}{dx}f(g(x)) = f\'(g(x))\\,g\'(x)"></span>. Here is a longer one:' +
    '<div class="mathbox" tabindex="0" role="region" aria-label="Equation, scrolls sideways"><span data-display data-tex="\\frac{d}{dx}\\sin\\left(x^2 + 3x + \\ln(x)\\right) = \\cos\\left(x^2 + 3x + \\ln(x)\\right)\\cdot\\left(2x + 3 + \\frac{1}{x}\\right) \\quad\\text{for } x > 0"></span></div>' +
    'And one KaTeX cannot draw: <code class="raw">\\begin{align*} y = \\undefinedmacro{x}</code>' +
    picture('mermaid', FLOW, 'The chain rule in three steps') + picture('graph', graphSvg(true), 'y = x&sup2;, with its tangent at x = 1') +
    '</div>' +
    '<div class="msg tutor"><div class="who">Tutor</div>Here is the picture you asked for.<div class="checking">Checking the picture... (draft)</div></div>' +
    '<div class="msg me' + (S.hit === '1' ? ' hit' : '') + '">So for sin(x&sup2;) it\'s cos(x&sup2;) times 2x?' + (S.hit === '1' ? ' <span class="small">(the matched message, opened from a snippet)</span>' : '') + '</div>' +
    '<div class="msg tutor"><div class="who">Tutor</div>Yes. You look ready to show it.<div class="offer"><b>Mastery check</b> (draft)<br><span class="small mute">4 problems, closed book</span><div class="row"><button class="btn primary">Start the check</button><button class="btn">Not yet</button></div></div></div>' +
    '<div class="sysline">Information: You\'ve used 70% of today\'s tutoring. (draft)</div>' +
    '<div class="sysline warn">Warning: Connection lost. Reconnecting... (draft)</div>' +
    '<div class="sysline stop">Stop: The reply broke off, so the tutor is starting again. (draft)</div>' +
    '<div class="sysline care">Care: If things feel like too much, you can talk to someone. (draft)</div>' +
    '<div class="sysline">Your message is saved. The tutor will answer it when it can. (draft)</div>' +
    '<div class="msg me">Can you show a harder one?<span class="wait">Sending...</span></div></div>' +
    '<div class="composer"><button class="iconbtn" aria-label="Add a file">&#128206;</button><input class="txt" placeholder="Message the tutor"><button class="btn primary">Send</button></div>';
}

function scene_learn(k) {
  var o = objectives();
  return sidebar(0) + '<div class="main">' + topbar('Derivatives: the chain rule', '<span class="link">Objectives</span>') +
    (S.dev === 'phone' ? o.strip : '') + '<div style="display:flex;flex:1;min-height:0"><div class="main">' + thread(k) + '</div>' + (S.dev === 'phone' ? '' : o.rail) + '</div></div>';
}

function scene_check() {
  return sidebar(3) + '<div class="main">' + topbar('SQL joins') +
    '<div class="checkbar">Mastery check &middot; Problem 2 of 4 &middot; closed book</div>' +
    '<div class="thread"><div class="msg tutor"><div class="who">Problem 2</div>The graph shows <span data-tex="y = x^2"></span>. What is the slope of the tangent at the marked point?' +
    picture('graph', graphSvg(false), 'y = x&sup2; from -2 to 2, one point marked') + '</div>' +
    '<div class="msg me">2, because the derivative is 2x and x = 1.</div>' +
    '<div class="sysline">Marking&hellip;</div>' +
    '<div class="result"><b>Result</b> (draft)<p style="margin:6px 0">3 of 4 objectives passed. <span class="ok">&#10003; Passed: joins, keys, filters</span></p>' +
    '<p class="small mute" style="margin:4px 0">Problem 4 missed: outer joins</p><div class="row"><button class="btn">See the problem sheet</button><button class="btn">Dispute</button><button class="btn primary">Back to learning</button></div></div>' +
    '</div><div class="composer"><button class="iconbtn" aria-label="Add a photo answer">&#128247;</button><input class="txt" placeholder="Your answer"><button class="btn primary">Send</button></div></div>';
}

function scene_pics() {
  var st = 'stateDiagram-v2\n  [*] --> Teaching\n  Teaching --> Check: ready\n  Check --> Mastered: pass\n  Check --> Teaching: fail';
  var sq = 'sequenceDiagram\n  Learner->>Tutor: Asks a question\n  Tutor->>Learner: Explains, with a picture\n  Learner->>Tutor: Tries a problem';
  return sidebar(0) + '<div class="main">' + topbar('Pictures and maths in a tutor message') + '<div class="thread">' +
    '<div class="msg tutor" style="max-width:96%"><div class="who">Tutor</div>' +
    picture('mermaid', FLOW, 'Flowchart') + picture('mermaid', st, 'State diagram') + picture('mermaid', sq, 'Sequence diagram') +
    picture('graph', graphSvg(true), 'Graph: y = x&sup2; with its tangent at x = 1') +
    '<p>Inline maths <span data-tex="e^{i\\pi} + 1 = 0"></span>, a wide one in its sideways box:</p><div class="mathbox" tabindex="0" role="region" aria-label="Equation, scrolls sideways"><span data-display data-tex="\\int_0^1 \\left(3x^2 + 2x + 1\\right)\\,dx = \\left[x^3 + x^2 + x\\right]_0^1 = 3 \\qquad \\sum_{n=1}^{\\infty} \\frac{1}{n^2} = \\frac{\\pi^2}{6}"></span></div>' +
    '<p>Maths KaTeX cannot draw: <code class="raw">\\frac{1}{\\notamacro{2}}</code></p></div>' +
    '<div class="msg tutor"><div class="who">Things Crux does not colour</div><div class="row">' +
    '<div class="ufile upage"><b>Lecture 4: The chain rule</b><p>If y = f(u) and u = g(x), then dy/dx = dy/du &middot; du/dx.</p>' +
    '<div class="chart"><i style="height:60%;background:#d93025"></i><i style="height:85%;background:#1e8e3e"></i><i style="height:40%;background:#1a73e8"></i></div><span class="pn">Page 3 of 12, from chain-rule-notes.pdf</span></div>' +
    '<div class="ufile uphoto"><span class="pencil">dy/dx = 2x &middot; cos(x&sup2;)</span><span class="pn">A photo answer, as taken</span></div></div></div>' +
    '</div></div>';
}
