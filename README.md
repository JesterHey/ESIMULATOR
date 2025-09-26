# ESIMULATOR

基于 Pyverilog 产出的 DFG 进行“Bind 级线性分析与标注”的小型工具集：
从 Verilog 与 DFG 出发，产出带有 Verilog 行号映射、AST 顺序与掩码、源/目的地定位等的结构化 JSON 与文本报告，并支持基础可视化与信号覆盖对比。


—

## 工作流程概览

Verilog + DFG → Bind 级 AST 分析与线性标注 → 报告/JSON → 可视化（可选）→ 全量信号覆盖对比（可选）。

工具要点：

- Bind 级 AST 构建：识别 Operator / Concat / Partselect / Branch / Terminal。
- 线性判定：支持算术域（arith）与 GF(2) 两种模式；可按需过滤“无可掩码单元”的平凡绑定。
- 掩码与邻接：导出 workset 顺序与掩码、可融合邻接（fusable_adj）、人类可读标签。
- Verilog 行号：为 bind 的目标与各源标注对应 Verilog 行号；可传入模块前缀以匹配命名空间（如 `alu.`）。
- 覆盖验证：提供“compare-signals”对比 Verilog/DFG/绑定 的覆盖与行号完整性。

—

## 目录结构（节选）

```text
ESIMULATOR/
├── dfg_files/                     # 输入 DFG 文件
├── verilog_files/                 # 示例 Verilog 文件
├── results/                       # 分析与可视化输出（JSON/DOT/报告）
├── esimulator/
│   ├── cli/                       # analyze / visualize / batch / compare / compare-signals
│   ├── core/                      # dfg_parser / linearity_analyzer / report_generator
│   ├── utils/                     # verilog_parser（行号映射）
│   └── visual/                    # 可视化导出
├── src/
│   └── analyzers/
│       └── dfg_linearity_corrector.py   # Bind 级增强分析/导出
├── esimulator_cli.py              # 命令行入口
└── docs/                          # 文档
```

—

## 安装

```bash
pip install -e .
```

可选依赖：可视化增强需要 `networkx`

```bash
pip install networkx
```

—

## 常用命令

以下命令均在仓库根目录执行。

1. 进行分析并导出报告/JSON（推荐同时传入 Verilog 文件以产生行号映射）

```bash
python esimulator_cli.py analyze dfg_files/4004_dfg.txt \
  --output results \
  --linearity-mode arith \
  --verilog-file verilog_files/4004.v \
  --module-prefix ""
```

生成内容见“输出物”一节。

1. 全量信号覆盖与行号完整性对比（可选）

```bash
python esimulator_cli.py compare-signals dfg_files/4004_dfg.txt \
  --verilog-file verilog_files/4004.v \
  --module-prefix "" \
  --output results
```

1. 可视化导出（DOT 等；安装 `networkx` 可增强样式）

```bash
python esimulator_cli.py visualize dfg_files/4004_dfg.txt --output results/visualizations
```

1. 批量模式（对目录下的所有 DFG 执行 analyze）

```bash
python esimulator_cli.py batch dfg_files --output results
```

备注：`compare` 子命令仅用于旧方法对比打印，非主流程；原“模拟退火/合并优化”路径已暂缓，不在文档主线中展开。

—

## 输出物（以 4004 为例）

- 文本报告：`results/4004_dfg_linearity_analysis.txt`
- 图数据：`results/4004_dfg_linearity_graph.json`（可视化/下游）
- Bind 级 JSON：`results/4004_dfg_bind_masks.json`
  - 关键字段：
    - `dest` / `sources`
    - `operator_order` 与 `operator_mask`（或 `workset_order` / `workset_mask`）
    - `fusable_adj`、`operator_types`、`bind_kind`、`maskable_count`、`is_trivial`
    - `dest_location` 与 `source_locations`（Verilog 行号）
    - `verilog_file`、`linearity_mode`、`workset_labels`
- 信号覆盖对比：`results/4004_dfg_signal_compare.txt` 与 `.json`
- 可视化 DOT：`results/4004_dfg.dot`（若运行 visualize）

—

## 已知限制与注意事项

- DFG 输入由上游（如基于 Pyverilog 的流程）生成，本仓库不包含 Verilog→DFG 的转换实现。
- 行号映射采用轻量级正则解析：支持常见的声明/赋值形式与多行声明；模块 ANSI 风格端口行（无分号）可能不计入映射。
- GF(2) 与算术域的线性定义不同，选择前请确认期望的代数域；默认使用 `arith`。
- 若未安装 `networkx`，可视化仍可导出基础 DOT；增强样式需额外安装。

—

## 许可证

MIT License
