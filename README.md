# ESIMULATOR

面向数字电路 Data Flow Graph (DFG) 的线性/非线性分析与分区优化实验平台。

> 目标：Verilog → DFG → 线性分析 → 图构建 → 分区优化（模拟退火）。

---

## ✨ 核心特性

- 递归解析 DFG 表达式（Operator / Concat / Branch / Partselect / Terminal / 常量）
- 基于 AST 的线性/非线性判定（避免简单字符串匹配局限）
- 统计报告：类别计数 / 运算符频率 / 非线性原因 / 线性比例
- 自动生成信号依赖图，导出 JSON / （可选）GEXF
- 模拟退火分区优化：多起点 + 自适应温度 + 多邻域扰动
- 成本策略插件化：simple / weighted / nonlinear_penalty / mixed
- 代码模块化，易于扩展更多图算法或分析维度

---

# ESIMULATOR

面向异构硬件（ONN/AMS）的数字电路数据流图（DFG）分析、掩码生成与分区优化平台。

> **核心流程**: Verilog → DFG → **Bind 级 AST 分析** → **Workset 掩码生成** → **模拟退火优化** → 硬件映射方案。

---

## ✨ 核心特性

- **深度 DFG 解析**: 基于 AST（抽象语法树）逐个 `bind` 表达式进行解析，精准识别 `Operator` / `Concat` / `Branch` / `Partselect` / `Terminal` 等单元。
- **Workset 概念**: 将 `Operator`、`Concat`、`Partselect` 等可映射单元统一为 `Workset`，为细粒度优化提供基础。
- **Bind 级掩码生成**:
  - 为每个 `bind` 表达式生成 `workset_order` (单元顺序) 和 `workset_mask` (线性/非线性状态)。
  - 导出 `fusable_adj` (可融合邻接表)，指导线性单元的硬件融合。
  - 包含 `bind_has_branch` (分支标记) 和 `sources` (源信号)，保留完整上下文。
- **模拟退火掩码优化**:
  - 以 `workset_mask` 为优化目标，通过“翻转”掩码位探索最优的线性/非线性组合。
  - 目标是最小化综合成本（面积、延迟、功耗、接口）。
- **可扩展成本模型**: 优化过程中的成本函数插件化，可根据目标硬件（如 ONN/AMS）的特性灵活调整。
- **模块化与自动化**: 代码结构清晰，支持一键运行从分析到优化的完整流程。

---

```text
ESIMULATOR/
├── dfg_files/                     # 输入 DFG 文件
├── results/                       # 分析与优化结果
├── src/
│   ├── analyzers/
│   │   └── dfg_linearity_corrector.py   # AST分析与掩码生成
│   └── simulated_annealing.py           # 掩码优化主流程
├── esimulator_cli.py              # 命令行工具入口
├── docs/
│   ├── QUICK_START.md             # 快速上手指南
│   └── MODULE_DOC.md              # 核心模块文档
└── README.md
```

---

## 🚀 快速上手

### 1. 准备 DFG

将 Verilog 通过外部工具转换为 DFG 格式，并放置于 `dfg_files/` 目录下，例如 `4004_dfg.txt`。

### 2. 运行分析与优化

通过命令行工具 `esimulator_cli.py` 一键完成所有操作。

```bash
# 运行针对 4004_dfg.txt 的完整流程
python esimulator_cli.py batch --dfg-filename 4004_dfg.txt
```

此命令将自动执行以下两步：

1. **分析与掩码生成**:
   - 读取 `dfg_files/4004_dfg.txt`。
   - 生成 `results/4004_dfg_bind_masks.json`，包含每个 `bind` 表达式的 `workset` 信息和掩码。

2. **模拟退火优化**:
   - 读取 `results/4004_dfg_bind_masks.json`。
   - 运行模拟退火算法，优化掩码组合。
   - 生成 `results/4004_bindmask_sa_best.json`，包含最优掩码、成本明细和统计数据。

---

## 📊 结果文件概览

### Bind 掩码文件 (`..._bind_masks.json`)

该文件是一个列表，每个元素对应一个 `bind` 表达式的分析结果。

```json
[
  {
    "bind_index": 0,
    "bind_statement": "wire [3:0] out = a + b;",
    "workset_order": ["ADD_0"],
    "workset_mask": [1],
    "fusable_adj": {},
    "bind_has_branch": false,
    "sources": ["a", "b"],
    "operator_count": 1
  },
  {
    "bind_index": 1,
    "bind_statement": "wire [7:0] d = {a, b};",
    "workset_order": ["CONCAT_0"],
    "workset_mask": [1],
    "fusable_adj": {},
    "bind_has_branch": false,
    "sources": ["a", "b"],
    "operator_count": 0
  }
]
```

