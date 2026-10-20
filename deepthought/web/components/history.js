// History of a project: past runs, and a comparison of two runs.
import { html, useEffect, useState } from '../vendor/preact-htm.mjs';
import { api, loadRun, projectHref, toast } from '../app.js';
import { Empty, FAILED, StatusIcon, timeAgo } from './ui.js';

function Compare({ a, b }) {
  const [ra, setRa] = useState(null);
  const [rb, setRb] = useState(null);
  useEffect(() => {
    Promise.all([loadRun(a), loadRun(b)]).then(([x, y]) => { setRa(x); setRb(y); }).catch((e) => toast(e.message, 'error'));
  }, [a, b]);
  if (!ra || !rb) return html`<p class="dim">Loading…</p>`;
  const before = new Map();
  for (const g of ra.groups) for (const t of g.tests) before.set(t.tid, t.status);
  const rows = [];
  for (const g of rb.groups) for (const t of g.tests) {
    const old = before.get(t.tid);
    if (old !== t.status) rows.push({ t, old, g });
  }
  return html`<div class="card">
    <h4>Changes from ${ra.id} to ${rb.id}</h4>
    ${rows.length ? html`<table class="table"><tbody>${rows.map(({ t, old, g }) => html`<tr>
      <td><${StatusIcon} status=${old || 'pending'} /> → <${StatusIcon} status=${t.status} /></td>
      <td><code>${t.id}</code></td><td class="dim small">${g.name}</td>
      <td>${FAILED.has(t.status) && old === 'pass' ? html`<span class="pill pill-regression">regression</span>` : t.status === 'pass' && FAILED.has(old) ? html`<span class="pill pill-pass">fixed</span>` : ''}</td>
    </tr>`)}</tbody></table>` : html`<p class="dim">No test changed status.</p>`}
  </div>`;
}

export function HistoryPage({ path }) {
  const [runs, setRuns] = useState(null);
  const [pick, setPick] = useState([]);
  useEffect(() => { api('GET', `/api/history?project=${encodeURIComponent(path)}`).then(setRuns).catch((e) => toast(e.message, 'error')); }, [path]);
  if (!runs) return html`<div class="boot">Loading…</div>`;
  const toggle = (id) => setPick((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id].slice(-2)));
  return html`<div class="history">
    <div class="row gap page-head"><h1 class="grow">History — ${path.split('/').pop()}</h1><a class="btn" href=${projectHref(path)}>← Back to the project</a></div>
    <p class="dim small">Tick two runs to compare them.</p>
    ${runs.length ? html`<div class="list">${runs.map((r) => html`<div class="list-row">
      <input type="checkbox" checked=${pick.includes(r.id)} onChange=${() => toggle(r.id)} />
      <${StatusIcon} status=${r.status === 'done' ? (r.score && r.score.verdict === 'ok' ? 'pass' : 'fail') : r.status} />
      <a href=${'#/run/' + r.id} class="mono">${r.id}</a>
      <span class="dim small">${new Date(r.started * 1000).toLocaleString()} · ${timeAgo(r.started)}</span>
      ${r.options && r.options.sanitize && html`<span class="tag">sanitizer</span>`}
      <span class="grow"></span>
      ${r.score && r.score.regressions > 0 && html`<span class="pill pill-regression">${r.score.regressions} regression(s)</span>`}
      ${r.score && r.score.fixed > 0 && html`<span class="pill pill-pass">${r.score.fixed} fixed</span>`}
      <strong>${r.score ? r.score.grade : '—'}</strong><span class="dim small">/100</span>
    </div>`)}</div>` : html`<${Empty} title="No runs yet" />`}
    ${pick.length === 2 && html`<${Compare} a=${[...pick].sort()[0]} b=${[...pick].sort()[1]} />`}
  </div>`;
}
