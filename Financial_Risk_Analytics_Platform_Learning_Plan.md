# Financial Risk Analytics Platform — Technical Stack Learning Plan

## 0. Current Starting Point

当前 SQL 水平：

> 可以独立完成约 **60% 的 DataLemur Medium** 题目。

因此本计划不再把时间浪费在：

- SELECT 基础
- WHERE 基础
- 普通 GROUP BY
- 普通 JOIN
- 基础聚合函数
- 入门 CTE

这些内容默认已经具备。

SQL 学习直接进入：

> **Project-oriented Analytics SQL**

重点训练如何把业务定义正确翻译成：

- cohort / vintage SQL
- date logic
- window analytics
- multi-stage aggregation
- denominator correctness
- grain control
- duplicate prevention
- DuckDB SQL
- dbt models
- data-quality checks

---

# 1. Learning Repo 与 Project Repo 分离

建立两个独立 repository。

## Repo A — Learning

```text
data-stack-learning/
├── 01_python_project_basics/
├── 02_duckdb_parquet/
├── 03_analytics_sql/
├── 04_testing_make/
├── 05_data_modeling_dbt/
├── 06_vintage_analytics/
├── 07_risk_analytics/
└── 08_ml_validation/
```

这里允许：

- 教学代码
- 小练习
- Notebook
- SQL 草稿
- 错误代码
- toy dataset
- ChatGPT 示例
- 临时实验

这个 repo 不追求漂亮。

---

## Repo B — Project

```text
financial-risk-platform/
```

只有满足以下三个条件的代码才能进入：

1. 我知道它为什么存在。
2. 我能解释它大致怎么工作。
3. 它确实属于正式 pipeline。

原则：

> **先在 Learning Repo 学会，再进入 Project Repo 实现。**

Codex 的主要工作环境是 Project Repo。

基础学习、练习、试错全部留在 Learning Repo。

---

# 2. Overall Learning Order

按照项目依赖顺序学习：

```text
Python 项目基础
        ↓
DuckDB + Parquet
        ↓
Project-oriented Analytics SQL
        ↓
pytest + ruff + Make
        ↓
Data Modeling + dbt
        ↓
Vintage / Cohort Analytics
        ↓
Risk / Pricing Analytics
        ↓
scikit-learn Logistic Regression
        ↓
OOT / Calibration / PSI
```

不是把一本教材全部学完再开始项目。

规则：

> 每学完一层，就允许 Project Repo 前进一层。

---

# 3. Phase 0 — Python Project Basics

## Target

从“会写 Python 练习”过渡到“能维护一个小型数据项目”。

## Must Learn

### Functions
- arguments
- return
- default arguments
- simple type hints

### Modules
理解：

```python
from pathlib import Path
from src.features import clean_features
```

掌握：

- `.py` 文件
- import
- 多文件函数调用
- `if __name__ == "__main__":`

### Scope
理解 local / global scope 即可。

### Exceptions
重点能看懂并处理：

- `KeyError`
- `ValueError`
- `TypeError`
- `FileNotFoundError`

会使用简单：

```python
try:
    ...
except ...
```

### pathlib
掌握：

- 路径拼接
- 创建目录
- 判断文件是否存在
- 遍历文件

### Pandas

重点：

```text
read_csv
read_parquet
to_parquet
select columns
filter
rename
astype
isna
fillna
dropna
sort_values
groupby
agg
merge
assign
datetime
drop_duplicates
```

特别需要理解：

- index 不等于业务主键
- merge 后为什么可能行数变多
- dtype 为什么重要
- datetime parsing

## Not Needed Yet

- OOP 深入
- decorators
- generators
- async
- metaclasses
- advanced typing

## Exit Test

独立完成：

```text
CSV
→ 清洗字段
→ 处理日期
→ 按 issue month 分组
→ 写出多个 Parquet
```

并能解释每一步。

---

