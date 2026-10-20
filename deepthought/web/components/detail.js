// Right-hand panels of the run view: test / group / stage details and the diff.
import { html, useState } from '../vendor/preact-htm.mjs';
import { api, toast, store } from '../app.js';
import { CopyButton, FAILED, STATUS, StatusPill, Visible, decodeUtf8, openInEditor } from './ui.js';

// ------------------------------------------------------------------ diff
function commonPrefix(a, b) {
  let i = 0;
  while (i < a.length && i < b.length && a[i] === b[i]) i++;
  return i;
}

function commonSuffix(a, b, prefix) {
  let i = 0;
  while (i < a.length - prefix && i < b.length - prefix && a[a.length - 1 - i] === b[b.length - 1 - i]) i++;
  return i;
}

// One string with the part that differs from `other` highlighted.
function Marked({ text, other, kind, allSpaces }) {
  if (text == null) return html`<span class="vis-null">(null)</span>`;
  if (other == null) return html`<${Visible} text=${text} allSpaces=${allSpaces} />`;
  const p = commonPrefix(text, other);
  const s = commonSuffix(text, other, p);
  const mid = text.slice(p, text.length - s);
  return html`<${Visible} text=${text.slice(0, p)} allSpaces=${allSpaces} />${mid
    ? html`<mark class=${'d-' + kind}><${Visible} text=${mid} allSpaces=${allSpaces} /></mark>`
    : html`<mark class=${'d-' + kind + ' d-missing'}>${kind === 'exp' ? '' : ''}</mark>`
  }<${Visible} text=${text.slice(text.length - s)} allSpaces=${allSpaces} />`;
}

function splitLines(t) {
  if (t == null) return [];
  const parts = t.split('\n');
  return parts.map((l, i) => (i < parts.length - 1 ? l + '\n' : l)).filter((l, i) => i < parts.length - 1 || l !== '');
}

// Line-level LCS for moderately sized texts; positional fallback for huge ones.
function lineDiff(a, b) {
  const n = a.length;
  const m = b.length;
  if (n * m > 250000) {
    const rows = [];
    for (let i = 0; i < Math.max(n, m); i++) rows.push({ e: a[i], a: b[i], same: a[i] === b[i] });
    return rows;
  }
  const dp = Array.from({ length: n + 1 }, () => new Int32Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) {
    dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  }
  const rows = [];
  let i = 0;
  let j = 0;
  while (i < n || j < m) {
    if (i < n && j < m && a[i] === b[j]) { rows.push({ e: a[i], a: b[j], same: true }); i++; j++; }
    else if (i < n && j < m && dp[i + 1][j + 1] >= Math.max(dp[i + 1][j], dp[i][j + 1])) { rows.push({ e: a[i], a: b[j] }); i++; j++; }
    else if (j < m && (i >= n || dp[i][j + 1] >= dp[i + 1][j])) { rows.push({ e: undefined, a: b[j] }); j++; }
    else { rows.push({ e: a[i], a: undefined }); i++; }
  }
  return rows;
}

