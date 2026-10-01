// The board (ui-spec section 4): one header line with the board's own facts, five lanes in a fixed order,
// the desktop card. Redrawn on every poll; the lanes' scroll offsets and "Show older" survive a redraw and a
// board -> card -> back round trip (sessionStorage).
var TONE = {blocked:"var(--crew-tone-blocked)", triage:"var(--crew-tone-blocked)", running:"var(--crew-tone-running)",
  review:"var(--crew-tone-review)", ready:"var(--crew-tone-ready)", todo:"var(--crew-tone-neutral)",
  done:"var(--crew-tone-done)", queued:"var(--crew-tone-ready)", other:"var(--crew-tone-neutral)"};
var QUIET_S = 120;                       // a live run with no heartbeat for this long crawls amber
var HEADER = [["running","running",["running"]],["blocked","blocked",["blocked","triage"]],["done","done",["done"]]];
var LAST = null, STALE_SINCE = null;

function store(k, v){ try{ if(v===undefined) return sessionStorage.getItem("crew."+k);
  if(v===null) sessionStorage.removeItem("crew."+k); else sessionStorage.setItem("crew."+k, v); }catch(e){ return null; } }
function shortId(id){ return String(id).replace(/^t_/,"").slice(0,6); }
function avatar(name, hue){ return '<span class="avatar" style="--hue:'+(hue||"var(--crew-text-3)")+'">'+
  esc((name||"?").slice(0,1).toUpperCase())+'</span>'; }
function hhmm(d){ function p(x){ return (x<10?"0":"")+x; } return p(d.getHours())+":"+p(d.getMinutes()); }

function ahead(att){ return 'needs you - <b>'+(att.stuck||0)+'</b> stuck - <b>'+(att.done||0)+'</b> done'; }
function drawNotes(att){
  var bell=document.getElementById("bell"), n=document.getElementById("belln");
  var list=document.getElementById("noterows");
  if(!bell||!n||!list) return;
  att=att||{}; var rows=att.rows||[];
  n.textContent=rows.length;
  bell.className="bell"+(rows.length?" waiting":"");
  bell.title=rows.length ? rows.length+" waiting - click for the list" : "nothing waiting";
  var h=document.getElementById("notehead"); if(h) h.innerHTML=ahead(att);
  list.innerHTML="";
  if(!rows.length){ var e=document.createElement("div"); e.className="empty";
    e.textContent="nothing waiting"; list.appendChild(e); return; }
  rows.forEach(function(r){
    var stuck=(r.status!=="done");
    var d=document.createElement("div"); d.className="ar"+(stuck?" stuck":"");
    d.innerHTML='<span class="st">'+esc(r.status)+'</span>'+
      '<a class="t" href="/card/'+esc(r.id)+'">'+esc(r.id)+' - '+esc(r.title||"(untitled)")+'</a>'+
      '<span class="w">'+esc(r.who||"-")+'</span><span class="ag">'+fmt(r.age_s)+'</span>';
    var b=document.createElement("button"); b.textContent="✕"; b.title="clear this one";
    b.onclick=function(){ fetch(r.ack_url,{cache:"no-store"}).then(tick); d.remove(); };
    d.appendChild(b);
    list.appendChild(d);
  });
}
function wireNotes(){
  var bell=document.getElementById("bell"), box=document.getElementById("notes");
  if(!bell||!box) return;
  bell.onclick=function(e){ e.stopPropagation(); box.hidden=!box.hidden; };
  document.addEventListener("click", function(e){
    if(!box.hidden && !box.contains(e.target) && e.target!==bell) box.hidden=true; });
  document.addEventListener("keydown", function(e){ if(e.key==="Escape") box.hidden=true; });
  var ca=document.getElementById("clearall");
  if(ca) ca.onclick=function(){ fetch("/ack/all",{cache:"no-store"}).then(tick); };
}

function drawCounts(c){
  var el=document.getElementById("counts"); if(!el) return;
  el.innerHTML=HEADER.map(function(h){
    var n=h[2].reduce(function(a,s){ return a+(c[s]||0); },0);
    return '<span class="'+h[0]+(n?'':' none')+'"><b>'+n+'</b>'+h[1]+'</span>'; }).join("");
}
function drawHeader(d){
  var c=document.getElementById("cards"); if(c) c.textContent=d.cards+" card"+(d.cards===1?"":"s");
  var l=document.getElementById("live"); if(l){ l.textContent=d.live ? d.live+" working now" : "nothing running";
    l.className="meta"+(d.live?" on":""); }
  var w=document.getElementById("when"); if(w) w.textContent="updated "+new Date().toLocaleTimeString();
}