# 4. Phase 1 — DuckDB + Parquet

## Target

理解项目的本地 analytical storage。

## Parquet

必须理解：

- CSV vs Parquet
- columnar storage
- schema / dtype
- compression
- partition
- why Parquet is suited for analytics

不需要深入研究 Parquet internals。

## DuckDB

必须会：

- query CSV
- query Parquet
- create table
- create view
- write Parquet
- join
- aggregate
- date functions
- basic EXPLAIN awareness

重点理解：

> DuckDB 是本地 analytical database，不是为了模拟传统 OLTP 数据库。

## Incremental Processing

理解：

> 新月份数据到来时，只处理新增部分，而不是每次重建所有原始步骤。

## Idempotency

同样输入重复运行：

```text
第一次 → 100 rows
第二次 → 100 rows
```

不能变成：

```text
第二次 → 200 rows
```

## Exit Test

完成 toy replay：

```text
loans.csv
→ 2020-01.parquet
→ 2020-02.parquet
→ 2020-03.parquet
```

重复运行结果一致。

---

# 5. Phase 2 — Project-Oriented Analytics SQL

## Current Level Adjustment

由于已经可以独立完成约 60% DataLemur Medium：

> **不安排基础 SQL 周。**

学习重点从“会不会写 SQL”转成：

> **能不能用 SQL 正确表达金融分析业务规则。**

---

## 5.1 Window Functions — 必须熟练

重点：

```sql
ROW_NUMBER()
RANK()
DENSE_RANK()
LAG()
LEAD()
SUM() OVER (...)
AVG() OVER (...)
COUNT() OVER (...)
```

需要熟练：

- `PARTITION BY`
- `ORDER BY`
- cumulative calculation
- rolling / prior-period comparison

项目用途：

- cumulative charge-off curve
- vintage curve
- month-over-month change
- policy drift
- cohort ranking

---

## 5.2 Date Analytics — 高优先级

重点训练：

- year
- quarter
- month
- date truncation
- date difference
- loan age
- vintage
- MOB

能够把：

```text
issue_d = 2015-03
last_pymnt_d = 2017-01
```

转换成：

```text
loan age ≈ 22 months
```

这是整个 Vintage Analysis 的核心 SQL 能力。

---

## 5.3 Conditional Aggregation

必须熟练：

```sql
SUM(CASE WHEN ... THEN ... END)
COUNT(CASE WHEN ... THEN 1 END)
AVG(CASE WHEN ... THEN ... END)
```

项目用途：

- default rate
- charge-off rate
- term mix
- grade mix
- censored share
- cohort-level metrics

---

## 5.4 Multi-Stage Aggregation

重点练习：

```text
loan-level
↓
grade × vintage
↓
year-level / portfolio-level
```

理解为什么很多指标不能直接：

```sql
AVG(metric)
```

特别训练：

- average of averages
- weighted average
- numerator / denominator
- portfolio mix

---

## 5.5 Grain Control

这是比刷 Medium 题更重要的能力。

每次 JOIN 前必须回答：

> 左表一行代表什么？  
> 右表一行代表什么？  
> JOIN 后预期一行代表什么？

重点练：

- one-to-one
- one-to-many
- accidental duplication
- row-count validation
- unique keys

项目里任何：

```text
贷款数量突然翻倍
```

都必须优先怀疑 grain / join。

---

## 5.6 Cohort / Vintage SQL

需要专门练习：

```text
origination cohort
loan age
terminal outcome
cumulative loss
cumulative charge-off
```

最终要能独立设计：

```text
vintage × MOB
```

分析表。

---

## 5.7 DuckDB SQL Differences

熟悉项目真正会用到的 DuckDB functions。

不需要系统学习数据库方言。

只关注：

- date functions
- string cleanup
- Parquet scanning
- casting
- list of supported aggregations
- window SQL

---

## 5.8 dbt SQL Style

SQL 从刷题风格过渡到 production analytics style：

