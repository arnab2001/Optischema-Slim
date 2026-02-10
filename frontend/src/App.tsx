import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import Home from "@/app/page";
import DashboardPage from "@/app/dashboard/page";
import HealthPage from "@/app/health/page";
import SettingsPage from "@/app/settings/page";
import SavedPage from "@/app/saved/page";
import AnalyticsRedirect from "@/app/analytics/page";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/health" element={<HealthPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/saved" element={<SavedPage />} />
        <Route path="/analytics" element={<AnalyticsRedirect />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
