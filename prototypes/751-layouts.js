// ---------- Variant A: conversation + objectives rail (desktop) / pull-down strip (phone) ----------
const ui = { sheet:false };
function VariantA(sc, phone) {
  const shown = Object.values(sc.st).filter(s => s==='sh'||s==='pa').length;
  const inCheck = sc.mode === 'check';
  const railBody = inCheck
    ? `<div class="h">Mastery check</div><div class="sub">Closed book: no notes, no searching and no other AI.</div>
       <div class="pdots" style="margin:10px 0">${Array.from({length:sc.n},(_,i)=>`<span class="${i<sc.done?'done':''} ${i===sc.k-1?'cur':''}" style="border-color:#666;color:#333">${i+1}</span>`).join('')}</div>
       <div class="card"><div class="sub">Files</div>Hidden until the result</div>
       <div class="card" style="margin-top:8px"><div class="sub">Earlier teaching</div>Hidden until the result</div>`
    : `<div class="h">${TOPIC}</div><div class="sub">from ${FILE}</div><div style="margin-top:8px">${objList(sc)}</div>
       ${sc.paused ? pausedHtml() : ''}
       <div style="margin-top:12px"><div class="sub">Your preferences</div>${prefsHtml()}</div>
       <div style="margin-top:12px"><div class="sub">Files</div><div class="chip">${FILE}</div>
         ${sc.flag ? '<div class="papernote" style="font-size:12px;cursor:pointer">Option A: Slide 30: possible error, ask your teacher. <u>Tell the tutor what they said</u></div>' : ''}</div>
       ${sc.notice ? `<div class="notice" style="margin-top:12px">Tell us what you think, 1 minute <b>&times;</b></div>` : ''}`;
  const head = inCheck
    ? `<div class="checkbar"><span>Mastery check &middot; Problem ${sc.k} of ${sc.n}</span><span>closed book</span></div>`
    : '';
  const stripTxt = inCheck ? '' : `<div class="strip" data-act="sheet"><span>Objectives: ${shown} of 5 shown or passed</span><span>${ui.sheet?'&#9650;':'&#9660;'}</span></div>`;
  const how = {
    popup: (it) => `<div class="sysline ${it.k}">${it.h}</div>`,
  };
  const body = `<div class="body"><div style="flex:1;display:flex;flex-direction:column;min-width:0;position:relative">
      ${phone ? stripTxt : ''}${head}
      ${phone && ui.sheet && !inCheck ? `<div class="sheet" style="top:${37}px">${railBody}</div>` : ''}
      <div class="thread">${phone && sc.notice ? `<div class="notice">Tell us what you think, 1 minute <b>&times;</b></div>` : ''}${thread(sc, how)}</div>
      ${composer(sc)}</div>
      ${phone ? '' : `<aside class="rail">${railBody}</aside>`}</div>`;
  return topbar(inCheck ? TOPIC : TOPIC, `<span class="link">Sessions</span><span class="link">Feedback</span>`) + body;
}

// ---------- Variant B: everything is in the conversation; pinned lines above the composer ----------
function VariantB(sc, phone) {
  const inCheck = sc.mode === 'check';
  const pins = [];
  const how = {
    objectives: () => `<div class="msg tutor" style="max-width:96%"><div class="who">Tutor &middot; your objectives</div><b>${TOPIC}</b><div class="sub">from ${FILE}</div>${objList(sc)}
        <div class="sub" style="margin-top:6px">Say "go", "I know some of this", or ask for a change.</div></div>`,
    popup: (it) => { pins.push(`<div class="pin ${it.k}">${it.h} <b style="float:right;cursor:pointer">&times;</b></div>`); return ''; },
    problem: (it) => `<div class="msg tutor" style="border:2px solid #1d2330"><div class="who">Problem ${it.k} of ${it.n}</div><b>${it.h}</b></div>`,
  };
  let inner = thread(sc, how);
  if (inCheck) inner = `<div class="stickyhead"><span>Mastery check &middot; Problem ${sc.k} of ${sc.n}</span><span>closed book</span></div>
     <div class="collapsed">Earlier teaching and your files are hidden until the result.</div>` + inner;
  if (sc.notice) pins.push(`<div class="pin info">Tell us what you think, 1 minute <b style="float:right">&times;</b></div>`);
  // B keeps a one-line status pill instead of a panel
  const shown = Object.values(sc.st).filter(s => s==='sh'||s==='pa').length;
  const pill = inCheck ? '' : `<span class="chip" title="Opens your objectives message">Objectives ${shown}/5</span>`;
  const menuLinks = `<span class="link" title="Preferences, paused topics, files and sessions live in this menu">&#9776;</span>`;
  return topbar(TOPIC, pill + menuLinks) +
    `<div class="body" style="flex-direction:column"><div class="thread">${inner}
       ${!inCheck && sc.paused ? `<div class="sysline">Paused: ${PAUSED.name} (${PAUSED.note}). Say "resume ${PAUSED.name}" to go back.</div>` : ''}</div>
     <div class="pins">${pins.join('')}</div>${composer(sc)}</div>`;
}

