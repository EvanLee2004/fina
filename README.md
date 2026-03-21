# Fina 项目总结

## 项目背景

Fina 是 ohao 平台的 AI 智能财务管理后端模块，服务于团队内部财务管理场景。管理员通过 ohao-admin 看板操作，AI Bot 自动调用接口记录财务数据，普通用户可通过对话形式查询自己的财务记录。

## 当前部署状态

目前 PostgreSQL 和 FastAPI 后端都支持通过 Docker Compose 启动。

当前仓库直接提交的是一份“模板版 `.env`”。

这意味着：

- 代码运行时始终只读取根目录 `.env`
- 仓库里的 `.env` 是可公开上传的模板配置，不包含真实 AI Key
- 你拿到代码后直接编辑 `.env` 即可启动
- 如果你本地临时填入了真实 Key，提交前必须把它清空或替换回模板值

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI (Python 3.12) |
| 数据库 | PostgreSQL 15 |
| ORM | SQLAlchemy 2.0 |
| 数据校验 | Pydantic v2 |
| AI 调用 | OpenAI 兼容 REST 接口 |
| 默认模型提供商 | DeepSeek |
| 认证 | X-Admin-Token |
| 部署 | Docker Compose / Railway |

## 环境变量

项目当前使用这些环境变量：

| 变量名 | 说明 |
|---|---|
| `DATABASE_URL` | PostgreSQL 连接地址 |
| `JWT_SECRET` | 备用 JWT 密钥 |
| `AI_API_KEY` | 通用 AI 服务访问密钥 |
| `AI_BASE_URL` | OpenAI 兼容接口基础地址，默认是 DeepSeek |
| `AI_MODEL` | 默认模型名，默认是 `deepseek-chat` |
| `ADMIN_TOKEN` | 后台接口请求头校验令牌 |

默认情况下，AI 调用层会访问：

- `AI_BASE_URL=https://api.deepseek.com/v1`
- 请求路径自动拼成 `/chat/completions`
- `AI_MODEL=deepseek-chat`

如果后续切换其他 OpenAI 兼容提供商，只需要调整 `.env` 中的 `AI_BASE_URL` 和 `AI_MODEL`，不需要改业务代码。

## 项目结构

```text
fina/
├── .env                          # 环境变量模板，代码运行时直接读取
├── docker-compose.yml            # 启动 PostgreSQL + FastAPI
├── README.md
└── backend/
    ├── Dockerfile                # FastAPI 后端镜像构建文件
    ├── main.py                   # FastAPI 入口，启动时自动建表
    ├── requirements.txt          # Python 依赖
    ├── core/
    │   ├── config.py             # 统一读取 .env 配置
    │   ├── database.py           # 数据库连接与 Session 管理
    │   ├── security.py           # JWT 工具（备用）
    │   └── auth.py               # X-Admin-Token 校验依赖
    ├── models/                   # SQLAlchemy 2.0 表模型
    ├── schemas/                  # Pydantic v2 请求/响应结构
    ├── routers/                  # API 路由层
    ├── services/                 # 业务逻辑层
    └── scripts/
        └── init_accounts.py      # 初始化标准会计科目
```

## 数据库设计

当前核心表共 5 张：

| 表名 | 说明 |
|---|---|
| `accounts` | 会计科目表 |
| `vouchers` | 凭证主表 |
| `voucher_entries` | 凭证分录表 |
| `receivables` | 应收应付表 |
| `reports` | AI 财务分析报告存档 |

## API 接口总览

所有接口前缀：`/api/admin/`  
认证方式：请求头 `X-Admin-Token: <token>`

### 科目管理

| 方法 | 地址 | 说明 |
|---|---|---|
| GET | `/api/admin/accounts/` | 获取科目列表 |
| GET | `/api/admin/accounts/tree` | 获取科目树 |
| POST | `/api/admin/accounts/` | 新增科目 |
| PATCH | `/api/admin/accounts/{id}` | 更新科目 |
| DELETE | `/api/admin/accounts/{id}` | 软删除科目 |

### 凭证管理

| 方法 | 地址 | 说明 |
|---|---|---|
| GET | `/api/admin/vouchers/` | 凭证列表，支持日期范围筛选 |
| GET | `/api/admin/vouchers/{id}` | 获取单条凭证 |
| POST | `/api/admin/vouchers/` | 新增凭证，带借贷平衡校验 |
| PATCH | `/api/admin/vouchers/{id}/approve` | 审核凭证 |
| DELETE | `/api/admin/vouchers/{id}` | 删除草稿凭证 |

### AI 接口

| 方法 | 地址 | 说明 |
|---|---|---|
| POST | `/api/admin/ai/parse` | 自然语言转凭证草稿 |
| POST | `/api/admin/ai/report` | 生成 AI 财务分析报告 |
| POST | `/api/admin/ai/query` | 自然语言查询财务数据 |

### 应收应付

| 方法 | 地址 | 说明 |
|---|---|---|
| GET | `/api/admin/receivables/` | 获取列表，支持类型和状态筛选 |
| POST | `/api/admin/receivables/` | 新增记录 |
| PATCH | `/api/admin/receivables/{id}/settle` | 标记已结清 |

### 报表

| 方法 | 地址 | 说明 |
|---|---|---|
| GET | `/api/admin/reports/` | 获取报告列表 |
| GET | `/api/admin/reports/{period}` | 获取指定月份报告 |

## 核心功能说明

### 自然语言记账

用户输入“今天付了 3000 块房租”后，系统会：

1. 从数据库读取所有启用中的会计科目。
2. 把完整科目表和用户输入一起拼进 Prompt。
3. 调用 OpenAI 兼容格式的 `/chat/completions` 接口，默认接 DeepSeek。
4. 严格要求模型只返回 JSON 凭证草稿。
5. 在后端校验借贷平衡，通过后返回给前端确认，不直接入库。

### 借贷平衡校验

创建凭证时会强制校验借方总额等于贷方总额。不平衡直接返回 `400`。已审核凭证不能重复审核，也不能删除。

### AI 财务分析报告

指定月份后，系统会：

1. 汇总该月所有已审核凭证的收入、支出、净利润。
2. 通过 OpenAI 兼容格式接口调用默认 AI 模型生成中文白话分析。
3. 把报告内容存入 `reports` 表。

## 快速启动

```bash
# 1. 按实际情况编辑根目录 .env

# 2. 启动 PostgreSQL 和 FastAPI 后端
docker compose up -d --build

# 3. 初始化标准会计科目
docker compose exec backend python scripts/init_accounts.py
```

启动成功后访问：

- 接口文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/ping

## 本地开发

如果你不走 Docker 跑 FastAPI，而是在宿主机本地直接启动后端，需要注意 `DATABASE_URL` 的主机名不能写 `postgres`，而要改成宿主机可访问的地址，例如 `localhost`。  
当前根目录 `.env` 里的默认值是给 Docker Compose 容器互联准备的。

## 待对接事项

- [ ] 和 ohao-admin 确认 `ADMIN_TOKEN` 的正式值，并写入 Cloudflare 环境变量
- [ ] 部署到 Railway
- [ ] 在 ohao-admin 的 `projects.ts` 里注册 Fina 模块
- [ ] 根据真实业务场景继续优化 AI Prompt