export function Diff({ expected, actual }) {
  const [allSpaces, setAllSpaces] = useState(false);
  const multiline = (expected && expected.includes('\n') && expected.indexOf('\n') < expected.length - 1)
    || (actual && actual.includes('\n') && actual.indexOf('\n') < actual.length - 1);
  const toggle = html`<label class="small dim toggle"><input type="checkbox" checked=${allSpaces}
    onChange=${(e) => setAllSpaces(e.target.checked)} /> show all spaces</label>`;
  const showLen = (expected || '').length > 8 || (actual || '').length > 8 || /[\x00-\x1f\x7f-\xff]/.test((expected || '') + (actual || ''));
  const lengths = html`<span class="small dim">${showLen ? `expected ${expected == null ? 'NULL' : expected.length + ' byte(s)'} · got ${actual == null ? 'NULL' : actual.length + ' byte(s)'}` : ''}</span>`;
  if (!multiline) {
    return html`<div class="diff">
      <div class="diff-row"><span class="diff-tag exp">expected</span><code class="diff-val"><${Marked} text=${expected} other=${actual} kind="exp" allSpaces=${allSpaces} /></code></div>
      <div class="diff-row"><span class="diff-tag act">actual</span><code class="diff-val"><${Marked} text=${actual} other=${expected} kind="act" allSpaces=${allSpaces} /></code></div>
      <div class="diff-foot">${lengths}${toggle}</div>
    </div>`;
  }
  const rows = lineDiff(splitLines(expected), splitLines(actual));
  let ln = 0;
  return html`<div class="diff">
    <table class="diff-table">
      <thead><tr><th></th><th>expected</th><th>actual</th></tr></thead>
      <tbody>${rows.map((r) => {
        ln++;
        return html`<tr class=${r.same ? 'same' : 'changed'}>
          <td class="ln">${ln}</td>
          <td>${r.e === undefined ? html`<span class="vis-null">—</span>` : html`<${Marked} text=${r.e} other=${r.same ? null : r.a} kind="exp" allSpaces=${allSpaces} />`}</td>
          <td>${r.a === undefined ? html`<span class="vis-null">—</span>` : html`<${Marked} text=${r.a} other=${r.same ? null : r.e} kind="act" allSpaces=${allSpaces} />`}</td>
        </tr>`;
      })}</tbody>
    </table>
    <div class="diff-foot">${lengths}${toggle}</div>
  </div>`;
}

// ------------------------------------------------------------------ source
function Source({ test, lines }) {
  if (!test.source) return null;
  const marks = new Set(lines);
  return html`<pre class="source">${test.source.split('\n').map((l, i) => {
    const n = test.line + i;
    return html`<div class=${'src-line' + (marks.has(n) ? ' hit' : '')}><span class="src-ln">${n}</span>${l || ' '}</div>`;
  })}</pre>`;
}

function basename(p) {
  return (p || '').split('/').pop();
}

// ------------------------------------------------------------------ panels
export function TestDetail({ run, group, test }) {
  const failed = FAILED.has(test.status);
  const rerunOne = async () => {
    try {
      await api('POST', `/api/runs/${run.id}/rerun`, { tids: [test.tid] });
      toast(`Re-running ${test.id}…`, 'info', 1500);
    } catch (e) { toast(e.message, 'error'); }
  };
  const assertLines = test.asserts.filter((a) => a.file === test.file).map((a) => a.line);
  const explain = EXPLAIN[test.status];
  return html`<div class="detail">
    <div class="detail-head">
      <${StatusPill} status=${test.status}>${test.status === 'crash' && test.signal ? test.signal : null}<//>
      ${test.regression && html`<span class="pill pill-regression">regression</span>`}
      ${test.fixed && html`<span class="pill pill-pass">fixed</span>`}
      ${test.carried && html`<span class="pill pill-skip" title="result carried over from the previous run">previous run</span>`}
      <span class="grow"></span>
      ${test.ms ? html`<span class="dim small">${test.ms} ms</span>` : ''}
    </div>
    <h2 class="test-title">${test.id}</h2>
    <div class="dim">${group.name}</div>
    ${test.desc && html`<p class="desc">${test.desc}</p>`}

    ${test.reason && html`<div class=${'reason reason-' + test.status}><strong>${STATUS[test.status]?.label || test.status}:</strong> <span class="pre">${test.reason}</span></div>`}
    ${explain && failed && html`<div class="hint">💡 ${explain}</div>`}

    ${test.asserts.length > 0 && html`<section>
      <h4>Failed checks <span class="count">${test.asserts.length}</span></h4>
      ${test.asserts.map((a) => html`<div class="assert">
        <div class="assert-head">
          <code>${a.msg}</code>
          ${a.file && html`<a class="loc" href="#" onClick=${(e) => { e.preventDefault(); openInEditor(a.file, a.line); }}>${basename(a.file)}:${a.line}</a>`}
        </div>
        ${a.context && html`<pre class="source context">${a.context.code.split('\n').map((l, i) => html`<div class=${'src-line' + (a.context.start + i === a.line ? ' hit' : '')}><span class="src-ln">${a.context.start + i}</span>${l || ' '}</div>`)}</pre>`}
        <${Diff} expected=${a.expected} actual=${a.actual} />
      </div>`)}
    </section>`}

    ${test.leaks && html`<section><h4>Memory</h4><div class="reason reason-leak">
      Leaked <strong>${test.leaks.bytes}</strong> byte(s) in <strong>${test.leaks.count}</strong> allocation(s)
      that were still allocated when the test finished.
    </div></section>`}

    ${test.logs.length > 0 && html`<section><h4>Notes</h4>${test.logs.map((l) => html`<div class="note">· ${l}</div>`)}</section>`}

    ${test.output && html`<section><h4>Output <span class="dim small">(stdout/stderr of the test)</span></h4>
      <pre class="output"><${Visible} text=${decodeUtf8(test.output)} /></pre></section>`}

    <section>
      <h4>Test code ${test.file && html`<a class="loc" href="#" onClick=${(e) => { e.preventDefault(); openInEditor(test.file, test.line); }}>${basename(test.file)}:${test.line}</a>`}</h4>
      <${Source} test=${test} lines=${assertLines} />
    </section>

    ${test.repro && html`<section>
      <h4>Reproduce in your terminal</h4>
      <pre class="cmd">${test.repro}</pre>
      <div class="row gap">
        <${CopyButton} text=${test.repro} label="Copy command" />
        <button class="btn btn-sm" onClick=${rerunOne}>↻ Re-run this test</button>
      </div>
    </section>`}
  </div>`;
}