```sql
with source as (...),

cleaned as (...),

final as (...)

select *
from final
```

重点：

- 一个 model 做一件事
- 清晰命名
- 不写巨大 SQL
- 可测试
- 可复用
- business logic 分层

---

## SQL Exit Test

不再以 DataLemur 正确率作为主要标准。

真正标准是：

能独立写出以下分析：

1. 每季度 origination 数量。
2. Grade × vintage 的平均利率。
3. Grade mix 随时间变化。
4. Average FICO / DTI 随时间变化。
5. 36/60 month mix。
6. Matured vs censored loan counts。
7. Vintage × MOB 的 cumulative charge-off table。
8. Weighted average interest rate。
9. JOIN 后验证 grain 没被破坏。
10. 将上述逻辑拆成清晰的 dbt models。

DataLemur 可以继续刷，但只作为：

> SQL fluency maintenance。

建议每周 2–3 道 Medium，不再作为主学习内容。

---

# 6. Phase 3 — pytest + ruff + Make

## pytest

只学习项目需要的测试思维。

重点会写：

```python
def test_xxx():
    ...
```

和：

```python
assert result == expected
```

## Project-Specific Tests

必须会写三类：

### Leakage Test
禁止字段不能进入 model features。

### Censoring Test
不成熟贷款必须被正确过滤 / 标记。

### Idempotency Test
Replay 重跑不能产生重复数据。

另外建议学：

- temporary directory
- small fixture
- deterministic test data

不需要深入 pytest plugin 生态。

---

## ruff

会运行：

```bash
ruff check .
```

理解它用于：

- lint
- import issues
- basic code-quality checks

足够。

---

## Make

理解 Makefile 是项目入口层。

最终需要：

```bash
make ingest
make replay
make dbt
make test
make model
make all
```

目标：

> 把多个命令组织成稳定的、可重复的项目入口。

---

# 7. Phase 4 — Data Modeling + dbt

## Data Modeling Core

你现在需要真正掌握的不是整本 Kimball，而是：

### Grain
一行到底代表什么？

本项目核心：

> One row = one loan.

### Fact
发生了什么？

例如：

> 一笔贷款被发放。

### Dimension
描述这件事情的上下文。

例如：

- borrower
- loan
- date

### Star Schema

理解：

```text
         dim_borrower
              |
dim_date — fact_origination — dim_loan
```

### Key Questions

建任何表之前都问：

1. Grain 是什么？
2. Primary key 是什么？
3. 哪些字段是 measures？
4. 哪些字段是 dimensions？
5. JOIN 会不会改变 grain？

---

## dbt Must Learn

- project
- source
- model
- `ref()`
- staging
- intermediate
- marts
- schema.yml
- dbt build
- dbt test

### Core Tests

- unique
- not_null
- accepted_values
- relationships

## Do Not Learn Yet

- advanced macros
- packages
- snapshots
- semantic layer
- advanced Jinja
- dbt Cloud
- complex incremental models

## Exit Test

使用 toy loan dataset：

```text
stg_loans
↓
int_eligible_loans
↓
dim_loan
dim_borrower
fact_origination
fact_loan_outcome
```

并通过 dbt tests。

---

# 8. Phase 5 — Vintage / Cohort Analytics

## Business Concepts

必须理解：

### Vintage
同一时期发放的一批贷款。

### MOB
Months on Book。

### Charge-off
核销 / 坏账结果。

### Cumulative Charge-off Rate
随着 loan age 增加，一个 vintage 累计发生多少坏账。

### Censoring
贷款还没观察够久，结果尚未完全实现。

---

## Technical Skills

重点组合：

- SQL date logic
- cohort table
- cumulative window
- Pandas sanity check
- matplotlib

## matplotlib

只学项目必要内容：

```python
plt.plot()
plt.xlabel()
plt.ylabel()
plt.title()
plt.legend()
plt.savefig()
```

