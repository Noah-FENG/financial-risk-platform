# 项目状态记录

**更新日期：** 2026-09-19  
**当前阶段：** Phase 1 — L0 Foundation 已完成  
**下一阶段：** Phase 2 — L1 Analytics Data Model

## Phase 1 完成内容

### 数据理解与清洗

- 已完成43个核心原始字段的数据字典和可用时点分类。
- 已建立清洗与验证规则。
- 原始 CSV 保持不变。
- 2,260,701 条原始记录中移除33条 footer，保留2,260,668笔有效贷款。
- 有效贷款 ID 唯一，`issue_d` 完整，期限均为36或60个月。
- 数据异常保留原始值，并通过单独 flag 标记。

### Ingestion

- `src/ingest.py` 已完成 CSV 到标准化 Parquet 的正式流程。
- 输入和输出路径可以作为参数传入。
- 文件级测试使用 pytest `tmp_path`，不会覆盖正式数据。
- 相同小样本连续运行两次，Parquet 和 cleaning audit 完全一致。

正式输出：

- `data/processed/accepted_loans_normalized.parquet`
- `outcomes/cleaning_audit.csv`

### 月度分区

- 已按 `issue_month` 建立139个月度分区。
- 覆盖范围为 `2007-06` 至 `2018-12`。
- 分区总行数为2,260,668。
- 无缺失月份、月份混入或重复贷款 ID。

分区形式：

```text
data/batches/issue_month=YYYY-MM/loans.parquet