const EXPLAIN = {
  crash: 'The test process was killed by a signal. Look for NULL pointers, freed memory, or reads/writes past the end of a buffer. Re-run with “Sanitizer” enabled for the exact line.',
  timeout: 'The test did not finish in time: usually an infinite loop (a missing increment, a wrong stop condition) or a read() waiting forever.',
  leak: 'Memory allocated during the test was never freed. Check every return path, especially error paths after a failed malloc.',
  build_error: 'The tests could not be compiled against your code: a missing function, a wrong prototype, or a header that does not compile.',
  error: 'The harness could not run this test properly. See the output below.',
};

export function GroupDetail({ run, group }) {
  const counts = {};
  for (const t of group.tests) counts[t.status] = (counts[t.status] || 0) + 1;
  return html`<div class="detail">
    <div class="detail-head"><${StatusPill} status=${group.status} /><span class="pill">${group.category}</span><span class="pill">${group.runner}</span></div>
    <h2 class="test-title">${group.name}</h2>
    ${group.message && html`<p class="desc">${group.message}</p>`}
    <div class="row gap wrap">${Object.entries(counts).map(([k, v]) => html`<${StatusPill} status=${k}>${v} ${STATUS[k]?.label.toLowerCase()}<//>`)}</div>
    ${group.build_cmd && html`<section><h4>Compile command</h4><pre class="cmd">${group.build_cmd}</pre><${CopyButton} text=${group.build_cmd} /></section>`}
    ${group.build_log && html`<section><h4>Build log</h4><pre class=${'output' + (group.status === 'build_error' ? ' bad' : '')}>${group.build_log}</pre></section>`}
    ${group.cwd && html`<section><h4>Test folder</h4><code class="small">${group.cwd}</code></section>`}
  </div>`;
}

export function StageDetail({ stage, project }) {
  const norm = stage.id.startsWith('norminette');
  return html`<div class="detail">
    <div class="detail-head"><${StatusPill} status=${stage.status} />${stage.ms ? html`<span class="dim small">${stage.ms} ms</span>` : ''}</div>
    <h2 class="test-title">${stage.name}</h2>
    ${stage.message && html`<p class="desc">${stage.message}</p>`}
    ${stage.hint && html`<div class="hint">💡 <code>${stage.hint}</code> <${CopyButton} text=${stage.hint} /></div>`}
    ${norm && stage.items.length > 0 && html`<section><h4>Norm errors <span class="count">${stage.items.length}</span></h4>
      <table class="table"><tbody>${stage.items.map((it) => html`<tr>
        <td><a class="loc" href="#" onClick=${(e) => { e.preventDefault(); openInEditor(project + '/' + it.file, it.line); }}>${it.file}:${it.line}:${it.col}</a></td>
        <td><code class="small">${it.code}</code></td><td>${it.msg}</td></tr>`)}</tbody></table></section>`}
    ${!norm && stage.items.length > 0 && html`<section><h4>Details</h4><ul class="checklist">${stage.items.map((it) => html`
      <li class=${it.ok ? 'ok' : 'ko'}>${it.ok ? '✓' : '✗'} <code>${it.label}</code> ${it.note && html`<span class="dim small">${it.note}</span>`}</li>`)}</ul></section>`}
    ${stage.log && html`<section><h4>Log</h4><pre class="output">${stage.log}</pre></section>`}
  </div>`;
}

export function Summary({ run, onSelect }) {
  const score = run.score;
  const failing = [];
  const info = [];
  for (const g of run.groups) for (const t of g.tests) if (FAILED.has(t.status)) (g.category === 'extra' ? info : failing).push([g, t]);
  const builds = run.groups.filter((g) => g.status === 'build_error' && !g.tests.length);
  const FLAGS = {
    norminette: 'Norminette errors: the moulinette gives 0 for norm errors.',
    forbidden: 'A forbidden function is used: this is a 0 at evaluation.',
    relink: 'The Makefile relinks: evaluators will check this.',
    rules: 'A required Makefile rule is missing.',
    files: 'A required file is missing.',
    build: 'The project does not build.',
  };
  return html`<div class="detail">
    <h2 class="test-title">Summary</h2>
    ${run.status === 'running' && html`<p class="dim">Tests are running… results appear live.</p>`}
    ${run.error && html`<div class="reason reason-error"><strong>Engine error</strong><pre>${run.error}</pre></div>`}
    ${score && html`<div class="score-grid">
      ${['mandatory', 'bonus'].map((k) => score[k] && score[k].total > 0 && html`<div class="score-card">
        <div class="dim small">${k}</div>
        <div class="big">${score[k].passed}<span class="dim">/${score[k].total}</span></div>
        <div class="bar"><div style=${`width:${score[k].pct || 0}%`} class=${score[k].pct === 100 ? 'ok' : 'ko'}></div></div>
      </div>`)}
      ${score.regressions > 0 && html`<div class="score-card"><div class="dim small">regressions</div><div class="big" style="color:var(--timeout)">${score.regressions}</div><div class="small dim">passed last run, fail now</div></div>`}
      ${score.fixed > 0 && html`<div class="score-card"><div class="dim small">fixed</div><div class="big" style="color:var(--pass)">${score.fixed}</div><div class="small dim">since last run</div></div>`}
    </div>`}
    ${score && score.flags.length > 0 && html`<section><h4>Evaluation warnings</h4>
      ${score.flags.map((f) => html`<div class="reason reason-fail">⚠ ${FLAGS[f] || f}</div>`)}</section>`}
    ${builds.length > 0 && html`<section><h4>Groups that did not build</h4>${builds.map((g) => html`
      <div class="fail-row" onClick=${() => onSelect({ type: 'group', gid: g.gid })}><span class="st st-build_error">⚒</span> ${g.name} <span class="dim small">${g.message}</span></div>`)}</section>`}
    ${failing.length > 0 && html`<section><h4>Failing tests <span class="count">${failing.length}</span></h4>
      ${failing.map(([g, t]) => html`<div class="fail-row" onClick=${() => onSelect({ type: 'test', gid: g.gid, id: t.id })}>
        <span class=${'st st-' + t.status}>${STATUS[t.status].icon}</span> <code>${t.id}</code>
        <span class="dim small ellipsis">${t.reason ? t.reason.split('\n')[0] : t.desc}</span>
        ${t.regression && html`<span class="pill pill-regression">regression</span>`}</div>`)}</section>`}
    ${info.length > 0 && html`<section><h4>Informational differences <span class="count">${info.length}</span></h4>
      <p class="small dim">Groups marked “info” are not graded: they show where your project differs from a reference on behaviour the subject does not require.</p>
      ${info.map(([g, t]) => html`<div class="fail-row" onClick=${() => onSelect({ type: 'test', gid: g.gid, id: t.id })}>
        <span class="st st-warn">~</span> <code>${t.id}</code> <span class="dim small ellipsis">${g.name}</span></div>`)}</section>`}
    ${score && !failing.length && !builds.length && run.status === 'done' && html`<div class="celebrate">
      <div class="big">🎉</div><div>Every test passed. Don't forget: evaluators may test things no tester thinks of.</div></div>`}
  </div>`;
}

export { store };
