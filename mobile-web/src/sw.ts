/// <reference lib="webworker" />

import { clientsClaim } from "workbox-core";
import { cleanupOutdatedCaches, precacheAndRoute } from "workbox-precaching";
import { registerRoute, setCatchHandler } from "workbox-routing";
import { CacheFirst, NetworkFirst, StaleWhileRevalidate } from "workbox-strategies";

declare let self: ServiceWorkerGlobalScope & {
  __WB_MANIFEST: Array<string | { revision: string | null; url: string }>;
};

self.skipWaiting();
clientsClaim();
precacheAndRoute(self.__WB_MANIFEST);
cleanupOutdatedCaches();

const appShellUrl = new URL("index.html", self.registration.scope).toString();

registerRoute(
  ({ request }) => request.mode === "navigate",
  new NetworkFirst({
    cacheName: "familycut-shell"
  })
);

registerRoute(
  ({ request, url }) =>
    request.method === "GET" &&
    (url.pathname.startsWith("/api/v1/reports") || url.pathname.startsWith("/api/v1/measurements") || url.pathname.startsWith("/api/v1/meals")),
  new NetworkFirst({
    cacheName: "familycut-api",
    networkTimeoutSeconds: 4
  })
);

registerRoute(
  ({ request, url }) =>
    request.destination === "image" && (url.pathname.startsWith("/report-files/") || url.pathname.startsWith("/media-files/")),
  new StaleWhileRevalidate({
    cacheName: "familycut-images"
  })
);

registerRoute(
  ({ request }) => ["style", "script", "font"].includes(request.destination),
  new CacheFirst({
    cacheName: "familycut-static"
  })
);

setCatchHandler(async ({ request }) => {
  if (request.mode === "navigate") {
    const cached = (await caches.match(appShellUrl)) ?? (await caches.match(new URL(appShellUrl).pathname));
    if (cached) {
      return cached;
    }
  }
  return Response.error();
});