// The state slot: live -> working · 4m (or no heartbeat), queued, or the verdict of a finished card.
// Every state reads as a chip tinted in its own tone: working green, no heartbeat amber, queued blue,
// verified green, verify failed red, unverified amber, done teal, blocked red.
function chip(text, tone){ return '<span class="schip" style="--tone:var(--crew-tone-'+tone+')">'+text+'</span>'; }
function stateHTML(t){
  if(t.active){
    if(t.active.quiet_s!==null && t.active.quiet_s>QUIET_S) return chip("no heartbeat", "review");
    return chip("working · "+fmt(t.active.for_s), "running");
  }
  if(t.status==="ready"||t.status==="todo") return chip("queued", "ready");
  if(t.status==="blocked"||t.status==="triage") return chip(t.status==="triage" ? "needs you" : "blocked", "blocked");
  if(t.status==="review") return chip("in review", "review");
  if(t.status!=="done") return "";
  if(t.verdict==="PASS") return chip("✓ verified", "running");
  if(t.verdict==="FAIL") return chip("✕ verify failed", "blocked");
  if(t.verdict==="unverified") return chip("○ unverified", "review");
  return chip("done", "done");
}

function cardHTML(t){
  var tone = TONE[t.status] || "var(--crew-tone-neutral)";
  var who = t.active ? t.active.profile : (t.role || t.assignee || "unassigned");
  var left = avatar(t.role, t.color)+'<span class="who">'+esc(who)+'</span>'+stateHTML(t);
  var r = "";
  if(t.runs>1) r += '<span title="runs">↻ '+t.runs+'</span>';
  var b = t.budget;
  if(b && b.pct>=80) r += '<span class="'+(b.pct>=100?"bad":"warn")+'" title="token budget: '+b.used+' of '+b.ceiling+'">'+
    Math.round(b.pct)+'%</span>';
  r += '<span title="time in this state">'+fmt(t.settled_s!==null&&t.settled_s!==undefined?t.settled_s:t.age_s)+'</span>'+
       '<span class="id" title="'+esc(t.id)+'">'+shortId(t.id)+'</span>';
  var motion = t.active ? (t.active.quiet_s!==null && t.active.quiet_s>QUIET_S ? " quiet" : " live") : "";
  return '<a class="card'+motion+'" data-id="'+esc(t.id)+'" href="/card/'+esc(t.id)+'" style="--tone:'+tone+'">'+
    '<div class="ti">'+esc(t.title||"(untitled)")+'</div>'+
    (t.summary?'<div class="su">'+esc(t.summary)+'</div>':'')+
    '<div class="ft">'+left+'<span class="r">'+r+'</span></div></a>';
}

function laneHTML(l){
  var tone = TONE[l.key] || "var(--crew-tone-neutral)";
  var tiles = l.tiles, n = l.tiles.length + (l.hidden||0);
  if(!n) return '<section class="lane rail" data-lane="'+l.key+'" style="--tone:'+tone+'" title="'+esc(l.label)+': empty">'+
    '<div class="lh"><i></i></div><span class="lt">'+esc(l.label)+'</span></section>';
  var more = l.hidden ? '<button class="more" data-older="1">Show '+l.hidden+' older</button>'
           : (l.key==="done" && store("older") ? '<button class="more" data-older="0">Show the newest only</button>' : '');
  return '<section class="lane" data-lane="'+l.key+'" style="--tone:'+tone+'">'+
    '<div class="lh"><i></i><span class="lt">'+esc(l.label)+'</span><span class="ln">'+n+'</span></div>'+
    '<div class="lbody">'+tiles.map(cardHTML).join("")+more+'</div></section>';
}

function draw(d){
  if(!d || !d.lanes) return;
  LAST = d;
  drawHeader(d);
  drawCounts(d.counts||{});
  drawNotes(d.attention);
  var main=document.getElementById("board"), scroll={};
  Array.prototype.forEach.call(main.querySelectorAll(".lane .lbody"), function(b){
    scroll[b.parentNode.getAttribute("data-lane")] = b.scrollTop; });
  main.innerHTML = d.lanes.map(function(l){ return laneHTML(l); }).join("");
  Array.prototype.forEach.call(main.querySelectorAll(".lane .lbody"), function(b){
    var k=b.parentNode.getAttribute("data-lane");
    var y = scroll[k]!==undefined ? scroll[k] : +(store("scroll."+k)||0);
    if(y) b.scrollTop=y;
    b.onscroll=function(){ store("scroll."+k, String(b.scrollTop)); };
  });
  var more = main.querySelector("[data-older]");
  if(more) more.onclick=function(){ store("older", more.getAttribute("data-older")==="1" ? "1" : null); tick(); };
}

function stale(on){
  var el=document.getElementById("stale"); if(!el) return;
  var b=document.getElementById("badge");
  if(b){ b.className="badge"+(on?" stale":""); b.title=on?"the board server is not answering":"the board server answers"; }
  if(on){ if(!STALE_SINCE) STALE_SINCE=new Date(); el.textContent="stale since "+hhmm(STALE_SINCE); el.hidden=false; }
  else { STALE_SINCE=null; el.hidden=true; }
}

function tick(){
  var qs=[]; if(/[?&]all=1/.test(location.search)) qs.push("all=1"); if(store("older")) qs.push("older=1");
  fetch("/board.json"+(qs.length?"?"+qs.join("&"):""),{cache:"no-store"})
    .then(function(r){ if(!r.ok) throw new Error(r.status); return r.json(); })
    .then(function(d){ stale(false); draw(d); })
    .catch(function(){ stale(true); });
}
wireNotes();
setInterval(tick, 2000);
if(store("older")) tick();
