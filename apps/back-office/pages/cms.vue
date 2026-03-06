<template>
  <main class="bo-wrap cms-studio">
    <header class="hero">
      <div>
        <h1>CMS Studio</h1>
        <p>Edition dans l'apercu, reglages a droite.</p>
      </div>
      <div class="hero-actions">
        <button class="ghost" :disabled="busy" @click="reload">Recharger</button>
        <button class="ghost" :disabled="busy" @click="saveDraft">Sauvegarder</button>
        <button :disabled="busy" @click="publish">Publier</button>
      </div>
    </header>

    <section class="meta card">
      <p><strong>Version publiee:</strong> {{ bundle?.published_version ?? "-" }}</p>
      <p><strong>Derniere mise a jour:</strong> {{ fmtDate(bundle?.updated_at) }}</p>
      <p><strong>Derniere publication:</strong> {{ fmtDate(bundle?.published_at) }}</p>
      <p class="msg" :class="msgType">{{ msg }}</p>
    </section>

    <section class="studio-layout">
      <article class="card studio-canvas">
        <div class="studio-toolbar">
          <div class="tabs">
            <span v-for="item in navPreviewItems" :key="item.key">{{ item.label }}</span>
          </div>
          <button class="small" :disabled="busy" @click="addSection">Ajouter section</button>
        </div>

        <div class="block-palette">
          <button v-for="type in blockPalette" :key="type.kind" class="palette-chip" draggable="true" @dragstart="onPaletteDragStart(type.kind)">
            {{ type.label }}
          </button>
        </div>

        <div class="canvas-stack">
          <article
            v-for="(section, sectionIndex) in draft.sections"
            :key="section.id"
            class="canvas-section"
            :class="{ selected: selection?.type === 'section' && selection.sectionId === section.id }"
            :style="sectionCardStyle(section)"
            draggable="true"
            @click="selectSection(section.id)"
            @dragstart="onSectionDragStart(sectionIndex)"
            @dragover.prevent
            @drop="onSectionDrop(sectionIndex)"
          >
            <header class="canvas-section-head">
              <div class="canvas-title-wrap">
                <input class="canvas-section-title" :value="section.title" @input="onSectionTitleInput(section.id, $event)" @click.stop />
                <p class="canvas-kicker">{{ section.nav_label || section.title }}</p>
              </div>
              <span>{{ layoutLabel(section.layout) }}</span>
            </header>

            <div class="canvas-grid" :style="sectionStyle(section)" @dragover.prevent @drop="onSectionCanvasDrop(sectionIndex)">
              <div v-if="section.blocks.length === 0" class="canvas-empty-drop" @dragover.prevent @drop="onEmptySectionDrop(sectionIndex)">
                Deposer un bloc ici
              </div>

              <template v-for="(block, blockIndex) in section.blocks" :key="block.id">
                <div class="canvas-drop-slot" :class="{ active: isDropTarget(sectionIndex, blockIndex) }" @dragover.prevent="setDropTarget(sectionIndex, blockIndex)" @drop="onBlockInsertDrop(sectionIndex, blockIndex)" />
                <article
                  class="canvas-block"
                  :class="{ selected: selection?.type === 'block' && selection.blockId === block.id }"
                  :style="blockStyle(section, block)"
                  draggable="true"
                  @click.stop="selectBlock(section.id, block.id)"
                  @dragstart="onBlockDragStart(sectionIndex, blockIndex)"
                  @dragover.prevent="setDropTarget(sectionIndex, blockIndex + 1)"
                  @drop="onBlockDrop(sectionIndex, blockIndex)"
                >
                  <template v-if="block.kind === 'machines_feed'">
                    <div class="canvas-block-head">
                      <input class="canvas-block-title" :value="block.title" @input="onBlockTitleInput(section.id, block.id, $event)" @click.stop />
                    </div>
                    <div class="block-preview-machine">
                      <div class="mini-kpi"><span>Etat des machines</span><span>WS live</span></div>
                      <div class="mini-bars"><i /><i /><i /></div>
                    </div>
                  </template>

                  <template v-else-if="block.kind === 'image'">
                    <input class="canvas-block-title" :value="block.title" @input="onBlockTitleInput(section.id, block.id, $event)" @click.stop />
                    <div class="block-preview-image" :class="{ empty: !block.image_url }">
                      <img v-if="block.image_url" :src="block.image_url" :alt="block.title" />
                      <span v-else>Image non renseignee</span>
                    </div>
                  </template>

                  <template v-else-if="block.kind === 'banner'">
                    <div class="block-preview-banner" :style="bannerStyle(block)">
                      <input class="canvas-block-title banner-title" :value="block.title" @input="onBlockTitleInput(section.id, block.id, $event)" @click.stop />
                      <textarea class="canvas-block-body banner-body" :value="block.body || ''" placeholder="Texte de banniere" @input="onBlockBodyInput(section.id, block.id, $event)" @click.stop />
                    </div>
                  </template>

                  <template v-else>
                    <input class="canvas-block-title" :value="block.title" @input="onBlockTitleInput(section.id, block.id, $event)" @click.stop />
                    <textarea class="canvas-block-body" :value="block.body || ''" :placeholder="bodyPlaceholder(block.kind)" @input="onBlockBodyInput(section.id, block.id, $event)" @click.stop />
                    <span v-if="block.link_to_section_id" class="block-link-badge">Lien vers une autre section</span>
                  </template>
                </article>
              </template>

              <div v-if="section.blocks.length > 0" class="canvas-drop-slot tail" :class="{ active: isDropTarget(sectionIndex, section.blocks.length) }" @dragover.prevent="setDropTarget(sectionIndex, section.blocks.length)" @drop="onBlockInsertDrop(sectionIndex, section.blocks.length)" />
            </div>
          </article>
        </div>
      </article>

      <aside class="card studio-inspector">
        <div class="inspector-head">
          <h2>Edition</h2>
          <button v-if="selection?.type === 'section'" class="small danger" :disabled="busy" @click="removeSelectedSection">Supprimer section</button>
          <button v-if="selection?.type === 'block'" class="small danger" :disabled="busy" @click="removeSelectedBlock">Supprimer bloc</button>
        </div>

        <div v-if="!selection" class="empty">Selectionnez une section ou un bloc dans l'apercu.</div>

        <template v-else-if="selection.type === 'section' && selectedSection">
          <details class="inspector-panel" open>
            <summary>Navigation</summary>
            <div class="inspector-panel-body">
              <label><span>Slug</span><input v-model="selectedSection.slug" @input="touch" /></label>
              <label><span>Titre navigation</span><input v-model="selectedSection.nav_label" @input="touch" placeholder="Par defaut: titre section" /></label>
              <label><span>Groupe navigation</span><input v-model="selectedSection.nav_group" @input="touch" placeholder="Ex: Services" /></label>
              <label class="toggle"><input v-model="selectedSection.show_in_nav" type="checkbox" @change="touch" /><span>Afficher dans menu</span></label>
            </div>
          </details>

          <details class="inspector-panel" open>
            <summary>Disposition</summary>
            <div class="inspector-panel-body">
              <label>
                <span>Mode</span>
                <select v-model="selectedSection.layout" @change="touch">
                  <option value="vertical">Flex vertical</option>
                  <option value="horizontal">Flex horizontal</option>
                  <option value="grid">Grid</option>
                </select>
              </label>
              <label><span>Gap</span><input v-model.number="selectedSection.gap" type="number" min="0" max="80" @input="touch" /></label>
              <div class="fields three">
                <label><span>Padding</span><input v-model.number="selectedSection.padding" type="number" min="0" max="120" @input="touch" /></label>
                <label><span>Marge haute</span><input v-model.number="selectedSection.margin_top" type="number" min="0" max="160" @input="touch" /></label>
                <label><span>Marge basse</span><input v-model.number="selectedSection.margin_bottom" type="number" min="0" max="160" @input="touch" /></label>
              </div>
              <div class="fields two" v-if="selectedSection.layout === 'grid'">
                <label><span>Colonnes</span><input v-model.number="selectedSection.columns" type="number" min="1" max="6" @input="touch" /></label>
                <label><span>Lignes</span><input v-model.number="selectedSection.rows" type="number" min="1" max="12" @input="touch" /></label>
              </div>
              <label class="toggle"><input v-model="selectedSection.show_in_home" type="checkbox" @change="touch" /><span>Afficher sur accueil</span></label>
            </div>
          </details>
        </template>

        <template v-else-if="selection.type === 'block' && selectedBlock && selectedSection">
          <details class="inspector-panel" open>
            <summary>Bloc</summary>
            <div class="inspector-panel-body">
              <label>
                <span>Type</span>
                <select v-model="selectedBlock.kind" @change="touch">
                  <option value="text">Texte</option>
                  <option value="links">Liens</option>
                  <option value="cta">CTA</option>
                  <option value="machines_feed">Etat des machines</option>
                  <option value="image">Image</option>
                  <option value="banner">Banniere</option>
                  <option value="custom">Libre</option>
                </select>
              </label>
              <label v-if="selectedBlock.kind === 'image' || selectedBlock.kind === 'banner'"><span>URL image</span><input v-model="selectedBlock.image_url" @input="touch" placeholder="https://..." /></label>
              <label><span>Lien vers section</span><select v-model="selectedBlock.link_to_section_id" @change="touch"><option :value="null">Aucun</option><option v-for="target in sectionTargets(selectedSection.id)" :key="target.id" :value="target.id">{{ target.title }}</option></select></label>
            </div>
          </details>

          <details class="inspector-panel" open>
            <summary>Style</summary>
            <div class="inspector-panel-body">
              <div class="fields three">
                <label><span>Padding</span><input v-model.number="selectedBlock.padding" type="number" min="0" max="120" @input="touch" /></label>
                <label><span>Marge haute</span><input v-model.number="selectedBlock.margin_top" type="number" min="0" max="160" @input="touch" /></label>
                <label><span>Marge basse</span><input v-model.number="selectedBlock.margin_bottom" type="number" min="0" max="160" @input="touch" /></label>
              </div>
              <div class="fields two">
                <label><span>Taille police</span><input v-model.number="selectedBlock.font_size" type="number" min="10" max="64" @input="touch" /></label>
                <label><span>Police</span><input v-model="selectedBlock.font_family" @input="touch" placeholder="Ex: Georgia, serif" /></label>
              </div>
            </div>
          </details>

          <details class="inspector-panel" open v-if="selectedSection.layout === 'grid'">
            <summary>Placement grid</summary>
            <div class="inspector-panel-body">
              <div class="fields two">
                <label><span>Span colonnes</span><input v-model.number="selectedBlock.span_cols" type="number" min="1" max="6" @input="touch" /></label>
                <label><span>Span lignes</span><input v-model.number="selectedBlock.span_rows" type="number" min="1" max="12" @input="touch" /></label>
              </div>
            </div>
          </details>
        </template>
      </aside>
    </section>
  </main>