重点不在美化，而在：

> 图能准确表达业务结论。

## Exit Test

用 toy dataset 独立完成：

> Cumulative Default / Charge-off Rate by Vintage and MOB

并能解释：

- 分母是什么
- 分子是什么
- 为什么存在 censoring
- 为什么不能简单比较不同 vintage 最终 default rate

---

# 9. Phase 6 — Risk / Pricing Analytics

## Must Learn

### Interest Rate

### Default / Charge-off Rate

### Realized Loss

### Recovery

### Grade / Sub-grade

### Weighted Average

### Portfolio Mix

### Pricing Adequacy

重点不是复杂金融公式，而是理解：

> 收取的风险溢价有没有跟上后来真正发生的损失。

---

## Policy Drift

会分析：

- Grade %
- Average FICO
- Average DTI
- Average Interest Rate
- Average Loan Amount
- 36 / 60 month mix

重点是：

> 把 SQL 输出转换成业务解释。

---

## Exit Test

能够独立回答：

```text
2013 Grade C
vs
2016 Grade C
```

在以下方面有什么变化：

- rate
- realized loss
- FICO
- DTI
- term mix
- volume

---

# 10. Phase 7 — scikit-learn Logistic Regression

只有 L0–L2 基本稳定以后才进入。

## ML Workflow

理解：

```text
Features
↓
Target
↓
Train
↓
Predict Probability
↓
Evaluate
```

## Logistic Regression

需要理解：

- probability
- coefficient
- log-odds 直觉
- threshold
- class prediction
- probability prediction

不需要深入优化算法推导。

## scikit-learn Must Learn

- `Pipeline`
- `ColumnTransformer`
- `StandardScaler`
- `OneHotEncoder`
- `LogisticRegression`
- `predict_proba`
- `roc_auc_score`

重点理解：

> preprocessing 必须只 fit 在训练数据上。

---

## Temporal Validation

普通练习可以使用 random split。

正式项目必须：

```text
Past
→ Train

Future
→ Test
```

因为项目研究的是：

> 模型在未来是否衰减。

---

# 11. Phase 8 — Model Validation

学习顺序：

## 1. AUC

理解：

> 模型对高风险和低风险借款人的排序能力。

---

## 2. Calibration

如果模型预测：

```text
PD = 10%
```

那么这一批人的实际违约率是否接近 10%。

需要会：

- calibration curve
- predicted probability bins
- actual default rate

---

## 3. OOT Performance

观察：

```text
2015
2016
2017
2018
```

模型表现如何变化。

重点：

> performance decay over time

---

## 4. PSI

先理解业务意义：

> 当前客户群与训练时期客户群变化了多少。

然后再学习公式和实现。

---

## 5. Cost-Sensitive Threshold

理解：

> False Positive 与 False Negative 在信贷业务中的成本不同。

不使用固定 `0.5` 作为天然业务阈值。

---

## 6. Expected Loss

最后学习：

```text
Expected Loss = PD × LGD × EAD
```

V1 目标是理解并完成基础测算，不需要建立复杂 LGD/EAD 模型。

---

# 12. Calendar — Sep to Dec 2026

## Sep 9 – Sep 15

### Learning
- Python project basics
- modules
- pathlib
- Pandas
- datetime
- CSV / Parquet
- debugging

### Project
- dataset setup
- Data Dictionary
- repo initialization
- minimal ingest prototype

---

## Sep 16 – Sep 22

### Learning
- DuckDB
- Parquet
- partition
- incremental processing
- idempotency
- project-oriented SQL date logic
- grain-aware JOIN

### Project
- `ingest.py`
- `replay.py`
- monthly batches

---

## Sep 23 – Sep 29

### Learning
- pytest
- ruff
- Make
- Data Modeling fundamentals
- dbt basics

### Project
- L0 completion
- leakage test
- censoring test
- idempotency test
- dbt staging start

