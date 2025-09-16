# ESIMULATOR

面向异构硬件（ONN/AMS）的数字电路数据流图（DFG）分析、Bind/Workset 级掩码优化与可视化平台。

核心流程：Verilog → DFG → Bind 级 AST 分析 → Workset 掩码与可融合关系 → 模拟退火优化 → 可视化 → AMS 生成与连通检查。

—

## 核心特性

- Bind 级 AST 分析：逐个 bind 表达式构建 AST，识别 Operator/Concat/Partselect/Branch/Terminal 等。
- Workset 掩码与可融合关系：为每个 bind 导出 `workset_order`/`workset_mask` 与 `fusable_adj`，并标记 `bind_has_branch`、`sources`、`operator_count`。
- 模拟退火（SA）在 Bind/Workset 级：以掩码为优化变量，支持邻域操作（flip/grow/shrink），在多目标成本下搜索最优。
- 成本模型贴合 ONN/AMS：综合 Area/Delay/Power/Interface，支持“优先模块数量与接口”的权重配置。
- 可视化支持回退：无 `networkx` 也可导出 DOT；若安装 `networkx`，则启用增强版布局和样式。
- AMS/RNM 脚手架与生成器：从 SA 结果自动生成 ONN/RNM 包装与顶层连接，便于快速连通检查与后续电气模型替换。

—

## 目录结构（节选）

```text
ESIMULATOR/
├── dfg_files/                     # 输入 DFG 文件
├── results/                       # 分析与优化输出（JSON/DOT/报告）
├── esimulator/                    # CLI 与内部模块
│   ├── cli/                       # analyze / visualize / batch / compare
│   └── visual/                    # 可视化导出（含无 networkx 回退）
├── src/
│   ├── analyzers/
│   │   └── dfg_linearity_corrector.py   # Bind/Workset 分析与掩码生成
│   └── simulated_annealing.py           # Bind/Workset 级 SA 优化
├── ams/
│   ├── models/                    # RNM 与电气模板（ideal_adc/dac 等）
│   ├── tb/                        # 连接顶层与测试平台（4004 示例）
│   └── build/                     # 由生成器输出的包装模块
├── tools/
│   └── generate_ams_from_sa.py    # 从 SA 结果生成 AMS 包装/连接文件
├── esimulator_cli.py              # 命令行入口
└── docs/                          # 文档
```

—

## 快速上手

1) 安装

```bash
pip install -e .
```

可选依赖：可视化增强需 `networkx`

```bash
pip install networkx
```

1) 运行完整流程（以 4004 为例）

```bash
python esimulator_cli.py batch --dfg-filename 4004_dfg.txt
```

对应输入文件应位于 `dfg_files/4004_dfg.txt`。

1) 单步运行

- 仅分析（生成 Bind/Workset 掩码与图）：

```bash
python esimulator_cli.py analyze --dfg-filename 4004_dfg.txt
```

- 仅可视化（生成 DOT，自动适配有/无 networkx）：

```bash
python esimulator_cli.py visualize --dfg-filename 4004_dfg.txt --out results
```

- 仅优化（在已有 bind 掩码基础上运行 SA）：

```bash
python esimulator_cli.py compare --dfg-filename 4004_dfg.txt
```

—

## 输出文件

- `results/4004_dfg_linearity_analysis.txt`：按 bind 的线性/非线性统计与原因小结。
- `results/4004_dfg_linearity_graph.json`：用于可视化/下游流程的图数据。
- `results/4004_dfg_bind_masks.json`：每个 bind 的 workset 顺序、掩码、可融合关系、分支与源列表等。
- `results/4004_dfg.dot`：DFG 视图（如启用 visualize）。
- `results/4004_bindmask_sa_best.json`：SA 最优结果，包含权重、度量与总成本。

—

## SA 成本模型与邻域

- 邻域操作：
  - flip：在某个 bind 的 workset 掩码位上 1↔0 翻转。
  - grow/shrink：沿 `fusable_adj` 在局部簇内扩张/收缩线性簇（受 `bind_has_branch` 约束）。
- 度量项（示例）：
  - L：线性 workset 总数
  - E：非线性 workset 总数
  - C：近似模块数（线性簇数量）
  - IFACE：跨域/跨簇接口度量
- 成本（示例可调）：
  - Area = a1*L − a2*E
  - Delay = d1*C
  - Power = p1*L
  - Interface = i1*IFACE
  - Total = wi*Area + wz*Delay + w3*Power + wa*Interface

针对“优先模块数量与接口”的需求，可增大 `wz` 与 `wa`，并适当调节 `a1/a2`、`d1/p1/i1`。

—

## AMS/RNM 生成与连通检查

从 SA 结果快速生成 RNM 包装与连接顶层，用于连通性验证：

```bash
python tools/generate_ams_from_sa.py \
  --sa results/4004_bindmask_sa_best.json \
  --out ams/build \
  --top ams/tb/ams_top_bind_connect.sv \
  --backend lut
```

生成物：

- `ams/build/bind_*.sv`：按 bind/workset 生成的包装模块（可连接到 ONN/RNM 模块）。
- `ams/tb/ams_top_bind_connect.sv`：连接顶层（示例已提供，亦可自定义）。

示例 RNM/电气模型位于 `ams/models/`，包含 `ideal_adc.sv`、`ideal_dac.sv`、`onn_linear_block.sv` 等；后续可替换为 Verilog‑AMS 电气模型（`*.va`）。

—

## 可视化与依赖

- 默认不强制依赖 `networkx`。
- 若未安装 `networkx`，仍可导出基础 DOT；安装后可启用增强版样式与布局。

安装命令：

```bash
pip install networkx
```

—

## 已知限制

- DFG 输入需由外部工具生成（本仓库不包含 Verilog→DFG 转换工具链）。
- SA 成本模型与度量可按目标硬件继续校准；文档中的权重为示例配置。
- 可视化当前以 DOT 为主；若需 PNG/SVG 输出，请使用 Graphviz：`dot -Tpng results/xxx.dot -o results/xxx.png`。

—

## 许可证

MIT License
