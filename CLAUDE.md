# Fina - AI 财务数字员工

## 项目定位

Fina 是一个面向单一企业长期服务的 AI 财务数字员工。

它的目标不是只做一个“会对话的报表机器人”，而是成为：

- 能理解企业经营背景的财务助手
- 能把自然语言转成财务动作的执行层
- 能沉淀长期业务知识的记忆层
- 能输出正式交付物的报告层

核心原则：**先有可靠的客观财务数据，再让模型从财务视角做总结与建议。**

## 当前架构

```text
Stripe / 外部业务系统 ---> 自动记账层 ---> 凭证 / 集成事件
                                    |
                                    v
外部 AI / 终端输入 -------> AI 工具层 ---> 查询 / 报告 / 导出 / 对话
```

## 关键设计决策

- **单公司模式**
  - 当前不做多租户隔离
  - 所有财务数据、对话和记忆默认都服务同一家公司

- **双数据库设计**
  - 主财务数据库：科目、凭证、应收应付、报告归档
  - 记忆数据库：会话、消息、公司画像、长期记忆

- **两层能力分离**
  - 自动记账层：接 Stripe 等事件，优先规则化、幂等和审计
  - AI 工具层：给外部 AI 调用，负责查询、分析、导出和对话

- **记忆不等于聊天记录**
  - 原始对话完整保留
  - 每轮对话后都做记忆蒸馏
  - 只有真正重要、可复用、稳定的知识才进入长期记忆

- **报告先算后写**
  - 代码先计算客观财务指标
  - 模型再基于这些指标输出财务分析
  - 模型不能编造数字

- **导出是正式工具能力**
  - Excel 导出和 Word 导出是系统内置能力
  - 模型可以决定何时调用
  - 但执行由稳定工具完成，而不是临时脚本

- **模型可配置，不绑定单一供应商**
  - 后端统一走 OpenAI 兼容接口
  - `AI_MODEL` 是默认模型
  - `AI_ALLOWED_MODELS` 可选，用于限制可调用模型范围
  - chat / parse / query / report / export 都可以按请求覆盖 model

- **报告可以带图**
  - 使用 `matplotlib` 生成关键指标图和账龄对比图
  - 图表以 PNG 形式写入 Word 报告
  - 中文字体优先走系统中文字体或 Docker 内安装的 Noto CJK

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI (Python 3.12) |
| 主数据库 | PostgreSQL 15 |
| 记忆数据库 | PostgreSQL 15 |
| ORM | SQLAlchemy 2.0 |
| AI | OpenAI 兼容接口 |
| 图表 | matplotlib |
| Excel 导出 | openpyxl |
| Word 导出 | python-docx |
| 部署 | Docker Compose |

## 目录结构

```text
backend/
├── main.py
├── core/
│   ├── config.py
│   ├── database.py
│   ├── memory_database.py
│   └── auth.py
├── models/
│   ├── account.py
│   ├── accounting_policy.py
│   ├── voucher.py
│   ├── receivable.py
│   ├── integration_event.py
│   ├── report.py
│   ├── memory.py
│   └── conversation.py
├── schemas/
│   ├── chat.py
│   ├── policy.py
│   ├── report.py
│   ├── export.py
│   └── ...
├── routers/
│   ├── chat.py
│   ├── ai.py
│   ├── reports.py
│   ├── exports.py
│   ├── policy.py
│   ├── stripe.py
│   └── ...
└── services/
    ├── accounting/
    ├── agent/
    ├── integrations/
    └── reporting/
```

## 现阶段重点

### 已完成方向

- [x] 基础财务 CRUD
- [x] 自然语言记账草稿
- [x] 统一对话入口
- [x] 双数据库架构
- [x] 长期记忆蒸馏
- [x] AI 财务报告
- [x] Excel 导出
- [x] Word 报告导出
- [x] Stripe webhook 自动记账
- [x] 会计政策与自动记账科目映射
- [x] 基础自动化测试

### 下一阶段建议

- [ ] 完整自动化测试
- [ ] 凭证落库确认流
- [ ] 现金流分析
- [ ] 应收风险预警
- [ ] 更稳的会计口径校验
- [ ] 文件下载与静态访问策略

## 开发约定

- 所有注释、提示词、对外文档统一使用中文
- 变量名、函数名和代码符号继续使用英文
- 业务逻辑放在 service，router 保持薄层
- 所有金额统一使用 `Numeric(10, 2)` / `Decimal`
- 模型输出如果要参与程序流程，必须转成严格 JSON
- 不能把模型输出直接当成可信财务事实，必须有后端校验
- 如果配置了 `AI_ALLOWED_MODELS`，新增模型时要同步更新 `.env.example` 和 README
- Stripe 自动记账必须优先走幂等控制和会计政策映射，不能直接依赖聊天式推断
