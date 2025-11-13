# 模块说明（Module Doc）

本文件聚焦当前主线能力：DFG/Bind 级线性分析与标注、报告与 JSON 导出、可视化、以及“全量信号覆盖对比”。
—

## 1) 分析器（CorrectedLinearityAnalyzer）

文件：`src/analyzers/dfg_linearity_corrector.py`

### 职责

- 解析 DFG（S-expression 风格）为 Bind 级 AST，兼容 Terminal/Operator/Concat/Partselect/Branch 等节点。
- 依据算术域（arith）或 GF(2) 进行线性性判定并生成掩码。
- 汇总 Workset 顺序、可融合邻接、操作符类型集合、分支与是否平凡等元信息。
- 若提供 Verilog 文件与模块前缀，补充绑定目标与源的行号映射（dest_location/source_locations）。
- 覆盖补全：将仅在 Verilog 中出现且参与绑定的信号，生成“合成条目”，用于 compare-signals 覆盖分析。

核心输出（按 bind，一条记录一个字典，字段可能随模式略有差异）：

- `dest`: 绑定目标信号名
- `sources`: 源信号名数组（常量以 `CONST(...)` 表示）
- `operator_order` 与 `operator_mask`（或 `workset_order` / `workset_mask`）
- `fusable_adj`: 可融合邻接边列表
- `operator_types`: 本绑定中出现过的运算符去重集合
- `bind_kind`: 表达式类别（如 assign/unary/concat/partselect/branch）
- `maskable_count`: 可置 1 的掩码位数量
- `is_trivial`: 是否为“无可掩码单元”的平凡绑定
- `dest_location`: 目标在 Verilog 中的行号（存在时）
- `source_locations`: 各源在 Verilog 中的行号（存在时；端口行可能为空）
- `verilog_file`, `linearity_mode`, `workset_labels`（可读标签，便于 UI）

—

## 2) 报告与导出（ReportGenerator）

文件：`esimulator/core/report_generator.py`

### 功能

- 文本报告（`*_linearity_analysis.txt`）：总体统计、类型与复杂度分布、非线性原因、逐信号结论。
- 图数据（`*_linearity_graph.json`）：`{ nodes, edges }`，节点含 is_linear/reason/operators 等，边来自 Terminal 依赖。
- Bind JSON（`*_dfg_bind_masks.json`）：封装第 1 节的绑定级数组，供外部消费与可视化。

调用示例：

```python
from esimulator.core.report_generator import ReportGenerator

report = ReportGenerator("results")
graph_path = report.generate_graph_json(analysis_result, dfg_file, "4004_dfg_linearity_graph.json")
bind_path = report.generate_bind_masks_json(
    analysis_result, dfg_file, "4004_dfg_bind_masks.json",
    linearity_mode="arith", omit_trivial=False,
    include_human_labels=True,
    verilog_file="verilog_files/4004.v", module_prefix=""
)
```

—

## 3) Verilog 行号解析器（verilog_parser）

文件：`esimulator/utils/verilog_parser.py`

### 说明

- 通过正则解析常见 `input/output/reg/wire/assign` 的目标名，支持多行声明与逗号分隔（忽略大括号/括号内逗号）。
- 返回 `dict[str,int]` 的首次出现行号映射，用于绑定记录补充 `dest_location`/`source_locations`。
- ANSI 风格端口（无分号）目前可能不记行号；这不影响目标行号与大多数源的标注。

—

## 4) 命令与参数（CLI）

入口：`esimulator_cli.py`

- `analyze <dfg_file>`：执行分析与导出报告/JSON
  - `--output/-o` 输出目录（默认 `results`）
  - `--linearity-mode {arith,gf2}` 代数域（默认 arith）
  - `--omit-trivial` 省略平凡绑定
  - `--verilog-file` Verilog 文件（用于行号）
  - `--module-prefix` 模块前缀（如 `alu.`）

- `compare-signals <dfg_file> --verilog-file <v> [--module-prefix <p>]`：
  - 生成 `<stem>_signal_compare.txt/.json`，核对覆盖范围、缺失行号等。

- `visualize <dfg_file>`：导出 DOT/HTML（无 networkx 亦可）

- `batch <dir>`：对目录内所有 DFG 运行 analyze

—

## 5) 注意与扩展

- DFG 输入需由外部工具生成；本项目提供后续分析与标注能力。
- GF(2) 与 arith 的线性定义不同，务必按目标使用选择参数。
- 若需要将模块端口行也标注行号，可扩展 verilog_parser 的 ANSI 端口解析；当前工具链默认允许端口源的行号为空。

