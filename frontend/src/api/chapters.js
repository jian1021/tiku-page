import { http } from "./client";

/** 省份列表（含是否已开放题库）。 */
export function getProvinces() {
  return http.get("/provinces").then((res) => res.data);
}

/** 指定省份的章节树（含题量与已做数）。 */
export function getChapters(provinceCode) {
  return http
    .get("/chapters", { params: { province_code: provinceCode } })
    .then((res) => res.data);
}
