
var DATA = %(json_name)s;
var INITIAL = %(initial)s;
var POLL_MS = 2000;
var NS = "http" + ":" + "//www.w3.org/2000/svg";
var COLOUR = %(colours)s;
var CHIP = {pending:"var(--crew-tone-review)", ok:"var(--crew-tone-neutral)", err:"var(--crew-tone-blocked)"};
// a tool call still in flight ticks a stopwatch beside its chip, like a live terminal counter
function tickChips(){
  var now = Date.now()/1000;
  document.querySelectorAll('.chip[data-tick]').forEach(function(c){
    var ts = parseFloat(c.dataset.ts || "0");
    if(!ts){ return; }
    var el = now - ts;
    var span = c.querySelector('.tk');
    if(el < 0 || el > 300){ if(span) span.remove(); return; }   // a stale line is not a running call
    if(!span){ span = document.createElement("span"); span.className = "tk"; c.appendChild(span); }
    span.textContent = " " + el.toFixed(1) + "s";
  });
}
var GLYPH = {running:"\u25CF", done:"\u2713", failed:"\u2717", blocked:"\u2717", pending:"\u25CB"};
var CELL_ZOOM = 0.5;   // below this zoom a card collapses to a solid status block
var MAX_CHIPS = 4;
var CW = 250;

var state = INITIAL;
var paused = false;
var selected = null;
var selStep = -1;
var focusRole = null;
var follow = false;
var cam = {k:1, tx:0, ty:0};
var world = {w:400, h:300};
var dom = {};
var fitted = false;

function shortId(s){ s=String(s); return s.length<=14 ? s : s.slice(0,7)+".."+s.slice(-5); }
function fmtTokens(n){ n=+n||0; if(n>=1000000) return (n/1000000).toFixed(1)+"M"; if(n>=1000) return (n/1000).toFixed(1)+"k"; return ""+n; }
function pad(x){ return (x<10?"0":"")+x; }
function fmtTime(sec){ if(sec==null||sec===undefined) return ""; var d=new Date(sec*1000); return pad(d.getHours())+":"+pad(d.getMinutes())+":"+pad(d.getSeconds()); }
function fmtAgo(sec){
  if(!sec) return "";
  var d = Date.now()/1000 - sec; if(d<0) d=0;
  if(d<60) return Math.round(d)+"s ago";
  if(d<3600) return Math.round(d/60)+"m ago";
  if(d<86400) return Math.round(d/3600)+"h ago";
  return Math.round(d/86400)+"d ago";
}
function offLabel(s){ if(s.sec!=null && s.sec!==undefined) return "t+"+s.sec+"s"; return ""; }
function roleDef(name){ var rs=state.roles||[]; for(var i=0;i<rs.length;i++) if(rs[i].name===name) return rs[i]; return null; }
function roleColor(n){ return n.role_color || ((roleDef(n.role)||{}).color) || "var(--crew-tone-neutral)"; }
function nameFor(n){
  if(n.kind==="card") return n.title || n.label;
  if(n.kind==="run") return "run " + n.label;
  if(n.kind==="verifier" && String(n.label).indexOf("verdict")===0) return n.label;
  if(n.kind==="brief") return n.title || "owner brief";
  return n.kind + " " + shortId(n.label);
}
function descFor(n){
  var e = n.evidence || {};
  if(n.kind==="card") return "status " + (n.status||"-") + " - coordinator" +
    (e.writer_role ? " - " + e.writer_role + " did the work" : "") + " - runs " + (e.run_count||0) +
    (e.model_override ? ("\nworker model: " + e.model_override + (e.provider_override ? (" via " + e.provider_override) : "")) : "");
  if(n.kind==="run") return (e.profile||"-") + " - " + (e.outcome||"-") + " - " + (e.duration||"-");
  if(e.verdict) return e.command || "";
  return (e.model||"-") + " - " + (e.duration||"-");
}
function toolsLine(n){
  var c = n.tool_count||0;
  if(n.last_tool) return "tools " + c + " - " + n.last_tool;
  return "tools " + c;
}
function tokensFor(n){
  var e = n.evidence || {};
  if(e.verdict) return "rc=" + e.rc + " - " + (e.duration_s!=null ? e.duration_s + "s" : "");
  var t = (e.output_tokens||0);
  return t ? fmtTokens(t) + " tok" : "";
}

function makeNode(n){
  var col = COLOUR[n.status] || "var(--crew-tone-neutral)";
  var rc = roleColor(n);
  var root = document.createElement("div");
  root.className = "node" + (n.status==="running" ? " alive" : "") + (selected && unitIds(selected)[n.id] ? " sel" : "");
  if(focusRole && n.role!==focusRole) root.classList.add("dim");
  var card = document.createElement("div");
  card.className = "card";
  card.style.borderLeftColor = rc;
  card.addEventListener("click", function(ev){ if(suppressClick) return; ev.stopPropagation(); selectNode(n.id); });
  // the role chip carries the role's symbol, the same one the role strip shows
  var badge = document.createElement("span"); badge.className = "badge"; badge.style.background = rc;
  badge.textContent = roleIcon(n.role) + " " + (n.role || "?");
  card.appendChild(badge);
  var gold = document.createElement("div"); gold.className = "gold";
  // Which card this node belongs to (req: a child card's live node must not read as the page card's
  // own activity): shown whenever it is not the card the page is about.
  gold.textContent = n.layer + " - " + n.kind + ((n.card && n.card !== state.card_id) ? " - card " + n.card : "");
  card.appendChild(gold);
  var hdr = document.createElement("div"); hdr.className = "hdr";
  var gl = document.createElement("span"); gl.className = "glyph"; gl.style.color = col; gl.textContent = GLYPH[n.status] || "\u25CB";
  var nm = document.createElement("span"); nm.className = "name"; nm.textContent = nameFor(n);
  hdr.appendChild(gl); hdr.appendChild(nm); card.appendChild(hdr);
  if(n.kind==="brief"){
    var bf = document.createElement("div"); bf.className = "brieftext";
    ((n.brief && n.brief.text) || "").split(/\n+/).slice(0, 4).forEach(function(ln){
      var le = document.createElement("div"); le.className = "bline"; le.textContent = ln; bf.appendChild(le);
    });
    card.appendChild(bf);
    var src = document.createElement("div"); src.className = "bsrc";
    src.textContent = "source: " + ((n.brief && n.brief.source) || "owner");
    card.appendChild(src);
  } else {
    var d = descFor(n);
    if(d){ var de = document.createElement("div"); de.className = "desc"; de.textContent = d; card.appendChild(de); }
  }
  if(n.kind!=="card" && n.kind!=="run"){
    var tl = document.createElement("div"); tl.className = "tools"; tl.textContent = toolsLine(n); card.appendChild(tl);
  }
  var ft = document.createElement("div"); ft.className = "foot";
  // the node's state as a tinted chip in its own tone (done teal, running green, blocked red, pending grey)
  var sw = document.createElement("span"); sw.className = "sw chip-tone"; sw.style.setProperty("--tone", col); sw.textContent = n.status;
  var tk = document.createElement("span"); tk.className = "tok"; tk.textContent = tokensFor(n);
  ft.appendChild(sw); ft.appendChild(tk); card.appendChild(ft);
  var cm = document.createElement("div"); cm.className = "cellmark"; cm.textContent = (n.role||"?").charAt(0).toUpperCase();
  card.appendChild(cm);
  root.appendChild(card);
  if(n.kind==="brief") root.classList.add("briefcard");
  root._card = card; root._status = col;

  var runs = n.tool_runs || [];
  if(runs.length){
    var chips = document.createElement("div"); chips.className = "chips";
    var total = n.tool_run_total || runs.length;
    var shown = runs.slice(-MAX_CHIPS);
    if(total > shown.length){ var mo = document.createElement("span"); mo.className = "chip more"; mo.textContent = "+" + (total-shown.length) + " more"; chips.appendChild(mo); }
    shown.forEach(function(r, ri){
      var c = document.createElement("span");
      c.className = "chip" + (r.state==="pending" ? "" : " done");
      var cc = CHIP[r.state] || "var(--crew-tone-neutral)";
      c.style.color = cc; c.style.borderColor = cc;
      var mark = r.state === "ok" ? " \u2713" : (r.state === "err" ? " \u2717" : "");
      c.textContent = r.tool + (r.count>1 ? " x" + r.count : "") + mark;
      c.title = r.state + (r.last_ts ? " - " + fmtTime(r.last_ts) : "");
      var live = (n.status === "running" || n.status === "pending" || n.t1 == null);
      if(live && ri === shown.length - 1 && r.last_ts){
        c.dataset.tick = "1"; c.dataset.ts = r.last_ts;      // a call in flight ticks like a stopwatch
      }
      chips.appendChild(c);
    });
    root.appendChild(chips);
  }

  root.appendChild(stepsFor(n, col));
  return root;
}

// The step lines under a card are a terminal window: a new line slides in at the bottom, the
// window holds at most MAX_STEP_LINES, and the oldest one slides out when a newer one arrives.
// The container survives a redraw, so a line animates once, when it first arrives.
var MAX_STEP_LINES = 6;
var stepCache = {};
var curSteps = {};

function stepKey(s){ return (s.tool||"?") + "@" + (s.ts||0) + "|" + String(s.args||"").slice(0,24); }

