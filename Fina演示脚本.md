
# Fina 后端功能演示文档

> 从零开始，完整演示所有功能
> 服务地址：`http://localhost:8000`
> 认证：所有接口带 Header `X-Admin-Token: fina-admin-secret-2024`

---

## 一、环境准备

### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/fina.git
cd fina
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入：

```
DATABASE_URL=postgresql://fina:fina123@postgres:5432/fina
JWT_SECRET=change-this-to-a-strong-secret
DEEPSEEK_API_KEY=你的DeepSeek API Key
ADMIN_TOKEN=fina-admin-secret-2024
AI_API_KEY=你的DeepSeek API Key
```

### 3. 启动 Docker

```bash
docker compose up -d --build
```

等待约 30 秒，确认两个容器都在跑：

```bash
docker compose ps
```

应看到 `fina-backend` 和 `fina-postgres` 都是 `Up` 状态。

### 4. 初始化标准会计科目

```bash
docker compose exec backend python scripts/init_accounts.py
```

应看到 66 条科目插入成功。

---

## 二、功能演示

### 第一步：健康检查

```bash
curl http://localhost:8000/ping
```

预期返回：

```json
{"message": "pong"}
```

---

### 第二步：查看接口文档

浏览器打开：

```
http://localhost:8000/docs
```

展示所有 18 个接口的完整文档。

---

### 第三步：查看标准会计科目表

```bash
curl http://localhost:8000/api/admin/accounts/ \
  -H "X-Admin-Token: fina-admin-secret-2024"
```

预期返回：66 条标准科目，涵盖资产、负债、权益、收入、成本、费用六大类，符合财政部《小企业会计准则》。

---

### 第四步：AI 自然语言记账（核心功能）

输入一句自然语言，AI 自动解析成借贷凭证草稿：

```bash
curl -X POST http://localhost:8000/api/admin/ai/parse \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: fina-admin-secret-2024" \
  -d '{"text": "今天付了8000块员工工资"}'
```

预期返回：AI 自动识别科目和金额，生成借贷平衡的凭证草稿， **不入库，等用户确认** 。

---

### 第五步：借贷平衡校验（演示保护机制）

故意输入借贷不平衡的凭证：

```bash
curl -X POST http://localhost:8000/api/admin/vouchers/ \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: fina-admin-secret-2024" \
  -d '{
    "date": "2026-03-21",
    "memo": "测试不平衡",
    "entries": [
      {"account_id": 17, "debit": 5000, "credit": 0},
      {"account_id": 2, "debit": 0, "credit": 3000}
    ]
  }'
```

预期返回 400：

```json
{"detail": "借贷不平衡：所有分录借方总额必须等于贷方总额。"}
```

---

### 第六步：创建三笔正式凭证

**凭证1：支付房租**

```bash
curl -X POST http://localhost:8000/api/admin/vouchers/ \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: fina-admin-secret-2024" \
  -d '{
    "date": "2026-03-05",
    "memo": "支付3月房租",
    "entries": [
      {"account_id": 17, "debit": 6000, "credit": 0},
      {"account_id": 2, "debit": 0, "credit": 6000}
    ]
  }'
```

**凭证2：支付员工工资**

```bash
curl -X POST http://localhost:8000/api/admin/vouchers/ \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: fina-admin-secret-2024" \
  -d '{
    "date": "2026-03-10",
    "memo": "支付员工工资",
    "entries": [
      {"account_id": 7, "debit": 20000, "credit": 0},
      {"account_id": 2, "debit": 0, "credit": 20000}
    ]
  }'
```

**凭证3：收到客户货款**

```bash
curl -X POST http://localhost:8000/api/admin/vouchers/ \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: fina-admin-secret-2024" \
  -d '{
    "date": "2026-03-15",
    "memo": "收到客户货款",
    "entries": [
      {"account_id": 2, "debit": 50000, "credit": 0},
      {"account_id": 13, "debit": 0, "credit": 50000}
    ]
  }'
```

---

### 第七步：查看凭证列表，记下 id

```bash
curl http://localhost:8000/api/admin/vouchers/ \
  -H "X-Admin-Token: fina-admin-secret-2024"
```

预期返回：3张草稿凭证， **记下 id** ，下一步要用。

---

### 第八步：审核凭证（id 换成上一步查到的真实值）

```bash
curl -X PATCH http://localhost:8000/api/admin/vouchers/1/approve \
  -H "X-Admin-Token: fina-admin-secret-2024"

curl -X PATCH http://localhost:8000/api/admin/vouchers/2/approve \
  -H "X-Admin-Token: fina-admin-secret-2024"

curl -X PATCH http://localhost:8000/api/admin/vouchers/3/approve \
  -H "X-Admin-Token: fina-admin-secret-2024"
```

预期返回：status 从 `draft` 变成 `approved`。

**演示重复审核被拒绝：**

```bash
curl -X PATCH http://localhost:8000/api/admin/vouchers/1/approve \
  -H "X-Admin-Token: fina-admin-secret-2024"
```

预期返回 400：

```json
{"detail": "凭证已审核，不可重复审核。"}
```

---

### 第九步：应收应付管理

新增一笔应付账款：

```bash
curl -X POST http://localhost:8000/api/admin/receivables/ \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: fina-admin-secret-2024" \
  -d '{
    "type": "payable",
    "party": "北京供应商有限公司",
    "amount": 15000,
    "due_date": "2026-04-30",
    "memo": "3月采购货款"
  }'
```

标记已结清：

```bash
curl -X PATCH http://localhost:8000/api/admin/receivables/1/settle \
  -H "X-Admin-Token: fina-admin-secret-2024"
```

预期返回：status 从 `pending` 变成 `settled`。

---

### 第十步：AI 财务分析报告（核心功能）

基于已审核凭证，AI 自动生成白话版财务分析报告：

```bash
curl -X POST http://localhost:8000/api/admin/ai/report \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: fina-admin-secret-2024" \
  -d '{"period": "2026-03"}'
```

预期返回：AI 汇总本月收入50000、支出26000、净利润24000，生成中文分析报告并存档。

---

## 三、演示结束后重置数据

保留科目，清空业务数据：

```bash
docker compose exec postgres psql -U fina -d fina -c "DELETE FROM voucher_entries;"
docker compose exec postgres psql -U fina -d fina -c "DELETE FROM vouchers;"
docker compose exec postgres psql -U fina -d fina -c "DELETE FROM reports;"
docker compose exec postgres psql -U fina -d fina -c "DELETE FROM receivables;"
```

---

## 四、功能亮点总结

| 功能               | 亮点                             |
| ------------------ | -------------------------------- |
| AI 自然语言记账    | 说人话生成借贷凭证，不需要懂会计 |
| 借贷平衡强校验     | 系统层面拦截错误数据             |
| 凭证状态管理       | 草稿→审核，审核后锁定           |
| AI 财务分析报告    | 自动汇总生成白话分析             |
| 应收应付管理       | 往来账款跟踪，一键结清           |
| 66条标准科目       | 符合财政部《小企业会计准则》     |
| X-Admin-Token 认证 | 接入 ohao 平台统一认证           |
| 完全容器化         | Docker 一键启动，随时部署        |
