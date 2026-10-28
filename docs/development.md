# 本地开发指南

## 1. 环境要求

| 组件 | 版本 | 说明 |
| --- | --- | --- |
| Node.js | 18+（推荐 20 LTS） | 前端构建 |
| Python | 3.10+（推荐 3.12） | 后端与管理后台 |
| SQLite | 随 Python 自带 | 开发数据库，无需额外安装 |

## 2. 启动后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 首次运行：写入示例数据（可重复执行）
python seed.py

# 启动服务（默认 0.0.0.0:8000，自动重载）
python main.py
```

- 接口文档：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/health>
- 数据文件：`backend/data/app.db`（首次启动自动建表）

生产或不需热重载时：`RELOAD=0 python main.py`。

> 题库导入脚本需要 pandas / pdfplumber 等，额外执行 `pip install -r requirements-tools.txt`。

## 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

默认地址 <http://localhost:3000>，`/api` 由 Vite 代理到 `http://localhost:8000`（见 `vite.config.js`），无需处理跨域。

生产构建与本地预览：

```bash
npm run build     # 产物在 dist/
npm run preview   # 预览构建结果
```

> 若从其他操作系统拷贝了 `node_modules`（例如 Windows → macOS），`rollup`/`esbuild` 的平台二进制会不匹配，报 `Cannot find module '@rollup/rollup-darwin-arm64'` 之类错误。删除 `node_modules` 与 `package-lock.json` 后重新 `npm install` 即可。
>
> 本仓库历史上曾把 `frontend/node_modules` 提交进 Git（跨机器克隆时会直接带出错误平台的二进制）。`.gitignore` 已忽略该目录，建议执行一次 `git rm -r --cached frontend/node_modules` 把它移出版本库（只改索引，不删本地文件）。

## 4. 启动管理后台

```bash
cd admin
pip install -r requirements.txt
streamlit run app.py
```

默认地址 <http://localhost:8501>，与后端共用 `backend/data/app.db`（可用 `DATABASE_URL` 覆盖）。

## 5. 测试账号

执行 `python seed.py` 后可用：

| 账号 | 密码 | 说明 |
| --- | --- | --- |
| `admin` | `admin123` | 管理员，跳过会员校验 |
| `13800138000` | `test1234` | 普通用户（未激活） |
| `13900139000` | `test1234` | 已开通 30 天会员 |

示例激活码：`DEMO-30D-0001`、`DEMO-7D-0001`、`DEMO-DISABLED`（已禁用，用于验证错误提示）。

## 6. 调试要点

### 6.1 前端页面与接口对照

| 页面 | 路由 | 主要接口 |
| --- | --- | --- |
| 练习首页 | `/` | `/provinces`、`/chapters`、`/stats` |
| 章节详情 | `/chapter/:id` | `/chapters` |
| 答题 | `/quiz` | `/questions`、`/questions/{id}/answer`、`/favorites` |
| 答题卡 | `/quiz/card` | `/questions` |
| 错题本 | `/wrong` | `/wrong` |
| 收藏 | `/favorites` | `/favorites` |
| 法规库 | `/law`、`/law/:id`、`/law/search` | `/laws`、`/laws/{id}`、`/laws/search` |
| 模拟考试 | `/exam`、`/exam/run`、`/exam/result/:id` | `/exam/*` |
| 服务 | `/service` | `/site-config`、`/feedback` |
| 我的 | `/me` | `/me`、`/activate`、`/stats` |

### 6.2 常见问题

| 现象 | 原因与处理 |
| --- | --- |
| 首页空白 / 控制台 `Failed to resolve import` | 路由指向的页面文件缺失，检查 `src/router/index.js` 与 `src/views/` 是否一致 |
| 页面样式错乱、颜色丢失 | `main.js` 必须引入 `styles/global.css`（设计令牌来源） |
| 接口 401 并自动退出 | 令牌过期或 `SECRET_KEY` 变更，重新登录即可 |
| 练习提示「会员专享」 | 该题 `is_free=false`，用已激活账号或输入激活码 |
| 开始考试提示「尚未配置」 | `exam_configs` 缺少题量/时长/及格分/总分，去管理后台补齐 |
| 启动考试 403 | 账号未激活会员（`memberships.expires_at` 已过期） |
| 章节题量为 0 | 题目 `status` 不是 `published`，或没有绑定 `chapter_id` |
| 法规搜索无结果 | 关键词在标题与条文中均未命中，或该法规 `province_code` 不在可见范围 |
| 提示「尝试次数过多」 | 激活码连续输错触发限流，等待 10 分钟 |

### 6.3 代码风格约定

- 前端：Vue 3 `<script setup>`，接口调用集中在 `src/api/`，页面不直接写 axios；颜色只用 `global.css` 中的 CSS 变量。
- 后端：路由按域拆分在 `app/routers/`，Pydantic 模型定义在对应路由文件内，注释使用中文。
- 提交前建议跑一次 `python -m compileall backend/app` 与 `npm run build`。
