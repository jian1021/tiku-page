import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { TOKEN_KEY, http } from "../api/client";
import { getMe, login as apiLogin, register as apiRegister, updateSettings as apiUpdateSettings } from "../api/auth";

const USER_KEY = "sx_user";

/** 读取本地缓存的用户信息，解析失败时返回 null。 */
function readCachedUser() {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

/** 写入用户缓存；传 null 表示清空。 */
function writeCachedUser(user) {
  try {
    if (user) {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(USER_KEY);
    }
  } catch {
    // 隐私模式下忽略存储异常
  }
}

export const useAuthStore = defineStore("auth", () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) || "");
  const user = ref(readCachedUser());

  const isLoggedIn = computed(() => Boolean(token.value));
  const isAdmin = computed(() => user.value?.role === "admin");
  const membershipExpiresAt = computed(() => user.value?.membership_expires_at || null);

  /** 会员是否有效：管理员始终有效，普通用户需到期时间晚于当前时刻。 */
  const isMember = computed(() => {
    if (isAdmin.value) return true;
    const expires = membershipExpiresAt.value;
    if (!expires) return false;
    const time = new Date(expires).getTime();
    return Number.isFinite(time) && time > Date.now();
  });

  /** 会员剩余天数，未开通返回 0。 */
  const memberDaysLeft = computed(() => {
    if (!isMember.value) return 0;
    const expires = membershipExpiresAt.value;
    if (!expires) return 0;
    const diff = new Date(expires).getTime() - Date.now();
    return diff > 0 ? Math.ceil(diff / 86400000) : 0;
  });

  const displayName = computed(
    () => user.value?.nickname || user.value?.phone || "未登录"
  );

  /** 保存登录态。 */
  function applyAuth(payload) {
    token.value = payload?.token || "";
    user.value = payload?.user || null;
    if (token.value) {
      localStorage.setItem(TOKEN_KEY, token.value);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
    writeCachedUser(user.value);
  }

  /** 清空登录态。 */
  function logout() {
    applyAuth(null);
  }

  /** 登录：失败时抛出错误，由页面负责提示。 */
  async function login(phone, password) {
    const data = await apiLogin({ phone, password });
    applyAuth(data);
    return data;
  }

  /** 注册并自动登录。 */
  async function register({ phone, password, nickname }) {
    const data = await apiRegister({ phone, password, nickname });
    applyAuth(data);
    return data;
  }

  /** 拉取最新用户信息（含会员到期时间）。 */
  async function fetchMe() {
    if (!token.value) return null;
    const data = await getMe();
    user.value = data;
    writeCachedUser(data);
    return data;
  }

  /** 更新昵称 / 省份 / 个人设置，并同步本地用户信息。 */
  async function updateSettings(payload) {
    const data = await apiUpdateSettings(payload);
    user.value = data;
    writeCachedUser(data);
    return data;
  }

  /** 应用启动时校验令牌；401 时 client 拦截器会广播事件并清理令牌。 */
  async function init() {
    if (typeof window !== "undefined") {
      window.addEventListener("auth:unauthorized", () => {
        token.value = "";
        user.value = null;
        writeCachedUser(null);
      });
    }
    if (!token.value) return;
    try {
      await fetchMe();
    } catch {
      // 网络异常时保留本地缓存，避免弱网下被强制退出
    }
  }

  return {
    token,
    user,
    isLoggedIn,
    isAdmin,
    isMember,
    membershipExpiresAt,
    memberDaysLeft,
    displayName,
    login,
    register,
    logout,
    fetchMe,
    updateSettings,
    init,
  };
});

/** 便于在拦截器等非组件环境读取令牌。 */
export function authHeader() {
  const value = localStorage.getItem(TOKEN_KEY);
  return value ? { Authorization: `Bearer ${value}` } : {};
}

export { http };
