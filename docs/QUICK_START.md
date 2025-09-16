# 快速上手

本指南引导你从 DFG 文件到 SA 优化与 AMS 生成的端到端流程。

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

## 3. 一键运行（推荐）

```bash
python esimulator_cli.py batch --dfg-filename 4004_dfg.txt
```

执行内容：

1. 分析并生成 Bind/Workset 掩码与图（写入 `results/`）。
2. 运行 SA 优化，产出 `..._bindmask_sa_best.json`。

## 4. 单步命令（可选）

- 仅分析：

```bash
python esimulator_cli.py analyze --dfg-filename 4004_dfg.txt
```

- 仅优化（需已有 `..._bind_masks.json`）：

```bash
python esimulator_cli.py compare --dfg-filename 4004_dfg.txt
```

- 仅可视化（自动适配是否安装 networkx）：

```bash
python esimulator_cli.py visualize --dfg-filename 4004_dfg.txt --out results
```

## 5. AMS/RNM 生成与连通检查（可选）

从 SA 最优结果生成包装与顶层连接：

```bash
python tools/generate_ams_from_sa.py \
  --sa results/4004_bindmask_sa_best.json \
  --out ams/build \
  --top ams/tb/ams_top_bind_connect.sv
```

`ams/models/` 下提供 RNM 与电气模板，可替换/扩展用于你的仿真环境。

## 6. 查看输出

- `results/4004_dfg_linearity_analysis.txt`
- `results/4004_dfg_linearity_graph.json`
- `results/4004_dfg_bind_masks.json`
- `results/4004_bindmask_sa_best.json`
- `results/4004_dfg.dot`（若运行 visualize）

更多细节请参阅 `docs/MODULE_DOC.md`。

