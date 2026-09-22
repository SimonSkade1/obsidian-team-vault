# Setting up the automation host

> **Not for members.** This file is only for whoever runs the *automation host* — the one machine that holds the vault's git repository and runs the nightly summary and cleanup jobs (currently Simon's VPS, see below). If you just use the vault, `INSTALL_AND_SETUP.md` is your setup and you can ignore this file entirely. It is kept so the host can be rebuilt, moved to another machine, or handed to someone else.

**Exactly one machine does this.** The vault's git repository and its two scheduled jobs belong to that machine alone: run by several people they would collide (two repositories, two writers of the same summary note, two cleanups moving the same files). Everyone else follows `INSTALL_AND_SETUP.md` and never touches git here.

Pick the machine that is on most of the time, has a Claude Code subscription login, and already syncs this vault. The steps below are Linux; on macOS or Windows only the scheduling differs.

**Current host (2026-09-19):** the Hetzner VPS `hetzner-vps-simon` (<HOST-IP>), user `simon`, vault at `/home/simon/PauseAI_Global_shared_vault`, Syncthing folder id `pai-shared-vault`, timer at 23:30 in the host's timezone — that machine runs UTC. Moving the host elsewhere = move the folder *including* `.git` (rsync), redo steps 3, 8 and 9 there, remove the units on the old host, and re-share the Syncthing folder from the new one.

## Preflight

