import axios from "axios";

const TOKEN_KEY = "monitor_admin_token";

const client = axios.create({
  baseURL: "/",
  timeout: 10000,
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function loginAdmin(payload) {
  return client.post("/api/auth/login", payload);
}

export function changePassword(payload) {
  return client.post("/api/auth/change-password", payload);
}

export function getAuthMe() {
  return client.get("/api/auth/me");
}

export function getAuditLogs(limit = 100) {
  return client.get("/api/audit-logs", { params: { limit } });
}

export function getHealth() {
  return client.get("/health");
}

export function getOverview() {
  return client.get("/api/dashboard/overview");
}

export function getServiceStatus() {
  return client.get("/api/dashboard/service-status");
}

export function getServices() {
  return client.get("/api/services");
}

export function getMonitorLogs(serviceId = null, limit = 100) {
  const params = { limit };
  if (serviceId !== null && serviceId !== undefined) {
    params.service_id = serviceId;
  }
  return client.get("/api/monitor/logs", { params });
}

export function getAlerts(limit = 50) {
  return client.get("/api/alerts", { params: { limit } });
}

export function runNow(serviceId) {
  return client.post(`/api/services/${serviceId}/run-now`);
}

export function runAllNow() {
  return client.post("/api/services/run-all-now");
}

export function createService(payload) {
  return client.post("/api/services", payload);
}

export function updateService(serviceId, payload) {
  return client.put(`/api/services/${serviceId}`, payload);
}

export function deleteService(serviceId) {
  return client.delete(`/api/services/${serviceId}`);
}

export function getSettings() {
  return client.get("/api/settings");
}

export function updateSettings(payload) {
  return client.put("/api/settings", payload);
}

export function sendTestAlert() {
  return client.post("/api/alerts/test");
}

export function getMaintenanceLogs(serviceId = null, limit = 100) {
  const params = { limit };
  if (serviceId !== null && serviceId !== undefined) {
    params.service_id = serviceId;
  }
  return client.get("/api/maintenance-logs", { params });
}

export function createMaintenanceLog(payload) {
  return client.post("/api/maintenance-logs", payload);
}

