"""Self-contained HTML dashboard (no CDN, no build step): all data embedded as JSON, rendered with vanilla JS/SVG."""

from __future__ import annotations

import json
from typing import Any

TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>World Emblem Data Foundation | Showcase</title><style>
:root{--bg:#0b1220;--panel:#121b2e;--ink:#e6edf7;--mut:#8fa1bd;--acc:#4cc9f0;--ok:#3ddc97;--warn:#ffb703;--bad:#ff5d73;--line:#23314d}
*{box-sizing:border-box}body{margin:0;font:14px/1.5 system-ui,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink);display:flex;min-height:100vh}
nav{width:230px;background:#0e1626;border-right:1px solid var(--line);padding:16px 10px;position:sticky;top:0;height:100vh;overflow:auto}
nav h1{font-size:15px;margin:0 6px 4px;color:var(--acc)}nav small{display:block;color:var(--mut);margin:0 6px 14px}
nav a{display:block;padding:7px 10px;border-radius:8px;color:var(--mut);cursor:pointer;text-decoration:none}nav a.on,nav a:hover{background:var(--panel);color:var(--ink)}
main{flex:1;padding:22px 28px;max-width:1280px}h2{margin:0 0 4px}p.lead{color:var(--mut);margin:0 0 18px}
.grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}
.kpi b{font-size:26px;display:block}.kpi span{color:var(--mut);font-size:12px}table{width:100%;border-collapse:collapse;background:var(--panel);border-radius:12px;overflow:hidden;margin:8px 0 18px}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--mut);font-weight:600;font-size:12px;text-transform:uppercase}
.pill{display:inline-block;padding:1px 8px;border-radius:99px;font-size:11px;font-weight:700}.ok{background:#12372b;color:var(--ok)}.bad{background:#40161f;color:var(--bad)}.warn{background:#41310a;color:var(--warn)}.info{background:#12303b;color:var(--acc)}
.bar{height:8px;background:var(--line);border-radius:6px;overflow:hidden}.bar i{display:block;height:100%;background:var(--acc)}code{background:#0b1426;padding:1px 6px;border-radius:6px;color:#9be7ff}
details{background:var(--panel);border:1px solid var(--line);border-radius:10px;margin:8px 0;padding:8px 12px}summary{cursor:pointer;font-weight:600}svg text{fill:var(--ink);font-size:11px}
ol,ul{margin:6px 0 6px 18px;padding:0}.sec{display:none}.sec.on{display:block}.mut{color:var(--mut)}
</style></head><body><nav><h1>World Emblem Data Foundation</h1><small>Senior Data Engineer showcase &middot; synthetic data</small><div id="nav"></div></nav><main id="main"></main>
<script>
const D=__DATA__;const $=(s)=>document.querySelector(s);
const esc=(v)=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pill=(t,k)=>`<span class="pill ${k}">${esc(t)}</span>`;const sev=(s)=>pill(s,{critical:'bad',high:'bad',error:'bad',medium:'warn',warning:'warn',low:'info',SEV1:'bad',SEV2:'warn',SEV3:'info'}[s]||'info');
const num=(v,d=0)=>v==null?'-':Number(v).toLocaleString(undefined,{maximumFractionDigits:d});
const table=(h,rows)=>`<table><thead><tr>${h.map(x=>`<th>${esc(x)}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map(c=>`<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
const bar=(p)=>`<div class="bar"><i style="width:${Math.max(0,Math.min(100,p||0))}%"></i></div>`;
const kpi=(v,l)=>`<div class="card kpi"><b>${v}</b><span>${l}</span></div>`;
function flowSvg(){const n=D.audit.flow_map.nodes,e=D.audit.flow_map.edges,W=900,H=470,cx=W/2,cy=H/2,R=185,pos={};
 n.forEach((x,i)=>{const a=2*Math.PI*i/n.length-Math.PI/2;pos[x.id]=[cx+R*1.75*Math.cos(a)*0.95,cy+R*1.05*Math.sin(a)]});
 const col={red:'#ff5d73',amber:'#ffb703',green:'#3ddc97'};
 let s=`<svg viewBox="0 0 ${W} ${H}" width="100%"><defs>${Object.entries(col).map(([k,c])=>`<marker id="m${k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10z" fill="${c}"/></marker>`).join('')}</defs>`;
 e.forEach((x,i)=>{const [a,b]=[pos[x.from],pos[x.to]];const mx=(a[0]+b[0])/2+(i%2?18:-18),my=(a[1]+b[1])/2+(i%2?14:-14);
  s+=`<path d="M${a[0]} ${a[1]} Q${mx} ${my} ${b[0]} ${b[1]}" stroke="${col[x.health]}" fill="none" stroke-width="2" marker-end="url(#m${x.health})" opacity=".85"/><text x="${mx}" y="${my}" text-anchor="middle" style="font-size:9px;fill:#8fa1bd">${esc(x.id)} ${esc(x.label)}</text>`});
 n.forEach(x=>{const p=pos[x.id];s+=`<g><rect x="${p[0]-62}" y="${p[1]-15}" width="124" height="30" rx="8" fill="#16223a" stroke="#2c3f63"/><text x="${p[0]}" y="${p[1]+4}" text-anchor="middle">${esc(x.label.length>22?x.label.slice(0,21)+'…':x.label)}</text></g>`});
 return s+'</svg>'}
function lineageSvg(){const nodes=D.lineage.nodes_view,cols={source:0,gold:1,consumer:2},by={source:[],gold:[],consumer:[]};nodes.forEach(n=>by[n.layer].push(n));
 const W=900,rows=Math.max(...Object.values(by).map(a=>a.length)),H=rows*24+30,pos={};
 Object.entries(by).forEach(([l,arr])=>arr.forEach((n,i)=>pos[n.id]=[110+cols[l]*340,20+i*24*(rows/arr.length)]));
 let s=`<svg viewBox="0 0 ${W} ${H}" width="100%">`;D.lineage.view.forEach(e=>{const a=pos[e.from],b=pos[e.to];if(a&&b)s+=`<path d="M${a[0]+90} ${a[1]} C${a[0]+170} ${a[1]} ${b[0]-170} ${b[1]} ${b[0]-90} ${b[1]}" stroke="#2f6f8f" fill="none" opacity=".55"/>`});
 nodes.forEach(n=>{const p=pos[n.id];s+=`<rect x="${p[0]-90}" y="${p[1]-9}" width="180" height="18" rx="5" fill="#16223a" stroke="#2c3f63"/><text x="${p[0]}" y="${p[1]+4}" text-anchor="middle" style="font-size:10px">${esc(n.id)}</text>`});return s+'</svg>'}
const S={
overview(){const b=D.audit.baseline,q=D.quality,v=D.plan.verification,okm=v.filter(x=>x.ok).length;
 return `<h2>Executive overview</h2><p class="lead">A working data foundation for World Emblem: audit &rarr; architecture &rarr; governed pipelines &rarr; quality &rarr; governance &rarr; AI/BI enablement, plus a verifiable 90-day plan. As-of ${esc(D.as_of)}.</p>
 <div class="grid">${kpi(D.audit.findings.length,'audit findings (current state)')}${kpi(Math.round(q.score*100)+'%','data-quality checks passing ('+q.total+')')}${kpi(D.recon.filter(r=>r.status==='break').length+' / '+D.recon.length,'reconciliation breaks')}${kpi(D.incidents.filter(i=>i.status==='open').length,'open incidents with owners')}${kpi(okm+' / '+v.length,'90-day milestones verified by code')}${kpi(D.architecture.platform.winner.label,'recommended platform')}</div>
 <h3>Baseline scorecard (Day-30 view)</h3><div class="grid">${['reliability_pct','security_pct','documentation_pct','ownership_pct','automation_pct','data_quality_pct'].map(k=>`<div class="card"><span class="mut">${esc(k.replace('_pct','').replace('_',' '))}</span><b style="font-size:20px;display:block">${b[k]??'-'}%</b>${bar(b[k])}</div>`).join('')}</div>
 <h3>Architecture at a glance</h3><div class="grid">${D.architecture.layers.map(l=>`<div class="card"><b>${esc(l.name)}</b><div class="mut">${esc(l.desc)}</div></div>`).join('')}</div>`},
current(){const f=D.audit.findings;return `<h2>1. Current-state audit</h2><p class="lead">Inventory of ${D.audit.baseline.counts.systems} systems, ${D.audit.baseline.counts.integrations} integrations, ${D.audit.baseline.counts.jobs} jobs, ${D.audit.baseline.counts.reports} reports. The estate is an <b>assumed</b> hypothesis from the job description, to be confirmed in days 1-30. Edge colour = control coverage.</p>${flowSvg()}
 <h3>Findings by category</h3><div class="grid">${Object.entries(D.audit.by_category).map(([k,v])=>kpi(v,k.replace('_',' '))).join('')}</div>
 <h3>Findings</h3>${table(['ID','Severity','Category','Subject','Finding','Remediation'],f.map(x=>[x.id,sev(x.severity),esc(x.category),esc(x.subject),esc(x.description),esc(x.remediation)]))}`},
arch(){const p=D.architecture.platform;return `<h2>2. Enterprise architecture</h2><p class="lead">One authority per domain (with field-level exceptions), common identifiers, and a platform recommendation that survives weight changes.</p>
 <h3>System-of-record matrix</h3>${table(['Domain','Business owner','Authority','Identifier','Field-level authority'],D.sor.matrix.map(r=>[esc(r.domain),esc(r.owner),`<code>${esc(r.authority)}</code>`,`<code>${esc(r.identifier)}</code>`,esc(Object.entries(r.field_overrides).map(([k,v])=>k+': '+v).join('; ')||'-')]))}
 <h3>Conflicting writers flagged (non-authority writing into the authority)</h3>${table(['Integration','Domain','From','Into'],D.sor.conflicts.map(c=>[c.integration,c.domain,c.from,c.to]))}
 <h3>Platform decision</h3>${table(['Option','Weighted score','Bar'],p.ranking.map(r=>[esc(r.label),r.score,bar(r.score*20)]))}<p>Weight-perturbation (&plusmn;${p.sensitivity.jitter_pct}%, ${p.sensitivity.trials} trials) win share: ${Object.entries(p.sensitivity.win_share).map(([k,v])=>`<code>${esc(k)}</code> ${(v*100).toFixed(0)}%`).join(', ')}</p>
 <h3>Tooling</h3>${table(['Concern','Choice','Why'],Object.entries(p.tools).map(([k,v])=>[esc(k),esc(v.choice),esc(v.why)]))}`},
pipe(){const p=D.pipeline;return `<h2>3. Pipelines and integration</h2><p class="lead">${p.contracts} data contracts drive typing, drift handling and freshness. Idempotent bronze, generated silver, SQL gold, Airflow DAGs, Spark parity job, webhooks.</p>
 <div class="grid">${Object.entries(p.health).map(([k,v])=>kpi(v,k.replace(/_/g,' '))).join('')}</div><h3>Task runs</h3>${table(['Task','Status','Rows out','Seconds'],p.runs.map(r=>[esc(r.task),pill(r.status,r.status==='success'?'ok':'bad'),num(r.rows_out),r.secs]))}
 <h3>Schema changes detected</h3>${table(['Dataset','Type','Detail','Severity'],p.schema_changes.map(r=>[esc(r.dataset),esc(r.type),esc(r.detail),sev(r.severity)]))}
 <details><summary>Ingest ledger per batch and dataset (received / inserted / duplicate / quarantined)</summary>${table(['Batch','Dataset','Received','Inserted','Duplicate','Quarantined'],p.ingest.map(r=>[r.batch,esc(r.dataset),num(r.received),num(r.inserted),num(r.duplicate),num(r.quarantined)]))}</details>`},
dq(){const q=D.quality;return `<h2>4. Data quality and reconciliation</h2><p class="lead">${q.total} automated checks across ${Object.keys(q.by_dimension).length} dimensions; six cross-system reconciliations with root-cause text.</p>
 <div class="grid">${Object.entries(q.by_dimension).map(([k,v])=>`<div class="card"><span class="mut">${esc(k)}</span><b style="font-size:20px;display:block">${Math.round(v*100)}%</b>${bar(v*100)}</div>`).join('')}</div>
 <h3>Reconciliation</h3>${table(['Measure','System A','A','System B','B','Delta %','Tol %','Status','Root cause'],D.recon.map(r=>[esc(r.measure),esc(r.system_a),num(r.value_a,1),esc(r.system_b),num(r.value_b,1),num(r.delta_pct,2),r.tolerance_pct,pill(r.status,r.status==='match'?'ok':'bad'),esc(r.root_cause)]))}
 <h3>Checks</h3>${table(['Check','Dimension','Severity','Result','Detail'],q.results.map(r=>[esc(r.check_id),esc(r.dimension),sev(r.severity),pill(r.passed?'pass':'fail',r.passed?'ok':'bad'),esc(r.detail)]))}`},
inc(){return `<h2>Incident response</h2><p class="lead">Every failure becomes an incident with severity, a business owner, an escalation ladder, a runbook and a fix-at-source action.</p>${table(['ID','Sev','Domain','Owner','Title','Escalation','Fix at source','Runbook'],D.incidents.map(i=>[i.incident_id,sev(i.severity),esc(i.domain),esc(i.owner),esc(i.title),esc(i.escalation.map(e=>e.after+': '+e.notify).join(' > ')),esc(i.source_fix_action),`<code>${esc(i.runbook)}</code>`]))}`},
gov(){const g=D.governance,m=g.masking_demo;return `<h2>5. Governance and security</h2><p class="lead">RBAC, classification-driven masking, field encryption, tamper-evident audit chain (<b>${g.audit_chain.valid?'valid':'BROKEN'}</b>, ${g.audit_chain.entries} entries) and retention enforcement (dry-run).</p>
 ${table(['Role','Max classification','Datasets','Can unmask'],g.roles.map(r=>[esc(r.role),esc(r.max_class),esc(r.datasets.join(', ')||'-'),esc(r.unmask.join(', ')||'-')]))}
 <h3>Masking in action (role: ${esc(m.as)}; masked: ${esc(m.masked_columns.join(', '))})</h3>${table(['Before (raw)','After (served)'],m.before.map((b,i)=>[esc(b.join(' | ')),esc(Object.values(m.after[i]).join(' | '))]))}
 <h3>Retention dry-run</h3><pre class="card">${esc(JSON.stringify(g.retention_dry_run,null,1))}</pre>`},
ai(){const a=D.ai,s=D.semantic;return `<h2>6. Reporting, AI and internal-product enablement</h2><p class="lead">Governed access only: Power BI semantic model, API, an approved-documents vector index and allow-listed agent tools. ${a.documents} approved non-PII documents indexed.</p>
 <h3>Agent tools (no free SQL)</h3>${table(['Tool','Description'],a.tools.map(t=>[`<code>${esc(t.name)}</code>`,esc(t.description)]))}
 <h3>Usage monitoring</h3>${table(['Caller','Tool','Calls','Rows','Denied'],a.usage.usage.map(u=>[esc(u.caller),esc(u.tool),u.calls,u.rows,u.denied]))}<p>Flags: ${esc(a.usage.flags.join('; ')||'none')}</p>
 <h3>Vector search demo</h3>${table(['Score','Document','Citation'],a.demo_search.map(h=>[h.score,esc(h.text),`<code>${esc(h.citation)}</code>`]))}
 <h3>Power BI semantic model (${s.valid?'valid':'INVALID'}; ${s.relationships} relationships; RLS: ${esc(s.roles.join(', '))})</h3>${table(['Table','Columns','Measures'],s.tables.map(t=>[esc(t.name),t.columns,esc(t.measures.join(', ')||'-')]))}
 <h3>Vendor integration review</h3>${table(['Vendor','Integration','Score','Verdict','Blockers'],D.vendors.map(v=>[esc(v.vendor),esc(v.integration),v.total,pill(v.verdict,v.blockers.length?'bad':'ok'),esc(v.blockers.join(', ')||'-')]))}`},
lin(){return `<h2>Lineage</h2><p class="lead">Generated from contracts and SQL <code>ref()</code> calls: ${D.lineage.nodes} nodes, ${D.lineage.edges} edges. Source &rarr; gold &rarr; consumer.</p>${lineageSvg()}`},
plan(){const v=Object.fromEntries(D.plan.verification.map(x=>[x.id,x]));return `<h2>90-day plan</h2><p class="lead">Exact steps and changes per milestone; each is verified against this running platform.</p>
 ${D.plan.phases.map(p=>`<h3>Days ${esc(p.days)}: ${esc(p.name)}</h3><p class="mut">${esc(p.goal)}</p>${p.milestones.map(m=>`<details><summary>${v[m.id]?pill(v[m.id].ok?'verified':'check',v[m.id].ok?'ok':'bad'):''} ${esc(m.id)} &middot; days ${esc(m.days)} &middot; ${esc(m.title)}</summary><p><b>JD:</b> ${esc(m.jd)}</p><b>Exact steps</b><ol>${m.steps.map(s=>`<li>${esc(s)}</li>`).join('')}</ol><b>Exact changes</b><ul>${m.changes.map(s=>`<li>${esc(s)}</li>`).join('')}</ul><p><b>Run:</b> <code>${esc(m.command)}</code> &middot; <b>Exit:</b> ${esc(m.exit_criteria)}<br><b>Metric:</b> ${esc(m.metric.name)}: ${esc(m.metric.baseline)} &rarr; ${esc(m.metric.target)}</p>${v[m.id]?`<p class="mut">Evidence: ${esc(v[m.id].evidence)}</p>`:''}</details>`).join('')}`).join('')}
 <h3>Prioritised roadmap</h3>${table(['#','Item','Value','Risk','AI','Effort','Priority'],D.plan.roadmap.map((r,i)=>[i+1,esc(r.name),r.value,r.risk,r.ai,r.effort,r.priority]))}
 <h3>Budget (annual USD)</h3>${table(['Item','Low','High'],[...D.plan.budget.lines.map(l=>[esc(l.item),num(l.low),num(l.high)]),['<b>Total</b>','<b>'+num(D.plan.budget.total_low)+'</b>','<b>'+num(D.plan.budget.total_high)+'</b>']])}`},
trace(){return `<h2>JD traceability</h2><p class="lead">Every job-description requirement mapped to code, tests and a command.</p>${table(['Section','Requirement','Evidence','Demo'],D.traceability.map(t=>[esc(t.section),esc(t.requirement),t.evidence.split(';').map(x=>`<code>${esc(x)}</code>`).join(' '),`<code>${esc(t.demo)}</code>`]))}`}};
const TABS=[['overview','Overview'],['current','1 Current state'],['arch','2 Architecture'],['pipe','3 Pipelines'],['dq','4 Quality & recon'],['inc','Incidents'],['gov','5 Governance'],['ai','6 AI & BI'],['lin','Lineage'],['plan','90-day plan'],['trace','JD traceability']];
function show(k){$('#main').innerHTML=S[k]();document.querySelectorAll('nav a').forEach(a=>a.classList.toggle('on',a.dataset.k===k));location.hash=k}
$('#nav').innerHTML=TABS.map(([k,l])=>`<a data-k="${k}">${esc(l)}</a>`).join('');document.querySelectorAll('nav a').forEach(a=>a.onclick=()=>show(a.dataset.k));
show(S[location.hash.slice(1)]?location.hash.slice(1):'overview');
</script></body></html>"""


def render(snapshot: dict[str, Any]) -> str:
    return TEMPLATE.replace("__DATA__", json.dumps(snapshot, default=str).replace("</", "<\\/"))
