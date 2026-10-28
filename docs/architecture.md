# 系统架构

## 1. 总体结构

| 层 | 技术 | 目录 | 职责 |
| --- | --- | --- | --- |
| 前端 | Vue 3 + Vite + Vue Router + Pinia | `frontend/` | 手机优先 H5、PWA、全部交互逻辑 |
| 后端 | FastAPI + SQLAlchemy 2.0 | `backend/app/` | 鉴权、题库、判分、考试、法规、站点配置 |
| 管理后台 | Streamlit + SQLAlchemy | `admin/` | 题库录入、激活码、站点配置、数据查看 |
| 数据库 | SQLite（开发）/ MySQL（生产） | `backend/data/app.db` | 业务数据持久化 |

前端只通过 `/api` 前缀访问后端，生产环境由 Nginx 把 `/api` 反向代理到 FastAPI，其余路径交给前端静态资源，因此不存在跨域问题；开发环境由 Vite 的 `server.proxy` 完成同样转发。

## 2. 目录结构

```
tiku-page/
├── frontend/
│   ├── index.html                # 入口 HTML（含 PWA meta）
│   ├── public/                   # manifest.webmanifest、sw.js、icon.svg
│   ├── vite.config.js            # 别名 @、/api 代理、px 转 vw
│   └── src/
│       ├── main.js               # 应用引导：Pinia、路由、全局样式、SW 注册
│       ├── App.vue               # 应用外壳：TabBar、Toast、主题/字号
│       ├── api/                  # 按域拆分的接口封装（axios 实例统一处理 401 与错误）
│       ├── stores/               # Pinia：auth / ui（其余为早期版本，见 §5）
│       ├── router/index.js       # 路由表与登录守卫
│       ├── components/           # TopBar、TabBar、Modal、Toast、Empty、Skeleton、ProgressBar、icons
│       ├── composables/          # useToast 全局提示
│       ├── views/                # 页面组件
│       ├── auth/                 # 登录、注册页
│       └── styles/               # global.css 设计令牌 + 全局组件样式
├── backend/
│   ├── main.py                   # 启动入口：uvicorn app.main:app
│   ├── app/
│   │   ├── main.py               # FastAPI 实例、CORS、路由挂载、建表
│   │   ├── config.py             # 配置（环境变量 / .env）
│   │   ├── database.py           # 引擎、会话、Base、get_db
│   │   ├── models.py             # 14 张业务表
│   │   ├── auth.py               # 密码哈希与 JWT
│   │   ├── deps.py               # 依赖：当前用户、会员/管理员校验
│   │   ├── serializers.py        # 题目公开/带答案序列化
│   │   ├── ratelimit.py          # 内存限流（题目列表、激活失败）
│   │   ├── seed.py               # 幂等种子数据
│   │   └── routers/              # auth、chapters、questions、wrong_favorites、laws、exams、members、site
│   ├── requirements.txt          # 运行时依赖
│   ├── requirements-tools.txt    # 题库导入脚本依赖（pandas 等）
│   └── data/app.db               # SQLite 数据文件（不提交版本库）
├── admin/                        # Streamlit 管理后台
├── docs/                         # 本文档目录
└── docker-compose.yml            # 一键部署
```

## 3. 关键设计

### 3.1 鉴权与权限

- 登录成功后后端签发 JWT（`sub` 为用户 ID，默认 7 天有效），前端存入 `localStorage` 的 `sx_token`。
- axios 请求拦截器自动附加 `Authorization: Bearer <token>`；响应 401 时清除令牌并广播 `auth:unauthorized`，前端回到未登录态。
- 权限分三档：
  - 游客：可浏览章节、练习免费题目（`questions.is_free = true`）、查看法规库。
  - 会员：可练习全部题目、参加模拟考试（校验 `memberships.expires_at`）。
  - 管理员（`users.role = 'admin'`）：跳过会员校验。

### 3.2 答题与判分

- 题目列表接口不下发答案与解析，只有提交作答（`POST /api/questions/{id}/answer`）的响应才带 `correct_answer` 与 `explanation`，减少答案被抓取的风险。
- 判分规则：单选、多选、判断统一按「选项集合完全相等」判定。
- 答错会写入 `answer_records` 并更新 `wrong_questions`（累计错误次数，`removed` 标记软删除）。

### 3.3 模拟考试

- `POST /api/exam/start` 随机抽题生成 `exams` 记录，写入抽题列表与截止时长。
- 答题过程中 `POST /api/exam/{id}/answer` 逐题保存（支持刷新/断网恢复）。
- 交卷或超时后统一走内部判分：计算分数、记录 `answer_records`、累加错题、返回章节正确率与错题明细。
- 前端剩余时间以服务端 `remaining_seconds` 为准，避免本地时钟漂移。

### 3.4 前端状态与主题

- `stores/ui.js` 管理主题（light/dark）、正文字号（16/18/20px）、游客省份，写入 `localStorage` 并在挂载前应用，避免首屏闪烁。
- 主题通过 `html[data-theme]` 与 `#app-shell.theme-dark` 两套选择器覆盖 CSS 变量，所有颜色均取自 `global.css` 的变量，不写死色值。
- `stores/auth.js` 缓存用户信息与会员到期时间，提供 `isLoggedIn`、`isMember`、`memberDaysLeft` 等派生状态。

### 3.5 PWA 与缓存策略

`public/sw.js` 采用如下策略：

- 静态资源：stale-while-revalidate。
- `/api/` 请求：完全不缓存（避免含答案的判分响应落到离线缓存）。
- 导航请求：网络优先，失败回退缓存的首页。

## 4. 里程碑对照

| 里程碑 | 内容 | 状态 |
| --- | --- | --- |
| M1 | 账号登录注册、章节练习、激活码 | 已完成 |
| M2 | 错题本、收藏、模拟考试 | 已完成 |
| M3 | 法规库、全文检索与高亮 | 已完成 |
| M4 | 服务页、我的、夜间模式、字号、PWA、学习统计 | 已完成 |

## 5. 历史遗留说明

`backend/routers/`（扁平路由）与 `frontend/src/views/practice|law/`、`frontend/src/stores/{practice,law,exam,settings}.js` 属于早期版本，接口路径与当前后端不一致，**已不再被引用**（`backend/main.py` 已改为加载 `app.main:app`，前端路由指向 `src/views/` 根目录下的页面）。保留它们仅作历史参考，新增功能请勿沿用。
