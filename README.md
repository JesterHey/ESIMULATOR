# ESIMULATOR 2.0 - DFG线性分析工具

## 🎯 项目简介

ESIMULATOR 2.0是一个专门用于Data Flow Graph (DFG)线性分析的工具套件，经过重新组织优化，提供了更强大的功能和更清晰的模块结构。


## 🚀 快速开始

### 命令行使用

```bash
# 基本分析
python esimulator_cli.py analyze dfg_files/4004_dfg.txt

# 批量分析
python esimulator_cli.py batch dfg_files/ --output results

# 可视化生成 (生成 DOT + 交互式 HTML)
python esimulator_cli.py visualize dfg_files/4004_dfg.txt

# 可视化带筛选/聚焦 (只看非线性, 以某节点为根, 深度=2)
python esimulator_cli.py visualize dfg_files/4004_dfg.txt \
	--output results/visualizations \
	--filter nonlinear \
	--focus alu1._rn0_result \
	--depth 2
```

### 程序化使用

```python
from esimulator import LinearityAnalyzer, ReportGenerator

# 创建分析器
analyzer = LinearityAnalyzer()

# 执行分析
result = analyzer.analyze_dfg_file("dfg_files/4004_dfg.txt")

# 生成报告
report_gen = ReportGenerator("results")
report_gen.generate_text_report(result)

# 可视化 (编程接口)
from esimulator.visual import visualize_from_dfg

visualize_from_dfg(
	'dfg_files/4004_dfg.txt',
	'results/visualizations',
	focus='alu1._rn0_result',
	depth=2,
	keep='nonlinear',  # 或 'linear'
	html=True,
	dot=True
)
print('生成: DOT + HTML')
```text

### 兼容性入口

```bash
python analyze_linearity_v2.py
python demo_comparison_v2.py
```

## 项目结构

```
ESIMULATOR/
├── src/                      # 源代码
│   ├── analyzers/           # 分析器模块
│   ├── parsers/             # 解析器模块
│   ├── visualizers/         # 可视化模块
│   └── utils/               # 工具模块
├── dfg_files/               # DFG输入文件
├── results/                 # 分析结果
│   ├── reports/             # 分析报告
│   └── data/                # 数据文件
├── tests/                   # 测试文件
├── docs/                    # 文档
└── examples/                # 示例代码
```

## 快速开始

### 运行线性分析

```bash
# 主要分析工具
python analyze_linearity.py

# 对比演示
python demo_comparison.py

# 运行测试
python tests/test_parsing_logic.py
```

### 核心功能

1. **DFG解析**: 解析Verilog DFG文件
2. **线性分析**: 按表达式级别分析线性特征
3. **结果对比**: 展示修正前后的差异
4. **可视化**: 生成 Graphviz DOT 与交互式 HTML 力导图 (支持筛选 / 聚焦)

## 技术细节

### 修正的分析方法

- **表达式级别分析**: 按信号表达式分析，而非单个运算符统计
- **递归解析**: 理解表达式的嵌套结构和运算优先级
- **类型分类**: 区分Terminal、Operator、Branch等不同表达式类型
- **整体判断**: 一个表达式包含任何非线性运算，整体就是非线性

### 线性运算符定义

- **线性**: Plus, Minus, Concat, Partselect
- **非线性**: And, Or, Xor, Unot, 比较运算, 分支运算

## 重要文件 (V2)

| 路径/模块 | 说明 |
|-----------|------|
| `esimulator/core/linearity_analyzer.py` | 新版表达式级线性分析引擎 |
| `esimulator/core/dfg_parser.py` | DFG 解析器 |
| `esimulator/core/report_generator.py` | 报告生成器 (文本/JSON) |
| `esimulator/visual/dfg_visual.py` | 可视化封装 (DOT & HTML) |
| `esimulator_cli.py` | 统一 CLI 入口 (analyze / compare / batch / visualize) |
| `src/visualization/dfg_linearity_viz.py` | 旧版可视化脚本 (deprecated, 向后兼容) |
| `results/` | 输出目录 (报告 / DOT / HTML / 图像) |

> 提示: 新项目推荐使用 `esimulator.visual.visualize_from_dfg` 生成可视化；旧脚本仍可用但后续将不再扩展。

### 可视化输出说明

1. DOT: 适合用 Graphviz 生成 PNG / SVG  (例: `dot -Tpng file.dot -o file.png`)
2. HTML: 自包含文件, 浏览器打开即可交互 (拖拽 / 搜索 / 邻居高亮 / 过滤按钮)
3. 过滤 (CLI `--filter`): 仅保留 `linear` 或 `nonlinear`
4. 聚焦 (CLI `--focus --depth`): 以根节点向前拓展指定层数并包含其直接前驱

### 指标字段 (HTML / API metrics)

| 字段 | 含义 |
|------|------|
| total_expressions | 有表达式的信号数 |
| linear_expressions | 线性表达式数 |
| nonlinear_expressions | 非线性表达式数 |
| linearity_ratio | 线性比例 |
| nonlinearity_ratio | 非线性比例 |
| nonlinear_reason_frequency | 非线性原因出现频次 |
| longest_linear_chain_length | 最长连续线性链长度 |
| longest_linear_chain_path | 该线性链路径 |


## 许可证

MIT License - 详见LICENSE文件
