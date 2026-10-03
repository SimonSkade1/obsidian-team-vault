#!/usr/bin/env python3
"""Read an Obsidian note with ![[embeds]] expanded inline — i.e. see the note the
way Obsidian renders it (transclusions included), while keeping source line
numbers so the underlying files stay editable.

Usage:
  read_obsidian.py "<vault-relative-path or bare note name>[#Heading|#^blockid]"

Link resolution follows Obsidian semantics: exact vault path first, then bare
name matched anywhere in the vault (shortest path wins; ambiguity is flagged).
Heading subpaths may be nested (#A#B). Embeds inside code fences / inline code
are not expanded. Recursion is cycle-safe.

Options:
  --vault PATH          vault root (default: derived from this script's location)
  --max-depth N         embed recursion depth (default 4)
  --max-embed-lines N   truncate one embedded section after N lines (default 400)
  --max-lines N         truncate the top-level file after N lines (default 2000)
  --subtask-base-only   print ONLY the children table of the embedded subtasks.base,
                        not the note's own text (the usual read for a `,` goal whose
                        queue state is all you need)

Output:
  <n>\t<line>                    top-level file, cat -n style
     ┌─ <resolved-file>[#subpath]  embedded content, with the source file's
     │ <n>\t<line>                 own line numbers
     └─
Unresolved / non-Markdown / cyclic embeds get a one-line ⊞ annotation instead.

An embedded base whose filters contain `parent == this` (i.e. subtasks.base) is
rendered as the embedding note's direct-children table — the same rows the base
shows a human, without the per-user "my …" filter and without grouping. Any
other .base embed keeps the one-line ⊞ stub.
"""

import argparse
import os
import re
import sys
from pathlib import Path

EMBED_RE = re.compile(r'!\[\[([^\[\]]+?)\]\]')
HEADING_RE = re.compile(r'^(#{1,6})\s+(.*?)\s*$')
LIST_RE = re.compile(r'^(\s*)(?:[-*+]|\d+[.)])\s')

# --- children of a note (rendering of a `parent == this` base embed) --------
CHILD_BASE_RE = re.compile(r'parent\s*==\s*this\b')   # subtasks.base's defining filter
CHILD_FOLDERS = ('projects-tasks-notes',               # the only folders with parent/child notes;
                 'private-projects-tasks-notes')       # the second is optional, per-user and never synced
CONFLICT_MARK = '.sync-conflict-'                      # Syncthing conflict copies (hidden, as in the base)
FM_RE = re.compile(r'^([A-Za-z_][\w-]*)\s*:\s*(.*)$')
WIKILINK_RE = re.compile(r'^!?\[\[(.+?)\]\]$')
LIST_ITEM_RE = re.compile(r'^\s*-\s+(.*)$')            # a block-list item in the frontmatter
CHILD_HEADERS = ('#', 'blocked', 'type', 'status', 'owner', 'stakeholder',
                 'priority', 'not_before', 'due', 'model', 'effort', 'dependencies', 'path')
FINISHED = ('review', 'done', 'cancelled', 'failed')     # a dependency blocks only while unfinished

KIND_BY_EXT = {'.md': 'md', '.pdf': 'pdf', '.canvas': 'canvas', '.base': 'base'}
for _e in ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.avif', '.bmp'):
    KIND_BY_EXT[_e] = 'image'
for _e in ('.mp3', '.wav', '.m4a', '.ogg', '.flac', '.3gp'):
    KIND_BY_EXT[_e] = 'audio'
for _e in ('.mp4', '.mov', '.mkv', '.webm', '.ogv'):
    KIND_BY_EXT[_e] = 'video'


def kind_of(path: Path) -> str:
    return KIND_BY_EXT.get(path.suffix.lower(), 'file')


def build_index(vault: Path):
    files = []
    for root, dirs, names in os.walk(vault):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
        for n in sorted(names):
            if not n.startswith('.'):
                files.append(Path(root, n).relative_to(vault))
    return files


def resolve_target(target: str, files):
    """Obsidian-style resolution. Returns (relpath|None, note|None)."""
    t = target.strip().strip('/')
    if not t:
        return None, None
    for cand in (t + '.md', t):
        cl = cand.lower()
        exact = [f for f in files if str(f).lower() == cl]
        matches = exact or [f for f in files if str(f).lower().endswith('/' + cl)]
        if matches:
            best = min(matches, key=lambda f: (len(f.parts), str(f)))
            note = None
            if len(matches) > 1:
                note = f"ambiguous ({len(matches)} matches), picked shortest"
            return best, note
    return None, None


