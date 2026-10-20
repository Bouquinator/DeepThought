// Small shared UI pieces.
import { html, useState } from '../vendor/preact-htm.mjs';
import { api, store, toast, useStore } from '../app.js';

export const STATUS = {
  pass: { icon: '✓', label: 'Passed' },
  fail: { icon: '✗', label: 'Failed' },
  crash: { icon: '✸', label: 'Crashed' },
  timeout: { icon: '⏱', label: 'Timeout' },
  leak: { icon: '◍', label: 'Leak' },
  error: { icon: '!', label: 'Error' },
  build_error: { icon: '⚒', label: 'Build error' },
  skip: { icon: '–', label: 'Skipped' },
  warn: { icon: '!', label: 'Warning' },
  pending: { icon: '·', label: 'Pending' },
  running: { icon: '◌', label: 'Running' },
  done: { icon: '✓', label: 'Done' },
  cancelled: { icon: '■', label: 'Cancelled' },
};

export const FAILED = new Set(['fail', 'crash', 'timeout', 'leak', 'error', 'build_error']);

export function StatusIcon({ status, size }) {
  const s = STATUS[status] || STATUS.pending;
  return html`<span class=${`st st-${status} ${size || ''}`} title=${s.label}>${s.icon}</span>`;
}

export function StatusPill({ status, children }) {
  const s = STATUS[status] || STATUS.pending;
  return html`<span class=${`pill pill-${status}`}>${s.icon} ${children || s.label}</span>`;
}

export function Logo() {
  return html`<svg class="logo" viewBox="0 0 64 64" aria-hidden="true">
    <rect width="64" height="64" rx="14" fill="var(--accent)" />
    <text x="32" y="43" font-size="30" font-family="ui-monospace, monospace" font-weight="800" text-anchor="middle" fill="#000">42</text>
  </svg>`;
}

export function GradeRing({ score, size = 96, running }) {
  const grade = score ? score.grade : null;
  const pct = grade == null ? 0 : Math.min(grade, 125) / 125;
  const r = 42;
  const c = 2 * Math.PI * r;
  const ok = score && score.verdict === 'ok' && grade >= 100;
  const color = grade == null ? 'var(--dim)' : ok ? 'var(--pass)' : grade >= 50 ? 'var(--leak)' : 'var(--fail)';
  return html`
    <div class=${'ring' + (running ? ' spinning' : '')} style=${`width:${size}px;height:${size}px`}>
      <svg viewBox="0 0 100 100">
        <circle cx="50" cy="50" r=${r} class="ring-bg" />
        <circle cx="50" cy="50" r=${r} class="ring-fg" stroke=${color}
          stroke-dasharray=${`${c * pct} ${c}`} transform="rotate(-90 50 50)" />
        ${grade >= 100 && html`<circle cx="50" cy="50" r=${r - 7} class="ring-bonus" stroke="var(--accent)"
          stroke-dasharray=${`${2 * Math.PI * (r - 7) * Math.max(0, (grade - 100) / 25)} 999`} transform="rotate(-90 50 50)" />`}
      </svg>
      <div class="ring-label" style=${`font-size:${Math.round(size * 0.16)}px`}>
        <strong style=${`color:${color}`}>${grade == null ? '—' : grade}</strong>
        <span>/100</span>
      </div>
    </div>`;
}

export function Progress({ done, total, failed }) {
  const pct = total ? (100 * done) / total : 0;
  const fpct = total ? (100 * failed) / total : 0;
  return html`<div class="progress" title=${`${done}/${total}`}>
    <div class="progress-ok" style=${`width:${pct - fpct}%`}></div>
    <div class="progress-ko" style=${`width:${fpct}%`}></div>
  </div>`;
}

export function Modal({ title, onClose, children, wide }) {
  return html`
    <div class="modal-back" onClick=${(e) => e.target === e.currentTarget && onClose()}>
      <div class=${'modal' + (wide ? ' wide' : '')} role="dialog" aria-label=${title}>
        <div class="modal-head"><h3>${title}</h3><button class="icon-btn" onClick=${onClose}>✕</button></div>
        <div class="modal-body">${children}</div>
      </div>
    </div>`;
}