</template>

<script setup lang="ts">
type LayoutMode = "vertical" | "horizontal" | "grid"
type BlockKind = "text" | "links" | "cta" | "machines_feed" | "image" | "banner" | "custom"
type CmsBlock = { id: string; title: string; body: string | null; image_url: string | null; kind: BlockKind; span_cols: number; span_rows: number; padding: number; margin_top: number; margin_bottom: number; font_size: number; font_family: string | null; link_to_section_id: string | null }
type CmsSection = { id: string; title: string; slug: string; show_in_nav: boolean; nav_label: string | null; nav_group: string | null; show_in_home: boolean; layout: LayoutMode; columns: number; rows: number; gap: number; padding: number; margin_top: number; margin_bottom: number; blocks: CmsBlock[] }
type CmsDraft = { sections: CmsSection[] }
type CmsSiteBundle = { draft: CmsDraft; published: CmsDraft; published_version: number; updated_at: string | null; published_at: string | null }
type Selection = { type: "section"; sectionId: string } | { type: "block"; sectionId: string; blockId: string }

const config = useRuntimeConfig()
const backendBase = config.public.backendBase as string
const draft = reactive<CmsDraft>({ sections: [] })
const bundle = ref<CmsSiteBundle | null>(null)
const busy = ref(false)
const dirty = ref(false)
const msg = ref("")
const msgType = ref("")
const selection = ref<Selection | null>(null)
const sectionDragIndex = ref<number | null>(null)
const blockDrag = ref<{ sectionIndex: number; blockIndex: number } | null>(null)
const paletteDragKind = ref<BlockKind | null>(null)
const dropTarget = ref<{ sectionIndex: number; blockIndex: number } | null>(null)

