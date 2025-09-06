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

## 🧱 目录结构（节选）

```text
ESIMULATOR/
├── verilog_files/                 # 输入 Verilog 源
├── dfg_files/                     # 外部生成的 DFG 描述
├── results/                       # 报告 & 图 & 优化输出
├── src/
│   ├── analyzers/
│   │   ├── dfg_linearity_corrector.py   # 线性分析 + 图导出
│   │   └── graph_loader.py              # 图 JSON -> networkx
│   ├── partitioning/
│   │   └── cost_strategies.py           # 成本函数策略
│   └── simulated_annealing.py           # 优化主流程
├── esimulator/examples/basic_usage.py   # 使用示例
├── QUICK_START.md
├── MODULE_DOC.md
├── docs/USER_MANUAL.md
├── docs/USAGE_GUIDE_V2.md
└── README.md
```

---

## 🚀 快速上手

### 1. 准备 DFG

将 Verilog 通过外部脚本/工具生成 `dfg_files/xxx_dfg.txt`。

### 2. 运行线性分析


```bash
python src/analyzers/dfg_linearity_corrector.py
```

输出：

- 文本报告：`results/<name>_linearity_analysis.txt`
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