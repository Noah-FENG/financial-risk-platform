# L0 Ingestion 学习与复习笔记

**整理日期：** 2026-09-12  
**对应阶段：** Phase 1 — L0 Foundation  
**目前边界：** ingestion 与 monthly batch audit 已完成运行验收；月度物理分区、replay 和正式 pytest 测试尚未完成。

## 1. 先看全局：我们已经做了什么

目前的工作可以按下面这条数据流理解：

```text
原始 CSV（保持不变）
        ↓ 读取
原始 DataFrame：df / raw
        ↓ 清洗、标准化、检查
清洗后 DataFrame：df_clean
        ├──→ accepted_loans_normalized.parquet
        └──→ cleaning_audit.csv
```

已经完成的内容：

1. **Step 3A — Data Dictionary**
   - 明确 43 个核心字段的含义、单位和使用时点。
   - 区分放款时可见字段与放款后才产生的字段，防止未来 PD 模型发生数据泄漏。

2. **Step 3B — Profiling**
   - 检查主键、缺失值、数值分布、类别取值和异常情况。
   - 这一步的作用是先认识数据，再决定清洗规则。

3. **Step 3C — Cleaning and Validation**
   - 保持原始 CSV 不变，创建新的 `df_clean`。
   - 删除 33 条不是贷款记录的 footer 行。
   - 删除全空的 `member_id` 列。
   - 标准化日期、数值、类别、期限和就业年限。
   - 对异常值增加 flag，不擅自删除或修改原始数值。
   - 检查主键、时间轴、期限、跨字段关系和 PD leakage 边界。

4. **正式 ingestion**
   - 将 Notebook 中验证过的逻辑迁移到 `src/ingest.py`。
   - 输入是原始 CSV，输出是标准化 Parquet 和 cleaning audit。

5. **运行结果验收**
   - 原始行数：2,260,701。
   - 删除 footer：33。
   - 清洗后行数：2,260,668。
   - 重复 `id`：0。
   - 缺失 `issue_d`：0。
   - 非法 `term_months`：0。

尚未完成：

- `data/batches/` 月度物理分区；
- `src/replay.py`；
- leakage、censoring、replay 的正式测试；
- `tests/` 目录中的 pytest 测试。

---

## 2. 四个容易混淆的概念

| 工作 | 它检查什么 | 当前状态 |
|---|---|---|
| 正式验收 `df_clean` | 一次清洗产生的数据是否符合规则 | 已运行通过 |
| 两次运行并比对 | 同样输入重复运行是否得到同样结果 | 已手动验证通过 |
| `ingest.py` | 是否能离开 Notebook，正式重复生产结果 | 已建立并运行 |
| `pytest` | 规则能否用小型自动测试持续检查 | 工具已安装，但测试尚未编写 |

一句话区分：

```text
df_clean 验收：这一次结果对不对？
两次运行比对：重复运行是否稳定？
ingest.py：怎样正式生产结果？
pytest：以后怎样自动发现规则被改坏了？
```

---

## 3. 工作一：汇总本步骤结果并正式验收 `df_clean`

### 3.1 `df_clean` 是什么

`df_clean` 是清洗后的 pandas DataFrame。可以先把 DataFrame 理解成 Python 内存里的一张表。

- `df` 或 `raw`：从原始 CSV 读进来的表。
- `df_clean`：从原始表复制出来，再按照规则清洗得到的表。

关键代码是：

```python
df_clean = raw.copy()
```

这里使用 `.copy()` 的原因是：后续修改 `df_clean` 时，不应该直接改变原始数据对象。硬盘上的原始 CSV 也始终不覆盖。

### 3.2 “汇总结果”在做什么

Notebook 创建了一个 `final_validation` 小表：

```python
final_validation = pd.DataFrame(
    {
        "metric": [
            "raw_row_count",
            "clean_row_count",
            "footer_rows_removed",
            "missing_id_count",
            "duplicate_id_count",
            "missing_issue_d_count",
            "invalid_term_count",
        ],
        "count": [
            original_len,
            len(df_clean),
            original_len - len(df_clean),
            int(df_clean["id"].isna().sum()),
            int(df_clean["id"].duplicated().sum()),
            int(df_clean["issue_d"].isna().sum()),
            int((~df_clean["term_months"].isin([36, 60])).sum()),
        ],
    }
)
```

逐项理解：

