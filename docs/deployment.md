# 部署指南

## 1. Docker Compose（推荐）

```bash
# 1. 复制并修改环境变量
cp backend/.env.example .env
# 至少修改 SECRET_KEY、ADMIN_PASSWORD；WEB_PORT 可改对外端口

# 2. 构建并启动
docker compose up -d --build

# 3. 首次部署写入示例数据（可选，正式环境建议用管理后台录入真实题库）
docker compose exec backend python seed.py

# 4. 查看状态与日志
docker compose ps
docker compose logs -f backend
```

访问地址：

| 服务 | 地址 | 说明 |
| --- | --- | --- |
| 前端 | `http://<服务器IP>:8080` | 由 `WEB_PORT` 控制，Nginx 托管静态资源并代理 `/api` |
| 后端 | 仅容器内暴露 `8000` | 不直接对公网开放，通过前端 Nginx 转发 |
| 管理后台 | `http://<服务器IP>:8501` | 建议限制来源 IP 或走内网 |

关闭：

```bash
docker compose down          # 保留数据卷
docker compose down -v       # 连同数据库一起删除（谨慎）
```

## 2. 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `SECRET_KEY` | `change-me-in-production` | JWT 签名密钥，**必须修改**为随机长串 |
| `DATABASE_URL` | `sqlite:///./data/app.db` | 后端数据库连接串 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` | 令牌有效期（分钟），默认 7 天 |
| `CORS_ORIGINS` | `http://localhost,http://localhost:8080` | 允许跨域来源，逗号分隔 |
| `WEB_PORT` | `8080` | 前端对外端口 |
| `ADMIN_PORT` | `8501` | 管理后台对外端口 |
| `ADMIN_USER` / `ADMIN_PASSWORD` | `admin` / `admin123` | 管理后台登录口令，**必须修改** |

生成随机密钥：

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 3. 使用 MySQL

1. 创建数据库（推荐 utf8mb4）：