def code_mask(lines):
    """True for lines inside (or delimiting) fenced code blocks."""
    mask = [False] * len(lines)
    fence = None  # (char, length)
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if fence is None:
            m = re.match(r'^(`{3,}|~{3,})', stripped)
            if m and indent <= 3:
                fence = (m.group(1)[0], len(m.group(1)))
                mask[i] = True
        else:
            mask[i] = True
            m = re.match(r'^(`{3,}|~{3,})\s*$', stripped)
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= fence[1] and indent <= 3:
                fence = None
    return mask


def normalize_heading(s: str) -> str:
    s = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', s)  # wikilink -> display text
    s = re.sub(r'[*_`~]', '', s)
    return re.sub(r'\s+', ' ', s).strip().lower()


def find_headings(lines, mask):
    out = []
    for i, line in enumerate(lines):
        if mask[i]:
            continue
        m = HEADING_RE.match(line)
        if m:
            out.append((i, len(m.group(1)), m.group(2)))
    return out


def extract_section(lines, subpath):
    """Heading path like 'A' or 'A#B'. Returns (start, end) incl. heading line."""
    parts = [p for p in subpath.split('#') if p.strip()]
    heads = find_headings(lines, code_mask(lines))
    lo, hi, min_level = 0, len(lines), 0
    for part in parts:
        want = normalize_heading(part)
        found = None
        for (i, lvl, text) in heads:
            if lo <= i < hi and lvl > min_level and normalize_heading(text) == want:
                found = (i, lvl)
                break
        if not found:
            return None
        i, lvl = found
        end = hi
        for (j, l2, _t) in heads:
            if j > i and l2 <= lvl:
                end = j
                break
        lo, hi, min_level = i, end, lvl
    while hi > lo and not lines[hi - 1].strip():
        hi -= 1
    return lo, hi


def extract_block(lines, block_id):
    """Block reference ^id. Returns (start, end)."""
    pat = re.compile(r'(?:^|\s)\^' + re.escape(block_id) + r'\s*$', re.IGNORECASE)
    mask = code_mask(lines)
    for i, line in enumerate(lines):
        if mask[i] or not pat.search(line):
            continue
        if line.strip().lower() == '^' + block_id.lower():
            # marker on its own line -> block is the preceding paragraph
            end = i - 1
            while end >= 0 and not lines[end].strip():
                end -= 1
            if end < 0:
                return None
            start = end
            while start > 0 and lines[start - 1].strip():
                start -= 1
            return start, end + 1
        lm = LIST_RE.match(line)
        if lm:
            # list item + its more-indented children
            indent = len(lm.group(1))
            end = i + 1
            while end < len(lines) and lines[end].strip() and \
                    (len(lines[end]) - len(lines[end].lstrip())) > indent:
                end += 1
            return i, end
        # plain paragraph
        start = i
        while start > 0 and lines[start - 1].strip():
            start -= 1
        end = i + 1
        while end < len(lines) and lines[end].strip():
            end += 1
        return start, end
    return None


def frontmatter_end(lines):
    if lines and lines[0].strip() == '---':
        for j in range(1, len(lines)):
            if lines[j].strip() in ('---', '...'):
                return j + 1
    return 0


class Ctx:
    def __init__(self, vault, files, args):
        self.vault, self.files, self.args = vault, files, args
        self.chain = []  # (relpath_lower, subpath_norm) currently open
        self.child_index = None  # [(relpath, frontmatter)] of notes with a `parent`
        self.parent_cache = {}   # link text -> resolved relpath | None
        self.fm_cache = {}       # relpath -> frontmatter, for notes outside child_index


def read_lines(path: Path):
    text = path.read_text(encoding='utf-8')
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    return lines


