// Settings: config.toml values, updates and environment info.
import { html, useState } from '../vendor/preact-htm.mjs';
import { api, refreshState, store, toast, useStore } from '../app.js';

const FIELDS = [
  ['cc', 'C compiler', 'text', 'Used to compile the tests (cc, gcc, clang…)'],
  ['cflags', 'Test CFLAGS', 'list', 'Flags for test binaries (space separated). Your Makefile keeps its own flags.'],
  ['timeout', 'Timeout per test (s)', 'number', 'A test running longer is reported as a timeout.'],
  ['jobs', 'Parallel jobs', 'number', 'How many test processes run at the same time.'],
  ['leaks', 'Fail on leaks', 'bool', 'Tests that leave memory allocated are reported as failures.'],
  ['sanitize', 'Sanitizer by default', 'bool', 'Build with AddressSanitizer/UBSan: precise crash reports, slower.'],
  ['norminette', 'Run norminette', 'bool', 'Requires norminette to be installed.'],
  ['cache_dir', 'Cache folder', 'text', 'Where builds happen. Empty = /tmp or goinfre (keeps your home quota free).'],
  ['port', 'Web port', 'number', 'Used the next time you start ./dt'],
  ['open_browser', 'Open the browser on start', 'bool', ''],
  ['check_updates', 'Check for updates daily', 'bool', 'git fetch once a day, in the background.'],
];

export function SettingsPage() {
  const s = useStore();
  const [draft, setDraft] = useState({ ...s.config });
  const [checking, setChecking] = useState(false);
  const set = (k, v) => setDraft({ ...draft, [k]: v });
  const save = async () => {
    const changes = {};
    for (const [k, , type] of FIELDS) {
      let v = draft[k];
      if (type === 'number') v = Number(v);
      if (type === 'list' && typeof v === 'string') v = v.split(/\s+/).filter(Boolean);
      if (JSON.stringify(v) !== JSON.stringify(s.config[k])) changes[k] = v;
    }
    if (!Object.keys(changes).length) return toast('Nothing changed', 'info', 1500);
    try {
      await api('POST', '/api/config', changes);
      await refreshState();
      toast('Settings saved', 'success');
    } catch (e) { toast(e.message, 'error'); }
  };
  const check = async () => {
    setChecking(true);
    try {
      const st = await api('POST', '/api/self/check');
      store.set({ update: st });
      toast(st.available ? `${st.behind} update(s) available` : st.is_git ? 'You are up to date' : 'Not a git clone', st.available ? 'warn' : 'success');
    } catch (e) { toast(e.message, 'error'); }
    setChecking(false);
  };
  const u = s.update || {};
  return html`<div class="settings">
    <h1>Settings</h1>
    <div class="card form">
      ${FIELDS.map(([k, label, type, help]) => html`<label class=${type === 'bool' ? 'row gap check' : ''}>
        ${type === 'bool'
          ? html`<input type="checkbox" checked=${!!draft[k]} onChange=${(e) => set(k, e.target.checked)} /> <span>${label}</span>`
          : html`<span>${label}</span><input class="input mono" type=${type === 'number' ? 'number' : 'text'} step="any"
              value=${Array.isArray(draft[k]) ? draft[k].join(' ') : draft[k]} onInput=${(e) => set(k, e.target.value)} />`}
        ${help && html`<span class="dim small help">${help}</span>`}
      </label>`)}
      <div class="row gap"><span class="grow"></span><button class="btn btn-primary" onClick=${save}>Save</button></div>
    </div>
    <h3>Updates</h3>
    <div class="card">
      <p>DeepThought <strong>${s.version}</strong> — <code class="small">${s.repo}</code></p>
      ${u.is_git === false && html`<p class="warn-text small">This copy is not a git clone: self-update is disabled. Clone the repository to get updates.</p>`}
      ${u.branch && html`<p class="small dim">branch ${u.branch} @ ${u.head}${u.upstream ? ` · tracking ${u.upstream}` : ' · no upstream'}${u.checked ? ` · checked ${new Date(u.checked * 1000).toLocaleString()}` : ''}</p>`}
      ${u.dirty && u.dirty.length > 0 && html`<p class="warn-text small">Local changes in the tester repo will block updates: ${u.dirty.join(', ')}</p>`}
      ${u.available && html`<p>⬆ ${u.behind} new commit(s):</p><ul class="small">${(u.changes || []).map((c) => html`<li><code>${c}</code></li>`)}</ul>`}
      <button class="btn" disabled=${checking} onClick=${check}>${checking ? 'Checking…' : 'Check for updates'}</button>
    </div>
  </div>`;
}
