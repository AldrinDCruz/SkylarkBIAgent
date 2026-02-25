// api.js – wrapper for all backend API calls

const API_URL = "/api";

export async function sendMessage(message, history = []) {
  const response = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Server error ${response.status}`);
  }
  return response.json();
}

export async function getLeadershipUpdate() {
  const response = await fetch(`${API_URL}/leadership-update`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Server error ${response.status}`);
  }
  return response.json();
}

export async function refreshCache() {
  const response = await fetch(`${API_URL}/refresh-cache`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error("Cache refresh failed");
  return response.json();
}

export async function runAdhocAnalysis(dimension, metric) {
  const response = await fetch(`${API_URL}/adhoc`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dimension, metric }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Server error ${response.status}`);
  }
  return response.json();
}
export async function fetchDashboardData(mock = false) {
  const url = `${API_URL}/dashboard-data${mock ? "?mock=true" : ""}`;
  const response = await fetch(url, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Server error ${response.status}`);
  }
  return response.json();
}