def render_lines(relpath, lines, start, end, prefix, ctx, depth, out):
    mask = code_mask(lines)
    cap = ctx.args.max_lines if depth == 0 else ctx.args.max_embed_lines
    shown_end = end if (end - start) <= cap else start + cap
    for i in range(start, shown_end):
        line = lines[i]
        out.append(f"{prefix}{i + 1:>5}\t{line}")
        if mask[i]:
            continue
        for m in EMBED_RE.finditer(line):
            if line.count('`', 0, m.start()) % 2 == 1:
                continue  # inside inline code
            if depth >= ctx.args.max_depth:
                out.append(f"{prefix}     \t   (max embed depth {ctx.args.max_depth} reached — not expanded)")
                break
            render_embed(m.group(1), relpath, prefix, ctx, depth, out)
    if shown_end < end:
        out.append(f"{prefix}    …\t(+{end - shown_end} more lines truncated — Read {relpath} for the rest)")


def unquote(val):
    val = val.strip()
    if len(val) > 1 and val[0] == val[-1] and val[0] in '"\'':
        val = val[1:-1]
    return val


def parse_frontmatter(lines):
    """Top-level frontmatter keys: scalars, and lists (block `- x` items or inline `[a, b]`)."""
    fm, key = {}, None
    if not (lines and lines[0].strip() == '---'):
        return fm
    for line in lines[1:]:
        if line.strip() in ('---', '...'):
            break
        m = FM_RE.match(line)
        if m:
            key, val = m.group(1).lower(), m.group(2).strip()
            if val.startswith('[') and not val.startswith('[['):      # inline list
                fm[key] = [unquote(x) for x in re.findall(r'"[^"]*"|\'[^\']*\'|[^,]+', val[1:-1]) if x.strip()]
            else:
                fm[key] = unquote(val)
            continue
        item = LIST_ITEM_RE.match(line)
        if item and key is not None and (fm[key] == '' or isinstance(fm[key], list)):
            fm[key] = (fm[key] or []) + [unquote(item.group(1))]
    return fm


def link_target(value):
    """'[[folder/,note|alias#H]]' -> 'folder/,note'. Plain, alias and path forms."""
    v = value.strip()
    m = WIKILINK_RE.match(v)
    if m:
        v = m.group(1)
    v = v.split('|', 1)[0].split('#', 1)[0].strip()
    return v[:-3] if v.lower().endswith('.md') else v


def child_index(ctx):
    """[(relpath, frontmatter)] for every note in CHILD_FOLDERS that has a `parent`."""
    if ctx.child_index is None:
        idx = []
        for f in ctx.files:
            if f.suffix.lower() != '.md' or f.parts[0] not in CHILD_FOLDERS:
                continue
            try:
                fm = parse_frontmatter(read_lines(ctx.vault / f))
            except OSError:
                continue
            if isinstance(fm.get('parent'), list):            # a link written as a one-item list
                fm['parent'] = fm['parent'][0] if fm['parent'] else ''
            if fm.get('parent', '').strip():
                idx.append((f, fm))
        ctx.child_index = idx
    return ctx.child_index


def children_of(ctx, rel):
    """(rows, hidden_conflict_copies, cycle) — direct children of `rel`, in topological order of `dependencies`."""
    rows, hidden = [], 0
    stem = rel.stem.lower()
    for f, fm in child_index(ctx):
        raw = link_target(fm['parent'])
        if not raw:
            continue
        if raw.lower() not in ctx.parent_cache:
            ctx.parent_cache[raw.lower()] = resolve_target(raw, ctx.files)[0]
        res = ctx.parent_cache[raw.lower()]
        hit = (res == rel) if res is not None else (raw.rsplit('/', 1)[-1].lower() == stem)
        if not hit:
            continue
        if CONFLICT_MARK in f.name:
            hidden += 1
            continue
        rows.append((f, fm))
    rows.sort(key=lambda item: item[0].name.lower())
    deps = [sibling_deps(ctx, rows, fm) for _, fm in rows]
    left, ordered, cycle = set(range(len(rows))), [], False   # Kahn's algorithm; ties by name (rows are sorted)
    while left:
        ready = [i for i in sorted(left) if not (deps[i] & left)]
        if not ready:                                       # a cycle: the rest by name, flagged in the header
            ready, cycle = sorted(left), True
        ordered.append(ready[0])
        left.remove(ready[0])
    return [rows[i] for i in ordered], hidden, cycle


def dependency_targets(fm):
    """The `dependencies` links of a note as link targets."""
    d = fm.get('dependencies', '')
    if isinstance(d, str):
        d = [d] if d.strip() else []
    return [t for t in (link_target(x) for x in d) if t]


