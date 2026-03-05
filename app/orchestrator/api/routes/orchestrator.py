import json
from collections import defaultdict, deque
from threading import Lock
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from app.orchestrator.application import services
from app.orchestrator.domain.models import DeviceRuntime, PrinterBinding, PrinterRuntime
from app.orchestrator.domain.schemas import (
    BindPrinterInput,
    DeviceIngestInput,
    FleetItem,
    PrinterStateInput,
    StartPrintCommandInput,
)
from app.orchestrator.infrastructure.db import engine, get_session

router = APIRouter(tags=["orchestrator"])
command_queues: dict[str, deque[dict[str, str | int]]] = defaultdict(deque)
command_lock = Lock()
ws_clients: set[WebSocket] = set()
ws_lock = Lock()
ws_machine_clients: set[WebSocket] = set()
ws_machine_lock = Lock()


async def _broadcast(event: str, payload: dict | list | None = None) -> None:
    message = json.dumps({"event": event, "payload": payload})
    with ws_lock:
        clients = list(ws_clients)
    dead: list[WebSocket] = []
    for client in clients:
        try:
            await client.send_text(message)
        except Exception:
            dead.append(client)
    if dead:
        with ws_lock:
            for client in dead:
                ws_clients.discard(client)


async def _broadcast_machines(event: str, payload: list[dict[str, str | None]]) -> None:
    message = json.dumps({"event": event, "payload": payload})
    with ws_machine_lock:
        clients = list(ws_machine_clients)
    dead: list[WebSocket] = []
    for client in clients:
        try:
            await client.send_text(message)
        except Exception:
            dead.append(client)
    if dead:
        with ws_machine_lock:
            for client in dead:
                ws_machine_clients.discard(client)


def _fleet_payload(session: Session) -> dict[str, list[dict[str, str | None]]]:
    return {
        "fleet": services.list_fleet(session),
        "unbound_ips": services.list_unbound_ips(session),
    }


def _machine_states_payload(session: Session) -> list[dict[str, str | None]]:
    states: list[dict[str, str | None]] = []
    for row in services.list_fleet(session):
        states.append(
            {
                "printer_id": row.get("printer_id"),
                "printer_ip": row.get("printer_ip"),
                "printer_model": row.get("printer_model"),
                "last_heartbeat_at": row.get("last_heartbeat_at"),
                "machine_id": row.get("printer_id"),
                "status": row.get("status"),
                "model": row.get("printer_model"),
            }
        )
    states.sort(key=lambda item: item["machine_id"] or "")
    return states


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "orchestrator"}


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    return """<!doctype html><html lang="fr"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Orchestrateur Dashboard</title><style>body{font-family:Segoe UI,Tahoma,sans-serif;margin:0;background:#eef5ff}main{max-width:1180px;margin:20px auto;padding:0 12px}.card{background:#fff;border-radius:12px;padding:12px;box-shadow:0 8px 24px rgba(0,0,0,.08);margin-bottom:12px}.row{display:flex;gap:8px;flex-wrap:wrap}input,button,select{padding:8px;border-radius:8px}button{border:0;background:#0b7a75;color:#fff}table{width:100%;border-collapse:collapse}th,td{padding:6px;border-bottom:1px solid #e5e7eb;text-align:left;font-size:14px}.muted{color:#6b7280;font-size:12px}</style></head><body><main>
<h1>Dashboard Orchestrateur</h1>
<section class="card"><h3>Binding IP -> printer_id</h3><div class="row"><input id="printerId" placeholder="PRN-01"/><input id="printerIp" placeholder="10.0.0.21"/><select id="printerModel"><option value=\"\">Auto detect</option><option>CORE ONE</option><option>XL</option><option>MK4S</option><option>MK4</option><option>MK3.9S</option><option>MK3.5S</option><option>MINI+</option><option>SL1S</option><option>SL1</option><option>HT90</option></select><button onclick="bindPrinter()">Bind</button></div><p id="bindMsg" class="muted"></p></section>
<section class="card"><h3>Commande impression</h3><div class="row"><input id="cmdPrinterId" placeholder="PRN-01"/><input id="cmdDuration" placeholder="900"/><button onclick="startPrintCmd()">Start</button></div><p id="cmdMsg" class="muted"></p></section>
<section class="card"><h3>Fleet</h3><table id="fleetTable"><thead><tr><th>printer_id</th><th>ip</th><th>modele</th><th>etat</th><th>heartbeat</th></tr></thead><tbody></tbody></table></section>
<section class="card"><h3>IP a attribuer</h3><table id="unboundTable"><thead><tr><th>ip</th><th>etat</th><th>modele detecte</th><th>heartbeat</th></tr></thead><tbody></tbody></table></section>
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
async function bootstrap(){}
function connectWs(){const proto=location.protocol==='https:'?'wss':'ws';const ws=new WebSocket(`${proto}://${location.host}/ws/events`);let ping=null;ws.onopen=()=>{ping=setInterval(()=>{if(ws.readyState===WebSocket.OPEN)ws.send('ping')},25000)};
ws.onmessage=(evt)=>{const m=JSON.parse(evt.data);if(m.event==='snapshot'&&m.payload){state.fleet=m.payload.fleet||[]; state.unbound_ips=m.payload.unbound_ips||[]} if(m.event==='fleet_updated'&&m.payload){state.fleet=m.payload.fleet||[]; state.unbound_ips=m.payload.unbound_ips||[]} render();};
ws.onclose=()=>{if(ping)clearInterval(ping);setTimeout(connectWs,1500)}}
bootstrap().then(connectWs);
</script></body></html>"""


