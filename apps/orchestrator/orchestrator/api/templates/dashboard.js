function computeBasePath() {
  const path = String(location.pathname || "");
  const match = path.match(/^(.*)\/dashboard\/?$/);
  if (match) return match[1] || "";
  return "";
}

const BASE_PATH = computeBasePath();

function apiUrl(path) {
  const clean = String(path || "");
  if (!clean.startsWith("/")) return `${BASE_PATH}/${clean}`;
  return `${BASE_PATH}${clean}`;
}

async function api(path, opts = {}) {
  const { timeout_ms, ...fetchOpts } = opts;
  const timeoutMs = Number(timeout_ms) || 0;
  const controller = timeoutMs > 0 ? new AbortController() : null;
  const timeout = controller ? setTimeout(() => controller.abort(), timeoutMs) : null;
  const r = await fetch(apiUrl(path), {
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

function deviceKey(row) {
  return String(row?.device_mac || row?.device_serial || row?.device_ip || "").trim();
}

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

function iconButton({ kind = "", title = "", label = "", disabled = false, onclick = "" } = {}, svg = "") {
  return `<button class="action-btn ${kind}" title="${esc(title)}" aria-label="${esc(label || title)}" ${disabled ? "disabled" : ""} onclick="${onclick}">${svg}</button>`;
}

function saveIcon(onclick = "", kind = "") {
  return iconButton(
    { kind, title: "Sauver", label: "Sauver", onclick },
    `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4h11l3 3v13H5zM8 4v6h8V4M9 20v-6h6v6"/></svg>`
  );
}

function deleteIcon(disabled = false, onclick = "") {
  return iconButton(
    { kind: "danger", title: "Supprimer", label: "Supprimer", disabled, onclick },
    `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3M8 7v13M12 7v13M16 7v13M6 7l1 13h10l1-13"/></svg>`
  );
}

function bindIcon(disabled = false, onclick = "") {
  return iconButton(
    { title: "Binder", label: "Binder", disabled, onclick },
    `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 13a5 5 0 0 1 0-7l1.5-1.5a5 5 0 0 1 7 7L17 13M14 11a5 5 0 0 1 0 7L12.5 19.5a5 5 0 0 1-7-7L7 11"/></svg>`
  );
}

function ignoreIcon(isIgnored = false, onclick = "", target = "") {
  const title = isIgnored ? "Ne plus ignorer" : "Ignorer";
  const svg = isIgnored
    ? `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6"/><circle cx="12" cy="12" r="3.2"/><path d="M4 20 20 4"/></svg>`
    : `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 12s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6"/><circle cx="12" cy="12" r="3.2"/><path d="M4 4 20 20"/></svg>`;
  return iconButton(
    { kind: "secondary", title, label: title, onclick },
    svg
  );
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

function isActiveStatus(status) {
  const value = String(status || "").toUpperCase();
  return ["PRINTING", "IN_USE", "BUSY", "RUNNING"].includes(value);
}

function numFmt(value, unit) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "-";
  return `${n.toFixed(1)}${unit}`;
}

function fmtDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return fmt(value);
  return date.toLocaleString("fr-FR");
}

function infoTooltip(lines) {
  const content = (lines || [])
    .map((line) => esc(line))
    .join("<br />");
  return `
    <span class="info-wrap">
      <span class="info-icon" aria-hidden="true">i</span>
      <span class="tooltip">${content}</span>
    </span>
  `;
}

function inlineNetworkInfo(row) {
  return `${fmt(row.device_ip)} | ${fmt(row.device_mac)}`;
}

function renderOngoingJobs(rows) {
  const active = (rows || []).filter((d) => {
    if (!d.is_bound) return false;
    const status = d.status;
    const jobId = d.current_job_id;
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
    const status = d.status;
    const currentJobId = d.current_job_id;
    const progress = Math.max(0, Math.min(100, Number(d.progress_pct) || 0));
    const nozzle = d.nozzle_temp_c;
    const bed = d.bed_temp_c;
    const hb = d.last_heartbeat_at;
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

async function saveBinding(mac, rowId, msgId, deviceIp = "", detectedAdapter = "") {
  const pid = document.getElementById(`pid-${rowId}`).value.trim();
  const modelInput = document.getElementById(`model-${rowId}`);
  const model = modelInput ? modelInput.value.trim() : "";
  const msg = document.getElementById(msgId);
  if (!pid) {
    msg.textContent = "id metier requis";
    return;
  }
  try {
    await api(`/bindings/${encodeURIComponent(mac)}`, {
      method: "PUT",
      body: JSON.stringify({
        printer_id: pid,
        printer_mac: mac,
        printer_ip: deviceIp || null,
        printer_model: model || null,
        adapter_name: detectedAdapter || null,
        is_ignored: false,
      }),
    });
    msg.textContent = "OK";
  } catch (e) {
    msg.textContent = e.message;
  }
}

async function setIgnored(deviceId, deviceMac, deviceIp, detectedAdapter, detectedModel, isIgnored, msgId) {
  const msg = document.getElementById(msgId);
  try {
    await api(`/bindings/${encodeURIComponent(deviceMac)}`, {
      method: "PUT",
      body: JSON.stringify({
        printer_id: null,
        printer_mac: deviceMac,
        printer_ip: deviceIp || null,
        printer_model: detectedModel || null,
        adapter_name: detectedAdapter || null,
        is_ignored: isIgnored,
      }),
    });
    msg.textContent = isIgnored ? "Device masque" : "Device restaure";
  } catch (e) {
    msg.textContent = e.message;
  }
}

async function deleteBinding(deviceMac, msgId) {
  const msg = document.getElementById(msgId);
  const mac = String(deviceMac || "").trim();
  if (!mac) {
    msg.textContent = "device_mac manquant";
    return;
  }
  try {
    await api(`/bindings/${encodeURIComponent(mac)}`, { method: "DELETE" });
    msg.textContent = `Binding supprime: ${mac}`;
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
    const out = await api("/devices/discover", { method: "POST", timeout_ms: 300000 });
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
  const available = (rows || []).filter((d) => !d.is_bound && !isIgnoredDevice(d));
  const bound = (rows || []).filter((d) => d.is_bound && !isIgnoredDevice(d));
  const ignored = (rows || []).filter((d) => isIgnoredDevice(d));
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
    const status = d.status;
    const hb = d.last_heartbeat_at;
    const dotClass = statusColor(status);
    const stateTitle = `Etat: ${fmt(status)} | Dernier ping: ${fmt(hb)}`;
    const statusInfo = inlineNetworkInfo(d);
    const ignoreBtn = canIgnoreDevice(d)
      ? ignoreIcon(
          isIgnoredDevice(d),
          `setIgnored(${Number(d.device_id) || 0}, '${esc(d.device_mac || "")}', '${esc(d.device_ip || "")}', '${esc(d.detected_adapter || "")}', '${esc(d.detected_model || "")}', ${isIgnoredDevice(d) ? "false" : "true"}, 'availMsg')`
        )
      : "";
    return `
    <tr>
      <td class="dot-col">
        <span class="status-cell" title="${esc(stateTitle)}">
          <span class="status-dot ${dotClass}"></span>
          <span class="status-inline">${esc(statusInfo)}</span>
        </span>
      </td>
      <td><input class="compact-input" id="pid-${rowId}" placeholder="PRN-01" value="${esc(d.printer_id || "")}" /></td>
      <td><input class="compact-input" id="model-${rowId}" list="modelOptions" placeholder="MK4S" value="${esc(d.printer_model || d.detected_model || "")}" /></td>
      <td>${supportLabel(d.detected_adapter)}</td>
      <td>
        <div class="actions">
          ${bindIcon(
            !hasMac,
            `saveBinding('${esc(d.device_mac || "")}', '${rowId}', 'availMsg', '${esc(d.device_ip || "")}', '${esc(d.detected_adapter || "")}')`
          )}
          ${ignoreBtn}
        </div>
      </td>
    </tr>`;
  }).join("");

  document.querySelector("#boundTable tbody").innerHTML = bound.map((d, idx) => {
    const rowId = `b-${idx}`;
    const status = d.status;
    const hb = d.last_heartbeat_at;
    const dotClass = statusColor(status);
    const title = `Etat: ${fmt(status)} | Dernier ping: ${fmt(hb)}`;
    const ignoreBtn = canIgnoreDevice(d)
      ? ignoreIcon(
          false,
          `setIgnored(${Number(d.device_id) || 0}, '${esc(d.device_mac || "")}', '${esc(d.device_ip || "")}', '${esc(d.detected_adapter || "")}', '${esc(d.detected_model || "")}', true, 'boundMsg')`
        )
      : "";
    const deviceMac = String(d.device_mac || "");
    return `
    <tr>
      <td class="dot-col">
        <span class="status-cell" title="${esc(title)}">
          <span class="status-dot ${dotClass}"></span>
          ${infoTooltip([
            `IP: ${fmt(d.device_ip)}`,
            `MAC: ${fmt(d.device_mac)}`,
            `Dernier ping: ${fmtDateTime(hb)}`,
          ])}
        </span>
      </td>
      <td><input class="compact-input" id="pid-${rowId}" value="${esc(d.printer_id || "")}" /></td>
      <td><input class="compact-input" id="model-${rowId}" list="modelOptions" placeholder="MK4S" value="${esc(d.printer_model || d.detected_model || "")}" /></td>
      <td>${supportLabel(d.detected_adapter)}</td>
      <td>
        <div class="actions">
          ${saveIcon(`saveBinding('${esc(d.device_mac || "")}', '${rowId}', 'boundMsg', '${esc(d.device_ip || "")}', '${esc(d.detected_adapter || "")}')`)}
          ${deleteIcon(!deviceMac, `deleteBinding('${esc(deviceMac)}', 'boundMsg')`)}
          ${ignoreBtn}
        </div>
      </td>
    </tr>`;
  }).join("");

  document.querySelector("#ignoredTable tbody").innerHTML = ignored.map((d) => {
    const status = d.status;
    const hb = d.last_heartbeat_at;
    const dotClass = statusColor(status);
    const title = `Etat: ${fmt(status)} | Dernier ping: ${fmt(hb)}`;
    return `
    <tr>
      <td class="dot-col">
        <span class="status-cell" title="${esc(title)}">
          <span class="status-dot ${dotClass}"></span>
          ${infoTooltip([
            `IP: ${fmt(d.device_ip)}`,
            `MAC: ${fmt(d.device_mac)}`,
            `Association: ${fmtDateTime(d.bound_at)}`,
          ])}
        </span>
      </td>
      <td>${supportLabel(d.detected_adapter)}</td>
      <td>
        <div class="actions">
          ${ignoreIcon(
            true,
            `setIgnored(${Number(d.device_id) || 0}, '${esc(d.device_mac || "")}', '${esc(d.device_ip || "")}', '${esc(d.detected_adapter || "")}', '${esc(d.detected_model || "")}', false, 'ignoredMsg')`
          )}
        </div>
      </td>
    </tr>`;
  }).join("");
}

function upsertDeviceRow(row) {
  const key = deviceKey(row);
  if (!key) return;
  const next = [...latestRows];
  const index = next.findIndex((item) => deviceKey(item) === key);
  if (index >= 0) next[index] = row;
  else next.push(row);
  renderDevices(next);
}

function removeDeviceRow(payload) {
  const key = String(payload?.device_key || payload?.device_mac || payload?.device_ip || "").trim();
  if (!key) return;
  renderDevices(latestRows.filter((item) => deviceKey(item) !== key));
}

function connectDevicesWs() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}${apiUrl("/devices/ws")}`);
  ws.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data);
      if (message.event === "devices_snapshot" && Array.isArray(message.payload)) {
        renderDevices(message.payload);
        return;
      }
      if (message.event === "device_added" && message.payload) {
        upsertDeviceRow(message.payload);
        return;
      }
      if (message.event === "device_binding_updated" && message.payload) {
        upsertDeviceRow(message.payload);
        return;
      }
      if (message.event === "device_state_updated" && message.payload) {
        upsertDeviceRow(message.payload);
        return;
      }
      if (message.event === "device_removed" && message.payload) {
        removeDeviceRow(message.payload);
      }
    } catch (_) {
        // ignore malformed frames
    }
  };
  ws.onclose = () => setTimeout(connectDevicesWs, 1200);
  ws.onerror = () => ws.close();
}

connectDevicesWs();
