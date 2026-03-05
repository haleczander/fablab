<template>
  <main class="container">
    <header>
      <h1 class="title">Backoffice Fablab</h1>
      <p class="subtitle">Nuxt 3 separé du backend API.</p>
    </header>

    <section class="grid">
      <article class="card">
        <h2>Enregistrer une imprimante</h2>
        <div class="row">
          <input v-model.trim="registerPrinterId" placeholder="PRN-01" />
          <button @click="registerPrinter">Enregistrer</button>
        </div>
        <p class="msg" :class="registerMsgType">{{ registerMsg }}</p>
      </article>

      <article class="card">
        <h2>Creer un job</h2>
        <div class="row">
          <input v-model.trim="jobPrinterId" placeholder="printer_id (PRN-01)" />
          <input v-model.trim="jobGcodeUrl" placeholder="https://.../piece.gcode" />
          <textarea v-model="jobParamsRaw" placeholder='{"layer_height": 0.2}'></textarea>
          <button @click="createJob">Ajouter a la file</button>
        </div>
        <p class="msg" :class="jobMsgType">{{ jobMsg }}</p>
      </article>
    </section>

    <section class="card">
      <h2>Etat imprimantes (source orchestrateur)</h2>
      <table>
        <thead>
          <tr>
            <th>machine_id</th>
            <th>ip</th>
            <th>modele</th>
            <th>status</th>
            <th>heartbeat</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="machines.length === 0">
            <td colspan="5" class="muted">Aucune imprimante</td>
          </tr>
          <tr v-for="p in machines" :key="p.machine_id">
            <td>{{ fmt(p.machine_id) }}</td>
            <td>{{ fmt(p.printer_ip) }}</td>
            <td>{{ fmt(p.model) }}</td>
            <td>{{ fmt(p.status) }}</td>
            <td>{{ fmt(p.last_heartbeat_at) }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="card">
      <h2>Jobs</h2>
      <table>
        <thead>
          <tr>
            <th>job_id</th>
            <th>printer_id</th>
            <th>status</th>
            <th>progress</th>
            <th>updated_at</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="jobs.length === 0">
            <td colspan="5" class="muted">Aucun job</td>
          </tr>
          <tr v-for="j in jobs" :key="j.job_id">
            <td>{{ fmt(j.job_id) }}</td>
            <td>{{ fmt(j.printer_id) }}</td>
            <td>{{ fmt(j.status) }}</td>
            <td>{{ fmt(j.progress_pct) }}</td>
            <td>{{ fmt(j.updated_at) }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </main>
</template>

<script setup lang="ts">
const config = useRuntimeConfig()
const backendBase = config.public.backendBase as string

type MachineRow = {
  machine_id: string
  printer_id?: string | null
  printer_ip?: string | null
  printer_model?: string | null
  model?: string | null
  status: string
  last_heartbeat_at?: string | null
}

type JobRow = {
  job_id: string
  printer_id: string
  status: string
  progress_pct?: number | null
  updated_at?: string | null
}

type WsEvent = {
  event: string
  payload: unknown
}

const machines = ref<MachineRow[]>([])
const jobs = ref<JobRow[]>([])

const registerPrinterId = ref("")
const registerMsg = ref("")
const registerMsgType = ref("")

const jobPrinterId = ref("")
const jobGcodeUrl = ref("")
const jobParamsRaw = ref('{"layer_height": 0.2}')
const jobMsg = ref("")
const jobMsgType = ref("")

let machinesWs: WebSocket | null = null
let jobsWs: WebSocket | null = null

function fmt(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-"
  return String(value)
}

function wsUrl(path: string): string {
  return backendBase.replace(/^http/, "ws") + path
}

async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${backendBase}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  })

  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const body = await response.json()
      if (body?.detail) detail = body.detail
    } catch {
      // ignore
    }
    throw new Error(detail)
  }

  if (response.status === 204) return null as T
  return (await response.json()) as T
}

function upsertMachine(row: MachineRow): void {
  const index = machines.value.findIndex((item) => item.machine_id === row.machine_id)
  if (index >= 0) {
    machines.value[index] = row
  } else {
    machines.value.push(row)
    machines.value.sort((a, b) => a.machine_id.localeCompare(b.machine_id))
  }
}

function upsertJob(row: JobRow): void {
  const index = jobs.value.findIndex((item) => item.job_id === row.job_id)
  if (index >= 0) {
    jobs.value[index] = row
  } else {
    jobs.value.unshift(row)
  }
}

function connectMachinesWs(): void {
  const ws = new WebSocket(wsUrl("/ws/machines"))
  machinesWs = ws

  ws.onmessage = (event) => {
    let message: WsEvent
    try {
      message = JSON.parse(event.data) as WsEvent
    } catch {
      return
    }

    if ((message.event === "machines_snapshot" || message.event === "machines_updated") && Array.isArray(message.payload)) {
      machines.value = message.payload as MachineRow[]
      return
    }

    if (message.payload) {
      upsertMachine(message.payload as MachineRow)
    }
  }

  ws.onclose = () => {
    if (machinesWs === ws) machinesWs = null
    setTimeout(connectMachinesWs, 1200)
  }

  ws.onerror = () => ws.close()
}

function connectJobsWs(): void {
  const ws = new WebSocket(wsUrl("/ws/jobs"))
  jobsWs = ws

  ws.onmessage = (event) => {
    let message: WsEvent
    try {
      message = JSON.parse(event.data) as WsEvent
    } catch {
      return
    }

    if (message.event === "snapshot" && Array.isArray(message.payload)) {
      jobs.value = message.payload as JobRow[]
      return
    }

    if ((message.event === "job_created" || message.event === "job_updated") && message.payload) {
      upsertJob(message.payload as JobRow)
    }
  }

  ws.onclose = () => {
    if (jobsWs === ws) jobsWs = null
    setTimeout(connectJobsWs, 1200)
  }

  ws.onerror = () => ws.close()
}

async function registerPrinter(): Promise<void> {
  if (!registerPrinterId.value) {
    registerMsg.value = "printer_id requis"
    registerMsgType.value = "err"
    return
  }

  try {
    await api<unknown>("/printers/register", {
      method: "POST",
      body: JSON.stringify({ printer_id: registerPrinterId.value }),
    })
    registerMsg.value = "Imprimante enregistree"
    registerMsgType.value = "ok"
  } catch (error) {
    registerMsg.value = error instanceof Error ? error.message : "Erreur"
    registerMsgType.value = "err"
  }
}

async function createJob(): Promise<void> {
  if (!jobPrinterId.value || !jobGcodeUrl.value) {
    jobMsg.value = "printer_id et gcode_url requis"
    jobMsgType.value = "err"
    return
  }

  let parameters: Record<string, unknown> = {}
  if (jobParamsRaw.value.trim()) {
    try {
      parameters = JSON.parse(jobParamsRaw.value) as Record<string, unknown>
    } catch {
      jobMsg.value = "JSON parametres invalide"
      jobMsgType.value = "err"
      return
    }
  }

  try {
    await api<unknown>("/jobs", {
      method: "POST",
      body: JSON.stringify({
        printer_id: jobPrinterId.value,
        gcode_url: jobGcodeUrl.value,
        parameters,
      }),
    })
    jobMsg.value = "Job cree"
    jobMsgType.value = "ok"
  } catch (error) {
    jobMsg.value = error instanceof Error ? error.message : "Erreur"
    jobMsgType.value = "err"
  }
}

onMounted(() => {
  connectMachinesWs()
  connectJobsWs()
})

onBeforeUnmount(() => {
  machinesWs?.close()
  jobsWs?.close()
})
</script>
