import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import AppShell from "./components/AppShell";
import EngineerScorecardPage from "./pages/EngineerScorecardPage";
import ExecutiveDashboardPage from "./pages/ExecutiveDashboardPage";
import GovernanceViewPage from "./pages/GovernanceViewPage";
import ServiceNowSettingsPage from "./pages/ServiceNowSettingsPage";
import VendorScorecardPage from "./pages/VendorScorecardPage";
import { getServiceNowStatus } from "./lib/api";

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [connected, setConnected] = useState(false);
  const [checkingStatus, setCheckingStatus] = useState(true);

  useEffect(() => {
    async function loadStatus() {
      try {
        const status = await getServiceNowStatus();
        setConnected(Boolean(status?.connected));
      } catch {
        setConnected(false);
      } finally {
        setCheckingStatus(false);
      }
    }
    loadStatus();
  }, []);

  function handleConnected() {
    setConnected(true);
    navigate("/executive", { replace: true });
  }

  if (checkingStatus) {
    return (
      <AppShell dashboardEnabled={false}>
        <div className="panel p-6 text-sm text-slate-600">Checking ServiceNow connection status...</div>
      </AppShell>
    );
  }

  if (!connected && location.pathname !== "/settings/servicenow") {
    return <Navigate to="/settings/servicenow" replace />;
  }

  return (
    <AppShell dashboardEnabled={connected}>
      <Routes>
        <Route
          path="/"
          element={<Navigate to={connected ? "/executive" : "/settings/servicenow"} replace />}
        />
        <Route
          path="/settings/servicenow"
          element={<ServiceNowSettingsPage onConnected={handleConnected} />}
        />
        <Route
          path="/executive"
          element={connected ? <ExecutiveDashboardPage /> : <Navigate to="/settings/servicenow" replace />}
        />
        <Route
          path="/vendor"
          element={connected ? <VendorScorecardPage /> : <Navigate to="/settings/servicenow" replace />}
        />
        <Route
          path="/engineer"
          element={connected ? <EngineerScorecardPage /> : <Navigate to="/settings/servicenow" replace />}
        />
        <Route
          path="/governance"
          element={connected ? <GovernanceViewPage /> : <Navigate to="/settings/servicenow" replace />}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}

