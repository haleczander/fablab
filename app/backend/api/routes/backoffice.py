from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["backoffice"])


@router.get("/backoffice", response_class=HTMLResponse)
def backoffice_home() -> str:
    return """<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Fablab Backoffice</title>
  <style>
    :root { --bg:#f5f7fb; --card:#ffffff; --text:#1f2937; --accent:#0f766e; --muted:#6b7280; }
    body { margin:0; font-family: "Segoe UI", Tahoma, sans-serif; background:linear-gradient(160deg,#e6f4f1,#f6fbff); color:var(--text); }
    main { max-width: 1100px; margin: 24px auto; padding: 0 16px 24px; }
    h1 { margin: 0 0 16px; }
    .grid { display:grid; gap:16px; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }
    .card { background:var(--card); border-radius:14px; box-shadow:0 10px 30px rgba(15,118,110,.10); padding:16px; }
    .row { display:flex; gap:8px; flex-wrap:wrap; margin-top:8px; }
    input, textarea, button { font: inherit; }
    input, textarea { width:100%; box-sizing:border-box; border:1px solid #d1d5db; border-radius:8px; padding:8px 10px; }
    textarea { min-height:76px; resize:vertical; }
    button { border:0; border-radius:9px; background:var(--accent); color:white; padding:9px 14px; cursor:pointer; }
    table { width:100%; border-collapse: collapse; font-size:14px; }
    th, td { text-align:left; border-bottom:1px solid #e5e7eb; padding:7px 4px; }
    .muted { color:var(--muted); font-size:12px; }
    .ok { color:#047857; }
    .err { color:#b91c1c; }
  </style>
</head>
<body>
<main>
  <h1>Backoffice Fablab</h1>
  <div class="grid">
    <section class="card">
      <h2>Enregistrer une imprimante</h2>
      <div class="row"><input id="printerId" placeholder="PRN-01" /></div>
      <div class="row"><button onclick="registerPrinter()">Enregistrer</button></div>
      <p id="printerMsg" class="muted"></p>
    </section>
    <section class="card">
      <h2>Creer un job</h2>
      <div class="row"><input id="jobPrinterId" placeholder="printer_id (PRN-01)" /></div>
      <div class="row"><input id="gcodeUrl" placeholder="https://.../piece.gcode" /></div>
      <div class="row"><textarea id="params" placeholder='{"layer_height":0.2}'></textarea></div>
      <div class="row"><button onclick="createJob()">Ajouter a la file</button></div>
      <p id="jobMsg" class="muted"></p>
    </section>
  </div>

  <section class="card" style="margin-top:16px;">
    <h2>Etat imprimantes</h2>
    <table id="printersTable"><thead><tr><th>printer_id</th><th>status</th><th>heartbeat</th><th>job</th><th>progress</th></tr></thead><tbody></tbody></table>
  </section>

  <section class="card" style="margin-top:16px;">
    <h2>Jobs</h2>
    <table id="jobsTable"><thead><tr><th>job_id</th><th>printer_id</th><th>status</th><th>progress</th><th>updated_at</th></tr></thead><tbody></tbody></table>
  </section>
</main>

<script>
async function api(path, opts={}) {
  const response = await fetch(path, { headers: { "Content-Type":"application/json" }, ...opts });
  if (!response.ok) {
    let detail = response.statusText;
    try { const body = await response.json(); if (body.detail) detail = body.detail; } catch (_) {}
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  return response.json();
}

function fmt(v) { return v === null || v === undefined ? "-" : String(v); }

async function registerPrinter() {
  const msg = document.getElementById("printerMsg");
  const printerId = document.getElementById("printerId").value.trim();
  if (!printerId) { msg.textContent = "printer_id requis"; msg.className = "err"; return; }
  try {
    await api("/printers/register", { method:"POST", body: JSON.stringify({ printer_id: printerId }) });
    msg.textContent = "Imprimante enregistree"; msg.className = "ok";
    loadData();
  } catch (e) { msg.textContent = e.message; msg.className = "err"; }
}

async function createJob() {
  const msg = document.getElementById("jobMsg");
  const printerId = document.getElementById("jobPrinterId").value.trim();
  const gcodeUrl = document.getElementById("gcodeUrl").value.trim();
  const raw = document.getElementById("params").value.trim();
  let parameters = {};
  if (raw) {
    try { parameters = JSON.parse(raw); } catch (_) { msg.textContent = "JSON parametres invalide"; msg.className = "err"; return; }
  }
  try {
    await api("/jobs", { method:"POST", body: JSON.stringify({ printer_id: printerId, gcode_url: gcodeUrl, parameters }) });
    msg.textContent = "Job cree"; msg.className = "ok";
    loadData();
  } catch (e) { msg.textContent = e.message; msg.className = "err"; }
}

async function loadData() {
  const printersBody = document.querySelector("#printersTable tbody");
  const jobsBody = document.querySelector("#jobsTable tbody");
  try {
    const [printers, jobs] = await Promise.all([api("/printers"), api("/jobs")]);
    printersBody.innerHTML = printers.map(p =>
      `<tr><td>${fmt(p.printer_id)}</td><td>${fmt(p.status)}</td><td>${fmt(p.last_heartbeat_at)}</td><td>${fmt(p.current_job_id)}</td><td>${fmt(p.progress_pct)}</td></tr>`
    ).join("");
    jobsBody.innerHTML = jobs.map(j =>
      `<tr><td>${fmt(j.job_id)}</td><td>${fmt(j.printer_id)}</td><td>${fmt(j.status)}</td><td>${fmt(j.progress_pct)}</td><td>${fmt(j.updated_at)}</td></tr>`
    ).join("");
  } catch (_) {
    printersBody.innerHTML = "<tr><td colspan='5'>Erreur chargement</td></tr>";
    jobsBody.innerHTML = "<tr><td colspan='5'>Erreur chargement</td></tr>";
  }
}

loadData();
setInterval(loadData, 5000);
</script>
</body>
</html>"""