---

## Sep 30 – Oct 6

### Learning
- star schema
- dbt tests
- vintage
- MOB
- cohort SQL
- cumulative windows
- matplotlib basics

### Project
- L1 completion
- first vintage mart
- Figure A v0

---

## Oct 7 – Oct 20

### Learning
- pricing analytics
- weighted averages
- realized loss
- portfolio mix
- policy drift

### Project
- Figure A final
- Figure B
- Figure C
- mentor presentation version

---

## Oct 21 – Nov 10

### Learning
- sklearn
- Logistic Regression
- preprocessing pipeline
- `predict_proba`
- temporal validation
- AUC

### Project
- PD Model V0
- Model A / B
- first OOT results

---

## Nov 11 – Nov 25

### Learning
- calibration
- PSI
- model decay
- cost-sensitive threshold
- Expected Loss

### Project
- model validation
- calibration
- PSI
- OOT decay
- Expected Loss v0

---

## Nov 26 – Dec 10

### Learning
原则：

> 不再开启新的技术主题。

只做针对项目缺口的复习。

### Project
- bug fixing
- dbt tests
- code cleanup
- README
- figures
- `make all`
- interview narrative

---

# 13. Weekly Time Allocation

## Learning Track

建议：

> **4–6 小时 / 周**

主要发生在：

```text
data-stack-learning
```

SQL 因已有较好基础，不再额外设置大量语法学习时间。

SQL 维护：

> 每周 2–3 道 DataLemur Medium。

其余 SQL 时间全部用于真实项目型分析问题。

---

## Project Track

建议：

> **8–10 小时 / 周**

只发生在：

```text
financial-risk-platform
```

---

# 14. V1 Skill Depth

| Skill | Fall 2026 Target |
|---|---|
| Python | 能写结构化数据处理脚本 |
| Pandas | 能完成清洗、merge、groupby、datetime |
| SQL | 能独立实现复杂 analytics / cohort SQL |
| Window Functions | 熟练用于累计、时间比较和 cohort |
| DuckDB | 能处理 CSV / Parquet / analytical tables |
| Parquet | 理解 schema、columnar、partition |
| Data Modeling | 能解释并维护 grain / fact / dimension |
| dbt | 能做 staging → intermediate → marts + tests |
| pytest | 能给核心业务规则写自动测试 |
| Make | 能组织端到端 pipeline |
| matplotlib | 能做清晰的业务分析图 |
| sklearn | 能完成 Logistic PD baseline |
| AUC | 会计算、会解释 |
| Calibration | 会计算、会解释 |
| OOT | 必须真正理解并实现 |
| PSI | 能计算、会解释 |
| Expected Loss | 理解 PD × LGD × EAD |
| Git | 能正常 commit / branch / revert |

---

# 15. Explicit Non-Learning List — Fall 2026

暂时不学习：

- Spark
- Airflow
- Dagster
- Azure
- AWS
- Docker
- XGBoost
- LightGBM
- SHAP
- Deep Learning
- LLM
- RAG
- Agent
- Streamlit
- Tableau
- Power BI
- Advanced dbt
- Advanced MLOps

原因不是这些技术没用，而是：

> 它们现在不会显著提高 V1 完成概率。

---

# 16. Working Rule

以后每进入一个新模块，都使用：

```text
Step 1
先理解概念

↓

Step 2
在 data-stack-learning
做一个小练习

↓

Step 3
自己能够解释代码

↓

Step 4
再打开 financial-risk-platform

↓

Step 5
让 Codex 帮助正式实现

↓

Step 6
测试

↓

Step 7
Commit
```

不要：

```text
打开 Codex
↓
一边学基础
一边让它生成正式项目代码
↓
最后 repo 里出现大量自己无法解释的内容
```

最终目标：

> **Codex 提高开发效率，但项目的核心设计、数据规则、分析逻辑与代码结构都必须由自己理解并负责。**
