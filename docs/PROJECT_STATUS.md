# 项目状态记录

**更新日期：** 2026-09-30

**当前阶段：** Phase 3 — L2 Risk Analytics 准备开始

**最近完成阶段：** Phase 2 — L1 Analytics Data Model

**总纲：** 以根目录 `PROJECT_CHARTER.md` 为项目目标、阶段和验收标准的主要依据。

## 当前结论

Phase 1 和 Phase 2 已完成并有验收证据。当前还没有 Phase 3 的风险分析结果，也没有形成 Figure A、B、C。下一步先固定三个业务问题的指标口径，再建立风险分析 mart 和图表。

2026-09-30 为 GitHub 发布重新执行了可公开复核的检查：`uv run pytest -q` 为 7 passed，Ruff 格式与静态检查通过，`uv run dbt build --project-dir dbt --profiles-dir dbt` 为 6 个 view models 和 39 项 data tests 全部通过（`PASS=45 WARN=0 ERROR=0 SKIP=0`）。本次未重跑会生成大体积本地数据的 ingestion 和 replay；其历史审计输出仍保留在 `outcomes/`。

| 阶段 | 状态 | 已验证结果 / 下一交付物 |
|---|---|---|
| Phase 1 — L0 Foundation | 已完成 | 标准化 Parquet、139 个月度分区、cutoff replay、L0 测试 |
| Phase 2 — L1 Data Modeling | 已完成并验证 | 6 个 dbt view models、39 项 data tests；`PASS=45` |
| Phase 3 — L2 Risk Analytics | 准备开始 | Metric Contract、3 个分析 mart、Figure A/B/C |
| Phase 4 — L3 PD Model | 未开始 | Logistic PD V0、temporal/OOT validation、calibration、PSI |
| Phase 5 — Finalization | 未开始 | `make all`、重复构建、README 定稿、项目讲解 |

## Phase 1 — L0 Foundation

### 数据理解与清洗

- 已完成 43 个核心原始字段的数据字典和可用时点分类。
- 原始 CSV 保持不变。
- 2,260,701 条原始记录中移除 33 条 footer，保留 2,260,668 笔有效贷款。
- 有效贷款 ID 唯一，`issue_d` 完整，期限均为 36 或 60 个月。
- 数据异常保留原始值，并通过单独 flag 标记。

### Ingestion 与月度分区

- `src/ingest.py` 完成 CSV 到标准化 Parquet 的正式流程。
- 标准化输出：`data/processed/accepted_loans_normalized.parquet`。
- 清洗审计：`outcomes/cleaning_audit.csv`。
- 已建立 139 个 `issue_month` 分区，覆盖 `2007-06` 至 `2018-12`。
- 分区总行数为 2,260,668；历史验收确认无重复贷款 ID、混入月份或源数据 ID 差异。

分区形式：

```text
data/batches/issue_month=YYYY-MM/loans.parquet
```

### Replay 与 L0 测试

- `src/replay.py` 支持按开始月份和截止月份顺序回放。
- `outcomes/replay_audit.csv` 当前包含 139 个月，最终累计贷款数为 2,260,668。
- replay 测试覆盖月度审计、cutoff 不读取未来批次和重复运行一致性。
- 当前测试目录共包含 7 个 pytest 测试函数。
- README 中最近记录的 L0 验收结果为 `7 passed` 和 Ruff passed；本次文档更新没有重新运行测试。

## Phase 2 — L1 Analytics Data Model

### 已建立的 dbt 模型

所有模型当前 materialized 为 DuckDB view，分析数据库为 `data/analytics.duckdb`。

| 模型 | 类型 | Grain | 作用 |
|---|---|---|---|
| `stg_loans` | staging | 一笔贷款一行 | 标准化 Parquet 的统一分析入口 |
| `dim_loan` | dimension | 一笔贷款一行 | 金额、期限、利率、Grade、用途 |
| `dim_borrower` | dimension | 一笔贷款申请一行 | 放款时借款人画像；不是一人一行 borrower master |
| `dim_date` | dimension | 一个实际发放月份一行 | 年、月、季度和 vintage 标签 |
| `fact_origination` | fact | 一笔贷款发放一行 | 发放日期和发放月份 |
| `fact_loan_outcome` | fact | 一笔贷款一行 | 终态、成熟度、censoring、近似违约年龄和损失 |

