"use client";

import { useEffect, useRef } from "react";

// Three.js and Vanta load from a CDN on first mount rather than being bundled.
const THREE_SRC = "https://unpkg.com/three@0.134.0/build/three.min.js";
const VANTA_CELLS_SRC = "https://unpkg.com/vanta@0.5.24/dist/vanta.cells.min.js";

type VantaInstance = { destroy?: () => void };
type VantaGlobal = { CELLS?: (options: Record<string, unknown>) => VantaInstance };

declare global {
  interface Window {
    THREE?: unknown;
    VANTA?: VantaGlobal;
  }
}

function loadScript(src: string): Promise<void> {
  const existing = document.querySelector<HTMLScriptElement>(`script[src="${src}"]`);
  if (existing?.dataset.loaded === "true") return Promise.resolve();

  return new Promise((resolve, reject) => {
    const script = existing ?? document.createElement("script");
    script.addEventListener("load", () => {
      script.dataset.loaded = "true";
      resolve();
    });
    script.addEventListener("error", () => reject(new Error(`Failed to load ${src}`)));
    if (!existing) {
      script.src = src;
      script.async = true;
      document.head.appendChild(script);
    }
  });
}

export default function VantaBackground() {
  const vantaRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    // Decorative motion: skip it for visitors who ask for less.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let instance: VantaInstance | null = null;
    let cancelled = false;

    (async () => {
      try {
        if (!window.THREE) await loadScript(THREE_SRC);
        if (!window.VANTA?.CELLS) await loadScript(VANTA_CELLS_SRC);
        if (cancelled || !vantaRef.current || !window.VANTA?.CELLS) return;

        instance = window.VANTA.CELLS({
          el: vantaRef.current,
          mouseControls: true,
          touchControls: true,
          gyroControls: false,
          minHeight: 200.0,
          minWidth: 200.0,
          scale: 1.0,
          // slightly darkened mixed blue/teal palette
          backgroundColor: 0x071028,
          color1: 0x096fe6,
          color2: 0x44cfa0,
        });
      } catch (err) {
        // The background is decorative; the flat body color stays in place.
        console.warn("Vanta failed to initialize:", err);
      }
    })();

    return () => {
      cancelled = true;
      instance?.destroy?.();
    };
  }, []);

  return <div id="vanta-bg" ref={vantaRef} aria-hidden className="fixed inset-0 -z-10" />;
}
