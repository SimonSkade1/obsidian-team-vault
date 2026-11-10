/* Team vault select properties: dropdowns for status, owner, reviewer and subscribers.
 * How: wraps render() of Obsidian's built-in `text` and `multitext` property widgets
 * (internal app.metadataTypeManager.registeredTypeWidgets). The Properties panel and Bases
 * table cells both draw through them; for the keys in CONFIG we draw a <select> (subscribers:
 * pills + an add-dropdown), anything else or any error falls back to the original widget.
 * Writes go ONLY through ctx.onChange: Obsidian binds it to the row's note at change time
 * (Bases recycles rows, so ctx.sourcePath can be stale). No property types are assigned
 * (types.json untouched), so without the plugin the fields are plain text again.
 * Options: edit CONFIG below. People = the .md files directly in vault-members/, saved as
 * "[[name]]"; "other…" asks for free text, saved as typed. Values not in the list are shown
 * and kept, never rewritten. Uses undocumented internals: checked against Obsidian 1.14.5.
 * Header guard: Bases empties a property by deleting it (kanban drop into the empty column, cleared
 * cells, "Remove property"), through app.fileManager.processFrontMatter; that method is wrapped so
 * that, in (private-)projects-tasks-notes/, a header key (HEADER_KEYS) a note had before the callback
 * ran is put back empty at its old position. Keys a note never had are not added; other folders and
 * the Properties panel (which edits the editor text) are untouched. styles.css also lets an embedded
 * base use the pane width when "Readable line length" is on.
 * New item body: a note this Obsidian creates empty in (private-)projects-tasks-notes/ (a base's New
 * button, Ctrl+N, a clicked link, the file menu: all go through app.fileManager.createNewFile, which
 * is wrapped) gets NEW_ITEM_BODY, its subtasks table, as body. Notes synced in from other machines
 * do not pass through it. The first time such a note's editor gets focus with the cursor at or above
 * that line (Enter after typing the name), the cursor moves below it, so typing does not land in
 * front of the embed.
 * created_by: in projects-tasks-notes/ (not private-), if _local/me.md names the user, that same write
 * puts the header above the body: HEADER_KEYS empty, then `created_by: "[[<user>]]"`, who made the
 * note (no base shows it). A base's New button (processFrontMatter) and the templates
 * (metadataEditor.insertProperties) fill keys in place, so it stays last. Files written outside
 * Obsidian (Claude, scripts, sync) never get it.
 * Source of truth: other-files/obsidian-plugins/team-vault-select-properties/ (synced); the
 * setup-member skill copies it into .obsidian/plugins/. Bump manifest.json "version" on change.
 */
const { Plugin, Modal, Notice, setIcon, TFile, TFolder, editorInfoField } = require('obsidian');
const { EditorView } = require('@codemirror/view');

// emptyLabel: the empty choice in the open list (table cells show empty as blank).
// hidden: valid values that VNA runs set; shown normally when present, never offered.
const CONFIG = {
  status: { kind: 'single', emptyLabel: '[Empty/TODO]', options: ['inbox', 'in-progress', 'review', 'discuss', 'done', 'cancelled', 'note', 'note-archived'], hidden: ['failed', 'exception'] },
  owner: { kind: 'single', emptyLabel: '[Empty]', people: true, extra: ['claude'] },
  reviewer: { kind: 'single', emptyLabel: '[Empty = owner]', people: true, extra: ['claude'] },
  subscribers: { kind: 'multi', people: true },
};
const MEMBERS_FOLDER = 'vault-members';
const SOURCE_DIR = 'other-files/obsidian-plugins/team-vault-select-properties';
const WRAPPED_TYPES = ['text', 'multitext'];
const MARK = '__pauseaiSelectPropertiesOriginal'; // own property of our wrapper -> original widget
const OTHER = '::psp-other';
const CURRENT = '::psp-current';
const LOG = '[team-vault-select-properties]';
const ITEM_FOLDER_RE = /(^|\/)(private-)?projects-tasks-notes\//;
const HEADER_KEYS = ['status', 'priority', 'parent', 'owner', 'reviewer', 'not_before', 'dependencies', 'due', 'subscribers'];
const FM_MARK = '__pauseaiSelectPropertiesOriginalProcessFrontMatter'; // own property of our wrapper -> original
const NEW_MARK = '__pauseaiSelectPropertiesOriginalCreateNewFile'; // likewise for createNewFile
const NEW_ITEM_BODY = '![[subtasks.base]]\n';
const SHARED_ITEM_FOLDER_RE = /(^|\/)projects-tasks-notes\//; // created_by: not in private-projects-tasks-notes/
const ME_FILE = '_local/me.md';

