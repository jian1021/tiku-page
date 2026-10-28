import { http } from "./client";

/**
 * 法规列表。
 * @param {{ province_code?: string, category?: string, status?: string }} params
 */
export function getLaws(params = {}) {
  return http.get("/laws", { params }).then((res) => res.data);
}

/** 法规详情（含条文）。 */
export function getLaw(id) {
  return http.get(`/laws/${id}`).then((res) => res.data);
}

/** 全文检索法规标题与条文。 */
export function searchLaws(q, provinceCode) {
  return http
    .get("/laws/search", {
      params: { q, province_code: provinceCode || undefined },
    })
    .then((res) => res.data);
}
