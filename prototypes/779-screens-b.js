/* PROTOTYPE, throwaway (calmxz/Crux#779). App shell pages, account pages, signed-out pages, owner page, contrast table. */
function scene_shell() {
  var hits = [['Derivatives: the chain rule', 'Today', 'So for sin(x&sup2;) it\'s cos(x&sup2;) times 2x? &hellip; the <mark>chain rule</mark> says multiply', 60],
    ['Kirchhoff\'s laws', '8 Nov', '&hellip; like the <mark>chain rule</mark>, each loop adds up to zero &hellip;', 20],
    ['Bayes\' theorem', '29 Oct', '&hellip; a <mark>chain</mark> of conditional probabilities, one <mark>rule</mark> at a time &hellip;', 55]];
  return sidebar(-1) + '<div class="main">' + topbar('All sessions') + '<div class="page"><h1>All sessions (24)</h1>' +
    '<div class="search"><input class="txt" value="chain rule" aria-label="Search your sessions"><button class="btn">Clear</button></div>' +
    hits.map(function (h) {
      return '<div class="hitline"><div class="nm">' + h[0] + ' <span class="small mute">' + h[1] + '</span></div><div class="snip"><a data-go=\'{"scene":"learn","hit":"1"}\' style="text-decoration:none;color:inherit">' + h[2] + '</a></div><div class="pbar" style="max-width:240px"><i style="width:' + h[3] + '%"></i></div></div>';
    }).join('') +
    '<p class="small mute">Loading...</p><h2>Other states</h2><p class="mute">No sessions match "photosynthesys". (draft)</p>' +
    '<p class="sysline warn" style="display:inline-block">Crux can\'t be reached right now. Try again later.</p>' +
    '<p class="small mute">Tap a snippet to open the session with the matched message highlighted.</p></div></div>';
}

function scene_record() {
  return sidebar(-1) + '<div class="main">' + topbar('What you\'ve mastered') + '<div class="page"><h1>What you\'ve mastered</h1>' +
    '<span class="seg" role="group" aria-label="Order"><button aria-pressed="true">By date</button><button aria-pressed="false">By session</button></span>' +
    '<table class="t" style="margin-top:14px"><tr><th>Mastered</th><th>Topic</th><th>Objectives passed</th></tr>' +
    '<tr><td>14 Nov</td><td>Photosynthesis</td><td class="ok">5 of 5</td></tr><tr><td>6 Nov</td><td>The French Revolution</td><td class="ok">4 of 4</td></tr>' +
    '<tr><td>2 Nov</td><td>Binary search</td><td class="ok">3 of 3</td></tr></table></div></div>';
}

function scene_settings() {
  var trial = S.who === 'trial';
  var appearance = (S.get !== 'A' && S.place !== 'B') ? '<div class="part new"><h2>Appearance <span class="tagnew">new, draft</span></h2>' +
    '<div class="row" style="margin-top:0"><span>Theme</span>' + themeControl(false) + '</div>' +
    (S.get === 'C' ? '<p class="small mute" style="margin:8px 0 0">"Match my device" follows your phone or computer\'s own setting. (draft)</p>' : '') + '</div>' : '';
  var h = sidebar(-1, { trial: trial }) + '<div class="main">' + topbar('Settings') + '<div class="page" style="max-width:720px"><h1>Settings</h1>' +
    '<div class="part"><h2>Tutoring</h2>Today\'s tutoring: 70% used<div class="pbar big"><i style="width:70%"></i></div><div style="margin-top:8px">This week: 45% used</div><div class="pbar big"><i style="width:45%"></i></div></div>' +
    '<div class="part"><h2>Files</h2>Your files: 186 of 200 MB<div class="pbar big"><i style="width:93%"></i></div><div class="row"><a>See your files</a></div></div>' +
    '<div class="part"><h2>Your feedback</h2><p class="small mute" style="margin:0 0 6px">Untick to withdraw a quote or end a share.</p>' +
    '<div><b>8 Nov &middot; Helped: yes &middot; Would pay: maybe</b></div><div class="small">The check made me actually learn it.</div>' +
    '<label class="tick"><input type="checkbox" checked> Quote me</label><label class="tick"><input type="checkbox" checked> Share: Personal essay (the owner can read it up to 8 Nov)</label></div>' +
    appearance;
  h += trial ? '<div class="part"><h2>Trial link K7Q-4MP</h2><button class="btn danger">Erase this trial link</button></div>'
    : '<div class="part"><h2>Account</h2><div>maria.santos@example.com</div><div class="row"><button class="btn danger" data-go=\'{"dlg":"1"}\'>Close account</button></div>' +
      '<div class="row small"><a>Terms</a><a>Privacy Policy</a><a>Who runs Crux</a></div><div class="row"><button class="btn">Sign out</button></div></div>';
  h += '<p class="small mute">' + (S.get === 'A' ? 'Option A: no switch anywhere; Crux follows the device.' : S.place === 'B' ? 'Option B: the switch is in the sidebar foot only.' : '') + ' Trial link view: <a data-go=\'{"who":"' + (trial ? 'account' : 'trial') + '"}\'>' + (trial ? 'show the account' : 'show a trial link') + '</a></p></div>';
  if (S.dlg === '1') h += '<div class="overlay"><div class="dialog" role="dialog" aria-label="Close your account?"><h2>Close your account?</h2>' +
    '<p class="small">This erases your 4 sessions, your files, and your record of 3 mastered topics after 11:59 pm on 10 Nov. Until then, open Crux and choose Keep my account to stop it.</p>' +
    '<label class="tick"><input type="checkbox"> Send me a copy first</label><label class="small">Type delete to confirm<input class="txt" style="margin-top:4px"></label>' +
    '<div class="row"><button class="btn" data-go=\'{"dlg":"0"}\'>Cancel</button><button class="btn danger" disabled>Close account</button></div></div></div>';
  return h + '</div>';
}