const LINK_RE = /^\[\[([^\]|#]*)(#[^\]|]*)?(\|([^\]]*))?\]\]$/;
const hasOwn = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
const toLink = (name) => '[[' + name + ']]';

function parseLink(v) {
  const m = typeof v === 'string' ? LINK_RE.exec(v.trim()) : null;
  return m ? { target: m[1].trim(), alias: m[4] } : null;
}
// The member a value links to ([[name]], [[name|N]], [[vault-members/name]]), else null.
function memberOf(v, members) {
  const l = parseLink(v);
  if (!l) return null;
  const base = l.target.replace(/\.md$/i, '').split('/').pop().toLowerCase();
  const hit = members.find((n) => n.toLowerCase() === base);
  return hit === undefined ? null : hit;
}
function plain(v) {
  const l = parseLink(v);
  return l ? (l.alias || l.target.split('/').pop()) : String(v);
}
// Runs a processFrontMatter callback on an item note, then puts back the header keys it deleted.
// Obsidian writes the keys in the object's order, so the object is rebuilt in place: original order
// with the surviving values, a lost header key empty at its old position, new keys appended.
function restoreHeaderKeys(data, fn, args) {
  const before = Object.keys(data);
  const result = fn(data, ...args);
  const lost = before.filter((k) => HEADER_KEYS.includes(k) && !hasOwn(data, k));
  if (lost.length) {
    const kept = {};
    for (const k of Object.keys(data)) { kept[k] = data[k]; delete data[k]; }
    for (const k of before) {
      if (hasOwn(kept, k)) data[k] = kept[k];
      else if (lost.includes(k)) data[k] = null;
    }
    for (const k of Object.keys(kept)) if (!hasOwn(data, k)) data[k] = kept[k];
  }
  return result;
}
function openPicker(sel) {
  try { sel.showPicker(); } catch (e) { /* no user activation or unsupported: focus only */ }
}
// Bases starts a drag-selection on pointerdown (its capture listener runs before ours) and ends
// it on pointerup, which the opening native dropdown swallows: the next click would select the
// rectangle up to this cell. Its drag helper also ends on pointercancel, so send one.
function endBasesDrag(e) {
  const win = e.view || window;
  try { win.dispatchEvent(new win.PointerEvent('pointercancel', { pointerId: e.pointerId })); } catch (err) { /* ignore */ }
}
// Keys on a focused, closed <select>. Chromium on Linux changes the value on arrow and letter
// keys, which would write to the note; so they never reach the select.
function onSelectKeydown(e, sel, ctx) {
  if (e.isComposing || e.ctrlKey || e.metaKey) return;
  const k = e.key;
  if (k === 'Enter' || k === ' ' || k === 'F4' || (e.altKey && (k === 'ArrowDown' || k === 'ArrowUp'))) {
    e.preventDefault(); e.stopPropagation(); openPicker(sel);
  } else if (e.altKey) {
    return;
  } else if (k === 'Escape') {
    e.preventDefault(); e.stopPropagation(); if (ctx.blur) ctx.blur();
  } else if (/^(Arrow|Page)/.test(k) || k === 'Home' || k === 'End') {
    e.preventDefault(); if (ctx.blur) ctx.blur(); // leave the field; the next key navigates
  } else if (k === 'Backspace' || k === 'Delete' || k.length === 1) {
    e.preventDefault();
  }
}

class OtherModal extends Modal {
  constructor(app, title, initial, done) {
    super(app);
    this.title = title; this.initial = initial; this.done = done; this.submitted = false;
  }
  onOpen() {
    this.titleEl.setText(this.title);
    const input = this.contentEl.createEl('input', { type: 'text', cls: 'psp-other-input', attr: { placeholder: 'Name, or [[link]]' } });
    input.value = this.initial || '';
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.isComposing) { e.preventDefault(); this.submit(input.value); }
    });
    const buttons = this.contentEl.createDiv({ cls: 'modal-button-container' });
    buttons.createEl('button', { text: 'Save', cls: 'mod-cta' }).addEventListener('click', () => this.submit(input.value));
    buttons.createEl('button', { text: 'Cancel' }).addEventListener('click', () => this.close());
    window.setTimeout(() => { input.focus(); input.select(); }, 0);
  }
  submit(text) {
    const t = text.trim();
    if (!t) { this.close(); return; } // empty = cancel
    this.submitted = true;
    this.close();
    this.done(t);
  }
  onClose() {
    this.contentEl.empty();
    if (!this.submitted) this.done(null);
  }
}

