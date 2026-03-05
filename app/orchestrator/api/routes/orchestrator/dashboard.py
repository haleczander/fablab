from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["orchestrator"])


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    return """<!doctype html><html lang='fr'><head><meta charset='utf-8'/><meta name='viewport' content='width=device-width, initial-scale=1'/>
<title>Orchestrateur Dashboard</title><style>body{font-family:Segoe UI,Tahoma,sans-serif;margin:0;background:#eef5ff}main{max-width:1180px;margin:20px auto;padding:0 12px}.card{background:#fff;border-radius:12px;padding:12px;box-shadow:0 8px 24px rgba(0,0,0,.08);margin-bottom:12px}.row{display:flex;gap:8px;flex-wrap:wrap}input,button,select{padding:8px;border-radius:8px}button{border:0;background:#0b7a75;color:#fff}table{width:100%;border-collapse:collapse}th,td{padding:6px;border-bottom:1px solid #e5e7eb;text-align:left;font-size:14px}.muted{color:#6b7280;font-size:12px}</style></head><body><main>
<h1>Dashboard Orchestrateur</h1>
<section class='card'><h3>Binding IP -> printer_id</h3><div class='row'><input id='printerId' placeholder='PRN-01'/><input id='printerIp' placeholder='10.0.0.21'/><select id='printerModel'><option value=''>Auto detect</option><option>CORE ONE</option><option>XL</option><option>MK4S</option><option>MK4</option><option>MK3.9S</option><option>MK3.5S</option><option>MINI+</option><option>SL1S</option><option>SL1</option><option>HT90</option></select><button onclick='bindPrinter()'>Bind</button></div><p id='bindMsg' class='muted'></p></section>
<section class='card'><h3>Commande impression</h3><div class='row'><input id='cmdPrinterId' placeholder='PRN-01'/><input id='cmdDuration' placeholder='900'/><button onclick='startPrintCmd()'>Start</button></div><p id='cmdMsg' class='muted'></p></section>
<section class='card'><h3>Fleet</h3><table id='fleetTable'><thead><tr><th>printer_id</th><th>ip</th><th>modele</th><th>etat</th><th>heartbeat</th></tr></thead><tbody></tbody></table></section>
<section class='card'><h3>IP a attribuer</h3><table id='unboundTable'><thead><tr><th>ip</th><th>etat</th><th>modele detecte</th><th>heartbeat</th></tr></thead><tbody></tbody></table></section>
</main><script>
async function api(path, opts={}) { const r=await fetch(path,{headers:{'Content-Type':'application/json'},...opts}); if(!r.ok){let t='';try{t=await r.text()}catch(_){t=r.statusText} throw new Error(t||r.statusText)} if(r.status===204)return null; return r.json(); }
function fmt(v){return (v===null||v===undefined||v==='')?'-':String(v)}
const state={fleet:[],unbound_ips:[]}
function render(){
  document.querySelector('#fleetTable tbody').innerHTML=state.fleet.map(f=>`<tr><td>${fmt(f.printer_id)}</td><td>${fmt(f.printer_ip)}</td><td>${fmt(f.printer_model)}</td><td>${fmt(f.status)}</td><td>${fmt(f.last_heartbeat_at)}</td></tr>`).join('');
  document.querySelector('#unboundTable tbody').innerHTML=state.unbound_ips.map(u=>`<tr><td>${fmt(u.device_ip)}</td><td>${fmt(u.status)}</td><td>${fmt(u.detected_model)}</td><td>${fmt(u.last_heartbeat_at)}</td></tr>`).join('');
}
async function bindPrinter(){const pid=document.getElementById('printerId').value.trim();const ip=document.getElementById('printerIp').value.trim();const model=document.getElementById('printerModel').value.trim();const msg=document.getElementById('bindMsg');try{await api('/printer-bindings',{method:'POST',body:JSON.stringify({printer_id:pid,printer_ip:ip,printer_model:model||null})});msg.textContent='OK';}catch(e){msg.textContent=e.message}}
async function startPrintCmd(){const pid=document.getElementById('cmdPrinterId').value.trim();const dur=Number(document.getElementById('cmdDuration').value.trim()||'900');const msg=document.getElementById('cmdMsg');try{msg.textContent=JSON.stringify(await api(`/printers/${encodeURIComponent(pid)}/commands/start`,{method:'POST',body:JSON.stringify({est_duration_s:dur})}))}catch(e){msg.textContent=e.message}}
function connectWs(){const proto=location.protocol==='https:'?'wss':'ws';const ws=new WebSocket(`${proto}://${location.host}/ws/events`);let ping=null;ws.onopen=()=>{ping=setInterval(()=>{if(ws.readyState===WebSocket.OPEN)ws.send('ping')},25000)};
ws.onmessage=(evt)=>{const m=JSON.parse(evt.data);if(m.event==='snapshot'&&m.payload){state.fleet=m.payload.fleet||[]; state.unbound_ips=m.payload.unbound_ips||[]} if(m.event==='fleet_updated'&&m.payload){state.fleet=m.payload.fleet||[]; state.unbound_ips=m.payload.unbound_ips||[]} render();};
ws.onclose=()=>{if(ping)clearInterval(ping);setTimeout(connectWs,1500)}}
connectWs();
</script></body></html>"""
