# ESIMULATOR 快速上手指南

本指南将引导您完成从准备 DFG（数据流图）文件到运行完整分析与优化流程的所有步骤。

## 1. 环境准备

- **Python 环境**: 确保您已安装 Python 3.10 或更高版本。
- **安装依赖**: 项目使用 `pyproject.toml` 管理依赖。请在项目根目录下运行以下命令进行安装：
  ```bash
  pip install -e .
  ```
  此命令会安装包括 `lark` (用于AST解析) 和 `click` (用于命令行界面) 在内的所有必要库。

## 2. 准备 DFG 文件

- **获取 DFG**: 本项目的输入是 DFG 格式的文本文件。您需要使用 Yosys、Pyverilog 等外部工具将您的 Verilog/SystemVerilog 源代码转换为 DFG。
- **存放位置**: 将生成的 DFG 文件（例如 `4004_dfg.txt`）放置在项目根目录下的 `dfg_files/` 文件夹中。

DFG 文件内容示例：
```
...
bind dff_2_q assign {1'd0,dff_1_q[3:1]};
bind dff_3_q assign {1'd0,dff_2_q[3:1]};
bind dff_4_q assign {1'd0,dff_3_q[3:1]};
...
```

## 3. 运行完整流程 (推荐)

我们提供了一个命令行工具 `esimulator_cli.py` 来一键执行完整的分析和优化流程。

- **命令格式**:
  ```bash
  python esimulator_cli.py batch --dfg-filename <your_dfg_file.txt>
  ```

- **示例**:
  假设您要处理 `dfg_files/4004_dfg.txt`，请运行：
  ```bash
  python esimulator_cli.py batch --dfg-filename 4004_dfg.txt
  ```

- **执行过程**:
  该命令会依次执行以下两个核心步骤：
  1.  **分析与掩码生成**:
      -   解析 `dfg_files/4004_dfg.txt`。
      -   在 `results/` 目录下生成 `4004_dfg_bind_masks.json`。该文件包含了对每个 `bind` 表达式进行 AST 分析后得到的 `workset` 掩码、可融合信息等。
  2.  **模拟退火优化**:
      -   读取上一步生成的 `bind_masks.json` 文件。
      -   以最小化硬件成本为目标，对 `workset` 的线性/非线性组合（即掩码）进行优化。
      -   在 `results/` 目录下生成 `4004_bindmask_sa_best.json`，其中包含全局最优的掩码配置和最终成本。

## 4. 单步执行 (可选)

如果您希望单独执行分析或优化，也可以使用 `analyze` 和 `compare` 子命令。

- **仅分析**:
  ```bash
  python esimulator_cli.py analyze --dfg-filename 4004_dfg.txt
  ```
  这将只生成 `..._bind_masks.json` 文件。

- **运行优化 (需先有分析结果)**:
  ```bash
  python esimulator_cli.py compare --dfg-filename 4004_dfg.txt
  ```
  这将读取已有的 `bind_masks.json` 并执行模拟退火优化。

## 5. 查看结果

所有输出文件都位于 `results/` 目录中。

- `..._bind_masks.json`: 详细的 `bind` 级分析结果，可用于调试或自定义后续处理。
- `..._bindmask_sa_best.json`: 最终的优化方案，可直接用于指导异构硬件（如 ONN/AMS）的映射。

**优化结果示例 (`..._bindmask_sa_best.json`)**:
```json
{
  "best_config": {
    "bind_masks": [ ... ] // 优化后的所有 bind 掩码
  },
  "best_cost": {
    "total_cost": 165.56, // 最小总成本
    "L_cost": 162.0,      // 线性单元成本
    "E_cost": 120.0,      // 非线性单元成本
    "C_cost": 42.0        // 接口成本
  },
  "statistics": { ... } // 统计信息
}
```

现在，您已经掌握了使用 ESIMULATOR 的基本流程。有关各模块更详细的说明，请参阅 `docs/MODULE_DOC.md`。

