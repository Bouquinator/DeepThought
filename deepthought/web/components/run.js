// The run view: header, stages, test tree and the detail panel.
import { html, useEffect, useMemo, useRef, useState } from '../vendor/preact-htm.mjs';
import { api, go, loadRun, projectHref, refreshState, startRun, store, toast, useStore } from '../app.js';
import { GroupDetail, StageDetail, Summary, TestDetail } from './detail.js';
import { Empty, FAILED, GradeRing, Modal, Progress, STATUS, StatusIcon, StatusPill, timeAgo } from './ui.js';

const FILTERS = [
  ['all', 'All'],
  ['failed', 'Failed'],
  ['passed', 'Passed'],
  ['skipped', 'Skipped'],
  ['suite', 'Suite problems'],  // shown only when there are some
];

function matchesFilter(t, filter, q) {
  if (filter === 'failed' && !FAILED.has(t.status)) return false;
  if (filter === 'passed' && t.status !== 'pass') return false;
  if (filter === 'skipped' && t.status !== 'skip') return false;
  if (filter === 'suite' && t.status !== 'suite_error') return false;
  if (q) {
    const hay = `${t.id} ${t.desc}`.toLowerCase();
    if (!hay.includes(q)) return false;
  }
  return true;
}

function counts(run) {
  let total = 0;
  let done = 0;
  let failed = 0;
  let suite = 0;  // problems of the test suite itself: not the student's fault
  for (const g of run.groups) {
    for (const t of g.tests) {
      total++;
      if (!['pending', 'running'].includes(t.status)) done++;
      if (FAILED.has(t.status) && g.category !== 'extra') failed++;
      if (t.status === 'suite_error') suite++;
    }
    if (g.status === 'build_error' && !g.tests.length) { total++; done++; failed++; }
    if (g.status === 'suite_error' && !g.tests.length) { total++; done++; suite++; }
  }
  return { total, done, failed, suite };
}

// ------------------------------------------------------------------ build options
export function BuildOptions({ project, onClose, onSaved }) {
  const s = useStore();
  const proj = s.projects.find((p) => p.path === project) || { build: {} };
  const b = proj.build || {};
  const [command, setCommand] = useState(b.command || '');
  const [makeArgs, setMakeArgs] = useState(b.make_args || '');
  const [env, setEnv] = useState(Object.entries(b.env || {}).map(([k, v]) => `${k}=${v}`).join('\n'));
  const [clean, setClean] = useState(!!b.clean);
  const save = async (andRun) => {
    try {
      await api('POST', '/api/projects/build', { path: project, build: { command, make_args: makeArgs, env, clean } });
      await refreshState();
      toast('Build options saved', 'success', 2000);
      onClose();
      if (andRun && onSaved) onSaved();
    } catch (e) { toast(e.message, 'error'); }
  };
  const isPython = (proj.default_build || '').startsWith('python');
  return html`<${Modal} title="Build options for this project" onClose=${onClose}>
    <p class="small dim">Used every time this project is tested or re-tested (in the isolated copy, never in your folder).</p>
    <div class="form">
      <label>Build command <span class="dim small">(empty = the suite's default)</span>
        <input class="input mono" value=${command} placeholder=${proj.default_build || 'no build step'} onInput=${(e) => setCommand(e.target.value)} />
        <span class="dim small help">${isPython
          ? 'Python projects get an automatic syntax check. Replace it with any command, e.g. python3 -m compileall -q {project}'
          : 'Placeholders: {project} = the project copy. E.g. make -C {project} re'}</span>
      </label>
      <label>Extra make arguments
        <input class="input mono" value=${makeArgs} placeholder="e.g.  bonus   CFLAGS=-O2   CC=gcc" onInput=${(e) => setMakeArgs(e.target.value)} />
        <span class="dim small help">Appended to the build's make command. Variables (X=Y) are also passed to the suites' extra make steps (e.g. make bonus).</span>
      </label>
      <label>Environment variables <span class="dim small">(one KEY=VALUE per line)</span>
        <textarea class="input mono" rows="3" value=${env} onInput=${(e) => setEnv(e.target.value)} placeholder="BUFFER_SIZE=42"></textarea>
      </label>
      <label class="row gap check"><input type="checkbox" checked=${clean} onChange=${(e) => setClean(e.target.checked)} /> <span>Always build from scratch (make fclean first)</span></label>
      <div class="row gap"><span class="grow"></span>
        <button class="btn" onClick=${onClose}>Cancel</button>
        <button class="btn" onClick=${() => save(false)}>Save</button>
        <button class="btn btn-primary" onClick=${() => save(true)}>Save & retest</button>
      </div>
    </div>
  <//>`;
}