- `original_len`：原始表有多少行。
- `len(df_clean)`：清洗后有多少行。
- `original_len - len(df_clean)`：删除了多少行。
- `isna().sum()`：某一列有多少个缺失值。
- `duplicated().sum()`：有多少个重复主键。
- `isin([36, 60])`：期限是否属于允许的 36 或 60 个月。
- 前面的 `~`：把判断反过来，因此统计“不属于 36 或 60”的行。
- `int(...)`：把 pandas/numpy 产生的数字转换成普通 Python 整数，方便写入 audit。

这张表的作用是给人看，让我们知道每项检查的结果是多少。

### 3.3 `assert` 在做什么

Notebook 接着执行：

```python
assert len(df_clean) == original_len - 33
assert df_clean["id"].isna().sum() == 0
assert df_clean["id"].duplicated().sum() == 0
assert df_clean["issue_d"].isna().sum() == 0
assert df_clean["term_months"].isin([36, 60]).all()
```

`assert 条件` 的意思是：**我要求这个条件必须为真。**

- 条件为真：程序继续运行。
- 条件为假：立即抛出 `AssertionError`，提醒我们不能把结果当成合格数据。

所以 `display(final_validation)` 和 `assert` 不是重复工作：

- `display(...)` 是把结果展示给人看；
- `assert` 是让程序自动阻止错误结果继续向下运行。

### 3.4 PD leakage 检查在做什么

Notebook 还准备了两张字段名单：

- `pd_feature_candidates`：未来可能放入 PD 模型的放款时特征；
- `forbidden_pd_columns`：贷款结果或放款后字段，禁止作为 PD 输入。

核心检查是：

```python
leakage_overlap = (
    set(pd_feature_candidates)
    & set(forbidden_pd_columns)
)

assert len(leakage_overlap) == 0
```

`&` 表示求两个集合的交集。如果交集为空，说明候选特征中没有混入禁用字段。

这一步不是在训练模型，只是在提前划清字段边界。

### 3.5 `cleaning_audit` 是什么

前面每一步产生的日期解析、数值解析、异常 flag、类别检查、跨字段检查和最终验收结果，最后通过 `pd.concat(...)` 合并成一张长表：

```text
section                  metric                                count
final_validation         clean_row_count                       2260668
final_validation         duplicate_id_count                    0
quality_flags            dti_out_of_range                      2563
...
```

注意：audit 中某些 `count` 不为 0 不一定代表 pipeline 失败。例如 `dti_out_of_range = 2563` 是“发现并记录了 2,563 条异常”，不是“已经删除 2,563 条数据”。

### 3.6 你需要掌握到什么程度

- **了解：** `df_clean` 是从原始数据派生出来的清洗结果，不是原始数据本身。
- **会使用：** 能读懂 `len`、`isna`、`duplicated`、`isin` 和 `assert` 的检查结果。
- **会证明：** 能根据输出说明为什么现在可以说“一行代表一笔有效贷款，主键唯一，发放月份可用”。

---

## 4. 工作二：两次运行并比照结果

### 4.1 它验证的是 idempotency

这里的目标叫 **idempotency（幂等性）**：

> 在输入文件和代码都没有变化时，重复运行 pipeline，应得到逻辑上完全相同的输出。

它不是说“程序能运行两次就够了”，而是说“两次产生的数据内容、列、顺序和类型都一致”。

### 4.2 Notebook 中的四个步骤

```python
# 第一次结果
before_data = pd.read_parquet(parquet_path)
before_audit = pd.read_csv(audit_path)

# 再运行一次正式脚本
result = subprocess.run(
    [sys.executable, "src/ingest.py"],
    capture_output=True,
    text=True,
)

# 第二次结果
after_data = pd.read_parquet(parquet_path)
after_audit = pd.read_csv(audit_path)

# 比较
assert_frame_equal(before_data, after_data, check_dtype=True)
assert_frame_equal(before_audit, after_audit, check_dtype=True)
```

各部分含义：

- `subprocess.run(...)`：从 Notebook 中启动另一个 Python 进程，执行正式脚本。
- `result.returncode == 0`：脚本正常结束；非 0 通常表示报错。
- `assert_frame_equal(...)`：比较两张 DataFrame 的内容、列、顺序等。
- `check_dtype=True`：不仅数字要相同，数据类型也要相同。例如 `int64` 和字符串不能被当作一样。

### 4.3 它和 `df_clean` 验收的区别

可能出现下面两种情况：

