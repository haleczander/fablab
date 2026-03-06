async function api(path, opts = {}) {
  const { timeout_ms, ...fetchOpts } = opts;
  const timeoutMs = Number(timeout_ms) || 0;
  const controller = timeoutMs > 0 ? new AbortController() : null;
  const timeout = controller ? setTimeout(() => controller.abort(), timeoutMs) : null;
  const r = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...fetchOpts,
    ...(controller ? { signal: controller.signal } : {}),
  });
  if (timeout) clearTimeout(timeout);
  if (!r.ok) {
    let t = "";
    try { t = await r.text(); } catch (_) { t = r.statusText; }
    throw new Error(t || r.statusText);
  }
  if (r.status === 204) return null;
  return r.json();
}

let latestRows = [];
const machineStateByPrinter = new Map();
let showAllAvailable = true;

function fmt(v) {
  return (v === null || v === undefined || v === "") ? "-" : String(v);
}

function supportLabel(adapter) {
  return String(adapter || "").toLowerCase() === "prusalink" ? "PrusaLink" : "X";
}

function hasSupportedContract(adapter) {
  return supportLabel(adapter) !== "X";
}

function esc(v) {
  return String(v ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function statusColor(status) {
  const value = String(status || "").toUpperCase();
  if (["IDLE", "READY", "AVAILABLE", "ON"].includes(value)) return "status-green";
  if (["IN_USE", "BUSY", "PRINTING", "RUNNING"].includes(value)) return "status-orange";
  if (["OFFLINE", "ERROR", "DISCONNECTED", "DOWN"].includes(value)) return "status-red";
  return "status-orange";
}

function canIgnoreDevice(row) {
  // Ne pas proposer "Pas une machine" si deja binde ET contrat d'interface supporte.
  return !(Boolean(row.is_bound) && hasSupportedContract(row.detected_adapter));
}

function isIgnoredDevice(row) {
  return Boolean(row?.is_ignored);
}

function syncShowAllButton() {
  const btn = document.getElementById("showAllBtn");
  if (!btn) return;
  btn.textContent = showAllAvailable ? "Masquer non machines" : "Tout voir";
}

function toggleShowAllAvailable() {
  showAllAvailable = !showAllAvailable;
  syncShowAllButton();
  renderDevices(latestRows);
}

function isActiveStatus(status) {
  const value = String(status || "").toUpperCase();
  return ["PRINTING", "IN_USE", "BUSY", "RUNNING"].includes(value);
}

function numFmt(value, unit) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "-";
  return `${n.toFixed(1)}${unit}`;
}

function renderOngoingJobs(rows) {
  const active = (rows || []).filter((d) => {
    if (!d.is_bound) return false;
    const live = machineStateByPrinter.get(String(d.printer_id || ""));
    const status = live?.status || d.status;
    const jobId = live?.current_job_id || d.current_job_id;
    return isActiveStatus(status) || Boolean(jobId);
  });
  const jobsMsg = document.getElementById("jobsMsg");
  const container = document.getElementById("ongoingJobs");

  if (!active.length) {
    jobsMsg.textContent = "Aucun job en cours.";
    container.innerHTML = "";
    return;
  }

  jobsMsg.textContent = `${active.length} job(s) actif(s).`;
  container.innerHTML = active.map((d) => {
    const pid = String(d.printer_id || "");
    const live = machineStateByPrinter.get(pid) || {};
    const status = live.status || d.status;
    const currentJobId = live.current_job_id || d.current_job_id;
    const progress = Math.max(0, Math.min(100, Number(live.progress_pct ?? d.progress_pct) || 0));
    const nozzle = live.nozzle_temp_c ?? d.nozzle_temp_c;
    const bed = live.bed_temp_c ?? d.bed_temp_c;
    const hb = live.last_heartbeat_at || d.last_heartbeat_at;
    const dotClass = statusColor(status);
    return `
      <article class="job-card">
        <div class="job-head">
          <h4 class="job-title">${esc(pid || "ID inconnu")}</h4>
          <span class="status-dot ${dotClass}" title="${esc(fmt(status))}"></span>
        </div>
        <p class="job-meta">Job: ${esc(fmt(currentJobId))}</p>
        <p class="job-meta">Modele: ${esc(fmt(d.printer_model || d.detected_model))}</p>
        <p class="job-meta">Progression: ${progress.toFixed(1)}%</p>
        <p class="job-meta">Nozzle: ${numFmt(nozzle, " C")} | Bed: ${numFmt(bed, " C")}</p>
        <p class="job-meta">Dernier ping: ${esc(fmt(hb))}</p>
        <div class="progress"><span style="width:${progress}%"></span></div>
      </article>
    `;
  }).join("");
}

async function saveBinding(mac, rowId, msgId, deviceIp = "", deviceSerial = "", detectedAdapter = "") {
  const pid = document.getElementById(`pid-${rowId}`).value.trim();
  const modelInput = document.getElementById(`model-${rowId}`);
  const model = modelInput ? modelInput.value.trim() : "";
  const msg = document.getElementById(msgId);
  if (!pid) {
    msg.textContent = "id metier requis";
    return;
  }
  try {
    await api("/printer-bindings", {
      method: "POST",
      body: JSON.stringify({
        printer_id: pid,
        printer_mac: mac,
        printer_ip: deviceIp || null,
        printer_serial: deviceSerial || null,
        printer_model: model || null,
        adapter_name: detectedAdapter || null,
      }),
    });
    msg.textContent = "OK";
  } catch (e) {
    msg.textContent = e.message;
  }
}

async function setIgnored(deviceId, deviceMac, deviceIp, deviceSerial, detectedAdapter, detectedModel, isIgnored, msgId) {
  const msg = document.getElementById(msgId);
  try {
    if (deviceId) {
      await api(`/devices/${deviceId}/ignored`, {
        method: "PATCH",
        body: JSON.stringify({ is_ignored: isIgnored }),
      });
    } else {
      await api("/devices/ignored/by-mac", {
        method: "POST",
        body: JSON.stringify({
          device_mac: deviceMac,
          device_ip: deviceIp,
          device_serial: deviceSerial || null,
          detected_adapter: detectedAdapter || null,
          detected_model: detectedModel || null,
          is_ignored: isIgnored,
        }),
      });
    }
    msg.textContent = isIgnored ? "Device masque" : "Device restaure";
  } catch (e) {
    msg.textContent = e.message;
  }
}

async function deleteBinding(printerId, msgId) {
  const msg = document.getElementById(msgId);
  const pid = String(printerId || "").trim();
  if (!pid) {
    msg.textContent = "printer_id manquant";
    return;
  }
  try {
    await api(`/printer-bindings/${encodeURIComponent(pid)}`, { method: "DELETE" });
    msg.textContent = `Binding supprime: ${pid}`;
  } catch (e) {
    msg.textContent = e.message;
  }
}

async function refreshNetworkDiscovery() {
  const msg = document.getElementById("scanMsg");
  const btn = document.getElementById("scanBtn");
  const progressWrap = document.getElementById("scanProgress");
  let timer = null;
  const startedAt = Date.now();

  if (msg) msg.className = "scan-msg run";
  if (btn) btn.disabled = true;
  if (progressWrap) progressWrap.classList.remove("hidden");
  if (progressWrap) progressWrap.classList.add("indeterminate");
  if (msg) msg.textContent = "Scan reseau en cours...";

  timer = setInterval(() => {
    const tookS = ((Date.now() - startedAt) / 1000).toFixed(0);
    if (msg) msg.textContent = `Scan reseau en cours... ${tookS}s`;
  }, 1000);

  try {
    const out = await api("/discovery/refresh", { method: "POST", timeout_ms: 300000 });
    const updated = Number(out?.updated) || 0;
    const tookMs = Date.now() - startedAt;
    const tookS = (tookMs / 1000).toFixed(1);
    const stamp = new Date().toLocaleTimeString("fr-FR");
    if (timer) clearInterval(timer);
    if (msg) {
      msg.className = "scan-msg ok";
      msg.textContent = `Scan termine: ${updated} maj en ${tookS}s (${stamp})`;
    }
  } catch (e) {
    if (timer) clearInterval(timer);
    if (msg) {
      msg.className = "scan-msg err";
      const reason = e instanceof Error && e.name === "AbortError"
        ? "timeout (scan trop long)"
        : (e instanceof Error ? e.message : "Erreur");
      msg.textContent = `Scan en erreur: ${reason}`;
    }
  } finally {
    setTimeout(() => {
      if (progressWrap) progressWrap.classList.remove("indeterminate");
      if (progressWrap) progressWrap.classList.add("hidden");
      if (btn) btn.disabled = false;
    }, 4000);
  }
}

function renderDevices(rows) {
  latestRows = Array.isArray(rows) ? rows : [];
  renderOngoingJobs(rows);
  const availableAll = (rows || []).filter((d) => !d.is_bound);
  const available = showAllAvailable ? availableAll : availableAll.filter((d) => !isIgnoredDevice(d));
  const bound = (rows || []).filter((d) => d.is_bound);
  const modelSet = new Set(["MK3S", "MK4", "MK4S", "XL", "MINI+"]);

  for (const d of rows || []) {
    if (d.printer_model) modelSet.add(String(d.printer_model));
    if (d.detected_model) modelSet.add(String(d.detected_model));
  }

  document.getElementById("modelOptions").innerHTML = [...modelSet]
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b))
    .map((m) => `<option value="${esc(m)}"></option>`)
    .join("");

  document.querySelector("#availableTable tbody").innerHTML = available.map((d, idx) => {
    const rowId = `a-${idx}`;
    const hasMac = Boolean(d.device_mac);
    const live = machineStateByPrinter.get(String(d.printer_id || "")) || {};
    const status = live.status || d.status;
    const hb = live.last_heartbeat_at || d.last_heartbeat_at;
    const dotClass = statusColor(status);
    const stateTitle = `Etat: ${fmt(status)} | Dernier ping: ${fmt(hb)}`;
    const networkTitle = `IP: ${fmt(d.device_ip)} | MAC: ${fmt(d.device_mac)} | Serial: ${fmt(d.device_serial)}`;
    const ignoreBtn = canIgnoreDevice(d)
      ? (isIgnoredDevice(d)
          ? `<button class="btn-secondary" onclick="setIgnored(${Number(d.device_id) || 0}, '${esc(d.device_mac || "")}', '${esc(d.device_ip || "")}', '${esc(d.device_serial || "")}', '${esc(d.detected_adapter || "")}', '${esc(d.detected_model || "")}', false, 'availMsg')">Reafficher</button>`
          : `<button class="btn-secondary" onclick="setIgnored(${Number(d.device_id) || 0}, '${esc(d.device_mac || "")}', '${esc(d.device_ip || "")}', '${esc(d.device_serial || "")}', '${esc(d.detected_adapter || "")}', '${esc(d.detected_model || "")}', true, 'availMsg')">Pas une machine</button>`)
      : "";
    return `
    <tr>
      <td class="dot-col">
        <span class="status-cell" title="${esc(stateTitle)}">
          <span class="status-dot ${dotClass}"></span>
        </span>
      </td>
      <td><input id="pid-${rowId}" placeholder="PRN-01" value="${esc(d.printer_id || "")}" /></td>
      <td><input id="model-${rowId}" list="modelOptions" placeholder="MK4S" value="${esc(d.printer_model || d.detected_model || "")}" /></td>
      <td>${supportLabel(d.detected_adapter)}</td>
      <td>
        <span class="info-wrap">
          <span class="info-icon" tabindex="0" aria-label="Infos reseau">i</span>
          <span class="tooltip">${esc(networkTitle)}</span>
        </span>
      </td>
      <td>
        <div class="actions">
          <button ${hasMac ? "" : "disabled"} onclick="saveBinding('${esc(d.device_mac || "")}', '${rowId}', 'availMsg', '${esc(d.device_ip || "")}', '${esc(d.device_serial || "")}', '${esc(d.detected_adapter || "")}')">Binder</button>
          ${isIgnoredDevice(d) ? '<span class="chip-muted">non machine</span>' : ""}
          ${ignoreBtn}
        </div>
      </td>
    </tr>`;
  }).join("");

  document.querySelector("#boundTable tbody").innerHTML = bound.map((d, idx) => {
    const rowId = `b-${idx}`;
    const live = machineStateByPrinter.get(String(d.printer_id || "")) || {};
    const status = live.status || d.status;
    const hb = live.last_heartbeat_at || d.last_heartbeat_at;
    const dotClass = statusColor(status);
    const title = `Etat: ${fmt(status)} | Dernier ping: ${fmt(hb)}`;
    const networkTitle = `IP: ${fmt(d.device_ip)} | MAC: ${fmt(d.device_mac)} | Serial: ${fmt(d.device_serial)}`;
    const ignoreBtn = canIgnoreDevice(d)
      ? `<button class="btn-secondary" onclick="setIgnored(${Number(d.device_id) || 0}, '${esc(d.device_mac || "")}', '${esc(d.device_ip || "")}', '${esc(d.device_serial || "")}', '${esc(d.detected_adapter || "")}', '${esc(d.detected_model || "")}', true, 'boundMsg')">Pas une machine</button>`
      : "";
    const printerId = String(d.printer_id || "");
    return `
    <tr>
      <td class="dot-col">
        <span class="status-cell" title="${esc(title)}">
          <span class="status-dot ${dotClass}"></span>
        </span>
      </td>
      <td><input id="pid-${rowId}" value="${esc(d.printer_id || "")}" /></td>
      <td><input id="model-${rowId}" list="modelOptions" placeholder="MK4S" value="${esc(d.printer_model || d.detected_model || "")}" /></td>
      <td>${supportLabel(d.detected_adapter)}</td>
      <td>
        <span class="info-wrap">
          <span class="info-icon" tabindex="0" aria-label="Infos reseau">i</span>
          <span class="tooltip">${esc(networkTitle)}</span>
        </span>
      </td>
      <td>
        <div class="actions">
          <button onclick="saveBinding('${esc(d.device_mac || "")}', '${rowId}', 'boundMsg', '${esc(d.device_ip || "")}', '${esc(d.device_serial || "")}', '${esc(d.detected_adapter || "")}')">Sauver</button>
          <button class="btn-danger" ${printerId ? "" : "disabled"} onclick="deleteBinding('${esc(printerId)}', 'boundMsg')">Supprimer binding</button>
          ${ignoreBtn}
        </div>
      </td>
    </tr>`;
  }).join("");
}

function connectDevicesWs() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/devices`);
  ws.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data);
      if (message.event === "devices_snapshot" && Array.isArray(message.payload)) {
        renderDevices(message.payload);
      }
    } catch (_) {
      // ignore malformed frames
    }
  };
  ws.onclose = () => setTimeout(connectDevicesWs, 1200);
  ws.onerror = () => ws.close();
}

function connectMachinesWs() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/machines`);
  ws.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data);
      if ((message.event === "machines_snapshot" || message.event === "machines_updated") && Array.isArray(message.payload)) {
        for (const row of message.payload) {
          if (!row?.printer_id) continue;
          machineStateByPrinter.set(String(row.printer_id), row);
        }
        renderDevices(latestRows);
      }
    } catch (_) {
      // ignore malformed frames
    }
  };
  ws.onclose = () => setTimeout(connectMachinesWs, 1200);
  ws.onerror = () => ws.close();
}

connectDevicesWs();
connectMachinesWs();
syncShowAllButton();
