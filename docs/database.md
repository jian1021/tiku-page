# 数据库说明

## 1. 连接配置

后端通过环境变量 `DATABASE_URL` 指定数据库，默认值为 `sqlite:///./data/app.db`（相对 `backend/` 目录）。

```bash
# 开发：SQLite
DATABASE_URL=sqlite:///./data/app.db

# 生产：MySQL（需先创建库并安装 pymysql）
DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/expert_exam?charset=utf8mb4
```

配置读取顺序：环境变量（`.env` 文件）> `app/config.py` 中的默认值。

## 2. 建表

- 后端启动时自动执行 `Base.metadata.create_all()`，已存在的表不会被修改。
- 管理后台**不建表**，需先启动一次后端或执行种子脚本。
- 结构变更（新增字段等）建议引入 Alembic 迁移，或在开发环境删除 `data/app.db` 后重新建表 + 种子。

## 3. 表结构概览

| 表 | 说明 | 关键字段 |
| --- | --- | --- |
| `users` | 用户 | `phone`（唯一）、`password_hash`、`role`（user/admin）、`province_code`、`settings`（JSON） |
| `chapters` | 章节（自关联树） | `province_code`、`parent_id`、`sort_order`，唯一键 `(province_code, parent_id, name)` |
| `questions` | 题目 | `type`（single/multi/judge）、`stem`、`options`（JSON `[{key,text}]`）、`answer`（JSON key 数组）、`explanation`、`is_free`、`status`（published/draft） |
| `law_documents` | 法规文件 | `title`、`category`、`issuer`、`status`（effective/revised/repealed）、`province_code`（`national` 表示全国） |
| `law_articles` | 法规条文 | `document_id`、`article_no`、`chapter_title`、`content`、`sort_order` |
| `activation_codes` | 激活码 | `code`（唯一）、`duration_days`、`status`（unused/used/disabled）、`used_by`、`used_at` |
| `memberships` | 会员有效期 | `user_id`（唯一）、`expires_at` |
| `answer_records` | 答题记录 | `user_id`、`question_id`、`selected`（JSON）、`is_correct`、`mode`（practice/exam） |
| `wrong_questions` | 错题本 | `user_id` + `question_id` 唯一、`wrong_count`、`last_wrong_at`、`removed`（软删除） |
| `favorites` | 收藏 | `user_id`、`target_type`（question/law_article）、`target_id`（字符串），三者唯一 |
| `exams` | 模拟考试 | `question_ids`（JSON）、`answers`（JSON）、`score`、`passed`、`started_at`、`submitted_at`、`duration_limit_sec` |
| `exam_configs` | 考试参数 | `province_code` + `key`：`question_count`、`duration_minutes`、`pass_score`、`total_score`、`type_distribution` |
| `site_configs` | 站点配置 | `key`（唯一）：`service_phone`、`service_wechat`、`service_intro` 等 |
| `feedbacks` | 意见反馈 | `user_id`（可空）、`content`、`created_at` |

JSON 字段统一使用 SQLAlchemy `JSON` 类型，SQLite 与 MySQL 8 均可正常存储。

## 4. 种子数据

在 `backend/` 目录执行（可重复执行）：

```bash
python seed.py
```

会创建：

| 角色 | 账号 | 密码 | 说明 |
| --- | --- | --- | --- |
| 管理员 | `admin` | `admin123` | 跳过会员校验，可用于后台管理 |
| 示例考生 | `13800138000` | `test1234` | 未激活，只能练免费题 |
| 示例考生 | `13900139000` | `test1234` | 已开通 30 天会员 |

同时写入示例章节、示例题目、示例法规与条文、激活码（`DEMO-30D-0001`、`DEMO-7D-0001`、`DEMO-DISABLED`）、站点配置与考试参数。

> 示例题目与法条均为联调用占位内容，不含真实考试信息；上线前需在管理后台替换或清空。

## 5. 备份与恢复

SQLite：

```bash
# 备份（建议停服或用 sqlite3 .backup 保证一致性）
sqlite3 backend/data/app.db ".backup 'backup-$(date +%F).db'"

# 恢复
cp backup-2026-10-28.db backend/data/app.db
```

MySQL：

```bash
mysqldump -u user -p --single-transaction expert_exam > expert_exam.sql
mysql -u user -p expert_exam < expert_exam.sql
```

Docker 环境下数据文件通过 `backend-data` 卷持久化，`docker compose down` 不会删除数据；只有 `docker compose down -v` 才会连同卷一起删除。
