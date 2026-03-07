<template>
  <article class="fo-block" :class="[`kind-${block.kind}`, { 'kind-container': block.kind === 'container' }]" :style="blockStyle(section, block)">
    <template v-if="block.kind === 'machines_feed'">
      <MachinesFeed :title="block.title" />
    </template>

    <template v-else-if="block.kind === 'image'">
      <figure v-if="block.image_url" class="fo-image">
        <img :src="block.image_url" :alt="block.title" />
      </figure>
    </template>

    <template v-else-if="block.kind === 'banner'">
      <div class="fo-banner" :style="bannerStyle(block)">
        <p v-if="block.body" class="fo-block-copy">{{ block.body }}</p>
      </div>
    </template>

    <template v-else-if="block.kind === 'heading'">
      <component :is="`h${block.heading_level || 2}`" v-if="block.title" class="fo-heading">{{ block.title }}</component>
    </template>

    <template v-else-if="block.kind === 'container'">
      <div class="fo-container">
        <CmsBlockNode
          v-for="child in block.children"
          :key="child.id"
          :block="child"
          :section="section"
          :sections="sections"
        />
      </div>
    </template>

    <template v-else>
      <div v-if="block.title" class="fo-block-head">
        <strong>{{ block.title }}</strong>
      </div>
      <p v-if="block.body" class="fo-block-copy">{{ block.body }}</p>
      <NuxtLink
        v-if="targetPath(block.link_to_section_id)"
        :to="targetPath(block.link_to_section_id) || '/'"
        class="fo-block-link"
      >
        Voir la section
      </NuxtLink>
    </template>
  </article>
</template>

<script setup lang="ts">
defineOptions({ name: "CmsBlockNode" })

type LayoutMode = "vertical" | "horizontal" | "grid"
type TextAlign = "left" | "center" | "right"
type BlockKind = "heading" | "text" | "links" | "cta" | "machines_feed" | "image" | "banner" | "container" | "custom"

type CmsBlock = {
  id: string
  title: string
  body: string | null
  image_url: string | null
  kind: BlockKind
  heading_level: number
  span_cols: number
  span_rows: number
  padding: number
  margin_top: number
  margin_bottom: number
  font_size: number
  font_family: string | null
  text_color: string | null
  background_color: string | null
  border_color: string | null
  border_width: number
  border_radius: number
  text_align: TextAlign
  link_to_section_id: string | null
  container_layout: LayoutMode
  container_columns: number
  container_gap: number
  children: CmsBlock[]
}

type CmsSection = {
  id: string
  title: string
  slug: string
  nav_label?: string | null
  nav_group?: string | null
  layout: LayoutMode
  columns: number
  rows: number
  gap: number
  padding: number
  margin_top: number
  margin_bottom: number
  blocks: CmsBlock[]
}

const props = defineProps<{
  block: CmsBlock
  section: CmsSection
  sections: CmsSection[]
}>()

function blockStyle(section: CmsSection, block: CmsBlock): Record<string, string> {
  const style: Record<string, string> = {
    padding: `${block.kind === "banner" || block.kind === "image" ? 0 : block.padding || 0}px`,
    marginTop: `${block.margin_top || 0}px`,
    marginBottom: `${block.margin_bottom || 0}px`,
    fontSize: `${block.font_size || 16}px`,
  }
  if (block.font_family) style.fontFamily = block.font_family
  if (block.text_color) style.color = block.text_color
  if (block.background_color) style.backgroundColor = block.background_color
  if ((block.border_width || 0) > 0) {
    style.borderWidth = `${block.border_width}px`
    style.borderStyle = "solid"
  }
  if (block.border_color) style.borderColor = block.border_color
  if ((block.border_radius || 0) > 0) style.borderRadius = `${block.border_radius}px`
  style.textAlign = block.text_align || "left"
  if (block.kind === "container") {
    Object.assign(style, containerStyle(block))
  }
  if (section.layout !== "grid") return style
  return {
    ...style,
    gridColumn: `span ${Math.max(1, block.span_cols)}`,
    gridRow: `span ${Math.max(1, block.span_rows)}`,
  }
}

function bannerStyle(block: CmsBlock): Record<string, string> {
  return {
    background: block.image_url
      ? `linear-gradient(rgba(23,36,25,0.42), rgba(23,36,25,0.24)), url("${block.image_url}") center / cover`
      : "linear-gradient(135deg, rgba(138,75,42,0.92), rgba(11,110,105,0.92))",
    padding: "0px",
  }
}

function containerStyle(block: CmsBlock): Record<string, string> {
  if (block.container_layout === "grid") {
    return {
      display: "grid",
      gap: `${block.container_gap || 0}px`,
      gridTemplateColumns: `repeat(${Math.max(1, block.container_columns || 1)}, minmax(0, 1fr))`,
      gridAutoRows: "minmax(120px, auto)",
    }
  }
  if (block.container_layout === "horizontal") {
    return {
      display: "grid",
      gap: `${block.container_gap || 0}px`,
      gridAutoFlow: "column",
      gridAutoColumns: "minmax(280px, 1fr)",
      overflowX: "auto",
    }
  }
  return {
    display: "grid",
    gap: `${block.container_gap || 0}px`,
  }
}

function targetPath(targetId: string | null): string | null {
  if (!targetId) return null
  const target = props.sections.find((section) => section.id === targetId)
  if (!target) return null
  return `/${target.slug}`
}
</script>