export function Toasts() {
  const s = useStore();
  return html`<div class="toasts">${s.toasts.map((t) => html`<div key=${t.id} class=${'toast toast-' + t.kind}>${t.message}</div>`)}</div>`;
}

export function UpdateBanner() {
  const s = useStore();
  const [busy, setBusy] = useState(false);
  const [hidden, setHidden] = useState(false);
  if (!s.update || !s.update.available || hidden) return null;
  const doUpdate = async () => {
    setBusy(true);
    try {
      const r = await api('POST', '/api/self/update');
      toast(r.message, r.ok ? 'success' : 'error', 10000);
      if (r.ok) store.set({ update: r.status });
    } catch (e) {
      toast(e.message, 'error');
    }
    setBusy(false);
  };
  return html`<div class="banner">
    <span>⬆ A DeepThought update is available (${s.update.behind} new commit${s.update.behind > 1 ? 's' : ''}).</span>
    ${(s.update.changes || []).slice(0, 3).map((c) => html`<code class="dim small">${c}</code>`)}
    <span class="grow"></span>
    <button class="btn btn-primary btn-sm" disabled=${busy} onClick=${doUpdate}>${busy ? 'Updating…' : 'Update now'}</button>
    <button class="icon-btn" onClick=${() => setHidden(true)}>✕</button>
  </div>`;
}

export function copy(text) {
  const done = () => toast('Copied to clipboard', 'success', 1500);
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(done, () => fallbackCopy(text, done));
  } else {
    fallbackCopy(text, done);
  }
}

function fallbackCopy(text, done) {
  const ta = document.createElement('textarea');
  ta.value = text;
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand('copy'); done(); } catch (e) { /* ignore */ }
  ta.remove();
}

export function CopyButton({ text, label }) {
  return html`<button class="btn btn-sm" onClick=${() => copy(text)}>⧉ ${label || 'Copy'}</button>`;
}

export function timeAgo(ts) {
  if (!ts) return 'never';
  const d = Date.now() / 1000 - ts;
  if (d < 60) return 'just now';
  if (d < 3600) return `${Math.floor(d / 60)} min ago`;
  if (d < 86400) return `${Math.floor(d / 3600)} h ago`;
  return new Date(ts * 1000).toLocaleDateString();
}

export function openInEditor(path, line) {
  api('POST', '/api/open', { path, line }).catch((e) => toast(e.message, 'error'));
}

// The C harness sends raw bytes as code points 0..255. Program output is
// usually UTF-8 text: decode it when it is valid UTF-8 (comparison values
// are left as bytes, so a diff stays byte-exact).
export function decodeUtf8(text) {
  if (!text || !/[\x80-\xff]/.test(text) || /[^\x00-\xff]/.test(text)) return text;
  try {
    const bytes = Uint8Array.from(text, (c) => c.charCodeAt(0));
    return new TextDecoder('utf-8', { fatal: true }).decode(bytes);
  } catch (e) {
    return text;
  }
}

// Render a string with invisible characters made visible.
// The C harness maps raw bytes to code points 0..255, so \u00XX == byte XX.
export function Visible({ text, allSpaces, className }) {
  if (text == null) return html`<span class="vis-null">(null)</span>`;
  const out = [];
  let buf = '';
  const flush = () => { if (buf) { out.push(buf); buf = ''; } };
  const trailing = text.length - text.replace(/ +$/, '').length;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    const code = ch.charCodeAt(0);
    if (ch === '\n') { flush(); out.push(html`<span class="ws">↵</span>`); out.push('\n'); }
    else if (ch === '\t') { flush(); out.push(html`<span class="ws">→</span>`); out.push('\t'); }
    else if (ch === ' ' && (allSpaces || i >= text.length - trailing)) { flush(); out.push(html`<span class="ws">·</span>`); }
    else if (code === 0) { flush(); out.push(html`<span class="esc">\\0</span>`); }
    else if (code < 32 || (code >= 127 && code <= 255)) {
      flush();
      out.push(html`<span class="esc">\\x${code.toString(16).padStart(2, '0')}</span>`);
    } else buf += ch;
  }
  flush();
  return html`<span class=${className || ''}>${out}</span>`;
}

export function Empty({ title, children }) {
  return html`<div class="empty"><div class="empty-title">${title}</div>${children}</div>`;
}