class SingleSelect {
  static make(plugin, value, ctx, conf, type) {
    if (value != null && typeof value !== 'string') return null; // e.g. a list: native widget
    return new SingleSelect(plugin, value, ctx, conf, type);
  }
  constructor(plugin, value, ctx, conf, type) {
    this.plugin = plugin; this.ctx = ctx; this.conf = conf; this.type = type;
    this.hoverPopover = null; this.containerEl = null;
    this.value = value == null ? '' : value;
    this.inBases = ctx.hoverSource === 'bases';
    this.root = createDiv({ cls: 'psp-single' });
    this.selectEl = this.root.createEl('select', { cls: 'psp-select', attr: { 'aria-label': ctx.key } });
    setIcon(this.root.createSpan({ cls: 'psp-chevron' }), 'chevrons-up-down');
    this.fill();
    this.selectEl.addEventListener('change', () => this.onSelect());
    this.selectEl.addEventListener('keydown', (e) => onSelectKeydown(e, this.selectEl, ctx));
    if (this.inBases) this.selectEl.addEventListener('pointerdown', endBasesDrag);
  }
  fill() {
    const { conf, selectEl: sel } = this;
    const cur = this.value;
    const members = conf.people ? this.plugin.getMembers() : [];
    const extra = conf.extra || [];
    let selected = null;
    if (cur === '') selected = '';
    else if (conf.people) {
      const m = memberOf(cur, members);
      if (m !== null) selected = toLink(m);
      else if (extra.includes(cur)) selected = cur;
    } else if (conf.options.includes(cur)) selected = cur;
    const invalid = selected === null && !conf.people && !(conf.hidden || []).includes(cur);
    sel.empty();
    const add = (value, label, cls) => sel.createEl('option', { text: label, value, cls });
    add('', conf.emptyLabel || '[Empty]', 'psp-empty');
    if (selected === null) add(CURRENT, conf.people ? 'other: ' + plain(cur) : cur, conf.people ? 'psp-other' : invalid ? 'is-invalid' : undefined);
    for (const o of conf.options || []) add(o, o);
    if (conf.people) {
      for (const m of members) add(toLink(m), m);
      for (const x of extra) add(x, x);
      add(OTHER, 'other…');
    }
    sel.value = selected === null ? CURRENT : selected;
    sel.toggleClass('is-empty', cur === '');
    sel.toggleClass('is-invalid', invalid);
    sel.title = cur;
  }
  onSelect() {
    const v = this.selectEl.value;
    if (this.selectEl.selectedIndex < 0 || v === CURRENT) return;
    if (v === OTHER) {
      this.fill(); // show the current value until the dialog is saved
      const cur = this.value;
      const keep = cur !== '' && memberOf(cur, this.plugin.getMembers()) === null && !(this.conf.extra || []).includes(cur);
      this.plugin.askOther(this, 'Other ' + this.ctx.key, keep ? cur : '', (t) => { this.commit(t); this.blur(); }, () => this.blur());
      return;
    }
    this.commit(v);
    this.blur();
  }
  commit(v) {
    this.value = v;
    this.fill();
    this.ctx.onChange(v); // '' = empty, as the native text widget sends
  }
  blur() { if (this.ctx.blur) this.ctx.blur(); }
  setValue(v) { this.value = v == null ? '' : String(v); this.fill(); }
  focus(mode) { this.onFocus(mode); }
  onFocus() { this.selectEl.focus({ preventScroll: true }); openPicker(this.selectEl); }
}