function stepLine(s, col, nodeId){
  var line = document.createElement("div"); line.className = "step";
  var ic = document.createElement("span"); ic.className = "ic"; ic.textContent = "\u25B8";
  var tn = document.createElement("span"); tn.className = "tn"; tn.style.color = col; tn.textContent = s.tool;
  var off = document.createElement("span"); off.className = "off"; off.textContent = offLabel(s);
  line.appendChild(ic); line.appendChild(tn); line.appendChild(off);
  if(s.args){ var ar = document.createElement("span"); ar.className = "args"; ar.textContent = s.args; line.appendChild(ar); }
  line.dataset.k = stepKey(s);
  line.addEventListener("click", function(ev){
    if(suppressClick) return; ev.stopPropagation();
    var list = curSteps[nodeId] || [];
    for(var i=0;i<list.length;i++){ if(stepKey(list[i])===line.dataset.k){ selectStep(nodeId, i); return; } }
  });
  return line;
}

function liveLines(el){
  return Array.prototype.slice.call(el.children).filter(function(c){ return !c.classList.contains("out"); });
}

function dropStep(el){
  el.classList.add("out");
  setTimeout(function(){ if(el.parentNode) el.parentNode.removeChild(el); }, 300);
}

function stepsFor(n, col){
  // The window carries the last MAX_STEP_LINES steps, never more. A node's list can be longer than
  // that (a failed step rides along its tail), and reconciling against the whole list made an idle
  // node evict and re-add one line on every poll for ever: a settled node's lines slid in and out as
  // if it were still working. The panel holds the full list, failures included.
  var steps = (n.steps || []).slice(-MAX_STEP_LINES);
  curSteps[n.id] = n.steps || [];
  var cache = stepCache[n.id];
  var fresh = false;
  if(!cache || !cache.el){ cache = stepCache[n.id] = {el: document.createElement("div")}; fresh = true; }
  var el = cache.el; el.className = "steps";
  var want = steps.map(stepKey);
  liveLines(el).forEach(function(c){ if(want.indexOf(c.dataset.k) < 0) dropStep(c); });
  steps.forEach(function(s){
    var k = stepKey(s);
    var exists = Array.prototype.slice.call(el.children).some(function(c){ return c.dataset.k === k; });
    if(exists) return;
    var line = stepLine(s, col, n.id);
    if(!fresh){
      line.classList.add("new");
      setTimeout(function(){ line.classList.remove("new"); }, 420);
    }
    el.appendChild(line);
  });
  var live = liveLines(el);
  while(live.length > MAX_STEP_LINES) dropStep(live.shift());
  return el;
}

function svgEl(name, attrs){ var n=document.createElementNS(NS,name); for(var k in attrs) n.setAttribute(k,attrs[k]); return n; }

function drawEdges(edgesEl){
  var defs = svgEl("defs", {});
  [["arrow","ah"],["arrowlive","ah live"]].forEach(function(p){
    var mk = svgEl("marker", {id:p[0], viewBox:"0 0 10 10", refX:"9", refY:"5", markerWidth:"6", markerHeight:"6", orient:"auto-start-reverse"});
    mk.appendChild(svgEl("path", {d:"M0,0 L10,5 L0,10 z", "class":p[1]}));
    defs.appendChild(mk);
  });
  edgesEl.appendChild(defs);
  (state.edges||[]).forEach(function(e){
    var a=dom[e.from], b=dom[e.to];
    if(!a||!b) return;
    var x1=a.x+CW/2, y1=a.y+a.cardH;
    var x2=b.x+CW/2, y2=b.y;
    var dy=(y2-y1); if(dy<0) dy=0;
    var c=dy*0.55;
    var d="M"+x1+" "+y1+" C "+x1+" "+(y1+c)+", "+x2+" "+(y2-c)+", "+x2+" "+y2;
    // edge is green while the child it points at is running, grey otherwise. A running child gets
    // animated dots travelling along the edge, from the parent that handed work over to it.
    var live = b.n.status==="running";
    var cls = "edge" + (live ? " live" : "");
    if(focusRole && (a.n.role!==focusRole && b.n.role!==focusRole)) cls += " dim";
    edgesEl.appendChild(svgEl("path", {d:d, "class":cls, "marker-end":"url(#"+(live?"arrowlive":"arrow")+")"}));
    if(live && !(focusRole && (a.n.role!==focusRole && b.n.role!==focusRole))){
      edgesEl.appendChild(svgEl("path", {d:d, "class":"edge flow"}));
      var dot = svgEl("circle", {r:"2.6", "class":"edge-dot"});
      dot.appendChild(svgEl("animateMotion", {dur:"1.6s", repeatCount:"indefinite", path:d, fill:"freeze"}));
      edgesEl.appendChild(dot);
    }
  });
}

function drawGraph(){
  var nodesEl = document.getElementById("nodes");
  var edgesEl = document.getElementById("edges");
  nodesEl.innerHTML = "";
  edgesEl.innerHTML = "";
  var nodes = state.nodes || [];
  var GX = 40, GY = 70, PADX = 30, PADY = 18;
  var layers = {};
  nodes.forEach(function(n){ (layers[n.layer]=layers[n.layer]||[]).push(n); });
  var maxLayer = 0;
  Object.keys(layers).forEach(function(k){ k=+k; if(k>maxLayer) maxLayer=k; });
  dom = {};
  var y = PADY, totalW = PADX;
  for(var l=0; l<=maxLayer; l++){
    var lyr = (layers[l]||[]).slice().sort(function(a,b){ return (a.x||0)-(b.x||0); });
    if(!lyr.length) continue;
    var x = PADX, items = [];
    lyr.forEach(function(n){
      var elNode = makeNode(n);
      nodesEl.appendChild(elNode);
      items.push({n:n, el:elNode, cardH:elNode._card.offsetHeight || 40, h:elNode.offsetHeight});
    });
    items.forEach(function(it){ it.x = x; x += CW + GX; });
    var maxH = 0;
    items.forEach(function(it){ if(it.h>maxH) maxH=it.h; });
    items.forEach(function(it){
      it.y = y;
      it.el.style.left = it.x + "px";
      it.el.style.top = it.y + "px";
      it.el._card.style.height = it.cardH + "px";
      dom[it.n.id] = it;
    });
    totalW = Math.max(totalW, x - GX + PADX);
    y += maxH + GY;
  }
  world.w = Math.max(totalW, 300);
  world.h = Math.max(y - GY + PADY, 200);
  nodesEl.style.width = world.w + "px";
  nodesEl.style.height = world.h + "px";
  edgesEl.setAttribute("width", world.w);
  edgesEl.setAttribute("height", world.h);
  edgesEl.style.width = world.w + "px";
  edgesEl.style.height = world.h + "px";
  drawEdges(edgesEl);
  tickChips();   // a fresh chip carries its stopwatch from the first frame
  Object.keys(stepCache).forEach(function(id){ if(!dom[id]){ delete stepCache[id]; delete curSteps[id]; } });
}

// ---------------------------------------------------------------- camera
function applyCam(){
  var w = document.getElementById("world");
  w.style.transform = "translate(" + cam.tx + "px," + cam.ty + "px) scale(" + cam.k + ")";
  w.classList.toggle("cells", cam.k < CELL_ZOOM);
  (state.nodes||[]).forEach(function(n){
    var it = dom[n.id]; if(!it) return;
    it.el._card.style.background = cam.k < CELL_ZOOM ? it.el._status : "";
  });
  var st = document.getElementById("stage");
  var g = 24*cam.k;
  st.style.backgroundSize = g + "px " + g + "px";
  st.style.backgroundPosition = cam.tx + "px " + cam.ty + "px";
  document.getElementById("zoomlbl").textContent = Math.round(cam.k*100) + "%" + (cam.k < CELL_ZOOM ? " - cells" : "");
  drawMinimap();
}
function stageSize(){ var st=document.getElementById("stage"); return {w:st.clientWidth, h:st.clientHeight}; }
function fitView(){
  var s = stageSize();
  var k = Math.min(s.w/world.w, s.h/world.h) * 0.92;
  cam.k = Math.max(0.12, Math.min(k, 1.2));
  cam.tx = (s.w - world.w*cam.k)/2;
  cam.ty = Math.max(10, (s.h - world.h*cam.k)/2);
  applyCam();
}
function resetZoom(){ cam.k = 1; cam.tx = 0; cam.ty = 0; applyCam(); }
function centerOn(id){
  var it = dom[id]; if(!it) return;
  var s = stageSize();
  cam.tx = s.w/2 - (it.x + CW/2)*cam.k;
  cam.ty = s.h/2 - (it.y + it.cardH/2)*cam.k;
  applyCam();
}
function followTarget(){
  var best=null, bt=-1, pool=(state.nodes||[]).filter(function(n){ return n.status==="running"; });
  if(!pool.length) pool = state.nodes || [];
  pool.forEach(function(n){ var t=n.last_ts||0; if(t>=bt){ bt=t; best=n; } });
  return best;
}
function doFollow(){ if(!follow) return; var t=followTarget(); if(t) centerOn(t.id); }
function setFollow(v){ follow = v; updateStatus(); doFollow(); }

function drawMinimap(){
  var c = document.getElementById("minimap");
  if(!c || !c.getContext) return;
  var W = c.width, H = c.height, ctx = c.getContext("2d");
  ctx.clearRect(0,0,W,H);
  var sc = Math.min((W-12)/world.w, (H-12)/world.h);
  var ox = (W - world.w*sc)/2, oy = (H - world.h*sc)/2;
  c._map = {sc:sc, ox:ox, oy:oy};
  (state.nodes||[]).forEach(function(n){
    var it = dom[n.id]; if(!it) return;
    ctx.globalAlpha = (focusRole && n.role!==focusRole) ? 0.25 : 1;
    ctx.fillStyle = cssColour(roleColor(n));
    var w = Math.max(4, CW*sc), h = Math.max(3, it.cardH*sc);
    ctx.fillRect(ox + it.x*sc, oy + it.y*sc, w, h);
  });
  ctx.globalAlpha = 1;
  var s = stageSize();
  var vx = -cam.tx/cam.k, vy = -cam.ty/cam.k, vw = s.w/cam.k, vh = s.h/cam.k;
  ctx.strokeStyle = cssColour("var(--crew-text-1)"); ctx.lineWidth = 1;
  ctx.strokeRect(ox + vx*sc + .5, oy + vy*sc + .5, vw*sc, vh*sc);
}

