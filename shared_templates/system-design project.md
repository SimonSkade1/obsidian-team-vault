<%*
/* Shared-vault template for a `,` SYSTEM-DESIGN PROJECT in projects-tasks-notes/: the project
   template (sections, subtasks table) plus the steps of [[system design algorithm]] up to the
   MVP as a checklist, and a Requirements section. Conventions: .claude/CLAUDE_shared.md.

   Inserted by hand: the command "Templater: Insert system-design project" (setup-member does not
   register it yet: add local_templates/system-design project.md under Templater's "Template
   hotkeys" and bind a key, e.g. Alt+Shift+P), cursor at the end of the file. Nothing inserts it
   on creation: Templater's creation trigger stays off in this vault (setup-member skill).

   Properties: the nine vault-wide ones in order — status, priority, parent, owner,
   reviewer, not_before, dependencies, due, subscribers. The "New" button of a base has usually written them
   already (`owner`, `reviewer` and, in a subtasks table, `parent` filled); this block fills in what a file still lacks. Only the keys the file LACKS are
   emitted: Templater does not paste the emitted `---` block as text; it hands it to Obsidian's
   property editor (metadataEditor.insertProperties), which MERGES it — missing keys are
   appended, a key that already holds a value is never overwritten by an empty one. `owner` is
   pre-filled from _local/me.md, as a link `"[[name]]"`, ONLY while the file's owner is still
   empty (emitting it otherwise would overwrite someone else's name); no identity note => no
   pre-fill. `reviewer`, ONLY while still empty: the owner of the file's `parent`, else the
   file's owner, else you (as for `owner`). `parent` is never
   guessed: the "New" button of an embedded subtasks.base pre-fills it, otherwise type it.

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

![[subtasks.base]]

# Steps
1. [ ] domain: know it or learn it first
2. [ ] target interviews — notes in a child note `target interviews for {<% tp.file.title.replace(/^,/, "") %>}`
3. [ ] archetypes clarified (each a concrete person) → Targets below
4. [ ] goals and criteria for each archetype clarified → Targets below
5. [ ] inspiration research: similar systems that work — findings under Notes
6. [ ] requirements listed, each with its why
7. [ ] requirements questioned: delete or loosen each you can
8. [ ] spec: one archetype walked through end-to-end, then the general design
9. [ ] deletion pass over the spec
10. [ ] simplification pass over the spec
11. [ ] MVP built (subtasks above)
12. [ ] sensors out (observe use, metrics) → improvement loop, [[system design algorithm]]

# Target Archetypes and goal clarification/criteria for each
(list archetypes and goals for each archetype)
1. 

# Requirements
(list requirements and specify who made it or why it needs to exist)
1. 

# Spec



# Notes



