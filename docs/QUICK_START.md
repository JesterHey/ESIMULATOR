# 快速上手（Quick Start）

本指南带你用最少命令把 DFG 做成“带 Verilog 行号与掩码的 Bind 级 JSON/报告”，并可选生成 DOT 和信号覆盖对比。

## 1. 环境准备

- Python 3.10+
- 安装基础依赖：

```bash
pip install -e .
```

- 可选：安装可视化增强（`networkx`）

```bash
pip install networkx
```

## 2. 准备 DFG 文件

- 使用外部工具将 Verilog 转为 DFG（项目不包含转换链），将 `xxx_dfg.txt` 放入 `dfg_files/`。
- 示例内容：

```text
bind dff_2_q assign {1'd0,dff_1_q[3:1]};
bind dff_3_q assign {1'd0,dff_2_q[3:1]};
bind dff_4_q assign {1'd0,dff_3_q[3:1]};
```

## 3. 最小可复现（推荐）

分析 + 导出报告/JSON（建议提供 Verilog 以便标注行号）：

```bash
python esimulator_cli.py analyze dfg_files/4004_dfg.txt \
  --output results \
  --linearity-mode arith \
  --verilog-file verilog_files/4004.v \
  --module-prefix ""
```

## 4. 其他命令（可选）

- 仅分析：

```bash
python esimulator_cli.py analyze dfg_files/4004_dfg.txt
```

- 仅优化（需已有 `..._bind_masks.json`）：

```bash
python esimulator_cli.py compare-signals dfg_files/4004_dfg.txt \
  --verilog-file verilog_files/4004.v \
  --module-prefix "" \
  --output results
```

- 仅可视化（自动适配是否安装 networkx）：

```bash
python esimulator_cli.py visualize dfg_files/4004_dfg.txt --output results
```

## 5. 查看输出

- `results/4004_dfg_linearity_analysis.txt`
- `results/4004_dfg_linearity_graph.json`
- `results/4004_dfg_bind_masks.json`
- `results/4004_dfg.dot`（若运行 visualize）
更多字段定义与模块说明请参阅 `docs/MODULE_DOC.md`。

