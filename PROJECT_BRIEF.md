# Financial Analytics & Risk Platform — 项目说明书

> 这份文档是给 AI coding agent（Codex）和我自己看的唯一事实来源。
> 开工前先读完，不要跳过"非目标"和"工作方式"两节。
> 有冲突时，以本文档为准；本文档没写的，先问，不要自己发挥。

---

## 0. 一句话

用 LendingClub 的历史放款数据，搭一个**可重放、可验证的信贷风险分析平台**：
从原始文件到维度模型到 vintage 分析到 PD 模型，全链路可以一条命令重建。

这是一个跨两年、逐版本长大的项目，不是一个学期作业。本学期只做 V1。

---

## 1. 背景与约束

- 作者：数据科学与 AI 硕士一年级（2026–2028），金融本硕 + 4 年券商/基金从业背景。
- 目标：求职 Data Engineer / Analytics Engineer / Risk Analytics（阿联酋市场）。
- 时间：兼顾课程，每周投入项目约 8–10 小时。
- 项目定位：**唯一的旗舰项目**。不再开第二个。所有新能力都往这个平台上加。

设计上的一条硬原则：**这个项目要证明"我能对一套系统的正确性负责"，而不是"我会跑模型"。**
所以数据正确性、可重建性、验证方法的优先级，永远高于模型精度。

---

## 2. 五层框架

| 层 | 内容 | 本学期 |
|---|---|---|
| **L0 数据与回放** | 原始文件 → 按 `issue_d` 切月度批次 → 分区 parquet；可重放、幂等 | ✅ 完整做完 |
| **L1 维度建模** | staging → star schema（dbt） | ✅ 完整做完 |
| **L2 SQL 分析** | vintage 曲线、信贷政策漂移、定价充分性 | ✅ 完整做完 |
| **L3 风险模型** | Logistic PD、OOT 验证、PSI、成本敏感阈值 | 🟡 只做 v0 |
| **L4 AI 层** | Analyst copilot / reject inference | ❌ 本学期不碰 |

L0 是地基。**没有时间轴，L2 和 L3 全是假的。** 先把回放跑通再谈别的。

---

## 3. 三个核心设计决策

这三条是本项目区别于网上几百个 LendingClub notebook 的全部原因。不要简化掉任何一条。

### 3.1 月度回放（最重要）

LendingClub 已于 2020 年底关闭 Notes 平台，公开数据是一份**静态快照**（约 2007–2018Q4）。
在静态 CSV 上搭管道是表演，面试时一问就穿。

解法：**按 `issue_d` 把数据切成月度批次，按时间顺序重放。**
系统在处理 2015-03 这一批时，只能看到 2015-03 及之前的数据。

这一招同时买到三样东西：
- **工程**：增量加载、幂等、回填、分区 —— 全部变成真问题
- **验证**：out-of-time validation 天然成立
- **金融**：vintage 分析成为可能

### 3.2 主线指标是 vintage 和衰减，不是 AUC

要回答的核心问题不是"能不能预测违约"，而是：

> 一家自己定价的贷款平台，它的风险定价对不对，什么时候开始不对的。

主线产出：
- 按放款年份/季度分组的**累计核销率 vs 账龄**曲线
- 同一 grade 内，**收取的利率是否覆盖了该 vintage 实际实现的损失**
- grade 分布、平均利率、平均 DTI、平均 FICO 随时间的**政策漂移**
- 模型在 OOT 上的**衰减**，配 PSI 监控

**AUC 只是附带指标，不是标题。**

### 3.3 泄漏与删失，第一周就锁死

这是公开 LendingClub 项目里错得最多的地方，也是最便宜的差异化。
在 `README` 里明确写清楚排除了什么、为什么、未到期贷款怎么处理。

**必须排除的泄漏字段**（放款后才产生）：

```
out_prncp, out_prncp_inv
total_pymnt, total_pymnt_inv
total_rec_prncp, total_rec_int, total_rec_late_fee
recoveries, collection_recovery_fee
last_pymnt_d, last_pymnt_amnt, next_pymnt_d
last_credit_pull_d, last_fico_range_high, last_fico_range_low
pymnt_plan
debt_settlement_flag*, settlement_*
hardship_*, deferral_term, orig_projected_additional_accrued_interest
```