def resolve_dependency(ctx, target):
    """(relpath|None, frontmatter) of a dependency link."""
    if target.lower() not in ctx.parent_cache:
        ctx.parent_cache[target.lower()] = resolve_target(target, ctx.files)[0]
    res = ctx.parent_cache[target.lower()]
    if res is None:
        return None, {}
    if res not in ctx.fm_cache:
        try:
            ctx.fm_cache[res] = parse_frontmatter(read_lines(ctx.vault / res))
        except OSError:
            ctx.fm_cache[res] = {}
    return res, ctx.fm_cache[res]


def sibling_deps(ctx, rows, fm):
    """Indices into `rows` of the dependencies that are siblings."""
    paths = {f: i for i, (f, _) in enumerate(rows)}
    out = set()
    for t in dependency_targets(fm):
        res, _ = resolve_dependency(ctx, t)
        if res in paths:
            out.add(paths[res])
    return out


def dependency_cells(ctx, rows):
    """Per row: (blocked, dependencies) cells — siblings shown as their row number."""
    paths = {f: i for i, (f, _) in enumerate(rows)}
    cells = []
    for _, fm in rows:
        shown, blocked = [], False
        for t in dependency_targets(fm):
            res, dfm = resolve_dependency(ctx, t)
            if res is None:
                shown.append('?' + t.rsplit('/', 1)[-1])          # broken link: does not block
                continue
            shown.append(str(paths[res] + 1) if res in paths else f'[[{res.stem}]]')
            blocked = blocked or (dfm.get('status', '') or '').strip().lower() not in FINISHED
        cells.append(('yes' if blocked else '-', ', '.join(shown) or '-'))
    return cells


def child_type(name):
    return 'project' if name.startswith(',') else ('task' if name.startswith('!') else 'note')


def render_children(raw, base_rel, note_rel, prefix, ctx, out):
    rows, hidden, cycle = children_of(ctx, note_rel)
    extra = f" · {hidden} .sync-conflict- {'copy' if hidden == 1 else 'copies'} hidden" if hidden else ''
    extra += ' · DEPENDENCY CYCLE among these rows' if cycle else ''
    if not rows:
        out.append(f"{prefix}⊞ ![[{raw}]] → {base_rel}: no note has \"{note_rel.stem}\" as its `parent`{extra}")
        return
    table = [CHILD_HEADERS]
    for i, ((f, fm), (blocked, deps)) in enumerate(zip(rows, dependency_cells(ctx, rows)), 1):
        table.append((str(i), blocked, child_type(f.name),
                      fm.get('status', '') or '-', fm.get('owner', '') or '-',
                      fm.get('stakeholder', '') or '-', fm.get('priority', '') or '-',
                      fm.get('not_before', '') or '-', fm.get('due', '') or '-', fm.get('model', '') or '-',
                      fm.get('effort', '') or '-', deps, str(f)))
    w = [max(len(r[c]) for r in table) for c in range(len(CHILD_HEADERS))]
    right = {CHILD_HEADERS.index('#'), CHILD_HEADERS.index('priority')}
    out.append(f"{prefix}┌─ {base_rel} → {len(rows)} direct children of \"{note_rel.stem}\" "
               f"(topological order){extra}")
    for r in table:
        out.append(f"{prefix}│ " + '  '.join((c.rjust(n) if i in right else c.ljust(n))
                                             for i, (c, n) in enumerate(zip(r, w))).rstrip())
    out.append(f"{prefix}└─")


