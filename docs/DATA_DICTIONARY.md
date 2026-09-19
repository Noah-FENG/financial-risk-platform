# LendingClub 数据字典

下面记录当前 `field_groups` 中的原始字段。`本地格式`来自本地 CSV 的实际取值；`fico_mid`不是原始字段，将在后续 feature engineering 阶段生成。

| 字段名 | 字段含义 | 类别 | 什么时候知道 | 项目用途 | PD模型泄漏 | 本地格式 |
|---|---|---|---|---|---|---|
| `id` | 贷款唯一编号 | loan key | 始终存在 | 主键、去重 | 否 | 数值样式的贷款 ID |
| `member_id` | 借款人编号 | loan key | 原始字段提供时 | 原始字段审计 | 否 | 本地数据中全为空；清洗时移除 |
| `loan_amnt` | 借款人申请的金额 | loan terms | 放款时 | 贷款规模分析 | 否 | 数值，USD |
| `funded_amnt` | 实际出资的贷款金额 | loan terms | 放款时 | exposure 参考 | 否 | 数值，USD |
| `funded_amnt_inv` | 投资者出资金额 | loan terms | 放款时 | 投资金额分析 | 否 | 数值，USD |
| `term` | 贷款期限 | loan terms | 放款时 | 36/60个月比较 | 否 | `36 months`、`60 months` |
| `issue_d` | 贷款发放月份 | timing | 放款时 | vintage分析 | 否 | `Dec-2015` |
| `int_rate` | 贷款年利率 | pricing | 放款时 | 定价分析 | 否 | `11.99`代表11.99% |
| `installment` | 每月计划还款额 | pricing | 放款时 | 还款结构分析 | 否 | 数值，USD/月 |
| `grade` | LendingClub大评级 | risk/pricing | 放款时 | Grade定价分析 | 否 | `A`–`G` |
| `sub_grade` | LendingClub细分评级 | risk/pricing | 放款时 | 更细的定价分析 | 否 | `A1`–`G5` |
| `annual_inc` | 借款人自报年收入 | borrower | 放款时 | 借款人分组、未来PD模型 | 否 | 数值，USD/年 |
| `emp_length` | 工作年限 | borrower | 放款时 | 借款人分组 | 否 | `10+ years`、`3 years`、`< 1 year` |
| `home_ownership` | 房屋所有权状态 | borrower | 放款时 | 借款人分组 | 否 | 分类字符串 |
| `verification_status` | 收入验证状态 | borrower | 放款时 | 风险分组 | 否 | 分类字符串 |
| `purpose` | 贷款用途 | borrower/loan | 放款时 | 贷款用途分组 | 否 | 分类字符串 |
| `addr_state` | 借款人所在州 | borrower | 放款时 | 地区分析 | 否 | 两位州代码 |
| `dti` | 债务收入比 | borrower/risk | 放款时 | 风险分组、未来PD模型 | 否 | 百分点，例如 `16.06`代表16.06% |
| `delinq_2yrs` | 过去两年逾期账户数 | credit history | 放款时 | 信用风险分组 | 否 | 数值计数 |
| `earliest_cr_line` | 最早信用记录月份 | credit history | 放款时 | 信用历史分析 | 否 | `Aug-2003` |
| `fico_range_low` | 发放时FICO区间下限 | credit risk | 放款时 | 信用风险分组 | 否 | 数值分数 |
| `fico_range_high` | 发放时FICO区间上限 | credit risk | 放款时 | 信用风险分组 | 否 | 数值分数 |
| `inq_last_6mths` | 最近六个月信用查询次数 | credit history | 放款时 | 信用风险分组 | 否 | 数值计数 |
| `open_acc` | 开放信用账户数量 | credit history | 放款时 | 信用风险分组 | 否 | 数值计数 |
| `pub_rec` | 公共信用记录数量 | credit history | 放款时 | 信用风险分组 | 否 | 数值计数 |
| `revol_bal` | 循环信用余额 | credit history | 放款时 | 借款人风险分析 | 否 | 数值，USD |
| `revol_util` | 循环信用使用率 | credit history | 放款时 | 借款人风险分析 | 否 | 百分点，例如 `29.7`代表29.7% |
| `total_acc` | 信用账户总数 | credit history | 放款时 | 信用历史分析 | 否 | 数值计数 |
| `pub_rec_bankruptcies` | 公共破产记录数量 | credit history | 放款时 | 信用风险分组 | 否 | 数值计数 |
| `loan_status` | 贷款当前或最终状态 | outcome | 放款后 | 定义贷款结果 | 是 | `Fully Paid`、`Current`、`Late (31-120 days)` |
| `out_prncp` | 尚未偿还本金 | outcome | 放款后 | 未偿本金分析 | 是 | 数值，USD |
| `total_pymnt` | 累计总还款金额 | outcome | 放款后 | 收入和回报分析 | 是 | 数值，USD |
| `total_rec_prncp` | 已收回本金 | outcome | 放款后 | 本金回收分析 | 是 | 数值，USD |
| `total_rec_int` | 已收回利息 | outcome | 放款后 | 利息收入分析 | 是 | 数值，USD |
| `total_rec_late_fee` | 已收取逾期费用 | outcome | 放款后 | 结果和费用分析 | 是 | 数值，USD |
| `recoveries` | 违约后的回收金额 | outcome | 放款后 | 损失计算 | 是 | 数值，USD |
| `collection_recovery_fee` | 回收相关费用 | outcome | 放款后 | 净损失计算 | 是 | 数值，USD |
| `last_pymnt_d` | 最近一次还款月份 | post-origination | 放款后 | 生命周期观察 | 是 | `Jan-2019` |
| `last_pymnt_amnt` | 最近一次还款金额 | post-origination | 放款后 | 生命周期观察 | 是 | 数值，USD |
| `next_pymnt_d` | 下一次计划还款月份 | post-origination | 放款后 | 生命周期观察 | 是 | 月份或空值 |
| `last_credit_pull_d` | 最近一次信用信息查询月份 | post-origination | 放款后 | 观察截止日期辅助判断 | 是 | `Mar-2019` |
| `last_fico_range_high` | 最近一次FICO区间上限 | post-origination | 放款后 | 历史结果观察 | 是 | 数值分数或空值 |
| `last_fico_range_low` | 最近一次FICO区间下限 | post-origination | 放款后 | 历史结果观察 | 是 | 数值分数或空值 |

## 后续派生字段

`fico_mid = (fico_range_low + fico_range_high) / 2` 不属于原始字段，也不在基础 ingestion 阶段生成。后续进入 feature engineering 后，再根据明确的特征定义创建。
