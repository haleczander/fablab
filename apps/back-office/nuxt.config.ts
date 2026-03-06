export default defineNuxtConfig({
  ssr: true,
  devtools: { enabled: false },
  css: ["~/assets/main.css"],
  runtimeConfig: {
    backendInternalBase: process.env.NUXT_BACKEND_INTERNAL_BASE || "http://backend:8000",
    public: {
      backendBase: process.env.NUXT_PUBLIC_BACKEND_BASE || "http://localhost:8000",
    },
  },
  app: {
    head: {
      title: "Fablab Backoffice",
    },
  },
})