def render_embed(raw, current_rel, prefix, ctx, depth, out):
    body = raw.split('|', 1)[0].strip()
    pathpart, subpath = (body.split('#', 1) + [None])[:2] if '#' in body else (body, None)
    pathpart = pathpart.strip()
    hp = prefix + '   '
    if pathpart:
        rel, note = resolve_target(pathpart, ctx.files)
    else:
        rel, note = Path(current_rel), None  # ![[#Heading]] -> same file
    if rel is None:
        out.append(f"{hp}⊞ ![[{raw}]] — unresolved")
        return
    kind = kind_of(rel)
    if kind == 'base':
        try:
            is_children = bool(CHILD_BASE_RE.search((ctx.vault / rel).read_text(encoding='utf-8')))
        except OSError:
            is_children = False
        if is_children:
            render_children(raw, rel, Path(current_rel), hp, ctx, out)
            return
    if kind != 'md':
        hint = ' — Read to view' if kind == 'image' else ''
        out.append(f"{hp}⊞ ![[{raw}]] → {rel} ({kind}{hint})")
        return
    key = (str(rel).lower(), normalize_heading(subpath) if subpath else '')
    if key in ctx.chain:
        out.append(f"{hp}⊞ ![[{raw}]] → {rel} — cycle, not expanded")
        return
    try:
        lines = read_lines(ctx.vault / rel)
    except OSError as e:
        out.append(f"{hp}⊞ ![[{raw}]] → {rel} — read error: {e}")
        return
    extra = f" ({note})" if note else ''
    if subpath is None:
        start = frontmatter_end(lines)
        end = len(lines)
        while end > start and not lines[end - 1].strip():
            end -= 1
        span = (start, end)
    elif subpath.startswith('^'):
        span = extract_block(lines, subpath[1:])
    else:
        span = extract_section(lines, subpath)
    if span is None:
        out.append(f"{hp}⊞ ![[{raw}]] → {rel} — #{subpath} not found")
        return
    a, b = span
    sub = f"#{subpath}" if subpath else ''
    out.append(f"{hp}┌─ {rel}{sub}{extra}")
    ctx.chain.append(key)
    render_lines(rel, lines, a, b, hp + '│ ', ctx, depth + 1, out)
    ctx.chain.pop()
    out.append(f"{hp}└─")


def main():
    ap = argparse.ArgumentParser(description='Read an Obsidian note with embeds expanded.')
    ap.add_argument('path', help='vault-relative path or bare note name, optional #Heading / #^blockid')
    ap.add_argument('--vault', default=None)
    ap.add_argument('--max-depth', type=int, default=4)
    ap.add_argument('--max-embed-lines', type=int, default=400)
    ap.add_argument('--max-lines', type=int, default=2000)
    ap.add_argument('--subtask-base-only', action='store_true',
                    help="print only the embedded subtasks.base children table, not the note's text")
    args = ap.parse_args()

    vault = Path(args.vault).resolve() if args.vault else Path(__file__).resolve().parents[2]
    spec, sub = (args.path.split('#', 1) + [None])[:2] if '#' in args.path else (args.path, None)
    spec = spec.strip()

    files = build_index(vault)
    rel = note = None
    p = Path(spec)
    if p.is_absolute():
        try:
            rel = p.resolve().relative_to(vault)
        except ValueError:
            sys.exit(f"error: {spec} is outside the vault {vault}")
        if not p.exists():
            sys.exit(f"error: {spec} does not exist")
    elif (vault / spec).is_file():
        rel = Path(spec)
    elif (vault / (spec + '.md')).is_file():
        rel = Path(spec + '.md')
    else:
        rel, note = resolve_target(spec, files)
    if rel is None:
        sys.exit(f"error: could not resolve '{spec}' in vault {vault}")

    if kind_of(rel) != 'md':
        sys.exit(f"error: {rel} is not markdown — use the Read tool directly")

    lines = read_lines(vault / rel)
    span, subnote = (0, len(lines)), ''
    if sub is not None:
        span = extract_block(lines, sub[1:]) if sub.startswith('^') else extract_section(lines, sub)
        if span is None:
            sys.exit(f"error: subpath #{sub} not found in {rel}")
        subnote = f" · section #{sub} · lines {span[0] + 1}-{span[1]}"

    out = [f"file: {rel}{subnote}" + (f" ({note})" if note else '')]
    ctx = Ctx(vault, files, args)
    if args.subtask_base_only:
        mask = code_mask(lines)
        embedded = any(re.search(r'!\[\[\s*subtasks\.base', ln) for i, ln in enumerate(lines) if not mask[i])
        if embedded:
            render_children('subtasks.base', 'subtasks.base', rel, '', ctx, out)
        else:
            out.append(f"(no ![[subtasks.base]] embed in {rel} \u2014 its children are invisible both in Obsidian "
                       f"and to this script; add the embed line at the very top of the body)")
        print('\n'.join(out))
        return
    ctx.chain.append((str(rel).lower(), normalize_heading(sub) if sub else ''))
    if not lines:
        out.append("(empty file)")
    render_lines(rel, lines, span[0], span[1], '', ctx, 0, out)
    print('\n'.join(out))


if __name__ == '__main__':
    main()
