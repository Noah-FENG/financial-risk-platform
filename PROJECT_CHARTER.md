# Financial Risk Analytics Platform — Project Plan

## 0. Project Definition

**Project:** Financial Risk Analytics Platform  
**Dataset:** LendingClub accepted loans, 2007–2018  
**Version:** V1 — Fall 2026  
**Repository:** `financial-risk-platform`

### 一句话定义

利用 LendingClub 2007–2018 历史贷款数据，模拟一家真实贷款公司的月度数据流，建立一套**可重放、可验证、可重复构建**的数据与风险分析系统，并回答三个核心问题：

1. LendingClub 的贷款风险什么时候开始恶化？
2. 收取的利率有没有充分补偿这些风险？
3. 风险变化是否来自借款人质量和信贷政策的漂移？

最后建立一个基础 Logistic PD 模型，观察模型在未来年份上的表现是否衰减。

---

## 1. Project Positioning

这不是：

- Kaggle 违约预测项目；
- 为展示模型精度而做的 ML 项目；
- 单纯为了展示 dbt / SQL 的 Data Platform；
- 第一学期就堆 Spark、Airflow、Cloud、Docker、LLM 的大而全项目。

它模拟的是：

> 一家真实金融科技公司的 Data / Risk Analytics 团队，如何从原始贷款数据建立可靠的数据系统，并持续监控贷款风险、定价与模型。

项目最终需要同时证明三类能力：

### Data / Analytics Engineering
- 原始数据清洗与标准化
- CSV → Parquet
- 月度 replay
- incremental processing
- idempotency
- DuckDB
- dbt data modeling
- automated tests
- reproducible pipeline

### Financial / Risk Analytics
- Vintage analysis
- Charge-off / default
- Pricing adequacy
- Borrower quality drift
- Credit policy drift

### Data Science
- Logistic PD model
- Temporal / OOT validation
- Calibration
- PSI
- Model decay
- Basic expected-loss thinking

---

# 2. Core Business Story

假设我是 LendingClub 风险数据团队的一名分析师。

公司每个月不断发放新的贷款。我需要持续回答三个业务问题。

## Question 1 — 风险发生了什么？

比较不同年份 / 季度发放的贷款，在相同账龄下的累计坏账表现。

重点看：

- MOB 6
- MOB 12
- MOB 18
- MOB 24
- MOB 36

目标：

> 判断哪些 vintage 的贷款开始明显恶化。

---

## Question 2 — 定价有没有跟上风险？

风险高的贷款通常收取更高利率，但真正的问题是：

> 增加的利率是否足以补偿增加的实际信用损失？

重点比较：

- Grade / Sub-grade
- Vintage
- Interest Rate
- Realized Credit Loss

核心分析：

> 同一个 Grade 在不同时期的利率是否仍然能够覆盖其实现的损失。

这是 V1 最重要的金融分析。

---

## Question 3 — 为什么风险会变化？

如果贷款表现越来越差，需要进一步判断：

- 借款人的 FICO 是否下降
- DTI 是否上升
- 60-month 贷款占比是否上升
- Grade mix 是否改变
- 平均利率是否同步调整
- Loan amount 是否扩张

目标：

> 判断 LendingClub 是否逐渐进入更高风险客户群，而信用等级与利率没有同步调整。

---

# 3. Five-Layer Architecture

## L0 — Data Replay

原始 LendingClub 文件是静态历史快照，但真实公司不会一次性看到未来数据。

因此按照 `issue_d` 把贷款重新切成月度批次，并按时间顺序回放。

例如：

```text
2007-06
2007-07
2007-08
...
2018-12
```

系统运行到 `2015-03` 时，只允许处理 2015-03 及以前可见的数据。

### L0 Deliverables

- `ingest.py`
- raw CSV → normalized Parquet
- monthly batch partition
- replay logic
- idempotency
- backfill capability
- leakage-rule test
- censoring-rule test
- replay test

### Key Principle

> 没有时间轴，后面的 vintage、OOT 和 model decay 都没有意义。

---

# 4. L1 — Analytics Data Model

使用：

- DuckDB
- dbt-duckdb

建立正式 analytics layer。

## Grain

项目最重要的 grain：

> **One row = one loan**

## Core Models

