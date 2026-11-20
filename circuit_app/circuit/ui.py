CSS = """
*{box-sizing:border-box}body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f4f5f7;color:#1d2330;font-size:14px}
header{background:#14213d;color:#fff;padding:10px 16px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header b{font-size:17px}header a{color:#ffd166}.tag{font-size:11px;padding:2px 6px;border-radius:4px;background:#e9ecef;color:#333;font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:10px;padding:10px}
.card{background:#fff;border-radius:8px;padding:10px;box-shadow:0 1px 2px rgba(0,0,0,.08);display:flex;flex-direction:column;gap:6px}
.card h3{margin:0;font-size:15px}.inbox{background:#e5ddd5;border-radius:6px;padding:6px;min-height:90px;max-height:260px;overflow:auto}
.msg{background:#fff;border-radius:6px;padding:6px 8px;margin:4px 0;white-space:pre-wrap}.msg small{color:#777;display:block}
textarea,input{width:100%;font:inherit;padding:6px;border:1px solid #ccc;border-radius:5px}
button{font:inherit;padding:6px 10px;border:0;border-radius:5px;background:#2b6cb0;color:#fff;cursor:pointer;margin:2px 2px 2px 0}
button.alt{background:#4a5568}button.ok{background:#2f855a}button.warn{background:#c05621}
.row{display:flex;gap:6px;align-items:center;flex-wrap:wrap}pre{white-space:pre-wrap;word-break:break-word;background:#f7f7f9;padding:6px;border-radius:5px;font-size:12px;margin:4px 0;max-height:320px;overflow:auto}
.LIVE{background:#c6f6d5}.DOC_SIMULATED{background:#feebc8}.ROLEPLAY{background:#e9d8fd}.SYNTHETIC_FIXTURE{background:#e2e8f0}.MODEL_DECISION{background:#bee3f8}.SYSTEM{background:#edf2f7}
"""

