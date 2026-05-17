"use client";

import { useEffect, useRef } from "react";

export default function VantaBackground() {
  const vantaRef = useRef<HTMLDivElement | null>(null);
  const vantaInstance = useRef<any>(null);

  useEffect(() => {
    let threeScript: HTMLScriptElement | null = null;
    let vantaScript: HTMLScriptElement | null = null;

    function loadScript(src: string) {
      return new Promise<HTMLScriptElement>((resolve, reject) => {
        const s = document.createElement("script");
        s.src = src;
        s.async = true;
        s.onload = () => resolve(s);
        s.onerror = () => reject(new Error(`Failed to load ${src}`));
        document.head.appendChild(s);
      });
    }

    async function initVanta() {
      try {
        if (!window) return;

        // Load Three.js (r134) and Vanta Cells if not already present
        if (!(window as any).THREE) {
          threeScript = await loadScript(
            "https://unpkg.com/three@0.134.0/build/three.min.js",
          );
        }
        if (!(window as any).VANTA) {
          vantaScript = await loadScript(
            "https://unpkg.com/vanta@latest/dist/vanta.cells.min.js",
          );
        }

        // Initialize when available
        const VANTA = (window as any).VANTA;
        if (vantaRef.current && VANTA && VANTA.CELLS) {
          vantaInstance.current = VANTA.CELLS({
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
        }
      } catch (err) {
        // Fail silently — background is decorative
        // eslint-disable-next-line no-console
        console.warn("Vanta failed to initialize:", err);
      }
    }

    initVanta();

    return () => {
      try {
        if (vantaInstance.current && typeof vantaInstance.current.destroy === "function") {
          vantaInstance.current.destroy();
          vantaInstance.current = null;
        }
      } catch (e) {
        // ignore
      }
      // Optionally remove injected scripts — leave them to cache for SPA navigation
      // but if you want to remove, uncomment the lines below.
      // if (threeScript && threeScript.parentNode) threeScript.parentNode.removeChild(threeScript);
      // if (vantaScript && vantaScript.parentNode) vantaScript.parentNode.removeChild(vantaScript);
    };
  }, []);

  return <div id="vanta-bg" ref={vantaRef} className="fixed inset-0 -z-10" />;
}
