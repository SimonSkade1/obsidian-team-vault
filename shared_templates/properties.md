<%*
/* Shared-vault template: the property header every file in projects-tasks-notes/ carries.
   Conventions: .claude/CLAUDE_shared.md.

   Inserted by hand — command "Templater: Insert properties" — into a note made without a
   base's "New" button (Ctrl+N, a clicked link); the button fills `owner`, `reviewer` and
   `parent` by itself. Nothing runs this on creation: Templater's creation trigger stays off in
   this vault (setup-member skill).

   Properties: the nine vault-wide ones in order — status, priority, parent, owner,
   reviewer, not_before, dependencies, due, subscribers. Only the keys the file LACKS are emitted: Templater
   hands the emitted `---` block to Obsidian's property editor, which MERGES it — missing keys
   are appended, a key that already holds a value is never overwritten by an empty one. `owner`
   (a link, `"[[name]]"`) comes from _local/me.md ONLY while the file's owner is still empty
   (never overwrite someone else's name); no identity note => no pre-fill. `reviewer`, ONLY
   while still empty: the owner of the file's `parent`, else the file's owner, else you (as for
   `owner`). `parent` is never guessed: type it before inserting if you want its owner as
   reviewer.

   Templater runs this from local_templates/ — each member's reviewed copy of shared_templates/,
   made by the setup-member skill. Change the shared copy, then re-run the setup. */
const { getFrontMatterInfo, parseYaml } = tp.obsidian;
const KEYS = ["status", "priority", "parent", "owner", "reviewer", "not_before", "dependencies", "due", "subscribers"];
const fmOf = (s) => { const i = getFrontMatterInfo(s); if (!i.exists) return {}; try { return parseYaml(i.frontmatter) || {}; } catch (e) { return {}; } };
const empty = (v) => v === undefined || v === null || v === "";
const yq = (v) => /^[\w .-]+$/.test(v) ? v : JSON.stringify(v);   // a link "[[name]]" gets quoted

const fm = fmOf(tp.file.content);
const idFile = app.vault.getFileByPath("_local/me.md");
const me = idFile ? String(fmOf(await app.vault.cachedRead(idFile)).user ?? "").trim() : "";

let rev = "";
if (empty(fm.reviewer)) {
    const lp = String(fm.parent ?? "").replace(/^\[\[|\]\]$/g, "").split(/[|#]/)[0].trim();
    const pf = lp ? app.metadataCache.getFirstLinkpathDest(lp, tp.file.path(true)) : null;
    const po = pf ? app.metadataCache.getFileCache(pf)?.frontmatter?.owner : undefined;
    if (!empty(po)) rev = yq(String(po));
    else if (!empty(fm.owner)) rev = yq(String(fm.owner));
    else if (me) rev = `"[[${me}]]"`;
}

let head = "";
for (const k of KEYS) {
    if (k === "owner" && me && empty(fm.owner)) head += `owner: "[[${me}]]"\n`;
    else if (k === "reviewer" && rev) head += `reviewer: ${rev}\n`;
    else if (fm[k] === undefined) head += k + ":\n";
}
if (head !== "") tR += "---\n" + head + "---\n";
%>
