import { http } from "./client";

/** 考试配置（题量、时长、及格分、总分）。 */
export function getExamConfig(provinceCode) {
  return http
    .get("/exam/config", {
      params: { province_code: provinceCode || undefined },
    })
    .then((res) => res.data);
}

/** 开始模拟考试。 */
export function startExam(payload = {}) {
  return http.post("/exam/start", payload).then((res) => res.data);
}

/** 获取考试详情（断网 / 刷新后恢复）。 */
export function getExam(id) {
  return http.get(`/exam/${id}`).then((res) => res.data);
}

/** 保存单题作答；超时会返回 auto_submitted。 */
export function saveExamAnswer(id, questionId, selected) {
  return http
    .post(`/exam/${id}/answer`, {
      question_id: questionId,
      selected,
    })
    .then((res) => res.data);
}

/** 交卷。answers 形如 { "12": ["A"] }。 */
export function submitExam(id, answers) {
  return http.post(`/exam/${id}/submit`, { answers }).then((res) => res.data);
}

/** 考试结果（含章节正确率与错题解析）。 */
export function getExamResult(id) {
  return http.get(`/exam/${id}/result`).then((res) => res.data);
}

/** 我的考试历史。 */
export function getExamHistory() {
  return http.get("/exam/history").then((res) => res.data);
}
