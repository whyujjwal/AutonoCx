import { createElement } from "react";
import { createRoot } from "react-dom/client";
import { Widget } from "./Widget";

interface AutonoCXConfig {
  apiUrl: string;
  agentId?: string;
  theme?: {
    primaryColor?: string;
    fontFamily?: string;
    position?: "bottom-right" | "bottom-left";
  };
  customer?: {
    id?: string;
    name?: string;
    email?: string;
  };
}

declare global {
  interface Window {
    AutonoCX: {
      init: (config: AutonoCXConfig) => void;
      open: () => void;
      close: () => void;
      destroy: () => void;
    };
  }
}

let root: ReturnType<typeof createRoot> | null = null;
let container: HTMLDivElement | null = null;

window.AutonoCX = {
  init(config: AutonoCXConfig) {
    if (container) return;

    container = document.createElement("div");
    container.id = "autonomocx-widget-root";
    document.body.appendChild(container);

    const shadow = container.attachShadow({ mode: "open" });
    const mountPoint = document.createElement("div");
    shadow.appendChild(mountPoint);

    root = createRoot(mountPoint);
    root.render(createElement(Widget, { config }));
  },

  open() {
    document.dispatchEvent(new CustomEvent("autonomocx:open"));
  },

  close() {
    document.dispatchEvent(new CustomEvent("autonomocx:close"));
  },

  destroy() {
    if (root) {
      root.unmount();
      root = null;
    }
    if (container) {
      container.remove();
      container = null;
    }
  },
};
