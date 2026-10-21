const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path) {
  const response = await fetch(API_BASE_URL + path);

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json();
}

export function getHealth() {
  return request("/api/health");
}

export function getMetadata() {
  return request("/api/metadata");
}

export function getRisks() {
  return request("/api/risks");
}

export function getPriorities() {
  return request("/api/priorities");
}

export function getAlerts() {
  return request("/api/alerts");
}

export { API_BASE_URL };
