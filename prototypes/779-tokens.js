/* PROTOTYPE, throwaway (calmxz/Crux#779). Every colour the screens use, per theme.
   The page reads them as CSS variables; the contrast panel checks the pairs below. */
var TOKENS = {
  // The light look as drawn in the earlier prototypes (751-780), gathered into tokens.
  lightDraft: {
    page:'#d9dde4', bg:'#f6f7f9', surface:'#ffffff', surface2:'#fafbfc', raise:'#ffffff',
    ink:'#1d2330', mute:'#6b7280', line:'#e3e6ec', line2:'#f0f1f4', ctl:'#c9ced8',
    accent:'#2f5bea', accentFill:'#2f5bea', onAccent:'#ffffff', sel:'#eef2ff',
    sys:'#eef1f6', sysInk:'#3b4252', warn:'#fff4e0', warnInk:'#3b4252', stop:'#fde8e8', stopInk:'#3b4252',
    care:'#e9f6ef', careInk:'#3b4252', ok:'#1f8a4c', prog:'#c27c0e', track:'#e3e6ec',
    hl:'#fff1a8', hlInk:'#1d2330', hlMsg:'#fff8d6', checkbar:'#1d2330', onCheckbar:'#ffffff',
    chk:'#1d2330', onChk:'#ffffff', waitBadge:'#fff4e0', onWaitBadge:'#8a5a00',
    focus:'#2f5bea', code:'#eef1f6', codeInk:'#1d2330', danger:'#b42318', overlay:'rgba(17,20,28,.45)',
    pic:'#ffffff', picInk:'#1d2330', picLine:'#6b7280', picNode:'#eef2ff', picNodeLine:'#2f5bea',
    curve:'#2f5bea', mark:'#c27c0e', grid:'#e3e6ec'
  },
  // Q "light fixes", option A: every border and divider darkened to 3:1.
  lightFixA: { line:'#8a919d', line2:'#8a919d', ctl:'#8a919d', track:'#d5d9e0',
    ok:'#1a7f45', prog:'#a8690a', mute:'#5f6673', grid:'#b9bfca', picLine:'#5f6673', mark:'#a8690a' },
  // Option B: dividers stay faint (they are decoration); controls, bars and picture lines reach 3:1.
  lightFixB: { ctl:'#868d9a', track:'#d5d9e0', ok:'#1a7f45', prog:'#a8690a', mute:'#5f6673',
    grid:'#d5d9e0', picLine:'#5f6673', mark:'#a8690a' },
  // Q "dark look": three drafts.
  darkA: { // Neutral grey
    page:'#0b0c0e', bg:'#16181c', surface:'#1f2227', surface2:'#262a30', raise:'#2a2e35',
    ink:'#e6e8eb', mute:'#a0a7b2', line:'#30353d', line2:'#2a2e35', ctl:'#7a828f',
    accent:'#8aa4ff', accentFill:'#3a5fe0', onAccent:'#ffffff', sel:'#25304d',
    sys:'#272c34', sysInk:'#d5d9e0', warn:'#3a2f15', warnInk:'#f2dca8', stop:'#3d2224', stopInk:'#f3c9c9',
    care:'#173326', careInk:'#bfe6cf', ok:'#5cc995', prog:'#e5a740', track:'#3a3f48',
    hl:'#6b5a12', hlInk:'#fff6cc', hlMsg:'#3a3418', checkbar:'#e6e8eb', onCheckbar:'#16181c',
    chk:'#e6e8eb', onChk:'#16181c', waitBadge:'#3a2f15', onWaitBadge:'#f2c46b',
    focus:'#8aa4ff', code:'#272c34', codeInk:'#e6e8eb', danger:'#ff8a80', overlay:'rgba(0,0,0,.6)',
    pic:'#1f2227', picInk:'#e6e8eb', picLine:'#a0a7b2', picNode:'#25304d', picNodeLine:'#8aa4ff',
    curve:'#8aa4ff', mark:'#e5a740', grid:'#3a3f48'
  },
  darkB: { // Blue slate
    page:'#050914', bg:'#0f172a', surface:'#1a2438', surface2:'#222e45', raise:'#26334c',
    ink:'#e2e8f0', mute:'#9aa8bd', line:'#2c3a52', line2:'#26334a', ctl:'#71829c',
    accent:'#8fa9ff', accentFill:'#3b5fe0', onAccent:'#ffffff', sel:'#263a66',
    sys:'#22304a', sysInk:'#d3dbe7', warn:'#3a2f17', warnInk:'#f2dca8', stop:'#3f2129', stopInk:'#f3c9cf',
    care:'#14352b', careInk:'#bfe6d4', ok:'#5ccb9b', prog:'#e8aa45', track:'#33425c',
    hl:'#665a1c', hlInk:'#fff6cc', hlMsg:'#33331f', checkbar:'#3b5fe0', onCheckbar:'#ffffff',
    chk:'#3b5fe0', onChk:'#ffffff', waitBadge:'#3a2f17', onWaitBadge:'#f2c46b',
    focus:'#8fa9ff', code:'#22304a', codeInk:'#e2e8f0', danger:'#ff8f8f', overlay:'rgba(2,6,16,.65)',
    pic:'#1a2438', picInk:'#e2e8f0', picLine:'#9aa8bd', picNode:'#263a66', picNodeLine:'#8fa9ff',
    curve:'#8fa9ff', mark:'#e8aa45', grid:'#33425c'
  },
  darkC: { // Near-black
    page:'#000000', bg:'#000000', surface:'#0e0f11', surface2:'#17181b', raise:'#1c1d21',
    ink:'#f2f2f3', mute:'#a6a8ae', line:'#2a2b30', line2:'#1f2024', ctl:'#76787f',
    accent:'#90a8ff', accentFill:'#3a5fe0', onAccent:'#ffffff', sel:'#1d2640',
    sys:'#1a1b1f', sysInk:'#dcdde0', warn:'#332810', warnInk:'#f2dca8', stop:'#361b1d', stopInk:'#f3c9c9',
    care:'#112b20', careInk:'#bfe6cf', ok:'#5cc995', prog:'#e5a740', track:'#2e2f35',
    hl:'#5e5010', hlInk:'#fff6cc', hlMsg:'#2b2712', checkbar:'#f2f2f3', onCheckbar:'#000000',
    chk:'#f2f2f3', onChk:'#000000', waitBadge:'#332810', onWaitBadge:'#f2c46b',
    focus:'#90a8ff', code:'#1a1b1f', codeInk:'#f2f2f3', danger:'#ff8a80', overlay:'rgba(0,0,0,.7)',
    pic:'#0e0f11', picInk:'#f2f2f3', picLine:'#a6a8ae', picNode:'#1d2640', picNodeLine:'#90a8ff',
    curve:'#90a8ff', mark:'#e5a740', grid:'#2e2f35'
  }
};

