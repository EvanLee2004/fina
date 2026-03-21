# Fina — AI 财务管理后端

Fina 是 ohao 平台内部的财务管理后端服务，为 `ohao-admin` 和 AI Bot 提供统一的财务数据 API。

## 当前状态

- 已完成 PostgreSQL 连接与 Docker 数据库启动
- 已完成核心数据表：科目、凭证、应收应付、报告
- 已完成基础 Schema、Router、Service 分层
- 已接入 `X-Admin-Token` 鉴权
- 已接入 AI 能力：
  - 自然语言转凭证草稿
  - 财务分析报告生成
  - 自然语言财务查询

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI |
| Python | 3.11+ |
| 数据库 | PostgreSQL 15 |
| ORM | SQLAlchemy 2.0 |
| 数据校验 | Pydantic v2 |
| HTTP 客户端 | httpx |
| 认证 | X-Admin-Token |
| AI 模型 | 智谱 GLM-4.7-Flash |
| 部署 | Docker + 本地 Uvicorn |

## 认证方式

除以下路径外，所有接口都需要在请求头中携带：

- `/ping`
- `/docs`
- `/openapi.json`

请求头格式：

```http
X-Admin-Token: <token>
```

当前本地开发环境中，token 从 `.env` 的 `ADMIN_TOKEN` 读取。

## 项目结构

```text
backend/
├── main.py
├── core/
│   ├── auth.py
│   ├── config.py
│   ├── database.py
│   └── security.py
├── models/
│   ├── account.py
│   ├── receivable.py
│   ├── report.py
│   └── voucher.py
├── schemas/
│   ├── account.py
│   ├── ai.py
│   ├── receivable.py
│   ├── report.py
│   └── voucher.py
├── routers/
│   ├── accounts.py
│   ├── ai.py
│   ├── receivables.py
│   ├── reports.py
│   └── vouchers.py
├── scripts/
│   └── init_accounts.py
└── services/
    ├── account_service.py
    ├── ai_service.py
    ├── receivable_service.py
    ├── report_service.py
    └── voucher_service.py
```

## 已实现接口

所有业务接口统一挂在 `/api/admin` 前缀下。

### 科目管理

- `GET /api/admin/accounts`
- `GET /api/admin/accounts/tree`
- `POST /api/admin/accounts`
- `PATCH /api/admin/accounts/{account_id}`
- `DELETE /api/admin/accounts/{account_id}`

### 凭证管理

- `GET /api/admin/vouchers`
- `GET /api/admin/vouchers/{voucher_id}`
- `POST /api/admin/vouchers`
- `PATCH /api/admin/vouchers/{voucher_id}/approve`
- `DELETE /api/admin/vouchers/{voucher_id}`

### AI 接口

- `POST /api/admin/ai/parse`
- `POST /api/admin/ai/report`
- `POST /api/admin/ai/query`

### 报表

- `GET /api/admin/reports`
- `GET /api/admin/reports/{period}`

### 应收应付

- `GET /api/admin/receivables`
- `POST /api/admin/receivables`
- `PATCH /api/admin/receivables/{receivable_id}/settle`

## 快速启动

### 1. 启动 PostgreSQL

```bash
docker compose up -d
```

### 2. 安装后端依赖

```bash
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 3. 启动后端服务

```bash
cd backend
uvicorn main:app --reload
```

启动后默认访问：

- 接口文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/ping`

## 环境变量

项目当前使用的核心环境变量：

```env
DATABASE_URL=postgresql://fina:fina123@localhost:5432/fina
DEEPSEEK_API_KEY=your_api_key
ADMIN_TOKEN=your_admin_token
```

说明：

- `DEEPSEEK_API_KEY` 这个字段名目前保留不变，但实际用于调用智谱 GLM 接口
- `JWT_SECRET` 目前仍保留在配置中，但当前架构下不参与主认证流程

## 初始化标准会计科目

项目内置了标准会计科目初始化脚本，会自动跳过已存在科目：

```bash
python backend/scripts/init_accounts.py
```

会插入以下常用科目：

- 资产类：库存现金、银行存款、应收账款、预付账款、库存商品
- 负债类：应付账款、应付职工薪酬、应交税费、预收账款
- 所有者权益类：实收资本、资本公积、本年利润
- 收入类：主营业务收入、其他业务收入
- 成本类：主营业务成本
- 费用类：销售费用、管理费用、财务费用

## AI 接口示例

### 生成财务分析报告

请求：

```bash
curl -X POST "http://127.0.0.1:8000/api/admin/ai/report" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: your_admin_token" \
  -d '{"period":"2026-03"}'
```

### 自然语言转凭证草稿

请求：

```bash
curl -X POST "http://127.0.0.1:8000/api/admin/ai/parse" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: your_admin_token" \
  -d '{"text":"支付3月份办公室房租3000元，银行转账"}'
```

## 当前限制

- AI 生成的凭证草稿目前只做解析和借贷校验，不自动入库
- 凭证创建时 `created_by` 仍使用占位值，后续需要接入外部管理员身份
- `reports` 相关接口已可查询，但完整报表域模型和更多报表类型还未扩展

## 下一步建议

- 接入真实管理员身份解析，替换 `created_by` 占位值
- 为 AI 查询补更细的语义解析和更多统计口径
- 为新增、修改、审核接口补测试
- 增加 Alembic 管理数据库迁移
