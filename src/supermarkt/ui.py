from __future__ import annotations

import html
import json

from .loyalty import normalize_program_ids


def build_home_html(*, error: str = "", postal_code: str = "") -> str:
    error_html = f'<div class="error" role="alert">{html.escape(error)}</div>' if error else ""
    postal = html.escape(postal_code, quote=True)
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="alternate icon" href="/favicon.ico">
<title>Supermarkt-Preisvergleich</title>
<style>
:root{{--bg:#f5f6f8;--panel:#fff;--text:#16181d;--muted:#68707d;--line:#dfe3e8;--accent:#0b57d0;--error:#b42318;--shadow:0 12px 38px rgba(0,0,0,.10)}}
@media(prefers-color-scheme:dark){{:root{{--bg:#111318;--panel:#191c22;--text:#f1f3f5;--muted:#aab1bc;--line:#303641;--accent:#8ab4f8;--error:#ff938a;--shadow:none}}}}
*{{box-sizing:border-box}} body{{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);color:var(--text);font:16px/1.5 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;padding:24px}}
.card{{width:min(620px,100%);background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:28px;box-shadow:var(--shadow)}}
h1{{font-size:30px;line-height:1.15;margin:0 0 10px}} p{{margin:0 0 24px;color:var(--muted)}}
form{{display:grid;grid-template-columns:1fr auto;gap:10px}} input,button{{font:inherit;border-radius:12px;padding:13px 14px}} input{{min-width:0;border:1px solid var(--line);background:var(--panel);color:var(--text);font-size:18px;letter-spacing:.05em}} button{{border:1px solid var(--accent);background:var(--accent);color:#fff;font-weight:700;cursor:pointer}} button:disabled{{opacity:.65;cursor:wait}}
.hint{{font-size:13px;color:var(--muted);margin-top:14px}} .error{{margin:0 0 16px;padding:10px 12px;border:1px solid color-mix(in srgb,var(--error) 45%,var(--line));border-radius:10px;color:var(--error)}}
@media(max-width:520px){{.card{{padding:22px}} form{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<main class="card">
<h1>Supermarkt-Preisvergleich</h1>
<p>Postleitzahl eingeben. Der Dienst sucht die verfügbaren Wochenangebote automatisch und öffnet anschließend den vollständigen Vergleich.</p>
{error_html}
<form method="post" action="/search" id="searchForm">
<input name="postal_code" value="{postal}" inputmode="numeric" autocomplete="postal-code" pattern="[0-9]{{5}}" minlength="5" maxlength="5" placeholder="Postleitzahl" aria-label="Postleitzahl" required autofocus>
<button type="submit" id="submitButton">Angebote suchen</button>
</form>
<div class="hint">Keine LLM erforderlich. Bonusprogramme, Händlerfilter und Sortierung wählst du anschließend in der Ergebnisansicht.</div>
</main>
<script>
document.getElementById("searchForm").addEventListener("submit",()=>{{const b=document.getElementById("submitButton");b.disabled=true;b.textContent="Angebote werden geladen …";}});
</script>
</body>
</html>"""


def build_results_html(
    search_id: str,
    signature: str,
    selected_programs: tuple[str, ...] = (),
) -> str:
    sid = json.dumps(search_id)
    token = json.dumps(signature)
    selected = json.dumps(list(normalize_program_ids(selected_programs)))
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="alternate icon" href="/favicon.ico">
<title>Supermarkt-Preisvergleich</title>
<style>
:root{{--bg:#f5f6f8;--panel:#fff;--text:#16181d;--muted:#68707d;--line:#dfe3e8;--accent:#0b57d0;--chip:#edf2ff;--good:#16794b;--shadow:0 8px 28px rgba(0,0,0,.08)}}
@media(prefers-color-scheme:dark){{:root{{--bg:#111318;--panel:#191c22;--text:#f1f3f5;--muted:#aab1bc;--line:#303641;--accent:#8ab4f8;--chip:#222b3a;--good:#72d5a6;--shadow:none}}}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
.wrap{{max-width:1600px;margin:auto;padding:18px}} .top{{position:sticky;top:0;z-index:10;background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:blur(12px);padding:4px 0 12px}}
h1{{font-size:25px;margin:0}} .titlebar{{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:4px}} .newSearch{{text-decoration:none;font-weight:650}} .meta{{color:var(--muted);margin-bottom:12px}} .controls{{display:grid;grid-template-columns:minmax(220px,2fr) minmax(170px,1fr);gap:8px}}
input,select,button{{font:inherit;border:1px solid var(--line);border-radius:10px;background:var(--panel);color:var(--text);padding:10px 12px}} button{{cursor:pointer}} .chips{{display:flex;gap:7px;flex-wrap:wrap;margin:10px 0 2px}} .viewTabs{{display:flex;gap:7px;flex-wrap:wrap;margin:10px 0 2px}} .viewTab{{border:1px solid var(--line);border-radius:999px;padding:7px 11px;background:var(--panel)}} .viewTab.active{{border-color:var(--accent);background:var(--chip);font-weight:650}}
.chip{{border:1px solid var(--line);border-radius:999px;padding:7px 11px;background:var(--panel)}} .chip.active{{border-color:var(--accent);background:var(--chip);font-weight:650}}
.loyaltyBox{{margin:10px 0;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:10px 12px}} .loyaltyHead{{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:7px}} .loyaltyTitle{{font-weight:700}} .loyaltyActions{{display:flex;gap:6px}} .loyaltyActions button{{padding:5px 9px;font-size:12px}} .loyaltyPrograms{{display:flex;flex-wrap:wrap;gap:7px 12px}} .loyaltyPrograms label{{display:flex;align-items:center;gap:6px;cursor:pointer}} .loyaltyPrograms input{{padding:0}} .loyaltyNote{{margin-top:7px;color:var(--muted);font-size:13px}}
.stats{{display:flex;gap:14px;flex-wrap:wrap;color:var(--muted);margin:10px 0}} details{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:9px 12px;margin:10px 0}}
.table{{background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden;box-shadow:var(--shadow)}} .row{{display:grid;grid-template-columns:72px 125px minmax(260px,2fr) 105px 145px minmax(150px,1fr) 120px;gap:12px;align-items:center;padding:10px 12px;border-top:1px solid var(--line)}} .table.single-retailer .row{{grid-template-columns:72px minmax(260px,2fr) 105px 145px minmax(150px,1fr) 120px}} .table.single-retailer .retailer{{display:none}}
.row.head{{font-weight:700;border-top:0;color:var(--muted);background:color-mix(in srgb,var(--panel) 88%,var(--bg))}} .thumb{{width:60px;height:60px;object-fit:contain;border-radius:8px;background:#fff}} .price{{font-size:17px;font-weight:750}} .price.best{{color:var(--good)}} .selectedPrice.saving{{color:var(--good)}} .product{{font-weight:650}} .small{{font-size:13px;color:var(--muted)}} .priceNote{{margin-top:3px;max-width:180px;white-space:normal}} .savingText{{color:var(--good);font-size:13px;font-weight:650}}
#sentinel{{text-align:center;color:var(--muted);padding:22px}} .error{{color:#b42318}} a{{color:var(--accent)}}
@media(max-width:980px){{.controls{{grid-template-columns:1fr 1fr}} .controls input{{grid-column:1/-1}} .row.head{{display:none}} .row{{grid-template-columns:64px 1fr 105px;align-items:start}} .table.single-retailer .row{{grid-template-columns:64px 1fr 105px}} .row .retailer{{grid-column:2}} .row .productblock{{grid-column:2/-1}} .row .regularPrice{{grid-column:3;grid-row:1}} .row .selectedPrice{{grid-column:3;grid-row:2}} .row .details{{grid-column:2/-1}} .row .validity{{grid-column:2/-1}}}}
</style>
</head>
<body><div class="wrap">
<div class="top"><div class="titlebar"><h1>Supermarkt-Preisvergleich</h1><a class="newSearch" href="/">Neue Suche</a></div><div class="meta" id="meta">Lade gespeicherten Vergleich …</div>
<div class="controls"><input id="q" type="search" placeholder="Produkt oder Marke filtern"><select id="sort"><option value="price">Preis mit Auswahl</option><option value="unit_price">Grundpreis mit Auswahl</option><option value="retailer">Händler</option><option value="product">Produktname</option></select></div><div class="viewTabs" role="tablist" aria-label="Dubletten"><button type="button" class="viewTab active" id="viewBest" data-view="best_only" role="tab" aria-selected="true">Günstigste</button><button type="button" class="viewTab" id="viewAll" data-view="all" role="tab" aria-selected="false">Teurere Dubletten einblenden</button></div>
<div class="loyaltyBox" id="loyaltyBox" hidden><div class="loyaltyHead"><div class="loyaltyTitle">Bonusprogramme</div><div class="loyaltyActions"><button type="button" id="loyaltyAll">Alle</button><button type="button" id="loyaltyNone">Keine</button></div></div><div class="loyaltyPrograms" id="loyaltyPrograms"></div><div class="loyaltyNote" id="loyaltyNote"></div></div>
<div class="chips" id="chips"></div><div class="stats" id="stats"></div></div>
<details id="warningsBox" hidden><summary>Hinweise oder Fehler</summary><div id="warnings"></div></details>
<div class="table" id="table"><div class="row head"><div>Bild</div><div class="retailer">Händler</div><div>Produkt</div><div>Ohne Bonus</div><div>Mit Auswahl</div><div>Packung / Grundpreis</div><div>Gültig</div></div><div id="rows"></div></div>
<div id="sentinel">Lade Angebote …</div></div>
<script>
const searchId={sid}, token={token}; let page=1, loading=false, done=false, retailer="", view="best_only", debounce=null, programsInitialized=false, requestSeq=0, controller=null;
const selectedPrograms=new Set({selected});
const $=id=>document.getElementById(id); const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;","\\\"":"&quot;","'":"&#39;"}}[c]));
function syncLoyaltyUrl(){{const u=new URL(location.href); const value=[...selectedPrograms].sort().join(","); value?u.searchParams.set("loyalty",value):u.searchParams.delete("loyalty"); history.replaceState(null,"",u);}}
function query(reset=false){{if(reset){{requestSeq++;controller?.abort();loading=false;page=1;done=false;$("rows").innerHTML="";}} if(loading||done)return; loading=true; const seq=requestSeq; controller=new AbortController(); $("sentinel").textContent="Lade Angebote …"; const p=new URLSearchParams({{token,page:String(page),page_size:"100",q:$("q").value,retailer,sort:$("sort").value,view,loyalty:[...selectedPrograms].sort().join(",")}}); fetch(`/api/results/${{encodeURIComponent(searchId)}}?${{p}}`,{{cache:"no-store",signal:controller.signal}}).then(async r=>{{if(!r.ok)throw new Error((await r.json().catch(()=>({{}}))).detail||`HTTP ${{r.status}}`); return r.json();}}).then(data=>{{if(seq!==requestSeq)return;render(data,reset);page=data.page+1;done=!data.has_next;$("sentinel").textContent=done?"Alle passenden Angebote geladen.":"Weitere Angebote werden beim Scrollen geladen …";}}).catch(e=>{{if(e.name==="AbortError")return;$("sentinel").innerHTML=`<span class="error">${{esc(e.message)}}</span>`;done=true;}}).finally(()=>{{if(seq===requestSeq)loading=false;}});}}
function render(data,reset){{$(`table`).classList.toggle("single-retailer",Boolean(retailer)); $(`meta`).textContent=`PLZ ${{data.postal_code}} · ${{data.source_offer_count}} Quellen-Treffer · Cache ${{Math.floor(data.cache_age_seconds/60)}} Min. alt`; const hidden=Number(data.hidden_count||0); const duplicateText=view==="all"?`${{hidden}} teurere Dubletten eingeblendet`:`${{hidden}} teurere Dubletten ausgeblendet`; $(`stats`).innerHTML=`<span>${{data.filtered_offer_count}} passende Treffer</span><span>${{duplicateText}}</span>`; $("viewBest").classList.toggle("active",view==="best_only");$("viewBest").setAttribute("aria-selected",String(view==="best_only"));$("viewAll").classList.toggle("active",view==="all");$("viewAll").setAttribute("aria-selected",String(view==="all"));$("viewAll").textContent=hidden?`Teurere Dubletten einblenden · ${{hidden}}`:"Teurere Dubletten einblenden"; renderChips(data.retailer_counts); renderPrograms(data.available_loyalty_programs||[],data.loyalty_note||""); const warnings=data.warnings||[]; $(`warningsBox`).hidden=!warnings.length; $(`warnings`).innerHTML=warnings.map(x=>`<div>${{esc(x)}}</div>`).join(""); const frag=document.createDocumentFragment(); for(const o of data.offers){{const row=document.createElement("div");row.className="row"; const img=o.image_url?`<img class="thumb" loading="lazy" src="${{esc(o.image_url)}}" onerror="this.style.visibility='hidden'">`:`<div class="thumb"></div>`; const source=o.source_url?`<a href="${{esc(o.source_url)}}" target="_blank" rel="noreferrer">${{esc(o.product)}}</a>`:esc(o.product); const saved=(o.loyalty_savings||0)>0.004; const selectedInfo=[o.loyalty_benefit,saved?`spart ${{o.loyalty_savings_text}}`:""].filter(Boolean).map(esc).join(" · "); const selectedUnit=o.selected_unit_price?`<div class="small">entspricht ${{esc(o.selected_unit_price)}}</div>`:""; const checkoutDiff=saved&&Math.abs((o.checkout_price??o.regular_price)-(o.effective_price??o.regular_price))>0.004?`<div class="small">${{esc(o.checkout_price_text)}} an der Kasse</div>`:""; const regularNote=o.regular_comparison?`<div class="small priceNote">${{esc(o.regular_comparison)}}</div>`:""; const selectedNote=o.selected_comparison?`<div class="small priceNote">${{esc(o.selected_comparison)}}</div>`:""; row.innerHTML=`<div>${{img}}</div><div class="retailer"><strong>${{esc(o.retailer)}}</strong></div><div class="productblock"><div class="product">${{source}}</div><div class="small">${{esc(o.description)}}</div></div><div class="regularPrice price ${{esc(o.regular_comparison_state)}}">${{esc(o.regular_price_text)}}${{regularNote}}</div><div class="selectedPrice price ${{esc(o.selected_comparison_state)}}${{saved?" saving":""}}">${{esc(o.effective_price_text)}}${{checkoutDiff}}${{selectedUnit}}${{selectedInfo?`<div class="${{saved?"savingText":"small"}}">${{selectedInfo}}</div>`:""}}${{selectedNote}}</div><div class="details"><div>${{esc(o.pack)}}</div><div class="small">${{esc(o.unit_price)}}</div></div><div class="validity small">${{esc(o.validity)}}</div>`; frag.appendChild(row);}} $("rows").appendChild(frag);}}
function renderChips(counts){{const box=$("chips"); const entries=Object.entries(counts||{{}}); box.innerHTML=""; const add=(name,count)=>{{const b=document.createElement("button");b.className="chip"+(retailer===name?" active":"");b.textContent=name?`${{name}} · ${{count}}`:`Alle Händler · ${{entries.reduce((a,[,n])=>a+n,0)}}`;b.onclick=()=>{{retailer=name;query(true)}};box.appendChild(b)}}; add("",0); entries.sort((a,b)=>a[0].localeCompare(b[0],"de")).forEach(([n,c])=>add(n,c));}}
function renderPrograms(programs,note){{const box=$("loyaltyBox"), list=$("loyaltyPrograms"); box.hidden=!programs.length; $("loyaltyNote").textContent=note; if(programsInitialized)return; programsInitialized=true; list.innerHTML=""; for(const program of programs){{const label=document.createElement("label"); const input=document.createElement("input"); input.type="checkbox"; input.dataset.program=program.id; input.checked=selectedPrograms.has(program.id); input.onchange=()=>{{input.checked?selectedPrograms.add(program.id):selectedPrograms.delete(program.id);syncLoyaltyUrl();query(true)}}; const text=document.createElement("span"); text.textContent=program.label; const count=Number(program.priced_offer_count||0); label.title=(program.note||"")+(count?` · Aktuell ${{count}} Angebote mit konkret beziffertem Vorteil.`:" · Im aktuellen Abruf ist kein konkreter Euro-Preisvorteil ausgewiesen."); label.append(input,text); list.appendChild(label);}} $("loyaltyAll").onclick=()=>{{for(const input of list.querySelectorAll("input[data-program]")){{input.checked=true;selectedPrograms.add(input.dataset.program)}}syncLoyaltyUrl();query(true)}}; $("loyaltyNone").onclick=()=>{{for(const input of list.querySelectorAll("input[data-program]"))input.checked=false;selectedPrograms.clear();syncLoyaltyUrl();query(true)}};}}
$("q").addEventListener("input",()=>{{clearTimeout(debounce);debounce=setTimeout(()=>query(true),300)}}); $("sort").addEventListener("change",()=>query(true)); document.querySelectorAll(".viewTab").forEach(button=>button.addEventListener("click",()=>{{view=button.dataset.view||"best_only";query(true)}}));
new IntersectionObserver(e=>{{if(e.some(x=>x.isIntersecting))query(false)}},{{rootMargin:"600px"}}).observe($("sentinel")); query(true);
</script></body></html>"""
