# 四川专家库入库考试助手（H5）

面向各省政府采购评审专家入库考试的备考网页应用，手机优先，响应式设计。

## 项目结构

```
/
├── frontend/          # Vue 3 + Vite 前端应用（H5 + PWA）
├── backend/           # Python FastAPI 后端应用
├── admin/             # Streamlit 管理后台
├── docs/              # 项目文档（架构 / 接口 / 数据库 / 开发 / 部署）
└── docker-compose.yml # 一键部署（前端 + 后端 + 管理后台）
```

## 技术栈

- **前端**: Vue 3 + Vite + Vue Router + Pinia
- **后端**: Python FastAPI + SQLAlchemy 2.0
- **管理后台**: Streamlit
- **数据库**: SQLite (开发) / MySQL (生产)
- **部署**: Docker Compose + Nginx

## 快速开始

### 环境要求

- Node.js 18+
- Python 3.10+
- Docker & Docker Compose（可选，用于部署）

### 开发环境启动

1. **克隆项目**

   ```bash
   git clone <repository-url>
   cd tiku-page
   ```

2. **启动后端**

   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   python seed.py       # 首次运行：写入示例账号、章节、题目与法规
   python main.py       # 默认 http://localhost:8000
   ```

3. **启动前端**

   ```bash
   cd frontend
   npm install
   npm run dev          # 默认 http://localhost:3000
   ```

4. **启动管理后台**

   ```bash
   cd admin
   pip install -r requirements.txt
   streamlit run app.py # 默认 http://localhost:8501
   ```

> 示例账号（`python seed.py` 后可用）：管理员 `admin / admin123`；普通用户 `13800138000 / test1234`；已激活会员 `13900139000 / test1234`。

### 生产环境部署

```bash
cp backend/.env.example .env   # 修改 SECRET_KEY 与 ADMIN_PASSWORD
docker compose up -d --build
docker compose exec backend python seed.py   # 可选，正式环境建议用管理后台录入
```

默认访问：前端 `http://<服务器IP>:8080`，管理后台 `http://<服务器IP>:8501`。完整步骤见 [docs/deployment.md](docs/deployment.md)。

## 功能特性

- 📱 手机优先，响应式设计（正文字号 16/18/20px 三档可调）
- 📝 在线答题：章节练习、随机练习、只看真题、答题卡、错题本、收藏
- 📖 法规库：分类与效力状态筛选、标题与条文全文检索并高亮定位
- 📊 模拟考试：随机抽题、倒计时与超时自动交卷、章节正确率与错题解析、历史成绩
- 🔐 会员激活：激活码开通/续期，非会员仅可练习免费题目
- 📈 学习数据：累计答题、正确率、错题数、收藏数、考试次数
- 🌙 夜间模式与 PWA（可添加到主屏幕，静态资源离线可用）

## 开发里程碑

- **M1**: 基础框架（账号登录、章节练习、激活码）✅
- **M2**: 错题与考试功能 ✅
- **M3**: 法规库功能 ✅
- **M4**: 完善功能（服务页、我的、夜间模式、PWA、学习统计）✅

## 文档

| 文档 | 内容 |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | 架构、目录结构、关键设计 |
| [docs/api.md](docs/api.md) | 接口清单与请求/响应示例 |
| [docs/database.md](docs/database.md) | 数据模型、建表与种子数据 |
| [docs/development.md](docs/development.md) | 本地开发与常见问题 |
| [docs/deployment.md](docs/deployment.md) | Docker / Nginx / HTTPS / 备份 |

## 接口文档

后端 API 文档可在 `http://localhost:8000/docs` 查看（开发环境）。

## 目录结构

```
tiku-page/
├── backend/                 FastAPI 服务
│   ├── app/
│   │   ├── main.py          应用入口（统一挂载 /api）
│   │   ├── config.py        配置（DATABASE_URL / SECRET_KEY / CORS）
│   │   ├── database.py      SQLAlchemy engine 与 Session
│   │   ├── models.py        ORM 模型（13 张表）
│   │   ├── auth.py          JWT 与密码哈希
│   │   ├── deps.py          依赖注入（当前用户、会员校验）
│   │   ├── ratelimit.py     登录/激活限流
│   │   ├── serializers.py   响应序列化（列表接口不下发答案）
│   │   └── routers/         auth / chapters / questions / exams /
│   │                        laws / members / site / wrong_favorites
│   ├── main.py              启动器（uvicorn app.main:app）
│   ├── seed.py              建表 + 种子数据（幂等）
│   ├── data/app.db          SQLite 数据文件（已 gitignore）
│   └── Dockerfile
├── frontend/                Vue 3 + Vite SPA
│   ├── src/
│   │   ├── api/             9 个接口封装，统一走 /api
│   │   ├── stores/          auth / ui（Pinia）
│   │   ├── views/           16 个页面
│   │   ├── components/      TabBar / Modal / Toast / ProgressBar 等
│   │   └── styles/          global.css 设计令牌
│   ├── public/              manifest.webmanifest / sw.js / icon.svg
│   ├── nginx.conf           生产反代（/api → backend）
│   └── Dockerfile
├── admin/                   Streamlit 管理后台
├── docs/                    架构 / 接口 / 数据库 / 开发 / 部署
└── docker-compose.yml       backend + frontend + admin 一键启动
```

> 早期版本的扁平后端（`backend/routers/`、`backend/models.py`）与旧页面
> （`frontend/src/views/practice|law/`、`frontend/src/stores/{practice,law,exam,settings}.js`）
> 已全部删除。若从旧提交回溯，请注意其接口与当前后端不兼容。

## 许可证

[待定]
