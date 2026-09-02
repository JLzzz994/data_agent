# 慧策·慧经营 AI 智能问数模块

该分支把原始 data_agent 从通用销售 Demo 改造成电商 SaaS / ERP / WMS 经营分析场景，目标是支持产品、运营、实施顾问和商家服务团队用自然语言查询订单、商品、店铺、库存、采购、仓储、履约和售后数据。

> 分支定位：面试可讲、代码可继续演进的业务化版本。conf/meta_config.yaml 使用演示 Schema，不代表慧策线上真实表名。

## 业务问题示例

- 最近 30 天各店铺支付金额、退款金额和退款率是多少？
- 本月各品牌 GMV、销量、毛利和毛利率排名。
- 当前各仓库可用库存最低的 20 个商品。
- 最近 7 天退款率明显高于整体均值的商品有哪些？
- 上季度各平台采购金额、采购量与销售量对比。

完整演示问题见 demo/queries.md，多租户样例数据见 demo/huijingying_demo.sql。

## 12 节点 LangGraph

1. extract_keywords
2. recall_column
3. recall_metric
4. recall_value
5. merge_retrieved_info
6. filter_metric
7. filter_table
8. add_extra_context
9. generate_sql
10. validate_sql
11. correct_sql
12. execute_sql

字段、指标、枚举值分别召回后合并元数据，并补齐主外键和示例值。SQL 生成时注入当前日期/时间、指标定义、数据库方言和版本。

## Milvus + Elasticsearch 三路召回

- 字段召回：字段名、描述、别名向量化后写入 Milvus collection huice_data_agent_column。
- 指标召回：指标名、描述、别名向量化后写入 Milvus collection huice_data_agent_metric。
- 枚举值召回：店铺、平台、品牌、类目、订单状态、售后类型等离散值写入 Elasticsearch。
- Embedding：BAAI/bge-large-zh-v1.5。

原项目的 Qdrant client、repository 和依赖已经从该分支删除。

## SQL 校验与纠错

validate_sql 保持一个 LangGraph 节点，但内部包含：

1. SQLGlot 静态安全校验：仅允许单条 SELECT/CTE，拒绝 DML、DDL、多语句和会话命令。
2. MySQL EXPLAIN：在真实 Schema 下检查表、字段、函数、JOIN 与可执行性，并设置查询超时。
3. LLM 语义一致性校验：校验时间范围、指标口径、聚合方式、GROUP BY 粒度、状态过滤和 JOIN 是否与用户问题一致。
4. 权限 SQL 注入后再次 EXPLAIN，确认安全改写后的 SQL 在真实库中仍可执行。

失败会回到 correct_sql，最多自动纠错 3 轮；每次纠错后重新进入完整校验，达到上限后拒绝执行。

## 租户 / 店铺硬权限

权限不交给 Prompt，也不允许大模型自己拼 tenant_id。

API 从可信认证网关接收：

- X-Internal-Tenant-Id
- X-Internal-Shop-Ids
- X-Internal-Gateway-Token

服务端用 INTERNAL_GATEWAY_TOKEN 验证内部调用上下文，然后生成 AccessScope。

SQL 通过业务语义校验后，scoped_sql.py 使用 SQLGlot AST 把每个受控物理表替换成安全子查询。例如概念上：

    fact_trade_order o

会变成：

    (
      SELECT *
      FROM fact_trade_order
      WHERE tenant_id = <当前租户>
        AND shop_id IN (<当前用户允许店铺>)
    ) o

因此即使自然语言里要求“查看其他租户”或模型遗漏权限条件，也不能改变执行范围。

tenant_id / shop_id 等安全字段只存在于物理 DW 和权限层，不暴露在 conf/meta_config.yaml 的 LLM 语义 Schema 中。

## 其他数据安全

- DW 使用只读账号/只读副本。
- 查询结果默认最多返回 500 行，API 最大允许 1000 行。
- MySQL 查询设置 MAX_EXECUTION_TIME。
- 手机、邮箱、姓名、收货地址等常见字段统一脱敏。
- 未配置 TABLE_ACCESS_POLICY 的物理表默认拒绝访问。

## 模型

默认按 Qwen2.5-14B-Instruct + vLLM OpenAI Compatible API 配置。

## Demo

先将 demo/huijingying_demo.sql 导入 DW 数据库。该数据集包含：

- tenant_hc_001：天猫店 + 京东店。
- tenant_other_001：故意放入极大订单、库存、采购和退款值的其他租户。

这样可以直接验证跨租户数据不会因为金额更大而泄露进聚合结果。

然后构建元数据：

    python -m app.scripts.build_meta_knowledge -c conf/meta_config.yaml

调用 API 前配置：

    INTERNAL_GATEWAY_TOKEN=<内部网关共享凭证>

示例权限上下文：

    X-Internal-Tenant-Id: tenant_hc_001
    X-Internal-Shop-Ids: shop_tmall_001,shop_jd_001
    X-Internal-Gateway-Token: <与服务端一致的内部凭证>

## 固定 500 条 Text2SQL 评测

该分支现在包含可复现的固定评测集：

- 50 个业务语义原型 × 10 种自然语言表达 = 500 条。
- 覆盖销售、毛利、库存、采购、售后。
- 每条问题固定日期，避免“最近 30 天”随运行时间漂移。
- 每条样本包含 gold SQL、难度、期望表/指标和租户/店铺权限。
- 主指标采用 execution accuracy，而不是 SQL 字符串完全一致。
- 自动输出 JSON / CSV / Markdown 报告和 bad case 分类。
- 评测模式可额外记录选表、选指标、初始 SQL 和每轮纠错 SQL。

评测入口：

    python -m evaluation.run_evaluation --target-accuracy 0.88

冒烟可先执行：

    python -m evaluation.run_evaluation --limit 20

详细说明见 evaluation/README.md。

注意：88% 目前是评测目标，不是代码中写死的结果；只有在当前模型、检索服务和 Demo DW 上实际跑完 500 条后，报告中的 execution accuracy 才能作为真实准确率。

## 与简历口径对应

该分支已经对齐：

- 12 节点 LangGraph。
- 字段 / 指标 / 枚举值三路召回（Milvus + Elasticsearch）。
- 主外键和示例值补齐。
- 指标口径、当前时间、数据库方言与版本注入。
- SQLGlot AST / 静态安全校验。
- MySQL EXPLAIN 可执行性校验。
- LLM 业务语义一致性校验。
- 最多 3 轮自动纠错并重新校验。
- 租户 / 店铺硬权限。
- 只读执行、限行、超时、脱敏与 SSE。

## 本地依赖同步

uv.lock 已随当前 pyproject.toml 刷新，并由 CI 使用 `uv lock --check` 校验。锁文件已包含 SQLGlot 与 PyMilvus，且不再包含 qdrant-client。

首次切换分支可直接执行：

    uv sync --frozen

需要主动升级依赖版本时，再执行 `uv lock --upgrade` 并提交新的锁文件。
