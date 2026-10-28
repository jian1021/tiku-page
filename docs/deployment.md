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

## 5. 手动部署（无 Docker）

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

## 6. 升级与回滚

```bash
git pull
docker compose up -d --build       # 重建镜像，数据卷不受影响
```

- 升级前先备份数据库（见 `database.md` 第 5 节）。
- 如涉及表结构变更，需在发布前执行迁移脚本；当前项目未启用 Alembic 版本管理，结构调整请先在测试库验证。
- 回滚：`git checkout <上一个版本 tag>` 后重新 `docker compose up -d --build`，并按需恢复数据库备份。

## 7. 监控与日志

- 健康检查：`curl http://127.0.0.1:8080/api/../health` 不经过代理，建议直接 `docker compose exec backend python -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/health').read())"`。
- 日志：`docker compose logs -f --tail=200 backend`。
- 关键指标：接口 5xx 数量、`/api/questions` 响应时间、激活失败次数（限流触发情况）。
