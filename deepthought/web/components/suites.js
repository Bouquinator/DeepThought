// Suites: installed suites, import (git / zip / folder), create, discover.
import { html, useEffect, useState } from '../vendor/preact-htm.mjs';
import { api, refreshState, toast, useStore } from '../app.js';
import { FolderPicker } from './home.js';
import { Modal } from './ui.js';

const SOURCE_HELP = {
  builtin: 'shipped with DeepThought, updated with it',
  local: 'created with “New suite”, lives in ~/.deepthought/suites/local',
  folder: 'linked folder: edit the files and re-run, no reinstall needed',
  git: 'cloned git repository: can be updated',
  zip: 'imported from a zip archive',
};

function SuiteCard({ s }) {
  const [busy, setBusy] = useState(false);
  const act = async (fn, okMsg) => {
    setBusy(true);
    try {
      const r = await fn();
      toast(okMsg || r.message || 'done', 'success');
      await refreshState();
    } catch (e) { toast(e.message, 'error', 8000); }
    setBusy(false);
  };
  return html`<div class=${'card suite-card' + (s.enabled ? '' : ' disabled')}>
    <div class="row gap wrap">
      <strong>${s.name}</strong><span class="dim small">v${s.version}</span>
      <span class="pill pill-kind">${s.project}</span>
      <span class=${'pill src-' + s.source} title=${SOURCE_HELP[s.source]}>${s.source}</span>
      ${!s.compatible && html`<span class="pill pill-fail">incompatible</span>`}
      <span class="grow"></span>
      <label class="toggle small"><input type="checkbox" checked=${s.enabled} disabled=${busy}
        onChange=${(e) => act(() => api('POST', `/api/suites/${encodeURIComponent(s.uid)}/enable`, { enabled: e.target.checked }), e.target.checked ? 'enabled' : 'disabled')} /> enabled</label>
    </div>
    ${s.description && html`<p class="small">${s.description}</p>`}
    <div class="small dim">id <code>${s.uid}</code>${s.authors.length ? ` · by ${s.authors.join(', ')}` : ''}</div>
    <div class="small dim mono ellipsis" title=${s.path}>${s.origin && s.origin !== s.path ? s.origin : s.path}</div>
    <div class="groups">${s.groups.map((g) => html`<span class="tag" title=${g.description}>${g.name}${g.variants > 1 ? ` ×${g.variants}` : ''} · ${g.runner}</span>`)}
      ${s.checks.map((c) => html`<span class="tag tag-check">${c}</span>`)}</div>
    ${s.warnings.map((w) => html`<div class="small warn-text">⚠ ${w}</div>`)}
    <div class="row gap card-foot">
      ${s.source === 'git' && html`<button class="btn btn-sm" disabled=${busy} onClick=${() => act(() => api('POST', `/api/suites/${encodeURIComponent(s.uid)}/update`))}>⟳ Update</button>`}
      <a class="btn btn-sm" href=${`/api/suites/${encodeURIComponent(s.uid)}/pack`} download>⇩ Export .zip</a>
      ${s.source !== 'builtin' && html`<button class="btn btn-sm btn-danger-ghost" disabled=${busy}
        onClick=${() => confirm(`Remove ${s.name}?${s.source === 'folder' ? ' (the folder itself is kept)' : ''}`) && act(() => api('DELETE', `/api/suites/${encodeURIComponent(s.uid)}`), 'removed')}>Remove</button>`}
    </div>
  </div>`;
}

