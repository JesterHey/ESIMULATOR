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

# 可视化生成
python esimulator_cli.py visualize dfg_files/4004_dfg.txt
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
```

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
4. **可视化**: 生成分析图表和报告

## 技术细节

### 修正的分析方法

- **表达式级别分析**: 按信号表达式分析，而非单个运算符统计
- **递归解析**: 理解表达式的嵌套结构和运算优先级
- **类型分类**: 区分Terminal、Operator、Branch等不同表达式类型
- **整体判断**: 一个表达式包含任何非线性运算，整体就是非线性

### 线性运算符定义

- **线性**: Plus, Minus, Concat, Partselect
- **非线性**: And, Or, Xor, Unot, 比较运算, 分支运算

## 重要文件

- `src/analyzers/dfg_linearity_corrector.py`: 修正的线性分析器
- `src/analyzers/analysis_comparator.py`: 方法对比工具
- `docs/DFG_Linearity_Correction.md`: 详细修正说明
- `results/reports/corrected_linearity_analysis.txt`: 分析报告


## 许可证

MIT License - 详见LICENSE文件
