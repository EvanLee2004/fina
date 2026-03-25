# Fina - AI 财务数字员工

面向单一企业长期服务的 AI 财务数字员工。
它不只是“会聊天”的程序，而是一个能结合公司背景、财务数据和长期记忆持续工作的财务助手。

## 当前能力

- **统一对话入口**：通过 `POST /api/agent/chat` 和 Fina 交互
- **自然语言记账**：把中文业务描述解析成凭证草稿
- **长期记忆蒸馏**：每轮对话后自动提炼高价值知识，过滤废话和无用信息
- **财务报告**：先由代码计算客观数据，再由模型从财务视角做分析
- **报告图表**：使用 `matplotlib` 自动生成带中文标题的财务图表，并嵌入 Word 报告
- **Excel 导出**：导出财务汇总、凭证、分录、应收应付和 AI 报告
- **Word 报告导出**：导出正式的 `.docx` 财务报告
- **双数据库架构**：财务主库和记忆库分离

## 架构说明

Fina 当前是 **单公司模式**，不再做多租户隔离。

现在按两层能力工作：

- **自动记账层**
  - 接收 Stripe webhook 等外部业务事件
  - 做幂等校验、事件入库、规则化记账草稿生成
  - 这一层优先追求稳定和可追溯，不依赖外部 AI 对话
- **AI 工具层**
  - 给外部 AI 调用的财务能力接口
  - 支持查询财务数据、生成报告、导出 Excel / Word、发起对话
  - AI 在你的项目外部，你的项目负责提供可靠工具

系统拆成两类数据库：

- **主财务数据库**
  - 会计科目
  - 凭证与分录
  - 应收应付
  - 报告归档
- **记忆数据库**
  - 对话会话
  - 对话消息
  - 公司画像记忆
  - 长期记忆

记忆系统采用两层设计：

- **公司画像记忆**
  - 稳定、基础、每次都要带入上下文的信息
  - 例如主营业务、经营模式、重要内部口径
- **长期记忆**
  - 从对话中提炼出的可复用知识
  - 例如客户回款周期、费用规律、供应商结算习惯

原始聊天记录不会直接等于长期记忆。
每次对话结束后，系统都会对最近对话做一次记忆蒸馏，只保留真正重要的知识。

## 快速开始

### 1. 配置环境变量

```bash
cp .env.example .env
```

需要重点确认这些变量：

- `DATABASE_URL`
- `MEMORY_DATABASE_URL`
- `AI_API_KEY`
- `AI_BASE_URL`
- `AI_MODEL`，这里必须填模型名，例如 `deepseek-chat`，不要误填成 API Key
- `AI_ALLOWED_MODELS`，可选，用英文逗号配置允许调用的模型列表
- `ADMIN_TOKEN`
- `JWT_SECRET`
- `STRIPE_WEBHOOK_SECRET`
- `EXPORTS_DIR`

### 2. 启动服务

```bash
docker compose up -d --build
```

当前 `docker-compose.yml` 会启动：

- `backend`
- `postgres` 主财务数据库
- `memory_postgres` 独立记忆数据库

后端镜像会额外安装中文字体包，用于保证 Docker 环境里生成的 `matplotlib` 中文图表不乱码。

### 3. 初始化会计科目

```bash
docker compose exec backend python scripts/init_accounts.py
```

### 4. 终端直接对话

```bash
PYTHONPATH=backend ./.venv/bin/python backend/scripts/chat_cli.py
```

## 核心接口

### 1. 统一对话入口

```bash
POST /api/agent/chat
```

请求体：

```json
{
  "session_id": "s_demo_001",
  "message": "把本月财务情况整理一下并导出 Excel",
  "model": "gpt-4o-mini"
}
```

返回示例：

```json
{
  "reply": "本月财务报告已经生成，Excel 文件也已准备好。",
  "session_id": "s_demo_001",
  "actions": [
    {"type": "report_generated", "detail": {"period": "2026-03"}},
    {"type": "excel_exported", "detail": {"file_type": "xlsx", "filename": "fina-report-2026-03.xlsx", "path": "/app/exports/fina-report-2026-03.xlsx"}}
  ],
  "memories_used": [
    "[公司画像] 主营业务: 主要从事电子配件贸易"
  ]
}
```

