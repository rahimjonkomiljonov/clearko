import type { MetadataRoute } from "next";

// Installable PWA. There is deliberately no service worker that caches pages or API
// calls: documents must never be stored on the device by ClearKo.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "ClearKo",
    short_name: "ClearKo",
    description: "Understand any Korean document",
    start_url: "/",
    display: "standalone",
    background_color: "#f7f6f2",
    theme_color: "#1f4fd8",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }],
  };
}
