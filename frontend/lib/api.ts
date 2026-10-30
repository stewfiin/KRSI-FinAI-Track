import axios from "axios";

// Di browser (baik desktop localhost maupun smartphone via IP Wi-Fi/Hotspot),
// gunakan relative URL "" agar seluruh panggilan API melewati Next.js Reverse Proxy
// Rewrites (/api/* -> http://127.0.0.1:8000/api/*) di port 3000.
// Hal ini menjamin HP tidak perlu akses langsung ke port 8000 dan bebas blokir firewall.
const getBaseUrl = () => {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (typeof window !== "undefined") {
    return "";
  }
  return "http://127.0.0.1:8000";
};

export const api = axios.create({
  baseURL: getBaseUrl(),
  headers: {
    "Content-Type": "application/json",
  },
});

// Request Interceptor: Otomatis menyuntikkan JWT Bearer Token jika ada
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    if (!process.env.NEXT_PUBLIC_API_URL && !config.baseURL) {
      config.baseURL = "";
    }
    const token = localStorage.getItem("finai_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Response Interceptor: Tangani 401 Unauthorized secara terpusat
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      const isAuthPage = window.location.pathname.startsWith("/login");
      if (!isAuthPage) {
        localStorage.removeItem("finai_token");
        localStorage.removeItem("finai_user");
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

