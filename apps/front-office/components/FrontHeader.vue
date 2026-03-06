<template>
  <header class="site-header">
    <NuxtLink to="/" class="site-brand">
      <span class="site-brand-mark">FabLab</span>
      <strong>JUNIA ISEN</strong>
    </NuxtLink>

    <nav class="site-nav">
      <NuxtLink to="/" class="site-link" active-class="is-active" exact-active-class="is-active">Accueil</NuxtLink>
      <template v-for="item in navItems" :key="item.key">
        <NuxtLink
          v-if="item.type === 'single'"
          :to="item.to"
          class="site-link"
          active-class="is-active"
        >
          {{ item.label }}
        </NuxtLink>

        <div v-else class="site-menu">
          <NuxtLink
            :to="item.to"
            class="site-link site-menu-label"
            active-class="is-active"
          >
            {{ item.label }}
          </NuxtLink>
          <div class="site-menu-panel">
            <NuxtLink
              v-for="child in item.children"
              :key="child.key"
              :to="child.to"
              class="site-menu-link"
              active-class="is-active"
            >
              {{ child.label }}
            </NuxtLink>
          </div>
        </div>
      </template>
    </nav>
  </header>
</template>

<script setup lang="ts">
type NavSection = {
  id: string
  title: string
  slug: string
  nav_label?: string | null
  nav_group?: string | null
}

const props = defineProps<{
  sections: NavSection[]
}>()

const navItems = computed(() => {
  const singleItems: Array<{ type: "single"; key: string; label: string; to: string }> = []
  const grouped = new Map<string, Array<{ key: string; label: string; to: string }>>()
  const normalizedGroupName = (value: string) => value.trim().toLowerCase()

  for (const section of props.sections) {
    const label = section.nav_label || section.title
    const group = (section.nav_group || "").trim()
    const item = { key: section.id, label, to: `/${section.slug}` }

    if (!group) {
      singleItems.push({ type: "single", ...item })
      continue
    }

    if (!grouped.has(group)) grouped.set(group, [])
    grouped.get(group)?.push(item)
  }

  const groupedItems = [...grouped.entries()].map(([group, children]) => {
    const inheritedParents = singleItems.filter((item) => normalizedGroupName(item.label) === normalizedGroupName(group))
    const filteredSingles = singleItems.filter((item) => normalizedGroupName(item.label) !== normalizedGroupName(group))
    singleItems.splice(0, singleItems.length, ...filteredSingles)

    const parent = inheritedParents[0]
    return {
      type: "group" as const,
      key: parent?.key || group,
      label: parent?.label || group,
      to: parent?.to || children[0]?.to || "/",
      children,
    }
  })

  return [...singleItems, ...groupedItems]
})
</script>
