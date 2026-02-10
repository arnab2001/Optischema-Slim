import React from "react";
import ReactDOM from "react-dom/client";
import "../app/globals.css";
import LandingPage from "@/app/landing/page";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <LandingPage />
  </React.StrictMode>
);
