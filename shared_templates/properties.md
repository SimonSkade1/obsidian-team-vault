<%*
/* Shared-vault template: the property header every file in projects-tasks-notes/ carries.
   Conventions: .claude/CLAUDE_shared.md.

   Inserted by hand — command "Templater: Insert properties" — into a note made without a
   base's "New" button (Ctrl+N, a clicked link); the button fills `owner` and `parent` by
   itself. Nothing runs this on creation: Templater's creation trigger stays off in this
   vault (setup-member skill).

   Properties: the seven vault-wide ones in order — status, priority, parent, owner,
   next_action_by, not_before, subscribers. Only the keys the file LACKS are emitted: Templater
   hands the emitted `---` block to Obsidian's property editor, which MERGES it — missing keys
   are appended, a key that already holds a value is never overwritten by an empty one. `owner`
   comes from _local/me.md ONLY while the file's owner is still empty (never overwrite someone
   else's name); no identity note => no pre-fill. `parent` is never guessed: type it.

   Templater runs this from local_templates/ — each member's reviewed copy of shared_templates/,
   made by the setup-member skill. Change the shared copy, then re-run the setup. */
const { getFrontMatterInfo, parseYaml } = tp.obsidian;
const KEYS = ["status", "priority", "parent", "owner", "next_action_by", "not_before", "subscribers"];
const fmOf = (s) => { const i = getFrontMatterInfo(s); if (!i.exists) return {}; try { return parseYaml(i.frontmatter) || {}; } catch (e) { return {}; } };

const fm = fmOf(tp.file.content);
const idFile = app.vault.getFileByPath("_local/me.md");
const me = idFile ? String(fmOf(await app.vault.cachedRead(idFile)).user ?? "").trim() : "";

let head = "";
for (const k of KEYS) {
    if (k === "owner" && me && (fm.owner === undefined || fm.owner === null || fm.owner === "")) head += "owner: " + me + "\n";
    else if (fm[k] === undefined) head += k + ":\n";
}
if (head !== "") tR += "---\n" + head + "---\n";
%>