### SA 优化结果 (`..._bindmask_sa_best.json`)

包含优化后的全局最佳配置和成本。

```json
{
  "best_config": {
    "bind_masks": [
      [1],
      [0]
    ]
  },
  "best_cost": {
    "total_cost": 165.56,
    "L_cost": 162.0,
    "E_cost": 120.0,
    "C_cost": 42.0
  },
  "statistics": {
    "total_binds": 81,
    "total_worksets": 162,
    "linear_worksets": 120,
    "nonlinear_worksets": 42
  }
}
```

---

## 🧠 Workset 与线性规则

- **Workset**: DFG 中可被独立映射为硬件单元的最小逻辑，当前主要包括 `Operator` (算术/逻辑运算), `Concat` (拼接), `Partselect` (位选)。
- **线性规则**:
  - **默认线性**: `+`, `-`, `~`, `&`, `|`, `^`, `concat`, `partselect` 等。
  - **默认非线性**: `*`, `/`, `%`, `>>`, `<<` 等。
  - **分支 (`Branch`)**: `if-else` 结构会限制其内部 `workset` 的融合，`bind_has_branch` 字段会标记此类情况。

这些规则定义在 `dfg_linearity_corrector.py` 中，可根据目标硬件特性进行扩展。

---

## 🧩 核心流程：从 DFG 到最优掩码

1. **DFG 解析**: 逐行读取 DFG 文件，分离出 `bind` 表达式。
2. **AST 构建**: 对每个 `bind` 表达式的右侧进行语法分析，构建 AST。
3. **Workset 提取**: 遍历 AST，识别出所有的 `Operator`, `Concat`, `Partselect`，并按出现顺序存入 `workset_order`。
4. **掩码与邻接表生成**:
   - 根据线性规则为 `workset_order` 中的每个单元生成初始的 `workset_mask` (1=线性, 0=非线性)。
   - 构建 `fusable_adj`，记录同 `bind` 内可融合的线性 `workset` 对。
5. **JSON 导出**: 将所有 `bind` 的分析结果保存至 `..._bind_masks.json`。
6. **模拟退火优化**:
   - 加载 `bind_masks.json` 作为初始解。
   - **邻域搜索**: 随机选择一个 `bind` 和其中的一个 `workset`，"翻转" 其在 `workset_mask` 中的状态 (1 ↔ 0)。
   - **成本评估**: 使用 `cost_function` (综合面积、延迟、功耗、接口) 评估新掩码的成本。
   - **Metropolis 准则**: 根据成本变化和当前温度决定是否接受新解。
   - 重复此过程直至收敛，输出全局最优的掩码组合。

---

## 🛠 成本模型

成本函数是 SA 优化的核心，它量化了一个给定的 `workset_mask` 组合有多“好”。当前模型位于 `simulated_annealing.py` 中，主要由三部分构成：

| 成本项 | 符号 | 描述 |
| :--- | :--- | :--- |
| **线性单元成本** | `L_cost` | 所有被标记为线性的 `workset` 单元的总面积/功耗。 |
| **非线性单元成本** | `E_cost` | 所有被标记为非线性的 `workset` 单元的总面积/功耗。 |
| **接口成本** | `C_cost` | 因 `workset` 融合状态改变而产生的内部连接成本。 |

**总成本 `Total_cost = w_L * L_cost + w_E * E_cost + w_C * C_cost`**

权重 `w_L`, `w_E`, `w_C` 可调，以平衡不同硬件资源的约束。

---

## ⚙️ 安装与运行

项目使用 `pyproject.toml` 管理依赖。

```bash
# 安装依赖
pip install -e .

# 运行 CLI
python esimulator_cli.py --help
```

---

## 🧾 TODO

- [ ] 结果可视化模块，展示优化前后的掩码分布。
- [ ] 集成上游工具链 (如 Yosys/Pyverilog) 实现 Verilog 到 DFG 的自动转换。
- [ ] 丰富成本模型，支持更复杂的硬件约束。

---

## 📄 许可证

MIT License


---

## 🚀 快速上手

### 1. 准备 DFG

将 Verilog 通过外部脚本/工具生成 `dfg_files/xxx_dfg.txt`。

### 2. 运行线性分析