// ------------------------------------------------------------------ project type & suites
export function ProjectSuites({ project, onClose, onSaved }) {
  const s = useStore();
  const proj = s.projects.find((p) => p.path === project) || { linked: [], suites: [], kind: '', mode: 'auto' };
  const [kind, setKind] = useState(proj.kind_manual ? proj.kind || '' : '');
  const [chosen, setChosen] = useState(proj.mode === 'linked');
  const [picked, setPicked] = useState(new Set(proj.mode === 'linked' ? proj.linked : proj.suites));
  const toggle = (uid) => { const n = new Set(picked); n.has(uid) ? n.delete(uid) : n.add(uid); setPicked(n); setChosen(true); };
  const byKind = {};
  for (const x of s.suites) (byKind[x.project] = byKind[x.project] || []).push(x);
  const effectiveKind = kind.trim() || proj.kind;
  const save = async (andRun) => {
    try {
      await api('POST', '/api/projects/config', { path: project, kind: kind.trim(), suites: chosen ? [...picked] : [] });
      await refreshState();
      toast('Project saved', 'success', 1500);
      onClose();
      if (andRun && onSaved) onSaved();
    } catch (e) { toast(e.message, 'error'); }
  };
  return html`<${Modal} title=${'Suites for ' + project.split('/').pop()} onClose=${onClose} wide>
    <div class="form">
      <label>Project type <span class="dim small">(empty = detect automatically${proj.mode === 'auto' && proj.kind ? `: ${proj.kind}` : ''})</span>
        <input class="input mono" list="dt-kinds" value=${kind} placeholder=${proj.mode === 'auto' && proj.kind ? proj.kind : 'e.g. libft, pipex, my_project…'}
          onInput=${(e) => setKind(e.target.value)} />
        <datalist id="dt-kinds">${(s.kinds || []).map((k) => html`<option value=${k} />`)}</datalist>
        <span class="dim small help">Any name works, even for projects DeepThought doesn't know: suites made for that type (their <code>project</code>) run automatically.</span>
      </label>
      <div>
        <label class="row gap check"><input type="radio" checked=${!chosen} onChange=${() => setChosen(false)} />
          <span>Automatic: every enabled suite for <strong>${effectiveKind || 'the detected type'}</strong></span></label>
        <label class="row gap check"><input type="radio" checked=${chosen} onChange=${() => setChosen(true)} />
          <span>Only the suites I choose below (any suite, whatever project it was made for)</span></label>
      </div>
      <div class="picker suite-picker">
        ${Object.keys(byKind).sort().map((k) => html`<div class="pick-kind">${k}</div>
          ${byKind[k].map((x) => html`<label class=${'pick-row' + (x.enabled ? '' : ' dim')}>
            <input type="checkbox" checked=${chosen ? picked.has(x.uid) : proj.suites.includes(x.uid)} onChange=${() => toggle(x.uid)} />
            <strong>${x.name}</strong> <span class="dim small">${x.uid} · ${x.source}</span>
            ${!x.enabled && html`<span class="tag">disabled</span>`}
          </label>`)}`)}
        ${!s.suites.length && html`<div class="pick-empty dim">No suite installed.</div>`}
      </div>
      <p class="small dim">No suite fits? <a href="#/suites">Create or import one</a> and link it to this project.</p>
      <div class="row gap"><span class="grow"></span>
        <button class="btn" onClick=${onClose}>Cancel</button>
        <button class="btn" onClick=${() => save(false)}>Save</button>
        <button class="btn btn-primary" onClick=${() => save(true)}>Save & run</button>
      </div>
    </div>
  <//>`;
}

