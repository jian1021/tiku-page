import { http } from "./client";

/**
 * 获取练习题目（不包含答案与解析）。
 * @param {{ chapter_id?: number|string, mode?: "practice"|"random", year_only?: boolean, province_code?: string }} params
 * @returns {Promise<{ items: object[], count: number }>}
 */
export function getQuestions(params = {}) {
  return http.get("/questions", { params }).then((res) => res.data);
}

/** 提交单题作答，返回判分结果、正确答案与解析。 */
export function submitAnswer(id, selected) {
  return http
    .post(`/questions/${id}/answer`, { selected, mode: "practice" })
    .then((res) => res.data);
}

/** 学习统计。 */
export function getStats() {
  return http.get("/stats").then((res) => res.data);
}

/** 站点配置（客服电话、微信、介绍等）。 */
export function getSiteConfig() {
  return http.get("/site-config").then((res) => res.data);
}

/** 意见反馈。 */
export function sendFeedback(content) {
  return http.post("/feedback", { content }).then((res) => res.data);
}