```bash
python src/analyzers/dfg_linearity_corrector.py
- 图：`results/<name>_linearity_graph.json`（可供后续优化）

### 3. 运行分区优化

```bash
python src/simulated_annealing.py
```

检测到图 JSON 时会尝试加载并执行一次默认（mixed 策略）优化。

---

## 📊 报告内容概览

报告包含：

- 总表达式数、线性/非线性数量与比例
- 每类节点分布（terminal / constant / operator / concat / branch 等）
- 运算符使用频率排行
- 每个信号的判定原因（例如：包含乘法 → 非线性）
- 图节点/边统计与导出路径

图 JSON 示例：

```json
{
  "nodes": {
    "a": {"is_linear": true},
    "b": {"is_linear": false}
  },
  "edges": [["a", "c"], ["b", "c"]]
}
```

---

## 🧠 线性判定规则（默认）

- Terminal / 常量：线性
- Operator：所有子节点线性且运算符属于线性集合（如 +, -, 一元逻辑）
- Concat：所有子项线性 → 线性
- Partselect：底层对象线性 → 线性
- Branch（三目/条件）：任一分支非线性则非线性（可扩展策略）
- 包含 *, /, &, |, ^, <<, >> 等 → 非线性

可在解析代码中扩展 `linear_operators` 或添加白名单/黑名单逻辑。

---

## 🧩 图与优化流程

1. 解析表达式并收集依赖：对每个赋值/表达式识别其使用的信号形成有向边 (src → dst)
2. 构建节点属性：`is_linear` / `type`
3. 导出 JSON（必要）与 GEXF（可选）
4. 读取 JSON 转为 `networkx.DiGraph`
5. 模拟退火对节点分区（当前示例二域，可扩展多域）

---

## 🛠 成本策略 (`partitioning/cost_strategies.py`)

| 策略 | 说明 |
| ---- | ---- |
| simple_cross | 仅统计跨分区边数量 |
| weighted_cross | 线性/非线性源边不同权重 |
| nonlinear_penalty | 非线性节点放入指定域惩罚或奖励聚集 |
| mixed | 组合：跨域权重 + 非线性惩罚 + 线性聚集奖励 |

使用示例：

```python
from partitioning.cost_strategies import get_cost_function
cost_fn = get_cost_function(
    strategy="mixed",
    graph=g,
    partitions=2,
    w_cross_linear=1.0,
    w_cross_nonlinear=1.5,
    penalty_nonlinear_domain1=2.0,
    reward_linear_cluster=0.1,
)
score = cost_fn(partition_assignment_dict)
```

返回值为 `float`，可自由扩展为对象并兼容 `.total_cost` 属性。

---

## 🔥 模拟退火特点

- 多邻域：flip / linear_cluster / nonlinear_cluster / mixed_cluster
- 自适应温度：基于近期接受率或成本方差调节
- Multi-start：多随机初始解，取全局最优
- 支持将成本函数换成任意符合签名的函数
- 可插入额外约束（如固定某些节点分区）

---

## 🧪 自定义调用示例

```python
from analyzers.graph_loader import load_graph_from_json
from partitioning.cost_strategies import get_cost_function
from simulated_annealing import optimize

graph = load_graph_from_json("results/4004_dfg_linearity_graph.json")
cost_fn = get_cost_function("mixed", graph, partitions=2)
best = optimize(graph, cost_fn, partitions=2, max_iterations=2000)
print(best)
```

---

## ⚙️ 安装

项目使用 `pyproject.toml`：

```bash
pip install -e .
```

最小依赖（仅图 + 优化）：

```bash
pip install networkx
```

可选：

```bash
pip install lxml matplotlib
```

---

## 🗂 常见文件

| 作用 | 文件 |
| ---- | ---- |
| 线性分析 + 图导出 | `src/analyzers/dfg_linearity_corrector.py` |
| 图加载 | `src/analyzers/graph_loader.py` |
| 成本策略 | `src/partitioning/cost_strategies.py` |
| 模拟退火示例 | `src/simulated_annealing.py` |
| 使用示例 | `esimulator/examples/basic_usage.py` |
| 快速开始 | `QUICK_START.md` |
| 深度模块说明 | `MODULE_DOC.md` |
| 用户手册 | `docs/USER_MANUAL.md` |
| 结构指南 | `docs/USAGE_GUIDE_V2.md` |

---

## 🧾TODO

- [ ] 结果可视化
- [ ] 整合pyverilog等上游工具链
- [ ] 线性标记逻辑强化

---

## 📄 许可证

MIT License
