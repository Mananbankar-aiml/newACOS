import axios from "axios";

// Empty REACT_APP_BACKEND_URL means "same origin" — used when deploying frontend + backend
// together (e.g. on Vercel), where the FastAPI function is served on the same host under /api.
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("acos_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
