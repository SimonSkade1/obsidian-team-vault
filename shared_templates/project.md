<%*
/* Shared-vault template for a `,` PROJECT in projects-tasks-notes/: the sections a project
   needs, its subtasks table above all. Conventions: .claude/CLAUDE_shared.md.

   Inserted by hand: the hotkey Alt+P ("Templater: Insert project"), cursor at the end of the
   file — for a new `,` file as for a task turned into a project. Nothing inserts it on
   creation: Templater's creation trigger stays off in this vault (setup-member skill).

   Properties: the nine vault-wide ones in order — status, priority, parent, owner,
   stakeholder, not_before, dependencies, due, subscribers. The "New" button of a base has usually written them
   already (`owner`, `stakeholder` and, in a subtasks table, `parent` filled); this block fills in what a file still lacks. Only the keys the file LACKS are
   emitted: Templater does not paste the emitted `---` block as text; it hands it to Obsidian's
   property editor (metadataEditor.insertProperties), which MERGES it — missing keys are
   appended, a key that already holds a value is never overwritten by an empty one. `owner` is
   pre-filled from _local/me.md, as a link `"[[name]]"`, ONLY while the file's owner is still
   empty (emitting it otherwise would overwrite someone else's name); no identity note => no
   pre-fill. `stakeholder`, ONLY while still empty: the owner of the file's `parent`, else the
   file's owner, else you (as for `owner`). `parent` is never
   guessed: the "New" button of an embedded subtasks.base pre-fills it, otherwise type it.

   Templater runs this from local_templates/ — each member's reviewed copy of shared_templates/,
   made by the setup-member skill. Change the shared copy, then re-run the setup. */
const { getFrontMatterInfo, parseYaml } = tp.obsidian;
const KEYS = ["status", "priority", "parent", "owner", "stakeholder", "not_before", "dependencies", "due", "subscribers"];
const fmOf = (s) => { const i = getFrontMatterInfo(s); if (!i.exists) return {}; try { return parseYaml(i.frontmatter) || {}; } catch (e) { return {}; } };
const empty = (v) => v === undefined || v === null || v === "";
const yq = (v) => /^[\w .-]+$/.test(v) ? v : JSON.stringify(v);   // a link "[[name]]" gets quoted

const fm = fmOf(tp.file.content);
const idFile = app.vault.getFileByPath("_local/me.md");
const me = idFile ? String(fmOf(await app.vault.cachedRead(idFile)).user ?? "").trim() : "";

let stake = "";
if (empty(fm.stakeholder)) {
    const lp = String(fm.parent ?? "").replace(/^\[\[|\]\]$/g, "").split(/[|#]/)[0].trim();
    const pf = lp ? app.metadataCache.getFirstLinkpathDest(lp, tp.file.path(true)) : null;
    const po = pf ? app.metadataCache.getFileCache(pf)?.frontmatter?.owner : undefined;
    if (!empty(po)) stake = yq(String(po));
    else if (!empty(fm.owner)) stake = yq(String(fm.owner));
    else if (me) stake = `"[[${me}]]"`;
}

let head = "";
for (const k of KEYS) {
    if (k === "owner" && me && empty(fm.owner)) head += `owner: "[[${me}]]"\n`;
    else if (k === "stakeholder" && stake) head += `stakeholder: ${stake}\n`;
    else if (fm[k] === undefined) head += k + ":\n";
}
if (head !== "") tR += "---\n" + head + "---\n";
%>

![[subtasks.base]]



# Purpose / goal clarification / success criteria



# Spec



# Notes





