import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || "/api",
});

// Attach the auth token (if we have one) to every request.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("sentinel_token");
  if (token) config.headers.Authorization = `Token ${token}`;
  return config;
});

export const register = (username, password) =>
  api.post("/auth/register/", { username, password });

export const login = (username, password) =>
  api.post("/auth/login/", { username, password });

export const listSessions = () => api.get("/sessions/");
export const getSession = (id) => api.get(`/sessions/${id}/`);
export const createSession = (payload) => api.post("/sessions/", payload);

export const streamSession = (id, onEvent, onDone) => {
  const token = localStorage.getItem("sentinel_token");
  // EventSource can't set custom headers, so the token goes as a query param here.
  const url = `${api.defaults.baseURL}/sessions/${id}/stream/?token=${token}`;
  const source = new EventSource(url);
  source.onmessage = (e) => onEvent(JSON.parse(e.data));
  source.addEventListener("done", (e) => {
    onDone?.(JSON.parse(e.data));
    source.close();
  });

  source.onerror = (err) => {
    console.error("SSE connection dropped:", err);
    source.close();
  };
  
  return () => source.close();
};
