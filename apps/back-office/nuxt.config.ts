export default defineNuxtConfig({
  ssr: true,
  devtools: { enabled: false },
  css: ["~/assets/main.css"],
  runtimeConfig: {
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