// ---------- Variant C: progress strip; the check is a separate exam-paper screen; Crux's own lines as pop-ups ----------
function VariantC(sc, phone) {
  const segs = OBJ.map(o => `<div class="seg ${sc.st[o.n]}" title="${o.n}. ${o.t}: ${LBL[sc.st[o.n]]}"></div>`).join('');
  const shown = Object.values(sc.st).filter(s => s==='sh'||s==='pa').length;
  const segbar = `<div class="segs" data-act="sheet">${segs}<span class="cap">${shown} of 5 &middot; tap for details</span></div>`;
  const overlays = [];
  const toasts = [];
  if (sc.mode === 'check' || sc.mode === 'result') {
    // the paper: no chat at all
    const probs = sc.items.filter(i => i.t === 'problem');
    const p = probs[probs.length-1];
    const notes = sc.items.filter(i => i.t==='tutor' || i.t==='sys').map(i => `<div class="papernote">${i.h}</div>`).join('');
    const buttons = sc.items.find(i => i.t==='buttons');
    let content;
    if (sc.mode === 'result') {
      content = `<div class="sub">Mastery check &middot; result</div>${resultHtml(sc.items[0])}${notes}<div class="row"><span class="btn primary">Back to teaching</span></div>`;
    } else {
      const answered = sc.items.some(i => i.t==='photo') ? '<div class="photo" style="margin-top:8px">photo of working</div>' : '';
      const marking = sc.items.some(i => i.t==='marking') ? '<div class="marking" style="margin-top:10px"><span class="dots">Marking</span></div>' : '';
      content = `<div style="display:flex;justify-content:space-between"><span class="sub">Mastery check &middot; closed book: no notes, no searching and no other AI</span><span class="sub">Problem ${sc.k} of ${sc.n}</span></div>
        <div class="pdots" style="margin:8px 0">${Array.from({length:sc.n},(_,i)=>`<span class="${i<sc.done?'done':''} ${i===sc.k-1?'cur':''}" style="border-color:#666;color:#333">${i+1}</span>`).join('')}</div>
        ${buttons ? `<div class="papernote">${sc.items[0].h}</div><div class="row">${buttons.b.map((b,i)=>`<span class="btn ${i===0?'primary':''}">${b}</span>`).join('')}</div>` : ''}
        ${p ? `<div class="q">${p.h}</div><textarea placeholder="Your answer, with working">${(sc.items.find(i=>i.t==='me')||{}).h||''}</textarea>${answered}
        <div class="row"><span class="btn">Add a photo of your working</span><span class="btn primary">Submit answer</span></div>` : ''}
        ${notes}${marking}`;
    }
    return topbar(TOPIC, `<span class="sub">files hidden</span>`) +
      `<div class="body"><div class="paper"><div class="sheetbox">${content}</div></div></div>`;
  }
  const how = {
    sys: (it) => { if (it.k==='stop' || it.k==='care') { overlays.push(`<div class="card"><div>${it.h}</div><div class="row"><span class="btn primary">OK</span></div></div>`); return `<div class="sysline ${it.k}" style="opacity:.6">${it.h.split('<br>')[0]}</div>`; }
                   toasts.push(it.h); return ''; },
    popup: (it) => { toasts.push(it.h); return ''; },
    tick: (it) => { overlays.push(`<div class="card">${tickHtml(it)}<div class="row"><span class="btn primary">OK</span></div></div>`); return ''; },
    age: () => { overlays.push(ageHtml()); return ''; },
    buttons: (it) => `<div class="row" style="align-self:flex-start">${it.b.map((b,i)=>`<span class="btn ${i===0?'primary':''}">${b}</span>`).join('')}</div>`,
  };
  const inner = thread(sc, how);
  const sheet = ui.sheet ? `<div class="sheet" style="top:0">${objList(sc)}${sc.paused?pausedHtml():''}<div style="margin-top:10px"><div class="sub">Your preferences</div>${prefsHtml()}</div></div>` : '';
  // only the first overlay is drawn at a time; the rest queue behind it
  const ov = overlays.length ? `<div class="overlay">${overlays[0]}${overlays.length>1?`<div class="sub" style="position:absolute;bottom:20px;color:#fff">+${overlays.length-1} more queued</div>`:''}</div>` : '';
  const ts = toasts.slice(0,2).map(h => `<div class="toast">${h}</div>`).join('') + (sc.notice ? `<div class="toast" style="background:#2f5bea">Tell us what you think, 1 minute</div>` : '');
  return topbar(TOPIC, `<span class="link">Sessions</span><span class="link">Feedback</span>`) + segbar +
    `<div class="body"><div style="flex:1;display:flex;flex-direction:column;min-width:0;position:relative">${sheet}
      <div class="thread">${inner}</div>${composer(sc)}${ts}${ov}</div></div>`;
}

const VARIANTS = [
  { key:'A', name:'Conversation + objectives rail', fn:VariantA,
    note:'Objectives, preferences, paused topics and files sit in a side rail (desktop) or a pull-down strip (phone). The check stays in the conversation, with a dark check bar; earlier teaching is gone from the thread. Crux\'s own lines are centred lines in the thread.' },
  { key:'B', name:'Everything in the conversation', fn:VariantB,
    note:'No panels. Objectives are a tutor message (the pill scrolls to it); preferences, paused topics and files sit behind the menu. The check is the same thread with a sticky check header. Limit pop-ups pin above the composer.' },
  { key:'C', name:'Progress strip + exam paper', fn:VariantC,
    note:'A segmented strip shows the 5 statuses at a glance (tap for details). The check leaves the chat for a separate paper screen, one problem per page. Crux\'s stops are pop-ups over the screen; lighter lines are toasts.' },
];
