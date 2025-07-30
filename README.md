# Intel 4004 ALU DFG到DAG分析项目

## 项目简介

本项目实现了将DFG（Data Flow Graph）文本转换为有向无环图（DAG）并进行拓扑排序的完整解决方案，专注于分析Intel 4004 ALU中不同信号之间的连接关系。

## 项目结构

```
ESIMULATOR/
├── src/                          # 源代码
│   ├── analyzers/               # 分析器模块
│   │   ├── correct_linearity_analyzer.py    # 正确的线性/非线性分析
│   │   ├── signal_connection_analyzer.py    # 信号连接分析
│   │   └── ...
│   ├── parsers/                 # 解析器模块  
│   │   ├── improved_dfg_parser.py          # 改进的DFG解析器
│   │   └── ...
│   ├── visualizers/             # 可视化工具
│   │   ├── dag_structure_visualizer.py     # DAG结构可视化
│   │   └── ...
│   ├── dag_structure_analyzer.py # DAG结构分析器
│   └── improved_dfg_to_dag.py   # 改进的DFG到DAG转换器
├── results/                      # 分析结果
│   ├── reports/                 # 文本报告
│   ├── data/                    # 结构化数据
│   └── visualizations/          # 图表文件
├── docs/                        # 文档
├── dfg_files/                   # DFG输入文件
├── verilog_files/              # Verilog源文件
└── examples/                   # 示例文件
```

## 核心功能

### 1. 正确的线性/非线性分析
- **线性运算**: 加法(+), 减法(-), 位移(<<, >>), 位拼接, 位选择
- **非线性运算**: 逻辑运算(&, |, ^, ~), 乘法(*), 除法(/), 比较运算

### 2. DAG结构分析  
- 拓扑排序
- 强连通分量检测
- 信号层次分析
- 关键路径识别

### 3. 信号连接关系分析
- 信号分类和统计
- 扇入扇出分析
- 连接类型识别
- 关键信号识别

### 4. 可视化
- DAG结构图
- 信号分布图
- 关键路径图
- 层次结构图

## 快速开始

1. **运行线性分析**:
   ```bash
   python src/analyzers/correct_linearity_analyzer.py
   ```

2. **生成DAG结构**:
   ```bash
   python src/dag_structure_analyzer.py
   ```

3. **信号连接分析**:
   ```bash
   python src/analyzers/signal_connection_analyzer.py
   ```

## 分析结果

### 线性度分析
- Intel 4004 ALU包含465个运算操作
- 线性运算: 294个 (63.2%)
- 非线性运算: 171个 (36.8%)

### DAG结构
- 58个主要信号
- 182个连接关系
- 最复杂信号: `alu.acc_out` (复杂度13)

### 关键发现
- 检测到1个包含49个节点的强连通分量
- 最长关键路径包含12个节点
- 75.3%的连接为组合逻辑, 24.7%为时序逻辑

## 技术特点

- ✅ 正确的数学线性定义
- ✅ 完整的DAG结构展示
- ✅ 清晰的项目组织结构
- ✅ 环路友好的图分析算法
- ✅ 多维度可视化支持

## 贡献

欢迎提交Issue和Pull Request来改进此项目。

## 许可证

MIT License
