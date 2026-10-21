// Home: your projects, adding a project (with a folder picker), recent runs.
import { html, useEffect, useState } from '../vendor/preact-htm.mjs';
import { api, go, projectHref, refreshState, startRun, toast, useStore } from '../app.js';
import { Empty, GradeRing, Modal, StatusIcon, timeAgo } from './ui.js';

export function FolderPicker({ start, onPick, onClose, title, pickLabel }) {
  const [dir, setDir] = useState(null);
  const [path, setPath] = useState(start || '');
  const [hidden, setHidden] = useState(false);
  const load = async (p) => {
    try {
      const d = await api('GET', `/api/fs/browse?path=${encodeURIComponent(p || '')}&hidden=${hidden ? 1 : 0}`);
      setDir(d);
      setPath(d.path);
    } catch (e) { toast(e.message, 'error'); }
  };
  useEffect(() => { load(path); }, [hidden]);
  if (!dir) return html`<${Modal} title=${title || 'Choose a folder'} onClose=${onClose}><div class="dim">Loading…</div><//>`;
  const crumbs = dir.path.split('/').filter(Boolean);
  return html`<${Modal} title=${title || 'Choose a folder'} onClose=${onClose} wide>
    <div class="row gap">
      <input class="input grow mono" value=${path} onInput=${(e) => setPath(e.target.value)} onKeyDown=${(e) => e.key === 'Enter' && load(path)} />
      <button class="btn" onClick=${() => load(path)}>Go</button>
    </div>
    <div class="crumbs">
      <a href="#" onClick=${(e) => { e.preventDefault(); load('/'); }}>/</a>
      ${crumbs.map((c, i) => html`<a href="#" onClick=${(e) => { e.preventDefault(); load('/' + crumbs.slice(0, i + 1).join('/')); }}>${c}</a><span class="dim">/</span>`)}
      <span class="grow"></span>
      <a href="#" onClick=${(e) => { e.preventDefault(); load(dir.home); }}>~ home</a>
    </div>
    <div class="picker">
      ${dir.parent && html`<div class="pick-row" onClick=${() => load(dir.parent)}>📁 ..</div>`}
      ${dir.dirs.map((d) => html`<div class=${'pick-row' + (d.locked ? ' dim' : '')} onClick=${() => load(d.path)}
        title=${d.locked ? 'no access right now (e.g. a network mount that is not available)' : ''}>
        ${d.locked ? '🔒' : '📁'} ${d.name} ${d.locked && html`<span class="tag">no access</span>`}
        ${d.has_makefile && html`<span class="tag">Makefile</span>`} ${d.has_suite && html`<span class="tag">suite</span>`}</div>`)}
      ${!dir.dirs.length && html`<div class="dim small pick-empty">No sub-folders. ${dir.files.length} file(s) here.</div>`}
    </div>
    <div class="row gap modal-foot">
      <label class="toggle small"><input type="checkbox" checked=${hidden} onChange=${(e) => setHidden(e.target.checked)} /> show hidden</label>
      ${dir.kind && html`<span class="pill pill-kind">looks like ${dir.kind}</span>`}
      <span class="grow"></span>
      <button class="btn" onClick=${onClose}>Cancel</button>
      <button class="btn btn-primary" onClick=${() => onPick(dir.path)}>${pickLabel || 'Use this folder'}</button>
    </div>
  <//>`;
}