**删失处理**：`loan_status` 为 `Current` / `In Grace Period` / `Late (*)` 的贷款结果尚未实现，
不能当作"未违约"。建模样本只取**已到期**的贷款：
- `term = 36 months` → `issue_d` 距快照 ≥ 36 个月
- `term = 60 months` → `issue_d` 距快照 ≥ 60 个月

目标变量：`Charged Off` / `Default` = 1，`Fully Paid` = 0，其余排除。

**一个必须处理的设计选择**：`grade` / `sub_grade` / `int_rate` 是 LendingClub 自己风控模型的输出，
不是泄漏，但把它们放进特征意味着你在"预测别人的模型"。
→ 做两个版本（含/不含），并在 README 里说明差异。这是加分项，不是可选项。

**一个必须记录的数据限制**：公开的 accepted 文件是每笔贷款一行的**终态快照**，
没有月度还款面板。vintage 曲线只能用 `issue_d` 与 `last_pymnt_d` 的差近似违约时点。
这是近似，必须在 README 和图注里写明。**不要假装有月度面板数据。**

---

## 4. 技术栈（硬约束）

**用**：Python 3.11+、DuckDB、dbt-duckdb、Polars 或 Pandas、scikit-learn、matplotlib、pytest、ruff、Make

**本学期明确不用**：Airflow / Dagster、Spark、任何云服务、XGBoost / LightGBM、SHAP、
任何 dashboard 框架、任何 LLM / API 调用、Docker

理由：这些全部排在 2027 年春季及以后。现在引入只会让进度在第 8 周崩掉。
如果 agent 认为某项"顺手加上更好"，**先停下来问，不要自己加**。

---

## 5. 仓库结构

```
financial-risk-platform/
├── README.md              # 项目说明 + 泄漏清单 + 数据限制（重要产出，不是摆设）
├── Makefile               # make all 端到端重建
├── pyproject.toml
├── data/
│   ├── raw/               # 原始 CSV，gitignored
│   └── batches/           # 月度分区 parquet，gitignored
├── src/
│   ├── ingest.py          # 原始文件 → 规范化 parquet
│   ├── replay.py          # 按 issue_d 切月度批次
│   ├── features.py        # 特征构造（严格只用 origination 时点可得字段）
│   └── modeling/
│       ├── pd_model.py    # logistic PD
│       └── validation.py  # OOT、PSI、校准
├── dbt/
│   └── models/
│       ├── staging/       # stg_loans, stg_borrowers
│       └── marts/         # dim_*, fact_*
├── analysis/              # 探索用 notebook，结论必须落回 dbt 或 src
├── reports/
│   └── figures/           # 三张主图
└── tests/
```

---

## 6. 数据模型（star schema 草案）

Agent 可以调整字段，但**粒度不许改**：

- `dim_borrower` — 申请时点的借款人属性：`annual_inc`、`emp_length`、`home_ownership`、
  `addr_state`、`dti`、`fico_range_low/high`、`earliest_cr_line`、`open_acc`、`revol_util`、`pub_rec` …
- `dim_loan` — 贷款条款：`loan_amnt`、`term`、`purpose`、`grade`、`sub_grade`、`int_rate`、`installment`
- `dim_date` — 月度日历，支撑 vintage 与账龄计算
- `fact_origination` — **粒度：一笔贷款一行**，放款时点事实
- `fact_loan_outcome` — **粒度：一笔贷款一行**，终态结果 + 近似违约账龄（含 `is_censored` 标记）

所有 mart 必须带 dbt test：主键唯一、非空、`accepted_values`、关系完整性。

---

## 7. 里程碑

### 第 1–2 周
- [ ] 数据下载，`ingest.py` 跑通，落规范化 parquet
- [ ] 泄漏字段清单落到代码里（一个常量 + 一个测试，不是文档里的一段话）
- [ ] 删失规则实现 + 单元测试
- [ ] 第一批探索性 SQL

