# Fina — AI 智能财务系统

> 面向微型企业的 AI 驱动财务管理工具。支持自然语言记账、智能财务分析报告，让老板和会计都能轻松用。

## 项目状态

🚧 开发中

## 核心功能

* **自然语言记账** — 直接输入"付了3000房租"，AI 自动解析生成借贷凭证，用户确认后入账
* **智能财务分析** — 月末自动汇总数据，AI 生成白话版财务分析报告，老板无需懂会计
* **凭证管理** — 凭证录入、查询、审核，借贷平衡强校验
* **科目管理** — 自定义会计科目表，支持多级科目
* **报表生成** — 资产负债表、利润表自动生成
* **应收应付** — 往来单位管理，账期与核销跟踪

## 技术栈

| 层        | 技术                  |
| --------- | --------------------- |
| 后端框架  | FastAPI (Python 3.11) |
| 数据库    | PostgreSQL            |
| ORM       | SQLAlchemy 2.0        |
| 前端框架  | React 18 + Vite       |
| UI 组件库 | Ant Design 5          |
| 全局状态  | Zustand               |
| AI 模型   | DeepSeek API          |
| 部署      | Docker Compose        |

## 项目结构

```
fina/
├── .env                          # API Key、数据库密码等敏感配置
├── docker-compose.yml            # 一键启动 backend + PostgreSQL
├── README.md
│
├── backend/
│   ├── main.py                   # FastAPI 入口，注册路由，配置 CORS
│   ├── requirements.txt.         #pip freeze > requirements.txt venv环境
│   ├── core/
│   │   ├── config.py             # 读取 .env 环境变量
│   │   ├── database.py           # PostgreSQL 连接，Session 管理
│   │   └── security.py          # JWT 生成与校验
│   │
│   ├── models/                   # SQLAlchemy 数据库表定义
│   │   ├── user.py
│   │   ├── account.py            # 会计科目表
│   │   ├── voucher.py            # 凭证表 + 凭证分录表
│   │   ├── receivable.py         # 应收应付表
│   │   └── report.py            # 生成报告存档表
│   │
│   ├── schemas/                  # Pydantic 请求/响应结构
│   │   ├── voucher.py
│   │   ├── account.py
│   │   ├── ai.py                 # 自然语言输入 / 凭证草稿输出
│   │   └── report.py
│   │
│   ├── routers/                  # 接收请求、调 service、返回响应
│   │   ├── auth.py               # 登录 / 注册
│   │   ├── ai.py                 # POST /ai/parse  POST /ai/report
│   │   ├── vouchers.py           # 凭证 CRUD
│   │   ├── accounts.py           # 科目管理
│   │   ├── reports.py            # 报表查询
│   │   └── receivables.py        # 应收应付
│   │
│   └── services/                 # 业务逻辑层
│       ├── ai_service.py         # 调 LLM，拼 Prompt，解析返回 JSON
│       ├── voucher_service.py    # 借贷平衡校验，凭证入库
│       ├── account_service.py    # 科目树管理
│       └── report_service.py    # 汇总数据，触发 AI 生成分析文字
│
└── frontend/
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── main.tsx
        ├── App.tsx               # 路由配置
        ├── api/                  # axios 统一封装
        │   ├── client.ts         # baseURL、拦截器、token 注入
        │   ├── ai.ts
        │   └── vouchers.ts
        ├── store/
        │   └── authStore.ts      # 登录态、用户信息（Zustand）
        ├── hooks/
        │   └── useAI.ts          # 调 AI 接口，处理 loading 状态
        ├── components/
        │   ├── VoucherTable/
        │   └── ReportCard/
        └── pages/
            ├── Dashboard/        # 老板总览仪表盘
            ├── AIVoucher/        # 自然语言记账（核心页面）
            ├── Vouchers/         # 凭证列表 + 手动录入
            ├── Accounts/         # 科目管理
            ├── Reports/          # 财务报告
            └── Receivables/      # 应收应付
```

## 快速启动

### 环境要求

* Docker & Docker Compose
* Node.js 18+
* Python 3.11+

### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/fina.git
cd fina
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入以下内容：
# DEEPSEEK_API_KEY=your_key_here
# DATABASE_URL=postgresql://fina:fina123@localhost:5432/fina
# JWT_SECRET=your_secret_here
```

### 3. 启动后端 + 数据库

```bash
docker-compose up -d
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 5. 访问

| 地址                       | 说明                     |
| -------------------------- | ------------------------ |
| http://localhost:5173      | 前端页面                 |
| http://localhost:8000/docs | 后端接口文档（自动生成） |
| http://localhost:8000/ping | 后端健康检查             |

## 接口概览

| 方法 | 地址         | 说明                 |
| ---- | ------------ | -------------------- |
| POST | /auth/login  | 登录                 |
| POST | /ai/parse    | 自然语言 → 凭证草稿 |
| POST | /ai/report   | 触发生成财务分析报告 |
| GET  | /vouchers    | 凭证列表             |
| POST | /vouchers    | 新增凭证             |
| GET  | /accounts    | 科目列表             |
| GET  | /reports     | 报表查询             |
| GET  | /receivables | 应收应付列表         |

## 开发计划

* [ ] 核心数据库表设计
* [ ] 用户认证（JWT）
* [ ] 科目管理 CRUD
* [ ] 手动凭证录入
* [ ] AI 自然语言记账
* [ ] 报表生成
* [ ] AI 财务分析报告
* [ ] 应收应付管理
* [ ] Docker 部署

## License

MIT
