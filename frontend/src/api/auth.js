import { http } from "./client";

/** 注册（成功后直接返回 token 与 user）。 */
export function register({ phone, password, nickname }) {
  return http
    .post("/auth/register", { phone, password, nickname })
    .then((res) => res.data);
}

/** 手机号 + 密码登录。 */
export function login({ phone, password }) {
  return http.post("/auth/login", { phone, password }).then((res) => res.data);
}

/** 获取当前登录用户。 */
export function getMe() {
  return http.get("/me").then((res) => res.data);
}

/** 更新昵称、省份与个人设置。 */
export function updateSettings(payload) {
  return http.put("/me/settings", payload).then((res) => res.data);
}
