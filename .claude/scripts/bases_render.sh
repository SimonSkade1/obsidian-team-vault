#!/usr/bin/env bash
# Shows a base view as Obsidian renders it: the groups in order, each with its rows in order.
# Usage: bash .claude/scripts/bases_render.sh <base path> <view name>      (Obsidian must be running)
# Needed because `obsidian base:query` ignores sort and groupBy. Opens the view in a temporary tab, closes it again.
set -euo pipefail
b=${1//\'/\\\'}; v=${2//\'/\\\'}
js=$(cat <<'EOF'
(async()=>{const leaf=app.workspace.getLeaf('tab');try{await leaf.setViewState({type:'bases',state:{file:'__BASE__',viewName:'__VIEW__'}});let d=null;for(let i=0;i<40;i++){await new Promise(r=>setTimeout(r,150));const c=leaf.view.controller;d=c&&c.view&&c.view.data;if(d&&d.data&&d.data.length)break}if(!d)return 'no data (wrong path or view name?)';const name=e=>(e.file&&e.file.basename)||e.path||'?';return d.groupedData.map(g=>'## '+(g.key?g.key.toString():'(None)')+'\n'+g.entries.map(e=>'- '+name(e)).join('\n')).join('\n')}finally{leaf.detach()}})()
EOF
)
js=${js//__BASE__/$b}; js=${js//__VIEW__/$v}
obsidian eval code="$js" | sed 's/^=> //'
