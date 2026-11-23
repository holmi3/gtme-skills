#!/usr/bin/env python3
"""render_page.py: one self-contained HTML page of the ranked list, for sales to read. Standard library only.

    python render_page.py --model model.json --file accounts.csv --out ranked.html [--evidence evidence.csv] [--title "..."]
                          [--theme theme.json]

Reads the newest S<n>- set. Shows band tiles (click to filter), a search box, the ranked table, and per account the
brief, the likely owner, each part's receipt and the evidence links. Opens from disk; no server. The only network
request is the client's web font, when the theme names one on Google Fonts or Bunny Fonts.

--theme takes the file brand_theme.py writes: the client's colors for a light and a dark page, fonts, corner radius
and which mode opens first. Without it the page uses a neutral built-in look. Either way there is a Light / Dark switch.

The page also carries a closed "Try other weights" panel: one slider per rule that adds points, starting at the
model's own weights, plus the hot and warm cut-offs. Moving a slider re-scores every row in the browser from that row's
own rule points and re-sorts the list, and the panel lists the model.json edits that give the same result. It changes
nothing on disk. Before adding it, the script re-scores every row with the
model and checks it gets the parts, totals, bands and confidence on the file; if any row differs (an old model, or a different --as-of than the
scoring run used), the panel is left off and the script says why. --no-weights leaves it off on purpose.
"""
import argparse, csv, html, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score import apply_rule, parse_date, read, score_row  # noqa: E402
import hashlib  # noqa: E402
import datetime as dt  # noqa: E402

# The built-in look when no --theme is given. Same token names brand_theme.py writes.
DEFAULT_THEME = {
    "client": None, "default_mode": None, "radius": "4px",
    "fonts": {"body": "system-ui, -apple-system, 'Segoe UI', sans-serif", "heading": None, "heading_weight": "650", "css_url": None},
    "light": {"bg": "#fbfbf9", "surface": "#ffffff", "fg": "#1d1d1b", "heading": "#1d1d1b", "muted": "#64635e", "line": "#e2e1dc",
              "accent": "#1d1d1b", "accent_fg": "#ffffff", "link": "#1d1d1b", "hot_bg": "#b4321e", "hot_fg": "#ffffff",
              "warm_bg": "#f0c463", "warm_fg": "#1d1d1b", "cold": "#2f6690", "research": "#64635e", "out": "#86857f"},
    "dark": {"bg": "#141413", "surface": "#1c1c1a", "fg": "#ecebe6", "heading": "#ecebe6", "muted": "#a3a29c", "line": "#2e2d2a",
             "accent": "#ecebe6", "accent_fg": "#141413", "link": "#ecebe6", "hot_bg": "#ef6f55", "hot_fg": "#141413",
             "warm_bg": "#e0b04a", "warm_fg": "#141413", "cold": "#7fb2dc", "research": "#a3a29c", "out": "#8a8983"},
}
TOKENS = ["bg", "surface", "fg", "heading", "muted", "line", "accent", "accent_fg", "link", "hot_bg", "hot_fg", "warm_bg",
          "warm_fg", "cold", "research", "out"]
FONT_HOSTS = ("https://fonts.googleapis.com/", "https://fonts.bunny.net/")
SAFE = re.compile(r"^[#\w\s.,'\"()%-]*$")  # what a font stack may contain; anything else is dropped
COLOR = re.compile(r"^(#[0-9a-fA-F]{3,8}|(rgb|hsl)a?\([\d.,%\s/]+\))$")  # what a color token may be


def css_vars(t, fallback):
    out = []
    for k in TOKENS:
        v = str(t.get(k) or fallback[k])
        out.append(f"--{k.replace('_', '-')}:{v if COLOR.match(v) else fallback[k]}")
    return ";".join(out)


def theme_css(theme):
    d = DEFAULT_THEME
    th = theme or d
    fonts = {**d["fonts"], **{k: v for k, v in (th.get("fonts") or {}).items() if v}}
    body = fonts["body"] if SAFE.match(fonts["body"]) else d["fonts"]["body"]
    if "sans-serif" not in body and "serif" not in body:
        body += ", system-ui, sans-serif"
    head = fonts.get("heading") or body
    head = head if SAFE.match(head) else body
    weight = str(fonts.get("heading_weight") or "650")
    weight = weight if weight.isdigit() else "650"
    radius = str(th.get("radius") or d["radius"])
    radius = radius if re.match(r"^\d+(\.\d+)?px$", radius) else d["radius"]
    url = fonts.get("css_url") or ""
    link = f"@import url('{url}');" if url.startswith(FONT_HOSTS) and "'" not in url else ""
    mode = th.get("default_mode") if th.get("default_mode") in ("light", "dark") else None
    return {"__FONTLINK__": link, "__LIGHT__": css_vars(th.get("light") or {}, d["light"]),
            "__DARK__": css_vars(th.get("dark") or {}, d["dark"]), "__RADIUS__": radius, "__BODYFONT__": body,
            "__HEADFONT__": head, "__HEADWEIGHT__": weight, "__MODEATTR__": f' data-theme="{mode}"' if mode else ""}