// ------------------------------------------------------------------ header
function RunHeader({ run, project }) {
  const s = useStore();
  const { total, done, failed, suite } = counts(run);
  const running = run.status === 'running' || run.status === 'pending';
  const [opts, setOpts] = useState({ sanitize: !!run.options.sanitize, leaks: run.options.leaks !== false });
  const [buildOpen, setBuildOpen] = useState(false);
  const [suitesOpen, setSuitesOpen] = useState(false);
  const build = run.options.build;
  const proj = s.projects.find((p) => p.path === run.project.path) || {};

  const rerunAll = async (clean) => {
    const r = await startRun(run.project.path, { ...opts, clean: !!clean }, run.options.suites);
    if (r && location.hash.startsWith('#/run/')) go(projectHref(run.project.path));
  };
  const rerunFailed = async () => {
    try {
      const r = await api('POST', `/api/runs/${run.id}/rerun`, { failed_only: true, options: opts });
      store.state.latest[run.project.path] = r.id;
      store.changed();
      if (location.hash.startsWith('#/run/')) go(projectHref(run.project.path));
    } catch (e) { toast(e.message, 'error'); }
  };
  const cancel = () => api('POST', `/api/runs/${run.id}/cancel`).catch((e) => toast(e.message, 'error'));
  const toggleWatch = async () => {
    try {
      await api('POST', '/api/watch', { project: run.project.path, enabled: !proj.watching, options: opts, suites: run.options.suites });
      toast(!proj.watching ? 'Watching: tests re-run every time you save a file' : 'Watch mode off', 'info', 2500);
    } catch (e) { toast(e.message, 'error'); }
  };

  useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.metaKey || e.ctrlKey) return;
      if (e.key === 'r' && !running) { e.preventDefault(); rerunAll(false); }
      if (e.key === 'f' && !running && (failed || suite)) { e.preventDefault(); rerunFailed(); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  return html`<div class="run-head">
    <${GradeRing} score=${run.score} running=${running} />
    <div class="run-title">
      <div class="row gap wrap">
        <h1>${run.project.name}</h1>
        <span class="pill pill-kind">${run.project.kind}</span>
        <${StatusPill} status=${run.status === 'done' ? (failed ? 'fail' : suite ? 'suite_error' : 'pass') : run.status}>${run.status === 'done' ? (failed ? `${failed} failing` : suite ? 'incomplete' : 'all green') : null}<//>
        ${suite > 0 && html`<span class="pill pill-suite_error" title="Problems in the test suite itself, not in your code. Not graded.">⚠ ${suite} suite problem${suite > 1 ? 's' : ''}</span>`}
        ${proj.watching && html`<span class="pill pill-watch">👀 watching</span>`}
      </div>
      <div class="dim small mono ellipsis" title=${run.project.path}>${run.project.path}</div>
      <div class="dim small">
        ${run.suites.map((x) => html`<span class="suite-chip">${x.name} <span class="dim">v${x.version}</span></span>`)}
        · run ${run.id} · ${timeAgo(run.started)}${run.base_run ? ' · re-run of failed tests' : ''}
      </div>
      ${build && html`<div class="dim small mono ellipsis" title="Build options of this project">⚙ ${[
        build.command, build.make_args && `make args: ${build.make_args}`,
        build.env && Object.entries(build.env).map(([k, v]) => `${k}=${v}`).join(' '), build.clean && 'clean build',
      ].filter(Boolean).join(' · ')}</div>`}
      <${Progress} done=${done} total=${total} failed=${failed} />
      <div class="dim small">${done}/${total} tests${failed ? html` · <span class="fail-text">${failed} failing</span>` : ''}</div>
    </div>
    <div class="run-actions">
      ${running
        ? html`<button class="btn btn-danger" onClick=${cancel}>■ Stop</button>`
        : html`<button class="btn btn-primary" onClick=${() => rerunAll(false)} title="Sync, rebuild what changed and run everything (r)">↻ Retest all</button>
            <button class="btn" disabled=${!failed && !suite} onClick=${rerunFailed} title="Re-run only failing tests and suite problems (f)">↻ Retest failed</button>`}
      <div class="row gap">
        <button class=${'btn btn-sm' + (proj.watching ? ' btn-on' : '')} onClick=${toggleWatch} title="Re-run automatically when you save a file">👀 Watch</button>
        <button class="btn btn-sm" disabled=${running} onClick=${() => rerunAll(true)} title="make fclean, then rebuild from scratch">Clean build</button>
        <button class=${'btn btn-sm' + (proj.build && Object.keys(proj.build).length ? ' btn-on' : '')} onClick=${() => setBuildOpen(true)} title="Build command, make arguments, environment">⚙ Build</button>
        <button class=${'btn btn-sm' + (proj.mode && proj.mode !== 'auto' ? ' btn-on' : '')} onClick=${() => setSuitesOpen(true)} title="Project type and the suites that run for it">☰ Suites</button>
      </div>
      ${suitesOpen && html`<${ProjectSuites} project=${run.project.path} onClose=${() => setSuitesOpen(false)} onSaved=${() => rerunAll(false)} />`}
      ${buildOpen && html`<${BuildOptions} project=${run.project.path} onClose=${() => setBuildOpen(false)} onSaved=${() => rerunAll(false)} />`}
      <div class="row gap small">
        <label class="toggle" title="Rebuild with AddressSanitizer + UBSan: exact crash location"><input type="checkbox" checked=${opts.sanitize} onChange=${(e) => setOpts({ ...opts, sanitize: e.target.checked })} /> Sanitizer</label>
        <label class="toggle" title="Fail tests that leak memory"><input type="checkbox" checked=${opts.leaks} onChange=${(e) => setOpts({ ...opts, leaks: e.target.checked })} /> Leaks</label>
        <a class="small" href=${'#/history' + run.project.path}>History</a>
      </div>
    </div>
  </div>`;
}

