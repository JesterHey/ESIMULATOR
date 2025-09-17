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
# 默认后端：ONN（可能依赖 RNM/Verilog-A，不一定适配纯数字仿真）
python tools/generate_ams_from_sa.py \
  --sa results/4004_bindmask_sa_best.json \
  --out ams/build \
  --top ams/tb/ams_top_bind_connect.sv

# 纯数字路径：LUT 后端（推荐，保证传统 Verilog 仿真器可跑通）
python tools/generate_ams_from_sa.py \
  --sa results/4004_bindmask_sa_best.json \
  --out ams/build \
  --top ams/tb/ams_top_bind_connect.sv \
  --backend lut
```

`ams/models/` 下提供 RNM 与电气模板，可替换/扩展用于你的仿真环境。

## 6. 仿真校验（LUT 纯数字）

本节提供一个可重复的“基线 vs LUT 包装”一致性校验，使用 SystemVerilog（Icarus Verilog 等传统仿真器）。

前置：已在第 5 节用 `--backend lut` 生成包装与连接顶层。

1. 编译并运行基线仿真（不含包装）

```bash
iverilog -g2012 -o sim_base.out \
  verilog_files/4004.v \
  ams/tb/tb_4004_baseline.sv && \
vvp sim_base.out +seed=1 | tee ams/out_base.txt
```

1. 编译并运行 LUT 包装仿真

```bash
iverilog -g2012 -o sim_lut.out \
  verilog_files/4004.v \
  ams/build/*.sv \
  ams/models/lut_block.sv \
  ams/tb/tb_4004_ams.sv && \
vvp sim_lut.out +seed=1 | tee ams/out_lut.txt
```

1. 输出对比与归档

```bash
mkdir -p results
diff -u ams/out_base.txt ams/out_lut.txt > results/baseline_vs_lut.diff.txt || true
if cmp -s ams/out_base.txt ams/out_lut.txt; then
  echo "No differences" > results/baseline_vs_lut.diff.txt
fi
cp ams/out_base.txt results/baseline_out.txt
cp ams/out_lut.txt results/lut_out.txt
```

预期：两侧日志应完全一致，唯一差异可能是 `$finish` 打印的 testbench 文件名不同（基线 vs LUT）。

提示：以上步骤已封装为 VS Code 任务，可在命令面板运行：

- `Generate AMS from SA (4004, LUT backend)`
- `Compile TB 4004 Baseline (iverilog)`
- `Compile TB 4004 LUT (iverilog)`
- `Save Diff to results`

## 7. 查看输出

- `results/4004_dfg_linearity_analysis.txt`
- `results/4004_dfg_linearity_graph.json`
- `results/4004_dfg_bind_masks.json`
- `results/4004_bindmask_sa_best.json`
- `results/4004_dfg.dot`（若运行 visualize）

LUT 校验相关：

- `results/baseline_out.txt`（基线日志）
- `results/lut_out.txt`（LUT 日志）
- `results/baseline_vs_lut.diff.txt`（差异报告；一致时为 “No differences”）

更多细节请参阅 `docs/MODULE_DOC.md`。