function scene_signin() {
  return '<div class="main">' + '<div class="topbar"><span class="title">Crux</span></div><div class="center"><div class="card" style="width:380px">' +
    '<h1 style="font-size:20px;margin:0 0 14px">Sign in or sign up</h1><button class="gbtn"><span class="g">G</span> Continue with Google</button>' +
    '<p class="mute" style="text-align:center;margin:10px 0">or</p><label class="small">Email<input class="txt" placeholder="you@example.com" style="margin-top:4px"></label>' +
    '<div class="turn"><span class="bx"></span>Verify you are human<span style="margin-left:auto;font-size:10px">Cloudflare (placeholder)</span></div>' +
    '<button class="btn primary" style="width:100%;margin-top:12px">Email me a code</button>' +
    '<p class="sysline stop" style="margin:12px 0 0">Too many code requests. Try again in an hour, or use Continue with Google.</p>' +
    '<p class="small mute" style="margin-top:12px">Google\'s button uses Google\'s own colours (light or dark), and Turnstile has light, dark and auto.</p></div></div></div>';
}

function scene_landing() {
  return '<div class="main"><div class="topbar"><span class="title">Crux</span><a class="small">Sign in</a></div><div class="page" style="max-width:820px;margin:0 auto">' +
    '<h1 style="font-size:26px">A tutor that teaches until you\'ve proven it. (draft)</h1>' +
    '<div class="card"><input class="txt" placeholder="What do you want to learn?"><div class="chips"><span class="chip">The chain rule</span><span class="chip">SQL joins</span><span class="chip">Upload a lesson file</span></div>' +
    '<label class="tick"><input type="checkbox"> I am 18 or over</label><label class="tick"><input type="checkbox"> I agree to the <a>Trial Terms</a> and the <a>Trial Privacy Notice</a></label>' +
    '<div class="row"><button class="btn primary">Start</button></div></div>' +
    '<p class="small mute">Crux is for adults 18 and over.</p><div class="video">The example video (its frames keep their own colours)</div>' +
    '<h2>Request access</h2><p class="small">Want more than a short try? Ask for a trial link. (draft)</p><button class="btn">Request access</button>' +
    '<p class="sysline warn" style="display:inline-block;margin-top:14px">Crux can\'t be reached right now. Try again later.</p></div></div>';
}

