#!/usr/bin/env bash
# Shows a base view as Obsidian renders it: the groups in order, each with its rows in order.
# Usage: bash .claude/scripts/bases_render.sh <base path> <view name> [<embedding note path>]   (Obsidian must be running)
# Needed because `obsidian base:query` ignores sort and groupBy. Headless: builds the base as an embed (Obsidian's own
# bases controller) in an invisible element, so nothing opens, shows or takes focus in the user's Obsidian.
# `this` is the base file, as when the base is open in a tab; with the third argument it is that note, as when the base
# is embedded there — what subtasks.base's views see inside a project.
set -euo pipefail
b=${1//\'/\\\'}; v=${2//\'/\\\'}; n=${3:-}; n=${n//\'/\\\'}
js=$(cat <<'EOF'
(async()=>{const B='__BASE__',V='__VIEW__',N='__NOTE__';const f=app.vault.getFileByPath(B);if(!f)return 'base not found';if(N&&!app.vault.getFileByPath(N))return 'note not found';const host=document.body.createDiv();host.setAttribute('style','position:absolute;left:0;top:0;width:1200px;height:900px;overflow:hidden;opacity:0;visibility:hidden;pointer-events:none;z-index:-1');const e=app.embedRegistry.getEmbedCreator(f)({app,containerEl:host.createDiv(),sourcePath:N||B,linktext:B,depth:0},f,'#'+V);try{e.load();await e.loadFile();const c=e.controller;let d=null;for(let i=0;i<100&&!c.error;i++){await sleep(100);d=!c.initialScan&&c.view&&c.view.data;if(d)break}if(!d)return c.error?'error: '+c.errorEl.textContent:'timed out';const name=x=>(x.file&&x.file.basename)||x.path||'?';return d.groupedData.map(g=>'## '+(g.key?g.key.toString():'(None)')+'\n'+g.entries.map(x=>'- '+name(x)).join('\n')).join('\n')||'(no rows)'}finally{e.unload();host.remove()}})()
EOF
)
js=${js//__BASE__/$b}; js=${js//__VIEW__/$v}; js=${js//__NOTE__/$n}
obsidian eval code="$js" | sed 's/^=> //'