function ImportPanel() {
  const [tab, setTab] = useState('git');
  const [spec, setSpec] = useState('');
  const [ref, setRef] = useState('');
  const [trust, setTrust] = useState(false);
  const [busy, setBusy] = useState(false);
  const [picker, setPicker] = useState(false);
  const [drag, setDrag] = useState(false);
  const s = useStore();

  const add = async () => {
    if (!trust) return toast('Please confirm that you trust this suite first.', 'warn');
    setBusy(true);
    try {
      const r = await api('POST', '/api/suites/add', { spec, ref });
      toast(`Added ${r.name} (${r.project})`, 'success');
      setSpec('');
      await refreshState();
    } catch (e) { toast(e.message, 'error', 10000); }
    setBusy(false);
  };
  const upload = async (file) => {
    if (!trust) return toast('Please confirm that you trust this suite first.', 'warn');
    setBusy(true);
    try {
      const buf = await file.arrayBuffer();
      let r;
      try {
        r = await api('POST', `/api/suites/upload?filename=${encodeURIComponent(file.name)}`, undefined, buf);
      } catch (e) {
        if (!e.message.includes('already installed') || !confirm(`${e.message}\n\nReplace it?`)) throw e;
        r = await api('POST', `/api/suites/upload?replace=1&filename=${encodeURIComponent(file.name)}`, undefined, buf);
      }
      toast(`Imported ${r.name} (${r.project})`, 'success');
      await refreshState();
    } catch (e) { toast(e.message, 'error', 10000); }
    setBusy(false);
  };

  return html`<div class="card import">
    <div class="tabs">
      ${[['git', 'Git repository'], ['zip', 'Zip file'], ['folder', 'Local folder']].map(([k, l]) => html`
        <button class=${'tab' + (tab === k ? ' on' : '')} onClick=${() => { setTab(k); setSpec(''); }}>${l}</button>`)}
    </div>
    ${tab === 'git' && html`<div class="row gap wrap">
      <input class="input grow mono" placeholder="https://github.com/someone/42-libft-suite.git" value=${spec} onInput=${(e) => setSpec(e.target.value)} />
      <input class="input mono" style="width:140px" placeholder="branch / tag" value=${ref} onInput=${(e) => setRef(e.target.value)} />
      <button class="btn btn-primary" disabled=${busy || !spec} onClick=${add}>${busy ? 'Cloning…' : 'Clone & add'}</button>
    </div>`}
    ${tab === 'zip' && html`<label class=${'drop' + (drag ? ' over' : '')}
        onDragOver=${(e) => { e.preventDefault(); setDrag(true); }} onDragLeave=${() => setDrag(false)}
        onDrop=${(e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files[0]; if (f) upload(f); }}>
      <input type="file" accept=".zip" hidden onChange=${(e) => e.target.files[0] && upload(e.target.files[0])} />
      ${busy ? 'Importing…' : html`Drop a <code>.zip</code> suite here, or click to choose one`}
    </label>`}
    ${tab === 'folder' && html`<div class="row gap wrap">
      <input class="input grow mono" placeholder="/path/to/my-suite (folder containing suite.toml)" value=${spec} onInput=${(e) => setSpec(e.target.value)} />
      <button class="btn" onClick=${() => setPicker(true)}>Browse…</button>
      <button class="btn btn-primary" disabled=${busy || !spec} onClick=${add}>Link folder</button>
    </div>
    <p class="small dim">The folder is linked, not copied: edit its tests and simply re-run.</p>`}
    <label class="trust small"><input type="checkbox" checked=${trust} onChange=${(e) => setTrust(e.target.checked)} />
      I understand that a suite contains code that will be compiled and run on my computer, and I trust its author.</label>
    ${picker && html`<${FolderPicker} start=${s.home} title="Choose a suite folder" pickLabel="Use this suite"
      onClose=${() => setPicker(false)} onPick=${(p) => { setSpec(p); setPicker(false); }} />`}
  </div>`;
}

