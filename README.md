# ESIMULATOR - DFG线性分析工具

## 项目简介

本项目专注于Data Flow Graph (DFG)的线性分析，特别是Intel 4004 ALU的线性特征分析。项目提供了修正的分析方法，能够准确评估数字电路的线性度。

## 重要发现

**修正前后的关键差异：**
- 原始方法：63.2% 线性度（运算符级别统计）
- 修正方法：16.2% 线性度（表达式级别分析）
- 差异：47个百分点！

修正后的结果更准确地反映了Intel 4004 ALU作为非线性数字电路的本质特征。

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

## 引用

如果在学术研究中使用本工具，请注意：
- 使用修正后的16.2%线性度结果
- 不要使用原始方法的63.2%结果（已被证明是误导性的）

## 许可证

MIT License - 详见LICENSE文件
