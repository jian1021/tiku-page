# 后端接口文档

- 服务地址：`http://localhost:8000`（开发）
- 统一前缀：`/api`
- 在线调试：`http://localhost:8000/docs`（Swagger UI）
- 鉴权：除标注「公开」外，均需请求头 `Authorization: Bearer <token>`
- 错误格式：`{"detail": "错误说明"}`，`detail` 为字符串或校验错误数组

## 目录

1. [认证](#1-认证)
2. [章节与省份](#2-章节与省份)
3. [题目练习](#3-题目练习)
4. [错题与收藏](#4-错题与收藏)
5. [法规库](#5-法规库)
6. [模拟考试](#6-模拟考试)
7. [会员激活](#7-会员激活)
8. [站点配置与统计](#8-站点配置与统计)

---

## 1. 认证

### POST /api/auth/register · 公开

注册并直接返回登录令牌。

```json
// 请求
{ "phone": "13800138000", "password": "123456", "nickname": "小王" }

// 响应 200
{
  "token": "eyJhbGciOi...",
  "user": {
    "id": 1,
    "phone": "13800138000",
    "nickname": "小王",
    "province_code": null,
    "settings": {},
    "role": "user",
    "membership_expires_at": null,
    "created_at": "2026-10-28T13:10:00"
  }
}
```

手机号重复 → `400 {"detail": "该手机号已注册"}`。

### POST /api/auth/login · 公开

```json
// 请求
{ "phone": "13800138000", "password": "123456" }
// 响应结构同注册
```

失败 → `401 {"detail": "手机号或密码错误"}`。

### GET /api/me

返回当前用户公开字段（同上 `user` 结构）。

### PUT /api/me/settings

三个字段均可选；`settings` 为字典，会与已有设置合并（常用于保存考试题量偏好）。

```json
{
  "province_code": "SC",
  "nickname": "小王",
  "settings": { "exam_question_count": 60, "exam_duration_minutes": 90 }
}
```

响应：更新后的用户对象。

---

## 2. 章节与省份

### GET /api/provinces · 公开

```json
[
  { "code": "SC", "name": "四川省", "open": true },
  { "code": "BJ", "name": "北京市", "open": false }
]
```

`open` 表示该省题库是否已开放（当前仅 `SC`）。

### GET /api/chapters?province_code=SC · 公开（带令牌时附带个人进度）

返回顶级章节数组，子章节在 `children` 中递归嵌套。

```json
[
  {
    "id": 1,
    "name": "第一章 政府采购基础",
    "province_code": "SC",
    "sort_order": 1,
    "question_count": 40,
    "answered_count": 12,
    "children": [
      {
        "id": 2,
        "name": "第一节 基本概念",
        "province_code": "SC",
        "sort_order": 2,
        "question_count": 20,
        "answered_count": 8,
        "children": []
      }
    ]
  }
]
```

`question_count` / `answered_count` 为**含子孙章节的汇总值**；`answered_count` 需要登录令牌，游客恒为 0。

---

## 3. 题目练习

### GET /api/questions

| 参数 | 说明 |
| --- | --- |
| `province_code` | 省份代码；缺省时取当前用户设置的省份 |
| `chapter_id` | 章节 ID，自动包含其所有子孙章节 |
| `mode` | `practice`（默认，按章节顺序）/ `random`（打乱；以「用户 + 章节 + 省份」为种子，同一场练习多次请求顺序稳定，答题卡与答题页题号一致） |
| `year_only` | `true` 时只返回带年份的真题 |

```json
{
  "items": [
    {
      "id": 12,
      "province_code": "SC",
      "chapter_id": 2,
      "chapter_name": "第一节 基本概念",
      "type": "single",
      "stem": "政府采购应当遵循的基本原则不包括下列哪一项？",
      "options": [
        { "key": "A", "text": "公开透明" },
        { "key": "B", "text": "公平竞争" }
      ],
      "difficulty": "easy",
      "year": null,
      "source_note": "示例题目",
      "is_free": true,
      "is_favorited": false
    }
  ],
  "count": 1
}
```

注意：列表**不返回** `correct_answer` 与 `explanation`。非会员只能拿到 `is_free = true` 的题目。限流：登录用户 120 次/分钟（按用户），游客按 IP。

### POST /api/questions/{question_id}/answer

```json
// 请求
{ "selected": ["C"], "mode": "practice" }

// 响应
{
  "question_id": 12,
  "is_correct": true,
  "selected": ["C"],
  "correct_answer": ["C"],
  "explanation": "本题为系统示例题目……",
  "chapter_name": "第一节 基本概念"
}
```

- 选项 key 不在题目选项内 → `400 {"detail": "选项不合法"}`
- 非会员作答收费题 → `403 {"detail": "该题目为会员专享，请先激活会员"}`
- 登录用户答错会自动进入错题本；游客不写记录

---

## 4. 错题与收藏

均需登录。

### GET /api/wrong

```json
{
  "total": 3,
  "groups": [
    {
      "chapter_id": 2,
      "chapter_name": "第一节 基本概念",
      "items": [
        {
          "question": { "id": 12, "stem": "……", "options": [], "is_favorited": false },
          "wrong_count": 2,
          "last_wrong_at": "2026-10-28T13:20:00"
        }
      ]
    }
  ]
}
```

### DELETE /api/wrong/{question_id}

软删除（`removed = true`），返回 `{"ok": true}`。

### GET /api/favorites?target_type=question

`target_type` 可选 `question` / `law_article`，缺省返回全部。

```json
{
  "items": [
    {
      "id": 5,
      "target_type": "question",
      "target_id": "12",
      "question": { "id": 12, "stem": "……" }
    },
    {
      "id": 6,
      "target_type": "law_article",
      "target_id": "88",
      "law_article": { "id": 88, "article_no": "第一条", "content": "……" },
      "law_document": {
        "id": 3,
        "title": "中华人民共和国政府采购法",
        "status": "effective",
        "category": "国家法律",
        "issuer": "全国人民代表大会常务委员会",
        "province_code": "national",
        "publish_date": "2002-06-29"
      }
    }
  ]
}
```

### POST /api/favorites

```json
{ "target_type": "question", "target_id": "12" }
```

幂等：已收藏返回 `{"ok": true, "created": false}`。

### DELETE /api/favorites/{target_type}/{target_id}

返回 `{"ok": true}`。

---

## 5. 法规库

### GET /api/laws?province_code=SC&category=&status=

返回 `{"items": [...]}`，按「现行有效 → 已修订 → 已废止」排序；`province_code` 有值时同时包含 `national` 法规。

```json
{
  "items": [
    {
      "id": 3,
      "title": "中华人民共和国政府采购法",
      "category": "national",
      "issuer": "全国人民代表大会常务委员会",
      "publish_date": "2002-06-29",
      "revise_date": "2014-08-31",
      "status": "effective",
      "province_code": "national",
      "article_count": 88
    }
  ]
}
```

### GET /api/laws/search?q=质疑&province_code=SC

在法规标题与条文中不区分大小写检索。

```json
{
  "q": "质疑",
  "total": 2,
  "hits": [
    {
      "document": { "id": 3, "title": "中华人民共和国政府采购法", "article_count": 88 },
      "article": { "id": 55, "article_no": "第五十二条", "chapter_title": "第六章 质疑与投诉", "content": "供应商认为……", "sort_order": 52 },
      "positions": [4],
      "title_hit": false
    }
  ]
}
```

`positions` 为关键词在条文中的字符下标，供前端高亮/定位。

### GET /api/laws/{document_id}

返回 `{"document": {...}, "articles": [{..., "is_favorited": false}]}`；登录用户会标记已收藏的条文。

---

## 6. 模拟考试

### GET /api/exam/config?province_code=SC

```json
{
  "province_code": "SC",
  "question_count": 100,
  "duration_minutes": 120,
  "pass_score": 60,
  "total_score": 100,
  "type_distribution": null,
  "configured": true,
  "available_questions": 320,
  "user_settings": { "exam_question_count": 60, "exam_duration_minutes": 90 }
}
```

`configured = false` 表示管理员尚未配置本省考试参数（题量/时长/及格分/总分四项齐全才为 true）。

### POST /api/exam/start · 会员

```json
// 请求（均可选，缺省取用户设置 → 省份配置）
{ "question_count": 60, "duration_minutes": 90 }

// 响应
{
  "id": 7,
  "started_at": "2026-10-28T13:30:00",
  "duration_limit_sec": 5400,
  "total": 60,
  "server_time": "2026-10-28T13:30:00",
  "pass_score": 60,
  "total_score": 100,
  "questions": [ { "id": 12, "type": "single", "stem": "……", "options": [] } ]
}
```

非会员 → `403 {"detail": "模拟考试仅会员可参加"}`。

### GET /api/exam/{exam_id}

用于刷新或断网恢复，返回本次考试题目、已保存答案、`remaining_seconds`；若已超时则自动交卷。

### POST /api/exam/{exam_id}/answer

```json
{ "question_id": 12, "selected": ["A", "C"] }
// → {"saved": true, "answered": 8, "total": 60}
// 超时：{"auto_submitted": true}
```

### POST /api/exam/{exam_id}/submit

```json
// 请求（可选：一次性提交全部答案）
{ "answers": { "12": ["A"], "13": ["B", "C"] } }

// 响应
{
  "id": 7,
  "score": 86.5,
  "passed": true,
  "total": 60,
  "total_score": 100,
  "pass_score": 60,
  "used_seconds": 3120,
  "submitted_at": "2026-10-28T14:22:00"
}
```

重复交卷幂等返回同一摘要。

### GET /api/exam/{exam_id}/result

```json
{
  "exam": { "id": 7, "score": 86.5, "passed": true, "total": 60, "pass_score": 60, "total_score": 100, "used_seconds": 3120 },
  "chapters": [
    { "chapter_id": 2, "chapter_name": "第一节 基本概念", "total": 20, "correct": 17, "accuracy": 85.0 }
  ],
  "wrong_items": [
    {
      "question": { "id": 13, "stem": "……", "correct_answer": ["B"], "explanation": "……" },
      "selected": ["A"]
    }
  ]
}
```

### GET /api/exam/history

```json
{
  "items": [
    { "id": 7, "started_at": "2026-10-28T13:30:00", "submitted_at": "2026-10-28T14:22:00", "score": 86.5, "passed": true, "total": 60, "used_seconds": 3120, "duration_limit_sec": 5400 }
  ]
}
```

---

## 7. 会员激活

### POST /api/activate · 登录

```json
// 请求
{ "code": "SX2026-ABCD-EFGH" }
// 响应
{ "ok": true, "expires_at": "2027-01-26T13:40:00", "duration_days": 90 }
```

- 未过期会员续期会在原到期时间上叠加
- 激活码不存在/已使用/已禁用 → 400 或 404
- 同一用户 10 分钟内失败 5 次 → `429 {"detail": "尝试次数过多，请稍后再试"}`

---

## 8. 站点配置与统计

### GET /api/site-config · 公开

```json
{ "service_phone": "028-88888888", "service_wechat": "sx-expert", "service_intro": "……" }
```

缺失项返回空字符串。

### POST /api/feedback · 可选登录

```json
{ "content": "第一章第 3 题答案有误" }   // 1~1024 字
// → {"ok": true}
```

### GET /api/stats

```json
{
  "answered_count": 320,
  "correct_count": 265,
  "correct_rate": 82.8,
  "wrong_count": 12,
  "favorite_count": 6,
  "exam_count": 3,
  "membership_expires_at": "2027-01-26T13:40:00"
}
```

未登录时全部为零值、`membership_expires_at` 为 `null`。
