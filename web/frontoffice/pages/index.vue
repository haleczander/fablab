<template>
  <main class="wrap">
    <section class="hero">
      <h1>FabLab JUNIA ISEN</h1>
      <p>
        Site vitrine du FabLab avec etat des machines en temps reel.
      </p>
    </section>

    <section class="grid">
      <article class="card">
        <h2>Disponibilite par modele</h2>
        <div class="models">
          <article v-for="model in groupedModels" :key="model.name" class="model">
            <h3>{{ model.name }}</h3>
            <p class="stats">
              Dispo: {{ model.dispo }} | Utilise: {{ model.utilise }} | En cours: {{ model.enCours }}
            </p>
          </article>
          <p v-if="groupedModels.length === 0" class="small">Aucune machine visible.</p>
        </div>
      </article>

      <aside class="card">
        <h2>Etat du flux</h2>
        <div class="kpi">
          <div class="kpi-row">
            <span>Canal</span>
            <span class="status" :class="wsOnline ? 'ok' : 'busy'">
              {{ wsOnline ? "WebSocket" : "Deconnecte" }}
            </span>
          </div>
          <div class="kpi-row">
            <span>Total machines</span>
            <strong>{{ printers.length }}</strong>
          </div>
          <div class="kpi-row">
            <span>Derniere maj</span>
            <strong>{{ lastUpdateLabel }}</strong>
          </div>
        </div>
      </aside>
    </section>
  </main>
</template>

<script setup lang="ts">
type PrinterRow = {
  machine_id?: string
  status?: string
  model?: string
}

type WsEvent = {
  event: string
  payload: unknown
}

const config = useRuntimeConfig()
const backendBase = config.public.backendBase as string

const printers = ref<PrinterRow[]>([])
const wsOnline = ref(false)
const lastUpdate = ref<Date | null>(null)

let machineWs: WebSocket | null = null

const groupedModels = computed(() => {
  const groups = new Map<string, { dispo: number; utilise: number; enCours: number }>()

  for (const printer of printers.value) {
    const name = printer.model || "Modele non renseigne"
    if (!groups.has(name)) {
      groups.set(name, { dispo: 0, utilise: 0, enCours: 0 })
    }

    const bucket = classifyStatus(printer.status)
    const counters = groups.get(name)
    if (!counters) continue

    if (bucket === "dispo") counters.dispo += 1
    if (bucket === "utilise") counters.utilise += 1
    if (bucket === "en_cours") counters.enCours += 1
  }

  return [...groups.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([name, data]) => ({ name, ...data }))
})

const lastUpdateLabel = computed(() => {
  if (!lastUpdate.value) return "-"
  return lastUpdate.value.toLocaleTimeString("fr-FR")
})

function classifyStatus(status?: string): "dispo" | "utilise" | "en_cours" {
  const value = String(status || "").toUpperCase()
  if (value === "PRINTING" || value === "RUNNING") return "en_cours"
  if (value === "IN_USE" || value === "BUSY") return "utilise"
  if (value === "IDLE" || value === "READY" || value === "AVAILABLE" || value === "ON") return "dispo"
  return "utilise"
}

function markUpdate(): void {
  lastUpdate.value = new Date()
}

function wsUrlFromBase(base: string): string {
  return base.replace(/^http/, "ws") + "/ws/machines"
}

function connectWebSocket(): void {
  const ws = new WebSocket(wsUrlFromBase(backendBase))
  machineWs = ws

  ws.onopen = () => {
    wsOnline.value = true
  }

  ws.onmessage = (event) => {
    let message: WsEvent
    try {
      message = JSON.parse(event.data) as WsEvent
    } catch {
      return
    }

    if ((message.event === "machines_snapshot" || message.event === "machines_updated") && Array.isArray(message.payload)) {
      printers.value = message.payload as PrinterRow[]
      markUpdate()
    }
  }

  ws.onclose = () => {
    wsOnline.value = false
    if (machineWs === ws) machineWs = null
    setTimeout(connectWebSocket, 1500)
  }

  ws.onerror = () => ws.close()
}

onMounted(() => {
  connectWebSocket()
})

onBeforeUnmount(() => {
  machineWs?.close()
})
</script>
