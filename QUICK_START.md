# ESIMULATOR 快速开始文档

本快速开始文档介绍如何使用本项目处理 Verilog 文件并生成 DFG 分析报告。

## 1. 准备工作

- **环境要求**：确保安装 Python 3.10+。
- **依赖工具**：
  - [pyverilog](https://github.com/PyHDI/pyverilog)（用于解析 Verilog 文件并生成 DFG 文本）。
  - 项目内其他 Python 环境依赖（详见 `pyproject.toml`）。

## 2. 使用 pyverilog 处理 Verilog 输入

1. 将待分析的 Verilog 文件放置于 `verilog_files/` 目录内（例如 `verilog_files/4004.v`）。
2. 使用 pyverilog 的命令行工具解析 Verilog 文件，并生成对应的 DFG 文本文件。例如：

```sh
pyverilog_ast --input verilog_files/4004.v --output dfg_files/4004_dfg.txt
```

*注意：实际的命令行参数请参考 pyverilog 的文档。*

## 3. 生成线性分析报告

1. 确定 DFG 文本文件已经生成（通常位于 `dfg_files/` 目录，例如 `dfg_files/4004_dfg.txt`）。
1. 运行项目内的线性分析模块 `dfg_linearity_corrector.py` 来处理 DFG 文件并生成分析报告。执行如下命令：

```sh
python src/analyzers/dfg_linearity_corrector.py
```

1. 运行完成后，分析报告将保存在 `results/` 目录（例如 `results/4004_dfg_linearity_analysis.txt`）。

## 4. 分析结果

- 报告中会统计所有信号表达式的总数、线性表达式和非线性表达式的比例。
- 每个信号的线性/非线性判定结果及触发原因也会被详细列出。

## 5. 其他注意事项

- 请确保 pyverilog 工具已正确安装并配置在你的系统路径中。
- 根据项目需求，`dfg_linearity_corrector.py` 中的线性/非线性判定策略可以进行调整。
- 如果报告结果与预期不符，可检查 Verilog 文件、DFG 生成过程以及分析脚本的日志输出。

## 6. 文件结构参考

- **Verilog 输入**：`verilog_files/`
- **DFG 文件**：`dfg_files/`
- **线性分析脚本**：`src/analyzers/dfg_linearity_corrector.py`
- **分析报告**：`results/`

按照以上步骤，你可以快速上手本项目，实现从 Verilog 输入到 DFG 线性分析报告的整个流程。
