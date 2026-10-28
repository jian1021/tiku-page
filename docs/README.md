# 项目文档

本目录集中存放「四川专家库入库考试助手」的开发与运维文档。

| 文档 | 内容 |
| --- | --- |
| [architecture.md](./architecture.md) | 系统架构、目录结构、前后端职责边界 |
| [api.md](./api.md) | 后端接口清单与请求/响应示例 |
| [database.md](./database.md) | 数据模型、建表与种子数据 |
| [development.md](./development.md) | 本地开发、调试与常见问题 |
| [deployment.md](./deployment.md) | Docker / Nginx 部署、域名与备份 |

## 一句话架构

```
浏览器（Vue 3 + Vite H5 / PWA）
        │  /api 反向代理
        ▼
FastAPI（backend/app）── SQLAlchemy ── SQLite / MySQL
        ▲
        └── Streamlit 管理后台（admin）直连同一数据库
```

## 快速验证清单

1. 后端：`cd backend && python main.py`，访问 `http://localhost:8000/docs` 可见 Swagger。
2. 前端：`cd frontend && npm run dev`，访问 `http://localhost:3000`。
3. 首页能显示章节树与题量，说明 `/api/provinces`、`/api/chapters` 正常。
4. 注册并登录后，答错一题再进入「错题本」，能看到该题，说明判分与错题入库正常。
5. 在「我的」输入激活码后，模拟考试可正常开始，说明会员校验正常。