CONSOLE_HTML = """<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Circuit - actor console</title><style>""" + CSS + """</style></head><body>
<header><b>Circuit</b><span>Actor console (ROLEPLAY_INBOX)</span><span id=hdr></span><a id=tr href="#" target=_blank>Open live trace</a>
<button class=alt onclick="if(confirm('Close this case and start fresh?'))post('/api/reset')">New case</button></header>
<div class=grid>
 <div class=card><h3>Household (Meera, role-play) <span class="tag ROLEPLAY">ROLEPLAY</span></h3>
  <div class=inbox id=in_household></div>
  <div class=row><input type=file id=audio accept="audio/*"><button onclick=sendAudio()>Send voice note</button></div>
  <textarea id=t_household rows=2 placeholder="Type a reply as the household"></textarea><button onclick="say('household')">Send text</button>
  <div id=hh_actions></div></div>
 <div class=card><h3>Agency dispatcher / owner <span class="tag ROLEPLAY">ROLEPLAY</span></h3>
  <div class=inbox id=in_agency></div><div id=ag_actions></div>
  <textarea id=t_agency rows=2 placeholder="Type as the agency"></textarea><button onclick="say('agency')">Send text</button></div>
 <div class=card><h3>Technician <span class="tag ROLEPLAY">ROLEPLAY</span></h3>
  <div class=inbox id=in_technician></div><div id=te_actions></div>
  <textarea id=t_technician rows=2 placeholder="Type as the technician"></textarea><button onclick="say('technician')">Send text</button></div>
 <div class=card><h3>Payer (adult, may be another city) <span class="tag ROLEPLAY">ROLEPLAY</span></h3>
  <div class=inbox id=in_payer></div><div id=pa_actions></div>
  <textarea id=t_payer rows=2 placeholder="Type as the payer"></textarea><button onclick="say('payer')">Send text</button></div>
 <div class=card style="grid-column:1/-1"><h3>Wizard: partner responses copied from documentation <span class="tag DOC_SIMULATED">DOC_SIMULATED</span></h3>
  <div id=wizard>No partner request yet.</div></div>
</div>
<script>
let S=null;
async function post(u,data){const fd=new FormData();for(const k in (data||{}))fd.append(k,data[k]);
 const r=await fetch(u,{method:'POST',body:fd});if(!r.ok){alert((await r.json()).detail||r.status)};refresh();}
async function sendAudio(){const f=document.getElementById('audio').files[0];if(!f)return alert('Choose the voice-note file');
 const fd=new FormData();fd.append('file',f);const r=await fetch('/api/household/audio',{method:'POST',body:fd});if(!r.ok)alert(await r.text());document.getElementById('audio').value='';refresh();}
function say(role){const el=document.getElementById('t_'+role);if(!el.value.trim())return;post('/api/'+role+'/text',{text:el.value});el.value='';}
function esc(s){return String(s??'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
function inbox(role){const m=(S.outbox||{})[role]||[];document.getElementById('in_'+role).innerHTML=m.map(x=>`<div class=msg><small>Circuit - ${x.ts.slice(11,19)}</small>${esc(x.text)}</div>`).join('')||'<small>No messages yet</small>';
 const b=document.getElementById('in_'+role);b.scrollTop=b.scrollHeight;}
async function refresh(){const r=await fetch('/api/state');S=await r.json();
 if(!S.case){document.getElementById('hdr').textContent='No case yet: waiting for the household';['household','agency','technician','payer'].forEach(r=>document.getElementById('in_'+r).innerHTML='');return;}
 const c=S.case,f=c.facts;document.getElementById('hdr').innerHTML=`${c.id} | state <b>${c.state}</b> | model ${esc(S.model)} ${S.busy?'| <b>Circuit is working...</b>':''} ${S.last_error?'| <span style="color:#ffb4b4">Last error '+S.last_error.ts.slice(11,19)+': '+esc(S.last_error.summary)+'</span>':''}`;
 document.getElementById('tr').href='/trace/'+c.id;['household','agency','technician','payer'].forEach(inbox);
 let h='';if(f.slots_offered.length&&!f.slot_selected)h+='<div>Choose slot: '+f.slots_offered.map(s=>`<button class=ok onclick="post('/api/household/slot',{slot:'${s}'})">${s.slice(5,16).replace('T',' ')}</button>`).join('')+'</div>';
 if(f.slot_selected&&f.resident.access_permission!=='GRANTED')h+=`<button class=ok onclick="post('/api/household/access')">Grant home access for ${f.slot_selected.slice(5,16).replace('T',' ')}</button>`;
 document.getElementById('hh_actions').innerHTML=h;
 let a='';if(f.ranked_techs.length&&!f.assigned_tech)a+='<div>Circuit ranked: '+f.ranked_techs.map(t=>`<button class=ok onclick="post('/api/agency/assign',{tech_id:'${t.tech_id}'})">Assign ${esc(t.name)}</button>`).join('')+'</div>';
 if(!f.owner_signoff)a+=`<button class=warn onclick="post('/api/agency/signoff')">Owner: sign off READY</button>`;else a+='<small>Owner signed off.</small>';
 document.getElementById('ag_actions').innerHTML=a;
 let t='';if(f.assigned_tech&&!f.tech_accepted)t+=`<button class=ok onclick="post('/api/technician/accept')">Accept job (${f.assigned_tech})</button><button class=warn onclick="post('/api/technician/decline')">Decline</button>`;
 if(f.kit.sku&&f.tech_accepted&&!f.kit.custody_ack)t+=`<button class=ok onclick="post('/api/technician/kit')">Confirm ${esc(f.kit.sku)} in my bag</button>`;
 document.getElementById('te_actions').innerHTML=t||'<small>Waiting for assignment.</small>';
 let p='';if(f.quote&&!f.payer_approved)p=`<button class=ok onclick="post('/api/payer/approve')">Approve up to Rs ${(f.quote.ceiling_paise/100).toFixed(0)} in UPI app</button>`;else if(f.payer_approved)p='<small>Approved ceiling Rs '+(f.payer_approved_ceiling_paise/100).toFixed(0)+'</small>';
 document.getElementById('pa_actions').innerHTML=p;
 const w=document.getElementById('wizard');const open=S.pending.filter(x=>x.status!=='RESPONDED');
 const sig=JSON.stringify(open.map(x=>x.id));if(w.dataset.sig!==sig){w.dataset.sig=sig;
  w.innerHTML=open.length?open.map(x=>`<div class=card style="background:#fffaf0"><b>${x.rail} request ${x.id}</b><small>${esc(x.doc_ref)}</small><pre>${esc(JSON.stringify(JSON.parse(x.request),null,1))}</pre>
  <input id=doc_${x.id} placeholder="Exact doc section / URL you copied the response from"><textarea id=resp_${x.id} rows=5 placeholder='Paste the documented JSON response, e.g. {"status":"ACTIVE", ...}'></textarea>
  <button onclick="post('/api/wizard/${x.id}',{response:document.getElementById('resp_${x.id}').value,doc_section:document.getElementById('doc_${x.id}').value})">Feed response to Circuit</button></div>`).join(''):'No open partner request.';}}
refresh();setInterval(refresh,1500);
</script></body></html>"""