### 验收证据

2026-09-30 的完整 `dbt build` 结果：

```text
Finished running 39 data tests, 6 view models
Done. PASS=45 WARN=0 ERROR=0 SKIP=0 TOTAL=45
```

测试覆盖：

- `not_null`
- `unique`
- `accepted_values`
- `relationships`

该结果证明当前 6 个模型在当前 DuckDB、Parquet 和 dbt 配置下成功构建，39 项已定义规则全部通过。它不代表尚未建立的 Phase 3 业务指标已经得到验证。

## Phase 3 — 当前入口

Phase 3 将回答三条相互衔接的业务问题：

1. 哪些 vintage 在相同 MOB 下开始表现恶化？
2. 同一 Grade、同一期限内，利率调整是否跟上实现信用损失的变化？
3. 风险恶化是否伴随借款人画像或已发放贷款组合变化？

三个问题需要不同的样本规则，不能共用一个万能过滤器：

| 分析 | 样本原则 | 计划 Grain |
|---|---|---|
| Vintage performance | 每个 MOB 下观察期足够的贷款 | `vintage × MOB × grade × term` |
| Grade pricing | 成熟、终态且同 Grade / term 的贷款 | `vintage × grade × term` |
| Borrower / policy drift | 全部有效 originations | `issue_quarter`，并做 Grade / term 分层 |

### 第一项工作：Metric Contract

在写 Phase 3 SQL 前，先固定：

- vintage 使用季度还是年度；
- MOB 从 0 还是 1 开始；
- Default / Charged Off 的事件定义；
- MOB-specific observability 和 censoring 规则；
- 每个指标的分子、分母和权重；
- “明显恶化”的基准、阈值、连续季度数和最低样本量；
- 36 / 60 month、Grade / Sub-grade 的分层方式；
- realized loss 与 pricing compensation 的解释边界。

### 计划交付物

```text
mart_vintage_performance
→ Figure A: Cumulative Default / Charge-off Rate by Vintage and MOB

mart_grade_pricing
→ Figure B: Interest Rate and Realized Credit Loss within Grade

mart_policy_drift
→ Figure C: Borrower Quality and Origination Mix Drift
```

目前这些 mart 和图尚未建立，项目也尚未得出风险何时恶化、定价是否跟上或政策为何变化的真实结论。

## 必须保留的数据边界

- accepted-loan 数据是一笔贷款一行的静态快照，不是月度 repayment panel。
- L0 replay 复原发放顺序，不会让最终状态、付款或 recoveries 在历史 cutoff 当时可见。
- 源文件没有明确快照日期；`fact_loan_outcome` 暂用 `2019-03-01` 作为假设快照月份。
- `last_pymnt_d` 只能近似违约年龄，不是真实 charge-off 日期。
- `realized_net_principal_loss` 是净本金短缺指标，不代表净利润或完整投资回报。
- accepted loans 只能观察已放款组合变化，不能单独证明审批政策改变或因果关系。
- 放款后信息可以用于结果分析，但不能进入放款时 PD features。

## 版本控制状态

截至本次更新，工作区存在尚未提交的用户修改，`dbt/` 目录也尚未被 Git 跟踪。Phase 2 已有运行和测试证据，但还没有形成新的 Git checkpoint。提交前应单独复核差异、忽略规则和生成物范围。

## 下一里程碑完成标准

Phase 3 的第一个里程碑不是完成 Figure A，而是完成并讲清楚 Metric Contract。完成标准是：

1. 能用一个小型假数据集手算三个问题的分子和分母；
2. 明确三个问题各自的样本和 grain；
3. 明确哪些结论是描述性证据、哪些结论当前数据不能支持；
4. 定义获得用户确认后，再实现第一张 `mart_vintage_performance`。
