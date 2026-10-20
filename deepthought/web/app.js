// DeepThought web UI — no build step: Preact + htm as plain ES modules.
import { html, render, useEffect, useState } from './vendor/preact-htm.mjs';
import { Home } from './components/home.js';
import { ProjectPage, RunPage } from './components/run.js';
import { SuitesPage } from './components/suites.js';
import { SettingsPage } from './components/settings.js';
import { HistoryPage } from './components/history.js';
import { Toasts, Logo, UpdateBanner } from './components/ui.js';

// ------------------------------------------------------------------ api
export async function api(method, path, body, raw) {
  const opts = { method, credentials: 'same-origin', headers: {} };
  if (raw !== undefined) {
    opts.body = raw;
    opts.headers['Content-Type'] = 'application/octet-stream';
  } else if (body !== undefined) {
    opts.body = JSON.stringify(body);
    opts.headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `${res.status} ${res.statusText}`);
  return data;
}

// ------------------------------------------------------------------ store
// A single mutable state object; components re-render on every change
// (batched per animation frame). Simple, and fast enough for ~1000 tests.
export const store = {
  state: {
    ready: false, error: '', config: {}, projects: [], suites: [], suiteErrors: [],
    update: {}, runs: {}, runList: [], latest: {}, toasts: [], connected: false,
  },
  listeners: new Set(),
  scheduled: false,
  version: 0,
  changed() {
    this.version++;
    if (this.scheduled) return;
    this.scheduled = true;
    // rAF batches renders; the timer keeps background tabs (no rAF) updating
    let fired = false;
    const flush = () => {
      if (fired) return;
      fired = true;
      this.scheduled = false;
      this.listeners.forEach((fn) => fn());
    };
    requestAnimationFrame(flush);
    setTimeout(flush, 80);
  },
  set(patch) {
    Object.assign(this.state, patch);
    this.changed();
  },
};

export function useStore() {
  const [, force] = useState(0);
  const seen = store.version;
  useEffect(() => {
    const fn = () => force((n) => n + 1);
    store.listeners.add(fn);
    // effects run after paint: catch up on changes made before we subscribed
    if (store.version !== seen) fn();
    return () => store.listeners.delete(fn);
  }, []);
  return store.state;
}

let toastId = 0;
export function toast(message, kind = 'info', ms = 5000) {
  const id = ++toastId;
  store.state.toasts = [...store.state.toasts, { id, message, kind }];
  store.changed();
  setTimeout(() => {
    store.state.toasts = store.state.toasts.filter((t) => t.id !== id);
    store.changed();
  }, ms);
}

export async function refreshState() {
  const s = await api('GET', '/api/state');
  const runs = store.state.runs;
  store.set({
    ready: true, version: s.version, config: s.config, projects: s.projects, suites: s.suites,
    suiteErrors: s.suite_errors, update: s.update || {}, home: s.home, repo: s.repo,
    runList: mergeRunList(store.state.runList, s.runs),
  });
  document.documentElement.dataset.theme = localStorageTheme() || s.config.theme || 'dark';
  return runs;
}

function localStorageTheme() {
  try { return localStorage.getItem('dt-theme'); } catch (e) { return null; }
}

function mergeRunList(list, more) {
  const byId = new Map(list.map((r) => [r.id, r]));
  for (const r of more) byId.set(r.id, { ...byId.get(r.id), ...r });
  return [...byId.values()].sort((a, b) => (a.id < b.id ? 1 : -1)).slice(0, 50);
}

export async function loadRun(id) {
  if (store.state.runs[id]) return store.state.runs[id];
  const run = await api('GET', `/api/runs/${id}`);
  store.state.runs[id] = run;
  store.changed();
  return run;
}

export async function startRun(project, options = {}, suites = null) {
  try {
    const summary = await api('POST', '/api/runs', { project, options, suites });
    store.state.latest[project] = summary.id;
    store.changed();
    return summary;
  } catch (e) {
    toast(e.message, 'error', 8000);
    return null;
  }
}

// ------------------------------------------------------------------ live events
function findGroup(run, gid) {
  return run && run.groups.find((g) => g.gid === gid);
}