function Stages({ run, sel, onSelect }) {
  return html`<div class="stages">${run.stages.filter((st) => st.id !== 'workspace' || st.status === 'error').map((st) => html`
    <button class=${'stage stage-' + st.status + (sel && sel.type === 'stage' && sel.id === st.id ? ' selected' : '')}
      onClick=${() => onSelect({ type: 'stage', id: st.id })} title=${st.message}>
      <${StatusIcon} status=${st.status} /> ${st.name}
    </button>`)}</div>`;
}

// ------------------------------------------------------------------ tree
function Tree({ run, sel, onSelect, filter, q }) {
  const [collapsed, setCollapsed] = useState({});
  const bySuite = run.suites.map((s) => ({ ...s, groups: run.groups.filter((g) => g.suite === s.uid) }));
  const multi = bySuite.length > 1;
  return html`<div class="tree">${bySuite.map((s) => html`
    ${multi && html`<div class="tree-suite">${s.name}</div>`}
    ${s.groups.map((g) => {
      const tests = g.tests.filter((t) => matchesFilter(t, filter, q));
      const nPass = g.tests.filter((t) => t.status === 'pass').length;
      const nRun = g.tests.filter((t) => t.status !== 'skip' && t.status !== 'suite_error').length;  // graded tests
      const open = collapsed[g.gid] === undefined ? true : !collapsed[g.gid];
      const emptyShown = g.status === 'build_error' || (g.status === 'suite_error' && ['all', 'suite'].includes(filter));
      if (!tests.length && filter !== 'all' && !emptyShown) return null;
      return html`<div class="tree-group">
        <div class=${'tree-row group-row' + (sel && sel.type === 'group' && sel.gid === g.gid ? ' selected' : '')}
          onClick=${() => onSelect({ type: 'group', gid: g.gid })}>
          <span class="caret" onClick=${(e) => { e.stopPropagation(); setCollapsed({ ...collapsed, [g.gid]: open }); }}>${open ? '▾' : '▸'}</span>
          <${StatusIcon} status=${g.status} />
          <span class="grow ellipsis">${g.name}</span>
          ${g.category === 'bonus' && html`<span class="tag">bonus</span>`}
          ${g.category === 'extra' && html`<span class="tag" title="informational: not graded">info</span>`}
          <span class="dim small">${g.tests.length ? `${nPass}/${nRun}` : g.status === 'skip' ? 'skipped' : ''}</span>
        </div>
        ${open && tests.map((t) => html`
          <div key=${t.tid} class=${'tree-row test-row' + (sel && sel.type === 'test' && sel.gid === g.gid && sel.id === t.id ? ' selected' : '') + (t.carried ? ' carried' : '')}
            onClick=${() => onSelect({ type: 'test', gid: g.gid, id: t.id })} title=${t.desc}>
            <${StatusIcon} status=${t.status} />
            <span class="grow ellipsis mono">${t.id}</span>
            ${t.regression && html`<span class="tag tag-reg">reg</span>`}
            ${t.leaks && html`<span class="tag tag-leak">leak</span>`}
          </div>`)}
      </div>`;
    })}`)}</div>`;
}

