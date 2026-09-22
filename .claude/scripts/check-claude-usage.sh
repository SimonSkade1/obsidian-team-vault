#!/bin/bash
# Check Claude plan usage via the internal OAuth usage API.
#
# Which account gets reported — first match wins:
#   1. $CLAUDE_CODE_OAUTH_TOKEN  — explicit token (lent / setup-token accounts).
#   2. $CLAUDE_CONFIG_DIR        — explicit dir (e.g. a shell function for a second account,
#                                  or a Claudian session that already exports it).
#   3. CLAUDE_CONFIG_DIR written in Claudian's *shared environment variables*, read from
#      <vault>/.claudian/claudian-settings.json (the plugin's live settings store;
#      .obsidian/plugins/*/data.json is a legacy fallback the plugin ignores).
#      Only that shared field counts — envSnippets are picked per conversation, not global.
#      This step matters when the setting was saved after the current session started, or
#      when the script runs from a shell that never inherited the var.
#   4. ~/.claude                 — the plain `claude` login.
# Inside a config dir: .credentials.json (browser OAuth login) first, then .oauth-token
# (alt-account dirs store a bare setup-token there and have no .credentials.json;
# Claudian doesn't pass CLAUDE_CODE_OAUTH_TOKEN through to subshells, so this is how an
# in-session run on such an account finds its token).
#
# The account actually used is printed under the header, so a stale/unexpected switch
# is visible instead of silent. Pass --raw for the raw JSON (account line goes to stderr).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# CLAUDE_CONFIG_DIR from Claudian's shared environment variables, if set there.
claudian_config_dir() {
  local f dir
  for f in "$VAULT_ROOT/.claudian/claudian-settings.json" "$PWD/.claudian/claudian-settings.json"; do
    [ -f "$f" ] || continue
    dir=$(node -e '
      const fs = require("fs");
      let s;
      try { s = JSON.parse(fs.readFileSync(process.argv[1], "utf8")).sharedEnvironmentVariables; } catch { process.exit(0); }
      if (typeof s !== "string") process.exit(0);
      let v = "";
      for (const line of s.split(/\r?\n/)) {
        const m = line.match(/^\s*(?:export\s+)?CLAUDE_CONFIG_DIR\s*=\s*(.*)$/);
        if (m) v = m[1].trim().replace(/^(["\x27])(.*)\1$/, "$2");
      }
      if (v) console.log(v);
    ' "$f" 2>/dev/null)
    if [ -n "$dir" ]; then printf '%s\n' "$dir"; return 0; fi
  done
  return 1
}

TOKEN=""; CONF_DIR=""; SOURCE=""; ACCT_EMAIL=""; ACCT_TIER=""

if [ -n "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
  TOKEN="$CLAUDE_CODE_OAUTH_TOKEN"
  SOURCE="token from \$CLAUDE_CODE_OAUTH_TOKEN"
else
  if [ -n "$CLAUDE_CONFIG_DIR" ]; then
    CONF_DIR="$CLAUDE_CONFIG_DIR"; SOURCE="\$CLAUDE_CONFIG_DIR"
  else
    CLAUDIAN_DIR=$(claudian_config_dir)
    if [ -n "$CLAUDIAN_DIR" ]; then
      CLAUDIAN_DIR="${CLAUDIAN_DIR/#\~/$HOME}"
      CLAUDIAN_DIR="${CLAUDIAN_DIR//\$\{HOME\}/$HOME}"
      CLAUDIAN_DIR="${CLAUDIAN_DIR//\$HOME/$HOME}"
      if [ -f "$CLAUDIAN_DIR/.credentials.json" ] || [ -f "$CLAUDIAN_DIR/.oauth-token" ]; then
        CONF_DIR="$CLAUDIAN_DIR"; SOURCE="Claudian setting"
      else
        echo "Warning: Claudian's CLAUDE_CONFIG_DIR ($CLAUDIAN_DIR) holds no credentials — falling back to ~/.claude." >&2
      fi
    fi
    if [ -z "$CONF_DIR" ]; then CONF_DIR="$HOME/.claude"; SOURCE="default"; fi
  fi

  # token + account identity from the chosen config dir (0x1f-separated, token never printed)
  INFO=$(node -e '
    const fs = require("fs"), path = require("path");
    const dir = process.argv[1];
    const read = (f) => { try { return fs.readFileSync(path.join(dir, f), "utf8"); } catch { return null; } };
    let token = "", email = "", tier = "";
    const credRaw = read(".credentials.json");
    if (credRaw) {
      try {
        const o = JSON.parse(credRaw).claudeAiOauth || {};
        token = o.accessToken || "";
        tier = o.rateLimitTier || o.subscriptionType || "";
      } catch {}
    }
    if (!token) { const t = read(".oauth-token"); if (t) token = t.trim(); }
    // Claude Code keeps the account record in <CLAUDE_CONFIG_DIR>/.claude.json, but for the
    // default dir (~/.claude) it sits at ~/.claude.json — one level up.
    let cfgRaw = read(".claude.json");
    if (!cfgRaw && path.resolve(dir) === path.join(require("os").homedir(), ".claude")) {
      try { cfgRaw = fs.readFileSync(path.join(require("os").homedir(), ".claude.json"), "utf8"); } catch {}
    }
    if (cfgRaw) { try { email = (JSON.parse(cfgRaw).oauthAccount || {}).emailAddress || ""; } catch {} }
    // \x1f, not \t: tab is IFS whitespace, so bash would collapse an empty middle field.
    console.log([token, email, tier].join("\x1f"));
  ' "$CONF_DIR")
  IFS=$'\x1f' read -r TOKEN ACCT_EMAIL ACCT_TIER <<< "$INFO"

  if [ -z "$TOKEN" ]; then
    echo "Error: No token found (checked \$CLAUDE_CODE_OAUTH_TOKEN, $CONF_DIR/.credentials.json, $CONF_DIR/.oauth-token)"
    echo "Set CLAUDE_CODE_OAUTH_TOKEN, or log into Claude Code."
    exit 1
  fi
  SOURCE="${CONF_DIR/#$HOME/~} ($SOURCE)"
fi

case "$ACCT_TIER" in
  *max_20x*) TIER_LABEL="Max 20x" ;;
  *max_5x*)  TIER_LABEL="Max 5x" ;;
  *pro*)     TIER_LABEL="Pro" ;;
  *)         TIER_LABEL="$ACCT_TIER" ;;
esac
ACCOUNT_LABEL="${ACCT_EMAIL:-unknown account}"
[ -n "$TIER_LABEL" ] && ACCOUNT_LABEL="$ACCOUNT_LABEL · $TIER_LABEL"
ACCOUNT_LABEL="$ACCOUNT_LABEL · $SOURCE"

fetch_usage() {
  curl -s -w "\n%{http_code}" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -H "anthropic-beta: oauth-2025-04-20" \
    "https://api.anthropic.com/api/oauth/usage"
}

RESPONSE=$(fetch_usage)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

# The endpoint 429s after a handful of calls in a minute. That is transient, unlike the
# 403 a setup-token gets, so retry once instead of dropping to the header probe (which
# would spend an inference call of this account's quota for a 5h/7d-only report).
if [ "$HTTP_CODE" = "429" ]; then
  sleep 3
  RESPONSE=$(fetch_usage)
  HTTP_CODE=$(echo "$RESPONSE" | tail -1)
  BODY=$(echo "$RESPONSE" | sed '$d')
fi

if [ "$HTTP_CODE" = "429" ]; then
  echo "Error: the usage API is rate-limiting this account (HTTP 429). Wait a minute and re-run." >&2
  exit 1
fi

if [ "$HTTP_CODE" != "200" ]; then
  # Setup-tokens (lent/alt accounts) lack the user:profile scope, so the OAuth
  # usage endpoint 403s permanently for them. Fallback: make a minimal 1-token
  # haiku call and read the anthropic-ratelimit-unified-* response headers —
  # the same Pro/Max subscription meter, but only 5h/7d totals + overage status
  # (no per-model weekly breakdown, no credit spend).
  HDRS=$(curl -s -D - -o /dev/null -X POST "https://api.anthropic.com/v1/messages" \
    -H "Authorization: Bearer $TOKEN" \
    -H "anthropic-beta: oauth-2025-04-20" \
    -H "anthropic-version: 2023-06-01" \
    -H "content-type: application/json" \
    -d '{"model":"claude-haiku-4-5","max_tokens":1,"messages":[{"role":"user","content":"hi"}]}' | tr -d '\r')

  if ! printf '%s\n' "$HDRS" | grep -qi '^anthropic-ratelimit-unified-'; then
    echo "Error: usage API returned HTTP $HTTP_CODE, and the rate-limit-header fallback got no unified headers either."
    echo "Usage API body: $BODY"
    echo "Fallback response status: $(printf '%s\n' "$HDRS" | head -1)"
    exit 1
  fi

  if [ "${1}" = "--raw" ]; then
    echo "$ACCOUNT_LABEL" >&2
    printf '%s\n' "$HDRS" | grep -i '^anthropic-ratelimit-unified-'
    exit 0
  fi

  node -e "
const lines = process.argv[1].split('\n');
const h = {};
for (const l of lines) {
  const m = l.match(/^anthropic-ratelimit-unified-(.+?):\s*(.*)$/i);
  if (m) h[m[1].toLowerCase()] = m[2].trim();
}
const pct = (v) => v == null ? '—' : (Number(v) * 100).toFixed(1) + '%';
const when = (s, dateOnly) => {
  if (!s) return '—';
  const d = /^\d+\$/.test(s) ? new Date(Number(s) * 1000) : new Date(s);
  if (isNaN(d)) return s;
  return dateOnly ? d.toLocaleDateString() : d.toLocaleTimeString();
};
const row = (label, value, note) => console.log(label.padEnd(16) + value + (note ? '  ' + note : ''));

console.log('═══ Claude Usage ═══  (from rate-limit headers; 5h/7d only — no per-model/credit breakdown)');
if (process.argv[2]) console.log(process.argv[2]);
console.log();
const flag = (k) => h[k] && h[k] !== 'allowed' ? ' [' + h[k] + ']' : '';
row('5-hour window:', pct(h['5h-utilization']) + flag('5h-status'), '(resets ' + when(h['5h-reset']) + ')');
row('7-day window:', pct(h['7d-utilization']) + flag('7d-status'), '(resets ' + when(h['7d-reset'], true) + ')');
if (h['overage-status']) {
  row('Overage:', h['overage-status'], h['overage-disabled-reason'] ? '(' + h['overage-disabled-reason'] + ')' : '');
}
// Surface any additional unified utilization headers (e.g. future per-model ones)
const known = ['5h-utilization','5h-reset','5h-status','7d-utilization','7d-reset','7d-status',
  'overage-status','overage-disabled-reason','status','fallback-percentage','representative-claim','reset'];
for (const k of Object.keys(h)) {
  if (!known.includes(k)) row(k + ':', h[k]);
}
console.log();
" "$HDRS" "$ACCOUNT_LABEL"
  exit 0
fi

# Raw JSON for debugging (pass --raw flag)
if [ "${1}" = "--raw" ]; then
  echo "$ACCOUNT_LABEL" >&2
  echo "$BODY" | node -e "process.stdin.setEncoding('utf8');let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>console.log(JSON.stringify(JSON.parse(d),null,2)))"
  exit 0
fi

# Parse and display with node
node -e "
const d = JSON.parse(process.argv[1]);
const pct = (v) => v == null ? '—' : Number(v).toFixed(1) + '%';
const when = (s, dateOnly) => !s ? '—' : (dateOnly ? new Date(s).toLocaleDateString() : new Date(s).toLocaleTimeString());
const sym = { USD: '\$', EUR: '€', GBP: '£' };
const limits = Array.isArray(d.limits) ? d.limits : [];
const byKind = (k) => limits.filter(l => l.kind === k);
const row = (label, value, note) => console.log(label.padEnd(16) + value + (note ? '  ' + note : ''));

console.log('═══ Claude Usage ═══');
if (process.argv[2]) console.log(process.argv[2]);
console.log();

// 5-hour / session window
const session = byKind('session')[0];
if (session || d.five_hour) {
  const s = session || d.five_hour;
  row('5-hour window:', pct(session ? s.percent : s.utilization), '(resets ' + when(s.resets_at) + ')');
}

// 7-day overall
const weekly = byKind('weekly_all')[0];
if (weekly || d.seven_day) {
  const s = weekly || d.seven_day;
  row('7-day window:', pct(weekly ? s.percent : s.utilization), '(resets ' + when(s.resets_at, true) + ')');
}

// Per-model 7-day windows (Fable, Opus, Sonnet, … — whatever the API reports)
const scoped = byKind('weekly_scoped');
for (const s of scoped) {
  const m = s.scope && s.scope.model;
  const name = (m && (m.display_name || m.id)) || (s.scope && s.scope.surface) || 'scoped';
  row('7-day ' + name + ':', pct(s.percent), '(resets ' + when(s.resets_at, true) + ')');
}
// Legacy fallback for the old top-level per-model fields
if (!scoped.length) {
  for (const [k, label] of [['seven_day_opus','Opus'],['seven_day_sonnet','Sonnet']]) {
    if (d[k]) row('7-day ' + label + ':', pct(d[k].utilization));
  }
}

// Extra usage credits — amounts come back in minor units (cents)
const sp = d.spend;
if (sp && sp.enabled && sp.used && sp.limit) {
  const cur = sym[sp.used.currency] || (sp.used.currency + ' ');
  const amt = (m) => cur + (m.amount_minor / Math.pow(10, m.exponent)).toFixed(2);
  row('Extra usage:', pct(sp.percent), '(' + amt(sp.used) + ' / ' + amt(sp.limit) + ')');
} else if (d.extra_usage && d.extra_usage.used_credits != null) {
  const e = d.extra_usage;
  const dp = e.decimal_places == null ? 2 : e.decimal_places;
  const cur = sym[e.currency] || ((e.currency || '') + ' ');
  const amt = (v) => v == null ? '?' : cur + (v / Math.pow(10, dp)).toFixed(2);
  row('Extra usage:', pct(e.utilization), '(' + amt(e.used_credits) + ' / ' + amt(e.monthly_limit) + ')');
}

console.log();
" "$BODY" "$ACCOUNT_LABEL"
