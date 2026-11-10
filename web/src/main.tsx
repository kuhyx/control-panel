import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@kuhyx/web-ui/tokens.css";

import "./styles/app.css";
import "./styles/live.css";
import "./styles/sessions.css";
import "./styles/shared.css";
import "./styles/table-controls.css";
import "./styles/glyphs.css";
import { App } from "./app.tsx";

const root = document.querySelector("#root");
if (root !== null) {
  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}
