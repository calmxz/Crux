// ---------- switcher (prototype only, not part of the design) ----------
const qp = new URLSearchParams(location.search);
let vi = Math.max(0, VARIANTS.findIndex(v => v.key === (qp.get('variant') || 'A')));
let scene = ORDER.includes(qp.get('scene')) ? qp.get('scene') : 'open';
let device = qp.get('device') === 'desktop' ? 'desktop' : 'phone';
const sel = document.getElementById('scene');
sel.innerHTML = ORDER.map(k => `<option value="${k}">${S[k].name}</option>`).join('');
function render() {
  const v = VARIANTS[vi], sc = S[scene], phone = device === 'phone';
  window.CURSC = sc;
  const d = document.getElementById('device');
  d.className = 'device ' + device;
  d.innerHTML = v.fn(sc, phone);
  document.getElementById('vlab').textContent = `${v.key} (${v.name})`;
  document.getElementById('dev').textContent = phone ? 'Phone' : 'Desktop';
  document.getElementById('note').innerHTML = `<p><b>PROTOTYPE, throwaway.</b> Variant ${v.key}: ${v.note} <i>Scene: ${sc.name}.</i> Red italic text has no spec wording yet.</p>`;
  sel.value = scene;
  const u = new URL(location); u.searchParams.set('variant', v.key); u.searchParams.set('scene', scene); u.searchParams.set('device', device);
  history.replaceState(null, '', u);
}
document.getElementById('prev').onclick = () => { vi = (vi + VARIANTS.length - 1) % VARIANTS.length; render(); };
document.getElementById('next').onclick = () => { vi = (vi + 1) % VARIANTS.length; render(); };
document.getElementById('dev').onclick = () => { device = device === 'phone' ? 'desktop' : 'phone'; render(); };
sel.onchange = () => { scene = sel.value; render(); };
document.addEventListener('keydown', e => {
  if (e.target.closest('input,textarea,select,[contenteditable]')) return;
  if (e.key === 'ArrowLeft') document.getElementById('prev').click();
  if (e.key === 'ArrowRight') document.getElementById('next').click();
});
render();