### `dim_borrower`
申请时点的借款人属性：

- annual income
- employment length
- home ownership
- state
- DTI
- FICO
- revolving utilization
- credit history

### `dim_loan`
贷款条款：

- loan amount
- term
- purpose
- grade
- sub-grade
- interest rate
- installment

### `dim_date`
月度日历，用于 vintage 和 loan age。

### `fact_origination`
粒度：一笔贷款一行。  
记录贷款发放时点事实。

### `fact_loan_outcome`
粒度：一笔贷款一行。  
记录：

- terminal outcome
- is_censored
- approximate default age
- realized loss information

## dbt Requirements

核心 mart 必须带测试：

- `unique`
- `not_null`
- `accepted_values`
- `relationships`

---

# 5. L2 — Risk Analytics

L2 是 V1 最重要的业务分析层。

最终只保留三条主线。

## Analysis A — Vintage Analysis

### Main Figure

**Cumulative Charge-off Rate vs Loan Age by Vintage**

比较不同：

- origination year
- origination quarter
- grade

的贷款表现。

### Question

> 哪些 vintage 的贷款开始明显恶化？

---

## Analysis B — Pricing Adequacy

### Main Figure

**Interest Rate vs Realized Credit Loss within Grade**

重点不是简单比较 Grade A 与 Grade G。

而是：

> 同一个 Grade，在不同 vintage 中，收取的利率是否仍然足够覆盖实际损失？

### Question

> LendingClub 的风险定价什么时候开始跟不上实际风险？

这是整个 V1 最重要的一张业务图。

---

## Analysis C — Credit Policy / Borrower Quality Drift

跟踪随时间变化的：

- Grade distribution
- Average interest rate
- Average FICO
- Average DTI
- Loan amount
- 36 / 60 month mix

### Question

> 风险恶化是否伴随着借款人质量或信贷政策的变化？

---

# 6. L3 — Basic PD Model

本学期只做：

> **Logistic Regression V0**

不追求复杂模型，不追求 Kaggle-style AUC。

## Target

```text
Charged Off / Default = 1
Fully Paid = 0
```

## Feature Rule

只允许使用贷款发放时已经可见的信息。

## Two Model Versions

### Model A — Borrower Fundamentals Only

不使用：

- `grade`
- `sub_grade`
- `int_rate`

目的是观察 borrower fundamentals 本身的预测能力。

### Model B — Include LendingClub Risk Outputs

加入：

- `grade`
- `sub_grade`
- `int_rate`

比较 LendingClub 自身风险体系能够提供多少额外信息。

## Validation

最终验证必须采用：

```text
Past data → Train
Future data → Test
```

而不是随机 train/test split。

重点输出：

- AUC
- calibration
- OOT performance
- PSI
- model decay
- population shift
- cost-sensitive threshold
- basic Expected Loss

---

# 7. Critical Data Rules

## 7.1 Data Leakage

贷款发放之后才产生的信息不能进入 PD model features。

例如：

- outstanding principal
- total payment
- total received principal
- total received interest
- recoveries
- collection recovery fee
- last payment date
- last payment amount
- post-origination FICO
- hardship / settlement information

这些字段可以用于结果分析，但不能用于放款时违约预测。

---

## 7.2 Censoring

仍在正常还款中的贷款不能简单视为 non-default。

基本规则：

```text
36-month loan
→ issue_d 距数据快照至少 36 个月

60-month loan
→ issue_d 距数据快照至少 60 个月
```

建模目标仅使用：

```text
Charged Off / Default
vs
Fully Paid
```

未实现的结果排除。

---

# 8. Data Limitation

公开 accepted-loan 数据是一笔贷款一行的终态快照，不是真正的月度 repayment panel。

因此 vintage 中的违约时点只能使用：

- `issue_d`
- `last_pymnt_d`

等字段进行近似。

这一限制必须：

- 写入 README
- 写入图注
- 在面试时主动解释

不能假装拥有不存在的月度还款面板。

---

# 9. V1 Technical Stack

固定使用：

- Python 3.11+
- Pandas
- DuckDB
- Parquet
- SQL
- dbt-duckdb
- scikit-learn
- matplotlib
- pytest
- ruff
- Make
- Git / GitHub