```sql
CREATE DATABASE expert_exam CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. 修改 `.env`：

```dotenv
DATABASE_URL=mysql+pymysql://user:password@mysql:3306/expert_exam?charset=utf8mb4
```

3. 在 `docker-compose.yml` 中增加 MySQL 服务，并把 `backend` 的 `depends_on` 指向它；`backend` 镜像已包含 `pymysql`。

4. 首次启动后端会自动建表，随后执行 `docker compose exec backend python seed.py` 可选地写入示例数据。

## 4. 域名与 HTTPS

### 4.1 前置反向代理（推荐）

在宿主机用已有的 Nginx/Caddy 终止 TLS，再转发到容器：

```nginx
server {
    listen 443 ssl http2;
    server_name exam.example.com;

    ssl_certificate     /etc/letsencrypt/live/exam.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/exam.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

证书可用 `certbot --nginx -d exam.example.com` 自动申请与续期。

### 4.2 上线检查清单

- [ ] `SECRET_KEY`、`ADMIN_PASSWORD` 已替换，`.env` 未提交到仓库
- [ ] `CORS_ORIGINS` 只保留正式域名
- [ ] 管理后台端口不对公网开放，或加了 IP 白名单/基础认证
- [ ] 示例题库与示例法条已替换为正式内容（或已清空）
- [ ] `exam_configs` 的题量、时长、及格分、总分与本省考试要求一致
- [ ] 已配置数据库定期备份
- [ ] HTTPS 生效，`sw.js` 返回 `Cache-Control: no-cache`

## 5. 前端托管到 Cloudflare Pages（前后端分离）

适用场景：前端放 Cloudflare Pages（免费、全球 CDN、自动 HTTPS），后端 FastAPI 仍跑在 Docker Compose / 云服务器上。

> **前提**：Pages 只能托管 Vite 构建出的静态文件，**不能运行 FastAPI**。数据库与 `/api/*` 接口必须由独立部署的后端提供。Pages 站点上没有 `/api`，因此必须通过环境变量 `VITE_API_BASE` 把接口指向后端的公网地址。

### 5.1 后端准备

后端先对外提供 HTTPS 地址（如 `https://api.example.com`），然后把 Pages 域名加入白名单：

```bash
# backend/.env
CORS_ORIGINS=https://tiku-page.pages.dev
# 每次 PR 的预览域名是随机子域，用正则一次覆盖
CORS_ORIGIN_REGEX=https://.*\.tiku-page\.pages\.dev
```

改完重启后端。未配置时前端会报 `blocked by CORS policy`。

### 5.2 在 Cloudflare 后台创建项目

Workers & Pages → Create → Pages → Connect to Git → 选择仓库 `jian1021/tiku-page`。

构建参数：

| 配置项 | 值 |
| --- | --- |
| Framework preset | `Vue` |
| Root directory | `frontend` |
| Build command | `npm run build` |
| Build output directory | `dist` |
| 环境变量 `VITE_API_BASE` | `https://api.example.com/api` |
| 环境变量 `NODE_VERSION` | `20` |

仓库里已备好构建所需的配套文件，无需额外配置：

- `frontend/public/_redirects`：`/* /index.html 200`，解决 history 模式深链刷新 404
- `frontend/public/_headers`：`/assets/*` 强缓存、`sw.js` 与 `index.html` 不缓存
- `frontend/wrangler.toml`：命令行部署时指定项目名与产物目录

### 5.3 命令行部署（可选）

不想接 Git 自动构建时：

```bash
cd frontend
npm ci
VITE_API_BASE=https://api.example.com/api npm run build
npx wrangler pages deploy      # 首次会要求 wrangler login 授权
```

### 5.4 上线校验

- [ ] 首页可打开，直接访问 `/law/search` 并刷新不 404（`_redirects` 生效）
- [ ] 浏览器 Network 中接口请求域名是后端地址，不再是 Pages 域名
- [ ] `curl -I https://<项目>.pages.dev/sw.js` 返回 `Cache-Control: no-cache`
- [ ] 能登录、能看到题库（说明后端已执行过 `seed.py`）

### 5.5 题库数据不在 Pages 里

Pages 产物只含前端代码，**105 道 2026 四川真题在后端数据库里**。后端首次部署后执行：

```bash
cd backend
python seed.py                 # 建表 + 示例数据 + 自动导入题库
# 或只做题库增量导入
python import_papers.py --dry-run
python import_papers.py
```

## 6. 手动部署（无 Docker）

```bash
# 后端
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
RELOAD=0 python main.py            # 建议用 systemd/supervisor 守护

# 前端
cd ../frontend
npm ci && npm run build            # 产物 dist/
# 将 dist/ 交给 Nginx，并按 docs 中的 frontend/nginx.conf 配置 /api 反代
```

systemd 单元示例：

```ini
[Unit]
Description=tiku backend
After=network.target

[Service]
WorkingDirectory=/opt/tiku/backend
Environment=RELOAD=0
Environment=DATABASE_URL=sqlite:///./data/app.db
ExecStart=/opt/tiku/backend/.venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## 7. 升级与回滚

```bash
git pull
docker compose up -d --build       # 重建镜像，数据卷不受影响
```

- 升级前先备份数据库（见 `database.md` 第 5 节）。
- 如涉及表结构变更，需在发布前执行迁移脚本；当前项目未启用 Alembic 版本管理，结构调整请先在测试库验证。
- 回滚：`git checkout <上一个版本 tag>` 后重新 `docker compose up -d --build`，并按需恢复数据库备份。

## 8. 监控与日志

- 健康检查：`curl http://127.0.0.1:8080/api/../health` 不经过代理，建议直接 `docker compose exec backend python -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/health').read())"`。
- 日志：`docker compose logs -f --tail=200 backend`。
- 关键指标：接口 5xx 数量、`/api/questions` 响应时间、激活失败次数（限流触发情况）。