### 2. 财务报告

```bash
GET /api/admin/reports/{period}
POST /api/admin/ai/report
```

报告返回内容包含：

- 关键指标卡片
- 客观财务汇总
- AI 财务概览
- 风险与异常
- 建议动作

### 3. 导出交付物

```bash
POST /api/admin/exports/excel
POST /api/admin/exports/word
POST /api/admin/exports/all
```

请求体：

```json
{
  "period": "2026-03"
}
```

### 4. 管理接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/admin/accounts/` | 科目列表 |
| POST | `/api/admin/vouchers/` | 创建凭证 |
| GET | `/api/admin/receivables/` | 应收应付列表 |
| GET | `/api/admin/reports/{period}` | 财务报告 |
| GET/PUT | `/api/admin/policy/` | 公司会计政策与 Stripe 自动记账映射 |
| POST | `/api/admin/exports/all` | 同时导出 Excel 和 Word |

### 5. Stripe 自动记账入口

```bash
POST /api/integrations/stripe/webhook
```

当前设计：

- 只对 `payment_intent.succeeded` 做自动记账
- 先做 Stripe 签名校验
- 再按 `event_id` 做幂等去重
- 根据公司会计政策中的 `Stripe 借方/贷方科目映射` 直接生成凭证
- 如果 `require_manual_confirmation=true`，自动生成的凭证会保持 `draft`

完整接口文档：`http://localhost:8000/docs`

## 导出内容

### Excel

导出的 `.xlsx` 默认包含这些工作表：

- `Summary`
- `Vouchers`
- `VoucherEntries`
- `Receivables`
- `AI_Report`

### Word

导出的 `.docx` 默认包含这些章节：

- 关键指标
- 客观财务数据
- 图表概览
- 财务概览
- 财务分析
- 风险与异常
- 建议动作

## 环境变量

| 变量 | 说明 |
|---|---|
| `DATABASE_URL` | 主财务数据库连接地址 |
| `MEMORY_DATABASE_URL` | 记忆数据库连接地址 |
| `AI_API_KEY` | AI 服务密钥 |
| `AI_BASE_URL` | OpenAI 兼容接口地址 |
| `AI_MODEL` | 默认模型名称 |
| `AI_ALLOWED_MODELS` | 可选模型白名单，英文逗号分隔 |
| `ADMIN_TOKEN` | 管理接口令牌 |
| `JWT_SECRET` | JWT 密钥 |
| `STRIPE_API_KEY` | Stripe 服务端密钥 |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook 签名密钥 |
| `EXPORTS_DIR` | 导出文件目录 |

## 模型调用

Fina 不再固定死在单一模型上。当前设计是：

- `AI_MODEL` 负责设置默认模型
- `AI_ALLOWED_MODELS` 可选，用于限制允许调用的模型范围
- `POST /api/agent/chat`
- `POST /api/admin/ai/parse`
- `POST /api/admin/ai/report`
- `POST /api/admin/ai/query`
- `POST /api/admin/exports/excel`
- `POST /api/admin/exports/word`
- `POST /api/admin/exports/all`

以上接口都支持额外传一个可选字段：

```json
{
  "model": "gpt-4o-mini"
}
```

另外可以通过下面的接口查看当前默认模型、白名单和常见示例模型：

```bash
GET /api/admin/ai/models
```

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI (Python 3.12) |
| 主数据存储 | PostgreSQL 15 |
| 记忆数据存储 | PostgreSQL 15 |
| ORM | SQLAlchemy 2.0 |
| AI | OpenAI 兼容 API |
| 图表 | matplotlib |
| Excel 导出 | openpyxl |
| Word 导出 | python-docx |
| 支付事件接入 | Stripe Webhooks |
| 部署 | Docker Compose |
