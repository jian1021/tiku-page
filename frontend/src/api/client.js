import axios from "axios";

export const TOKEN_KEY = "sx_token";

/**
 * 统一 axios 实例。
 * - 自动附带登录令牌
 * - 401 时清除本地令牌并广播 auth:unauthorized
 * - 错误信息统一挂到 error.message（优先使用后端 detail）
 */
export const http = axios.create({
  baseURL: "/api",
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

http.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

http.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;

    if (status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("auth:unauthorized"));
      }
    }

    let message = error.response?.data?.detail;

    if (Array.isArray(message)) {
      message = message
        .map((item) => item?.msg || item?.message || "")
        .filter(Boolean)
        .join("；");
    }

    if (!message && error.code === "ECONNABORTED") {
      message = "请求超时，请检查网络后重试";
    }

    if (!message && !error.response) {
      message = "网络连接失败，请检查网络后重试";
    }

    error.detail = error.response?.data?.detail ?? null;

    if (typeof message === "string" && message.trim()) {
      error.message = message;
    } else if (!error.message) {
      error.message = "请求失败，请稍后重试";
    }

    return Promise.reject(error);
  }
);

export default http;
