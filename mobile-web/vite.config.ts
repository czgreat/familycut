import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

const devProxyTarget = process.env.VITE_DEV_PROXY_TARGET ?? "http://127.0.0.1:25999";
const appBase = process.env.VITE_APP_BASE ?? "/";
const normalizedBase = appBase.endsWith("/") ? appBase : `${appBase}/`;

export default defineConfig({
  base: normalizedBase,
  plugins: [
    react(),
    VitePWA({
      strategies: "injectManifest",
      srcDir: "src",
      filename: "sw.ts",
      registerType: "autoUpdate",
      injectManifest: {
        globPatterns: ["**/*.{js,css,html,svg,png,ico,webmanifest}"]
      },
      manifest: {
        name: "FamilyCut",
        short_name: "FamilyCut",
        description: "面向家庭用户的减脂记录 PWA。",
        lang: "zh-CN",
        id: normalizedBase,
        start_url: normalizedBase,
        scope: normalizedBase,
        display: "standalone",
        display_override: ["standalone", "minimal-ui", "browser"],
        background_color: "#f4e8d8",
        theme_color: "#e99a5c",
        prefer_related_applications: false,
        icons: [
          {
            src: "icon-192.png",
            sizes: "192x192",
            type: "image/png"
          },
          {
            src: "icon-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "any maskable"
          }
        ]
      },
      devOptions: {
        enabled: false
      }
    })
  ],
  server: {
    host: "0.0.0.0",
    port: 4174,
    proxy: {
      "/api": devProxyTarget,
      "/media-files": devProxyTarget,
      "/report-files": devProxyTarget
    }
  }
});