function applyEvent(ev) {
  const s = store.state;
  const run = s.runs[ev.run_id];
  switch (ev.type) {
    case 'snapshot':
      s.runs[ev.run_id] = ev.run;
      s.runList = mergeRunList(s.runList, [summaryOf(ev.run)]);
      s.latest[ev.run.project.path] = latestId(s.latest[ev.run.project.path], ev.run_id);
      break;
    case 'run':
      if (run) Object.assign(run, ev.run);
      s.runList = mergeRunList(s.runList, [ev.run]);
      if (['done', 'cancelled', 'error'].includes(ev.run.status)) refreshState().catch(() => {});
      break;
    case 'stage':
      if (run) {
        const i = run.stages.findIndex((x) => x.id === ev.stage.id);
        if (i >= 0) run.stages[i] = ev.stage; else run.stages.push(ev.stage);
      }
      break;
    case 'group': {
      const g = findGroup(run, ev.group.gid);
      if (g) Object.assign(g, ev.group);
      break;
    }
    case 'tests': {
      const g = findGroup(run, ev.gid);
      if (g) g.tests = ev.tests;
      break;
    }
    case 'test': {
      const g = findGroup(run, ev.gid);
      if (g) {
        const i = g.tests.findIndex((t) => t.id === ev.test.id);
        if (i >= 0) g.tests[i] = ev.test; else g.tests.push(ev.test);
      }
      break;
    }
    case 'watch': {
      const p = s.projects.find((x) => x.path === ev.project);
      if (p) p.watching = ev.enabled;
      if (ev.error) toast(ev.error, 'error');
      break;
    }
    case 'update':
      s.update = ev.status;
      break;
    default:
      return;
  }
  store.changed();
}

function latestId(a, b) {
  return !a || b > a ? b : a;
}

function summaryOf(run) {
  const { id, project, status, started, finished, score, suites } = run;
  return { id, project, status, started, finished, score, suites };
}

function connect() {
  const es = new EventSource('/api/events');
  es.onopen = () => store.set({ connected: true });
  es.onmessage = (m) => {
    try { applyEvent(JSON.parse(m.data)); } catch (e) { console.error(e); }
  };
  es.onerror = () => store.set({ connected: false });
}

// ------------------------------------------------------------------ router
function parseRoute() {
  const hash = decodeURIComponent(location.hash.replace(/^#/, '')) || '/';
  const parts = hash.split('/').filter(Boolean);
  if (parts[0] === 'project') return { page: 'project', path: '/' + parts.slice(1).join('/') };
  if (parts[0] === 'run') return { page: 'run', id: parts[1] };
  if (parts[0] === 'history') return { page: 'history', path: '/' + parts.slice(1).join('/') };
  if (parts[0] === 'suites') return { page: 'suites' };
  if (parts[0] === 'settings') return { page: 'settings' };
  return { page: 'home' };
}

export function go(hash) {
  location.hash = hash;
}

export function projectHref(path) {
  return '#/project' + path.split('/').map(encodeURIComponent).join('/');
}

function useRoute() {
  const [route, setRoute] = useState(parseRoute());
  useEffect(() => {
    const fn = () => setRoute(parseRoute());
    window.addEventListener('hashchange', fn);
    return () => window.removeEventListener('hashchange', fn);
  }, []);
  return route;
}

// ------------------------------------------------------------------ shell
function Nav({ route }) {
  const s = useStore();
  const link = (href, label, active) => html`<a href=${href} class=${'nav-link' + (active ? ' active' : '')}>${label}</a>`;
  const toggleTheme = () => {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('dt-theme', next); } catch (e) {}
  };
  return html`
    <header class="nav">
      <a href="#/" class="brand"><${Logo} /> <span>DeepThought</span></a>
      <nav>
        ${link('#/', 'Projects', ['home', 'project', 'run', 'history'].includes(route.page))}
        ${link('#/suites', 'Suites', route.page === 'suites')}
        ${link('#/settings', 'Settings', route.page === 'settings')}
      </nav>
      <div class="nav-right">
        <span class=${'conn ' + (s.connected ? 'on' : 'off')} title=${s.connected ? 'live' : 'disconnected — is ./dt still running?'}></span>
        <button class="icon-btn" title="Toggle light/dark theme" onClick=${toggleTheme}>◐</button>
        <span class="dim small">v${s.version || ''}</span>
      </div>
    </header>`;
}

function App() {
  const route = useRoute();
  const s = useStore();
  if (!s.ready) {
    return html`<div class="boot">${s.error ? html`<div class="error-box">${s.error}</div>` : 'DeepThought is thinking…'}</div>`;
  }
  let page;
  if (route.page === 'project') page = html`<${ProjectPage} path=${route.path} />`;
  else if (route.page === 'run') page = html`<${RunPage} id=${route.id} />`;
  else if (route.page === 'suites') page = html`<${SuitesPage} />`;
  else if (route.page === 'settings') page = html`<${SettingsPage} />`;
  else if (route.page === 'history') page = html`<${HistoryPage} path=${route.path} />`;
  else page = html`<${Home} />`;
  return html`
    <${Nav} route=${route} />
    <${UpdateBanner} />
    <main class=${'page page-' + route.page}>${page}</main>
    <${Toasts} />`;
}

refreshState()
  .then(() => connect())
  .catch((e) => store.set({ error: e.message.includes('token') ? 'Open the link printed in your terminal (it contains your access token).' : e.message }));
render(html`<${App} />`, document.getElementById('app'));