// ---------------------------------------------------------------- roster
var ROLE_ICON = {coordinator:"\u25c6", worker:"\u25b2", content:"\u25cf", verifier:"\u2713"};
function roleIcon(name){ return ROLE_ICON[name] || "\u25aa"; }
function drawRoster(){
  var rail = document.getElementById("roster");
  rail.innerHTML = "";
  var all = document.createElement("div"); all.className = "role all" + (focusRole ? "" : " on");
  var al = document.createElement("div"); al.className = "rl";
  var ai = document.createElement("span"); ai.className = "ricon"; ai.textContent = "\u25a6";
  var an = document.createElement("span"); an.className = "rn"; an.textContent = focusRole ? "\u2190 show all roles" : "all roles";
  al.appendChild(ai);
  var ac = document.createElement("span"); ac.className = "rc"; ac.textContent = (state.node_count||0) + " nodes";
  al.appendChild(an); al.appendChild(ac); all.appendChild(al);
  all.addEventListener("click", function(){ focusRole = null; drawAll(); });
  rail.appendChild(all);
  (state.roles||[]).forEach(function(r){
    var row = document.createElement("div"); row.className = "role" + (focusRole===r.name ? " on" : "");
    var l1 = document.createElement("div"); l1.className = "rl";
    // the role's own symbol is its marker; it pulses while one of the role's nodes is running
    var ic = document.createElement("span"); ic.className = "ricon" + (r.active ? " act" : "");
    ic.style.color = r.color; ic.textContent = roleIcon(r.name);
    var nm = document.createElement("span"); nm.className = "rn"; nm.style.color = r.color; nm.textContent = r.name;
    var cnt = document.createElement("span"); cnt.className = "rc"; cnt.textContent = r.nodes + (r.nodes===1 ? " node" : " nodes");
    l1.appendChild(ic); l1.appendChild(nm); l1.appendChild(cnt);
    row.title = (r.purpose || "") + (r.active ? " - working now" : "");
    row.appendChild(l1);
    row.addEventListener("click", function(){ focusRole = (focusRole===r.name) ? null : r.name; drawAll(); });
    rail.appendChild(row);
  });
}

function liveNode(){
  var out=null;
  (state.nodes||[]).forEach(function(n){ if(n.status==="live"||n.status==="running") out=n; });
  return out;
}
function updateEvent(){
  var el = document.getElementById("event");
  var lastRun=null, lastEnd=-1;
  (state.nodes||[]).forEach(function(n){
    if(n.kind==="run" && (n.t1||0)>lastEnd){ lastEnd=n.t1||0; lastRun=n; }
    if(n.kind==="verifier" && (n.t1||0)>lastEnd){ lastEnd=n.t1||0; lastRun=n; }
  });
  var root=null;
  (state.nodes||[]).forEach(function(n){ if(n.kind==="card") root=n; });
  var rootEv=(root && root.evidence) || {};
  if(rootEv.block_reason){
    el.innerHTML = "<span class='t'>"+esc(fmtTime(root.t1||0))+"</span>"+
      "<span class='t'>coordinator</span><span class='txt'>card "+esc(state.card_status||"blocked")+
      ": "+esc(rootEv.block_reason)+"</span>";
    return;
  }
  var live=liveNode();
  if(live){
    var s=(live.steps||[])[(live.steps||[]).length-1];
    el.innerHTML = "<span class='t'>"+esc(fmtTime(s?s.ts:live.t1))+"</span>"+
      "<span class='t'>"+esc(live.role||"")+"</span><span class='txt'>working now"+
      (s? ": "+esc(s.tool)+(s.args? " "+esc(s.args):"") : "")+"</span>";
    return;
  }
  var best=null, bestTs=-1, bestN=null;
  if(lastRun){ (lastRun.steps||[]).forEach(function(s){
    if(s.ts>=lastEnd-2 && s.ts>bestTs){bestTs=s.ts;best=s;bestN=lastRun;}
  });}
  var st=(state.card_status||"");
  var head = "<span class='t'>"+esc(fmtTime(lastEnd>0?lastEnd:0))+"</span>"+
             "<span class='t'>"+esc(state.card_role||"coordinator")+"</span>";
  if(best){
    el.innerHTML = head+"<span class='txt'>"+esc(bestN.role||"")+" "+esc(best.tool)+
      (best.args? " "+esc(best.args):"")+" - card "+esc(st)+"</span>";
  } else {
    el.innerHTML = head+"<span class='txt'>card "+esc(st)+" - "+esc(state.card_title||"")+"</span>";
  }
}

function getSelectedNode(){
  if(selected){
    for(var i=0;i<(state.nodes||[]).length;i++) if(state.nodes[i].id===selected) return state.nodes[i];
  }
  var best=null, bestTs=-1;
  (state.nodes||[]).forEach(function(n){ (n.steps||[]).forEach(function(s){
    var t=s.ts||0; if(t>bestTs){bestTs=t;best=n;}
  });});
  return best || ((state.nodes&&state.nodes[0])||null);
}

function stepState(s){
  return s.state === "err" ? "err" : (s.state === "pending" ? "pending" : "ok");
}
function stepWord(s){
  return s.state === "err" ? "failed" : (s.state === "pending" ? "still running" : "ok");
}
// The state line of a step: the word, the failure's reason, the last text the step's own output
// produced, and when it happened. The reason and the output are usually the same text (a failure that
// repeats itself, a note capped shorter than the output): the longer one is printed once, never both.
function stepStatus(g){
  var note = g.note || "", out = g.out || "", text = "";
  if(note && out) text = (out.indexOf(note) === 0 || note.indexOf(out) === 0)
    ? (out.length > note.length ? out : note) : note + " - " + out;
  else text = note || out;
  var bits = [stepWord(g)];
  if(text) bits.push(text);
  if(g.ts) bits.push(fmtTime(g.ts));
  return bits.join(" - ");
}
function panelStepKey(s){ return (s.tool||"?") + "@" + (s.ts||0); }
// Parallel calls land in one assistant message: same tool, same second. The panel shows them as one
// box that lists every arg, so a repeated failure - seven identical boxes on the verify node - reads
// once. The box's state is the worst of its calls: a failure is never averaged away.
function groupParallel(steps){
  var out = [];
  (steps||[]).forEach(function(s){
    var k = panelStepKey(s), last = out[out.length-1];
    if(last && last.k===k){
      last.args.push(s.args||""); last.states.push(s.state);
      if(!last.note) last.note = s.note;
      if(s.out) last.out = s.out;
      if(!last.say) last.say = s.say;
    } else {
      out.push({k:k, tool:s.tool, ts:s.ts, sec:s.sec, args:[s.args||""], states:[s.state],
                note:s.note, out:s.out, say:s.say});
    }
  });
  out.forEach(function(g){
    g.state = g.states.indexOf("err")>=0 ? "err" : (g.states.indexOf("pending")>=0 ? "pending" : "ok");
  });
  return out;
}
function tickTime(s){ return s.ts ? fmtTime(s.ts) : offLabel(s); }

function drawScrubber(){
  var bar = document.getElementById("scrubber");
  var sel = getSelectedNode();
  var steps = sel ? (sel.steps||[]) : [];
  bar.innerHTML = "";
  var track = document.createElement("div"); track.className = "track"; bar.appendChild(track);
  if(!steps.length){
    var e = document.createElement("span"); e.className = "tl left"; e.textContent = "no steps"; bar.appendChild(e);
    return;
  }
  var firstLbl = document.createElement("span"); firstLbl.className = "tl left"; firstLbl.textContent = tickTime(steps[0]); bar.appendChild(firstLbl);
  var lastLbl = document.createElement("span"); lastLbl.className = "tl right"; lastLbl.textContent = tickTime(steps[steps.length-1]); bar.appendChild(lastLbl);
  steps.forEach(function(s,i){
    var t = document.createElement("div"); t.className = "tick";
    t.style.left = (steps.length===1 ? 50 : (i/(steps.length-1))*100) + "%";
    var d = document.createElement("div"); d.className = "diam"; t.appendChild(d);
    if(i===selStep) t.classList.add("active");
    if(i===steps.length-1) t.classList.add("playhead");
    t.addEventListener("click", function(){ selectStep(sel.id, i); });
    bar.appendChild(t);
  });
}

// ---------------------------------------------------------------- the step panel (ui-spec section 5)
// One template for every node kind: header - id chips - callout - KPIs - tabs. A run and its session are ONE
// unit (joined on run_id): clicking either opens the same panel and highlights both. Every poll redraws in
// place: a section's markup is only replaced when it changed, and the Transcript and Calls lists are
// reconciled per row (key -> element), so the reader's scroll offset, an in-progress text selection and the
// once-only arrival animation all survive the 2 s poll (owner rules 1-7, crew_panel_steps_proof.py).
var COPYFLASH = {};        // copy id -> until when the button reads "copied" (survives a redraw)
var PANEL_SEEN = {};       // unit key -> {row key: 1}: what the Transcript already showed (animate only new)
var PANEL_EXPAND = {};     // transcript row key -> expanded past its clamp
var PANEL_OPEN = {};       // unit key|call key -> call row unfolded (all folded by default, failed too)
var PANEL_VIEW = {};       // unit key -> "failed" | "latest"
var PANEL_TAB = null;      // tab asked for by the hash, applied once to the node it names
var LATEST_N = 6;
var TAB_SETS = {step: ["Transcript", "Calls", "Details"], card: ["Contract", "Route", "Details"],
                verifier: ["Proof", "Runs", "Details"], close: ["Result", "Details"], brief: []};
