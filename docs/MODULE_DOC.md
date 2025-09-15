# ESIMULATOR 核心模块文档

本文档详细介绍 ESIMULATOR 项目的两大核心模块：`dfg_linearity_corrector.py` (分析器) 和 `simulated_annealing.py` (优化器)，旨在帮助开发者理解其设计思想、工作流程和关键实现。

---

## 1. 分析器: `src/analyzers/dfg_linearity_corrector.py`

该模块是整个流程的起点，负责将输入的 DFG (数据流图) 文本文件转换为结构化的、可供优化的 JSON 数据。

### 1.1 核心功能

- **Bind 表达式解析**: 逐行读取 DFG 文件，并以 `bind` 语句为单位进行处理。
- **AST 构建**: 使用 `lark` 库对每个 `bind` 表达式的右侧进行语法分析，构建精确的抽象语法树 (AST)。这克服了早期版本中基于正则表达式和括号匹配的局限性。
- **Workset 提取与标记**:
  - **Workset**: 定义为 DFG 中可独立映射为硬件单元的最小逻辑，目前包括 `Operator` (算术/逻辑运算), `Concat` (拼接), `Partselect` (位选)。
  - 遍历 AST，识别出所有 `workset` 单元，并根据其类型和预设规则判断其**线性/非线性**属性。
- **结构化数据导出**: 为每个 `bind` 表达式生成一个包含丰富信息的 JSON 对象，最终汇集成一个列表。

### 1.2 工作流程

1.  **加载 DFG**: `CorrectedLinearityAnalyzer.analyze_dfg_file()` 读取指定的 DFG 文件。
2.  **遍历 Bind**: 对文件中的每个 `bind` 语句：
    a. **AST 解析**: 调用 `_parse_and_build_ast()`，使用 `lark.Lark` 解析器将表达式字符串转换为 AST。
    b. **Workset 遍历**: `_traverse_ast_and_collect_worksets()` 递归遍历 AST，识别 `Operator`, `Concat`, `Partselect` 节点。
    c. **信息收集**: 在遍历过程中，完成以下任务：
        - 将 `workset` 节点按出现顺序存入 `workset_order`。
        - 根据节点类型（如 `ADD` vs `MUL`）和线性规则，生成对应的 `workset_mask` (1=线性, 0=非线性)。
        - 记录 `bind` 表达式是否包含 `Branch` (if-else)，存入 `bind_has_branch`。
        - 识别并存储所有源信号 (`sources`)。
    d. **邻接表生成**: `_build_fusable_adj()` 根据 `workset_mask` 和 `bind_has_branch` 标志，构建 `fusable_adj`，记录同一 `bind` 内部可以融合的**线性** `workset` 对。
3.  **JSON 导出**: 所有 `bind` 表达式的分析结果被组织成一个 JSON 列表，并写入 `results/..._bind_masks.json` 文件。

### 1.3 输出 JSON 结构详解

每个 `bind` 表达式对应一个 JSON 对象：

```json
{
  "bind_index": 0,
  "bind_statement": "wire [3:0] out = a + b;",
  "workset_order": ["ADD_0"], // bind 内 workset 的名称和顺序
  "workset_mask": [1],        // 对应的线性掩码 (1=线性, 0=非线性)
  "fusable_adj": {},          // 可融合的线性 workset 对 (邻接表)
  "bind_has_branch": false,   // 是否包含 if-else 结构
  "sources": ["a", "b"],      // 该 bind 依赖的源信号
  "operator_count": 1         // Operator 类型 workset 的数量
}
```

---

## 2. 优化器: `src/simulated_annealing.py`

该模块接收分析器生成的 `bind_masks.json`，通过模拟退火 (SA) 算法对其进行优化，以找到成本最低的硬件映射方案。

### 2.1 核心功能

- **Bind 级掩码优化**: 优化的对象不再是整个 DFG 的节点划分，而是每个 `bind` 表达式内部 `workset` 的线性/非线性状态组合，即 `workset_mask`。
- **模拟退火**: 采用经典的 SA 框架，通过在解空间中随机游走并根据 Metropolis 准则接受新解，来寻找全局最优解。
- **成本函数**: 定义了一个量化硬件实现成本的函数，是 SA 优化的核心依据。
- **结果导出**: 输出最优的掩码组合 (`best_config`) 和对应的成本明细 (`best_cost`)。

### 2.2 工作流程

1.  **加载初始解**: `run_sa_optimization()` 读取 `..._bind_masks.json` 文件，提取所有 `bind` 的 `workset_mask` 作为 SA 的初始解。
2.  **SA 主循环**:
    a. **邻域搜索 (生成新解)**: `_get_neighbor()` 随机选择一个 `bind` 及其内部的一个 `workset`，将其掩码位进行“翻转”(1 ↔ 0)，生成一个新的掩码组合。
    b. **成本评估**: `_cost_function()` 计算新掩码组合的总成本。
    c. **接受准则**:
        - 如果新解成本更低，则接受。
        - 如果新解成本更高，则以一定概率 `exp(-delta_cost / temperature)` 接受（Metropolis 准则），以跳出局部最优。
    d. **降温**: `temperature` 随迭代次数增加而缓慢下降，使得算法在初期能探索更广阔的空间，在后期趋于收敛。
3.  **结果记录与导出**: 算法在迭代过程中始终记录遇到的全局最优解。循环结束后，将 `best_config` 和 `best_cost` 写入 `results/..._bindmask_sa_best.json`。

### 2.3 成本函数 (`_cost_function`)

成本函数是 SA 的“指挥棒”，它决定了优化的方向。当前模型包含三个部分：

| 成本项 | 符号 | 描述 |
| :--- | :--- | :--- |
| **线性单元成本** | `L_cost` | 所有被标记为线性的 `workset` 单元的总硬件成本（如面积、功耗）。成本系数 `L_UNIT_COST` 可调。 |
| **非线性单元成本**| `E_cost` | 所有被标记为非线性的 `workset` 单元的总硬件成本。成本系数 `E_UNIT_COST` 可调。 |
| **接口成本** | `C_cost` | 因 `workset` 融合状态改变而产生的内部连接成本。当一个 `bind` 内有多个线性 `workset` 时，它们可以融合，减少接口；反之，则增加接口。成本系数 `C_UNIT_COST` 可调。 |

**总成本 `Total_cost = L_cost + E_cost + C_cost`**

通过调整 `L_UNIT_COST`, `E_UNIT_COST`, `C_UNIT_COST` 这三个超参数，可以使优化过程倾向于不同的硬件实现目标（例如，优先节省非线性资源，或优先减少内部连线）。

---

## 3. 命令行接口: `esimulator_cli.py`

为了简化操作，项目提供了一个基于 `click` 的命令行工具，封装了分析和优化的完整流程。

- `esimulator_cli.py batch`: 运行完整流程，从分析到优化。
- `esimulator_cli.py analyze`: 仅运行分析器。
- `esimulator_cli.py compare`: 在已有分析结果上运行优化器。

这使得用户无需关心内部实现细节，即可快速得到最终的优化结果。