function NewSuite({ onClose }) {
  const [name, setName] = useState('');
  const [project, setProject] = useState('libft');
  const [runner, setRunner] = useState('c-unit');
  const [result, setResult] = useState(null);
  const create = async () => {
    try {
      const r = await api('POST', '/api/suites/new', { name, project, runner });
      setResult(r.path);
      refreshState();
    } catch (e) { toast(e.message, 'error'); }
  };
  return html`<${Modal} title="Create a new suite" onClose=${onClose}>
    ${result ? html`<div>
      <p>✓ Created <code>${result}</code></p>
      <ol class="small">
        <li>Open <code>${result}/suite.toml</code> and the files in <code>tests/</code>.</li>
        <li>Write tests (see the example inside and <code>docs/writing-suites.md</code>).</li>
        <li>Run your project: the suite is picked up automatically.</li>
      </ol>
      <button class="btn btn-primary" onClick=${onClose}>Done</button></div>`
    : html`<div class="form">
      <label>Name<input class="input" value=${name} onInput=${(e) => setName(e.target.value)} placeholder="my-libft-tests" /></label>
      <label>Project kind<input class="input" value=${project} onInput=${(e) => setProject(e.target.value)} placeholder="libft, get_next_line, push_swap…" /></label>
      <label>Runner<select class="input" value=${runner} onChange=${(e) => setRunner(e.target.value)}>
        <option value="c-unit">c-unit — C functions (libraries)</option>
        <option value="exec">exec — run a program, check its output (any language)</option>
        <option value="python-unit">python-unit — Python functions</option>
        <option value="script">script — your own runner speaking DTP</option>
      </select></label>
      <div class="row gap"><span class="grow"></span><button class="btn" onClick=${onClose}>Cancel</button>
        <button class="btn btn-primary" disabled=${!name} onClick=${create}>Create</button></div>
    </div>`}
  <//>`;
}

function Discover() {
  const [index, setIndex] = useState(null);
  useEffect(() => { api('GET', '/api/index').then(setIndex).catch(() => setIndex({ suites: [] })); }, []);
  if (!index) return null;
  return html`<section>
    <h3>Discover <span class="dim small">community suites listed in index.json</span></h3>
    ${index.suites.length ? html`<div class="list">${index.suites.map((x) => html`<div class="list-row">
      <strong>${x.name}</strong><span class="pill pill-kind">${x.project}</span><span class="dim small grow">${x.description}</span>
      ${x.installed ? html`<span class="pill pill-pass">installed</span>` : html`<code class="small">${x.url}</code>`}
    </div>`)}</div>` : html`<p class="dim small">No community suite listed yet. Publish yours by adding it to <code>index.json</code> in a pull request.</p>`}
  </section>`;
}

export function SuitesPage() {
  const s = useStore();
  const [creating, setCreating] = useState(false);
  const byProject = {};
  for (const x of s.suites) (byProject[x.project] = byProject[x.project] || []).push(x);
  const reload = async () => {
    await api('POST', '/api/suites/reload');
    await refreshState();
    toast('Suites rescanned', 'success', 1500);
  };
  return html`<div class="suites-page">
    <div class="row gap page-head">
      <h1 class="grow">Test suites</h1>
      <button class="btn" onClick=${reload} title="Re-read every suite.toml (after editing one)">⟳ Rescan</button>
      <button class="btn btn-primary" onClick=${() => setCreating(true)}>＋ New suite</button>
    </div>
    ${s.suiteErrors.length > 0 && html`<section class="card bad">
      <h4>Suites with errors</h4>
      ${s.suiteErrors.map((e) => html`<div class="suite-error"><code class="small">${e.path}</code> <span class="pill">${e.source}</span>
        <ul>${e.errors.map((m) => html`<li class="small">${m}</li>`)}</ul></div>`)}
    </section>`}
    <section><h3>Add a suite</h3><${ImportPanel} /></section>
    <section>
      <h3>Installed <span class="dim small">${s.suites.length} suite(s) for ${Object.keys(byProject).length} project(s)</span></h3>
      <div class="grid">${Object.keys(byProject).sort().flatMap((proj) => byProject[proj]).map((x) => html`<${SuiteCard} key=${x.uid} s=${x} />`)}</div>
    </section>
    <${Discover} />
    ${creating && html`<${NewSuite} onClose=${() => setCreating(false)} />`}
  </div>`;
}