var STATUS_TONE = {running: "running", live: "running", pending: "neutral", done: "done", completed: "done",
                   finished: "done", blocked: "blocked", triage: "blocked", failed: "blocked", crashed: "blocked",
                   timed_out: "blocked", gave_up: "blocked", review: "review", review_requested: "review",
                   ready: "ready", queued: "ready", todo: "neutral", PASS: "running", verified: "running",
                   FAIL: "blocked", unverified: "review", rate_limited: "review"};

function nodeById(id){ var ns = state.nodes || []; for(var i=0;i<ns.length;i++) if(ns[i].id===id) return ns[i]; return null; }
// The unit a node belongs to: {run, session, main} - a run and the session it ran, whichever was clicked.
function unitOf(n){
  if(!n) return null;
  var run = null, sess = null;
  if(n.kind === "run"){
    run = n;
    var rid = (n.evidence||{}).run_id;
    (state.nodes||[]).forEach(function(x){ if(x.kind==="session" && x.run_id!==undefined && x.run_id!==null && x.run_id===rid) sess = x; });
  } else if(n.kind === "session"){
    sess = n;
    if(n.run_id!==undefined && n.run_id!==null) run = nodeById("run:" + n.run_id);
  }
  return {run: run, session: sess, main: n, key: run ? run.id : n.id};
}
function unitIds(id){
  var u = unitOf(nodeById(id)); if(!u) return {};
  var out = {}; out[id] = 1; if(u.run) out[u.run.id] = 1; if(u.session) out[u.session.id] = 1; return out;
}
function panelKind(n){
  if(n.kind==="run" || n.kind==="session" || n.kind==="subagent") return "step";
  if(n.kind==="card" || n.kind==="verifier" || n.kind==="close" || n.kind==="brief") return n.kind;
  return "step";
}
function cap1(s){ s = String(s||""); return s.charAt(0).toUpperCase() + s.slice(1); }
function hhmm(ts){ return ts ? fmtTime(ts).slice(0,5) : ""; }
function dayTime(ts){ if(!ts) return ""; var d = new Date(ts*1000), m = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return m[d.getMonth()] + " " + d.getDate() + " " + pad(d.getHours()) + ":" + pad(d.getMinutes()); }
function md(s){ return esc(s).replace(/`([^`\n]+)`/g, "<code>$1</code>"); }
function toneVar(word){ return "var(--crew-tone-" + (STATUS_TONE[word] || "neutral") + ")"; }
function pillHTML(text, word){
  if(!text) return "";
  return '<span class="pill" style="--tone:' + toneVar(word || text) + '"><i></i>' + esc(text) + '</span>';
}
function avatarHTML(role, big){
  var hue = ((roleDef(role)||{}).color) || "var(--crew-tone-neutral)";
  return '<span class="avatar' + (big ? " lg" : "") + '" style="--hue:' + hue + '">' + esc(cap1(role||"?").slice(0,1)) + '</span>';
}
// An id chip IS the copy button; the payload is verbatim "key: value" (owner rule 4).
function idChip(key, label, value, copyId){
  var shown = value || "none";
  var flash = COPYFLASH[copyId] && COPYFLASH[copyId] > Date.now();
  return '<button type="button" class="idc" id="' + copyId + '" data-k="' + esc(key) + '" data-v="' + esc(value||"") +
    '" title="copy ' + esc(key) + '" aria-label="copy ' + esc(key) + '">' + esc(label) +
    '<b class="idv">' + esc(shown) + '</b><i>' + (flash ? "copied" : "⧉") + '</i></button>';
}
function kpiHTML(items){
  items = items.filter(function(x){ return x; });
  if(!items.length) return "";
  return '<div class="kpis">' + items.map(function(k){
    return '<div class="kpi"><div class="kv">' + k[0] + '</div><div class="kl">' + k[1] + '</div></div>'; }).join("") + '</div>';
}
function calloutHTML(title, body, meta, word, copyId){
  if(!body) return "";
  return '<div class="callout" style="--tone:' + toneVar(word || "blocked") + '"><div class="ct">' + esc(title) +
    (copyId ? '<button type="button" class="copy" id="' + copyId + '" data-copytext="' + esc(body) + '">' +
      ((COPYFLASH[copyId] && COPYFLASH[copyId] > Date.now()) ? "copied" : "copy") + '</button>' : '') +
    '</div><div class="cb">' + md(body) + '</div>' + (meta ? '<div class="cm">' + esc(meta) + '</div>' : '') + '</div>';
}
function kvRow(key, val, sub){
  if(val===null || val===undefined || val==="") return "";
  return '<div class="kvr"><dt>' + esc(key) + '</dt><dd>' + val + (sub ? '<small>' + esc(sub) + '</small>' : '') + '</dd></div>';
}
function rawFields(evs, skip){
  var rows = [];
  evs.forEach(function(ev){ Object.keys(ev||{}).forEach(function(k){
    var v = ev[k];
    if(skip[k] || v===null || v===undefined || v==="" || typeof v === "object") return;
    rows.push(kvRow(k, esc(((/at$/).test(k) || k==="ts") && typeof v === "number" ? fmtTime(v) : String(v))));
    skip[k] = 1; }); });
  return rows.length ? '<details class="raw"><summary>Raw fields</summary><dl>' + rows.join("") + '</dl></details>' : "";
}
function roleAbout(role){
  var rd = roleDef(role) || {};
  if(!rd.purpose && !rd.proof) return "";
  return '<div class="sec"><div class="label">About the ' + esc(role) + ' role</div><div class="prose">' + esc(rd.purpose||"") + '</div>' +
    (rd.proof ? '<div class="prose dimp">Proof: ' + esc(rd.proof) + '</div>' : '') + '</div>';
}
// The model pick behind a run: the newest route/reroute row written before it started.
function modelPick(startedAt){
  var pick = null;
  (state.route||[]).forEach(function(r){ if(r.kind!=="quota_wall" && (!startedAt || (r.ts||0) <= startedAt + 5)) pick = r; });
  return pick;
}

// ---- what each node kind says
function panelModel(n){
  var ev = n.evidence || {}, kind = panelKind(n), u = unitOf(n), m = {kind: kind, tabs: TAB_SETS[kind]};
  var other = (n.card && n.card !== state.card_id) ? n.card : null;
  if(kind === "step"){
    var run = u.run, sess = u.session || (n.kind==="subagent" ? n : null);
    var re = (run||{}).evidence || {}, se = (sess||{}).evidence || {};
    var live = ((sess||run||n).live||{}).state === "pending" || (run||n).status === "running";
    var lv = (sess||run||n).live || {};
    m.role = n.role; m.unit = u;
    m.title = cap1(n.role) + " · " + (run ? "run " + (re.run_id!==undefined ? re.run_id : run.label) : (n.kind==="subagent" ? "subagent" : "session"));
    m.sub = live ? "running " + fmtAgo((run||n).t0 || 0).replace(/ ago$/, "") + (lv.tool ? " · " + lv.tool : "")
                 : (re.profile || se.profile_name || "") + (re.ended_at || (sess||{}).t1 ? " · ended " + hhmm(re.ended_at || sess.t1) : "");
    if(other) m.sub += " · card " + other;
    var outcome = re.outcome || (sess||n).status;
    m.pill = [live ? "Running" : cap1(String(outcome||"").replace(/_/g, " ")), live ? "running" : outcome];
    m.chips = [["model", "model", se.model || ev.model, "panelModCopy"], ["session_id", "session", se.session_id || ev.session_id, "panelSidCopy"],
               ["kanban id", "card", other || state.card_id, "panelCidCopy"]];
    if(run && !live && outcome && outcome !== "completed" && (re.summary || re.error))
      m.callout = ["Why this run stopped", re.summary || re.error, re.summary && re.error ? re.error : "", outcome, "panelWhyCopy"];
    var tin = +se.input_tokens || 0, tout = +se.output_tokens || 0, calls = se.tool_call_count || (sess||n).tool_count || 0;
    var failed = (se.calls_failed !== undefined && se.calls_failed !== null) ? se.calls_failed
               : (sess||n).steps ? (sess||n).steps.filter(function(s){ return s.state==="err"; }).length : 0;
    m.kpis = [[esc(re.duration || se.duration || "-"), "duration"],
              sess ? [fmtTokens(tin + tout), "tokens · " + fmtTokens(tout) + " out"] : null,
              sess ? [String(calls), "tool calls" + (failed ? ' · <span class="bad">' + failed + ' failed</span>' : "")] : null];
    m.src = sess || run || n; m.run = run; m.sess = sess; m.live = live; m.failed = failed; m.calls = calls;
  } else if(kind === "card"){
    m.role = "coordinator";
    m.title = "Coordinator · card"; m.sub = (state.card_title || "") + (ev.run_count ? " · " + ev.run_count + " run" + (ev.run_count===1?"":"s") : "");
    m.pill = [cap1(state.card_status || n.status), state.card_status || n.status];
    m.chips = [["model", "model", ev.model_override ? (ev.provider_override ? ev.provider_override + "/" : "") + ev.model_override : "", "panelModCopy"],
               ["session_id", "session", ev.coordinator || "", "panelSidCopy"], ["kanban id", "card", state.card_id, "panelCidCopy"]];
  } else if(kind === "verifier"){
    m.role = "verifier"; m.title = "Verifier · verdict";
    var runsV = ev.review_runs || [], lastRun = runsV[runsV.length-1] || {};
    m.sub = ev.by ? "by " + ev.by + (ev.ts ? " · " + hhmm(ev.ts) : "") : (runsV.length ? runsV.length + " review run(s)" : "no verdict yet");
    m.pill = [ev.verdict || "unverified", ev.verdict || "unverified"];
    m.chips = [["model", "model", "", "panelModCopy"], ["session_id", "session", lastRun.session_id || "", "panelSidCopy"],
               ["kanban id", "card", state.card_id, "panelCidCopy"]];
    if(ev.verdict === "FAIL") m.callout = ["Verification failed", ev.output_head || "(no output recorded)", ev.command ? "command: " + ev.command : "", "FAIL", "panelWhyCopy"];
    m.kpis = [[ev.rc===null || ev.rc===undefined ? "-" : String(ev.rc), "rc"],
              [ev.duration_s===null || ev.duration_s===undefined ? "-" : ev.duration_s + "s", "duration"],
              [String(ev.verdict_count || 0), "verdict lines"]];
  } else if(kind === "close"){
    m.role = "coordinator"; m.title = "Coordinator · close";
    m.sub = ev.completed_at ? "completed " + dayTime(ev.completed_at) : "not closed";
    m.pill = [cap1(ev.status || n.status), ev.status || n.status];
    m.chips = [["model", "model", "", "panelModCopy"], ["session_id", "session", "", "panelSidCopy"], ["kanban id", "card", state.card_id, "panelCidCopy"]];
  } else if(kind === "brief"){
    m.role = n.role || "owner"; m.title = "Owner brief"; m.sub = ev.source ? "from " + ev.source : "";
    m.chips = [["kanban id", "card", state.card_id, "panelCidCopy"]];
  }
  if(!m.kpis) m.kpis = [];
  return m;
}

// ---- tab bodies: [{key, html, cls}] rows for the reconciled lists, or one html string
function transcriptRows(m){
  var src = m.src || {}, lines = (src.text || []).slice().reverse(), live = m.live;
  if(!lines.length) return [];
  return lines.map(function(l, i){
    var key = String(l.ts || "") + "|" + String(l.text || "").slice(0, 80);
    var ex = PANEL_EXPAND[key];
    return {key: key, cls: "msg" + (i===0 ? " first" : "") + (ex ? " ex" : ""),
            html: '<time>' + (i===0 && live ? '<i class="livedot"></i>' : '') + esc(l.ts ? fmtTime(l.ts) : "") + '</time><p>' + md(l.text) + '</p>'};
  });
}
function callGroups(m){
  var steps = (m.src || {}).steps || [];
  var view = PANEL_VIEW[m.unit.key] || (m.failed > 0 ? "failed" : "latest");
  var picked = view === "failed" ? steps.filter(function(s){ return s.state==="err"; }) : steps.slice(-LATEST_N);
  return {view: view, groups: groupParallel(picked).reverse(), steps: steps};
}
function callRows(m, cg){
  return cg.groups.map(function(g){
    var key = g.k + "|" + (g.args[0]||"").slice(0,24), open = !!PANEL_OPEN[m.unit.key + "|" + key];
    var icon = g.state==="err" ? '<span class="st bad">✕</span>' : (g.state==="pending" ? '<span class="st warn">●</span>' : '<span class="st ok">✓</span>');
    var prev = (g.state==="err" && (g.note||g.out)) ? (g.note||g.out) : (g.args[0]||"");
    var html = icon + '<span class="tn">' + esc(g.tool) + (g.args.length>1 ? " ×" + g.args.length : "") + '</span>' +
      '<span class="ar">' + esc(prev) + '</span><span class="of">' + esc(offLabel(g)) + '</span>';
    if(open){
      html += '<div class="ex">' + g.args.filter(function(a){ return a; }).map(function(a){ return '<div class="ea">' + esc(a) + '</div>'; }).join("") +
        '<div class="eo' + (g.state==="err" ? " er" : "") + '">' + esc(stepStatus(g)) + '</div></div>';
    }
    return {key: key, cls: "call" + (open ? " open" : "") + (g.state==="err" ? " failed" : ""), html: html};
  });
}
function callsHead(m, cg){
  var total = m.calls || cg.steps.length, loaded = cg.steps.length;
  var nf = m.failed || 0, latest = Math.min(LATEST_N, loaded);
  var chips = {}; ((m.src||{}).tool_runs || []).forEach(function(t){ chips[t.tool] = (chips[t.tool]||0) + t.count; });
  var hint = cg.view === "failed" ? nf + " failed of " + total + " calls" + (nf > cg.steps.filter(function(s){return s.state==="err";}).length ? " (older failures not loaded)" : "")
                                  : "latest " + latest + " of " + total + " calls";
  var notLoaded = Math.max(0, total - loaded);
  return '<div class="calltools"><div class="seg cbfilter" role="tablist">' +
      '<b class="' + (cg.view==="failed" ? "on" : "") + '" data-view="failed">Failed<span>' + nf + '</span></b>' +
      '<b class="' + (cg.view==="latest" ? "on" : "") + '" data-view="latest">Latest<span>' + latest + '</span></b></div>' +
      '<span class="hint">' + esc(hint) + '</span></div>' +
    (Object.keys(chips).length ? '<div class="chips">' + Object.keys(chips).map(function(t){ return '<span class="chip">' + esc(t) + '<b>' + chips[t] + '</b></span>'; }).join("") + '</div>' : '') +
    (notLoaded ? '<div class="nl">' + notLoaded + ' earlier ok call' + (notLoaded===1?"":"s") + ' not loaded</div>' : '');
}
function detailsStep(m){
  var re = (m.run||{}).evidence || {}, se = (m.sess||{}).evidence || {}, pick = modelPick(re.started_at || (m.src||{}).t0);
  var skip = {model:1, session_id:1, run_id:1, profile:1, profile_name:1, started_at:1, ended_at:1, duration:1, input_tokens:1,
              output_tokens:1, message_count:1, tool_call_count:1, calls_failed:1, summary:1, error:1, outcome:1};
  return '<dl>' +
    kvRow("Model pick", pick ? esc(pick.why || pick.model) : "", pick ? "routed " + dayTime(pick.ts) + " · " + (pick.provider||"") + "/" + (pick.model||"") : "") +
    kvRow("Profile", esc(re.profile || se.profile_name || "")) +
    kvRow("Started", esc(fmtTime(re.started_at || (m.src||{}).t0)), (re.ended_at ? "ended " + fmtTime(re.ended_at) : "") + (re.duration ? " · " + re.duration : "")) +
    kvRow("Tokens", m.sess ? esc(fmtTokens(se.input_tokens) + " in · " + fmtTokens(se.output_tokens) + " out") : "", se.message_count ? se.message_count + " messages" : "") +
    kvRow("Prompt", (m.src||{}).prompt ? '<span class="mono">' + esc(m.src.prompt) + '</span>' : "") +
    '</dl>' + roleAbout(m.role) + rawFields([re, se], skip);
}
function routeHTML(){
  var rows = state.route || [];
  if(!rows.length) return '<div class="empty">No model was routed for this card: its runs used the role profile\'s own model.</div>';
  return '<div class="route">' + rows.map(function(r){
    var wall = r.kind === "quota_wall";
    var what = wall ? "quota wall" + (r.wall_number ? " #" + r.wall_number : "") + " on " + (r.model||"?") + " - " + (r.why||"")
                    : (r.kind === "reroute" ? "re-routed to " : "picked ") + (r.provider ? r.provider + "/" : "") + (r.model||"?") + (r.why ? " - " + r.why : "");
    return '<div class="rr"><time>' + esc(dayTime(r.ts)) + '</time><span class="' + (wall ? "bad" : "") + '">' + esc(what) + '</span></div>'; }).join("") + '</div>';
}
function tabBody(n, m, tab){
  var ev = n.evidence || {};
  if(m.kind === "card"){
    if(tab === "Contract") return '<dl>' + kvRow("Done when", md(ev.done_when||"")) +
      kvRow("Writer", esc((ev.writer_role||"") + (ev.assignee ? " · " + ev.assignee : ""))) + kvRow("Verifier", esc(ev.verifier||"")) +
      kvRow("Model pin", esc(ev.model_override ? (ev.provider_override ? ev.provider_override + "/" : "") + ev.model_override : "none - the role profile's model")) +
      kvRow("Budget", ev.ceiling ? esc(fmtTokens(ev.spent) + " of " + fmtTokens(ev.ceiling) + " tokens") : "") +
      kvRow("Result", ev.result ? md(ev.result) : "") + '</dl>';
    if(tab === "Route") return routeHTML();
    var dec = (ev.decisions || []).map(function(d){ return '<div class="rr"><time>' + esc(dayTime(d.ts)) + '</time><span>' + esc(d.label || d.decision || "") + '</span></div>'; }).join("");
    return (dec ? '<div class="sec"><div class="label">Coordinator decisions</div><div class="route">' + dec + '</div></div>' : '') +
      roleAbout("coordinator") + rawFields([ev], {done_when:1, writer_role:1, assignee:1, verifier:1, model_override:1, provider_override:1, ceiling:1, spent:1, result:1, block_reason:1, status:1, decisions:1});
  }
  if(m.kind === "verifier"){
    if(tab === "Proof") return '<dl>' + kvRow("Done when", md(ev.done_when||"")) + kvRow("Command", ev.command ? '<span class="mono">' + esc(ev.command) + '</span>' : "") +
      kvRow("Verdict", esc(ev.verdict||"unverified"), ev.by ? "by " + ev.by + (ev.ts ? " · " + dayTime(ev.ts) : "") : "") + '</dl>' +
      (ev.output_head ? '<div class="sec"><div class="label">Output</div><div class="cmd">' + esc(ev.output_head) + '</div></div>' : '');
    if(tab === "Runs"){
      var rs = ev.review_runs || [];
      return rs.length ? '<div class="route">' + rs.map(function(r){ return '<div class="rr"><time>run ' + esc(r.run_id) + '</time><span>' +
        esc((r.profile||"") + " · " + (r.outcome||"-") + " · " + (r.duration||"-") + (r.summary ? " - " + r.summary : "")) + '</span></div>'; }).join("") + '</div>'
        : '<div class="empty">No review run: the proof was run without a verifier session.</div>';
    }
    return roleAbout("verifier") + rawFields([ev], {done_when:1, command:1, verdict:1, by:1, ts:1, output_head:1, rc:1, duration_s:1, verdict_count:1, review_runs:1});
  }
  if(m.kind === "close"){
    if(tab === "Result") return '<dl>' + kvRow("Status", esc(ev.status||"")) + kvRow("Completed", esc(dayTime(ev.completed_at))) + '</dl>' +
      (ev.result ? '<div class="prose">' + md(ev.result) + '</div>' : '<div class="empty">No result recorded yet.</div>');
    return rawFields([ev], {status:1, completed_at:1, result:1});
  }
  if(m.kind === "brief") return '<div class="prose">' + md(ev.text || ev.brief || n.brief || "") + '</div>' +
    (ev.source || ev.by ? '<div class="cm">' + esc([ev.source, ev.by, ev.origin].filter(function(x){ return x; }).join(" · ")) + '</div>' : '');
  if(tab === "Details") return detailsStep(m);
  return null;       // Transcript and Calls are reconciled lists
}

// ---- in-place drawing helpers
function setHTML(el, html){ if(el.__h !== html){ el.innerHTML = html; el.__h = html; } }
// Keyed list reconcile: an element is reused for the same key, patched only when its markup changed, and
// moved only when it is out of place (a move drops a selection inside it). Returns the keys that are new.
function reconcile(box, items){
  var have = {}, added = [];
  [].slice.call(box.children).forEach(function(el){ if(el.dataset && el.dataset.key !== undefined) have[el.dataset.key] = el; });
  var ref = box.firstChild;
  items.forEach(function(it){
    var el = have[it.key];
    if(el){ delete have[it.key]; if(el.__h !== it.html){ el.innerHTML = it.html; el.__h = it.html; } }
    else { el = document.createElement("div"); el.dataset.key = it.key; el.innerHTML = it.html; el.__h = it.html; added.push(it.key); }
    var keep = el.classList.contains("new");
    el.className = it.cls + (keep ? " new" : "");
    if(el === ref){ ref = ref.nextSibling; return; }
    box.insertBefore(el, ref);
  });
  Object.keys(have).forEach(function(k){ if(have[k].parentNode) have[k].parentNode.removeChild(have[k]); });
  return added;
}
function panelSkeleton(p){
  if(p.querySelector(".phead")) return;
  p.innerHTML = '<div class="phead"><div class="pnav"></div><div class="pid"></div><div class="ids"></div><div class="pcall"></div><div class="pkpi"></div></div>' +
    '<div class="ptabs"></div><div class="pbody"><div class="ptop"></div><div class="plist"></div><div class="pdoc"></div></div>';
  p.addEventListener("click", panelClick);
}
function currentTab(n, m){
  if(!m.tabs.length) return null;
  if(PANEL_TAB && PANEL_TAB.node === n.id){ var t = PANEL_TAB.tab; PANEL_TAB = null;
    for(var i=0;i<m.tabs.length;i++) if(m.tabs[i].toLowerCase() === String(t).toLowerCase()){ storeTab(m.kind, m.tabs[i]); return m.tabs[i]; } }
  var want = null; try{ want = localStorage.getItem("crewTab." + m.kind); }catch(e){}
  return m.tabs.indexOf(want) >= 0 ? want : m.tabs[0];
}
function storeTab(kind, tab){ try{ localStorage.setItem("crewTab." + kind, tab); }catch(e){} }
function writeHash(n, tab){
  var parts = [];
  (location.hash||"").replace(/^#/, "").split("&").forEach(function(kv){ if(kv && !/^(node|tab)=/.test(kv)) parts.push(kv); });
  if(n) parts.push("node=" + encodeURIComponent(n.id));
  if(n && tab) parts.push("tab=" + tab.toLowerCase());
  var h = parts.length ? "#" + parts.join("&") : "";
  if(h !== location.hash){ try{ history.replaceState(null, "", location.pathname + location.search + h); }catch(e){} }
}

function updatePanel(){
  var p = document.getElementById("panel");
  if(!p || !p.classList.contains("open")) return;
  var n = getSelectedNode();
  if(!n) return;
  // The selection and the body's scroll are read before and put back after: a patched section never
  // steals either (owner rule 6).
  var selRange = null;
  try { selRange = document.getSelection().toString() ? document.getSelection().getRangeAt(0).cloneRange() : null; } catch(e){}
  panelSkeleton(p);
  var body = p.querySelector(".pbody"), scrollTop = body.scrollTop;
  var m = panelModel(n), tab = currentTab(n, m), ukey = (m.unit && m.unit.key) || n.id;
  if(p._pnode !== ukey){ scrollTop = 0; }
  // header
  setHTML(p.querySelector(".pnav"), (n.kind === "card" ? '<span>Card</span>' : '<button type="button" class="navback" data-node="card:' + esc(state.card_id) + '">‹ Card</button>') +
    '<span class="dim">/</span><span>' + esc(m.role || n.kind) + '</span><button type="button" class="x" title="close (esc)">✕</button>');
  setHTML(p.querySelector(".pid"), avatarHTML(m.role, true) + '<div class="pidt"><div class="pt">' + esc(m.title) + '</div>' +
    (m.sub ? '<div class="ps">' + esc(m.sub) + '</div>' : '') + '</div>' + (m.pill ? pillHTML(m.pill[0], m.pill[1]) : ''));
  setHTML(p.querySelector(".ids"), (m.chips||[]).map(function(c){ return idChip(c[0], c[1], c[2], c[3]); }).join(""));
  setHTML(p.querySelector(".pcall"), m.callout ? calloutHTML(m.callout[0], m.callout[1], m.callout[2], m.callout[3], m.callout[4]) : "");
  setHTML(p.querySelector(".pkpi"), kpiHTML(m.kpis));
  var tabsHTML = m.tabs.length ? '<div class="seg" role="tablist">' + m.tabs.map(function(t){
      var cnt = t === "Calls" ? '<span>' + (m.calls||0) + '</span>' : (t === "Route" ? '<span>' + (state.route||[]).length + '</span>' : '');
      return '<b class="' + (t===tab ? "on" : "") + '" data-tab="' + t + '">' + t + cnt + '</b>'; }).join("") + '</div>' +
      (tab === "Transcript" ? '<span class="hint">newest first</span>' : '') : '';
  setHTML(p.querySelector(".ptabs"), tabsHTML);
  p.querySelector(".ptabs").hidden = !m.tabs.length;
  // body
  var top = p.querySelector(".ptop"), list = p.querySelector(".plist"), doc = p.querySelector(".pdoc");
  var html = tabBody(n, m, tab);
  if(html !== null){
    setHTML(top, ""); list.className = "plist"; reconcile(list, []); setHTML(doc, html);
  } else if(tab === "Transcript"){
    setHTML(top, ""); setHTML(doc, "");
    var rows = transcriptRows(m);
    list.className = "plist transcript";
    var added = reconcile(list, rows);
    var seen = PANEL_SEEN[ukey];
    if(!rows.length){ setHTML(doc, '<div class="empty">No text yet, this run has only made tool calls.</div>'); }
    // a line animates once: only one that arrives after this unit was first drawn, never on the first paint
    if(seen){
      added.forEach(function(k){ if(!seen[k]){ var el = list.querySelector('[data-key="' + CSS.escape(k) + '"]'); if(el) el.classList.add("new"); } });
      if(added.length) setTimeout(function(){ [].slice.call(list.querySelectorAll(".new")).forEach(function(e){ e.classList.remove("new"); }); }, 420);
    }
    seen = PANEL_SEEN[ukey] = seen || {};
    rows.forEach(function(r){ seen[r.key] = 1; });
  } else {
    setHTML(doc, "");
    var cg = callGroups(m);
    setHTML(top, callsHead(m, cg));
    list.className = "plist calls";
    reconcile(list, callRows(m, cg));
    if(!cg.steps.length) setHTML(doc, '<div class="empty">No tool call recorded for this run.</div>');
    else if(!cg.groups.length) setHTML(doc, '<div class="empty">' + (cg.view === "failed" ? "No failed call." : "No call.") + '</div>');
  }
  if(p._pnode !== ukey || p._ptab !== tab){ writeHash(n, tab); }
  p._pnode = ukey; p._ptab = tab;
  body.scrollTop = scrollTop;
  try { if(selRange){ var sel = document.getSelection(); sel.removeAllRanges(); sel.addRange(selRange); } } catch(e){}
}

function flashCopy(btn, text){
  copyText(text, function(ok){
    COPYFLASH[btn.id] = Date.now() + 1600;
    var slot = btn.querySelector("i") || btn;
    slot.textContent = ok ? "copied" : "select + copy";
    setTimeout(function(){ updatePanel(); }, 1700);
  });
}
function panelClick(e){
  var t = e.target, p = document.getElementById("panel");
  var chip = t.closest(".idc");
  if(chip){ e.stopPropagation(); flashCopy(chip, chip.getAttribute("data-k") + ": " + chip.getAttribute("data-v")); return; }
  var cp = t.closest(".copy[data-copytext]");
  if(cp){ e.stopPropagation(); copyText(cp.getAttribute("data-copytext"), function(ok){ COPYFLASH[cp.id] = Date.now() + 1600;
    cp.textContent = ok ? "copied" : "select + copy"; setTimeout(updatePanel, 1700); }); return; }
  if(t.closest(".x")){ closePanel(); return; }
  var back = t.closest(".navback");
  if(back){ selectNode(back.getAttribute("data-node")); return; }
  var n = getSelectedNode(); if(!n) return;
  var m = panelModel(n), ukey = (m.unit && m.unit.key) || n.id;
  var tb = t.closest(".ptabs [data-tab]");
  if(tb){ storeTab(m.kind, tb.getAttribute("data-tab")); p.querySelector(".pbody").scrollTop = 0; updatePanel(); return; }
  var vw = t.closest(".cbfilter [data-view]");
  if(vw){ PANEL_VIEW[ukey] = vw.getAttribute("data-view"); updatePanel(); return; }
  if(String(document.getSelection() || "")) return;         // a click that ends a selection does not fold/unfold
  var call = t.closest(".plist.calls > .call");
  if(call && !t.closest(".ex")){ var k = ukey + "|" + call.dataset.key; PANEL_OPEN[k] = !PANEL_OPEN[k]; updatePanel(); return; }
  var msg = t.closest(".plist.transcript > .msg");
  if(msg){ PANEL_EXPAND[msg.dataset.key] = !PANEL_EXPAND[msg.dataset.key]; updatePanel(); }
}

function updateStatus(){
  document.getElementById("cardtitle").textContent = state.card_title || state.card_id || "";
  document.getElementById("counts").textContent = (state.node_count||0) + " nodes - " + (state.edge_count||0) + " edges";
  var act = (state.roles||[]).filter(function(r){ return r.active; }).map(function(r){ return r.name; });
  document.getElementById("ractive").textContent = "roles active: " + (act.length ? act.join(", ") : "none");
  var live = document.getElementById("live");
  live.textContent = paused ? "PAUSED" : "LIVE";
  live.className = "live" + (paused ? " paused" : "");
  var fb = document.getElementById("followbtn");
  fb.textContent = "follow " + (follow ? "on" : "off");
  fb.className = "pill btn" + (follow ? " on" : "");
}

// A card's own fields, one labelled row each. The two values the owner takes off the page carry a
// copy button, and the flash survives a redraw (the page re-renders on every poll).
function sitFieldRow(box, label, value, copy){
  if(value === null || value === undefined || value === "") return;
  var r = document.createElement("span"); r.className = "fp";
  var k = document.createElement("span"); k.className = "fk"; k.textContent = label;
  var v = document.createElement("span"); v.className = "fv"; v.textContent = value;
  v.title = value;
  r.appendChild(k); r.appendChild(v);
  if(copy){
    var b = document.createElement("button");
    b.type = "button"; b.className = "copy"; b.id = copy.id;
    b.textContent = (COPYFLASH[copy.id] && COPYFLASH[copy.id] > Date.now()) ? "copied" : "copy";
    b.title = copy.title; b.setAttribute("aria-label", copy.title);
    b.addEventListener("click", function(e){
      e.stopPropagation();
      copyText(copy.value, function(ok){
        COPYFLASH[copy.id] = Date.now() + 1600;
        b.textContent = ok ? "copied" : "select + copy";
        setTimeout(function(){ b.textContent = "copy"; }, 1600);
      });
    });
    r.appendChild(b);
  }
  box.appendChild(r);
}
function renderSitFields(){
  var box = document.getElementById("sitfields");
  if(!box) return;
  box.innerHTML = "";
  // Only what the box does not already say above (the chips), and not what the rail carries: the
  // status, the run breakdown and the counters stay chips; the tokens stay in the rail; the role,
  // who and the verifier are the graph's own labels, so the box does not repeat them. Four pairs on
  // one line, not four rows: the box is the top of the page and the graph wants the height.
  sitFieldRow(box, "model", state.card_model || "");
  // fmtAge takes an AGE in seconds, not a timestamp: created_at straight in reads as 20000 days.
  if(state.card_created_at)
    sitFieldRow(box, "started", fmtAge(Date.now() / 1000 - state.card_created_at));
  sitFieldRow(box, "kanban id", state.card_id || "",
    {id: "cardIdCopy", value: state.card_id || "", title: "copy the kanban id"});
  sitFieldRow(box, "coordinator", state.coordinator || "",
    {id: "cardCoCopy", value: state.coordinator || "", title: "copy the coordinator session"});
}
function renderSituation(){
  var s = state.situation || {};
  var el = document.getElementById("sit");
  if(!el) return;
  var bits = [];
  var cls = s.headline && s.headline.indexOf("stopped") === 0 ? "blocked"
          : (s.headline === "finished" ? "done" : (s.headline && s.headline.indexOf("working") === 0 ? "running" : ""));
  // State first, as tinted pills in their tone (the step panel's pill): the card's status, then the headline.
  var st = state.card_status || "-";
  bits.push("<span class='pill sh' style='--tone:" + toneVar(st) + "'><i></i>" + esc(st) + "</span>");
  bits.push("<span class='pill sb " + cls + "' style='--tone:" + toneVar(cls || "pending") + "'>" + esc(s.headline || "-") + "</span>");
  var fp = s.first_pass || {};
  if(fp.rounds) bits.push("<span class='pill sb " + (fp.first_pass ? "done" : "blocked") + "' style='--tone:" +
    toneVar(fp.first_pass ? "PASS" : "FAIL") + "'>" + (fp.first_pass ? "passed first try" : (fp.fails||0) + " fail(s) before pass") + "</span>");
  var un = s.units || {};
  if(un.total) bits.push("<span class='pill sd' style='--tone:" + toneVar(un.passed >= un.total ? "PASS" : "pending") + "'>units " +
    (un.passed||0) + " of " + un.total + " passed</span>");
  if((s.children||[]).length) bits.push("<span class='pill sd' style='--tone:" + toneVar("pending") + "'>children " + (s.children||[]).length + "</span>");
  // The runs as a key-number grid (the panel's KPI row); a count above zero takes its state's tone.
  // The id, the tokens and the card's other facts live in the field chips below (or in the rail).
  var c = s.counts || {};
  function kpi(v, label, word){ return "<div class='kpi'><div class='kv" + (v && word ? " on" : "") + "' style='--tone:" +
    toneVar(word || "pending") + "'>" + (v||0) + "</div><div class='kl'>" + label + "</div></div>"; }
  bits.push("<div class='sitkpis' title='" + (s.runs||0) + " runs: " + (c.done||0) + " done, " + (c.blocked||0) + " blocked, " +
    (c.failed||0) + " failed, " + (c.running||0) + " running'>" + kpi(s.runs, "runs", "") + kpi(c.done, "done", "done") +
    kpi(c.blocked, "blocked", "blocked") + kpi(c.failed, "failed", "failed") + kpi(c.running, "running", "running") + "</div>");
  var html = bits.join("");
  (s.done||[]).slice(0,2).forEach(function(d){
    html += "<div class='sd sdone' title='" + esc(d) + "'><b>done</b><span>" + esc(d) + "</span></div>";
  });
  el.innerHTML = html;
  renderSitFields();
  renderSitBox(s, cls);
  renderSpinBox(s);
}
function renderSpinBox(s){
  var box = document.getElementById("spinbox");
  if(!box) return;
  var text = s.repeat_text || "";
  var none = document.getElementById("spinboxNone");
  // The whole cell goes with it: a card that is not looping has nothing for the third column, and
  // leaving it standing took a third of the width from the two boxes that do have something to say.
  var cell = document.getElementById("topSpin");
  var area = document.getElementById("toparea");
  var quiet = !s.repeat || !text;
  if(cell) cell.hidden = quiet;
  if(area) area.classList.toggle("two", quiet);
  if(quiet){ box.hidden = true; if(none) none.hidden = false; return; }
  if(none) none.hidden = true;
  var stops = s.repeat_stops || 0;
  document.getElementById("spinboxCount").textContent =
    stops + " of " + (s.runs || 0) + " runs stopped on the same reason";
  var body = document.getElementById("spinboxText");
  if(body.textContent !== text) body.textContent = text;
  box.hidden = false;
}
function sitCopyClick(e){
  if(e) e.stopPropagation();
  var btn = document.getElementById("sitCopy");
  var reason = document.getElementById("sitboxWhy").textContent || "";
  var card = (document.body && document.body.dataset ? document.body.dataset.card : "") || "";
  // the identifier rides along with the copy so the card can be found at once; the box still shows
  // the reason alone
  var text = (card ? card + "\n\n" : "") + reason;
  copyText(text, function(ok){ btn.textContent = ok ? "copied" : "select + copy";
    setTimeout(function(){ btn.textContent = "copy"; }, 1600); });
}
function spinCopyClick(e){
  if(e) e.stopPropagation();
  var btn = document.getElementById("spinCopy");
  var text = document.getElementById("spinboxText").textContent || "";
  copyText(text, function(ok){ btn.textContent = ok ? "copied" : "select + copy";
    setTimeout(function(){ btn.textContent = "copy"; }, 1600); });
}
function fmtAge(sec){
  if(sec === null || sec === undefined || sec === "") return "age unknown";
  sec = Math.max(0, Math.round(+sec||0));
  if(sec < 60) return sec + "s ago";
  if(sec < 3600) return Math.floor(sec/60) + "m " + (sec%60) + "s ago";
  if(sec < 86400) return Math.floor(sec/3600) + "h " + Math.floor((sec%3600)/60) + "m ago";
  return Math.floor(sec/86400) + "d " + Math.floor((sec%86400)/3600) + "h ago";
}
function renderSitBox(s, cls){
  var box = document.getElementById("sitbox");
  if(!box) return;
  var reason = s.reason || s.why || "";
  var none = document.getElementById("sitboxNone");
  if(!reason){ box.hidden = true; if(none) none.hidden = false; return; }
  if(none) none.hidden = true;
  var you = (s.reason_actor || (s.reason ? "nobody" : "")) === "you" || cls === "blocked";
  box.className = you ? "you" : "nobody";
  var head = document.getElementById("sitboxHead");
  head.querySelector(".sbl").textContent = you ? "needs you" : "waiting - nobody has to act";
  var badge = head.querySelector(".sb");
  badge.className = "sb " + (cls || "");
  badge.textContent = (state.card_status || "-") + (s.headline ? " - " + s.headline : "");
  document.getElementById("sitboxWhy").textContent = reason;
  document.getElementById("sitboxMeta").textContent = "source: " + (s.reason_source || "task") +
    " - recorded " + fmtAge(s.reason_age_s) +
    (s.reason_age_s !== null && s.reason_age_s !== undefined ? " (" + s.reason_age_s + "s)" : "");
  box.hidden = false;
}
function fmtExact(n){ n=Math.round(+n||0); return n.toLocaleString("en-US"); }
function drawTokens(){
  var t = state.tokens || {};
  var ceil = +t.ceiling||0, used = +t.used||0;
  var pct = ceil ? Math.round(1000*used/ceil)/10 : 0;
  var vals = {tokCeiling: fmtExact(ceil), tokUsed: fmtExact(used), tokRaw: fmtExact(t.raw_total),
              tokCalls: fmtExact(t.calls), tokPct: pct.toFixed(1) + "%"};
  Object.keys(vals).forEach(function(id){
    var row = document.getElementById(id); if(!row) return;
    var v = row.querySelector(".tv"); if(v) v.textContent = vals[id];
  });
  var pv = document.querySelector("#tokPct .tv");
  if(pv) pv.style.color = ceil ? budgetTone(pct) : "";
}
// The share of the ceiling as a colour that slides green -> yellow -> red: green up to half, yellow by 80 %,
// red from 100 % (the board card's own budget thresholds), mixed from the tone tokens in between.
function budgetTone(pct){
  var G = "var(--crew-tone-running)", Y = "var(--crew-tone-review)", R = "var(--crew-tone-blocked)";
  if(pct >= 100) return R;
  if(pct >= 80) return "color-mix(in srgb, " + R + " " + Math.round((pct-80)/20*100) + "%, " + Y + ")";
  if(pct >= 50) return "color-mix(in srgb, " + Y + " " + Math.round((pct-50)/30*100) + "%, " + G + ")";
  return G;
}
function drawAll(){
  drawGraph();
  drawTokens();
  drawRoster();
  updateEvent();
  drawScrubber();
  updateStatus();
  updatePanel();
  // The panel is a docked column: opening or closing it resizes the stage, so the graph re-fits once on
  // every change of that state - whichever path changed it (a click, the hash, esc, the canvas).
  var po = document.getElementById("panel").classList.contains("open");
  if(po !== FIT_PANEL_OPEN){ FIT_PANEL_OPEN = po; fitted = false; }
  if(!fitted){ fitted = true; fitView(); } else { applyCam(); }
  doFollow();
}

var FIT_PANEL_OPEN = null;
function openPanel(){ document.getElementById("panel").classList.add("open"); }
function selectNode(id){
  selected = id; selStep = -1;
  openPanel();
  drawAll();
}

function selectStep(id, i){
  selected = id; selStep = i;
  openPanel();
  drawAll();
}

function refresh(){
  if(paused) return;
  try{
    var x = new XMLHttpRequest();
    x.open("GET", DATA, true);
    x.onreadystatechange = function(){
      if(x.readyState===4 && x.status===200 && x.responseText){
        try{
          state = JSON.parse(x.responseText);
          renderSituation();
          drawAll();
        }catch(e){}
      }
    };
    x.send(null);
  }catch(e){}
}

// ---------------------------------------------------------------- pan / zoom input
var drag = null, suppressClick = false;
function closePanel(){
  var p = document.getElementById("panel");
  if(p) p.classList.remove("open");
  selected = null;
  writeHash(null, null);
  if(p) p._pnode = null;
  drawAll();
}
function bindInput(){
  var st = document.getElementById("stage");
  // clicking empty canvas closes the panel a node click opened
  st.addEventListener("click", function(e){
    if(suppressClick) return;
    if(selected) closePanel();
  });
  st.addEventListener("wheel", function(e){
    e.preventDefault();
    var r = st.getBoundingClientRect();
    var mx = e.clientX - r.left, my = e.clientY - r.top;
    var k2 = Math.max(0.12, Math.min(2.5, cam.k * Math.exp(-e.deltaY*0.0015)));
    var wx = (mx - cam.tx)/cam.k, wy = (my - cam.ty)/cam.k;
    cam.k = k2; cam.tx = mx - wx*k2; cam.ty = my - wy*k2;
    if(follow){ follow = false; updateStatus(); }
    applyCam();
  }, {passive:false});
  st.addEventListener("mousedown", function(e){
    if(e.button!==0 || e.target.id==="minimap") return;
    drag = {x:e.clientX, y:e.clientY, tx:cam.tx, ty:cam.ty, moved:false};
    suppressClick = false;
  });
  window.addEventListener("mousemove", function(e){
    if(!drag) return;
    var dx = e.clientX-drag.x, dy = e.clientY-drag.y;
    if(!drag.moved && Math.abs(dx)+Math.abs(dy) > 4){ drag.moved = true; st.classList.add("drag"); if(follow){ follow=false; updateStatus(); } }
    if(drag.moved){ cam.tx = drag.tx+dx; cam.ty = drag.ty+dy; applyCam(); }
  });
  window.addEventListener("mouseup", function(){
    if(drag && drag.moved){ suppressClick = true; setTimeout(function(){ suppressClick = false; }, 0); }
    drag = null; st.classList.remove("drag");
  });
  var mm = document.getElementById("minimap");
  mm.addEventListener("click", function(e){
    var m = mm._map; if(!m) return;
    var r = mm.getBoundingClientRect();
    var wx = (e.clientX - r.left - m.ox)/m.sc, wy = (e.clientY - r.top - m.oy)/m.sc;
    var s = stageSize();
    cam.tx = s.w/2 - wx*cam.k; cam.ty = s.h/2 - wy*cam.k;
    if(follow){ follow=false; updateStatus(); }
    applyCam();
  });
  document.getElementById("followbtn").addEventListener("click", function(){ setFollow(!follow); });
  window.addEventListener("resize", applyCam);
}

document.addEventListener("keydown", function(e){
  var tag = (document.activeElement && document.activeElement.tagName) || "";
  if(tag==="INPUT"||tag==="TEXTAREA") return;
  if(e.code==="Space"){ e.preventDefault(); paused=!paused; updateStatus(); }
  else if(e.key==="r"||e.key==="R"){ refresh(); }
  else if(e.key==="?"){ document.getElementById("help").classList.toggle("open"); }
  else if(e.key==="o"||e.key==="O"){ window.location.href = "/"; }
  else if(e.key==="f"){ if(follow){ follow=false; updateStatus(); } fitView(); }
  else if(e.key==="F"){ setFollow(!follow); }
  else if(e.key==="0"){ if(follow){ follow=false; updateStatus(); } resetZoom(); }
  else if(e.key==="Escape"){
    document.getElementById("help").classList.remove("open");
    if(selected){ closePanel(); return; }
    focusRole=null; drawAll();
  }
});

function applyHash(){
  // shareable view state: #role=<name> focuses a role, #node=<id> opens that node's panel, &tab=<name> on it
  var h = (location.hash || "").replace(/^#/, ""), node = null, tab = null;
  h.split("&").forEach(function(kv){
    var i = kv.indexOf("="); if(i < 0) return;
    var k = kv.slice(0, i), v = decodeURIComponent(kv.slice(i + 1));
    if(k === "role") focusRole = v || null;
    if(k === "node" && v) node = v;
    if(k === "tab" && v) tab = v;
  });
  if(node && node !== selected){ selected = node; selStep = -1; openPanel(); }
  if(node && tab) PANEL_TAB = {node: node, tab: tab};
}

function setRail(collapsed){
  var rail = document.getElementById("rail");
  rail.classList.toggle("collapsed", collapsed);
  var arrow = collapsed ? "\u203a" : "\u2039";
  ["railTop","railBot"].forEach(function(id){
    var b = document.getElementById(id);
    if(b){ b.textContent = arrow;
      b.title = collapsed ? "expand the sidebar" : "collapse the sidebar"; }
  });
  var back = document.getElementById("railBack");
  if(back) back.title = "back to the board";
  var back = rail.querySelector("a.railbtn");
  if(back) back.title = "back to the board";
  try{ localStorage.setItem("crewRailCollapsed", collapsed ? "1" : "0"); }catch(e){}
  drawAll();
}
function bindRail(){
  ["railTop","railBot"].forEach(function(id){
    var b = document.getElementById(id);
    if(b) b.addEventListener("click", function(){
      setRail(!document.getElementById("rail").classList.contains("collapsed")); });
  });
  var want = "0";
  try{ want = localStorage.getItem("crewRailCollapsed") || "0"; }catch(e){}
  setRail(want === "1");
}
function boot(){
  if(state && state.situation) renderSituation();
  bindInput();
  bindRail();
  if(/rail=collapsed/.test(location.hash)) setRail(true);
  applyHash();
  drawAll();
  setInterval(refresh, POLL_MS);
  setInterval(drawRoster, 1000);
  setInterval(tickChips, 500);
}
window.addEventListener("hashchange", function(){ applyHash(); drawAll(); });
document.addEventListener("DOMContentLoaded", boot);