function flatTests(run, filter, q) {
  const out = [];
  for (const g of run.groups) for (const t of g.tests) if (matchesFilter(t, filter, q)) out.push({ type: 'test', gid: g.gid, id: t.id });
  return out;
}

// ------------------------------------------------------------------ view
export function RunView({ run }) {
  const [sel, setSel] = useState(null);
  const [filter, setFilter] = useState('all');
  const [q, setQ] = useState('');
  const searchRef = useRef(null);
  const ql = q.trim().toLowerCase();

  useEffect(() => { setSel(null); }, [run.id]);

  // j/k navigation, / to search
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === '/' && e.target.tagName !== 'INPUT') { e.preventDefault(); searchRef.current && searchRef.current.focus(); return; }
      if (e.target.tagName === 'INPUT' || e.metaKey || e.ctrlKey) return;
      if (e.key !== 'j' && e.key !== 'k' && e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
      const list = flatTests(run, filter, ql);
      if (!list.length) return;
      e.preventDefault();
      const idx = sel && sel.type === 'test' ? list.findIndex((x) => x.gid === sel.gid && x.id === sel.id) : -1;
      const next = e.key === 'j' || e.key === 'ArrowDown' ? Math.min(idx + 1, list.length - 1) : Math.max(idx - 1, 0);
      setSel(list[next]);
      requestAnimationFrame(() => {
        const el = document.querySelector('.tree-row.selected');
        if (el) el.scrollIntoView({ block: 'nearest' });
      });
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  let detail;
  if (sel && sel.type === 'test') {
    const g = run.groups.find((x) => x.gid === sel.gid);
    const t = g && g.tests.find((x) => x.id === sel.id);
    detail = t ? html`<${TestDetail} run=${run} group=${g} test=${t} />` : null;
  } else if (sel && sel.type === 'group') {
    const g = run.groups.find((x) => x.gid === sel.gid);
    detail = g ? html`<${GroupDetail} run=${run} group=${g} />` : null;
  } else if (sel && sel.type === 'stage') {
    const st = run.stages.find((x) => x.id === sel.id);
    detail = st ? html`<${StageDetail} stage=${st} project=${run.project.path} />` : null;
  }
  if (!detail) detail = html`<${Summary} run=${run} onSelect=${setSel} />`;

  const nFailed = run.groups.reduce((n, g) => n + (g.category === 'extra' ? 0 : g.tests.filter((t) => FAILED.has(t.status)).length), 0);
  const nSuite = counts(run).suite;
  return html`<div class="run">
    <${RunHeader} run=${run} />
    <${Stages} run=${run} sel=${sel} onSelect=${setSel} />
    <div class="run-body">
      <aside class="side">
        <div class="side-tools">
          <input ref=${searchRef} class="input search" placeholder="Search tests  ( / )" value=${q} onInput=${(e) => setQ(e.target.value)} />
          <div class="chips">${FILTERS.filter(([k]) => k !== 'suite' || nSuite || filter === 'suite').map(([k, label]) => html`
            <button class=${'chip' + (filter === k ? ' on' : '') + (k === 'suite' ? ' chip-suite' : '')} onClick=${() => setFilter(k)}>
              ${label}${k === 'failed' && nFailed ? html` <span class="count">${nFailed}</span>` : ''}${k === 'suite' && nSuite ? html` <span class="count">${nSuite}</span>` : ''}</button>`)}
            <button class=${'chip' + (!sel ? ' on' : '')} onClick=${() => setSel(null)} title="Summary">Σ</button>
          </div>
        </div>
        <${Tree} run=${run} sel=${sel} onSelect=${setSel} filter=${filter} q=${ql} />
        <div class="side-foot dim small">j/k navigate · r retest · f retest failed · / search</div>
      </aside>
      <section class="main">${detail}</section>
    </div>
  </div>`;
}

