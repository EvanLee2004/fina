# Fina 项目总结

## 项目背景

Fina 是 ohao 平台的 AI 智能财务管理后端模块，服务于 ohao 团队内部财务管理需求。管理员通过 ohao-admin 看板操作，AI Bot 自动调用接口记录财务数据，普通用户可通过对话形式查询财务记录。

---

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI (Python 3.12) |
| 数据库 | PostgreSQL 15 |
| ORM | SQLAlchemy 2.0 |
| 数据校验 | Pydantic v2 |
| AI 模型 | DeepSeek API |
| 认证 | X-Admin-Token |
| 部署 | Docker Compose |

---

## 项目结构

```text
fina/
├── .env                          # 敏感配置（不进 Git）
├── docker-compose.yml            # 一键启动 PostgreSQL
├── README.md
└── backend/
    ├── main.py                   # FastAPI 入口，注册路由，启动建表
    ├── requirements.txt          # Python 依赖
    ├── core/
    │   ├── config.py             # 读取 .env 环境变量
    │   ├── database.py           # PostgreSQL 连接，Session 管理
    │   ├── security.py           # JWT 工具（备用）
    │   └── auth.py               # X-Admin-Token 验证依赖
    ├── models/                   # SQLAlchemy 数据库表定义
    │   ├── account.py            # 会计科目表
    │   ├── voucher.py            # 凭证表 + 凭证分录表
    │   ├── receivable.py         # 应收应付表
    │   └── report.py             # AI 报告存档表
    ├── schemas/                  # Pydantic 请求/响应结构
    │   ├── account.py
    │   ├── voucher.py
    │   ├── ai.py
    │   ├── receivable.py
    │   └── report.py
    ├── routers/                  # API 路由层
    │   ├── accounts.py
    │   ├── vouchers.py
    │   ├── ai.py
    │   ├── reports.py
    │   └── receivables.py
    ├── services/                 # 业务逻辑层
    │   ├── account_service.py
    │   ├── voucher_service.py
    │   ├── ai_service.py
    │   ├── receivable_service.py
    │   └── report_service.py
    └── scripts/
        └── init_accounts.py      # 初始化标准会计科目
```

---

## 数据库设计

共 5 张表：

| 表名 | 说明 |
|---|---|
| accounts | 会计科目表，含18条标准科目 |
| vouchers | 凭证主表 |
| voucher_entries | 凭证分录表（一对多） |
| receivables | 应收应付表 |
| reports | AI 财务分析报告存档 |

---

## API 接口总览

所有接口前缀：`/api/admin/`  
认证方式：请求头 `X-Admin-Token: <token>`

### 科目管理

| 方法 | 地址 | 说明 |
|---|---|---|
| GET | /api/admin/accounts/ | 获取科目列表 |
| GET | /api/admin/accounts/tree | 获取科目树 |
| POST | /api/admin/accounts/ | 新增科目 |
| PATCH | /api/admin/accounts/{id} | 更新科目 |
| DELETE | /api/admin/accounts/{id} | 软删除科目 |

### 凭证管理

| 方法 | 地址 | 说明 |
|---|---|---|
| GET | /api/admin/vouchers/ | 凭证列表（支持日期筛选） |
| GET | /api/admin/vouchers/{id} | 获取单条凭证 |
| POST | /api/admin/vouchers/ | 新增凭证（含借贷平衡校验） |
| PATCH | /api/admin/vouchers/{id}/approve | 审核凭证 |
| DELETE | /api/admin/vouchers/{id} | 删除草稿凭证 |

### AI 接口

| 方法 | 地址 | 说明 |
|---|---|---|
| POST | /api/admin/ai/parse | 自然语言 → 凭证草稿 |
| POST | /api/admin/ai/report | 生成 AI 财务分析报告 |
| POST | /api/admin/ai/query | 自然语言查询财务数据 |

### 应收应付

| 方法 | 地址 | 说明 |
|---|---|---|
| GET | /api/admin/receivables/ | 列表（支持类型和状态筛选） |
| POST | /api/admin/receivables/ | 新增记录 |
| PATCH | /api/admin/receivables/{id}/settle | 标记已结清 |

### 报表

| 方法 | 地址 | 说明 |
|---|---|---|
| GET | /api/admin/reports/ | 报告列表 |
| GET | /api/admin/reports/{period} | 获取指定月份报告 |

---

## 核心功能说明

### 自然语言记账

用户输入"今天付了3000块房租"，系统自动：

1. 查出所有会计科目，注入 Prompt
2. 调用 DeepSeek API 解析意图
3. 返回结构化凭证草稿（含借贷科目和金额）
4. 校验借贷平衡
5. 用户确认后调凭证接口入库

### 借贷平衡校验

创建凭证时强制校验：借方总额 = 贷方总额，不平衡返回 400 错误。已审核凭证不可删除、不可重复审核。

### AI 财务分析报告

指定月份后，系统自动：

1. 汇总该月已审核凭证数据
2. 计算总收入、总支出、净利润
3. 调 DeepSeek 生成白话版分析报告
4. 存入 reports 表备查

---

## 快速启动

```bash
# 1. 启动数据库
docker compose up -d

# 2. 激活虚拟环境
source .venv/bin/activate

# 3. 安装依赖
pip install -r backend/requirements.txt

# 4. 初始化标准科目
python backend/scripts/init_accounts.py

# 5. 启动服务
cd backend
uvicorn main:app --reload
```

访问：

- 接口文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/ping

---

## 待对接事项

- [ ] 和 ohao-admin 确认 ADMIN_TOKEN 的值，写入 Cloudflare 环境变量
- [ ] 部署到 Railway（和 MoGen3D、Fluxa 同一平台）
- [ ] 在 ohao-admin 的 projects.ts 里注册 Fina 模块
- [ ] AI query 接口根据实际使用场景调整 Prompt

---