function scene_guest() {
  var trial = S.who === 'trial';
  return sidebar(0, { guest: !trial, trial: trial }) + '<div class="main">' +
    (trial ? '<div class="banner">This trial link works on this browser. (draft)</div>' : '') + topbar('Derivatives: the chain rule') +
    '<div class="thread"><div class="msg me">Teach me the chain rule</div><div class="msg tutor"><div class="who">Tutor</div>Let\'s start with what a function inside a function looks like: <span data-tex="\\sin(x^2)"></span>.</div>' +
    (trial ? '' : '<div class="sysline warn">3 replies left in this guest try. (draft)</div>') +
    '<p class="small mute" style="align-self:center">' + (trial ? 'Trial link view.' : 'Guest view: nothing is kept after the tab closes.') + ' <a data-go=\'{"who":"' + (trial ? 'account' : 'trial') + '"}\'>' + (trial ? 'Show a guest' : 'Show a trial link') + '</a></p>' +
    '</div><div class="composer"><input class="txt" placeholder="Message the tutor"><button class="btn primary">Send</button></div></div>';
}

function scene_owner() {
  return '<div class="main"><div class="topbar"><span class="title">Crux owner</span><a class="small" data-go=\'{"scene":"learn"}\'>Back to Crux</a></div>' +
    '<div class="tabs"><button aria-current="page">Today<span class="count">3</span></button><button>Trial</button><button>Safety<span class="count">1</span></button><button>Feedback</button><button>Counts</button><button>Money</button><button>Switches</button></div>' +
    '<div class="page" style="display:grid;grid-template-columns:1fr 1fr;gap:16px;align-content:start">' +
    '<div class="card"><h2 style="margin-top:0">What needs you</h2><table class="t"><tr><th>Item</th><th>Since</th></tr><tr><td><a>Flag 4821: 3 declines</a></td><td>2 h</td></tr><tr><td><a>Trial request from j.cruz</a></td><td>Yesterday</td></tr><tr><td><a>2 unread feedback answers</a></td><td>Mon</td></tr></table></div>' +
    '<div class="card"><h2 style="margin-top:0">Money this month</h2>Learners: USD 5.12 of 8.00<div class="pbar big"><i style="width:64%"></i></div><div style="margin-top:8px">Your share: USD 1.10 of 3.00</div><div class="pbar big"><i style="width:37%"></i></div><div class="row"><button class="btn">Raise a limit</button></div></div>' +
    '<div class="card"><h2 style="margin-top:0">Switches</h2><p>New sign-ups <span class="sw on" role="switch" aria-checked="true" aria-label="New sign-ups"></span></p><p>Guest mode <span class="sw" role="switch" aria-checked="false" aria-label="Guest mode"></span></p></div>' +
    '<div class="card"><h2 style="margin-top:0">Flag 4821</h2><div class="sysline stop" style="text-align:left">The tutor declined 3 requests in "Personal essay".</div><div class="row"><button class="btn">Warn</button><button class="btn">Dismiss</button><button class="btn danger">Close</button></div></div>' +
    '</div></div>';
}

function scene_contrast(k, eff) {
  var other = eff.theme === 'dark' ? 'light' : 'dark', k2 = themeTokens(other, S.pal, S.light);
  function cell(set, p) {
    var r = ratio(set[p[0]], set[p[1]]), need = p[2] === 'text' ? 4.5 : 3, info = p[2] === 'info';
    return '<td><span class="swatch" style="background:' + set[p[1]] + ';color:' + set[p[0]] + '">Aa</span></td><td class="' + (info ? '' : r >= need ? 'pass' : 'fail') + '">' + r.toFixed(2) + (info ? ' (info)' : r >= need ? '' : ' fails') + '</td>';
  }
  var lbl = function (t) { return t === 'light' ? 'Light (' + QS.light.opts[S.light] + ')' : 'Dark (' + QS.pal.opts[S.pal] + ')'; };
  var h = '<div class="main"><div class="page"><h1>Contrast of every colour pair</h1><p class="small mute">Text needs 4.5:1; interface parts and the parts of a picture needed to read it need 3:1. Diagram colours as drawn are measured under each picture in the Pictures scene.</p>' +
    '<table class="t ctable"><tr><th>Where it shows</th><th>Need</th><th colspan="2">' + lbl(eff.theme) + '</th><th colspan="2">' + lbl(other) + '</th></tr>';
  PAIRS.forEach(function (p) { h += '<tr><td>' + p[3] + '</td><td>' + (p[2] === 'text' ? '4.5' : p[2] === 'ui' ? '3' : '-') + '</td>' + cell(k, p) + cell(k2, p) + '</tr>'; });
  return h + '</table></div></div>';
}