// The pairs AA cares about: [foreground, background, kind, where it shows].
// text = 4.5:1, ui = 3:1 (large text, interface parts, the parts of a picture needed to read it).
var PAIRS = [
  ['ink','bg','text','Body text on the page'], ['ink','surface','text','Text on bars, sidebar, cards'],
  ['mute','surface','text','Secondary text (dates, counts) on cards'], ['mute','bg','text','Secondary text on the page'],
  ['accent','surface','text','Links on cards'], ['accent','bg','text','Links on the page'],
  ['onAccent','accentFill','text','Your message; primary buttons'], ['ink','sel','text','The open session in the list'], ['mute','sel','text','The open session\'s date'],
  ['sysInk','sys','text','Crux line: information'], ['warnInk','warn','text','Crux line: warning'],
  ['stopInk','stop','text','Crux line: stop'], ['careInk','care','text','Crux line: care'],
  ['ok','surface','text','"Passed" and other green text'], ['onWaitBadge','waitBadge','text','"Waiting" badge'],
  ['onChk','chk','text','"Check" badge'], ['onCheckbar','checkbar','text','Mastery check bar'],
  ['hlInk','hl','text','Matched words in a snippet'], ['ink','hlMsg','text','The matched message, highlighted'],
  ['codeInk','code','text','Maths KaTeX cannot draw'], ['danger','surface','text','"Close account"'],
  ['ink','raise','text','Text in a dialog'], ['picInk','pic','text','Words in a diagram or graph'],
  ['ctl','surface','ui','Border of a text box, tick or button'], ['focus','surface','ui','Focus ring on a card'],
  ['focus','bg','ui','Focus ring on the page'], ['prog','track','ui','Progress bar against its track'],
  ['prog','surface','ui','Progress bar against the card'], ['ok','track','ui','Full bar against its track'],
  ['accentFill','bg','ui','Your message bubble against the page'], ['checkbar','bg','ui','Check bar against the page'],
  ['picLine','pic','ui','Diagram arrows, graph axes'], ['picNodeLine','pic','ui','Diagram box borders'],
  ['curve','pic','ui','The graph\'s curve'], ['mark','pic','ui','Marked points on a graph'],
  ['hl','surface','info','Snippet highlight against its card (matched words are also bold)']
];

function themeTokens(theme, pal, light) {
  var base = Object.assign({}, TOKENS.lightDraft);
  if (theme === 'light') {
    if (light === 'A') Object.assign(base, TOKENS.lightFixA);
    if (light === 'B') Object.assign(base, TOKENS.lightFixB);
    return base;
  }
  return Object.assign(base, TOKENS['dark' + (pal || 'A')]);
}

function lum(hex) {
  var h = hex.replace('#', ''), c = [0, 2, 4].map(function (i) { return parseInt(h.substr(i, 2), 16) / 255; });
  c = c.map(function (v) { return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}
function ratio(a, b) { var x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); }

if (typeof module !== 'undefined') module.exports = { TOKENS: TOKENS, PAIRS: PAIRS, themeTokens: themeTokens, ratio: ratio };
