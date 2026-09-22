---
name: obsidian-bases
description: Query, create, and edit Obsidian Bases (.base files) — views, filters, formulas, and the base:query CLI. Use for anything involving a .base file or database-style views of notes.
---

# Obsidian Bases

Base files are YAML defining database-like views over vault notes. This vault's bases: `me.base` (everything in `projects-tasks-notes/`, first view filtered to the current user), `major_projects.base` (the top-level projects: `,` files with an empty `parent`, grouped by owner; its own small `formulas:` block, not the shared one), `subtasks.base` (embedded in every project's `# Subtasks`; direct children only) and `recent.base` (recently modified notes). `me.base` and `subtasks.base` carry the same `formulas:` block verbatim up to `section` (Bases has no include mechanism) — change one and change the other in the same edit, or the two views of an item disagree; only `me.base` has formulas after it: `parent_terminal`, `nested`, `nested_any` (the *overview* views hide items whose parent has the same owner — those are seen in the project's table) and the *projects* views' group key `pgroup` with its parts (next section). `major_projects.base` repeats the block's effective-priority lines with `top: file`.

## The projects views' group key

Bases groups by one property and shows the key as the header, so in `my projects` / `everyone projects` the key is the sort order made readable: `<effective priority> <name>` per project along the ancestor chain (`seg1`–`seg3` for the ancestors, the head's own segment inline in `pgroup`; see the next section), joined by ` › `, e.g. `3 improve this synced obsidian vault › 9 create discord bot:`. Groups are ordered with `Intl.Collator(undefined, {sensitivity: "base", numeric: true})` — natural order, `10` after `7`, no zero-padding — in direction DESC, so higher priority comes first; the trailing `:` makes a parent's key sort before its children's keys (without it the parent key is a prefix of theirs and would follow them in DESC); `no project:` starts with a letter, which collates above digits, so it comes first. Only a project with non-terminal children (`has_children`, via `file.backlinks`) heads a group; every other row takes its parent's key; within a group the sort `is_head` DESC puts the project first. `base:query` ignores sort and groupBy — check rendered order with `bash .claude/scripts/bases_render.sh me.base "my projects"`.

## Effective priority

`effective_priority` (the row sort of every view) = max(own `priority`, or 5 if empty; the highest `priority` on any descendant that would sit in the viewer's sections 1–4 — Inbox, In Progress, Review, Your Tasks — so it is per member; empty priorities contribute nothing). Formulas can't recurse or query the vault, so each row walks its whole tree once: `anc1`–`anc3` → `top` (the tree's root project, or the row itself) → `lvl1`–`lvl3` (the non-terminal nodes by depth below `top`, each level = the `backlinks` of the previous level whose `parent` is in it) → `tree` (the counting nodes, each as the string `"<priority>|<ancestor path>|…|"`, since a formula can't carry a pair) → a node's effective priority filters `tree` by `"|<its path>|"`. The same filter with `anc1`–`anc3` gives `seg1`–`seg3`, the parts of `pgroup`. Limit: three levels below `top`, i.e. four-level trees; one more level costs one more `anc`, `lvl` and `seg` line. Cost: one tree walk per row.

## The New button's pre-fill — why the bases carry an always-true filter

A base's **New** button writes properties into the new note from the filters: every non-negated rule of the form `prop == value` (also `contains`, `file.hasTag`, `file.inFolder`), wherever it sits — inside an `or` too — with the right side evaluated, formulas and `this` included; then, empty, every note property of the view's `order` that is still missing. This is how a new note here gets its header and its `owner` without any plugin:

1. `parent == this` in `subtasks.base` fills `parent` with the project the table is embedded in.
2. `me.base`, `subtasks.base` and `major_projects.base` end their global `filters.and` with

	```yaml
	- or:
	    - owner == formula.me
	    - owner != formula.me
	```

	The pair is always true, so it selects the same rows; its one job is that the first rule fills `owner` with the member's name (`formula.me`, read from `_local/me.md`). Keep it although it looks redundant in the filter UI — a YAML comment would not survive Obsidian's re-saves of the file, so the explanation lives here.

This is undocumented Obsidian behaviour, verified on 1.13.7: if new notes stop getting their `owner` after an Obsidian update, check this first. The top-level keys `newItemFolder` (where New creates the note) and `newItemTemplate` (copies that note's properties instead, which switches the filter pre-fill off) exist as well.

## Querying a base

**List views:**

```bash
obsidian base:query path="me.base"
```

**Query a view:**

```bash
obsidian base:query path="me.base" view="my overview" format=json
```

Paths relative to vault root. Formats: `json|csv|tsv|md|paths`. The CLI needs the Obsidian app running.

To understand a base's structure, just read the `.base` file — human-readable YAML with `filters`, `formulas`, `properties`, `views`.

## Workflow for creating/editing

1. **Create the file**: Create a `.base` file with valid YAML
2. **Define scope**: Add `filters` to select which notes appear (by tag, folder, property, or date)
3. **Add formulas** (optional): Define computed properties in the `formulas` section
4. **Configure views**: Add one or more views (`table`, `cards`, `list`, or `map`) with `order` specifying which properties to display
5. **Validate**: Verify valid YAML; check all referenced properties/formulas exist. Common issues: unquoted strings with special YAML characters, mismatched quotes in formulas, referencing `formula.X` without defining `X` in `formulas`
6. **Test**: Open the `.base` file in Obsidian (or run `base:query`) to confirm it renders. On YAML error, check quoting rules below

## Schema

```yaml
# Global filters apply to ALL views in the base
filters:
  # Can be a single filter string
  # OR a recursive filter object with and/or/not
  and: []
  or: []
  not: []

# Define formula properties that can be used across all views
formulas:
  formula_name: 'expression'

# Configure display names and settings for properties
properties:
  property_name:
    displayName: "Display Name"
  formula.formula_name:
    displayName: "Formula Display Name"
  file.ext:
    displayName: "Extension"

# Define custom summary formulas
summaries:
  custom_summary_name: 'values.mean().round(3)'

# Define one or more views
views:
  - type: table | cards | list | map
    name: "View Name"
    limit: 10                    # Optional: limit results
    groupBy:                     # Optional: group results
      property: property_name
      direction: ASC | DESC
    filters:                     # View-specific filters
      and: []
    order:                       # Properties to display in order
      - file.name
      - property_name
      - formula.formula_name
    summaries:                   # Map properties to summary formulas
      property_name: Average
```

## Filter Syntax

Filters narrow down results. They can be applied globally or per-view.

### Filter Structure

```yaml
# Single filter
filters: 'status == "done"'

# AND - all conditions must be true
filters:
  and:
    - 'status == "done"'
    - 'priority > 3'

# OR - any condition can be true
filters:
  or:
    - 'file.hasTag("book")'
    - 'file.hasTag("article")'

# NOT - exclude matching items
filters:
  not:
    - 'file.hasTag("archived")'

# Nested filters
filters:
  or:
    - file.hasTag("tag")
    - and:
        - file.hasTag("book")
        - file.hasLink("Textbook")
    - not:
        - file.hasTag("book")
        - file.inFolder("Required Reading")
```

### Filter Operators

`==`, `!=`, `>`, `<`, `>=`, `<=`, `&&`, `||`, `!`

## Properties

### Three Types of Properties

1. **Note properties** - From frontmatter: `note.author` or just `author`
2. **File properties** - File metadata: `file.name`, `file.mtime`, etc.
3. **Formula properties** - Computed values: `formula.my_formula`

### File Properties Reference

| Property | Type | Description |
|----------|------|-------------|
| `file.name` | String | File name |
| `file.basename` | String | File name without extension |
| `file.path` | String | Full path to file |
| `file.folder` | String | Parent folder path |
| `file.ext` | String | File extension |
| `file.size` | Number | File size in bytes |
| `file.ctime` | Date | Created time |
| `file.mtime` | Date | Modified time |
| `file.tags` | List | All tags in file |
| `file.links` | List | Internal links in file |
| `file.backlinks` | List | Files linking to this file |
| `file.embeds` | List | Embeds in the note |
| `file.properties` | Object | All frontmatter properties |

### The `this` Keyword

- In main content area: refers to the base file itself
- When embedded: refers to the embedding file
- In sidebar: refers to the active file in main content

## Formula Syntax

Formulas compute values from properties. Defined in the `formulas` section.

```yaml
formulas:
  # Simple arithmetic
  total: "price * quantity"

  # Conditional logic
  status_icon: 'if(done, "✅", "⏳")'

  # String formatting
  formatted_price: 'if(price, price.toFixed(2) + " dollars")'

  # Date formatting
  created: 'file.ctime.format("YYYY-MM-DD")'

  # Calculate days since created (use .days for Duration)
  days_old: '(now() - file.ctime).days'

  # Calculate days until due date
  days_until_due: 'if(due_date, (date(due_date) - today()).days, "")'
```

## Key Functions

Most commonly used functions. For the complete reference of all types (Date, String, Number, List, File, Link, Object, RegExp), see [FUNCTIONS_REFERENCE.md](references/FUNCTIONS_REFERENCE.md).

| Function | Signature | Description |
|----------|-----------|-------------|
| `date()` | `date(string): date` | Parse string to date (`YYYY-MM-DD HH:mm:ss`) |
| `now()` | `now(): date` | Current date and time |
| `today()` | `today(): date` | Current date (time = 00:00:00) |
| `if()` | `if(condition, trueResult, falseResult?)` | Conditional |
| `duration()` | `duration(string): duration` | Parse duration string |
| `file()` | `file(path): file` | Get file object |
| `link()` | `link(path, display?): Link` | Create a link |

### Duration Type

When subtracting two dates, the result is a **Duration** type (not a number).

**Duration Fields:** `duration.days`, `duration.hours`, `duration.minutes`, `duration.seconds`, `duration.milliseconds`

**IMPORTANT:** Duration does NOT support `.round()`, `.floor()`, `.ceil()` directly. Access a numeric field first (like `.days`), then apply number functions.

```yaml
# CORRECT: Calculate days between dates
"(date(due_date) - today()).days"                    # Returns number of days
"(now() - file.ctime).days"                          # Days since created
"(date(due_date) - today()).days.round(0)"           # Rounded days

# WRONG - will cause error:
# "((date(due) - today()) / 86400000).round(0)"      # Duration doesn't support division then round
```

### Date Arithmetic

```yaml
# Duration units: y/year/years, M/month/months, d/day/days,
#                 w/week/weeks, h/hour/hours, m/minute/minutes, s/second/seconds
"now() + \"1 day\""       # Tomorrow
"today() + \"7d\""        # A week from today
"now() - file.ctime"      # Returns Duration
"(now() - file.ctime).days"  # Get days as number
```

## View Types

### Table View

```yaml
views:
  - type: table
    name: "My Table"
    order:
      - file.name
      - status
      - due_date
    summaries:
      price: Sum
      count: Average
```

### Cards View

```yaml
views:
  - type: cards
    name: "Gallery"
    order:
      - file.name
      - cover_image
      - description
```

### List View

```yaml
views:
  - type: list
    name: "Simple List"
    order:
      - file.name
      - status
```

### Map View

Requires latitude/longitude properties and the Maps community plugin.

```yaml
views:
  - type: map
    name: "Locations"
    # Map-specific settings for lat/lng properties
```

## Default Summary Formulas

| Name | Input Type | Description |
|------|------------|-------------|
| `Average` | Number | Mathematical mean |
| `Min` | Number | Smallest number |
| `Max` | Number | Largest number |
| `Sum` | Number | Sum of all numbers |
| `Range` | Number | Max - Min |
| `Median` | Number | Mathematical median |
| `Stddev` | Number | Standard deviation |
| `Earliest` | Date | Earliest date |
| `Latest` | Date | Latest date |
| `Range` | Date | Latest - Earliest |
| `Checked` | Boolean | Count of true values |
| `Unchecked` | Boolean | Count of false values |
| `Empty` | Any | Count of empty values |
| `Filled` | Any | Count of non-empty values |
| `Unique` | Any | Count of unique values |

## Complete Example

```yaml
filters:
  and:
    - file.hasTag("task")
    - 'file.ext == "md"'

formulas:
  days_until_due: 'if(due, (date(due) - today()).days, "")'
  is_overdue: 'if(due, date(due) < today() && status != "done", false)'
  priority_label: 'if(priority == 1, "🔴 High", if(priority == 2, "🟡 Medium", "🟢 Low"))'

properties:
  status:
    displayName: Status
  formula.days_until_due:
    displayName: "Days Until Due"
  formula.priority_label:
    displayName: Priority

views:
  - type: table
    name: "Active Tasks"
    filters:
      and:
        - 'status != "done"'
    order:
      - file.name
      - status
      - formula.priority_label
      - due
      - formula.days_until_due
    groupBy:
      property: status
      direction: ASC
    summaries:
      formula.days_until_due: Average

  - type: table
    name: "Completed"
    filters:
      and:
        - 'status == "done"'
    order:
      - file.name
      - completed_date
```

## Embedding Bases

Embed in Markdown files:

```markdown
![[MyBase.base]]

<!-- Specific view -->
![[MyBase.base#View Name]]
```

## YAML Quoting Rules

- Use single quotes for formulas containing double quotes: `'if(done, "Yes", "No")'`
- Use double quotes for simple strings: `"My View Name"`
- Escape nested quotes properly in complex expressions

## Troubleshooting

### YAML Syntax Errors

**Unquoted special characters**: Strings containing `:`, `{`, `}`, `[`, `]`, `,`, `&`, `*`, `#`, `?`, `|`, `-`, `<`, `>`, `=`, `!`, `%`, `@`, `` ` `` must be quoted.

```yaml
# WRONG - colon in unquoted string
displayName: Status: Active

# CORRECT
displayName: "Status: Active"
```

**Mismatched quotes in formulas**: When a formula contains double quotes, wrap the entire formula in single quotes.

```yaml
# WRONG - double quotes inside double quotes
formulas:
  label: "if(done, "Yes", "No")"

# CORRECT - single quotes wrapping double quotes
formulas:
  label: 'if(done, "Yes", "No")'
```

### Common Formula Errors

**Duration math without field access**: Subtracting dates returns a Duration, not a number. Always access `.days`, `.hours`, etc.

```yaml
# WRONG - Duration is not a number
"(now() - file.ctime).round(0)"

# CORRECT - access .days first, then round
"(now() - file.ctime).days.round(0)"
```

**Missing null checks**: Properties may not exist on all notes. Use `if()` to guard.

```yaml
# WRONG - crashes if due_date is empty
"(date(due_date) - today()).days"

# CORRECT - guard with if()
'if(due_date, (date(due_date) - today()).days, "")'
```

**Referencing undefined formulas**: Ensure every `formula.X` in `order` or `properties` has a matching entry in `formulas`.

```yaml
# This will fail silently if 'total' is not defined in formulas
order:
  - formula.total

# Fix: define it
formulas:
  total: "price * quantity"
```

## References

- [Bases Syntax](https://help.obsidian.md/bases/syntax)
- [Functions](https://help.obsidian.md/bases/functions)
- [Views](https://help.obsidian.md/bases/views)
- [Formulas](https://help.obsidian.md/formulas)
- [Complete Functions Reference](references/FUNCTIONS_REFERENCE.md)
