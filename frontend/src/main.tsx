import { MotionConfig } from "framer-motion";
// LearningPreferences moved 2026-09-14: it renders per-route inside
// lazy-page's guide row (next to "How this page works"), not at the app
// root — the old root mount floated it fixed at the bottom-left corner.
import { OfflineSyncBridge } from "./offline/OfflineSyncBridge";
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.tsx";
// Font Awesome icon pack (self-hosted via npm — no CDN dependency).
// Pages use <i className="fa-solid fa-..."> markup; without this the glyphs
// render as blank boxes. Imported here so it applies to every route.
import "@fortawesome/fontawesome-free/css/all.min.css";
import "./styles/app.css";
import { ThemeProvider } from "./contexts/theme-context";
import { HelmetProvider } from "react-helmet-async";

// Global error handlers to catch unhandled promise rejections
if (typeof window !== "undefined") {
  window.addEventListener("unhandledrejection", (event) => {
    // Log the error with full context
    console.error("Unhandled promise rejection:", event.reason);
    // Only prevent default for React Query errors (already logged per-query)
    // Let critical errors propagate to browser
    if (
      event.reason?.message?.includes("Failed to fetch") ||
      event.reason?.name === "AbortError"
    ) {
      // Network-related errors that React Query handles
      return;
    }
    // Don't swallow all errors - let them surface for debugging
  });
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <HelmetProvider>
      <ThemeProvider>
        <MotionConfig
          reducedMotion="user"
          transition={{ duration: 0.16, ease: [0.2, 0.7, 0.3, 1] }}
        >
          <App />
          <OfflineSyncBridge />
        </MotionConfig>
      </ThemeProvider>
    </HelmetProvider>
  </React.StrictMode>,
); // v1778429448
