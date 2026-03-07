<template>
  <main class="fo-wrap">
    <FrontHeader :sections="navSections" />

    <section class="fo-hero">
      <h1>FabLab JUNIA ISEN</h1>
    </section>

    <PublishedSection
      v-for="section in homeSections"
      :key="section.id"
      :section="section"
      :sections="allSections"
    />
  </main>
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
  show_in_nav: boolean
  nav_label: string | null
  nav_group: string | null
  show_in_home: boolean
  layout: LayoutMode
  columns: number
  rows: number
  gap: number
  padding: number
  margin_top: number
  margin_bottom: number
  blocks: CmsBlock[]
}

type CmsPublishedSite = {
  published: {
    sections: CmsSection[]
  }
  published_version: number
  published_at: string | null
}

const config = useRuntimeConfig()
const backendBase = (process.server ? config.backendInternalBase : config.public.backendBase) as string
const { data } = await useFetch<CmsPublishedSite>(`${backendBase}/cms/frontoffice/published`)

const allSections = computed(() => data.value?.published.sections ?? [])
const navSections = computed(() => allSections.value.filter((section) => section.show_in_nav))
const homeSections = computed(() => allSections.value.filter((section) => section.show_in_home))
</script>