PANEL = '<details class="wt" id="wt"><summary>Try other weights<small>Move the sliders and the list re-sorts. Starts at the model\'s weights; nothing on disk changes.</small></summary><div id="wtBody"></div></details>'

BANDS = [("hot", "personal outreach now"), ("warm", "after hot is done"), ("cold", "nurture only"),
         ("research", "not handed over until a page is read"), ("out", "disqualified, kept with its reason")]

PAGE = """<!doctype html>
<html lang="en"__MODEATTR__><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
__FONTLINK__
:root{__LIGHT__;--radius:__RADIUS__;--body-font:__BODYFONT__;--heading-font:__HEADFONT__;--heading-weight:__HEADWEIGHT__;color-scheme:light}
@media (prefers-color-scheme: dark){:root:not([data-theme=light]){__DARK__;color-scheme:dark}}
:root[data-theme=dark]{__DARK__;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 var(--body-font)}
main{max-width:1100px;margin:0 auto;padding:24px 16px 64px}
header{display:flex;gap:12px;align-items:flex-start;justify-content:space-between;border-bottom:3px solid var(--accent);padding-bottom:12px;margin-bottom:16px}
h1{font:var(--heading-weight) 24px/1.2 var(--heading-font);color:var(--heading);margin:0 0 4px}.sub{color:var(--muted);margin:0}
.mode{flex:none;background:var(--accent);color:var(--accent-fg);border:0;border-radius:var(--radius);padding:7px 14px;font:600 13px/1.2 var(--body-font);cursor:pointer}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-bottom:16px}
.tile{border:1px solid var(--line);border-radius:var(--radius);background:var(--surface);padding:10px 12px;cursor:pointer;text-align:left;color:inherit;font:inherit}
.tile b{display:block;font-size:24px;line-height:1.2;margin-bottom:4px}.tile span.l{display:block;color:var(--muted);font-size:13px;margin-top:4px}.tile[aria-pressed=true]{outline:2px solid var(--fg);outline-offset:-1px}
input[type=search]{width:100%;padding:9px 10px;border:1px solid var(--line);border-radius:var(--radius);background:var(--surface);color:var(--fg);font:inherit;margin-bottom:12px}
.wrap{overflow-x:auto;border:1px solid var(--line);border-radius:var(--radius);background:var(--surface)}table{border-collapse:collapse;width:100%;min-width:680px}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{font-size:12px;color:var(--muted);font-weight:600}
td.n{text-align:right;font-variant-numeric:tabular-nums}tr.row{cursor:pointer}tr.row:hover{background:color-mix(in srgb,var(--line) 35%,transparent)}
.chip{display:inline-block;padding:1px 9px;border:1px solid currentColor;border-radius:min(var(--radius),999px);font-size:12px;font-weight:600}
.chip.hot{background:var(--hot-bg);color:var(--hot-fg);border-color:var(--hot-bg)}.chip.warm{background:var(--warm-bg);color:var(--warm-fg);border-color:var(--warm-bg)}
.chip.cold{color:var(--cold)}.chip.research{color:var(--research);border-style:dashed}.chip.out{color:var(--out)}
tr.detail td{background:var(--bg)}.detail p{margin:4px 0 10px}.detail ul{margin:4px 0 10px;padding-left:18px}.k{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
details.legend{margin:16px 0;border:1px solid var(--line);border-radius:var(--radius);background:var(--surface);padding:10px 12px}details.legend summary{cursor:pointer}
.legend table{min-width:0}a{color:var(--link)}footer{color:var(--muted);font-size:12px;margin-top:24px}
details.wt{margin:0 0 16px;border:1px solid var(--line);border-radius:var(--radius);background:var(--surface);padding:10px 12px}
details.wt>summary{cursor:pointer;font-weight:600}details.wt>summary small{display:block;font-weight:400;color:var(--muted);font-size:13px}
.wt-pre{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:12px 0}.wt-pre>span.l{color:var(--muted);font-size:13px}
.wt-b{border:1px solid var(--line);background:var(--bg);color:var(--fg);border-radius:min(var(--radius),999px);padding:3px 10px;font:500 13px/1.3 var(--body-font);cursor:pointer}
.wt-b[aria-pressed=true]{background:var(--accent);color:var(--accent-fg);border-color:var(--accent)}.wt-b.x{padding:3px 7px;margin-left:-4px}
.wt-g{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px}
.wt-p{border:1px solid var(--line);border-radius:var(--radius);padding:8px 10px;background:var(--bg)}.wt-p h3{font:600 14px/1.3 var(--body-font);margin:0 0 6px;display:flex;justify-content:space-between;gap:8px}
.wt-p h3 span,.wt-s small,.wt-note{color:var(--muted);font-weight:400;font-size:12px}
.wt-s{display:grid;grid-template-columns:1fr auto;gap:0 8px;margin:6px 0;font-size:13px}.wt-s input{grid-column:1/-1;width:100%}.wt-s output{font-variant-numeric:tabular-nums}
.wt-s small{grid-column:1/-1}.chg{font-weight:700;color:var(--fg)}
.wt-ed{flex-basis:100%;margin-top:6px}.wt-ed ul{margin:4px 0;padding-left:18px}.wt-if{display:none;margin:10px 0 0;padding:8px 10px;border-left:3px solid var(--accent);background:var(--bg);font-size:13px}.wt-if.on{display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap}
.wt-top{margin:6px 0 0;padding-left:20px;font-size:13px}.wt-top .mv{color:var(--muted);font-size:12px}
.wt-form{display:inline-flex;gap:6px}.wt-form[hidden]{display:none}.wt-form input{padding:3px 8px;border:1px solid var(--line);border-radius:var(--radius);background:var(--bg);color:var(--fg);font:inherit;font-size:13px}
small.was,small.d{display:block;color:var(--muted);font-size:11px;font-weight:400}small.d{display:inline;margin-left:6px}
</style></head><body><main>
<header><div><h1>__TITLE__</h1><p class="sub">__SUB__</p></div><button class="mode" id="mode" type="button">Dark</button></header>
__PANEL__<div class="tiles" id="tiles"></div>
<input type="search" id="q" placeholder="Search company, domain, owner or brief" aria-label="Search">
<div class="wrap"><table><thead><tr><th>#</th><th>Company</th><th>Band</th><th class="n">Total</th>__PARTHEADS__<th>Likely owner</th></tr></thead><tbody id="tb"></tbody></table></div>
<details class="legend"><summary>How to read this page</summary>__LEGEND__</details>
<footer>__FOOT__</footer>
</main>
<script>
const DATA = __DATA__; const PARTS = __PARTS__; const WT = __WT__;
let band = null, q = "", open = null, whatIf = false, wasOf = () => "", delta = () => "";
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function tiles(){const t=document.getElementById("tiles");t.innerHTML="";for(const [b,label] of __BANDS__){const n=DATA.filter(r=>r.band===b).length;const el=document.createElement("button");el.className="tile";el.setAttribute("aria-pressed",band===b);el.innerHTML=`<b>${n}${whatIf?delta(b,n):""}</b><span class="chip ${b}">${b}</span><span class="l">${esc(label)}</span>`;el.onclick=()=>{band=band===b?null:b;render()};t.appendChild(el)}}
function render(){tiles();const tb=document.getElementById("tb");tb.innerHTML="";const ql=q.toLowerCase();let i=0;
 for(const r of DATA){if(band&&r.band!==band)continue;if(ql&&!(r.company+r.key+r.owner+r.brief).toLowerCase().includes(ql))continue;i++;
  const tr=document.createElement("tr");tr.className="row";tr.innerHTML=`<td class="n">${i}</td><td><b>${esc(r.company)}</b><br><span class="k">${esc(r.key)}</span></td><td><span class="chip ${esc(r.band)}">${esc(r.band)}</span></td><td class="n">${esc(r.total)}${whatIf?wasOf(r):""}</td>`+PARTS.map(p=>`<td class="n">${esc(r.parts[p])}</td>`).join("")+`<td>${esc(r.owner)}</td>`;
  tr.onclick=()=>{open=open===r.key?null:r.key;render()};tb.appendChild(tr);
  if(open===r.key){const d=document.createElement("tr");d.className="detail";const ev=r.evidence.map(e=>`<li>${esc(e.field)}: "${esc(e.quote)}" <a href="${/^https?:[/][/]/i.test(e.url)?esc(e.url):"#"}" rel="noopener">source</a>, read ${esc(e.read_on)} (${esc(e.confidence)})</li>`).join("");
   d.innerHTML=`<td></td><td colspan="${4+PARTS.length}">`+(r.brief?`<div class="k">Account brief</div><p>${esc(r.brief)}</p>`:"")+(r.owner?`<div class="k">Likely owner</div><p>${esc(r.owner)}${r.champion?", with the "+esc(r.champion)+" as champion":""}. <span class="k">${esc(r.owner_basis)}</span></p>`:"")+`<div class="k">Why it scores ${esc(whatIf?r._o.total:r.total)} at the model's weights (${esc(r.confidence||"no")} confidence)</div><ul>${r.why.split(" | ").map(w=>`<li>${esc(w)}</li>`).join("")}</ul>`+(ev?`<div class="k">Evidence</div><ul>${ev}</ul>`:"")+`</td>`;tb.appendChild(d)}}
 if(!i)tb.innerHTML=`<tr><td colspan="${5+PARTS.length}">No accounts match.</td></tr>`}
document.getElementById("q").oninput=e=>{q=e.target.value;render()};
__WTJS__
render();
const root=document.documentElement,mb=document.getElementById("mode");
const isDark=()=>root.dataset.theme?root.dataset.theme==="dark":matchMedia("(prefers-color-scheme: dark)").matches;
const label=()=>{mb.textContent=isDark()?"Light":"Dark";mb.setAttribute("aria-label","Switch to "+mb.textContent.toLowerCase()+" mode")};
mb.onclick=()=>{root.dataset.theme=isDark()?"light":"dark";label()};label();
</script></body></html>"""