1. Work from the vault root — `README.md`, `me.base` and `.claude/` are in it.
2. Check what the jobs need, and install what is missing: `git --version`; `flock` and `uuidgen` (util-linux — `flock` may be absent on macOS, which then needs a small edit to both wrapper scripts); `python3 --version` (3.8+); `claude --version` plus a logged-in subscription account (step 13 proves the login works).
3. This machine already holds files the others must never receive, above all `.git`. So make sure `.stignore` exists in the vault root, containing the single line `#include .stignore-shared`, *before* you add the folder to Syncthing here — `.stignore-shared` is already on disk, so the include resolves right away. (Syncthing's **Edit → Ignore Patterns** tab writes the same file and works here too, including while you add the folder; writing it first is just easier to check — `cat .stignore`.)
	1. Then add the vault as a Syncthing folder **on this machine first** (any id the members' Syncthing does not use yet — currently `pai-shared-vault`; the label is free). Copy the versioning of your other folders if you want deleted files recoverable (currently: staggered, 1 year). Members are added afterwards, one command each: sub-item 4 below.
	2. **Hub and spoke, not a mesh:** this host is the only device that shares the folder with anyone. Every member accepts the share from *this* device and adds no other member's device to it. That keeps one place where the file set is authoritative, keeps a new member's onboarding to one accept, and stops a laptop that is offline for weeks from resurrecting deleted files for everyone. It costs the direct laptop-to-laptop path: while the host is down, members do not exchange edits.
	3. Wait until this folder reports **Up to Date** and 0 errors before telling a member to accept — they pull from here.
	4. **Adding a member** — the host half of `INSTALL_AND_SETUP.md` steps 2 and 5. They send you their device ID and first name; you run `other-files/add-member.sh <DEVICE-ID> <name>` on this machine. It adds the device and shares the folder through Syncthing's own REST API on localhost, so it needs no GUI and no ssh tunnel into this host, and re-running it changes nothing. With no arguments it prints the devices the folder is shared with and this host's device ID — the one the member sees in their notification. By hand it is the same two actions: **Add Remote Device**, then the folder's **Edit → Sharing**. (Verified against Syncthing 1.27.2 and 2.1.5; it reads the API key from `config.xml`, override the location with `STHOME` and the folder id with `PAI_FOLDER_ID`.)
4. Create `_local/me.md` with your own `user:` line (three lines: `---`, `user: yourname`, `---` — the member route, `setup-member`, refuses to run on this host because of the `.git` here) — the summaries are written by a Claude session that reads the same bases everyone else sees.

## Git — the pipeline's backbone

The nightly job commits one snapshot per day and then summarizes that diff; the cleanup uses the history to scope its run. Both refuse to start without a repository. This repository is the automation's: it has no remote, it is never synced (`.stignore-shared` ignores `/.git`), and nobody clones it.

5. `git rev-parse --git-dir` — if it fails: `git init -b main`.
6. Make sure a commit identity exists (`git config user.name`, `git config user.email`; set them repo-locally if they are empty). The address ends up in every commit of this local repository.
7. If the repository has no commits yet: `git add -A && git commit -m "Initial vault snapshot"`.

## Scheduling

Two wrapper scripts in `other-files/` are the whole interface: `run-daily-review.sh` (nightly — commits the snapshot, writes the daily note in `periodic-auto-summaries/`, then any due weekly/monthly/quarterly/yearly note, and chains the cleanup) and `run-vault-cleanup.sh` (called by the first one, runs at most every second day). The nightly wrapper also runs `other-files/check-unassigned.py` (pure python, no Claude): when new unassigned items appear — neither `owner` nor `next_action_by`, status not terminal, the `Unassigned` view of `me.base` — it files an `inbox` task for simon in `quick-tasks-and-notes/`, or appends them to the open check task if there is one; an item is listed once, ever (every `!check unassigned items …` file, archived ones too, counts as coverage). Scheduling means invoking `run-daily-review.sh` once a night; 23:30 keeps it inside the quiet hour the cleanup wants, when other members are unlikely to have files open.

8. **Linux (systemd user units, shipped):** the units in `other-files/systemd/` are named `pai-shared-daily-review.service` / `.timer` so they cannot collide with the units of another vault on the same account, and the service's `ExecStart` points at `%h/PauseAI_Global_shared_vault/other-files/run-daily-review.sh` (`%h` = the running user’s home directory). **If the vault sits anywhere else, edit that line first** (a header comment marks it); edit the copy in the vault — `install.sh` links the units from here, so the vault copies stay the source of truth. Then `bash other-files/systemd/install.sh`, which links, enables and starts the timer and prints the next fire times.
	1. **The model** the two jobs run on is the `"model"` key of `other-files/scheduled-settings.json` and `other-files/cleanup-settings.json` (currently `opus`) — the wrappers pass those files with `--settings` and no `--model`. Change the model there, not in the scripts.
	2. That key is also the fix for a headless run that dies with "There's an issue with the selected model": a `"model"` in the host user's `~/.claude/settings.json` applies to `claude -p` as well, and an alias that only interactive sessions accept then kills every scheduled run (it silently broke Simon's other vault for two nights in 2026-09). The `--settings` key wins over it, so setting it here makes the jobs independent of the host's interactive default. Check once: `claude -p "Reply with exactly: ok" --settings other-files/scheduled-settings.json --strict-mcp-config`.
9. **Then allow the timer to run without you: `sudo loginctl enable-linger $USER`.** A `systemctl --user` timer lives inside your login session — on a machine you only ssh into, the whole user manager is torn down when you log out and the job silently never fires again. Run this once on any host where you are not permanently logged in (a VPS above all); `install.sh` does not do it, because it needs root, but it warns you when lingering is off. On a desktop that stays logged in it is optional — `Persistent=true` in the timer catches up a run the machine slept through.
10. **macOS / Windows:** no systemd — set up the platform equivalent (a launchd plist, a Task Scheduler job) that runs `other-files/run-daily-review.sh` nightly with the vault as the working directory. A user must be logged in for the Claude session to run.

## Verify without spending tokens

11. `DR_COMPUTE_ONLY=1 bash other-files/run-daily-review.sh` — prints the review periods it would write, then exits.
12. `VC_GATE_ONLY=1 bash other-files/run-vault-cleanup.sh` — prints the cleanup's cadence decision (on a fresh vault: `LAST_RUN=none`).
13. `bash .claude/scripts/check-claude-usage.sh` — prints the plan's 5-hour and 7-day usage, and is the one check that proves the subscription login works in this shell. Nothing gates on it automatically: the wrappers do not call it (the VNA controller does), so if this host shares a plan with someone's interactive work, look here before adding more scheduled jobs.
14. `python3 .claude/scripts/read_obsidian.py "README.md"` — the read script runs.
15. `loginctl show-user $USER --property=Linger` — must print `Linger=yes` on any host you log out of; otherwise re-read step 9.
16. `systemctl --user list-timers pai-shared-daily-review.timer` — shows when the job fires next.
17. If any command warns "this workspace has not been trusted", Claude Code ignores this vault's own `.claude/settings.json` allowlist. Run `claude` once interactively in the vault root and accept the dialog, or — on a host you only reach over ssh — set `projects["<vault path>"].hasTrustDialogAccepted: true` in `~/.claude.json` (done on the current host 2026-09-19; the warning line names the exact key).

## What the jobs will do

18. Each run commits whatever changed in the vault since the last snapshot — everyone's edits, under this machine's commit identity. There is no authorship inside the vault, so the summaries say what changed, not who changed it.
19. The cleanup moves files: it rebuilds the `projects-tasks-notes/` folder tree from the `parent` properties and moves finished trees into `archived/`. Under Syncthing a move is a delete plus a create, and it cannot see which notes are open on other people's machines — it skips files modified in the last 30 minutes, which is why it runs in the middle of the night. Its documentation is `other-files/vault-cleanup routine.md`, the open questions it collects `other-files/vault-cleanup log.md`.
20. Told to stop: disable the timer (`systemctl --user disable --now pai-shared-daily-review.timer`). Nothing else in the vault depends on these jobs.