本学期不同时学习 Pandas 与 Polars，固定使用 Pandas。

---

# 10. Repository Structure

```text
financial-risk-platform/
├── README.md
├── Makefile
├── pyproject.toml
├── data/
│   ├── raw/
│   └── batches/
├── src/
│   ├── ingest.py
│   ├── replay.py
│   ├── features.py
│   └── modeling/
│       ├── pd_model.py
│       └── validation.py
├── dbt/
│   └── models/
│       ├── staging/
│       ├── intermediate/
│       └── marts/
├── analysis/
├── reports/
│   └── figures/
└── tests/
```

Notebook 只用于探索。

最终业务逻辑必须回到：

- `src/`
- 或 `dbt/`

---

# 11. Milestones

## Phase 1 — L0 Foundation

### Target
完成可靠的数据入口和 replay。

### Deliverables
- 数据下载与字段审计
- Data Dictionary
- `ingest.py`
- CSV → Parquet
- 月度 replay
- leakage rules
- censoring rules
- pytest
- idempotency

---

## Phase 2 — L1 Data Modeling

### Target
完成正式 analytics layer。

### Deliverables
- dbt staging
- 5–8 个核心 dbt models
- star schema
- dbt tests
- DuckDB analytics database

---

## Phase 3 — L2 Analytics

### Target
完成三条业务分析线。

### Deliverables

#### Figure A
Cumulative Charge-off Rate by Vintage and Loan Age

#### Figure B
Interest Rate vs Realized Credit Loss within Grade

#### Figure C
Credit Policy / Borrower Quality Drift

并形成一段完整业务结论：

```text
风险发生了什么
→ 定价有没有跟上
→ 为什么会发生
```

---

## Phase 4 — L3 PD Model

### Target
完成基础信用风险模型及时间验证。

### Deliverables
- Logistic Regression
- Model A / B
- temporal split
- OOT validation
- AUC
- calibration
- PSI
- model decay
- basic Expected Loss

---

## Phase 5 — Finalization

### Deliverables
- `make all`
- 全链路可重建
- 连续运行两次结果一致
- 全部关键 tests 通过
- README 完成
- 三张主图定稿
- 3–5 分钟项目讲解
- GitHub repo clean-up

---

# 12. Definition of Done

V1 必须同时满足：

1. `make all` 能从原始数据重建整个项目。
2. 重跑两次结果一致。
3. Star schema 完成。
4. 5–8 个 dbt models 全部有必要测试。
5. Figure A / B / C 完成。
6. 三条业务分析线可以讲出明确结论。
7. Logistic PD V0 完成。
8. OOT + calibration + PSI 完成。
9. README 明确写出 leakage、censoring 与数据限制。
10. 项目中的核心代码和设计选择自己能够解释。

---

# 13. Explicit Non-Goals — Fall 2026

本学期不使用：

- Spark
- Airflow
- Dagster
- Azure / AWS
- Docker
- XGBoost
- LightGBM
- SHAP
- Deep Learning
- Dashboard
- Streamlit
- LLM
- RAG
- Agent
- API integration

也不追求：

- Kaggle 排名
- 极致 AUC
- 过度抽象
- 提前为 2027 搭建复杂架构

原则：

> **Correctness > Completeness > Complexity**

---

# 14. Final Project Narrative

项目完成后，应能用 3–5 分钟清楚说明：

> I reconstructed LendingClub's historical originations as a replayable monthly data pipeline and built a tested analytical warehouse on top of it. I then used vintage analysis to identify changes in portfolio performance, examined whether interest-rate pricing adequately compensated for realized credit losses, and analyzed shifts in borrower quality and credit policy over time. Finally, I built a baseline PD model and evaluated how its performance deteriorated out of time.

---

# 15. Future Versions

## Spring 2027
在 V1 稳定后再考虑：

- XGBoost
- SHAP
- stronger Expected Loss modeling
- orchestration
- model monitoring
- cloud engineering

## Fall 2027
根据实习和职业方向二选一：

- Fraud / AML
- AI-assisted Risk Analytics

## Spring 2028
作为 Capstone / Flagship Portfolio 完成最终版本。

原则：

> 新能力尽量接入同一旗舰系统，但只有在当前版本稳定后才能扩展。