class MultiSelect {
  static make(plugin, value, ctx, conf, type) {
    let list;
    if (value == null || value === '') list = [];
    else if (typeof value === 'string') list = [value];
    else if (Array.isArray(value) && value.every((x) => typeof x === 'string')) list = value.slice();
    else return null;
    return new MultiSelect(plugin, list, ctx, conf, type);
  }
  constructor(plugin, list, ctx, conf, type) {
    this.plugin = plugin; this.ctx = ctx; this.conf = conf; this.type = type;
    this.hoverPopover = null; this.containerEl = null;
    this.values = list;
    this.inBases = ctx.hoverSource === 'bases';
    this.root = createDiv({ cls: 'psp-multi multi-select-container' });
    this.render();
  }
  render() {
    const root = this.root;
    const hadFocus = root.contains(root.ownerDocument.activeElement);
    root.empty();
    const members = this.plugin.getMembers();
    const present = new Set();
    this.values.forEach((v, i) => {
      const m = memberOf(v, members);
      if (m !== null) present.add(m);
      const pill = root.createDiv({ cls: 'multi-select-pill', attr: { tabindex: 0, title: v } });
      if (m === null) pill.addClass('psp-other');
      pill.createDiv({ cls: 'multi-select-pill-content', text: m !== null ? m : plain(v) });
      const x = pill.createDiv({ cls: 'multi-select-pill-remove-button', attr: { 'aria-label': 'Remove' } });
      setIcon(x, 'x');
      x.addEventListener('click', (e) => { e.preventDefault(); e.stopPropagation(); this.write(this.values.filter((_, j) => j !== i)); });
      pill.addEventListener('keydown', (e) => {
        if (e.isComposing) return;
        if (e.key === 'Backspace' || e.key === 'Delete') { e.preventDefault(); this.write(this.values.filter((_, j) => j !== i)); }
        else if (e.key === 'Escape') { e.preventDefault(); if (this.ctx.blur) this.ctx.blur(); }
      });
    });
    const sel = this.addEl = root.createEl('select', { cls: 'psp-select psp-add', attr: { 'aria-label': 'Add to ' + this.ctx.key } });
    const ph = sel.createEl('option', { text: this.values.length || this.inBases ? '+' : 'Empty', value: '' });
    ph.hidden = true;
    for (const m of members) if (!present.has(m)) sel.createEl('option', { text: m, value: toLink(m) });
    sel.createEl('option', { text: 'other…', value: OTHER });
    sel.value = '';
    sel.toggleClass('is-empty', this.values.length === 0);
    sel.addEventListener('change', () => this.onAdd());
    sel.addEventListener('keydown', (e) => onSelectKeydown(e, sel, this.ctx));
    if (this.inBases) sel.addEventListener('pointerdown', endBasesDrag);
    if (hadFocus) sel.focus({ preventScroll: true });
  }
  onAdd() {
    const v = this.addEl.selectedIndex < 0 ? '' : this.addEl.value;
    this.addEl.value = '';
    if (!v) return;
    if (v === OTHER) {
      this.plugin.askOther(this, 'Add to ' + this.ctx.key, '', (t) => this.addValue(t), null);
      return;
    }
    this.addValue(v);
  }
  addValue(v) {
    const members = this.plugin.getMembers();
    const m = memberOf(v, members);
    if (this.values.includes(v) || (m !== null && this.values.some((x) => memberOf(x, members) === m))) return;
    this.write(this.values.concat([v]));
  }
  write(next) {
    this.values = next;
    this.render();
    this.ctx.onChange(next.slice()); // [] = empty, as the native list widget sends
  }
  setValue(v) {
    this.values = v == null || v === '' ? [] : Array.isArray(v) ? v.map(String) : [String(v)];
    this.render();
  }
  focus(mode) { this.onFocus(mode); }
  onFocus() { this.addEl.focus({ preventScroll: true }); openPicker(this.addEl); }
}

