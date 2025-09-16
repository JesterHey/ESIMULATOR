# 模块说明

本文件说明三大模块：分析器（Bind/Workset 级）、优化器（SA）、可视化与生成器（AMS/RNM）。

—

## 1) 分析器 `src/analyzers/dfg_linearity_corrector.py`

职责：将 `dfg_files/*.txt` 中的 bind 表达式解析为 AST，抽取 Workset 并打上线性掩码，导出可融合关系和上下文信息。

输出（列表，元素为每个 bind）：

```json
{
  "bind_index": 0,
  "bind_statement": "...",
  "workset_order": ["ADD_0", "CONCAT_1", "PSL_2"],
  "workset_mask": [1, 1, 0],
  "fusable_adj": {"ADD_0": ["CONCAT_1"]},
  "bind_has_branch": false,
  "sources": ["a", "b"],
  "operator_count": 1
}
```

并导出：

- `results/*_linearity_analysis.txt`（统计摘要）
- `results/*_linearity_graph.json`（用于可视化/下游）
- `results/*_bind_masks.json`（供 SA 使用）

—

## 2) 优化器 `src/simulated_annealing.py`

职责：读取 `*_bind_masks.json`，在 Bind/Workset 掩码空间搜索最优，目标是综合 Area/Delay/Power/Interface 最小。

邻域与度量：

- 邻域 flip/grow/shrink；分支限制由 `bind_has_branch` 约束；融合关系参照 `fusable_adj`。
- 统计 L/E/C/IFACE 等度量，成本示例：
  - Area = a1*L − a2*E
  - Delay = d1*C
  - Power = p1*L
  - Interface = i1*IFACE
  - Total = wi*Area + wz*Delay + w3*Power + wa*Interface

输出：`results/*_bindmask_sa_best.json`，包含权重、度量与总成本，以及最优掩码集合。

—

## 3) 可视化与生成器

可视化：

- `esimulator/visual` 提供 `visualize` 命令的实现：
  - 默认从 `results/*_linearity_graph.json` 读取图。
  - 无 `networkx` 也能导出 DOT（降级回退）。
  - 安装 `networkx` 启用增强版布局与样式。

AMS 生成器：

- `tools/generate_ams_from_sa.py` 读取 SA 最优结果，生成：
  - `ams/build/bind_*.sv` 包装模块
  - `ams/tb/ams_top_bind_connect.sv` 连接顶层
  - RNM/电气模板位于 `ams/models/`

—

## 4) 命令行 `esimulator_cli.py`

- `analyze`：解析 bind，导出图与掩码
- `visualize`：输出 DOT（自动回退）
- `compare`：运行 SA（基于已有掩码）
- `batch`：analyze → compare → 可选 visualize

示例：

```bash
python esimulator_cli.py analyze --dfg-filename 4004_dfg.txt
python esimulator_cli.py compare --dfg-filename 4004_dfg.txt
python esimulator_cli.py visualize --dfg-filename 4004_dfg.txt --out results
```

—

## 5) 扩展与注意

- 线性规则与 Workset 定义可在分析器中扩展（含 concat/partselect）。
- SA 权重可按“优先模块数量与接口”进行调优，见 README。
- DFG 输入需外部工具生成；可视化导出为 DOT，PNG/SVG 需自装 Graphviz。