TRACE_HTML = """<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Circuit trace __CID__</title><style>""" + CSS + """
.ev{background:#fff;margin:6px 10px;padding:8px 10px;border-radius:6px;border-left:5px solid #cbd5e0}
.ev.k-gnani_stt{border-color:#38a169}.ev.k-pine_request,.ev.k-pine_response{border-color:#dd6b20}.ev.k-delhivery_request,.ev.k-delhivery_response{border-color:#d69e2e}
.ev.k-agent_decision{border-color:#3182ce}.ev.k-message_out{border-color:#805ad5}.ev.k-agent_error{border-color:#e53e3e}
.meta{font-size:12px;color:#555}details summary{cursor:pointer;color:#2b6cb0;font-size:12px}
#gate{margin:10px;background:#fff;padding:8px;border-radius:6px}#gate td{padding:2px 8px;font-size:13px}
</style></head><body><header><b>Circuit live trace</b><span>__CID__</span><span id=st></span><a href="/export/__CID__.md" target=_blank>Export decision log</a></header>
<div id=gate></div><div id=evs></div>
<script>
function esc(s){return String(s??'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
let n=0;
async function load(){const r=await fetch('/api/trace/__CID__');const d=await r.json();
 document.getElementById('st').innerHTML='state <b>'+d.case.state+'</b>';
 const g=d.case.facts.gate;if(g)document.getElementById('gate').innerHTML='<b>S5 readiness gate: '+g.verdict+'</b> <small>'+esc(g.label)+'</small><table>'+g.predicates.map(p=>`<tr><td>${p.result==='PASS'?'&#9989;':p.result==='FAIL'?'&#10060;':'&#9898;'}</td><td>${p.predicate}</td><td class=meta>${esc(p.source)}</td></tr>`).join('')+'</table>';
 if(d.events.length===n)return;n=d.events.length;
 document.getElementById('evs').innerHTML=d.events.map(e=>{const pl=e.payload;let det='';
  if(pl){const show=['gnani_stt','pine_request','pine_response','delhivery_request','delhivery_response'].includes(e.kind);
   const p2=JSON.parse(JSON.stringify(pl));if(p2&&p2.raw_model_output)delete p2.raw_model_output;
   det=show?`<pre>${esc(JSON.stringify(p2,null,1))}</pre>`:`<details><summary>details</summary><pre>${esc(JSON.stringify(p2,null,1))}</pre></details>`;}
  return `<div class="ev k-${e.kind}"><div class=meta>${e.ts.slice(11,19)} | <b>${e.kind}</b> | ${esc(e.actor)} | <span class="tag ${e.source_mode}">${e.source_mode}</span> ${e.transport?'| '+esc(e.transport):''} ${e.rule_ids?'| rules '+e.rule_ids:''} ${e.state_before||e.state_after?'| '+e.state_before+' &rarr; '+e.state_after:''}</div>
  <div>${esc(e.summary)}</div>${det}</div>`}).join('');window.scrollTo(0,document.body.scrollHeight);}
load();setInterval(load,1500);
</script></body></html>"""