WTJS = r'''if(WT){(()=>{
/* What-if weights. Each row carries its own points per rule (r.wt, from the model at render time). A slider sets the
   most points a rule can give; a row keeps its level on that rule and the slider scales it. Penalties stay fixed. Parts
   keep their caps (scaled with their sliders) and the total is scaled back to the model's usual maximum. */
const $=id=>document.getElementById(id), r1=x=>Math.round(x*10)/10;
const DEF={},W={};WT.parts.forEach(p=>p.rules.forEach(x=>{DEF[x.id]=x.d}));
const DTH=[WT.bands.hot,WT.bands.warm];let TH=DTH.slice(),cur="def";
const resetW=()=>{for(const k in DEF)W[k]=DEF[k];TH=DTH.slice()};resetW();
const isDef=()=>Object.keys(DEF).every(k=>W[k]===DEF[k])&&TH[0]===DTH[0]&&TH[1]===DTH[1];
const sum=(p,w)=>p.rules.reduce((s,x)=>s+w[x.id],0);
const cap=p=>{const d=sum(p,DEF);return d?p.max*sum(p,W)/d:p.max};
const TOP=WT.parts.reduce((s,p)=>s+p.max,0);
/* No rescaling: a part cap moves with its sliders and totals may pass TOP, so every what-if equals a plain model edit
   (rule points times W/D, part max = cap, the same cut-offs), shown under "Same result in the model file". */
const norm=()=>1;
const ORDER={hot:0,warm:1,cold:2,research:3,out:4},ORANK={},OB={};
DATA.forEach((r,i)=>{r._o={band:r.band,total:r.total,parts:{...r.parts},i};ORANK[r.key]=i+1;OB[r.band]=(OB[r.band]||0)+1});
function bandOf(r,t){if(r.confidence!=="medium"&&r.confidence!=="high")return"research";return t>=TH[0]?"hot":t>=TH[1]?"warm":"cold"}
function rescore(){whatIf=!isDef();
 if(!whatIf){DATA.forEach(r=>{r.band=r._o.band;r.total=r._o.total;r.parts={...r._o.parts}});DATA.sort((a,b)=>a._o.i-b._o.i);return}
 const n=norm();
 DATA.forEach(r=>{if(!r.wt)return;let t=0;const ps={};
  WT.parts.forEach(p=>{const c=r.wt[p.k];let raw=c.f;c.l.forEach(([id,v])=>{raw+=v*W[id]/DEF[id]});
   const v=Math.max(0,Math.min(cap(p),raw));t+=v;ps[p.k]=r1(v*n)});
  r.parts=ps;r.total=r1(t*n);r.band=bandOf(r,r.total)});
 DATA.sort((a,b)=>(ORDER[a.band]??9)-(ORDER[b.band]??9)||(Number(b.total)||0)-(Number(a.total)||0)||a._o.i-b._o.i);
}
wasOf=r=>{const o=r._o;if(String(o.total)===String(r.total)&&o.band===r.band)return"";return `<small class="was">was ${esc(o.total)}${o.band!==r.band?" "+esc(o.band):""}, #${ORANK[r.key]}</small>`};
delta=(b,n)=>{const d=n-(OB[b]||0);return d?`<small class="d">${d>0?"+":""}${d}</small>`:""};
const cap1=s=>s.charAt(0).toUpperCase()+s.slice(1);
const PRE={def:{}};WT.parts.forEach(p=>{const o={};p.rules.forEach(x=>{o[x.id]=x.d*2});PRE["x2:"+p.k]=o});
const box=$("wtBody");
box.innerHTML=`<div class="wt-pre" id="wtPre"><span class="l">Try:</span><button class="wt-b" type="button" data-p="def">Model weights</button>`+
 WT.parts.filter(p=>p.rules.length).map(p=>`<button class="wt-b" type="button" data-p="x2:${esc(p.k)}">${esc(cap1(p.k))} counts double</button>`).join("")+
 `<span id="wtCustom" style="display:contents"></span><button class="wt-b" id="wtSave" type="button" hidden>+ Save these weights</button>`+
 `<span class="wt-form" id="wtForm" hidden><input id="wtName" maxlength="40" placeholder="Name these weights" aria-label="Name these weights"><button class="wt-b" type="button" id="wtOk">Save</button><button class="wt-b" type="button" id="wtCancel">Cancel</button></span></div>`+
 `<div class="wt-g">`+WT.parts.map(p=>`<div class="wt-p"><h3>${esc(cap1(p.k))}<span data-mx="${esc(p.k)}"></span></h3>`+
  (p.rules.length?p.rules.map(x=>`<label class="wt-s"><span>${esc(x.label)}</span><output data-o="${esc(x.id)}"></output><input type="range" min="0" max="${Math.max(8,2*x.d)}" step="1" data-k="${esc(x.id)}" aria-label="${esc(p.k+": "+x.label)}"><small>model: up to ${x.d} points</small></label>`).join(""):`<p class="wt-note">No adjustable rules.</p>`)+
  (p.fixed?`<p class="wt-note">Penalties in this part stay at the model's values.</p>`:"")+`</div>`).join("")+
 `<div class="wt-p"><h3>Bands<span id="wtN"></span></h3><label class="wt-s"><span>Hot from</span><output id="wtO0"></output><input type="range" min="1" max="${2*TOP}" id="wtTh0" aria-label="Hot from score"><small>model: ${DTH[0]}</small></label>`+
 `<label class="wt-s"><span>Warm from</span><output id="wtO1"></output><input type="range" min="0" max="${2*TOP}" id="wtTh1" aria-label="Warm from score"><small>model: ${DTH[1]}</small></label>`+
 `<p class="wt-note">Research rows stay research at any score, because something the model needs is still unread. Out rows stay out.</p><div class="k">Top 8 now</div><ol class="wt-top" id="wtTop"></ol></div></div>`+
 `<div class="wt-if" id="wtIf"><span><b>What-if view.</b> The list below uses these weights. Nothing on disk changes, and each row's receipt still shows the model's points.</span><button class="wt-b" type="button" id="wtReset">Back to model weights</button><details class="wt-ed"><summary>Same result in the model file</summary><ul id="wtEdit"></ul><p class="wt-note">Make these edits in model.json and rescore to get this ranking for real. Recency-weighted rules can differ by a rounding step.</p></details></div>`+
 `<p class="wt-note">Each slider sets the most points a rule can give. Each company keeps its level on that rule (for example its size band), and the slider scales it. A part's cap moves with its sliders, so totals can go above ${TOP}. Saved weights stay in this browser only.</p>`;
box.querySelectorAll("input[data-k]").forEach(i=>i.addEventListener("input",()=>{W[i.dataset.k]=+i.value;cur="";update()}));
[0,1].forEach(i=>$("wtTh"+i).addEventListener("input",()=>{TH[i]=+$("wtTh"+i).value;if(TH[1]>TH[0]){if(i===0)TH[1]=TH[0];else TH[0]=TH[1]}cur="";update()}));
let CUSTOM={},canStore=true;try{CUSTOM=JSON.parse(localStorage.getItem(WT.store)||"{}")||{}}catch(e){CUSTOM={};canStore=false}
const store=()=>{try{localStorage.setItem(WT.store,JSON.stringify(CUSTOM))}catch(e){}};
function chips(){const ids=Object.keys(CUSTOM).sort((a,b)=>(CUSTOM[a].at||"")<(CUSTOM[b].at||"")?-1:1);
 $("wtCustom").innerHTML=ids.map(id=>`<button class="wt-b" type="button" data-c="${esc(id)}" aria-pressed="${cur==="c:"+id}">${esc(CUSTOM[id].name)}</button><button class="wt-b x" type="button" data-del="${esc(id)}" aria-label="Delete ${esc(CUSTOM[id].name)}">×</button>`).join("");
 $("wtSave").hidden=!canStore||!$("wtForm").hidden||isDef()||cur.startsWith("c:")}
$("wtPre").addEventListener("click",e=>{const b=e.target.closest("button");if(!b)return;
 if(b.dataset.p){resetW();Object.assign(W,PRE[b.dataset.p]||{});cur=b.dataset.p;update()}
 else if(b.dataset.c){const c=CUSTOM[b.dataset.c];if(!c)return;resetW();for(const k in c.w||{})if(k in DEF)W[k]=Math.max(0,Math.min(99,+c.w[k]||0));if(Array.isArray(c.th)&&c.th.length===2){TH=c.th.map(x=>Math.max(0,Math.min(2*TOP,Math.round(+x)||0)));if(TH[1]>TH[0])TH[1]=TH[0]}cur="c:"+b.dataset.c;update()}
 else if(b.dataset.del){if(cur==="c:"+b.dataset.del)cur="";delete CUSTOM[b.dataset.del];store();chips()}});
$("wtSave").onclick=()=>{$("wtForm").hidden=false;$("wtSave").hidden=true;$("wtName").value="";$("wtName").focus()};
$("wtCancel").onclick=()=>{$("wtForm").hidden=true;chips()};
function save(){const name=$("wtName").value.trim().slice(0,40);if(!name){$("wtName").focus();return}
 const id=name.toLowerCase().replace(/[^a-z0-9]+/g,"-").slice(0,30)+"-"+Date.now().toString(36);
 CUSTOM[id]={name,w:{...W},th:TH.slice(),at:new Date().toISOString()};store();cur="c:"+id;$("wtForm").hidden=true;update()}
$("wtOk").onclick=save;$("wtName").addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();save()}if(e.key==="Escape")$("wtCancel").onclick()});
$("wtReset").onclick=()=>{resetW();cur="def";update()};
function update(){rescore();const n=norm();
 box.querySelectorAll("input[data-k]").forEach(i=>{const k=i.dataset.k;i.value=W[k];const o=box.querySelector(`[data-o="${CSS.escape(k)}"]`);o.textContent=W[k];o.classList.toggle("chg",W[k]!==DEF[k])});
 [0,1].forEach(i=>{$("wtTh"+i).value=TH[i];$("wtO"+i).textContent=TH[i];$("wtO"+i).classList.toggle("chg",TH[i]!==DTH[i])});
 WT.parts.forEach(p=>{const v=whatIf?r1(cap(p)*n):p.max,el=box.querySelector(`[data-mx="${CSS.escape(p.k)}"]`);el.textContent=`up to ${v}`;el.classList.toggle("chg",v!==p.max)});
 $("wtN").textContent=DATA.length+" accounts";
 $("wtTop").innerHTML=DATA.slice(0,8).map((r,i)=>{const mv=ORANK[r.key]-(i+1);return `<li>${esc(r.company)} ${esc(r.total)} <span class="mv">${mv?(mv>0?"up "+mv:"down "+(-mv)):"same"}</span></li>`}).join("");
 box.querySelectorAll("button[data-p]").forEach(b=>b.setAttribute("aria-pressed",b.dataset.p===cur));
 const ed=[];WT.parts.forEach(p=>{p.rules.forEach(x=>{if(W[x.id]!==x.d)ed.push(`${p.k} / ${x.label}: multiply its points by ${r1(W[x.id]/x.d)} (top ${x.d} becomes ${W[x.id]})`)});
  const c=r1(cap(p));if(c!==p.max)ed.push(`${p.k}: max ${p.max} becomes ${c}`)});
 if(TH[0]!==DTH[0]||TH[1]!==DTH[1])ed.push(`bands: hot ${TH[0]}, warm ${TH[1]}`);
 $("wtEdit").innerHTML=ed.map(e=>`<li>${esc(e)}</li>`).join("");
 $("wtIf").classList.toggle("on",whatIf);chips();render()}
update();
})()}'''