function ProjectCard({ p }) {
  const remove = async (e) => {
    e.stopPropagation();
    if (!confirm(`Remove ${p.name} from the list? (your files are not touched)`)) return;
    await api('DELETE', `/api/projects?path=${encodeURIComponent(p.path)}`);
    refreshState();
  };
  const run = async (e) => {
    e.stopPropagation();
    if (await startRun(p.path)) go(projectHref(p.path));
  };
  const score = p.last_grade == null ? null : { grade: p.last_grade, verdict: p.last_grade >= 100 ? 'ok' : 'ko' };
  return html`<div class="card project-card" onClick=${() => go(projectHref(p.path))}>
    <${GradeRing} score=${score} size=${64} running=${!!p.active_run} />
    <div class="grow card-main">
      <div class="row gap"><strong class="ellipsis">${p.name}</strong>
        ${p.kind ? html`<span class="pill pill-kind">${p.kind}</span>` : html`<span class="pill pill-skip">no suite yet</span>`}
        ${p.mode === 'linked' && html`<span class="tag" title="suites chosen by you">${p.suites.length} linked</span>`}
        ${p.watching && html`<span class="pill pill-watch">👀</span>`}</div>
      <div class="dim small mono ellipsis" title=${p.path}>${p.path}</div>
      <div class="dim small">${p.active_run ? 'running…' : `last run ${timeAgo(p.last_time)}`}</div>
    </div>
    <div class="card-actions">
      <button class="btn btn-primary btn-sm" onClick=${run} disabled=${!p.suites || !p.suites.length}
        title=${p.suites && p.suites.length ? `runs ${p.suites.join(', ')}` : 'no suite for this project: open it to choose some'}>▶ Run</button>
      <button class="icon-btn" title="Remove from list" onClick=${remove}>✕</button>
    </div>
  </div>`;
}

export function Home() {
  const s = useStore();
  const [path, setPath] = useState('');
  const [kind, setKind] = useState('');
  const [picker, setPicker] = useState(false);
  const add = async (p) => {
    setPicker(false);
    const target = (p || path).trim();
    if (!target) return;
    try {
      const proj = await api('POST', '/api/projects', { path: target, kind: kind.trim() });
      await refreshState();
      setPath('');
      setKind('');
      if (!proj.suites.length) toast('Added. No suite runs for it yet: choose some with “Suites”.', 'warn', 7000);
      go(projectHref(proj.path));
    } catch (e) { toast(e.message, 'error'); }
  };
  const recent = s.runList.slice(0, 8);
  return html`<div class="home">
    <section class="hero">
      <h1>Test your 42 projects.</h1>
      <p class="dim">Pick a project folder: DeepThought copies it to an isolated folder, builds it, runs every matching suite and explains each failure.</p>
      <div class="row gap add-row">
        <input class="input grow mono" placeholder="/path/to/your/project   (e.g. ~/libft)" value=${path}
          onInput=${(e) => setPath(e.target.value)} onKeyDown=${(e) => e.key === 'Enter' && add()} />
        <input class="input mono" style="width:190px" list="dt-kinds-home" placeholder="type (optional)" value=${kind}
          title="Leave empty to detect it. Any name works, e.g. pipex or my_project." onInput=${(e) => setKind(e.target.value)} />
        <datalist id="dt-kinds-home">${(s.kinds || []).map((k) => html`<option value=${k} />`)}</datalist>
        <button class="btn" onClick=${() => setPicker(true)}>Browse…</button>
        <button class="btn btn-primary" onClick=${() => add()}>Add project</button>
      </div>
      <p class="dim small">Any folder works: DeepThought detects libft, get_next_line, ft_printf… For your own projects, give it a type and choose (or create) the suites that test it.</p>
    </section>

    <section>
      <h3>Projects</h3>
      ${s.projects.length
        ? html`<div class="grid">${s.projects.map((p) => html`<${ProjectCard} key=${p.path} p=${p} />`)}</div>`
        : html`<${Empty} title="No project yet"><p>Add your libft, get_next_line or ft_printf folder above.</p>
            <p class="dim small">Installed suites: ${s.suites.map((x) => x.name).join(', ') || 'none'}</p><//>`}
    </section>

    ${recent.length > 0 && html`<section>
      <h3>Recent runs</h3>
      <div class="list">${recent.map((r) => html`<a class="list-row" href=${'#/run/' + r.id}>
        <${StatusIcon} status=${r.status === 'done' ? (r.score && r.score.verdict === 'ok' ? 'pass' : 'fail') : r.status} />
        <strong>${r.project.name}</strong><span class="dim small">${r.project.kind}</span>
        <span class="grow"></span>
        <span class="small">${r.score ? `${r.score.grade}/100` : r.status}</span>
        <span class="dim small">${timeAgo(r.started)}</span></a>`)}</div>
    </section>`}
    ${picker && html`<${FolderPicker} start=${path || s.home} onPick=${add} onClose=${() => setPicker(false)} title="Choose your project folder" />`}
  </div>`;
}