const blockPalette = [
  { kind: "text", label: "Bloc texte" },
  { kind: "links", label: "Bloc liens" },
  { kind: "cta", label: "Bloc CTA" },
  { kind: "machines_feed", label: "Etat des machines" },
  { kind: "image", label: "Image" },
  { kind: "banner", label: "Banniere" },
  { kind: "custom", label: "Bloc libre" },
] as const

const navSections = computed(() => draft.sections.filter((section) => section.show_in_nav))
const navPreviewItems = computed(() => {
  const items: Array<{ key: string; label: string }> = []
  const groups = new Map<string, string[]>()
  for (const section of navSections.value) {
    const label = section.nav_label || section.title
    const group = (section.nav_group || "").trim()
    if (!group) items.push({ key: section.id, label })
    else {
      if (!groups.has(group)) groups.set(group, [])
      groups.get(group)?.push(label)
    }
  }
  for (const [group, labels] of groups.entries()) items.push({ key: group, label: `${group} / ${labels.join(", ")}` })
  return items
})
const selectedSection = computed(() => !selection.value ? null : draft.sections.find((section) => section.id === selection.value!.sectionId) || null)
const selectedBlock = computed(() => !selection.value || selection.value.type !== "block" ? null : selectedSection.value?.blocks.find((block) => block.id === selection.value!.blockId) || null)