1. 两次结果完全一样，但两次都错了。
   - 幂等性通过。
   - 业务规则验收不一定通过。

2. 每次结果单独看都合理，但排序或随机处理导致两次不同。
   - 单次业务验收可能通过。
   - 幂等性失败。

因此两种检查都需要。

### 4.4 当前脚本每次都会完整运行

当前执行：

```powershell
uv run python src/ingest.py
```

会重新读取原始 CSV、执行清洗并写出结果。因此，做幂等性复验时，需要在运行前保留第一份逻辑结果，运行后再和第二份逻辑结果比较。

以后如果确实需要增加缓存，缓存判断还必须同时考虑输入内容、清洗代码版本和输出完整性，不能只凭文件修改时间决定跳过。

Notebook 的全量比较会同时占用较多内存。以后正式自动化时，不会让 pytest 每次加载两份 226 万行数据；小型业务规则测试使用人工小样本，全量幂等性作为单独的端到端检查。

### 4.5 你需要掌握到什么程度

- **了解：** 幂等性回答的是“同样输入重复运行是否稳定”。
- **会使用：** 能运行正式脚本，并看懂 `returncode` 和 `assert_frame_equal`。
- **会证明：** 能说明“运行两次都没有报错”为什么不等于“两次输出完全一致”。

---

## 5. 工作三：`ingest.py`

### 5.1 它是什么

`ingest` 可以先理解为“把外部原始数据可靠地接入项目”。

`src/ingest.py` 的职责是：

```text
找到原始 CSV
→ 检查输入字段
→ 执行清洗规则
→ 执行质量检查
→ 生成 df_clean 和 cleaning_audit
→ 写出 Parquet 和 CSV audit
```

### 5.2 为什么不能永远只用 Notebook

Notebook 适合：

- 看数据；
- 逐步实验；
- 显示表格；
- 理解异常。

正式脚本适合：

- 从头重复运行；
- 明确输入和输出；
- 遇到错误立即停止；
- 被测试、Makefile 或后续 pipeline 调用。

所以迁移到 `ingest.py` 不是重复写一遍，而是把“探索成功的步骤”变成“正式生产流程”。

### 5.3 当前脚本的四层结构

#### 第一层：路径和规则名单

例如：

```python
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_CSV_PATH = PROJECT_ROOT / "data" / "raw" / "accepted_2007_to_2018Q4.csv"
```

这样无论从哪个工作目录调用脚本，它都能相对于项目根目录寻找文件。

`DATE_COLUMNS`、`NUMERIC_COLUMNS`、`PD_FEATURE_CANDIDATES` 和 `FORBIDDEN_PD_COLUMNS` 则集中记录字段规则。

#### 第二层：`clean_loans(raw)`

```python
def clean_loans(raw):
    ...
    return df_clean, cleaning_audit
```

它接收原始 DataFrame，返回两个结果：

1. 清洗后的贷款数据；
2. 清洗审计表。

这是核心业务逻辑。

#### 第三层：`run_pipeline()`

它负责文件层面的流程：

- 用 `pd.read_csv` 读取原始文件；
- 调用 `clean_loans(raw)`；
- 用 `to_parquet` 和 `to_csv` 写出结果；

可以把它理解为总调度员，而 `clean_loans` 是负责实际清洗的工作人员。

#### 第四层：命令行入口

```python
if __name__ == "__main__":
    ...
```

这表示：只有直接运行这个文件时，下面的命令行逻辑才执行。

```powershell
uv run python src/ingest.py
```

当前每次运行都会从原始 CSV 完整执行清洗和写出。

### 5.4 你现在不需要背什么

暂时不需要背完整的 600 多行代码，也不需要自己从空白文件写出全部 pipeline。优先做到：

1. 能指出输入文件和两个输出文件；
2. 能找到 `clean_loans`、`run_pipeline` 和命令行入口；
3. 能用自己的话说出它们各自负责什么；
4. 能在一个小规则上做修改，并知道应该补什么检查。

### 5.5 你需要掌握到什么程度

- **了解：** Notebook 是探索环境，`ingest.py` 是正式可重复程序。
- **会使用：** 会运行脚本，并看终端的成功/报错信息。
- **会证明：** 能从代码中指出输入、清洗函数、输出和失败条件分别在哪里。

---

## 6. 工作四：pytest

### 6.1 pytest 是什么

pytest 是 Python 的自动测试工具。它会寻找通常叫作 `test_*.py` 的文件，再运行其中以 `test_` 开头的函数。

