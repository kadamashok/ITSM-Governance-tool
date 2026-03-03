import api from "./axiosClient";

export async function getServiceNowStatus() {
  const { data } = await api.get("/api/config/status");
  return data;
}

export async function saveServiceNowOAuthConfig(payload) {
  const { data } = await api.post("/api/config/servicenow", payload);
  return data;
}

export async function getExecutiveDashboard(period = "1d", page = 1, size = 25) {
  const { data } = await api.get("/api/dashboard/executive", {
    params: { period, page, size },
  });
  return data;
}

export async function getVendorDashboard(vendorName, period = "1d") {
  const { data } = await api.get(`/api/dashboard/vendor/${encodeURIComponent(vendorName)}`, {
    params: { period },
  });
  return data;
}

export async function getEngineerDashboard(engineerName, period = "1d") {
  const { data } = await api.get(`/api/dashboard/engineer/${encodeURIComponent(engineerName)}`, {
    params: { period },
  });
  return data;
}

export async function getGovernanceReport(period = "1d") {
  const { data } = await api.get("/api/analytics/governance-report", {
    params: { period },
  });
  return data;
}

export async function getDuplicates() {
  const { data } = await api.get("/api/analytics/duplicates");
  return data;
}
