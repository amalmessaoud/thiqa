import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000/api",
});

// Attach JWT token to every request if present
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("thiqa_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const thiqaApi = {
  // Auth
  register: (email, password) =>
    api.post("/auth/register/", { email, password }).then((r) => r.data),
  login: (email, password) =>
    api.post("/auth/login/", { email, password }).then((r) => r.data),
  logout: () => api.post("/auth/logout/").then((r) => r.data),
  me: () => api.get("/auth/me/").then((r) => r.data),

  // Search
  search: (q) =>
    api.get(`/search/?q=${encodeURIComponent(q)}`).then((r) => r.data),

  // Analyze
  analyzeText: (text) =>
    api.post("/analyze/text/", { text }).then((r) => r.data),

  analyzeScreenshot: (files) => {
    const form = new FormData();
    Array.from(files).forEach((file) => form.append("screenshots", file));
    return api.post("/analyze/screenshot/", form).then((r) => r.data);
  },

  analyzeImage: (files) => {
    const form = new FormData();
    Array.from(files).forEach((file) => form.append("images", file));
    return api.post("/analyze/image/", form).then((r) => r.data);
  },

  // Reports
  submitReport: ({ profile_url, scam_type, description, screenshot, contacts }) => {
    const form = new FormData();
    form.append("profile_url", profile_url);
    form.append("scam_type", scam_type);
    if (description) form.append("description", description);
    if (screenshot) form.append("screenshot", screenshot);
    if (contacts) form.append("contacts", JSON.stringify(contacts));
    return api.post("/reports/", form, {
      headers: { "Content-Type": "multipart/form-data" }
    }).then((r) => r.data);
  },

  getReports: (seller_id) =>
    api.get(`/reports/?seller_id=${seller_id}`).then((r) => r.data),

  // Reviews
  submitReview: (data) => api.post("/reviews/", data).then((r) => r.data),

  getReviews: (seller_id) =>
    api.get(`/reviews/?seller_id=${seller_id}`).then((r) => r.data),

  // Blacklist
  getBlacklist: (params) =>
    api.get("/blacklist/", { params }).then((r) => r.data),

  // History
  getHistory: () => api.get("/history/").then((r) => r.data),
};