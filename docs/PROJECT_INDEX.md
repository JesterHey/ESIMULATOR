# 项目文件索引

## 核心模块

### 分析器 (src/analyzers/)
- `correct_linearity_analyzer.py` - 正确的线性/非线性运算分析
- `signal_connection_analyzer.py` - 信号连接关系分析  
- `dfg_linearity_analyzer.py` - DFG线性度分析（早期版本）
- `verilog_linearity_analyzer.py` - Verilog源码线性分析

### 解析器 (src/parsers/)
- `improved_dfg_parser.py` - 改进的DFG解析器
- `dfg_parser.py` - 基础DFG解析器
- `dfg_to_python.py` - DFG到Python转换

### 可视化工具 (src/visualizers/)
- `dag_structure_visualizer.py` - DAG结构可视化（NetworkX版）
- `signal_visualization.py` - 信号关系可视化

### 核心工具 (src/)
- `dag_structure_analyzer.py` - DAG结构分析器（文本版）
- `improved_dfg_to_dag.py` - 改进的DFG到DAG转换器
- `dfg_to_dag_converter.py` - 基础DFG到DAG转换器

## 分析结果

### 报告文件 (results/reports/)
- `correct_linearity_analysis.txt` - 正确线性分析报告
- `dag_structure_report.txt` - DAG结构详细报告
- `4004_signal_connection_analysis.txt` - 信号连接分析报告
- `4004_ALU_Linearity_Summary.md` - ALU线性度总结

### 数据文件 (results/data/)
- `4004_signal_connections.json` - 信号连接结构化数据

### 可视化文件 (results/visualizations/)
- `4004_signal_distribution.png` - 信号类型分布图
- `4004_fan_in_out_analysis.png` - 扇入扇出分析图
- `4004_critical_path.png` - 关键路径可视化
- `4004_signal_hierarchy.png` - 信号层次结构图

## 文档 (docs/)
- `DFG_to_DAG_Analysis_Summary.md` - 项目完整总结报告
- `README_DFG_Framework.md` - DFG框架说明

## 输入数据
- `dfg_files/4004_dfg.txt` - Intel 4004 ALU的DFG文件
- `verilog_files/alu1.v` - ALU Verilog源码

## 使用说明

1. **基础分析流程**:
   ```bash
   # 1. 线性分析
   python src/analyzers/correct_linearity_analyzer.py
   
   # 2. 信号连接分析  
   python src/analyzers/signal_connection_analyzer.py
   
   # 3. DAG结构分析
   python src/dag_structure_analyzer.py
   ```

2. **高级分析**:
   ```bash
   # 强连通分量分析
   python src/improved_dfg_to_dag.py
   
   # 可视化生成
   python src/visualizers/signal_visualization.py
   ```

## 主要成果

- ✅ 解决了线性/非线性定义问题
- ✅ 提供了清晰的DAG结构展示
- ✅ 建立了整洁的项目文件结构
- ✅ 完成了Intel 4004 ALU的全面分析