export function RunPage({ id }) {
  const s = useStore();
  const [err, setErr] = useState('');
  useEffect(() => { loadRun(id).catch((e) => setErr(e.message)); }, [id]);
  const run = s.runs[id];
  if (err) return html`<${Empty} title="Run not found"><p>${err}</p><a href="#/">Back to projects</a><//>`;
  if (!run) return html`<div class="boot">Loading run…</div>`;
  const latest = s.latest[run.project.path];
  return html`
    ${latest && latest !== id && html`<div class="banner info">A newer run exists for this project. <a href=${'#/run/' + latest}>Open it →</a></div>`}
    <${RunView} run=${run} />`;
}

// The project page always shows the most recent run of the project and
// follows new runs (watch mode, re-runs) automatically.
export function ProjectPage({ path }) {
  const s = useStore();
  const proj = s.projects.find((p) => p.path === path);
  const runId = s.latest[path] || (proj && (proj.active_run || proj.last_run));
  const [err, setErr] = useState('');
  const [buildOpen, setBuildOpen] = useState(false);
  useEffect(() => {
    if (runId && !s.runs[runId]) loadRun(runId).catch((e) => setErr(e.message));
  }, [runId]);
  const run = runId && s.runs[runId];
  if (run) return html`<${RunView} run=${run} />`;
  if (runId && !err) return html`<div class="boot">Loading…</div>`;
  const [suitesOpen, setSuitesOpen] = useState(false);
  const ready = proj && proj.suites && proj.suites.length > 0;
  return html`<${Empty} title=${proj ? proj.name : path.split('/').pop()}>
    <p class="mono dim">${path}</p>
    ${ready
      ? html`<p>Project type <span class="pill pill-kind">${proj.kind || 'custom'}</span> — ${proj.suites.length} suite(s) will run${proj.mode === 'linked' ? ' (chosen by you)' : ''}.</p>
          <p class="small dim">Build: <code>${(proj.build && proj.build.command) || proj.default_build || 'none'}</code>${proj.build && proj.build.make_args ? html` + <code>${proj.build.make_args}</code>` : ''}</p>`
      : html`<p>No suite runs for this project yet${proj && proj.kind ? html` (type <span class="pill pill-kind">${proj.kind}</span>)` : ''}.</p>
          <p class="small">Choose suites for it (any suite, even one made for another project), give it a type, or <a href="#/suites">create a suite</a>.</p>`}
    <div class="row gap" style="justify-content:center">
      ${ready && html`<button class="btn btn-primary btn-lg" onClick=${() => startRun(path)}>▶ Run the tests</button>`}
      <button class=${'btn btn-lg' + (ready ? '' : ' btn-primary')} onClick=${() => setSuitesOpen(true)}>☰ Suites${ready ? '' : ' for this project'}</button>
      <button class="btn btn-lg" onClick=${() => setBuildOpen(true)}>⚙ Build options</button>
    </div>
    ${buildOpen && html`<${BuildOptions} project=${path} onClose=${() => setBuildOpen(false)} onSaved=${() => startRun(path)} />`}
    ${suitesOpen && html`<${ProjectSuites} project=${path} onClose=${() => setSuitesOpen(false)} onSaved=${() => startRun(path)} />`}
  <//>`;
}

export { STATUS };
