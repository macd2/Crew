// Shared by the board and the card page: inlined ahead of board.js / card.js.
function esc(t){ return (t===null||t===undefined)?"":String(t)
  .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }
// A duration in seconds as 4s / 4m / 4h / 4d.
function fmt(s){ if(s===null||s===undefined) return "";
  s=Math.max(0,Math.floor(s)); if(s<60) return s+"s";
  if(s<3600) return Math.floor(s/60)+"m"; if(s<86400) return Math.floor(s/3600)+"h";
  return Math.floor(s/86400)+"d"; }
// A canvas cannot read var(--token): resolve any CSS colour (a token, a hex, a colour-mix) to the
// colour the browser computes for it.
var COLOUR_PROBE = null;
function cssColour(v){
  if(!COLOUR_PROBE){ COLOUR_PROBE = document.createElement("span"); COLOUR_PROBE.style.display = "none";
    document.body.appendChild(COLOUR_PROBE); }
  COLOUR_PROBE.style.color = v;
  return getComputedStyle(COLOUR_PROBE).color;
}
function copyText(text, done){
  try{
    if(navigator.clipboard && window.isSecureContext){
      navigator.clipboard.writeText(text).then(function(){ done(true); }, function(){ done(false); });
      return;
    }
  }catch(e){}
  try{
    var ta = document.createElement("textarea");
    ta.value = text; ta.setAttribute("readonly","");
    ta.style.position = "fixed"; ta.style.top = "-1000px";
    document.body.appendChild(ta); ta.select(); ta.setSelectionRange(0, ta.value.length);
    var ok = document.execCommand("copy");
    document.body.removeChild(ta); done(ok);
  }catch(e){ done(false); }
}