module.exports = class PauseAISelectProperties extends Plugin {
  onload() {
    this.changeCount = 0; // vault changes, to guard the delayed write after the "other…" dialog
    const bump = () => { this.changeCount++; };
    this.registerEvent(this.app.metadataCache.on('changed', bump));
    this.registerEvent(this.app.vault.on('create', bump));
    this.registerEvent(this.app.vault.on('delete', bump));
    this.registerEvent(this.app.vault.on('rename', bump));
    const midSession = this.app.workspace.layoutReady; // at startup plugins load before any view
    this.patch();
    this.patchFrontMatter();
    this.freshItems = new WeakSet(); // TFiles that got NEW_ITEM_BODY and were not focused yet
    this.patchCreateNewFile();
    this.registerEditorExtension(this.cursorBelowTable());
    if (midSession) this.refreshViews();
    this.app.workspace.onLayoutReady(() => this.checkForUpdate());
  }

  onunload() {
    this.unpatchCreateNewFile();
    this.unpatchFrontMatter();
    this.unpatch();
    this.refreshViews();
  }

  patch() {
    const reg = this.app.metadataTypeManager && this.app.metadataTypeManager.registeredTypeWidgets;
    this.originals = {};
    if (!reg) { console.warn(LOG, 'widget registry not found; plugin inactive'); return; }
    for (const type of WRAPPED_TYPES) {
      let orig = reg[type];
      if (orig && hasOwn(orig, MARK)) orig = orig[MARK]; // stale wrapper of an earlier load: no double wrap
      if (!orig || typeof orig.render !== 'function') { console.warn(LOG, 'no "' + type + '" widget; left alone'); continue; }
      // A new object (not an in-place patch), so Bases sees a changed widget and redraws its cells.
      const wrapper = Object.create(orig);
      wrapper.render = this.makeRender(orig, type);
      wrapper[MARK] = orig;
      reg[type] = wrapper;
      this.originals[type] = orig;
    }
    this.active = true;
  }

  unpatch() {
    this.active = false; // a wrapper that someone else wrapped again now just passes through
    const reg = this.app.metadataTypeManager && this.app.metadataTypeManager.registeredTypeWidgets;
    if (!reg) return;
    for (const type of Object.keys(this.originals || {})) {
      const cur = reg[type];
      if (cur && hasOwn(cur, MARK) && cur[MARK] === this.originals[type]) reg[type] = this.originals[type];
    }
  }

  // Header guard (see top): Bases, its undo stack and the URI handler write properties through
  // app.fileManager.processFrontMatter; the wrapper only touches the object the callback mutates.
  patchFrontMatter() {
    const fm = this.app.fileManager;
    let orig = fm && fm.processFrontMatter;
    if (orig && hasOwn(orig, FM_MARK)) orig = orig[FM_MARK]; // stale wrapper of an earlier load: no double wrap
    if (typeof orig !== 'function') { console.warn(LOG, 'processFrontMatter not found; header keys unguarded'); return; }
    const plugin = this;
    const wrapper = function (file, fn, ...rest) {
      const guard = plugin.fmActive && typeof fn === 'function' && !!file && ITEM_FOLDER_RE.test(file.path || '');
      return orig.call(this, file, guard ? (data, ...args) => restoreHeaderKeys(data, fn, args) : fn, ...rest);
    };
    wrapper[FM_MARK] = orig;
    fm.processFrontMatter = wrapper;
    this.originalProcessFrontMatter = orig;
    this.fmActive = true;
  }

  unpatchFrontMatter() {
    this.fmActive = false; // a wrapper that someone else wrapped again now just passes through
    const fm = this.app.fileManager;
    const cur = fm && fm.processFrontMatter;
    if (!cur || !hasOwn(cur, FM_MARK) || cur[FM_MARK] !== this.originalProcessFrontMatter) return;
    if (Object.getPrototypeOf(fm).processFrontMatter === cur[FM_MARK]) delete fm.processFrontMatter;
    else fm.processFrontMatter = cur[FM_MARK];
  }

  // New item body (see top). Written after the creation and before the caller goes on, so a base's
  // New button then puts the properties above it.
  patchCreateNewFile() {
    const fm = this.app.fileManager;
    let orig = fm && fm.createNewFile;
    if (orig && hasOwn(orig, NEW_MARK)) orig = orig[NEW_MARK]; // stale wrapper of an earlier load: no double wrap
    if (typeof orig !== 'function') { console.warn(LOG, 'createNewFile not found; new items start empty'); return; }
    const plugin = this;
    const wrapper = async function (folder, name, ext, contents, ...rest) {
      const file = await orig.call(this, folder, name, ext, contents, ...rest);
      if (plugin.newActive && !contents && file instanceof TFile && file.extension === 'md' && ITEM_FOLDER_RE.test(file.path)) {
        try {
          const body = plugin.newItemHeader(file) + NEW_ITEM_BODY;
          await plugin.app.vault.process(file, (text) => (text === '' ? body : text));
          plugin.freshItems.add(file);
        } catch (e) {
          console.error(LOG, 'new note left empty:', e);
        }
      }
      return file;
    };
    wrapper[NEW_MARK] = orig;
    fm.createNewFile = wrapper;
    this.originalCreateNewFile = orig;
    this.newActive = true;
  }

  // created_by (see top): the header a new item starts with, '' for none.
  newItemHeader(file) {
    try {
      if (!SHARED_ITEM_FOLDER_RE.test(file.path)) return '';
      const me = this.app.vault.getFileByPath(ME_FILE);
      const cache = me && this.app.metadataCache.getFileCache(me);
      const user = cache && cache.frontmatter && cache.frontmatter.user != null ? String(cache.frontmatter.user).trim() : '';
      if (!user) return '';
      return '---\n' + HEADER_KEYS.map((k) => k + ':\n').join('') + 'created_by: ' + JSON.stringify(toLink(user)) + '\n---\n';
    } catch (e) {
      console.error(LOG, 'new item without created_by:', e);
      return '';
    }
  }

  unpatchCreateNewFile() {
    this.newActive = false; // a wrapper that someone else wrapped again now just passes through
    const fm = this.app.fileManager;
    const cur = fm && fm.createNewFile;
    if (!cur || !hasOwn(cur, NEW_MARK) || cur[NEW_MARK] !== this.originalCreateNewFile) return;
    if (Object.getPrototypeOf(fm).createNewFile === cur[NEW_MARK]) delete fm.createNewFile;
    else fm.createNewFile = cur[NEW_MARK];
  }

  // New item body, the cursor (see top). A new note's cursor starts at 0, which Obsidian puts at
  // the start of the body: in front of the embed.
  cursorBelowTable() {
    const plugin = this;
    return EditorView.updateListener.of((u) => {
      if (!u.focusChanged || !u.view.hasFocus) return;
      const info = u.state.field(editorInfoField, false);
      const file = info && info.file;
      if (!file || !plugin.freshItems.has(file)) return;
      plugin.freshItems.delete(file);
      const at = u.state.doc.toString().indexOf(NEW_ITEM_BODY);
      if (at < 0 || u.state.selection.main.head > at) return;
      const below = at + NEW_ITEM_BODY.length;
      // not inside the update that is running
      setTimeout(() => { if (u.view.state.doc === u.state.doc) u.view.dispatch({ selection: { anchor: below } }); }, 0);
    });
  }

  makeRender(orig, type) {
    const plugin = this;
    return function (el, value, ctx) {
      if (plugin.active) {
        try {
          const conf = plugin.confFor(ctx);
          const comp = !conf ? null : conf.kind === 'multi'
            ? MultiSelect.make(plugin, value, ctx, conf, type)
            : SingleSelect.make(plugin, value, ctx, conf, type);
          if (comp) {
            comp.containerEl = el;
            el.appendChild(comp.root);
            return comp;
          }
        } catch (err) {
          console.error(LOG, 'showing the plain field instead:', err);
        }
      }
      return orig.render.call(orig, el, value, ctx);
    };
  }

  // Only real property editing of a note: the Properties panel and Bases cells. Not Bases
  // filters (sourcePath "") or the "add group" row (filterSuggestion).
  confFor(ctx) {
    if (!ctx || typeof ctx.key !== 'string' || typeof ctx.onChange !== 'function') return null;
    if (!/\.md$/i.test(ctx.sourcePath || '') || 'filterSuggestion' in ctx) return null;
    const key = ctx.key.toLowerCase();
    return hasOwn(CONFIG, key) ? CONFIG[key] : null;
  }

  getMembers() {
    const folder = this.app.vault.getAbstractFileByPath(MEMBERS_FOLDER);
    if (!(folder instanceof TFolder)) return [];
    return folder.children
      .filter((f) => f instanceof TFile && f.extension === 'md')
      .map((f) => f.basename)
      .sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }));
  }

  // done(text) runs only if the field is still on screen and, in Bases, no note changed meanwhile
  // (rows could have been reassigned to other notes while the dialog was open).
  askOther(comp, title, initial, done, cancelled) {
    const start = this.changeCount;
    new OtherModal(this.app, title, initial, (text) => {
      if (text === null) { if (cancelled) cancelled(); return; }
      if (!comp.root.isConnected || (comp.inBases && this.changeCount !== start)) {
        new Notice('Team vault select properties: the table changed while the dialog was open, so nothing was saved. Please try again.');
        return;
      }
      done(text);
    }).open();
  }

  // Redraw open views: what Obsidian itself does after a property type changes.
  refreshViews() {
    const mtm = this.app.metadataTypeManager;
    if (!mtm || typeof mtm.trigger !== 'function') return;
    for (const key of Object.keys(CONFIG)) {
      try { mtm.trigger('changed', key); } catch (e) { console.error(LOG, e); }
    }
  }

  async checkForUpdate() {
    try {
      const path = SOURCE_DIR + '/manifest.json';
      if (!(await this.app.vault.adapter.exists(path))) return;
      const synced = JSON.parse(await this.app.vault.adapter.read(path));
      if (isNewer(synced.version, this.manifest.version)) {
        new Notice('Team vault select properties: a newer version is in the vault — ask Claude to "complete the setup".', 0);
      }
    } catch (e) {
      console.warn(LOG, 'update check failed', e);
    }
  }
};

function isNewer(a, b) {
  const pa = String(a).split('.').map(Number);
  const pb = String(b).split('.').map(Number);
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const x = pa[i] || 0;
    const y = pb[i] || 0;
    if (x !== y) return x > y;
  }
  return false;
}
