"use client";

import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function AnalyticsRedirect() {
  const navigate = useNavigate();

  useEffect(() => {
    navigate("/dashboard", { replace: true });
  }, [navigate]);

  return null;
}
