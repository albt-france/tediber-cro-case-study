"""Self-contained interactive dashboard (one HTML file, Plotly embedded, works offline): dashboard/cro_dashboard.html

Tabs: (1) Weekly overview, (2) Funnel & segments (filters), (3) Anomalies, (4) Experiments (+ live calculator),
(5) Real GA4 funnel (PUBLIC DATA, Google Merchandise Store - not Tediber). The same CSVs in data/processed/ can feed
a Looker Studio report.
    python src/build_dashboard.py
"""
import json
from pathlib import Path

import pandas as pd
from plotly.offline import get_plotlyjs

ROOT = Path(__file__).resolve().parents[1]
PROC, OUT = ROOT / "data" / "processed", ROOT / "dashboard" / "cro_dashboard.html"


def rec(name, cols=None, q=None):
    d = pd.read_csv(PROC / f"{name}.csv")
    if q is not None:
        d = d.query(q)
    if cols:
        d = d[cols]
    return json.loads(d.round(6).to_json(orient="records", date_format="iso"))


def data():
    promos = pd.read_parquet(ROOT / "data" / "sim" / "promo_calendar.parquet")
    return {
        "weekly": rec("weekly_kpis", ["week_start", "dimension", "segment", "sessions", "orders", "revenue_eur",
                                      "conversion_rate", "conversion_per_user", "aov_eur", "revenue_per_visit_eur",
                                      "net_revenue_per_visit_eur", "add_to_cart_rate", "checkout_abandonment",
                                      "conversion_rate_wow", "sessions_wow", "rpv_wow", "aov_wow"]),
        "cube": rec("funnel_cube_monthly"),
        "series": rec("anomaly_series", ["slice", "kpi", "d", "rate", "expected", "flagged", "win_promo"]),
        "incidents": rec("anomaly_incidents", ["slice", "kpi", "first_day", "last_day", "rel_change_at_peak",
                                               "z_at_peak", "status", "candidate_releases"]),
        "mix": rec("mix_decomposition"),
        "recon": rec("reconciliation_daily", ["d", "revenue_ratio_7d", "duplicate_share_7d"]),
        "tests": rec("experiment_readout"),
        "peek": rec("peeking"),
        "ga4": rec("ga4_funnel_segments"),
        "ga4dq": rec("ga4_data_quality"),
        "ga4dedup": rec("ga4_revenue_dedup"),
        "promos": [{"name": r.promo, "a": str(r.start_date.date()), "b": str(r.end_date.date())} for r in promos.itertuples()],
    }


HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CRO dashboard - DTC bedding case study</title>
<style>
:root { color-scheme: light; --bg:#F2EFE9; --card:#FFFFFF; --line:#E1DDD4; --ink:#1F1F1D; --muted:#5E5C57; --accent:#2A78D6; --bad:#C2413A; --ok:#2E8B57; --exp:#9A9890;
  --pub:#E3EEFB; --pubt:#1C5CAB; --sim:#FBE9E0; --simt:#9A3B12; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { color-scheme: dark; --bg:#161615; --card:#1F1F1D; --line:#34332F; --ink:#F0EFEC; --muted:#C3C2B7; --accent:#4A93EA; --bad:#E5655D; --ok:#4FB07A; --exp:#8B8980; --pub:#1C2E45; --pubt:#9CC3F2; --sim:#40261A; --simt:#F2B89C; } }
:root[data-theme="dark"] { color-scheme: dark; --bg:#161615; --card:#1F1F1D; --line:#34332F; --ink:#F0EFEC; --muted:#C3C2B7; --accent:#4A93EA; --bad:#E5655D; --ok:#4FB07A; --exp:#8B8980; --pub:#1C2E45; --pubt:#9CC3F2; --sim:#40261A; --simt:#F2B89C; }
* { box-sizing:border-box; } body { margin:0; font-family:'Segoe UI', Arial, sans-serif; background:var(--bg); color:var(--ink); }
.wrap { max-width:1280px; margin:0 auto; padding:20px 16px 40px; }
h1 { font-size:24px; margin:0 0 4px; } .sub { color:var(--muted); margin:0 0 14px; font-size:14px; }
nav { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:12px; }
nav button { border:1px solid var(--line); background:var(--card); color:var(--ink); padding:7px 12px; border-radius:6px; cursor:pointer; font:inherit; font-size:14px; }
nav button.on { border-color:var(--accent); color:var(--accent); font-weight:600; }
.tab { display:none; } .tab.on { display:block; }
.grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(340px, 1fr)); gap:12px; }
.tiles { display:grid; grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); gap:10px; margin-bottom:12px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:12px 14px; min-width:0; }
.card h2 { font-size:15px; margin:0 0 6px; } .card p { font-size:13px; color:var(--muted); margin:4px 0; }
.tile .k { font-size:12px; color:var(--muted); } .tile .v { font-size:24px; font-weight:700; margin:2px 0; } .tile .d { font-size:12px; }
.up { color:var(--ok); } .down { color:var(--bad); }
.tag { font-size:11px; font-weight:700; letter-spacing:.06em; padding:3px 7px; border-radius:4px; margin-left:6px; vertical-align:middle; }
.pub { background:var(--pub); color:var(--pubt); } .sim { background:var(--sim); color:var(--simt); }
.ctrl { display:flex; gap:12px; flex-wrap:wrap; align-items:center; margin:6px 0 10px; font-size:13px; color:var(--muted); }
select, input { font:inherit; font-size:13px; padding:4px 6px; border:1px solid var(--line); border-radius:5px; background:var(--card); color:var(--ink); }
input[type=number] { width:90px; }
.tblwrap { overflow-x:auto; } table { border-collapse:collapse; width:100%; font-size:13px; }
th, td { text-align:left; padding:4px 6px; border-bottom:1px solid var(--line); vertical-align:top; } th { color:var(--muted); font-weight:600; }
.plot { width:100%; height:340px; } footer { margin-top:18px; font-size:12px; color:var(--muted); }
</style></head><body><div class="wrap">
<h1>CRO dashboard · DTC bedding store</h1>
<p class="sub">Companion to the case study "Tediber: finding where the mattress funnel leaks". Tabs 1-4 use a <b>simulated</b> store modelled on public information (not Tediber's data); tab 5 uses <b>real public</b> GA4 data from another store.</p>
<nav id="nav"><button data-t="t1" class="on">Weekly overview</button><button data-t="t2">Funnel &amp; segments</button><button data-t="t3">Anomalies</button><button data-t="t4">Experiments</button><button data-t="t5">Real GA4 funnel</button></nav>

<section id="t1" class="tab on">
 <div class="ctrl">Week starting <select id="wk"></select> Segment <select id="wseg"></select><span class="tag sim">SIMULATED</span></div>
 <div class="tiles" id="tiles"></div>
 <div class="grid"><div class="card"><h2>Conversion rate per session, weekly</h2><div id="p_cr" class="plot"></div><p>Shaded: promotions (sales, Black Month). Compare promo weeks with last year's promo, not with the week before.</p></div>
 <div class="card"><h2>Sessions and revenue per visit (gross vs net of returns)</h2><div id="p_rpv" class="plot"></div><p>Net revenue of recent weeks looks high: most 100-night returns are not visible yet.</p></div></div>
</section>

<section id="t2" class="tab">
 <div class="ctrl">Device <select id="fdev"></select> Channel <select id="fch"></select> Visitor <select id="fvt"></select> Entry category <select id="fcat"></select> From <select id="fm1"></select> to <select id="fm2"></select><span class="tag sim">SIMULATED</span></div>
 <div class="grid"><div class="card"><h2>Funnel (sessions reaching each step)</h2><div id="p_fun" class="plot"></div></div>
 <div class="card"><h2>Step pass rates - selection vs all traffic</h2><div id="p_pass" class="plot"></div><p>Pick "Bed base &amp; bed" or "Sofa": the shipping step loses twice as many shoppers (delivery fee appears at checkout).</p></div></div>
</section>

<section id="t3" class="tab">
 <div class="ctrl">Series <select id="aser"></select><span class="tag sim">SIMULATED</span></div>
 <div class="grid"><div class="card"><h2 id="a_title">Rate vs expected</h2><div id="p_an" class="plot"></div><p>Expected = median of the same weekday over 8 weeks (promotion windows excluded; inside a promotion, last year's promotion). Red = flagged days.</p></div>
 <div class="card"><h2>Traffic mix in Sep 2026: rate effect vs mix effect</h2><div id="p_mix" class="plot"></div><p>Topline conversion fell, yet conversion inside each channel barely moved: the drop comes from more paid-social visits. No incident opened.</p></div>
 <div class="card"><h2>Analytics revenue / shop revenue (7 days)</h2><div id="p_rec" class="plot"></div><p>Above 100 % = purchases counted twice (tag migrated 7 Jul, fixed 4 Aug). Rule: de-duplicate on transaction id.</p></div>
 <div class="card"><h2>Incident log</h2><div class="tblwrap"><table id="inc"></table></div></div></div>
</section>

<section id="t4" class="tab">
 <div class="grid"><div class="card"><h2>Results with 95 % intervals<span class="tag sim">SIMULATED</span></h2><div id="p_tests" class="plot"></div><p>Primary KPI vs net revenue per visitor (bootstrap). Test B is not read: sample ratio mismatch.</p></div>
 <div class="card"><h2>Decisions</h2><div class="tblwrap"><table id="tt"></table></div></div>
 <div class="card"><h2>Why not stop early: A/A test checked every day</h2><div id="p_peek" class="plot"></div><p>No real difference, yet stopping at the first p &lt; 0.05 "finds" a winner in about 1 test out of 4.</p></div>
 <div class="card"><h2>Sample size calculator</h2>
  <div class="ctrl">Baseline <input id="c_p" type="number" step="0.001" value="0.016"> MDE (relative) <input id="c_m" type="number" step="0.01" value="0.08"> Visitors/day <input id="c_v" type="number" value="6000"></div>
  <div class="ctrl">alpha 5 %, power 80 %, two variants</div><div id="c_out" class="big" style="font-size:20px;font-weight:700"></div></div></div>
</section>

<section id="t5" class="tab">
 <div class="ctrl">Split by <select id="gdim"></select><span class="tag pub">PUBLIC DATA</span><span style="font-size:12px">Google Merchandise Store GA4 sample, 1 Nov 2020 - 31 Jan 2021 - not Tediber</span></div>
 <div class="grid"><div class="card"><h2>Real funnel: sessions reaching each step</h2><div id="p_g" class="plot"></div></div>
 <div class="card"><h2>Conversion and checkout abandonment by segment</h2><div id="p_g2" class="plot"></div></div>
 <div class="card"><h2>Data-quality checks on the real export</h2><div class="tblwrap"><table id="gdq"></table></div></div></div>
</section>
<footer>Independent case study based on public data · not affiliated with or endorsed by Tediber. Data: data/processed/*.csv (the same files can feed a Looker Studio report).</footer>
</div>
<script>__PLOTLY__</script>
<script>
const D = __DATA__;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const C = () => ({ink:css('--ink'), muted:css('--muted'), line:css('--line'), acc:css('--accent'), bad:css('--bad'), ok:css('--ok'), exp:css('--exp'), card:css('--card')});
const lay = (o={}) => { const c=C(); return Object.assign({margin:{l:56,r:16,t:10,b:40}, paper_bgcolor:c.card, plot_bgcolor:c.card, font:{family:'Segoe UI, Arial', size:12, color:c.ink},
  xaxis:{gridcolor:c.line, zerolinecolor:c.line}, yaxis:{gridcolor:c.line, zerolinecolor:c.line}, legend:{orientation:'h', y:-0.18}, showlegend:true}, o); };
const cfg = {displaylogo:false, responsive:true, modeBarButtonsToRemove:['lasso2d','select2d']};
const pct = (x,d=2) => (x==null||isNaN(x))?'-':(100*x).toFixed(d)+'%';
const sgn = (x,d=1) => (x==null||isNaN(x))?'-':(x>=0?'+':'')+(100*x).toFixed(d)+'%';
const eur = x => '€'+x.toFixed(2);
const fill = (sel, vals, def) => { const s=document.getElementById(sel); s.innerHTML = vals.map(v=>`<option${v===def?' selected':''}>${v}</option>`).join(''); };
const promoShapes = () => D.promos.map(p => ({type:'rect', xref:'x', yref:'paper', x0:p.a, x1:p.b, y0:0, y1:1, fillcolor:C().exp, opacity:0.15, line:{width:0}}));

// ---------- tab 1
const weeks = [...new Set(D.weekly.map(r=>r.week_start.slice(0,10)))].sort();
fill('wk', weeks, '2026-03-16');
fill('wseg', ['All','mobile','desktop','tablet','Mattress','Bed base & bed','Pillow & duvet','Paid social','Organic search','New','Returning'], 'All');
function segRows(seg){ return D.weekly.filter(r => seg==='All' ? r.dimension==='All' : r.segment===seg).sort((a,b)=>a.week_start<b.week_start?-1:1); }
function drawWeekly(){
  const seg = wseg.value, rows = segRows(seg), w = wk.value, i = rows.findIndex(r=>r.week_start.slice(0,10)===w), r = rows[i], p = rows[i-1]||{};
  const t = [['Sessions', r.sessions.toLocaleString('en'), r.sessions_wow],['Conversion / session', pct(r.conversion_rate), r.conversion_rate_wow],
    ['Conversion / user', pct(r.conversion_per_user), p.conversion_per_user? r.conversion_per_user/p.conversion_per_user-1 : null],
    ['Average order value', '€'+Math.round(r.aov_eur), r.aov_wow],['Revenue / visit (gross)', eur(r.revenue_per_visit_eur), r.rpv_wow],
    ['Revenue / visit (net)', eur(r.net_revenue_per_visit_eur), p.net_revenue_per_visit_eur? r.net_revenue_per_visit_eur/p.net_revenue_per_visit_eur-1:null],
    ['Add-to-cart rate', pct(r.add_to_cart_rate), p.add_to_cart_rate? r.add_to_cart_rate/p.add_to_cart_rate-1:null],
    ['Checkout abandonment', pct(r.checkout_abandonment,1), p.checkout_abandonment!=null? r.checkout_abandonment-p.checkout_abandonment:null, true]];
  tiles.innerHTML = t.map(([k,v,d,pts]) => { const good = pts ? d<=0 : d>=0; const txt = d==null?'':(pts?((d>=0?'+':'')+(100*d).toFixed(2)+' pp'):sgn(d))+' wow';
    return `<div class="card tile"><div class="k">${k}</div><div class="v">${v}</div><div class="d ${d==null?'':(good?'up':'down')}">${txt}</div></div>`; }).join('');
  const x = rows.map(r=>r.week_start.slice(0,10));
  Plotly.react('p_cr', [{x, y:rows.map(r=>r.conversion_rate), name:'conversion per session', line:{color:C().acc}},
    {x:[w], y:[r.conversion_rate], mode:'markers', marker:{size:11, color:C().bad}, name:'selected week'}],
    lay({yaxis:{tickformat:'.2%', gridcolor:C().line}, shapes:promoShapes()}), cfg);
  Plotly.react('p_rpv', [{x, y:rows.map(r=>r.revenue_per_visit_eur), name:'RPV gross (€)', line:{color:C().acc}},
    {x, y:rows.map(r=>r.net_revenue_per_visit_eur), name:'RPV net of returns (€)', line:{color:C().ok}},
    {x, y:rows.map(r=>r.sessions), name:'sessions', yaxis:'y2', type:'bar', marker:{color:C().exp}, opacity:0.35}],
    lay({margin:{l:56,r:56,t:10,b:40}, yaxis:{title:'€ per visit', gridcolor:C().line}, yaxis2:{overlaying:'y', side:'right', showgrid:false, title:'sessions'}, shapes:promoShapes()}), cfg);
}
wk.onchange = wseg.onchange = drawWeekly;

// ---------- tab 2
const uniq = k => ['All', ...[...new Set(D.cube.map(r=>r[k]))].sort()];
fill('fdev', uniq('device'), 'All'); fill('fch', uniq('channel'), 'All'); fill('fvt', uniq('visitor_type'), 'All'); fill('fcat', uniq('entry_category'), 'All');
const months = [...new Set(D.cube.map(r=>r.month.slice(0,7)))].sort(); fill('fm1', months, months[0]); fill('fm2', months, months[months.length-1]);
const STEPS = [['sessions','Sessions'],['product_views','Product view'],['add_to_cart','Add to cart'],['checkout_starts','Checkout'],['shipping_completed','Shipping'],['payment_completed','Payment'],['orders','Order']];
function agg(f){ const s = Object.fromEntries(STEPS.map(([k])=>[k,0])); D.cube.forEach(r => { if (f(r)) STEPS.forEach(([k])=> s[k]+=r[k]); }); return s; }
function drawFunnel(){
  const m1=fm1.value, m2=fm2.value, inRange = r => r.month.slice(0,7)>=m1 && r.month.slice(0,7)<=m2;
  const sel = agg(r => inRange(r) && [['device',fdev],['channel',fch],['visitor_type',fvt],['entry_category',fcat]].every(([k,e]) => e.value==='All' || r[k]===e.value));
  const all = agg(inRange);
  Plotly.react('p_fun', [{type:'funnel', y:STEPS.map(s=>s[1]), x:STEPS.map(([k])=>sel[k]), textinfo:'value+percent initial', marker:{color:C().acc}}], lay({margin:{l:100,r:16,t:10,b:30}, showlegend:false}), cfg);
  const lab = STEPS.slice(1).map(s=>s[1]); const pr = s => STEPS.slice(1).map(([k],i)=> s[k]/s[STEPS[i][0]]);
  Plotly.react('p_pass', [{type:'bar', x:lab, y:pr(sel), name:'selection', marker:{color:C().acc}}, {type:'bar', x:lab, y:pr(all), name:'all traffic', marker:{color:C().exp}}],
    lay({yaxis:{tickformat:'.0%', gridcolor:C().line}, barmode:'group'}), cfg);
}
[fdev,fch,fvt,fcat,fm1,fm2].forEach(e => e.onchange = drawFunnel);

// ---------- tab 3
const series = [...new Set(D.series.map(r=>r.slice+' | '+r.kpi))];
fill('aser', series, 'mobile / Safari iOS | payment step');
function drawAnom(){
  const [sl,kpi] = aser.value.split(' | '); const rows = D.series.filter(r=>r.slice===sl && r.kpi===kpi); const x = rows.map(r=>r.d.slice(0,10));
  a_title.textContent = sl+' · '+kpi+' (7-day rate) vs expected';
  const fl = rows.filter(r=>r.flagged);
  Plotly.react('p_an', [{x, y:rows.map(r=>r.rate), name:'observed', line:{color:C().acc}}, {x, y:rows.map(r=>r.expected), name:'expected', line:{color:C().exp, dash:'dot'}},
    {x:fl.map(r=>r.d.slice(0,10)), y:fl.map(r=>r.rate), mode:'markers', name:'flagged', marker:{color:C().bad, size:6}}],
    lay({yaxis:{tickformat:'.1%', gridcolor:C().line}, shapes:promoShapes()}), cfg);
}
aser.onchange = drawAnom;
function drawStatic3(){
  const m = D.mix.filter(r=>r.first_day.slice(0,10)===D.mix[0].first_day.slice(0,10));
  Plotly.react('p_mix', [{type:'bar', x:m.map(r=>r.channel), y:m.map(r=>100*r.rate_effect), name:'rate effect (pp)', marker:{color:C().acc}},
    {type:'bar', x:m.map(r=>r.channel), y:m.map(r=>100*r.mix_effect), name:'mix effect (pp)', marker:{color:C().bad}}],
    lay({barmode:'group', yaxis:{title:'contribution to topline change (pp)', gridcolor:C().line}}), cfg);
  const x = D.recon.map(r=>r.d.slice(0,10));
  Plotly.react('p_rec', [{x, y:D.recon.map(r=>r.revenue_ratio_7d), name:'analytics / shop revenue', line:{color:C().acc}},
    {x:[x[0],x[x.length-1]], y:[1,1], name:'100 %', line:{color:C().bad, dash:'dash'}}], lay({yaxis:{tickformat:'.0%', gridcolor:C().line}}), cfg);
  inc.innerHTML = '<tr><th>From</th><th>To</th><th>Slice</th><th>KPI</th><th>vs expected</th><th>Status</th><th>Releases before</th></tr>' +
    D.incidents.map(r=>`<tr><td>${r.first_day.slice(0,10)}</td><td>${r.last_day.slice(0,10)}</td><td>${r.slice}</td><td>${r.kpi}</td><td>${sgn(r.rel_change_at_peak)}</td><td>${r.status}</td><td>${r.candidate_releases||''}</td></tr>`).join('');
}

// ---------- tab 4
function drawTests(){
  const T = D.tests, y = T.map(t=>t.test_id+' · '+t.test_name.slice(0,28));
  const tr = (k, lo, hi, name, col, off) => ({x:T.map(t=>t[k]), y:y.map(v=>v), error_x:{type:'data', symmetric:false, array:T.map(t=>t[hi]-t[k]), arrayminus:T.map(t=>t[k]-t[lo]), color:col},
     mode:'markers', marker:{size:10, color:col, symbol:off?'diamond':'circle'}, name, type:'scatter'});
  Plotly.react('p_tests', [tr('primary_lift','primary_ci_low','primary_ci_high','primary KPI', C().acc), tr('rpv_net_lift','rpv_net_ci_low','rpv_net_ci_high','net revenue / visitor', C().ok, 1)],
    lay({margin:{l:220,r:16,t:10,b:40}, xaxis:{tickformat:'+.0%', zeroline:true, zerolinecolor:C().ink, gridcolor:C().line}, yaxis:{autorange:'reversed'}}), cfg);
  tt.innerHTML = '<tr><th>Test</th><th>Variant share</th><th>Primary</th><th>Net RPV</th><th>Returns ctl/var</th><th>Decision</th></tr>' +
    T.map(t=>`<tr><td>${t.test_id} · ${t.test_name}</td><td>${pct(t.variant_share)}</td><td>${sgn(t.primary_lift)} (p ${t.primary_p_value.toFixed(4)})</td><td>${sgn(t.rpv_net_lift)}</td><td>${pct(t.return_rate_control,1)} / ${pct(t.return_rate_variant,1)}</td><td><b>${t.decision}</b></td></tr>`).join('');
  Plotly.react('p_peek', [{x:D.peek.map(r=>r.day), y:D.peek.map(r=>r.false_positive_if_stopped_at_first_win), name:'stop at first p<0.05', line:{color:C().bad}},
    {x:D.peek.map(r=>r.day), y:D.peek.map(r=>r.false_positive_fixed_horizon), name:'read once at the end', line:{color:C().ok, dash:'dash'}}],
    lay({xaxis:{title:'days run', gridcolor:C().line}, yaxis:{tickformat:'.0%', title:'false positives', gridcolor:C().line}}), cfg);
}
function qnorm(p){ // Acklam's inverse normal
  const a=[-39.6968302866538,220.946098424521,-275.928510446969,138.357751867269,-30.6647980661472,2.50662827745924],b=[-54.4760987982241,161.585836858041,-155.698979859887,66.8013118877197,-13.2806815528857],
  c=[-0.00778489400243029,-0.322396458041136,-2.40075827716184,-2.54973253934373,4.37466414146497,2.93816398269878],d=[0.00778469570904146,0.32246712907004,2.445134137143,3.75440866190742];
  const pl=0.02425; let q,r; if(p<pl){q=Math.sqrt(-2*Math.log(p));return(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1);}
  if(p>1-pl){q=Math.sqrt(-2*Math.log(1-p));return-(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5])/((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1);}
  q=p-0.5;r=q*q;return(((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q/(((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1); }
function calc(){ const p1=+c_p.value, p2=p1*(1+ +c_m.value), z=qnorm(0.975)+qnorm(0.8); const n=Math.ceil(z*z*(p1*(1-p1)+p2*(1-p2))/((p2-p1)**2));
  const days=Math.ceil(2*n/+c_v.value/7)*7; c_out.textContent = `${n.toLocaleString('en')} visitors per variant · ${days} days`; }
[c_p,c_m,c_v].forEach(e=>e.oninput=calc);

// ---------- tab 5
fill('gdim', [...new Set(D.ga4.map(r=>r.dimension))], 'Device');
function drawGA4(){
  const rows = D.ga4.filter(r=>r.dimension===gdim.value); const st=[['sessions','Session'],['view_item','View item'],['add_to_cart','Add to cart'],['begin_checkout','Begin checkout'],['add_shipping_info','Shipping info'],['add_payment_info','Payment info'],['purchase','Purchase']];
  const pal=[C().acc,C().bad,C().ok,C().exp,'#B07AA1','#EDA100'];
  Plotly.react('p_g', rows.map((r,i)=>({type:'scatter', mode:'lines+markers', x:st.map(s=>s[1]), y:st.map(([k])=>r[k]/r.sessions), name:r.segment, line:{color:pal[i%pal.length]}})),
    lay({yaxis:{type:'log', tickformat:'.1%', title:'share of sessions (log)', gridcolor:C().line}}), cfg);
  Plotly.react('p_g2', [{type:'bar', x:rows.map(r=>r.segment), y:rows.map(r=>r.conversion_rate), name:'conversion per session', marker:{color:C().acc}},
    {type:'bar', x:rows.map(r=>r.segment), y:rows.map(r=>r.checkout_abandonment), name:'checkout abandonment', marker:{color:C().exp}, yaxis:'y2'}],
    lay({barmode:'group', yaxis:{tickformat:'.1%', gridcolor:C().line}, yaxis2:{overlaying:'y', side:'right', tickformat:'.0%', showgrid:false}}), cfg);
  gdq.innerHTML = '<tr><th>Check</th><th>Value</th></tr>' + D.ga4dq.map(r=>`<tr><td>${r.check_name}</td><td>${r.unit==='share'?pct(r.value,1):Math.round(r.value).toLocaleString('en')}</td></tr>`).join('') +
    `<tr><td>revenue inflation if purchases are not de-duplicated on transaction id</td><td>${sgn(D.ga4dedup[0].inflation_share)}</td></tr>`;
}
gdim.onchange = drawGA4;

function all(){ drawWeekly(); drawFunnel(); drawAnom(); drawStatic3(); drawTests(); calc(); drawGA4(); }
document.querySelectorAll('#nav button').forEach(b => b.onclick = () => {
  document.querySelectorAll('#nav button').forEach(x=>x.classList.toggle('on', x===b));
  document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('on', t.id===b.dataset.t));
  document.querySelectorAll('#'+b.dataset.t+' .js-plotly-plot').forEach(el => Plotly.Plots.resize(el));
});
all();
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', all);
</script></body></html>"""


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    html = HTML.replace("__PLOTLY__", get_plotlyjs()).replace("__DATA__", json.dumps(data(), ensure_ascii=False))
    OUT.write_text(html, encoding="utf-8")
    print(f"written {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
