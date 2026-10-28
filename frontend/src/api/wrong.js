import { http } from "./client";

/** 错题本（按章节分组）。 */
export function getWrong() {
  return http.get("/wrong").then((res) => res.data);
}

/** 从错题本移除一道题。 */
export function removeWrong(questionId) {
  return http.delete(`/wrong/${questionId}`).then((res) => res.data);
}
