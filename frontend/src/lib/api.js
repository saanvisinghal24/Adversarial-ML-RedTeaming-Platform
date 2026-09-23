/**
 * Thin fetch wrapper around the FastAPI backend.
 * Everything goes through here so auth headers, error shape and base URL live in one place.
 */
import { useAuth } from "../store/auth";

// In dev, Vite proxies /api -> localhost:8000. In prod, VITE_API_URL points at the deployed API.
export const API_BASE = import.meta.env.VITE_API_URL || "/api";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function parseError(res) {
  let detail = `Request failed (${res.status})`;
  try {
    const body = await res.json();
    if (typeof body.detail === "string") detail = body.detail;
    // FastAPI validation errors come back as a list of {loc, msg}
    else if (Array.isArray(body.detail)) detail = body.detail.map((d) => d.msg).join("; ");
  } catch {
    /* non-JSON error body — keep the status message */
  }
  return new ApiError(detail, res.status);
}

async function request(path, { method = "GET", body, auth = true, isForm = false } = {}) {
  const headers = {};
  if (auth) {
    const token = useAuth.getState().accessToken;
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  if (!isForm && body !== undefined) headers["Content-Type"] = "application/json";

  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: isForm ? body : body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("Can't reach the API. Is the backend running?", 0);
  }

  if (res.status === 401 && auth) {
    useAuth.getState().logout();
    throw new ApiError("Session expired. Sign in again.", 401);
  }
  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  health: () => request("/health", { auth: false }),
  register: (email, password) =>
    request("/auth/register", { method: "POST", body: { email, password }, auth: false }),
  login: (email, password) =>
    request("/auth/login", { method: "POST", body: { email, password }, auth: false }),
  me: () => request("/auth/me"),

  listModels: () => request("/models"),
  uploadModel: (formData) => request("/models", { method: "POST", body: formData, isForm: true }),

  createScan: (payload) => request("/scans", { method: "POST", body: payload }),
  getScan: (id) => request(`/scans/${id}`),
  getFindings: (id) => request(`/scans/${id}/findings`),
  modelScans: (modelId) => request(`/models/${modelId}/scans`),

  reportUrl: (scanId, format) => {
    const token = useAuth.getState().accessToken;
    return `${API_BASE}/scans/${scanId}/report?format=${format}&token=${encodeURIComponent(token ?? "")}`;
  },
};
