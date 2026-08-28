import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@kuhyx/web-ui/tokens.css";

import "./styles/app.css";
import { App } from "./app.tsx";

const root = document.querySelector("#root");
if (root !== null) {
  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}
