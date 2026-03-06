<template>
  <div class="shell">
    <header class="shell-header">
      <NuxtLink to="/machines" class="brand">Fablab Backoffice</NuxtLink>
      <nav class="shell-nav">
        <NuxtLink to="/machines" class="shell-link" active-class="is-active">Machines</NuxtLink>
        <NuxtLink to="/cms" class="shell-link" active-class="is-active">CMS</NuxtLink>
      </nav>
    </header>
    <NuxtPage />
  </div>
</template>
