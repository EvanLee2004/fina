# Fina — AI 财务管理后端

ohao 平台的财务管理模块，为 ohao-admin 提供财务数据 API。

## 定位

- ohao 平台内部财务模块，非独立产品
- 管理员通过 ohao-admin 看板操作
- AI Bot 自动调用接口记录财务数据
- 用户可通过对话形式查询自己的财务记录

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI (Python 3.11) |
| 数据库 | PostgreSQL 15 |
| ORM | SQLAlchemy 2.0 |
| 认证 | X-Admin-Token（ohao 平台统一管理） |
| AI | DeepSeek API |
| 部署 | Docker（独立容器） |

## 认证方式

所有请求需要在 Header 里带：
X-Admin-Token: <token>

token 由 ohao 平台统一管理，存在 Cloudflare 环境变量里。

## 核心接口

| 方法 | 地址 | 说明 |
|---|---|---|
| POST | /ai/parse | 自然语言 → 凭证草稿 |
| POST | /ai/report | 生成财务分析报告 |
| POST | /ai/query | 自然语言查询财务数据 |
| GET | /vouchers | 凭证列表 |
| POST | /vouchers | 新增凭证 |
| GET | /accounts | 科目列表 |
| GET | /reports | 报表查询 |
| GET | /receivables | 应收应付列表 |

## 快速启动

cp .env.example .env
编辑 .env 填入配置

docker-compose up -d

后端跑在 localhost:8000
接口文档：localhost:8000/docs

## 项目结构

backend/
├── main.py
├── core/
│   ├── config.py
│   ├── database.py
│   ├── security.py
│   └── auth.py（X-Admin-Token 验证）
├── models/
├── schemas/
├── routers/
└── services/

## 开发计划

- [x] 数据库表设计
- [ ] X-Admin-Token 验证中间件
- [ ] 科目管理接口
- [ ] 凭证管理接口
- [ ] AI 自然语言记账
- [ ] 报表生成
- [ ] AI 财务分析报告
- [ ] 应收应付管理
- [ ] 部署到 Railway
