<template>
  <section :id="section.slug" class="fo-section">
    <header v-if="hasVisibleSectionHeader(section)" class="fo-section-head">
      <h2>{{ section.title }}</h2>
    </header>

    <div class="fo-grid" :style="sectionStyle(section)">
      <CmsBlockNode
        v-for="block in section.blocks"
        :key="block.id"
        :block="block"
        :section="section"
        :sections="sections"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
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
  section: CmsSection
  sections: CmsSection[]
}>()

function hasVisibleSectionHeader(section: CmsSection): boolean {
  return Boolean((section.title || "").trim())
}

function sectionStyle(section: CmsSection): Record<string, string> {
  if (section.layout === "grid") {
    return {
      display: "grid",
      gap: `${section.gap}px`,
      gridTemplateColumns: `repeat(${Math.max(1, section.columns)}, minmax(0, 1fr))`,
      gridAutoRows: "minmax(120px, auto)",
      padding: `${section.padding || 0}px`,
    }
  }
  if (section.layout === "horizontal") {
    return {
      display: "grid",
      gap: `${section.gap}px`,
      gridAutoFlow: "column",
      gridAutoColumns: "minmax(280px, 1fr)",
      overflowX: "auto",
      padding: `${section.padding || 0}px`,
    }
  }
  return {
    display: "grid",
    gap: `${section.gap}px`,
    padding: `${section.padding || 0}px`,
  }
}

</script>
