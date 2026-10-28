import { http } from "./client";

/**
 * 激活会员。
 * 后端路由为 POST /api/activate。
 */
export function activate(code) {
  return http.post("/activate", { code }).then((res) => res.data);
}