### 第 3 周
- [ ] `replay.py` 跑通：月度分区、幂等（重跑两次结果一致）
- [ ] dbt staging + 第一版 star schema

### 第 4 周 —— **10 月与导师会面的截止线**
- [ ] 三张主图产出（见第 8 节）
- [ ] 5 页汇报材料

### 第 5–12 周
- [ ] mart 层补齐，5–8 个 dbt model，全部带 test
- [ ] vintage / 政策漂移 / 定价充分性 三条分析线完成
- [ ] Logistic PD v0 + OOT 衰减曲线 + PSI
- [ ] 成本敏感阈值与 Expected Loss 测算
- [ ] README 定稿

---

## 8. 验收标准（12 月中）

五条，全部可勾选，缺一不算完成：

1. **一条命令**（`make all`）从原始文件重建到 2018-12，**重跑两次结果完全一致**
2. star schema 落地，5–8 个 dbt model，**每个都带 test**
3. 三张主图 + 一段能讲清楚的结论：
   - 图 A：按 vintage 的累计核销率 vs 账龄
   - 图 B：同 grade 内利率覆盖 vs 实现损失（**这张是核心**）
   - 图 C：grade 结构 / 定价 / 借款人质量的时间漂移
4. Logistic PD 模型 + OOT 衰减曲线 + PSI 监控
5. README 含泄漏字段清单、删失处理说明、数据限制声明

---

## 9. 非目标（明确不做）

- ❌ 第二个项目
- ❌ XGBoost / SHAP / 深度学习
- ❌ Airflow / Dagster / Spark / 云 / Docker
- ❌ Dashboard、前端、可视化平台
- ❌ 任何 LLM 集成
- ❌ 追求 AUC 排名
- ❌ 提前搭"以后用得上"的抽象层

以上全部排在 2027 及以后。**过度工程是这个项目最大的失败模式。**

---

## 10. 给 agent 的工作方式约定

1. **小步、每步可运行。** 不要一次生成整个项目骨架。每次改动后 `make all` 必须仍然能跑通。
2. **先出能跑的丑版本，再改好。** 第一版 `replay.py` 可以是一个 for 循环。不要一上来抽象。
3. **不确定就问，不要发挥。** 尤其是引入新依赖、新工具、新目录层级之前。
4. **正确性 > 性能 > 优雅。** 数据量在单机 DuckDB 上完全够用，不要为了性能做提前优化。
5. **每个关键数据规则都要有测试。** 泄漏排除、删失过滤、幂等性 —— 这三件事必须有测试守着。
6. **README 是产出物之一**，不是收尾工作。边做边写。

---

## 11. 后续版本路线（本学期不实现，仅供架构时留意）

| 时间 | 加什么 | 改叫 |
|---|---|---|
| 2027 春 | XGBoost、SHAP、成本敏感决策、编排器、故障注入演练 | Financial Risk Analytics Platform |
| 2027 夏 | 实习期暂停；无实习则迁云（Azure，配合 DP-203） | — |
| 2027 秋 | Fraud / AML 模块 **或** L4 AI 层（二选一，不要都做） | AI-Powered Financial Risk Platform |
| 2028 春 | Capstone、演示视频、README 定稿 | 毕业作品 |

**触发条件**：任何时候拿到一份真实的、脏的、会更新的数据（通过导师、实习或其他渠道），
把它接成新的 L0，**不要另起项目**。这是这个平台唯一的硬伤，也是唯一的升级机会。

---

## 12. 两个研究问题（不写进代码，但影响设计取舍）

留给与导师讨论，本学期不实现：

**A｜选择偏误**
只观测到被批准贷款的结果，被拒的永远没有 outcome。
那如何评估这家平台的**信贷政策本身**的好坏？（reject inference）

**B｜AI 层**
若让 LLM 基于模型输出生成风险解释，人类审批员的决策**质量与一致性**会变好还是变差？

设计 L1/L2 时保留足够的原始字段，别为了建模方便把这两个问题需要的信息提前丢掉。
