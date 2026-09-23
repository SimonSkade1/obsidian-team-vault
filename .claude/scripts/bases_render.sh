#!/usr/bin/env bash
# Shows a base view as Obsidian renders it: the groups in order, each with its rows in order.
# Usage: bash .claude/scripts/bases_render.sh <base path> <view name> [<embedding note path>]   (Obsidian must be running)
# Needed because `obsidian base:query` ignores sort and groupBy. Opens the view in a temporary tab, closes it again.
# With the third argument the base is rendered as embedded in that note (reading view), so `this` is the note —
# what subtasks.base's views see inside a project. The note must contain `![[<base>]]`.
set -euo pipefail
b=${1//\'/\\\'}; v=${2//\'/\\\'}; n=${3:-}; n=${n//\'/\\\'}
js=$(cat <<'EOF'
(async()=>{const leaf=app.workspace.getLeaf('tab');try{let c=null;if('__NOTE__'){const f=app.vault.getFileByPath('__NOTE__');if(!f)return 'note not found';await leaf.openFile(f,{state:{mode:'preview'}});const find=()=>{const seen=new Set(),q=[[leaf.view,0]];while(q.length){const [o,d]=q.shift();if(!o||typeof o!=='object'||seen.has(o)||d>7||o instanceof Node)continue;seen.add(o);if(o.controller&&o.controller.view&&o.file&&o.file.path==='__BASE__')return o.controller;for(const k of Object.keys(o)){const x=o[k];if(x&&typeof x==='object')q.push([x,d+1])}}return null};for(let i=0;i<40&&!c;i++){await new Promise(r=>setTimeout(r,200));c=find()}if(!c)return 'embedded base not found in the note';c.selectView('__VIEW__');await new Promise(r=>setTimeout(r,1500))}else await leaf.setViewState({type:'bases',state:{file:'__BASE__',viewName:'__VIEW__'}});let d=null;for(let i=0;i<40;i++){await new Promise(r=>setTimeout(r,150));const cc=c||leaf.view.controller;d=cc&&cc.view&&cc.view.data;if(d&&d.data&&d.data.length)break}if(!d)return 'no data (wrong path or view name?)';const name=e=>(e.file&&e.file.basename)||e.path||'?';return d.groupedData.map(g=>'## '+(g.key?g.key.toString():'(None)')+'\n'+g.entries.map(e=>'- '+name(e)).join('\n')).join('\n')}finally{leaf.detach()}})()
EOF
)
js=${js//__BASE__/$b}; js=${js//__VIEW__/$v}; js=${js//__NOTE__/$n}
obsidian eval code="$js" | sed 's/^=> //'