def rule_top(r):
    """The most points a rule can give; 0 for a rule that can only take points away."""
    t = r["type"]
    if t == "map":
        return max(list(r["points"].values()) + [r.get("default", 0), 0])
    if t == "flag":
        return max(r["points"], 0)
    if t in ("bands", "ratio"):
        return max([s["points"] for s in r["steps"]] + [0])
    if t == "count_of":
        return max(min(r["each"] * len(r["any"]), r.get("max", 99)), 0)
    return 0


def rule_low(r):
    """The fewest points a rule can give (negative for a penalty)."""
    t = r["type"]
    if t == "map":
        return min(list(r["points"].values()) + [r.get("default", 0), 0])
    if t == "flag":
        return min(r["points"], 0)
    if t in ("bands", "ratio"):
        return min([s["points"] for s in r["steps"]] + [0])
    if t == "count_of":
        return min(r["each"], 0)
    return 0


def weights_data(model, rows, p, as_of, store_key):
    """Per-rule points for every scored row, for the what-if panel. Returns ((spec, per_row), None) or (None, problem).
    The panel is only built when the model reproduces every part on the file, so it never shows numbers that disagree
    with the table."""
    parts, key = list(model["parts"]), model.get("key", "domain")
    spec = {"parts": [], "bands": model["bands"], "store": store_key}
    for k in parts:
        rules = model["parts"][k]["rules"]
        sl = [{"id": f"{k}.{i}", "label": r.get("label", r.get("column", "")), "d": rule_top(r)}
              for i, r in enumerate(rules) if rule_top(r) > 0]
        fixed = any(rule_low(r) < 0 for r in rules)
        spec["parts"].append({"k": k, "max": model["parts"][k]["max"], "rules": sl, "fixed": fixed})
    per_row, bad = [], []
    for r in rows:
        day = as_of or parse_date(r.get(p + "scored_on")) or dt.date.today()
        s_row = score_row(r, model, day)
        for col, have in (("total", s_row["total"]), ("band", s_row["band"]), ("confidence", s_row["confidence"])):
            want = r.get(p + col, "")
            same = (abs(float(want or 0) - float(have)) <= 0.05) if col == "total" else str(want) == str(have)
            if not same:
                bad.append(f"{r.get(key)} {col}: file {want!r}, model {have!r}")
        if s_row["band"] == "out":
            per_row.append(None)
            continue
        wt = {}
        for k in parts:
            s, lines, fixed = model["parts"][k], [], 0.0
            for i, rule in enumerate(s["rules"]):
                got = apply_rule(r, rule, day)[0]
                if got > 0 and rule_top(rule) > 0:
                    lines.append([f"{k}.{i}", got])
                else:
                    fixed += got  # penalties stay at the model's value
            have = round(max(0.0, min(fixed + sum(v for _, v in lines), s["max"])), 1)
            want = r.get(p + k, "")
            try:
                ok = abs(float(want) - have) <= 0.05
            except ValueError:
                ok = False
            if not ok:
                bad.append(f"{r.get(key)} {k}: file {want!r}, model {have}")
            wt[k] = {"f": round(fixed, 2), "l": lines}
        per_row.append(wt)
    if bad:
        return None, f"{len(bad)} value(s) differ, first: {bad[0]}"
    return (spec, per_row), None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True); ap.add_argument("--file", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--evidence"); ap.add_argument("--title", default="Ranked accounts")
    ap.add_argument("--theme", help="theme.json from brand_theme.py; leave out for the built-in look")
    ap.add_argument("--as-of", help="the date score.py used for recency (its --as-of); default: each row's scored_on")
    ap.add_argument("--no-weights", action="store_true", help="leave out the Try other weights panel")
    a = ap.parse_args()
    model = json.loads(Path(a.model).read_text(encoding="utf-8"))
    theme = json.loads(Path(a.theme).read_text(encoding="utf-8")) if a.theme else None
    key, parts = model.get("key", "domain"), list(model["parts"])
    rows, cols = read(a.file)
    sets = sorted({int(m.group(1)) for c in cols if (m := re.match(r"S(\d+)-total$", c))})
    if not sets:
        sys.exit("no scored set on the file; run score.py --write first")
    p = f"S{sets[-1]}-"
    ev = {}
    if a.evidence:
        for e in csv.DictReader(open(a.evidence, newline="", encoding="utf-8")):
            ev.setdefault(e[key], []).append(e)
    order = {b: i for i, (b, _) in enumerate(BANDS)}
    data = []
    for r in rows:
        data.append({"key": r[key], "company": r.get("company", r[key]), "band": r.get(p + "band", ""),
                     "total": r.get(p + "total", ""), "confidence": r.get(p + "confidence", ""),
                     "parts": {x: r.get(p + x, "") for x in parts}, "why": r.get(p + "why", ""),
                     "brief": r.get("brief", ""), "owner": r.get("owner", ""), "champion": r.get("champion", ""),
                     "owner_basis": r.get("owner_basis", ""), "evidence": ev.get(r[key], [])})
    wt_spec, note = None, "left out (--no-weights)"
    if not a.no_weights:
        as_of = dt.date.fromisoformat(a.as_of) if a.as_of else None
        slug = re.sub(r"[^a-z0-9]+", "-", a.title.lower()).strip("-")[:60]
        sig = json.dumps([model.get("name", ""), {k: [r.get("label", r.get("column", "")) for r in v["rules"]]
                                                     for k, v in model["parts"].items()}], sort_keys=True)
        store = f"tam-weights:{slug}:{hashlib.sha1(sig.encode()).hexdigest()[:10]}"  # a model edit starts a fresh set
        got, problem = weights_data(model, rows, p, as_of, store)
        if got:
            wt_spec, per_row = got
            for d, w in zip(data, per_row):
                d["wt"] = w
            note = "on"
        else:
            note = f"left out, because the model does not reproduce the scores on the file ({problem}); rescore, or pass the --as-of the scoring run used"
    data.sort(key=lambda d: (order.get(d["band"], 9), -float(d["total"] or 0)))
    b = model["bands"]
    legend = ("<table><tr><th>Band</th><th>Rule</th><th>What happens</th></tr>"
              f"<tr><td><span class='chip hot'>hot</span></td><td>total {b['hot']} or more, medium or high confidence</td><td>personal outreach now</td></tr>"
              f"<tr><td><span class='chip warm'>warm</span></td><td>{b['warm']} to below {b['hot']}, medium or high confidence</td><td>after hot is done</td></tr>"
              f"<tr><td><span class='chip cold'>cold</span></td><td>below {b['warm']}, medium or high confidence</td><td>nurture only</td></tr>"
              "<tr><td><span class='chip research'>research</span></td><td>low confidence: no page read yet, or too little data</td><td>not handed over until a page is read</td></tr>"
              "<tr><td><span class='chip out'>out</span></td><td>disqualified (anti-ICP, customer, partner, competitor)</td><td>kept so nobody researches it again</td></tr></table>"
              "<p>Each part has a maximum: " + ", ".join(f"{x} {model['parts'][x]['max']}" for x in parts) +
              ". Fit and prize come from what the company is; the other parts only rank within that. Click any row for the brief, the receipt behind every point, and the sources.</p>")
    sub = f"{len(rows)} accounts, scored by {model.get('name', 'the model')}"
    foot = "Built from public sources. Every point has a receipt; click a row to see it."
    if theme and theme.get("client"):
        sub = f"Prepared for {theme['client']}. " + sub
        foot += f" Colors and type follow {theme['client']}'s website" + (f", read {theme['read_on']}." if theme.get("read_on") else ".")
    out = PAGE
    for k, v in theme_css(theme).items():
        out = out.replace(k, v)
    out = (out.replace("__TITLE__", html.escape(a.title))
           .replace("__SUB__", html.escape(sub)).replace("__FOOT__", html.escape(foot))
           .replace("__PARTHEADS__", "".join(f'<th class="n">{html.escape(x.capitalize())}</th>' for x in parts))
           .replace("__LEGEND__", legend)
           .replace("__BANDS__", json.dumps(BANDS))
           .replace("__PARTS__", json.dumps(parts))
           .replace("__PANEL__", PANEL if wt_spec else "")
           .replace("__WTJS__", WTJS if wt_spec else "")
           .replace("__WT__", json.dumps(wt_spec).replace("</", "<\\/"))
           .replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))
    Path(a.out).write_text(out, encoding="utf-8")
    print(f"wrote {a.out} ({len(data)} accounts, {'theme for ' + str(theme.get('client')) if theme else 'built-in look'}; "
          f"weights panel {note})")


if __name__ == "__main__":
    main()
