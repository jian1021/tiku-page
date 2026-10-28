import { http } from "./client";

/** 收藏列表；targetType 为空表示全部（question / law_article）。 */
export function getFavorites(targetType) {
  return http
    .get("/favorites", { params: { target_type: targetType || undefined } })
    .then((res) => res.data);
}

/** 添加收藏（幂等）。 */
export function addFavorite(targetType, targetId) {
  return http
    .post("/favorites", {
      target_type: targetType,
      target_id: String(targetId),
    })
    .then((res) => res.data);
}

/** 取消收藏。 */
export function removeFavorite(targetType, targetId) {
  return http
    .delete(`/favorites/${targetType}/${targetId}`)
    .then((res) => res.data);
}