@router.get("/printers", response_model=list[PrinterRuntime])
def list_printers(session: Session = Depends(get_session)) -> list[PrinterRuntime]:
    return services.list_runtimes(session)


@router.get("/devices", response_model=list[DeviceRuntime])
def list_devices(session: Session = Depends(get_session)) -> list[DeviceRuntime]:
    return services.list_devices(session)


@router.get("/printer-bindings", response_model=list[PrinterBinding])
def list_bindings(session: Session = Depends(get_session)) -> list[PrinterBinding]:
    return services.list_bindings(session)


@router.get("/fleet", response_model=list[FleetItem])
def list_fleet(session: Session = Depends(get_session)) -> list[FleetItem]:
    return [FleetItem(**row) for row in services.list_fleet(session)]


@router.post("/printer-bindings", response_model=PrinterBinding)
async def bind_printer(payload: BindPrinterInput, session: Session = Depends(get_session)) -> PrinterBinding:
    row = services.upsert_binding(
        session,
        printer_id=payload.printer_id,
        printer_ip=str(payload.printer_ip),
        printer_model=payload.printer_model,
    )
    await _broadcast("binding_updated", row.model_dump(mode="json"))
    await _broadcast("fleet_updated", _fleet_payload(session))
    await _broadcast_machines("machines_updated", _machine_states_payload(session))
    return row


@router.post("/printers/{printer_id}/state", response_model=PrinterRuntime)
async def update_printer_state(printer_id: str, payload: PrinterStateInput, session: Session = Depends(get_session)) -> PrinterRuntime:
    row = services.upsert_runtime(session, printer_id=printer_id, data=payload)
    await _broadcast("runtime_updated", row.model_dump(mode="json"))
    await _broadcast("fleet_updated", _fleet_payload(session))
    await _broadcast_machines("machines_updated", _machine_states_payload(session))
    return row


@router.post("/devices/state-ingest", response_model=DeviceRuntime)
async def ingest_device_state(payload: DeviceIngestInput, request: Request, session: Session = Depends(get_session)) -> DeviceRuntime:
    source_ip = request.client.host if request.client else "0.0.0.0"
    device, runtime = services.upsert_device_runtime(session, source_ip, payload)
    await _broadcast("device_updated", device.model_dump(mode="json"))
    if runtime:
        await _broadcast("runtime_updated", runtime.model_dump(mode="json"))
    await _broadcast("fleet_updated", _fleet_payload(session))
    await _broadcast_machines("machines_updated", _machine_states_payload(session))
    return device


@router.post("/printers/{printer_id}/jobs/poll-once")
def poll_next_job(printer_id: str) -> dict[str, str | bool | None]:
    return services.poll_next_job_once(printer_id)


@router.post("/printers/{printer_id}/commands/start")
async def command_start_print(
    printer_id: str,
    payload: StartPrintCommandInput,
    session: Session = Depends(get_session),
) -> dict[str, str | int]:
    job_id = payload.job_id or f"JOB-AUTO-{uuid4().hex[:10].upper()}"
    command = {"type": "START_PRINT", "job_id": job_id, "est_duration_s": payload.est_duration_s}
    with command_lock:
        command_queues[printer_id].append(command)
        queued = len(command_queues[printer_id])
    runtime = services.mark_job_sent_now(session, printer_id=printer_id, job_id=job_id)
    out = {"printer_id": printer_id, "queued": queued, **command}
    await _broadcast("command_queued", out)
    await _broadcast("runtime_updated", runtime.model_dump(mode="json"))
    await _broadcast("fleet_updated", _fleet_payload(session))
    await _broadcast_machines("machines_updated", _machine_states_payload(session))
    return out


@router.get("/devices/commands/next")
def pop_next_command_for_source_ip(request: Request, session: Session = Depends(get_session)) -> dict[str, str | int] | None:
    source_ip = request.client.host if request.client else "0.0.0.0"
    binding = services.get_binding_by_ip(session, source_ip)
    if not binding:
        return None
    with command_lock:
        queue = command_queues[binding.printer_id]
        if not queue:
            return None
        return queue.popleft()


@router.websocket("/ws/events")
async def ws_events(websocket: WebSocket) -> None:
    await websocket.accept()
    with ws_lock:
        ws_clients.add(websocket)
    try:
        with Session(engine) as session:
            snapshot = {
                "devices": [d.model_dump(mode="json") for d in services.list_devices(session)],
                "printers": [p.model_dump(mode="json") for p in services.list_runtimes(session)],
                "bindings": [b.model_dump(mode="json") for b in services.list_bindings(session)],
                "fleet": services.list_fleet(session),
                "unbound_ips": services.list_unbound_ips(session),
            }
        await websocket.send_text(json.dumps({"event": "snapshot", "payload": snapshot}))
        while True:
            if await websocket.receive_text() == "ping":
                await websocket.send_text(json.dumps({"event": "pong", "payload": None}))
    except WebSocketDisconnect:
        pass
    finally:
        with ws_lock:
            ws_clients.discard(websocket)


@router.websocket("/ws/machines")
async def ws_machines(websocket: WebSocket) -> None:
    await websocket.accept()
    with ws_machine_lock:
        ws_machine_clients.add(websocket)
    try:
        with Session(engine) as session:
            snapshot = _machine_states_payload(session)
        await websocket.send_text(json.dumps({"event": "machines_snapshot", "payload": snapshot}))
        while True:
            if await websocket.receive_text() == "ping":
                await websocket.send_text(json.dumps({"event": "pong", "payload": None}))
    except WebSocketDisconnect:
        pass
    finally:
        with ws_machine_lock:
            ws_machine_clients.discard(websocket)
