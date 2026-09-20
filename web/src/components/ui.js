// Tiny hyperscript helper. The whole app renders by replacing subtrees, so a
// DOM builder beats string templates for keeping listeners attached.

export function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props ?? {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
    else if (k === 'html') el.innerHTML = v;
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === 'dataset') Object.assign(el.dataset, v);
    else el.setAttribute(k, v === true ? '' : String(v));
  }
  append(el, children);
  return el;
}

/** Replace an element's children, filtering out null/undefined/false. */
export function fill(el, ...children) {
  el.textContent = '';
  append(el, children);
  return el;
}

function append(el, children) {
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
}

export function svg(pathMarkup, { size = 20, stroke = 'currentColor', width = 1.8, fill = 'none' } = {}) {
  const s = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  s.setAttribute('width', size);
  s.setAttribute('height', size);
  s.setAttribute('viewBox', '0 0 24 24');
  s.setAttribute('fill', fill);
  s.setAttribute('stroke', stroke);
  s.setAttribute('stroke-width', width);
  s.setAttribute('stroke-linecap', 'round');
  s.setAttribute('stroke-linejoin', 'round');
  s.setAttribute('aria-hidden', 'true');
  s.innerHTML = pathMarkup;
  return s;
}

// Lucide-flavoured glyphs, inlined so the app ships no icon dependency.
export const icons = {
  // A flame over a bench: the Hearth & Bench mark.
  mark: '<path d="M12 3c2.5 3.2 4.5 5.1 4.5 8a4.5 4.5 0 0 1-9 0c0-1.6.8-2.9 2-4.3"/><path d="M4 19h16"/><path d="M6.5 19v2M17.5 19v2"/>',
  flame: '<path d="M12 3c2.5 3.2 4.5 5.1 4.5 8a4.5 4.5 0 0 1-9 0c0-1.6.8-2.9 2-4.3"/>',
  bench: '<path d="M4 19h16"/><path d="M6.5 19v2M17.5 19v2"/><path d="M4 14h16"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
  bell: '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/>',
  chevronDown: '<path d="m6 9 6 6 6-6"/>',
  external: '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><path d="M15 3h6v6"/><path d="M10 14 21 3"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  gift: '<rect x="3" y="8" width="18" height="4" rx="1"/><path d="M12 8v13M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/><path d="M7.5 8a2.5 2.5 0 0 1 0-5C10 3 12 8 12 8s2-5 4.5-5a2.5 2.5 0 0 1 0 5"/>',
  tag: '<path d="M12.6 2.6a2 2 0 0 0-1.4-.6H4a2 2 0 0 0-2 2v7.2a2 2 0 0 0 .6 1.4l8.2 8.2a2 2 0 0 0 2.8 0l7.2-7.2a2 2 0 0 0 0-2.8z"/><circle cx="6.5" cy="6.5" r="1.2"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  arrowRight: '<path d="M5 12h14M12 5l7 7-7 7"/>',
  calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
  ticket: '<path d="M2 9a3 3 0 0 1 0 6v3a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-3a3 3 0 0 1 0-6V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2z"/><path d="M13 5v2M13 11v2M13 17v2"/>',
  message: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  alert: '<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
  share: '<path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><path d="M16 6l-4-4-4 4"/><path d="M12 2v13"/>',
};

export const money = (cents) =>
  (cents / 100).toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: cents % 100 ? 2 : 0 });

export const matchDate = (iso) =>
  new Date(iso).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });

export const matchTime = (iso) =>
  new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });

export const shortDate = (iso) =>
  new Date(iso).toLocaleDateString('en-US', { month: 'numeric', day: 'numeric' });

export const relative = (iso) => {
  const mins = Math.round((Date.now() - new Date(iso)) / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
};

export function avatar(member, { lg = false } = {}) {
  if (!member) {
    return h('div', { class: `avatar${lg ? ' avatar--lg' : ''} avatar--empty`, title: 'Open seat' }, '+');
  }
  return h('div', {
    class: `avatar${lg ? ' avatar--lg' : ''}`,
    style: { background: member.colour },
    title: member.name,
    'aria-label': member.name,
  }, member.initials);
}

export function badge(text, kind = 'mute') {
  return h('span', { class: `badge badge--${kind}` }, text);
}

export function toggle(checked, label, onChange, { ember = false } = {}) {
  return h('button', {
    class: `switch${ember ? ' switch--ember' : ''}`,
    type: 'button',
    role: 'switch',
    'aria-checked': String(checked),
    'aria-label': label,
    onclick: () => onChange(!checked),
  });
}

/** Filter chips that carry a filled selected state, not aria alone. */
export function chipRow(options, active, onPick, { stone = false } = {}) {
  return h('div', { class: 'scroll-row', role: 'tablist' },
    options.map((o) => {
      const value = typeof o === 'string' ? o : o.value;
      const label = typeof o === 'string' ? o : o.label;
      return h('button', {
        class: `chip${stone ? ' chip--stone' : ''}`,
        type: 'button',
        role: 'tab',
        'aria-selected': String(value === active),
        onclick: () => onPick(value),
      }, label);
    }),
  );
}

let sheetHost = null;

export function openSheet(node) {
  closeSheet();
  const sheet = h('div', { class: 'sheet', role: 'dialog', 'aria-modal': 'true' },
    h('div', { class: 'sheet__handle' }),
    node,
  );
  sheetHost = h('div', {
    class: 'sheet-backdrop',
    onclick: (e) => { if (e.target === sheetHost) closeSheet(); },
  }, sheet);
  document.body.append(sheetHost);
  document.body.style.overflow = 'hidden';
  document.addEventListener('keydown', onEsc);
  (sheet.querySelector('button, input, textarea, [tabindex]') ?? sheet).focus?.();
}

function onEsc(e) { if (e.key === 'Escape') closeSheet(); }

export function closeSheet() {
  if (!sheetHost) return;
  sheetHost.remove();
  sheetHost = null;
  document.body.style.overflow = '';
  document.removeEventListener('keydown', onEsc);
}

/** A drag-and-drop slot for a public-domain player photo. */
export function photoSlot(playerId, size, current, onDrop) {
  const slot = h('div', {
    class: 'photo-slot',
    style: { width: `${size}px`, height: `${size}px` },
    role: 'button',
    tabindex: '0',
    'aria-label': 'Drop a player photo here',
  });

  const paint = () => {
    slot.textContent = '';
    if (current) slot.append(h('img', { src: current, alt: '' }));
    else slot.append(h('span', { class: 'photo-slot__caption' }, 'Photo'));
  };
  paint();

  const read = (file) => {
    if (!file || !file.type.startsWith('image/')) return;
    const fr = new FileReader();
    fr.onload = () => onDrop(fr.result);
    fr.readAsDataURL(file);
  };

  slot.addEventListener('dragover', (e) => { e.preventDefault(); slot.classList.add('is-over'); });
  slot.addEventListener('dragleave', () => slot.classList.remove('is-over'));
  slot.addEventListener('drop', (e) => {
    e.preventDefault();
    slot.classList.remove('is-over');
    read(e.dataTransfer?.files?.[0]);
  });
  const pick = () => {
    const input = h('input', { type: 'file', accept: 'image/*', style: { display: 'none' } });
    input.addEventListener('change', () => read(input.files[0]));
    document.body.append(input);
    input.click();
    input.remove();
  };
  slot.addEventListener('click', pick);
  slot.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(); } });

  return slot;
}
