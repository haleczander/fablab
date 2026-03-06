<template>
  <section :id="section.slug" class="fo-section">
    <header class="fo-section-head">
      <h2>{{ section.title }}</h2>
    </header>

    <div class="fo-grid" :style="sectionStyle(section)">
      <article
        v-for="block in section.blocks"
        :key="block.id"
        class="fo-block"
        :class="`kind-${block.kind}`"
        :style="blockStyle(section, block)"
      >
        <template v-if="block.kind === 'machines_feed'">
          <MachinesFeed :title="block.title" />
        </template>

        <template v-else-if="block.kind === 'image'">
          <div class="fo-block-head">
            <strong>{{ block.title }}</strong>
          </div>
          <figure v-if="block.image_url" class="fo-image">
            <img :src="block.image_url" :alt="block.title" />
          </figure>
        </template>

        <template v-else-if="block.kind === 'banner'">
          <div class="fo-banner" :style="bannerStyle(block)">
            <div class="fo-block-head">
              <strong>{{ block.title }}</strong>
            </div>
            <p v-if="block.body" class="fo-block-copy">{{ block.body }}</p>
          </div>
        </template>

        <template v-else>
          <div class="fo-block-head">
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
    </div>
  </section>
</template>

<script setup lang="ts">
type LayoutMode = "vertical" | "horizontal" | "grid"
type BlockKind = "text" | "links" | "cta" | "machines_feed" | "image" | "banner" | "custom"

type CmsBlock = {
  id: string
  title: string
  body: string | null
  image_url: string | null
  kind: BlockKind
  span_cols: number
  span_rows: number
  padding: number
  margin_top: number
  margin_bottom: number
  font_size: number
  font_family: string | null
  link_to_section_id: string | null
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

function blockStyle(section: CmsSection, block: CmsBlock): Record<string, string> {
  const style: Record<string, string> = {
    padding: `${block.padding || 0}px`,
    marginTop: `${block.margin_top || 0}px`,
    marginBottom: `${block.margin_bottom || 0}px`,
    fontSize: `${block.font_size || 16}px`,
  }
  if (block.font_family) style.fontFamily = block.font_family
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
  }
}

function targetPath(targetId: string | null): string | null {
  if (!targetId) return null
  const target = props.sections.find((section) => section.id === targetId)
  if (!target) return null
  return `/${target.slug}`
}
</script>