最小示例：

```python
def add_one(x):
    return x + 1


def test_add_one():
    assert add_one(2) == 3
```

运行：

```powershell
uv run pytest -q
```

pytest 会告诉我们哪些测试通过、哪些失败，以及失败发生在哪一行。

### 6.2 它和 Notebook 里的 `assert` 有什么区别

Notebook 中的 `assert`：

- 只在运行那个单元格时检查；
- 结果容易受 Notebook 当前内存状态和执行顺序影响；
- 适合探索阶段快速验收。

pytest：

- 从干净测试过程开始；
- 可以一次自动执行许多独立测试；
- 修改代码后随时重跑；
- 适合长期保护已经确定的规则。

pytest 内部仍然经常使用 `assert`。区别不在于有没有 `assert`，而在于这些检查是否被组织成可以重复发现和执行的测试。

### 6.3 为什么测试用小样本

我们不会让每个 pytest 都读取 1.6GB CSV。正式测试应构造几行人工数据，专门验证一个规则，例如：

- 缺少必要字段时应报错；
- `term = " 36 months"` 能转换成 `36`；
- 非法期限会报错；
- `< 1 year` 会转换成 `0.5`，类型允许小数；
- 重复 `id` 会报错；
- PD 候选字段不能包含放款后字段。

小样本的优点是：快、错误原因清楚、每个规则可以单独复现。

全量 pipeline 验收仍然有价值，但它属于运行较慢的端到端检查，不应该代替小型业务规则测试。

### 6.4 当前项目的真实状态

pytest 已经安装，但当前没有 `tests/` 目录和测试文件。因此：

```powershell
uv run pytest -q
```

目前返回的是：

```text
no tests ran
```

这不代表测试通过，而是代表 pytest 没找到任何测试。正式 pytest 工作仍未完成。

### 6.5 你需要掌握到什么程度

- **了解：** pytest 是自动执行测试的框架，不是清洗工具。
- **会使用：** 能运行 `uv run pytest -q`，能区分 passed、failed 和 no tests ran。
- **会证明：** 能解释为什么小型人工样本测试和全量 pipeline 验收缺一不可。

---

## 7. 四者如何连在一起

```text
Notebook 中探索和确定规则
        ↓
生成 df_clean
        ↓
final_validation + assert 检查本次结果
        ↓
把规则迁移到 src/ingest.py
        ↓
完整重跑并比较两次输出，验证幂等性
        ↓
把关键规则写成 pytest，长期防止回归
```

这里的“回归”不是统计学 regression，而是指：以后修改代码时，把以前正确的功能意外改坏了。

---

## 8. 建议的复习顺序

不要从头硬读完整的 `ingest.py`。按以下顺序复习：

1. **先复述数据流**
   - 原始 CSV → `raw` → `df_clean` → Parquet + audit。

2. **重看 Notebook 的最终验收单元格**
   - 逐句解释 `len`、`isna`、`duplicated`、`isin`、`assert`。

3. **重看两次运行比较单元格**
   - 逐句解释 before、run、after、compare。

4. **只看 `ingest.py` 的三个入口**
   - `clean_loans`；
   - `run_pipeline`；
   - `if __name__ == "__main__"`。

5. **最后学习 pytest**
   - 先写一个只检查一个规则的小测试，不从全量测试开始。

---

## 9. 自测问题

如果下面问题能用自己的话回答，说明已经掌握本阶段的主干：

1. 为什么不直接修改原始 CSV？
2. `df_clean` 与原始 `df` 有什么区别？
3. 为什么 `dti_out_of_range` 不为 0，但 ingestion 仍然可以通过？
4. `display(final_validation)` 和 `assert` 的作用分别是什么？
5. 为什么两次程序都成功结束，仍不能直接证明幂等？
6. 为什么脚本运行成功还不能单独证明幂等性？
7. `clean_loans` 和 `run_pipeline` 各负责什么？
8. 为什么 `loan_status` 可以保留在 Parquet 中，却不能作为 PD 特征？
9. `pytest` 显示 `no tests ran` 是否代表测试通过？
10. 为什么 pytest 使用小型人工样本，而全量 CSV 另做端到端验收？

## 10. 现阶段最重要的一句话

> 昨天已经证明 pipeline 在当前数据上可以运行并产生合格、稳定的输出；接下来的学习目标，是让你能够解释这些检查为什么成立，并逐渐独立修改和测试小段规则。
