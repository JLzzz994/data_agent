# 慧经营 Text2SQL 固定评测

## 目标

该目录把“SQL 执行准确率”从简历描述变成可复现的工程评测。

当前固定集：

- 500 条自然语言问题。
- 50 个业务语义原型。
- 每个语义原型 10 种表达。
- 使用明确日期，不使用“最近 30 天 / 本月”等会随运行日期漂移的相对时间。
- 每条样本包含 gold SQL、业务分类、难度、期望表、期望指标和租户/店铺权限范围。

`fixed_500.spec.json` 是语义源文件，`fixed_500.jsonl` 是提交到仓库的固定快照。CI 会验证二者完全一致。

## 为什么不是比较 SQL 字符串

Text2SQL 可能存在多种等价写法，例如 JOIN 顺序、子查询、别名和过滤表达式不同，但执行结果完全一致。

因此主指标使用 **execution accuracy**：

1. 在同一个 Demo DW 和同一租户/店铺权限范围下执行 gold SQL。
2. 调用 Data Agent 生成并执行预测 SQL。
3. 对结果列、行数和值做规范化。
4. 两边执行结果等价才记为通过。

数值会统一处理 Decimal / JSON 数字字符串差异；默认忽略结果行顺序，但不会忽略列和值差异。

## 运行

先启动 MySQL、Milvus、Elasticsearch、Embedding、vLLM 和 Data Agent，并导入 Demo 数据、构建元数据。

评测服务建议开启：

    DATA_AGENT_EVAL_TRACE=1

普通业务环境不要开启这个变量。开启后 SSE 会额外输出评测 trace，包括过滤后的表/字段、过滤后的指标、初始生成 SQL、每一轮纠错 SQL。

然后运行：

    python -m evaluation.run_evaluation \
      --api-url http://127.0.0.1:8000/api/query \
      --target-accuracy 0.88

默认使用环境变量 `INTERNAL_GATEWAY_TOKEN`。

冒烟：

    python -m evaluation.run_evaluation --limit 20

如果希望低于 88% 时命令直接失败：

    python -m evaluation.run_evaluation \
      --target-accuracy 0.88 \
      --enforce-target

## 输出

默认写到：

    reports/evaluation/evaluation.json
    reports/evaluation/evaluation.csv
    reports/evaluation/evaluation.md

报告包含总 execution accuracy、各业务分类准确率、难度准确率、平均延迟、纠错轮数分布、bad case 分类，以及每条问题的初始 SQL / 最终 SQL / 失败原因。

## Bad case 分类

- `schema_linking_miss`：过滤后的表缺少 gold 所需表。
- `metric_recall_miss`：过滤后的指标缺少 gold 所需指标。
- `retrieval_or_schema_linking_error`：召回/合并/过滤节点异常。
- `sql_generation_error`：首次 SQL 生成失败。
- `sql_correction_error`：纠错节点失败。
- `semantic_validation_rejected`：LLM 语义一致性校验拒绝。
- `static_explain_or_validation_error`：SQLGlot / EXPLAIN / 其他校验失败。
- `access_control_rejected`：确定性租户/店铺权限拒绝。
- `sql_execution_error`：SQL 实际执行失败。
- `row_count_mismatch`：结果行数不同。
- `column_mismatch`：结果列不同。
- `value_mismatch`：结果值不同。
- `transport_timeout` / `transport_error`：API 网络层失败。

## 关于 88%

仓库现在提供的是**可复现 88% 目标的评测基础设施**，不是预先写死“准确率 = 88%”。

只有实际启动当前模型、检索服务和数据库后跑完 500 条，报告中的 execution accuracy 才是可以对外陈述的真实结果。