function uid(prefix: string): string { return `${prefix}-${Math.random().toString(36).slice(2, 9)}` }
function slugify(value: string): string { return (value || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") }
function touch(): void { dirty.value = true }
function layoutLabel(layout: LayoutMode): string { return layout === "vertical" ? "flex vertical" : layout === "horizontal" ? "flex horizontal" : "grid" }
function bodyPlaceholder(kind: BlockKind): string { return kind === "links" ? "Liste de liens, une ligne par entree" : kind === "cta" ? "Texte d'accroche et appel a l'action" : kind === "text" ? "Texte du bloc" : kind === "banner" ? "Texte de banniere" : "Contenu du bloc" }
function fmtDate(value: string | null | undefined): string { if (!value) return "-"; const date = new Date(value); return Number.isNaN(date.valueOf()) ? String(value) : `${date.toLocaleDateString("fr-FR")} ${date.toLocaleTimeString("fr-FR")}` }
function isDropTarget(sectionIndex: number, blockIndex: number): boolean { return dropTarget.value?.sectionIndex === sectionIndex && dropTarget.value?.blockIndex === blockIndex }
function inputValue(event: Event): string { const target = event.target; return target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement ? target.value : "" }

async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${backendBase}${path}`, { headers: { "Content-Type": "application/json" }, ...options })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return (await response.json()) as T
}

function normalizeDraft(next: CmsDraft): CmsDraft {
  return {
    sections: next.sections.map((section) => ({
      ...section,
      nav_label: section.nav_label ?? null,
      nav_group: section.nav_group ?? null,
      padding: section.padding ?? 16,
      margin_top: section.margin_top ?? 0,
      margin_bottom: section.margin_bottom ?? 24,
      blocks: section.blocks.map((block) => ({
        ...block,
        body: block.body ?? null,
        image_url: block.image_url ?? null,
        padding: block.padding ?? 16,
        margin_top: block.margin_top ?? 0,
        margin_bottom: block.margin_bottom ?? 0,
        font_size: block.font_size ?? 16,
        font_family: block.font_family ?? null,
      })),
    })),
  }
}

function setDraft(next: CmsDraft): void { const normalized = normalizeDraft(next); draft.sections.splice(0, draft.sections.length, ...normalized.sections) }
async function reload(): Promise<void> { busy.value = true; try { const next = await api<CmsSiteBundle>("/cms/frontoffice"); bundle.value = next; setDraft(structuredClone(next.draft)); selection.value = draft.sections[0] ? { type: "section", sectionId: draft.sections[0].id } : null; dirty.value = false; msg.value = "Brouillon charge."; msgType.value = "ok" } catch (error) { msg.value = error instanceof Error ? error.message : "Erreur"; msgType.value = "err" } finally { busy.value = false } }
async function saveDraft(): Promise<void> { busy.value = true; try { const next = await api<CmsSiteBundle>("/cms/frontoffice/draft", { method: "PUT", body: JSON.stringify(draft) }); bundle.value = next; dirty.value = false; msg.value = "Brouillon sauvegarde."; msgType.value = "ok" } catch (error) { msg.value = error instanceof Error ? error.message : "Erreur"; msgType.value = "err" } finally { busy.value = false } }
async function publish(): Promise<void> { if (dirty.value) await saveDraft(); busy.value = true; try { const next = await api<CmsSiteBundle>("/cms/frontoffice/publish", { method: "POST" }); bundle.value = next; msg.value = "Publication effectuee."; msgType.value = "ok" } catch (error) { msg.value = error instanceof Error ? error.message : "Erreur"; msgType.value = "err" } finally { busy.value = false } }

function createSection(): CmsSection { const id = uid("section"); return { id, title: "Nouvelle section", slug: id, show_in_nav: true, nav_label: null, nav_group: null, show_in_home: true, layout: "vertical", columns: 1, rows: 1, gap: 16, padding: 16, margin_top: 0, margin_bottom: 24, blocks: [] } }
function defaultBodyForKind(kind: BlockKind): string | null { return kind === "machines_feed" || kind === "image" ? null : kind === "banner" ? "Texte de banniere" : kind === "links" ? "Lien 1\nLien 2" : kind === "cta" ? "Votre message d'action" : kind === "text" ? "Votre texte ici" : "Contenu" }
function createBlock(kind: BlockKind = "custom"): CmsBlock { return { id: uid("block"), title: kind === "machines_feed" ? "Etat des machines" : kind === "image" ? "Image" : kind === "banner" ? "Banniere" : "Nouveau bloc", body: defaultBodyForKind(kind), image_url: null, kind, span_cols: 1, span_rows: 1, padding: kind === "banner" ? 28 : 16, margin_top: 0, margin_bottom: 0, font_size: kind === "banner" ? 24 : 16, font_family: null, link_to_section_id: null } }
function addSection(): void { const section = createSection(); section.blocks.push(createBlock("text")); draft.sections.push(section); selection.value = { type: "section", sectionId: section.id }; touch() }
function selectSection(sectionId: string): void { selection.value = { type: "section", sectionId } }
function selectBlock(sectionId: string, blockId: string): void { selection.value = { type: "block", sectionId, blockId } }
function updateSectionTitle(sectionId: string, value: string): void { const section = draft.sections.find((item) => item.id === sectionId); if (!section) return; section.title = value; if (!section.slug || section.slug.startsWith("section-")) section.slug = slugify(value) || section.id; touch() }
function updateBlockTitle(sectionId: string, blockId: string, value: string): void { const block = draft.sections.find((item) => item.id === sectionId)?.blocks.find((item) => item.id === blockId); if (!block) return; block.title = value; touch() }
function updateBlockBody(sectionId: string, blockId: string, value: string): void { const block = draft.sections.find((item) => item.id === sectionId)?.blocks.find((item) => item.id === blockId); if (!block) return; block.body = value; touch() }
function onSectionTitleInput(sectionId: string, event: Event): void { updateSectionTitle(sectionId, inputValue(event)) }
function onBlockTitleInput(sectionId: string, blockId: string, event: Event): void { updateBlockTitle(sectionId, blockId, inputValue(event)) }
function onBlockBodyInput(sectionId: string, blockId: string, event: Event): void { updateBlockBody(sectionId, blockId, inputValue(event)) }
function removeSelectedSection(): void { if (!selectedSection.value) return; const index = draft.sections.findIndex((section) => section.id === selectedSection.value!.id); if (index < 0) return; draft.sections.splice(index, 1); selection.value = draft.sections[0] ? { type: "section", sectionId: draft.sections[0].id } : null; touch() }
function removeSelectedBlock(): void { if (!selectedSection.value || !selectedBlock.value) return; const index = selectedSection.value.blocks.findIndex((block) => block.id === selectedBlock.value!.id); if (index < 0) return; selectedSection.value.blocks.splice(index, 1); selection.value = { type: "section", sectionId: selectedSection.value.id }; touch() }
function onPaletteDragStart(kind: BlockKind): void { paletteDragKind.value = kind }
function setDropTarget(sectionIndex: number, blockIndex: number): void { dropTarget.value = { sectionIndex, blockIndex } }
function insertPaletteBlock(sectionIndex: number, blockIndex: number): void { if (!paletteDragKind.value) return; const section = draft.sections[sectionIndex]; if (!section) return; const block = createBlock(paletteDragKind.value); section.blocks.splice(blockIndex, 0, block); selection.value = { type: "block", sectionId: section.id, blockId: block.id }; paletteDragKind.value = null; dropTarget.value = null; touch() }
function onEmptySectionDrop(sectionIndex: number): void { insertPaletteBlock(sectionIndex, 0) }
function onSectionCanvasDrop(sectionIndex: number): void { if (draft.sections[sectionIndex]?.blocks.length === 0) insertPaletteBlock(sectionIndex, 0) }
function onBlockInsertDrop(sectionIndex: number, blockIndex: number): void { if (paletteDragKind.value) return insertPaletteBlock(sectionIndex, blockIndex); const source = blockDrag.value; blockDrag.value = null; dropTarget.value = null; if (!source || source.sectionIndex !== sectionIndex) return; const section = draft.sections[sectionIndex]; if (!section) return; const [item] = section.blocks.splice(source.blockIndex, 1); const insertIndex = source.blockIndex < blockIndex ? blockIndex - 1 : blockIndex; section.blocks.splice(insertIndex, 0, item); touch() }
function onSectionDragStart(sectionIndex: number): void { sectionDragIndex.value = sectionIndex }
function onSectionDrop(targetIndex: number): void { const sourceIndex = sectionDragIndex.value; sectionDragIndex.value = null; if (sourceIndex === null || sourceIndex === targetIndex) return; const [item] = draft.sections.splice(sourceIndex, 1); draft.sections.splice(targetIndex, 0, item); touch() }
function onBlockDragStart(sectionIndex: number, blockIndex: number): void { blockDrag.value = { sectionIndex, blockIndex } }
function onBlockDrop(sectionIndex: number, blockIndex: number): void { if (paletteDragKind.value) insertPaletteBlock(sectionIndex, blockIndex + 1); else setDropTarget(sectionIndex, blockIndex + 1) }
function sectionTargets(selfId: string): CmsSection[] { return draft.sections.filter((section) => section.id !== selfId) }
function sectionCardStyle(section: CmsSection): Record<string, string> { return { marginTop: `${section.margin_top}px`, marginBottom: `${section.margin_bottom}px` } }
function sectionStyle(section: CmsSection): Record<string, string> { if (section.layout === "grid") return { display: "grid", gap: `${section.gap}px`, gridTemplateColumns: `repeat(${Math.max(1, section.columns)}, minmax(0, 1fr))`, gridAutoRows: "minmax(140px, auto)", padding: `${section.padding}px` }; if (section.layout === "horizontal") return { display: "grid", gap: `${section.gap}px`, gridAutoFlow: "column", gridAutoColumns: "minmax(240px, 1fr)", overflowX: "auto", padding: `${section.padding}px` }; return { display: "grid", gap: `${section.gap}px`, padding: `${section.padding}px` } }
function blockStyle(section: CmsSection, block: CmsBlock): Record<string, string> { const style: Record<string, string> = { padding: `${block.padding}px`, marginTop: `${block.margin_top}px`, marginBottom: `${block.margin_bottom}px`, fontSize: `${block.font_size}px` }; if (block.font_family) style.fontFamily = block.font_family; if (section.layout !== "grid") return style; return { ...style, gridColumn: `span ${Math.max(1, block.span_cols)}`, gridRow: `span ${Math.max(1, block.span_rows)}` } }
function bannerStyle(block: CmsBlock): Record<string, string> { const background = block.image_url ? `linear-gradient(rgba(23,34,35,0.4), rgba(23,34,35,0.22)), url("${block.image_url}") center / cover` : "linear-gradient(135deg, rgba(13,102,96,0.92), rgba(11,74,70,0.92))"; const style: Record<string, string> = { background, padding: `${block.padding}px` }; if (block.font_family) style.fontFamily = block.font_family; return style }

watch(() => draft.sections.map((section) => section.title), () => { for (const section of draft.sections) { if (!section.slug || section.slug.startsWith("section-")) section.slug = slugify(section.title) || section.id } }, { deep: true })
onMounted(() => { reload() })
</script>
